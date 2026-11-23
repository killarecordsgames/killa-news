-- Classifiche dei giochi Killa Records (Il Mio Bar e Global Manager)
-- Partecipazione volontaria: compare solo chi sceglie un nickname dal sito.

create table if not exists public.classifica_iscritti (
  user_id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null,
  creato timestamptz not null default now(),
  constraint classifica_nickname_formato check (nickname ~ '^[A-Za-z0-9ÀÈÉÌÒÙàèéìòù_. -]{3,20}$')
);
create unique index if not exists classifica_nickname_unico on public.classifica_iscritti (lower(nickname));

create table if not exists public.classifica_snapshot (
  settimana date not null,
  gioco text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  valore numeric not null,
  primary key (settimana, gioco, user_id)
);

create table if not exists public.classifica_vincitori (
  settimana date not null,
  gioco text not null,
  nickname text not null,
  punteggio numeric not null,
  primary key (settimana, gioco)
);

create table if not exists public.classifica_settimane_chiuse (
  settimana date primary key,
  chiusa timestamptz not null default now()
);

alter table public.classifica_iscritti enable row level security;
alter table public.classifica_snapshot enable row level security;
alter table public.classifica_vincitori enable row level security;
alter table public.classifica_settimane_chiuse enable row level security;

drop policy if exists "leggo la mia iscrizione" on public.classifica_iscritti;
create policy "leggo la mia iscrizione" on public.classifica_iscritti for select to authenticated using (auth.uid() = user_id);
drop policy if exists "mi iscrivo" on public.classifica_iscritti;
create policy "mi iscrivo" on public.classifica_iscritti for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "cambio nickname" on public.classifica_iscritti;
create policy "cambio nickname" on public.classifica_iscritti for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "esco dalla classifica" on public.classifica_iscritti;
create policy "esco dalla classifica" on public.classifica_iscritti for delete to authenticated using (auth.uid() = user_id);
grant select, insert, update, delete on public.classifica_iscritti to authenticated;

drop policy if exists "vincitori pubblici" on public.classifica_vincitori;
create policy "vincitori pubblici" on public.classifica_vincitori for select to anon, authenticated using (true);
grant select on public.classifica_vincitori to anon, authenticated;

-- Settimana che inizia il lunedì, ora italiana
create or replace function public.kr_settimana() returns date
language sql stable as $$ select (date_trunc('week', now() at time zone 'Europe/Rome'))::date $$;

-- Valori attuali dei giocatori: cassa del bar, patrimonio verificato del manager
create or replace function public.kr_valori() returns table (gioco text, user_id uuid, valore numeric)
language sql stable security definer set search_path = public as $$
  select 'bar', s.user_id, coalesce(s.cash, 0)::numeric from saves s
  union all
  select 'gm', p.id, coalesce(p.patrimonio_verificato, 0)::numeric from gm_profili p where not coalesce(p.invisibile, false)
$$;

-- Nickname: controllo parole offensive e fotografia di partenza alla prima iscrizione
create or replace function public.kr_iscrizione_controlla() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.nickname := btrim(regexp_replace(new.nickname, '\s+', ' ', 'g'));
  if lower(new.nickname) ~ '(cazz|merd|puttan|troi|vaffanc|coglion|stronz|negr|froc|ricchion|hitler|nazi|porco ?dio|dio ?porco|madonna|fuck|shit|bitch|admin|killa ?records)' then
    raise exception 'Questo nickname non è consentito. Scegline un altro.';
  end if;
  return new;
end $$;

create or replace function public.kr_iscrizione_fotografia() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into classifica_snapshot (settimana, gioco, user_id, valore)
  select kr_settimana(), v.gioco, v.user_id, v.valore from kr_valori() v where v.user_id = new.user_id
  on conflict do nothing;
  return new;
end $$;

drop trigger if exists kr_iscrizione_controlla on public.classifica_iscritti;
create trigger kr_iscrizione_controlla before insert or update on public.classifica_iscritti
for each row execute function public.kr_iscrizione_controlla();
drop trigger if exists kr_iscrizione_fotografia on public.classifica_iscritti;
create trigger kr_iscrizione_fotografia after insert on public.classifica_iscritti
for each row execute function public.kr_iscrizione_fotografia();

-- Classifica di una settimana: crescita dall'inizio della settimana (punteggio) e totale attuale
create or replace function public.kr_classifica(p_settimana date)
returns table (gioco text, posizione int, nickname text, punteggio numeric, totale numeric)
language sql stable security definer set search_path = public as $$
  with v as (
    select v.gioco, v.user_id, v.valore, i.nickname,
           v.valore - coalesce(sn.valore, v.valore) as crescita
    from kr_valori() v
    join classifica_iscritti i on i.user_id = v.user_id
    left join classifica_snapshot sn on sn.settimana = p_settimana and sn.gioco = v.gioco and sn.user_id = v.user_id
  )
  select gioco, (row_number() over (partition by gioco order by crescita desc, valore desc, nickname))::int,
         nickname, crescita, valore
  from v order by gioco, 2
$$;

-- Pubblica: classifica della settimana in corso (solo nickname e numeri)
create or replace function public.classifica_corrente()
returns table (gioco text, posizione int, nickname text, punteggio numeric, totale numeric, settimana date)
language sql stable security definer set search_path = public as $$
  select c.*, kr_settimana() from kr_classifica(kr_settimana()) c where c.posizione <= 20
$$;

-- Chiusura settimanale: salva i vincitori della settimana passata e fa la nuova fotografia.
-- Gira ogni ora ma lavora una sola volta per settimana (anche con l'ora legale).
create or replace function public.kr_chiudi_settimana() returns text
language plpgsql security definer set search_path = public as $$
declare w date := kr_settimana(); wp date := kr_settimana() - 7; n int := 0;
begin
  if exists (select 1 from classifica_settimane_chiuse where settimana = w) then
    return 'già fatto';
  end if;
  if exists (select 1 from classifica_snapshot where settimana = wp) then
    insert into classifica_vincitori (settimana, gioco, nickname, punteggio)
    select wp, c.gioco, c.nickname, c.punteggio from kr_classifica(wp) c
    where c.posizione = 1 and c.punteggio > 0
    on conflict do nothing;
    get diagnostics n = row_count;
  end if;
  insert into classifica_snapshot (settimana, gioco, user_id, valore)
  select w, v.gioco, v.user_id, v.valore from kr_valori() v
  join classifica_iscritti i on i.user_id = v.user_id
  on conflict do nothing;
  delete from classifica_snapshot where settimana < w - 56;
  insert into classifica_settimane_chiuse (settimana) values (w);
  return 'chiusa, vincitori: ' || n;
end $$;

revoke all on function public.kr_valori() from public, anon, authenticated;
revoke all on function public.kr_classifica(date) from public, anon, authenticated;
revoke all on function public.kr_chiudi_settimana() from public, anon, authenticated;
revoke all on function public.kr_iscrizione_fotografia() from public, anon, authenticated;
revoke all on function public.kr_iscrizione_controlla() from public, anon, authenticated;
grant execute on function public.classifica_corrente() to anon, authenticated;
grant execute on function public.kr_settimana() to anon, authenticated;

select cron.unschedule(jobid) from cron.job where jobname = 'kr-classifica-settimanale';
select cron.schedule('kr-classifica-settimanale', '5 * * * *', 'select public.kr_chiudi_settimana()');

select public.kr_chiudi_settimana();
