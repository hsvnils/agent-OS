# K6 -- Stilllegung nilshubv2 + Worker (Bestandsaufnahme + Plan)

> Stand 2026-07-02. **Reine Bestandsaufnahme + Plan -- nichts ist geloescht/abgeschaltet.**
> Loeschen/Abschalten = **CEO-Tor**. Reihenfolge: erst Bestaetigen, dann Backup, dann schrittweise.

## 1. Live-Befund (Supabase, Zeilen + juengster Eintrag)

| Tabelle | Zeilen | zuletzt geschrieben | Einordnung |
|---|---|---|---|
| **trend_signals** | 7 | 2026-06-12 | KEEP -- LUNA content_ops (K1/K3) |
| **ideas** | 6 | 2026-06-12 | KEEP -- LUNA content_ops |
| **content_drafts** | 10 | 2026-06-12 | KEEP -- LUNA content_ops |
| **sources** | 6 | -- | KEEP -- LUNA content_ops |
| **ai_intel_items** | 24 | 2026-06-23 | KEEP -- LUNA AI-Inbox |
| **crm_companies/messages/todos** | 0/0/0 | -- | KEEP -- LUNA CRM (Write-Through) |
| **luna_os_users** | 1 | -- | KEEP -- LUNA Team-Auth (K4) |
| **luna_cutter_jobs** | 0 | -- | KEEP -- LUNA Cutter (K5) |
| worker_tasks | 5191 | **2026-06-27** | DROP -- alter Worker (tot) |
| agent_runs | 3803 | **2026-06-27** | DROP -- alter Worker |
| activity_events | 3983 | **2026-06-27** | DROP -- alter Worker |
| worker_instances / worker_state | 1 / 1 | -- | DROP -- alter Worker |
| agent_configs | 1 | -- | DROP -- alter Worker |
| cutter_jobs | 3 | 2026-06-23 | DROP -- alter HCC-Video-Cutter (Testdaten) |
| cutter_job_logs/outputs/perf_stats/revisions/segments/timings/workers | 12/2/6/0/18/3/1 | -- | DROP -- alter Cutter (+ rpc claim_next_cutter_job) |
| telegram_inputs | 47 | 2026-06-23 | DROP -- alter Telegram-Intake |
| telegram_bot_configs | 1 | -- | DROP -- alter Telegram-Intake |
| content_findings | 28 | -- | PRUEFEN -- HCC-Findings, von LUNA nicht genutzt |
| trend_candidate_reviews | 2 | -- | PRUEFEN -- HCC-Review-Meta |
| idea_candidate_reviews | 4 | -- | PRUEFEN -- HCC-Review-Meta |
| draft_suggestion_reviews | 10 | -- | PRUEFEN -- HCC-Review-Meta |
| ai_intel_assets | 1 | -- | PRUEFEN -- HCC-Review-Meta |
| profiles | 2 | -- | PRUEFEN -- HCC-Supabase-Auth-Profile (LUNA nutzt luna_os_users) |
| team_members | 2 | -- | PRUEFEN -- HCC-Team (superseded) |
| notifications | 88 | -- | PRUEFEN -- HCC-Notifs (LUNA nutzt lokale Outbox) |
| approvals | 0 | -- | DROP -- leer |

LUNA-OS liest/schreibt ausschliesslich die **KEEP**-Tabellen (aus `orchestrator/channels/web/app.py`:
trend_signals, ideas, content_drafts, sources, ai_intel_items, crm_*, luna_os_users, luna_cutter_jobs).

## 2. Dienste / Deployment

- **HCC-Web-App (nilshubv2, Next.js):** NAS-Ordner `/volume1/docker/nilshubv2` ist **leer** -> laeuft dort
  nicht. Kein `.vercel`/`vercel.json` im Repo. GitHub-Remote: `github.com/hsvnils/nilshubv2`.
  **OFFEN (CEO bestaetigen): Wo laeuft die HCC-App aktuell -- Vercel, lokal, gar nicht? Nutzt sie noch jemand?**
- **Synology-Worker:** `/volume1/docker/hanserautisch/worker` (Node/TS, `docker-compose.yml`) + viele
  `hanserautisch-worker-*.zip` (Funktions-Artefakte). Schreibt seit **2026-06-27 nichts mehr** -> praktisch
  offline. Vermutlich ueber Synology-Task-Scheduler (`/volume1/docker/synoscheduler`) getriggert.
- **LUNA (behalten):** `/volume1/docker/ki-unternehmen` -> Container `luna-telegram` + `luna-os`.

## 3. Reihenfolge-Blocker (aus Phase-3-Befund)

`worker_*`/`agent_*`/`telegram_*` (+ die HCC-Review-Tabellen) speisten die **Team-Review-Kandidaten** der alten
HCC-Web-App (`lib/workers`, Telegram-Intake). Sie duerfen erst weg, wenn:
1. **niemand mehr die HCC-Web-App nutzt** (Team ist auf LUNA-OS umgezogen -- K4 fertig, Nutzer anlegen), UND
2. die **LUNA-Fuetterung (K3) im Dauerbetrieb** laeuft (`CONTENT_FEED_ENABLED=1` in NAS-.env + `luna-telegram`
   neu starten) -- damit content_ops weiter Nachschub bekommt.

Da der Worker seit 06-27 tot ist und der HCC-App-Ordner leer ist, ist das Risiko gering -- aber vor dem
endgueltigen DROP bestaetigen.

## 4. Vorgeschlagene Reihenfolge (jede Stufe = eigener CEO-Freigabe-Schritt)

- **K6.0 Voraussetzung:** K3 scharf schalten (`CONTENT_FEED_ENABLED=1` + luna-telegram-Neustart); bestaetigen,
  dass das Team nur noch LUNA-OS nutzt.
- **K6.1 Backup:** vollstaendiges DB-Backup / CSV-Export der DROP-Tabellen (Supabase Dashboard -> Backups bzw.
  `pg_dump`). Erst danach loeschen.
- **K6.2 Worker abschalten:** Synology-Scheduler-Tasks deaktivieren + `hanserautisch/worker`-Container stoppen/
  entfernen. (Kein DB-Effekt -- nur der Schreiber verschwindet.)
- **K6.3 Cutter-Altlast droppen:** `cutter_*`-Tabellen + `rpc claim_next_cutter_job` (DROP-SQL-Muster
  `docs/hcc_drop_cutter.sql`). LUNA nutzt `luna_cutter_jobs`, nicht betroffen.
- **K6.4 Worker/Agenten/Telegram droppen:** `worker_*`, `agent_*`, `activity_events`, `telegram_*`,
  `approvals`.
- **K6.5 HCC-Review-Meta droppen (nach Sichtung):** `content_findings`, `*_reviews`, `ai_intel_assets`,
  ggf. `notifications`, `profiles`, `team_members` (Vorsicht: `profiles` haengt an `auth.users`).
- **K6.6 HCC-App stilllegen:** Deployment abschalten (Vercel/NAS), Repo `nilshubv2` archivieren (GitHub:
  „Archive"), NAS-Ordner `nilshubv2` (leer) + `hanserautisch` (Worker+Zips) sichern & entfernen.

## 5. Offene Fragen an den CEO (bevor irgendetwas passiert)

1. **Wo laeuft die HCC-Web-App aktuell und nutzt sie noch jemand?** (bestimmt, ob K6.6 sofort geht)
2. **K3 jetzt scharf schalten** (`CONTENT_FEED_ENABLED=1`)? -- Voraussetzung fuer K6.4.
3. **HCC-Review-Meta + notifications/profiles/team_members**: wirklich weg, oder als Historie behalten?
4. Backup-Weg: Supabase-Dashboard-Backup reicht, oder zusaetzlich CSV-Export der DROP-Tabellen?
