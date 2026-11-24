-- Consensi all'informativa del bot Telegram di KILLA NEWS.
-- Si conserva solo un codice cifrato (SHA-256) dell'utente e la data: niente nomi, numeri o messaggi.
create table if not exists public.telegram_consensi (
  codice text primary key,
  accettato_il timestamptz not null default now(),
  versione text not null default '2026-11-24'
);
alter table public.telegram_consensi enable row level security;
-- Nessuna policy: solo la funzione del bot (chiave di servizio) può leggere e scrivere.
revoke all on public.telegram_consensi from anon, authenticated;
grant select, insert, update, delete on public.telegram_consensi to service_role;

-- Impostazioni del bot (gruppo Killa Radio collegato, ultimo post del mattino)
create table if not exists public.telegram_config (chiave text primary key, valore text not null default '');
alter table public.telegram_config enable row level security;
revoke all on public.telegram_config from anon, authenticated;
grant select, insert, update, delete on public.telegram_config to service_role;
grant select, update on public.vault_stato to service_role;
