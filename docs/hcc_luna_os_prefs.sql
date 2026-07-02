-- #2 -- Nutzer-Praeferenzen fuer LUNA-OS (pro Nutzer, geraeteuebergreifend), z. B. das Dashboard-Layout.
-- Vom CEO in der Supabase-SQL-Konsole (Projekt nilshubv2) auszufuehren (Schema-Aenderung = CEO-Tor).
-- Nur LUNA-OS greift server-seitig (service_role) darauf zu; jeder Nutzer liest/schreibt nur seine Zeile.

create extension if not exists pgcrypto;

create table if not exists public.luna_os_prefs (
  username text primary key,
  prefs jsonb not null default '{}'::jsonb,     -- z. B. { "dashboard": { "order": [...], "hidden": [...] } }
  updated_at timestamptz not null default now()
);

drop trigger if exists set_luna_os_prefs_updated_at on public.luna_os_prefs;
create trigger set_luna_os_prefs_updated_at
  before update on public.luna_os_prefs
  for each row execute function public.update_updated_at_column();

alter table public.luna_os_prefs enable row level security;
