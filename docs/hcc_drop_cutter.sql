-- Alten Video-Cutter aus Supabase entfernen (nachdem der HCC-Cutter-CODE raus ist, Branch
-- chore/ausmisten-cutter-invest). In der PRODUCTION-DB im Supabase SQL-Editor ausfuehren.
-- EMPFEHLUNG: vorher Export/Backup der cutter_*-Tabellen (Table Editor -> Export, oder pg_dump).
-- CASCADE loest FK-Abhaengigkeiten zwischen den cutter_*-Tabellen.
--
-- NUR cutter_* wird entfernt. worker_*/agent_*/telegram_* BLEIBEN (die content_ops-Features des Teams
-- haengen aktuell noch daran -- Entfernung erst nach LUNA-Phase 5/6).

drop table if exists public.cutter_outputs cascade;
drop table if exists public.cutter_timings cascade;
drop table if exists public.cutter_perf_stats cascade;
drop table if exists public.cutter_segments cascade;
drop table if exists public.cutter_job_logs cascade;
drop table if exists public.cutter_revisions cascade;
drop table if exists public.cutter_jobs cascade;
drop table if exists public.cutter_workers cascade;
