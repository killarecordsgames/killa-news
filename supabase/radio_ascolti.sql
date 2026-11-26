-- KILLA RADIO: contatore anonimo degli ascoltatori del Vault.
-- Ogni pagina con la radio accesa manda un segnale ogni 30 secondi: si salva una riga per sessione e per minuto.
-- Nessun dato personale oltre all'utente del Vault (che è già membro); le righe più vecchie di 90 giorni si cancellano.

create table if not exists public.radio_ascolti (
  sessione text not null check (char_length(sessione) between 8 and 40),
  user_id uuid not null references auth.users (id) on delete cascade,
  minuto timestamptz not null,
  primary key (sessione, minuto)
);
create index if not exists radio_ascolti_minuto on public.radio_ascolti (minuto);

alter table public.radio_ascolti enable row level security;
revoke all on public.radio_ascolti from anon, authenticated;
grant select, insert, delete on public.radio_ascolti to service_role;

create or replace function public.radio_statistiche() returns json
language sql security definer set search_path = public as $$
  with r as (
    select sessione, user_id, minuto, (minuto at time zone 'Europe/Rome') as loc
    from radio_ascolti where minuto > now() - interval '8 days'
  ),
  per_min as (select minuto, count(distinct sessione) as n from r group by minuto),
  giorni as (select loc::date as g, count(distinct user_id) as persone, count(*) as minuti from r group by 1),
  picchi as (
    select distinct on ((minuto at time zone 'Europe/Rome')::date)
      (minuto at time zone 'Europe/Rome')::date as g, n, to_char(minuto at time zone 'Europe/Rome', 'HH24:MI') as ora
    from per_min order by (minuto at time zone 'Europe/Rome')::date, n desc, minuto
  )
  select json_build_object(
    'ora', (select count(distinct sessione) from radio_ascolti where minuto >= date_trunc('minute', now()) - interval '1 minute'),
    'giorni', (select coalesce(json_agg(json_build_object('giorno', g.g, 'persone', g.persone, 'minuti', g.minuti, 'picco', p.n, 'ora_picco', p.ora) order by g.g desc), '[]'::json)
               from giorni g left join picchi p on p.g = g.g)
  );
$$;
revoke execute on function public.radio_statistiche() from public, anon, authenticated;
grant execute on function public.radio_statistiche() to service_role;
