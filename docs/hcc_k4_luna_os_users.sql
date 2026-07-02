-- K4 -- Team-Auth fuer LUNA-OS: Nutzer-Tabelle (Mehr-Nutzer-Login + Rollen/Module).
-- Vom CEO in der Supabase-SQL-Konsole des Projekts (nilshubv2) auszufuehren (Schema-Aenderung = CEO-Tor).
-- LUNA-OS liest/schreibt diese Tabelle server-seitig mit dem service_role-Key (umgeht RLS). Die Tabelle
-- ist NICHT fuer den anonymen/Browser-Zugriff gedacht -- daher bewusst KEINE permissiven RLS-Policies.

create extension if not exists pgcrypto;

create table if not exists public.luna_os_users (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  password_hash text not null,                 -- PBKDF2 (pbkdf2_sha256$iter$salt$hash); nie Klartext
  display_name text,
  role text not null default 'content',        -- owner = Superuser; sonst zaehlt allowed_modules
  allowed_modules text[] not null default '{content_ops}'::text[],
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- updated_at automatisch pflegen (Funktion existiert aus 001_initial_schema.sql).
drop trigger if exists set_luna_os_users_updated_at on public.luna_os_users;
create trigger set_luna_os_users_updated_at
  before update on public.luna_os_users
  for each row execute function public.update_updated_at_column();

-- RLS an, ohne Policies: nur der service_role-Key (LUNA-OS-Backend) kommt an die Daten.
alter table public.luna_os_users enable row level security;

-- Nutzer anlegen NICHT hier (Passwoerter gehoeren nicht ins Repo). Stattdessen lokal/auf der NAS:
--   python -m orchestrator.core.team_auth add <username> <passwort> [rolle] [modul,modul]
-- Rollen: owner|admin (alle Module) · team (content_ops,crm) · content|viewer (content_ops).
-- Module: content_ops · crm · invest · administration.
