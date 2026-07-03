-- Investment Walk-Forward-Lern-Loop -- Supabase-Schema (CEO-gewuenscht 2026-07-03).
-- Vom CEO in der Supabase-SQL-Konsole auszufuehren (Schema-Aenderung = CEO-Tor).
-- Nur LUNA-OS greift server-seitig (service_role) darauf zu. Kein echtes Geld, keine Trades -- reine
-- Datenhaltung fuer den Prognose-Lern-Loop: taeglich Merkmale sammeln -> 7-Tage-Prognose -> Abgleich mit der
-- Realitaet -> Abweichungen SEPARAT und dauerhaft festhalten -> messen, ob die Abweichung ueber Zeit kleiner
-- wird. Alle Tabellen append-only gedacht; das Abweichungs-Register wird nie ueberschrieben.

create extension if not exists pgcrypto;

-- 1) Taeglicher Merkmals-/Preis-Snapshot je Wert (baut unsere eigene Kurs-Historie auf).
create table if not exists public.inv_features (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  asset text not null default 'aktie',            -- aktie | krypto
  datum date not null,
  close numeric,                                  -- Schlusskurs/aktueller Kurs zum Snapshot
  change_pct numeric,                             -- Tagesveraenderung in %
  features jsonb not null default '{}'::jsonb,    -- abgeleitet: ret_1d/5d/20d, vola_20d, sma_5/20, mom_10, n_hist
  baseline boolean not null default false,        -- true = Benchmark-Serie (z. B. SPY, BTC)
  quelle text,
  created_at timestamptz not null default now(),
  unique (symbol, datum)                          -- ein Snapshot je Wert je Tag (Upsert-Schluessel)
);
create index if not exists inv_features_symbol_datum on public.inv_features (symbol, datum);

-- 2) Prognose: zum Zeitpunkt erstellt_am eine Vorhersage fuer faellig_am (= +7 Tage).
create table if not exists public.inv_forecasts (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  asset text not null default 'aktie',
  erstellt_am date not null,
  faellig_am date not null,
  richtung text,                                  -- steigt | faellt | seitwaerts
  ziel_return_pct numeric,                        -- erwartete Rendite (Mittel der Spanne)
  spanne_low numeric,
  spanne_high numeric,
  konfidenz numeric,                              -- 0..1
  modell_version text not null default 'v1',      -- Wissens-/Modellstand (macht Verbesserung zuordenbar)
  features_ref jsonb not null default '{}'::jsonb, -- genutzte Merkmale/Signale (Transparenz)
  rationale text,
  baseline_richtung text,                         -- naive Vergleichs-Prognose (die Messlatte)
  baseline_return_pct numeric,
  status text not null default 'offen',           -- offen | ausgewertet
  created_at timestamptz not null default now()
);
create index if not exists inv_forecasts_faellig on public.inv_forecasts (faellig_am, status);

-- 3) Eingetretene Realitaet zu einer Prognose (nach Ablauf der 7 Tage).
create table if not exists public.inv_actuals (
  id uuid primary key default gen_random_uuid(),
  forecast_id uuid references public.inv_forecasts (id),
  symbol text not null,
  faellig_am date not null,
  real_return_pct numeric,
  real_richtung text,
  created_at timestamptz not null default now()
);

-- 4) ABWEICHUNGS-REGISTER -- SEPARAT und dauerhaft (CEO-Anforderung). Nie ueberschreiben.
--    Der Beweis, ob Daten-/Wissens-Anreicherung die Prognosen ueber Zeit genauer macht.
create table if not exists public.inv_deviations (
  id uuid primary key default gen_random_uuid(),
  forecast_id uuid references public.inv_forecasts (id),
  symbol text not null,
  modell_version text not null,
  erstellt_am date not null,
  faellig_am date not null,
  prognose_return_pct numeric,
  real_return_pct numeric,
  fehler_abs_pct numeric,                         -- |Prognose - Real| (der Kern-Fehler)
  richtungstreffer boolean,                       -- Richtung richtig getroffen?
  baseline_fehler_abs_pct numeric,                -- Fehler der naiven Baseline zum Vergleich
  besser_als_baseline boolean,                    -- haben wir die Messlatte geschlagen?
  konfidenz numeric,
  regime text,                                    -- Marktphase (z. B. hohe/niedrige Vola) fuer spaetere Analyse
  created_at timestamptz not null default now()
);
create index if not exists inv_deviations_version on public.inv_deviations (modell_version, faellig_am);

-- 5) Lern-Log: was sich zwischen den Zyklen geaendert hat (damit Verbesserung zuordenbar ist).
create table if not exists public.inv_model_runs (
  id uuid primary key default gen_random_uuid(),
  version text not null,
  datum date not null,
  was_geaendert text,
  warum text,
  kennzahlen jsonb not null default '{}'::jsonb,  -- z. B. { "mae": .., "richtungsquote": .., "vs_baseline": .. }
  created_at timestamptz not null default now()
);

alter table public.inv_features enable row level security;
alter table public.inv_forecasts enable row level security;
alter table public.inv_actuals enable row level security;
alter table public.inv_deviations enable row level security;
alter table public.inv_model_runs enable row level security;
