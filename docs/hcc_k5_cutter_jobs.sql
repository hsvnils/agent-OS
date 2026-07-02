-- K5 -- LUNA-Cutter-Jobs (geteilte Status/Historie zwischen Mac-Cutter und LUNA-OS auf der NAS).
-- Vom CEO in der Supabase-SQL-Konsole (Projekt nilshubv2) auszufuehren (Schema-Aenderung = CEO-Tor).
-- Nur LUNA-OS greift server-seitig (service_role) darauf zu; der Mac-Cutter meldet ueber die LUNA-OS-API.
--
-- WICHTIG: bewusst EIGENE Tabelle `luna_cutter_jobs` -- NICHT das alte HCC `cutter_jobs` (Migration 028,
-- ganz anderes Schema: title/source_folder/error + Status-CHECK). Das alte cutter_jobs wird in K6 gedroppt.

create extension if not exists pgcrypto;

create table if not exists public.luna_cutter_jobs (
  id uuid primary key default gen_random_uuid(),
  projekt text not null,                        -- Ordnername in der Cutter-Inbox
  status text not null default 'queued',        -- queued | running | done | failed
  quelle text default 'luna-os',                -- luna-os (aus der UI angestossen) | mac (auto-verarbeitet)
  clips_verwendet integer,
  dauer_sek numeric,
  untertitel text,
  reel_datei text,
  groesse_mb numeric,
  fehler text,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- updated_at automatisch pflegen (Funktion existiert aus 001_initial_schema.sql).
drop trigger if exists set_luna_cutter_jobs_updated_at on public.luna_cutter_jobs;
create trigger set_luna_cutter_jobs_updated_at
  before update on public.luna_cutter_jobs
  for each row execute function public.update_updated_at_column();

-- RLS an, ohne Policies: nur der service_role-Key (LUNA-OS) kommt an die Daten.
alter table public.luna_cutter_jobs enable row level security;

-- HINWEIS: Die erste (falsche) K5-Migration hat versehentlich `alter table public.cutter_jobs enable row
-- level security` auf der ALTEN HCC-Tabelle ausgefuehrt. Falls der alte HCC-Cutter-Worker vor K6 noch
-- Zugriff braucht, hier zuruecknehmen:  alter table public.cutter_jobs disable row level security;
-- (LUNA-OS nutzt die alte Tabelle nicht -- fuer LUNA ist das egal.)
