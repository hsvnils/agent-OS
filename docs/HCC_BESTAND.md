# HCC-Bestandsaufnahme (Hanserautisch Command Center)

> Momentaufnahme des bestehenden Dashboards `~/Documents/nilshubv2` (Repo `hanserautisch-command-center`).
> Grundlage fuer die HCC<->LUNA-Integration (siehe `HCC_INTEGRATION_ROADMAP.md`). Stand 2026-07-02.

## Was es ist
Next.js + Supabase, dunkles **Content-Operations-Dashboard fuer ein Instagram-Creator-Team**. Auth per
Supabase (Magic Link + E-Mail/Passwort), Team-Rollen, modulbasierte Zugriffssteuerung. Zusaetzlich ein
getrennter **Synology-Worker** (Node/TS, Docker) fuer serverseitige Aufgaben (aktuell **offline**). NAS hat
einen eigenen Docker-Ordner dafuer. Ursprung: eine fruehere, parallele Auspraegung derselben Idee wie LUNA.

## Module (kanonisch, aus `profiles.allowed_modules`)
`content_ops` · `telegram` · `agents_workers` · `invest` · `administration`
(Nicht-Owner-Default: `content_ops` + `telegram`.)

## Bereiche / Routen (app/)
- **content_ops:** `trends`, `content-radar`, `drafts`, `ideas`, `sources`, `ai-inbox` — Trend-Inbox,
  KI-Entwuerfe je Trend, Ideen-Labor, Draft-Uebersicht, Quellen-Monitor, AI-Intel-Inbox.
- **telegram:** `telegram`, `telegram-bots` — Bot-Konfiguration + Telegram-Intake (Inputs/Router).
- **agents_workers:** `agents`, `agent-config`, `agents-office`, `workers`, `video-cutter` — Agenten-Laeufe/
  Konfiguration + Worker-Status + **Video-Cutter** (Jobs/Revisionen/Segmente/Outputs).
- **invest:** `invest` — Investment-Ansicht.
- **administration:** `team`, `settings`, `security`, `profile`, `auth`, `notifications`, `activity` —
  Teamverwaltung/Rollen, Einstellungen (Supabase/Auth/Telegram/Keys), Security Center, Benachrichtigungen,
  Aktivitaets-Log.

## Supabase-Schema (Tabellen, 29 Migrationen)
- **Content:** `sources`, `trend_signals`, `trend_candidate_reviews`, `content_findings`, `content_drafts`,
  `ideas`, `idea_candidate_reviews`, `draft_suggestion_reviews`, `ai_intel_items`, `ai_intel_assets`.
- **Telegram:** `telegram_bot_configs`, `telegram_inputs`.
- **Agenten/Worker:** `agent_configs`, `agent_runs`, `worker_instances`, `worker_tasks`, `worker_state`.
- **Video-Cutter:** `cutter_jobs`, `cutter_revisions`, `cutter_job_logs`, `cutter_workers`, `cutter_segments`,
  `cutter_timings`, `cutter_perf_stats`, `cutter_outputs`.
- **Ops/Team:** `profiles`, `team_members`, `notifications`, `approvals`, `activity_events`.
- **KEIN CRM/Kontakte/Leads** — muss fuer die geteilte CRM-Basis neu angelegt werden.

## Worker (Synology, aktuell offline)
Node/TS-Dienst, laeuft getrennt von der Web-App. Schreibt Heartbeats, `agent_runs`, `worker_tasks`,
`activity_events` nach Supabase; treibt den Video-Cutter. Aktuell keine echten Scraper/KI-Calls.

## Ueberschneidung mit LUNA (luna-os)
Agenten, Telegram, Trends/Content, Video-Cutter, Invest, Notifications/Approvals/Activity gibt es in beiden.
Konsequenz fuer die Integration: **luna-os hat Vorrang**; die HCC-eigenen Agenten/Invest/Worker-Logiken werden
zugunsten von LUNA abgeloest, HCC bleibt das **Team-Web-Gesicht** (siehe Roadmap).
