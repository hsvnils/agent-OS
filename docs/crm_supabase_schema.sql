-- Geteilte Collab-CRM-Tabellen (LUNA <-> HCC), Architektur A (relationale Projektion).
-- LUNA projiziert per Write-Through den AKTUELLEN Stand hierher; das lokale Event-Log auf der NAS bleibt
-- Quelle + Offline-Fallback. `updated_by` (luna|hcc) fuer Nachvollziehbarkeit/Vorrang (luna-os gewinnt).
-- Ausfuehren im Supabase SQL-Editor. RLS ist aktiviert (deny-all fuer anon) -- fuers HCC-Frontend spaeter
-- Lese-/Schreib-Policies nach eurem bestehenden Muster ergaenzen. service_role (LUNA) umgeht RLS.

create table if not exists public.crm_companies (
  id uuid primary key default gen_random_uuid(),
  ref text unique not null,                 -- stabiler Schluessel (normalisierter Firmen-/Absendername)
  firma text not null,                      -- Anzeigename
  status text not null default 'neu',       -- neu|in_gespraech|angebot|vereinbart|abgelehnt
  quelle text,                              -- instagram|telegram|gmail|manuell
  nachrichten integer not null default 0,
  letzter_kontakt timestamptz,
  updated_at timestamptz not null default now(),
  updated_by text not null default 'luna'   -- luna|hcc
);

create table if not exists public.crm_messages (
  id uuid primary key default gen_random_uuid(),
  extern_id text unique,                     -- Meta-Message-ID (Dedup); null erlaubt (manuelle Eintraege)
  ref text not null references public.crm_companies(ref) on delete cascade,
  firma text not null,
  richtung text not null default 'ein',      -- ein|aus
  quelle text,
  kategorie text,                            -- kooperation|unklar
  text text not null,
  ts timestamptz not null default now()
);

create table if not exists public.crm_todos (
  id text primary key,                       -- LUNAs To-do-ID (T-...)
  ref text not null references public.crm_companies(ref) on delete cascade,
  firma text not null,
  vorschlag text not null,
  begruendung text,
  status text not null default 'offen',      -- offen|erledigt
  faellig text,
  updated_at timestamptz not null default now(),
  updated_by text not null default 'luna'
);

create index if not exists crm_messages_ref_idx on public.crm_messages(ref);
create index if not exists crm_todos_ref_idx on public.crm_todos(ref);

alter table public.crm_companies enable row level security;
alter table public.crm_messages enable row level security;
alter table public.crm_todos enable row level security;
