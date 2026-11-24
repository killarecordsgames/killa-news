-- KILLA VAULT: area riservata del sito, si entra solo su invito.
-- Le tabelle si leggono e si scrivono solo dalla funzione killa-vault (chiave di servizio).

create table if not exists public.vault_richieste (
  id uuid primary key default gen_random_uuid(),
  nickname text not null check (char_length(nickname) between 3 and 24),
  email text not null check (char_length(email) <= 254),
  creata_il timestamptz not null default now(),
  stato text not null default 'in_attesa' check (stato in ('in_attesa', 'invitato', 'iscritto', 'rifiutato')),
  codice_hash text,
  codice_scade timestamptz,
  invitata_il timestamptz
);
create unique index if not exists vault_richieste_email on public.vault_richieste (lower(email));

create table if not exists public.vault_membri (
  user_id uuid primary key references auth.users (id) on delete cascade,
  nickname text not null unique,
  tessera integer generated always as identity unique,
  entrato_il timestamptz not null default now()
);

create table if not exists public.vault_stato (
  id integer primary key default 1 check (id = 1),
  in_diretta boolean not null default false,
  titolo_diretta text not null default '',
  link_diretta text not null default '',
  aggiornato_il timestamptz not null default now()
);
insert into public.vault_stato (id) values (1) on conflict do nothing;

alter table public.vault_richieste enable row level security;
alter table public.vault_membri enable row level security;
alter table public.vault_stato enable row level security;
revoke all on public.vault_richieste, public.vault_membri, public.vault_stato from anon, authenticated;
grant select, insert, update, delete on public.vault_richieste, public.vault_membri, public.vault_stato to service_role;
