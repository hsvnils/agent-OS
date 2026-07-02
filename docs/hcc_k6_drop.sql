-- K6 -- Aufraeumen der alten HCC-Tabellen (nilshubv2 + Worker werden stillgelegt).
-- =====================================================================================
-- VORHER PFLICHT (CEO):
--   1. Supabase-Dashboard-Backup (Backup #1) bestaetigt vorhanden.
--   2. CSV-Export (Backup #2) liegt auf der NAS: ~/k6_backup_<ts>/ (von Claude erstellt).
--   3. Team nutzt nur noch LUNA-OS; HCC-Vercel-Deployment wird abgeschaltet.
--   4. K3 scharf (CONTENT_FEED_ENABLED=1 gesetzt) + luna-telegram neu gestartet.
-- LOESCHEN = CEO-Tor. Diese Datei NUR nach obiger Bestaetigung im Supabase-SQL-Editor ausfuehren.
--
-- BEHALTEN (LUNA-OS nutzt sie -- NICHT anfassen):
--   trend_signals, ideas, content_drafts, sources, ai_intel_items,
--   crm_companies, crm_messages, crm_todos, luna_os_users, luna_cutter_jobs
-- =====================================================================================

begin;

-- 1) Alter HCC-Video-Cutter (Testdaten; LUNA nutzt luna_cutter_jobs)
drop table if exists public.cutter_job_logs   cascade;
drop table if exists public.cutter_outputs    cascade;
drop table if exists public.cutter_perf_stats cascade;
drop table if exists public.cutter_revisions  cascade;
drop table if exists public.cutter_segments   cascade;
drop table if exists public.cutter_timings    cascade;
drop table if exists public.cutter_workers    cascade;
drop table if exists public.cutter_jobs       cascade;
-- zugehoerige Worker-Funktion (Signatur ggf. anpassen, falls Fehler):
drop function if exists public.claim_next_cutter_job cascade;

-- 2) Alter Synology-Worker + Agenten (seit 2026-06-27 tot)
drop table if exists public.worker_tasks     cascade;
drop table if exists public.worker_state     cascade;
drop table if exists public.worker_instances cascade;
drop table if exists public.agent_runs       cascade;
drop table if exists public.agent_configs    cascade;
drop table if exists public.activity_events  cascade;

-- 3) Alter Telegram-Intake (LUNA hat eigenen Telegram-Bot)
drop table if exists public.telegram_inputs      cascade;
drop table if exists public.telegram_bot_configs cascade;

-- 4) HCC-Review-Meta + Ops (CEO: loeschen; LUNA nutzt sie nicht)
drop table if exists public.content_findings          cascade;
drop table if exists public.trend_candidate_reviews   cascade;
drop table if exists public.idea_candidate_reviews    cascade;
drop table if exists public.draft_suggestion_reviews  cascade;
drop table if exists public.ai_intel_assets           cascade;
drop table if exists public.notifications             cascade;
drop table if exists public.approvals                 cascade;
drop table if exists public.team_members              cascade;
-- profiles zuletzt: haengt an auth.users; cascade entfernt evtl. noch RLS-Policies auf BEHALTENEN
-- Tabellen, die profiles referenzieren -- fuer LUNA (service_role) egal.
drop table if exists public.profiles                  cascade;

commit;

-- Kontrolle danach: nur noch die BEHALTEN-Tabellen + Supabase-interne sollten uebrig sein.
