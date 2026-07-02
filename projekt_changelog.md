# Projekt-Changelog

> **Changelog-Pflicht:** Keine Aufgabe gilt als abgeschlossen, bevor ein Eintrag hier geschrieben wurde.
> Jede Erstellung, Aenderung oder Loeschung von Dateien sowie jede Struktur- oder Mandatsaenderung MUSS hier
> protokolliert werden — von jedem Tool und jedem Agenten. Neueste Eintraege stehen **oben**.

Eintragsformat:

```
## [JJJJ-MM-TT HH:MM] — <Akteur, z. B. Claude Code / Codex / Head of Agents>
- **Was:** <kurz, was geändert wurde>
- **Warum:** <Grund/Anweisung>
- **Betroffen:** <Dateien/Agenten>
```

---

## Eintraege

## [2026-07-02 20:10] — Claude Code — K5-Fix: eigene Tabelle luna_cutter_jobs (Kollision mit HCC-cutter_jobs)
- **Was:** Beim Live-Test schlug der Insert fehl (HTTP 400, `column cutter_jobs.fehler does not exist`): die
  Tabelle `cutter_jobs` existiert bereits aus dem alten HCC-Video-Cutter (Migration 028, voellig anderes Schema
  title/source_folder/error + Status-CHECK ohne `running`). Mein `create table if not exists` hatte daher nichts
  angelegt. Fix: LUNA nutzt jetzt eine **eigene Tabelle `luna_cutter_jobs`** (app.py cutter_store + Migration
  `docs/hcc_k5_cutter_jobs.sql` umbenannt). Kollidiert nicht mehr mit dem alten HCC-Cutter (faellt in K6 weg).
- **Warum:** Namenskollision mit Bestands-Schema; Live-Rundlauf-Test.
- **Betroffen:** `orchestrator/channels/web/app.py`, `docs/hcc_k5_cutter_jobs.sql`. Import ok. OFFEN (CEO):
  korrigierte SQL (luna_cutter_jobs) in Supabase ausfuehren; luna-os laeuft bereits mit K5-Code.

## [2026-07-02 19:45] — Claude Code — K5: Cutter-App in LUNA-OS (Job-Status/Historie + anstossen)
- **Was:** Cutter (Phase 15, laeuft lokal auf dem Mac) an LUNA-OS (NAS) angebunden. Bruecke = **ueber die
  LUNA-OS-API** (CEO-Wahl; kein Supabase-service_role auf dem Mac). Tabelle `cutter_jobs` (generischer
  ContentStore, `CUTTER_FELDER`/`CUTTER_STATUSES` in content_store.py). LUNA-OS-Endpunkte (Modul content_ops):
  `GET /api/cutter`, `POST /api/cutter/job` (queued), `GET /api/cutter/queue` (Mac-Poll), `POST
  /api/cutter/report` (Mac meldet running/done/failed; job_id -> Update sonst neue Zeile). Frontend: App
  „Cutter" (🎬) + Sidebar-Eintrag -- Job-Historie mit Status-Badges + „Reel-Job anstossen"-Formular. Mac-Seite:
  `cutter/luna_bridge.py` (LunaBridge, Basic-Auth via LUNA_OS_URL/USER/PASSWORD in Mac-.env; inaktiv ohne
  Config) + `cutter/watch.py` meldet Status + holt queued Jobs. Gating `/api/cutter` -> content_ops, App-
  Zuordnung `cutter`->content_ops. Migration `docs/hcc_k5_cutter_jobs.sql`. Cache-Bust v28.
- **Warum:** „Weiter mit K5" (CEO) -- Cutter-Steuerung/Historie zentral in LUNA-OS.
- **Betroffen:** `orchestrator/core/content_store.py`, `orchestrator/channels/web/app.py`,
  `orchestrator/core/team_auth.py`, `orchestrator/channels/web/static/{app.js,index.html}`,
  `orchestrator/tests/test_team_auth.py`, `cutter/luna_bridge.py` (neu), `cutter/watch.py`,
  `cutter/tests/test_luna_bridge.py` (neu), `docs/hcc_k5_cutter_jobs.sql` (neu), `HCC_INTEGRATION_ROADMAP.md`.
  Suite 317 (orchestrator) + 11 (cutter) gruen; im Preview verifiziert. OFFEN (CEO): SQL ausfuehren,
  LUNA_OS_URL/USER/PASSWORD in Mac-.env, Cutter-Watcher + luna-os neu starten. Posten bleibt CEO-Tor.

## [2026-07-02 19:00] — Claude Code — Fix: Sidebar-Menue scrollt jetzt + Nutzer-Chip-Layout
- **Was:** Das Sidebar-Menue liess sich nicht scrollen (mit „Team" 18 Eintraege -> unten abgeschnitten auf
  kleinen Hoehen). Ursache: `#nav` hatte `flex:1` ohne `min-height:0`/eigenes `overflow` -> in einem
  Flex-Column-Container wird die Liste abgeschnitten statt scrollbar. Fix: `#nav { flex:1 1 auto; min-height:0;
  overflow-y:auto }` + schlanker Scrollbar; `brand-block`/`side-voice` `flex:0 0 auto` (schrumpfen nicht, Nav
  bekommt den Scrollraum). Zusatz: `brand-block` `flex-wrap:wrap`, damit der K4-Nutzer-Chip auf einer eigenen
  vollen Zeile sitzt statt in der Brand-Zeile gequetscht. Cache-Bust v27.
- **Warum:** CEO-Hinweis -- Menue nicht scrollbar.
- **Betroffen:** `orchestrator/channels/web/static/{style.css,index.html}`. Im Preview verifiziert (Handy 812px:
  Nav scrollt bis „Team"/„LUNA-Chat", Voice-Leiste bleibt unten; keine Console-Fehler). Reines Frontend
  (volume-gemountet) -> nach Sync sofort live per Hard-Reload, kein Container-Neustart noetig.

## [2026-07-02 18:40] — Claude Code — K4: Team-Verwaltungs-App in LUNA-OS (statt CLI)
- **Was:** Rollenvergabe wie im HCC jetzt als **LUNA-OS-App „Team"** (kein CLI-Zwang mehr). Backend
  (`web/app.py`): `GET /api/team` (Nutzerliste + Module + Rollen), `POST /api/team` (anlegen/aktualisieren,
  Passwort wird server-seitig gehasht), `POST /api/team/{username}/aktiv` (aktiv/inaktiv) -- alle ueber Modul
  `administration` gegated (owner/admin). `team_auth.py`: `/api/team` -> administration in `modul_fuer_pfad`,
  App `team` in `APP_MODUL`. Frontend (`app.js`): App + Sidebar-Eintrag „Team" (👥), Formular (Benutzername/
  Anzeigename/Passwort/Rolle + Modul-Checkboxen) + Nutzerliste mit Aktiv/Inaktiv-Toggle; CSS + Cache-Bust v26.
- **Warum:** CEO -- CLI-Nutzeranlage zu umstaendlich; Rollenvergabe soll wie im HCC in der Oberflaeche gehen.
- **Betroffen:** `orchestrator/channels/web/app.py`, `orchestrator/core/team_auth.py`,
  `orchestrator/channels/web/static/{app.js,style.css,index.html}`, `orchestrator/tests/test_team_auth.py`.
  Suite 316 gruen; im Preview verifiziert (Formular + 3 Nutzerkarten + Toggle, keine Console-Fehler). Die CLI
  bleibt als Alternative bestehen.

## [2026-07-02 18:05] — Claude Code — K4: Team-Auth + Rollen in LUNA-OS (Mehr-Nutzer-Login)
- **Was:** LUNA-OS von Single-CEO-Basic-Auth auf **Mehr-Nutzer + Rollen/Module** umgestellt. Neu
  `orchestrator/core/team_auth.py`: TeamAuth gegen Supabase-Tabelle `luna_os_users` (Login/Anlegen/Liste/
  Deaktivieren), Passwort-Hashing PBKDF2-HMAC-SHA256 (stdlib, nie Klartext), Module content_ops/crm/invest/
  administration, Rolle `owner`=Superuser sonst `allowed_modules`, `modul_fuer_pfad`-Gating, `erlaubte_apps`
  (SSOT Frontend), CLI `python -m orchestrator.core.team_auth add|list|deactivate`. `web/app.py`: `auth`
  loest env-CEO (owner) ODER Team-Nutzer auf, setzt `request.state.user`, gated sensible Endpunkte mit 403;
  neuer `/api/me`. Frontend `static/app.js`: `ladeMe()` -> blendet nicht-erlaubte Apps in Sidebar/Dock aus
  (`darf()`), Nutzer-Chip (Name+Rolle) + CSS; Cache-Bust v25. Migration `docs/hcc_k4_luna_os_users.sql`.
- **Warum:** „Weiter mit K4" (CEO) -- Team-Zugang mit Rollen vor dem Team-Go-Live.
- **Betroffen:** `orchestrator/core/team_auth.py` (neu), `orchestrator/channels/web/app.py`,
  `orchestrator/channels/web/static/{app.js,style.css,index.html}`, `orchestrator/tests/test_team_auth.py`
  (neu), `docs/hcc_k4_luna_os_users.sql` (neu), `HCC_INTEGRATION_ROADMAP.md`. Suite 314 gruen; im Preview
  verifiziert (Owner=17 Apps, Content-Rolle=6 Apps, keine Console-Fehler). Graceful: ohne Tabelle bleibt
  env-CEO-Basic-Auth unveraendert. OFFEN (CEO): SQL-Migration ausfuehren + Team-Nutzer per CLI anlegen.

## [2026-07-02 17:20] — Claude Code — K3 CODE-KOMPLETT: Content-Pipeline Trends->Ideen->Drafts
- **Was:** K3 fertiggebaut. `ContentFeed` um zwei LLM-Stufen erweitert: `ideen_lauf()` (aus offenen Trends
  `new` -> Content-Ideen via Fachagent `cco` -> `ideas` Status `inbox`; Trend rueckt auf `reviewing`) und
  `drafts_lauf()` (aus offenen Ideen `inbox` -> Reel-Entwuerfe Hook/Caption/Hashtags -> `content_drafts`
  Status `idea`; Idee rueckt auf `sorted`) + `pipeline_lauf()` (volle Kette). Status-Progression = idempotenter
  Dedup (nichts laeuft doppelt). Schema live abgeglichen (nilshubv2 001_initial_schema.sql): `hashtags`/`tags`
  = `text[]` -> als Liste geschrieben; keine CHECK-Constraints auf status/platform. LUNA-Tool `content_feed_lauf`
  auf `stufe`=trends|ideen|drafts|alles erweitert; Tages-Loop `_start_content_feed_loop` faehrt jetzt die volle
  `pipeline_lauf` (07:00 DE, `CONTENT_FEED_ENABLED=1`). Neuer Helper `_content_feed()` baut den Feed mit allen
  Stores + LLM-Core. Autonomie L1/L2 (nur Kandidaten fuers Team-Review; kein Auto-Publish = CEO-Tor).
- **Warum:** „K3 zu Ende machen" (CEO); ersetzt getTelegramIdeaCandidates/getDraftAssistantSuggestions des alten
  Dummy-Workers durch LUNA-Agenten.
- **Betroffen:** `orchestrator/core/content_feed.py`, `orchestrator/core/hoa_tools.py`,
  `orchestrator/channels/telegram/bot.py`, `orchestrator/tests/test_content_feed.py`,
  `HCC_INTEGRATION_ROADMAP.md`. Suite 294 gruen. OFFEN: deployen + live gegen Supabase verifizieren.

## [2026-07-02 16:10] — Claude Code — K3-Pilot: Content-Feed-Loop (LUNA fuettert content_ops)
- **Was:** Erster Baustein von K3 (LUNA-Agenten fuettern content_ops). (1) `ContentStore.add()` +
  `_cache_prepend()` ergaenzt (Insert neuer Zeilen via Supabase-upsert; created_at/updated_at auto, id bleibt
  offen -> Supabase-Default; None-Felder fallen raus). (2) Neuer `orchestrator/core/content_feed.py` mit
  `ContentFeed.trend_lauf()` -- Content-Researcher erzeugt ueber Brave-Web-Recherche (kostenlos, KEIN
  Hintergrund-LLM) Trend-Kandidaten und schreibt sie mit Status `new` nach `trend_signals`; Dedup gegen
  bestehende `source_url`, Limits (max je Thema + max gesamt), Notbremse (`WatchStore.paused`), Research-Ticket
  + CEO-Meldung. Default-Themen = kuratierte Content-Themen (`watch_config`, Abteilung 'cco'). Als Loop nach
  `governance/autonomie-stufen.md` §5b entworfen, **Autonomie L1** (nur sammeln + melden; kein Auto-Publish,
  Oeffentlichkeit = CEO-Tor). (3) LUNA-Tool `content_feed_lauf` (manueller Ausloeser) + gated
  Hintergrund-Loop `_start_content_feed_loop` (taeglich 07:00 DE, nur mit `CONTENT_FEED_ENABLED=1`).
- **Warum:** K3 laut Uebergabe 2026-07-02 = naechster Schritt; ersetzt den alten Dummy-Worker schrittweise.
- **Betroffen:** `orchestrator/core/content_store.py`, `orchestrator/core/content_feed.py` (neu),
  `orchestrator/core/hoa_tools.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_content_store.py`, `orchestrator/tests/test_content_feed.py` (neu). Suite 287 gruen.

## [2026-07-02 14:30] — Claude Code — Loop Engineering in der Roadmap verankert (recherchiert)
- **Was:** Loop-Engineering war schon in `governance/autonomie-stufen.md` (L1→L2→L3, Maker/Checker) +
  `INVESTMENT_ROADMAP.md` §10, aber nicht als uebergreifendes Prinzip in der Haupt-`ROADMAP.md`. Ergaenzt:
  (1) autonomie-stufen.md **§5b „Loop-Anatomie"** (Ziel/Trigger/Lauf/Verifikation/Stop; aktuelle Fassung
  Osmani u. a. 2026 -- „den Loop entwerfen, der den Agenten ansteuert", statt Einzel-Prompt); (2) ROADMAP.md
  Design-Prinzip fuer ALLE autonomen Schleifen (Verweis auf autonomie-stufen.md); (3) HCC_INTEGRATION_ROADMAP
  **K3 als konkreter Loop** (Ziel/Trigger/Lauf/Verifikation/Stop, L1/L2, Team-Review, kein Auto-Publish).
- **Warum:** CEO-Frage; Loop-Engineering als Leitbild fuer die content_ops-Fuetterung (K3) und alle Loops.
- **Betroffen:** governance/autonomie-stufen.md, ROADMAP.md, HCC_INTEGRATION_ROADMAP.md

## [2026-07-02 14:05] — Claude Code — Konsolidierung K2: Sources + AI-Inbox (content_ops-Flaeche komplett)
- **Was:** ContentStore verallgemeinert -- `status_feld` (beliebiges Statusfeld, z. B. `recommendation`) +
  generisches `patch(rid, felder)`. **Sources-App** (`/api/sources` + `is_active`-Toggle via patch; name/
  source_type/url/priority; kein Status) + **AI-Inbox-App** (`/api/ai-inbox` + recommendation use/investigate/
  later/ignore via status_setzen mit status_feld=recommendation; Titel/Autor/Summary/Scores). LUNA-OS-Apps
  „Quellen" + „AI-Inbox", Cache-Bust **v24**. 2 neue Tests; Gesamtsuite **274**; Preview ok. **Damit ist die
  content_ops-Team-Flaeche in LUNA-OS komplett** (Trends/Ideen/Drafts/Quellen/AI-Inbox, lesen+schreiben Supabase).
- **Warum:** HCC->LUNA-OS Konsolidierung K1/K2 abgeschlossen. Naechster grosser Hebel: K3 (LUNA-Agenten fuettern).
- **Betroffen:** orchestrator/core/content_store.py, orchestrator/tests/test_content_store.py,
  orchestrator/channels/web/app.py, orchestrator/channels/web/static/app.js + index.html

## [2026-07-02 13:40] — Claude Code — Konsolidierung K2: Drafts (Kern-Pipeline Trends->Ideen->Drafts komplett)
- **Was:** Drafts als dritter content_ops-Typ ueber den generischen `ContentStore` (`content_drafts`,
  DRAFT_FELDER/DRAFT_STATUSES idea/in_progress/review/approved/scheduled/published/archived). `/api/drafts` +
  status-Endpunkt; LUNA-OS-App **„Drafts"** (Hook/Caption/Hashtags + Status-Buttons). Cache-Bust **v23**;
  Suite **272**; Preview ok. Damit ist die Kern-Content-Pipeline **Trends -> Ideen -> Drafts** in LUNA-OS
  komplett (lesen+schreiben gegen Supabase).
- **Warum:** HCC->LUNA-OS Konsolidierung K1/K2. Offen: Sources (name/is_active, kein Status) + AI-Inbox
  (recommendation/scores) -- andere Form, folgen separat.
- **Betroffen:** orchestrator/core/content_store.py, orchestrator/channels/web/app.py,
  orchestrator/channels/web/static/app.js + index.html

## [2026-07-02 13:20] — Claude Code — Konsolidierung K2: Ideen-Labor + generischer ContentStore
- **Was:** `orchestrator/core/content_store.py` -- **generischer `ContentStore`** (Supabase=DB via select +
  PATCH-Status, lokaler Cache-Fallback; parametriert je Tabelle: FELDER/STATUSES). Ersetzt die bespoke
  `trends.py` (geloescht). Trends laufen jetzt ueber ContentStore; **neu: Ideen-Labor** (`/api/ideas` +
  status-Endpunkt, LUNA-OS-App „Ideen-Labor" mit Status Eingang/Einsortiert/Geplant/In Arbeit/Erledigt/
  Archiviert). Cache-Bust **v22**. Tests test_content_store (6, parametriert); Gesamtsuite **272**. Preview ok.
- **Warum:** HCC->LUNA-OS Konsolidierung K1/K2 -- zweiter content_ops-Typ; DRY-Store fuer alle weiteren
  (Drafts/Quellen/AI-Inbox folgen per Instanz).
- **Betroffen:** orchestrator/core/content_store.py (+ trends.py/test_trends.py geloescht),
  orchestrator/tests/test_content_store.py, orchestrator/channels/web/app.py,
  orchestrator/channels/web/static/app.js + index.html, .gitignore

## [2026-07-02 12:55] — Claude Code — Fix: Trend-Status-Write via PATCH (statt Upsert)
- **Was:** `SupabaseClient.update()` (PATCH, Teil-Update) ergaenzt; `TrendStore.status_setzen` nutzt jetzt PATCH
  `id=eq.<id>` statt Upsert. Grund: Upsert scheiterte mit HTTP 400, weil `trend_signals.title` NOT NULL ist und
  beim Status-Write nur `status` gesendet wird (Upsert impliziert INSERT). PATCH aktualisiert nur die Zeile.
  MockSupabaseClient.update + Tests; Gesamtsuite **271**.
- **Warum:** Live-Test des Trend-Status-Writes gab 400; Read-Pfad war schon live ok (7 Trends aus Supabase).
- **Betroffen:** orchestrator/governance/supabase.py, orchestrator/core/trends.py,
  orchestrator/tests/test_supabase.py, orchestrator/tests/test_trends.py

## [2026-07-02 12:40] — Claude Code — Konsolidierung K1+K2: Trends-Pilot in LUNA-OS
- **Was:** `orchestrator/core/trends.py` (`TrendStore` -- Supabase als DB via `SupabaseClient`, lokaler
  JSONL-Cache-Fallback, `list()`/`status_setzen()`, Status new/reviewing/draft_created/approved/published/
  ignored). Endpunkte `GET /api/trends` + `POST /api/trends/{id}/status`. LUNA-OS-App **„Trends"** (Trend-Inbox
  mit Relevanz/Score/Quelle + Status-Buttons), APPS+NAV, Cache-Bust **v21**. 5 Tests; Gesamtsuite **270**.
  Preview: UI rendert, kein JS-Fehler.
- **Warum:** HCC->LUNA-OS Konsolidierung, K1 (content_ops-Datenschicht) + K2 (content_ops-App), Trends als
  erster Content-Typ (Blaupause fuer Ideen/Drafts/Quellen).
- **Betroffen:** orchestrator/core/trends.py, orchestrator/tests/test_trends.py,
  orchestrator/channels/web/app.py, orchestrator/channels/web/static/app.js,
  orchestrator/channels/web/static/index.html, .gitignore

## [2026-07-02 12:10] — Claude Code — Richtungswechsel: Konsolidierung HCC -> LUNA-OS (Roadmap neu)
- **Was:** CEO-Entscheidung: **EIN System = LUNA-OS** (Gehirn + Team-Web-Gesicht); altes nilshubv2/Next.js +
  Worker **stilllegen**; behaltene Teile (content_ops, CRM, Team) in LUNA-OS **nachbauen**; **Supabase = primaere
  DB + NAS-Fallback** (kein Zwei-App-Sync mehr). `HCC_INTEGRATION_ROADMAP.md` komplett neu (Phasen K0-K6:
  Datenschicht -> content_ops-Apps -> LUNA-Agenten-Fuetterung -> Team-Auth/Rollen -> Cutter-App -> nilshubv2
  stilllegen). ROADMAP.md Phase 18 aktualisiert.
- **Warum:** CEO will eine Codebasis/Deploy, LUNA als Gehirn+Gesicht, Team mit Rollen. Folge: CRM-Store/
  Projektion/SupabaseClient/Collab-CRM-App passen direkt; Read-back crm_sync wird ueberfluessig (spaeter raus).
- **Betroffen:** HCC_INTEGRATION_ROADMAP.md, ROADMAP.md

## [2026-07-02 11:40] — Claude Code — HCC Phase 3 (Teilstart): Video-Cutter + Invest ausgemistet
- **Was:** Im HCC-Repo (`~/Documents/nilshubv2`, Branch `chore/ausmisten-cutter-invest`, NICHT gemergt/deployt)
  die **isolierten** Bereiche entfernt: **Video-Cutter** (app/video-cutter+api, lib/cutter, components/video-
  cutter) + **Invest** (app/invest); Nav/middleware/Modul-Route bereinigt (invest-Modultyp bleibt vorerst wg.
  agents-office). **Build gruen.** DROP-SQL fuer `cutter_*` in `docs/hcc_drop_cutter.sql` (CEO fuehrt in
  Produktion aus). **Befund:** agents/workers/telegram sind NICHT sauber entfernbar -- content_ops haengt an
  `lib/workers`/`agents`/`telegram` (Kandidaten-Fuetterung: getTrendDetectorCandidates/getTelegramIdeaCandidates
  /getDraftAssistantSuggestions) -> verschoben nach LUNA-Phase 5/6 (LUNA-Agenten uebernehmen die Fuetterung).
- **Warum:** HCC-Ausmisten (#2), sicherer Teil; alter Cutter weg als Vorbereitung fuer #3 (LUNA-Cutter spiegeln).
- **Betroffen:** (Repo nilshubv2, Branch) + docs/hcc_drop_cutter.sql

## [2026-07-02 11:05] — Claude Code — HCC Phase 2: CRM Rueckschreiben (bidirektional 1:1)
- **Was:** `orchestrator/core/crm_sync.py` (`CrmSync.pull()` -- holt Supabase-Zeilen mit `updated_by='hcc'`
  cursor-basiert und wendet sie lokal an). `CrmStore.uebernehmen_status_extern/uebernehmen_todo_extern`
  (appenden OHNE Rueck-Projektion = Loop-Schutz; Vorrang luna-os). In den Telegram-Bot-Poll eingehaengt (laeuft
  sofort beim Start + alle ~15 min). MockSupabaseClient um `select` erweitert. 5 neue Tests (Statuswechsel,
  Todo-erledigt, idempotent, kein Rueck-Loop, Fall-B); Gesamtsuite **265**. `crm/sync_cursor.txt` gitignored.
- **Warum:** HCC<->LUNA Phase 2, bidirektionale 1:1-Synchronisierung (mit Write-Through zusammen komplett).
- **Betroffen:** orchestrator/core/crm_sync.py, orchestrator/core/crm.py, orchestrator/governance/supabase.py,
  orchestrator/channels/telegram/bot.py, orchestrator/tests/test_crm_sync.py, .gitignore

## [2026-07-02 10:40] — Claude Code — HCC Phase 2: CRM Write-Through nach Supabase
- **Was:** `orchestrator/core/crm_projection.py` (`SupabaseCrmProjection`, duck-typed .firma/.nachricht/.todo
  -> Upsert in crm_companies/crm_messages/crm_todos). `CrmStore` um optionalen `projektor` erweitert: nach
  jedem Ereignis Write-Through (Firma zuerst wg. FK, dann Nachricht/To-do), best-effort -> lokaler Store bleibt
  Quelle + Offline-Fallback; alle LUNA-Zeilen `updated_by='luna'`. In `web/app.py` + `telegram/bot.py`
  verdrahtet (aktiviert automatisch, sobald SUPABASE_URL+SERVICE_ROLE_KEY da sind, sonst rein lokal). CRM-
  Tabellen in Supabase angelegt (CEO). 2 neue Tests; Gesamtsuite **260**.
- **Warum:** HCC<->LUNA Phase 2 (CRM-Pilot, relationale Projektion, Option A).
- **Betroffen:** orchestrator/core/crm_projection.py, orchestrator/core/crm.py,
  orchestrator/channels/web/app.py, orchestrator/channels/telegram/bot.py, orchestrator/tests/test_crm.py

## [2026-07-02 10:15] — Claude Code — HCC Phase 1: Supabase-Client (Datenbruecke)
- **Was:** `orchestrator/governance/supabase.py` -- Capability-Muster fuer die geteilte Datenbasis:
  `SupabaseAuth.from_env` (SUPABASE_URL/SERVICE_ROLE_KEY) + `SupabaseClient` (PostgREST upsert/select/delete
  via urllib, service_role, Fall-B ohne Keys, HTTP injizierbar) + `MockSupabaseClient`. 6 Tests; Suite 258.
  Live-Verbindungstest von der NAS bestanden (profiles 200 / trend_signals 206). Nur geteilte Team-Flaechen;
  luna-os-Interna bleiben lokal. `docs/crm_supabase_schema.sql` (relationale Projektion) fuer den CRM-Pilot.
- **Warum:** HCC<->LUNA Integration, Phase 1 (Architektur A: Shared Supabase + NAS-Fallback).
- **Betroffen:** orchestrator/governance/supabase.py, orchestrator/tests/test_supabase.py, docs/crm_supabase_schema.sql

## [2026-07-02 09:45] — Claude Code — HCC-Roadmap: CEO-Entscheidungen eingearbeitet
- **Was:** `HCC_INTEGRATION_ROADMAP.md` aktualisiert: Architektur = **A (Shared Supabase) + NAS-Offline-
  Fallback (Write-Through)**; **Telegram fliegt** aus HCC (Idee „Team-Reminder" ins Backlog); **alter Video-
  Cutter wird geloescht** (Phase 3, inkl. Worker/Routen/`cutter_*`+`worker_*`-Schema), LUNA-Cutter gespiegelt
  ueber neue schlanke Tabellen (Phase 4); Datenschutz-Freigabe (Supabase-Cloud) vermerkt. Entscheidungen +
  Backlog-Abschnitt ergaenzt.
- **Warum:** CEO-Feedback zur Roadmap.
- **Betroffen:** HCC_INTEGRATION_ROADMAP.md

## [2026-07-02 09:30] — Claude Code — HCC<->LUNA Integration: Bestand + Roadmap
- **Was:** Bestehendes Dashboard `~/Documents/nilshubv2` (Hanserautisch Command Center, Next.js+Supabase)
  erkundet und dokumentiert: `docs/HCC_BESTAND.md` (Module/Routen/Supabase-Schema/Worker/Ueberschneidung mit
  LUNA). Neue `HCC_INTEGRATION_ROADMAP.md` (Vision: HCC = Team-Web-Gesicht, luna-os = Gehirn+Datenhoheit+
  Vorrang, gemeinsame bidirektionale Datenbasis; 8 Phasen 0-7 mit GATES; Architektur-Kern A/B). ROADMAP.md
  um **Phase 18 (HCC als Team-Web-Gesicht)** ergaenzt.
- **Warum:** CEO-Vision -- HCC fuers Social-Media-Team; Cutter aus luna-os spiegeln, Researcher als Ausbaustufe
  in luna-os, Agenten laufen im Hintergrund fuers HCC (wie CRM). Nur Planung, kein Code.
- **Betroffen:** docs/HCC_BESTAND.md, HCC_INTEGRATION_ROADMAP.md, ROADMAP.md

## [2026-07-02 00:50] — Claude Code — Doku: Instagram App-Review-Einreichungspaket
- **Was:** `docs/APP_REVIEW_INSTAGRAM.md` -- fertige Texte (Use-Case, Detail, Pruefer-Anleitung, Screencast-
  Drehbuch via Tester-Account, App-Settings-Checkliste) fuer die Meta App-Review von
  `instagram_business_manage_messages`. Referenz zum Fortsetzen.
- **Warum:** Business-Verifizierung laeuft (~2 Werktage); App-Review folgt danach. CEO: morgen weiter.
- **Betroffen:** docs/APP_REVIEW_INSTAGRAM.md

## [2026-07-02 00:35] — Claude Code — Instagram-Webhook: robuster Payload-Parser (beide Formate)
- **Was:** `nachrichten_aus_webhook()` parst jetzt auch `entry[].changes[].value` + Metas flache Feldprobe
  `{"field":"messages","value":{...}}`, nicht nur `entry[].messaging[]`. **Live verifiziert:** Metas
  „messages"-Feldprobe kommt an (`sig_valid=True`), wird geparst, im `CrmStore` gespeichert + klassifiziert.
  Temporaeres Diagnose-Logging wieder entfernt. 2 neue Tests; Suite gruen.
- **Warum:** Meta signiert+liefert Webhooks korrekt (Instagram-App-Secret stimmt, Basic-Auth-Fix wirkt). Echte
  Fremd-DMs bleiben **Meta-seitig** blockiert bis App-Review/Veroeffentlichung -- der Dev-Modus liefert nur
  Test-Events + DMs zwischen App-Rollen-Accounts (dokumentierter Meta-Gate, kein Code-Problem).
- **Betroffen:** orchestrator/governance/instagram.py, orchestrator/channels/web/app.py,
  orchestrator/tests/test_instagram.py

## [2026-07-02 00:07] — Claude Code — Fix: Instagram-Webhook von LUNA-OS-Basic-Auth ausnehmen
- **Was:** `app.py` `auth`-Dependency nimmt `/api/webhook/*` von der HTTP-Basic-Auth aus (Request-Pfad-Check).
  Der Webhook sichert sich selbst -- GET ueber den Verify-Token, POST ueber die HMAC-Signatur. Lokal
  verifiziert: `/api/state`=401 (weiter geschuetzt), `/api/webhook/instagram`=403 statt 401 (Handler erreicht).
- **Warum:** Meta-Verify-Handshake scheiterte mit `401 {"detail":"Login noetig"}` -- die globale Basic-Auth
  (`FastAPI(dependencies=[Depends(auth)])`) blockierte Metas Webhook-Aufruf, der sich nicht einloggen kann.
- **Betroffen:** orchestrator/channels/web/app.py

## [2026-07-02 00:50] — Claude Code — ROADMAP: Collab-CRM als erster Baustein des Partner-/Akten-Systems
- **Was:** In `ROADMAP.md` beim Backlog-Punkt „Partner-/Akten-System (CRM-artig)" vermerkt, dass der erste
  Baustein (Collab-CRM unter dem CRO, kanalagnostischer Store + Instagram-Webhook + LUNA-OS-App) umgesetzt ist
  (Branch feat/insider-crm, noch nicht deployt). Roadmap bleibt lebende SSOT.
- **Warum:** CEO-Anweisung „Roadmap immer aktuell"; Teil A des Bauplans ist code-komplett.
- **Betroffen:** ROADMAP.md

## [2026-07-02 00:45] — Claude Code — A-Phase 2+3 Collab-CRM Logik + Anzeige (Teil A code-komplett)
- **Was:** A2 -- regelbasierte Klassifikation (`klassifiziere()`, Koop-Keywords, token-frugal, kein LLM) +
  `CrmStore.verarbeite_eingang()` (eingehende DM -> Kategorie + Auto-To-do bei NEUER Kooperationsanfrage);
  Instagram-Webhook meldet Kooperationsanfragen ueber **Notifier** + legt **Second-Brain**-Notiz an
  (`brain_merken`, quelle=crm). Neue HoA-Tools `crm_zeigen`/`crm_konversation`/`crm_todo_erledigen`/
  `crm_status_setzen`; `CrmStore` in `ToolContext` + `bot.py` verdrahtet. A3 -- LUNA-OS-App **„Collab-CRM"**
  (`/api/crm` + `/api/crm/konversation` + `/api/crm/todo/{id}/erledigen`; `app.js` APPS+NAV+`ladeCRM` +
  Konversations-Fenster). Cache-Bust **v20**. 3 neue Tests; Gesamtsuite **250**. Preview verifiziert
  (DM -> Klassifikation -> Store -> API -> UI -> Konversation).
- **Warum:** Bauplan Teil A / A-Phasen 2+3. Kein Auto-Senden (Oeffentlichkeit = CEO-Tor). Damit ist **Teil A
  code-komplett** (Live-Empfang wartet nur auf GATE B: Meta-App + INSTAGRAM_* in .env).
- **Betroffen:** orchestrator/core/crm.py, orchestrator/core/hoa_tools.py, orchestrator/channels/web/app.py,
  orchestrator/channels/web/static/app.js, orchestrator/channels/web/static/index.html,
  orchestrator/channels/telegram/bot.py, orchestrator/tests/test_crm.py

## [2026-07-02 00:20] — Claude Code — A-Phase 1 Instagram-Anbindung (Code; GATE B offen)
- **Was:** Capability-Modul `orchestrator/governance/instagram.py` (`InstagramAuth.from_env` +
  `InstagramMessaging`: Verify-Challenge, **HMAC-SHA256-Signaturpruefung**, Webhook-Parsing nur eingehender
  Text; `MockInstagramMessaging`). Webhook-Routen **GET/POST `/api/webhook/instagram`** in `app.py`
  (Signatur pflicht, eingehende DMs -> `CrmStore`, quelle=instagram, Dedup via Message-ID). `CrmStore` in
  `app.py` verdrahtet. 7 Tests (gruen; Gesamtsuite **247**).
- **Warum:** Bauplan Teil A / A-Phase 1. **Kein Vercel** (Webhook laeuft ueber die bestehende HTTPS-URL). Live-
  Aktivierung = **GATE B** (CEO richtet Meta-App ein, `INSTAGRAM_*` in `.env`, CEO-Tor + CISO) -- Code ist
  bereit + mock-getestet.
- **Betroffen:** orchestrator/governance/instagram.py, orchestrator/channels/web/app.py,
  orchestrator/tests/test_instagram.py

## [2026-07-02 00:05] — Claude Code (als Head of Agents, CEO-Freigabe) — A-Phase 0 Collab-CRM
- **Was:** CRO-Charta (`agents/04_cro.md`) um **Collab-CRM** ergaenzt (6 Punkte: Auftrag, „Ausdruecklich NICHT"
  kein Auto-Senden, Tools, Aufgabenkatalog, Workflow, Unter-Agent). Neuer **kanalagnostischer** `CrmStore`
  (`orchestrator/core/crm.py`, event-sourced JSONL `crm/log.jsonl`, Quelle instagram|telegram|gmail|manuell,
  Pipeline neu->in_gespraech->angebot->vereinbart|abgelehnt, To-dos, Dedup via extern_id). 6 Tests (gruen;
  Gesamtsuite **240**). `CRM_PLAN.md`; `crm/log.jsonl` gitignored.
- **Warum:** Bauplan Teil A; CEO-Entscheidung File-Store statt Supabase + kanalagnostisch. Charta-Diff vorab
  freigegeben (AGENTS.md 3.3).
- **Betroffen:** agents/04_cro.md, orchestrator/core/crm.py, orchestrator/tests/test_crm.py, CRM_PLAN.md, .gitignore

## [2026-07-01 23:50] — Claude Code — B-Phase 3 Insider-Anzeige (LUNA-OS) + Teil B fertig
- **Was:** `/api/investment` liefert jetzt `insider`-Signale; neuer POST `/api/investment/insider-scan`.
  Investment-App (`static/app.js`) um Button **„Insider-Scan"** + Sektion **„Insider-Signale (SEC Form 4)"**
  (Symbol/Cluster/Betrag/Rolle/Konfidenz/Filing-Link) erweitert; Cache-Bust **v19**. Roadmap Phase 2.5 auf
  ✅ umgesetzt. Preview verifiziert (Panel rendert, Button + Sektion da, kein JS-Fehler).
- **Warum:** Bauplan Teil B / Roadmap Phase 2.5 -- Anzeige; damit ist **Teil B (Insider-Screening) komplett**
  (B-Phasen 0-3, advisory, dateibasiert, kein neuer bezahlter Dienst).
- **Betroffen:** orchestrator/channels/web/app.py, orchestrator/channels/web/static/app.js,
  orchestrator/channels/web/static/index.html, INVESTMENT_ROADMAP.md

## [2026-07-01 23:35] — Claude Code — B-Phase 2 Insider-Screening + Alerts
- **Was:** `InvestmentEngine.insider_scan()` -- zieht Form-4-Kaeufe je Watchlist-Symbol, erkennt Insider-
  **Cluster**/Grosskaeufe, erzeugt Risk-gepruefte 'beobachten'-Alerts (via Notifier/`melde_an_ceo`) mit
  Filing-Link + **Second-Brain-Notiz**. Engine um optionalen `brain`-Callback erweitert (in `bot.py` +
  `app.py` verdrahtet). Neue HoA-Tools **`insider_scan`** + **`insider_signale_zeigen`**. 3 neue Engine-Tests
  (Cluster/Alert, unauffaellig, Fall-B); Gesamtsuite **234** gruen.
- **Warum:** Bauplan Teil B / Roadmap Phase 2.5 (advisory, keine Trades).
- **Betroffen:** orchestrator/investment/engine.py, orchestrator/core/hoa_tools.py,
  orchestrator/channels/telegram/bot.py, orchestrator/channels/web/app.py,
  orchestrator/tests/test_investment_engine.py

## [2026-07-01 23:15] — Claude Code — B-Phase 1 Insider-Datenanbindung (gratis)
- **Was:** `MarketData.insider_transactions()` (SEC **Form 4** via Finnhub, normalisiert Kauf/Verkauf je
  Insider, Wert-Berechnung, Filing-Link, **Fall-B** ohne Key) + `InvestmentStore`-Tabelle `insider_signals`
  (`insider_signal_add`/`insider_signals`). 4 neue Tests (Mock, gruen; Gesamtsuite **231**).
- **Warum:** Bauplan Teil B / Roadmap Phase 2.5 -- gratis Datenanbindung fuers Insider-Screening (kein neuer
  bezahlter Dienst, SEC EDGAR/Finnhub-Free).
- **Betroffen:** orchestrator/investment/providers.py, orchestrator/investment/store.py,
  orchestrator/tests/test_investment_providers.py, orchestrator/tests/test_investment_store.py

## [2026-07-01 23:06] — Claude Code (als Head of Agents, CEO-Freigabe) — B-Phase 0 Insider-Screening
- **Was:** CIO-Charta (`agents/16_cio.md`) um Insider-/Smart-Money-Screen (SEC Form 4) ergaenzt (5 Punkte:
  Auftrag, „Ausdruecklich NICHT" rechtliche Klarstellung nur oeffentliche Pflichtmeldungen, Tools, Aufgaben-
  katalog, Workflow). `INVESTMENT_ROADMAP.md` um **Phase 2.5** (Insider-Screening, advisory, dateibasiert, kein
  GATE) + Status-Tabellenzeile erweitert.
- **Warum:** CEO-freigegebener Bauplan (Insider-Screening unter CIO, Teil B); Charta-Diff vorab freigegeben (AGENTS.md 3.3).
- **Betroffen:** agents/16_cio.md, INVESTMENT_ROADMAP.md

## [2026-07-01 01:00] — Claude Code (Antrags-Revision durch CEO-Feedback + Batch-Reformat)
- **Was:** Neue Faehigkeit: **Antraege revidieren**. `antraege.py` `revidieren()` (neues Event mit
  ueberarbeitetem titel/beschreibung + Status zurueck auf 'eingereicht' -> Neufreigabe noetig) +
  `reset_eingereicht()`. `innovation.py`: `revidiere(antrag_id, feedback)` -- Fachagenten (Gemini-Fallback)
  denken Loesung + Kostenvoranschlag NEU anhand CEO-Feedback (suchen guenstigere/kostenlose Wege), Ergebnis im
  neuen knappen Format mit `↻ REVIDIERT`-Marker; `neu_formatieren()` (Batch: alle offenen Antraege ins neue
  Format, freigegebene zurueckgesetzt). CFO-Format als `_CFO_PROMPT` faktorisiert, `_baue_beschreibung`/
  `_agent_fuer` Helfer. LUNA-Tools `antrag_revidieren` + `antraege_neu_formatieren`. LUNA-OS: Endpunkte
  `/api/antraege/{id}/revidieren` + `/api/antraege/neu-formatieren`; Frontend: Button **„✏️ Revidieren"** mit
  Feedback-Eingabefeld (Status-/Kosten-Update live). Asset-Cache-Bust v15. **Verifiziert:** Suite 228/228;
  Revision-Smoke-Test (Feedback 'mach es kostenlos' -> 'KOSTEN: 0 EUR' + Status eingereicht); app.js Syntax ok.
- **Warum:** CEO-Wunsch 2026-07-01 -- Antraege ins neue Format regenerieren, freigegebene zuruecksetzen, und
  ein Feld, in das der CEO Feedback eintraegt (z. B. 'guenstiger/kostenlos'), das von LUNA/Sonnet verstanden
  und neu erarbeitet wird.
- **Betroffen:** orchestrator/core/{antraege.py, innovation.py, hoa_tools.py},
  orchestrator/channels/web/{app.py, static/app.js, static/index.html}, projekt_changelog.md.

## [2026-07-01 00:20] — Claude Code (CFO-Kostenvoranschlag: auf einen Blick, EUR, Stufen)
- **Was:** CFO-Kostenvoranschlag der Innovations-/Self-Dev-Pipeline (`innovation.py`) auf ein knappes,
  scannbares Format umgestellt: Zeile 1 zwingend `KOSTEN: ~<einmalig> EUR einmalig, ~<laufend> EUR/Monat`,
  danach `Stufen:` (z. B. Sparvariante ~20 EUR vs. Mehr ~40 EUR -- mit dem konkreten UNTERSCHIED), `Nutzen:`
  (ein Satz), `Kostentreiber:` -- in **EUR**, max ~7 Zeilen, KEINE Tabellen/Pipes/Sterne. Im Antrag steht die
  **Kosten-Kernzeile jetzt ganz oben** (`💶 KOSTEN…`, via `_kosten_kopf`) -> auf einen Blick erfassbar.
  `_strip_md` (innovation) + `_md_strip` (LUNA-OS, app.py) wandeln zusaetzlich Markdown-Tabellen in lesbaren
  Text (`a · b · c`, Trennzeilen raus) -> auch ALT-Antraege werden in LUNA-OS sauber dargestellt.
- **Warum:** CEO-Meldung 2026-07-01 -- CFO-Voranschlaege unuebersichtlich (rohe Markdown-Tabellen, USD,
  Textwand); CEO muss auf einen Blick Monatskosten + Nutzen + Stufen (20 vs. 40 EUR) erkennen.
  Neue Antraege bekommen das volle Format; bestehende werden zumindest lesbar gerendert.
- **Betroffen:** orchestrator/core/innovation.py, orchestrator/channels/web/app.py, projekt_changelog.md.

## [2026-06-30 14:30] — Claude Code (Telegram-Umlaute an der Wurzel + Antrags-Struktur sauberer)
- **Was:** (1) **Umlaute systemisch:** Fachagenten-Backend (`backends.py` FallbackBackend) haengt jetzt eine
  Stil-Anweisung an JEDEN Fachagenten-Prompt an: korrektes Deutsch mit echten Umlauten (ä/ö/ü/ß) + reiner
  Fliesstext OHNE Markdown (keine `**`, `#`). Das war die Wurzel: Innovations-/Self-Dev-Antraege kamen in
  ae/oe/ue + mit Sternen, weil die Subagenten (anders als LUNAs Chat) keine Umlaut-Vorgabe hatten. Zusaetzlich
  vereinzelte ASCII-Anzeigetexte gefixt: CIO-Push (Vorschläge/geprüft, bot.py), Self-Dev-Hinweis/Thema
  (nötig/über/Lücken), Kalender-Watcher (überschneiden/Überschneidung), Wissensstand (Einträge, scheduler.py).
  (2) **Antrags-Struktur (innovation.py):** klar gegliederte, markdown-freie Beschreibung — Abschnitte
  `IDEE / MACHBARKEIT (CTO) / KOSTEN (CFO) / QUELLEN`; Titel ohne Sterne; dupliziertem Titel in der IDEE
  entfernt (`_strip_md`/`_clean`). (3) **LUNA-OS-Anzeige (app.py):** `_md_strip` entfernt Markdown aus Antrags-
  Titel/Beschreibung -> auch Alt-Antraege werden sauber dargestellt. Test (`test_innovation.py`) auf die neue
  Umlaut-Meldung nachgezogen. **Verifiziert:** Suite 228/228.
- **Warum:** CEO-Meldung 2026-06-30 -- Telegram noch ae/oe/ue (CIO „geprueft", Briefing „fuer"); Antraege
  schlecht dargestellt (Sterne) und inhaltlich unstrukturiert. Wurzel (Subagenten-Stil) statt Symptom-Jagd.
- **Betroffen:** orchestrator/core/{backends.py, innovation.py, scheduler.py, self_development.py},
  orchestrator/channels/{telegram/bot.py, web/app.py}, orchestrator/tests/test_innovation.py, projekt_changelog.md.

## [2026-06-30 12:30] — Claude Code (CEO: LUNA auf Sonnet 5 umgestellt)
- **Was:** `orchestrator/config.toml`: LUNAs Gehirn (`[voice] llm_model`), die Fachagenten (`[models]`
  hoa/cto/berater) und die Code-Execution (`[voice] exec_model`, neu) von `claude-haiku-4-5`/`claude-opus-4-8`
  auf **`claude-sonnet-5`** umgestellt. Routing-Modell bewusst auf `claude-haiku-4-5` belassen (kostenbewusst,
  internes Routing). Modell-IDs ueber claude-api-Skill verifiziert (Sonnet 5 = `claude-sonnet-5`, adaptive
  Thinking default, $3/$15 pro 1M, Intro $2/$10 bis 31.08.2026).
- **Warum:** CEO-Entscheidung 2026-06-30 (Umfang: Chat + Fachagenten + Execution; jetzt eintragen). Sonnet 5
  bietet nahezu Opus-Qualitaet bei agentischer Arbeit/Tool-Calling + Vision, guenstiger als Opus 4.8.
  **WICHTIG:** greift erst, wenn **Anthropic-API-Guthaben** verfuegbar ist (Raw-API ueber ModelRouter, nicht
  CLI-Abo) — Anthropic-Sperre bis 2026-07-01 + frueherer 'credit balance too low'-Blocker; bis dahin faellt
  LUNA weiter auf Gemini zurueck (kein Bruch). Kostenpflichtiges Modell = **CEO-Tor/Budget** (finance/budget.md,
  CFO). **Deployment:** NAS-Sync noetig (sync-to-nas.sh), damit die NAS-Container die neue Config nutzen.
  **Verifiziert:** config.toml laedt; Suite 228/228.
- **Betroffen:** orchestrator/config.toml, projekt_changelog.md.

## [2026-06-29 12:45] — Claude Code (Phase 17 M5/#3: Haende in den Orb (native Steuerung via Datei-Queue))
- **Was:** Tastatur/Maus laufen jetzt im Orb-Kontext (dort liegt das Bedienungshilfen-Recht). Neu
  `mac/LunaOrb/.../OrbActuator.swift` — native CGEvent-Primitive (tippen via keyboardSetUnicodeString, taste
  via Keycode+Flags, klick) + Berechtigungspruefung `AXIsProcessTrusted`; liest Befehle aus `~/.luna_orb/`
  (Datei-Queue) und schreibt Ergebnisse zurueck. main.swift: Aktuator-Start + Menue „Steuerung erlauben
  (Bedienungshilfen)" (Prompt + oeffnet den Einstellungs-Bereich). Server-Seite: `runner/orb_bridge.py`
  (schreibt cmd-/liest res-Datei, Timeout) + Aktuator routet `tastatur_text`/`taste`/`klick` ueber den Orb
  (osascript-Weg entfaellt, da Permission dort fehlte). Neues Verb `klick` (x,y). **Verifiziert:** Suite
  228/228; Datei-Queue Round-Trip Server->Orb->Ergebnis laeuft (Orb meldet sauber „Bedienungshilfen nicht
  erlaubt", da noch nicht erteilt -> Plumbing bewiesen). Live-Tasten/Klicks nach CEO-Freigabe der
  Bedienungshilfen.
- **Warum:** CEO „Mach das" — Haende in den Orb verlagern (Accessibility am .app), damit `tastatur_text`/`taste`/
  `klick` real wirken; Voraussetzung fuer den generischen Seh-Handle-Loop.
- **Betroffen:** mac/LunaOrb/Sources/LunaOrb/{OrbActuator.swift (neu), main.swift}, runner/orb_bridge.py (neu),
  runner/actuator.py, orchestrator/core/hoa_tools.py, projekt_changelog.md.

## [2026-06-29 12:15] — Claude Code (Phase 17 M5/#3: LUNA sieht den Bildschirm (Gemini-Augen, gratis))
- **Was:** Generisches „Bildschirm sehen" — der Orb nimmt einen Screenshot auf und ein Vision-Modell liest ihn.
  Neu `runner/vision.py` (`bild_lesen` -> Gemini-Vision via OpenAI-kompatibel, gratis; kein Anthropic) + neuer
  Endpunkt **`/api/sehen`** in `orchestrator/channels/web/app.py` (nimmt base64-PNG + optionale Frage). Orb:
  `ScreenReader.swift` (ScreenCaptureKit `SCScreenshotManager`, Berechtigung Bildschirmaufnahme), `LunaClient.sehen`,
  Menuepunkt **„Was siehst du?"** (Screenshot -> /api/sehen -> Beschreibung als Dialog). Package.swift Plattform
  auf macOS 14 angehoben (SCScreenshotManager). **`cliclick` installiert** (brew, fuer spaetere Maus-Klicks).
  **Verifiziert:** Suite 228/228; `/api/sehen` mit Test-PNG -> Gemini erkennt korrekt App (XMind), Button
  („Exportieren") und Inhalt; `build_app.sh` gruen; Orb laeuft. **Live-Capture vom Orb testet der CEO**
  (Bildschirmaufnahme beim ersten „Was siehst du?" erlauben).
- **Warum:** CEO will „beides" (Gemini-Loop + deterministisch) und Inhalte generisch sehen — die „Augen" sind
  damit gratis (Gemini), ohne Anthropic. Screenshot kommt vom Orb (Screen-Recording am .app), da serverseitig
  TCC-blockiert.
- **Betroffen:** runner/vision.py (neu), orchestrator/channels/web/app.py,
  mac/LunaOrb/Sources/LunaOrb/{ScreenReader.swift (neu), LunaClient.swift, main.swift}, mac/LunaOrb/Package.swift,
  projekt_changelog.md. (System: cliclick via brew installiert.)

## [2026-06-29 11:40] — Claude Code (Phase 17: deterministische Tastatur-Haende + Computer-Use-Architektur korrigiert)
- **Was:** (1) **Generische Haende (deterministisch, gratis):** Aktuator-Verben **`tastatur_text`** (tippt Text
  in die vorderste App) und **`taste`** (Tastenkuerzel wie 'cmd+s'/'return', Parser `build_taste_script` mit
  Modifier-/Spezialtasten-Map) in `runner/actuator.py`; in GENERIC_VERBS (jede installierte App), gegated.
  `rechner_aktion`-Beschreibung erweitert. Unit-Tests (`test_phase17_actuator.py`). (2) **Architektur-Korrektur
  (CEO-Frage 'warum Anthropic noetig?'):** Anthropic ist NICHT zwingend — Bedienen ist gratis/lokal; nur das
  'Screenshot deuten' braucht ein multimodales Modell (Gemini Gratis-Tier moeglich). PHASE17_PLAN.md 8a neu
  gefasst (Gemini-Loop + deterministisch; CEO-Wahl 'beides'). (3) **Befund:** echtes Steuern braucht zwei
  macOS-Rechte am ausfuehrenden Prozess: **Accessibility** (Tasten/Maus; Fehler 1002 im Server-Kontext) +
  **Screen Recording** (Screenshot; serverseitig 'could not create image from display'). -> Aktuator+Capture
  gehoeren in den **Orb (.app)**. **Verifiziert:** Suite 228/228 (+5 Parser-Tests); Tastenkuerzel-Parser ok.
  **Noch NICHT live:** keystroke-Ausfuehrung braucht Accessibility (im Terminal-Server nicht erteilt) — Logik
  steht, laeuft sobald der ausfuehrende Prozess (Orb) das Recht hat.
- **Warum:** CEO will 'beides' (Gemini-Loop + deterministisch) und fragte, warum Anthropic noetig sei — Antwort
  eingearbeitet; Fundament (Haende) gebaut, Architektur (Orb-Kontext) geklaert.
- **Betroffen:** runner/actuator.py, orchestrator/core/hoa_tools.py,
  orchestrator/tests/test_phase17_actuator.py, PHASE17_PLAN.md, projekt_changelog.md.

## [2026-06-29 11:10] — Claude Code (Phase 17: App in den Vordergrund holen)
- **Was:** Beim Arbeiten in einer App holt LUNA sie jetzt in den **Vordergrund** (vorher blieb sie hinten).
  `runner/actuator.py`: `app_oeffnen` macht nach `open -a` zusaetzlich `activate` (sicher im Vordergrund);
  neue Helfer `app_aktivieren(app)` und `datei_im_vordergrund_oeffnen(pfad)` (`open <pfad>`). Die XMind-Tools
  (`xmind_lesen`, `xmind_bearbeiten` in `orchestrator/core/hoa_tools.py`) holen nach Erfolg **XMind mit der
  Datei in den Vordergrund**; beim Bearbeiten zusaetzlicher Hinweis, dass eine offene Datei einmal neu
  geoeffnet werden muss, damit die Aenderung sichtbar wird. **Verifiziert:** Suite 223/223; app_aktivieren/
  app_oeffnen/datei_im_vordergrund liefern ok (XMind kommt nach vorn).
- **Warum:** CEO-Wunsch 2026-06-29 — die App, ueber die gesprochen/in der gearbeitet wird, soll sichtbar im
  Vordergrund sein, nicht im Hintergrund.
- **Betroffen:** runner/actuator.py, orchestrator/core/hoa_tools.py, projekt_changelog.md.

## [2026-06-29 10:55] — Claude Code (Phase 17 M5/#3: Computer-Use-Integrationsplan)
- **Was:** PHASE17_PLAN.md um Abschnitt „8a. M5/#3 — Computer-Use" ergaenzt: Architektur (Orb-Screenshot ->
  Anthropic-Computer-Use-Loop -> jede Aktion durch DASSELBE Tor: actuator.gate/Not-Aus/Allowlist/Audit,
  CEO-Tor bleibt), Kosten (billbar -> CFO/CEO-Tor) und Aktivierungs-Checkliste. **Status: vorbereitet,
  Aktivierung mit Anthropic-Zugang (~2026-07-01)** — wird NICHT ungetestet ausgeliefert. M5 in die
  Milestone-Liste aufgenommen (Teil #2 XMind erledigt, Teil #3 Computer-Use folgt).
- **Warum:** CEO waehlte „2 und 3"; #3 (generisches Sehen+Bedienen) braucht Modellzugang -> Plan jetzt fixiert,
  Bau/Test bei Verfuegbarkeit.
- **Betroffen:** PHASE17_PLAN.md, projekt_changelog.md.

## [2026-06-29 10:50] — Claude Code (Phase 17 M5/#2: XMind-Inhalt sehen + bearbeiten)
- **Was:** LUNA kann den **Inhalt** einer XMind-Mindmap lesen UND bearbeiten — direkt ueber die `.xmind`-Datei
  (ZIP + content.json), ohne Screenshot/Computer-Use. Neu `runner/xmind.py` (find_recent_xmind, read_outline,
  add_node, rename_node; ZIP wird sauber neu geschrieben, andere Eintraege unveraendert). Neuer Gate-Helper
  `runner/actuator.gate(kategorie)` (Not-Aus + Modus, wiederverwendbar). Zwei LUNA-Tools:
  **`xmind_lesen`** (read-only Gliederung) und **`xmind_bearbeiten`** (aktion=knoten_hinzufuegen|umbenennen,
  gegated: Vorschau/Bestaetigung/Not-Aus/Audit). Test `orchestrator/tests/test_phase17_xmind.py`.
  **Verifiziert:** Suite 223/223 (+6 neu); Chat „Lies governance/organigramm.xmind" -> LUNA nennt die
  Struktur (CEO/HoA/14 C-Level); Gate-Bearbeiten Vorschau->Ausfuehrung legt Knoten real an (an Kopie getestet,
  Repo-Datei unveraendert). **Hinweis:** Aenderung geht in die Datei; bei offener Datei erst nach erneutem
  Oeffnen sichtbar (Live-waehrend-offen = Computer-Use-Weg #3).
- **Warum:** CEO-Anweisung 2026-06-29 — LUNA soll Programminhalte (XMind) sehen + bearbeiten; gewaehlt wurde
  Weg #2 (app-spezifisch ueber Dateiformat) zusammen mit #3 (Computer-Use, folgt mit Anthropic-Zugang).
- **Betroffen:** runner/xmind.py (neu), runner/actuator.py, orchestrator/core/hoa_tools.py,
  orchestrator/tests/test_phase17_xmind.py, projekt_changelog.md.

## [2026-06-29 10:25] — Claude Code (Roadmap: Social Media Analyzer + M5 Inhalte sehen/bearbeiten)
- **Was:** ROADMAP.md ergaenzt: (1) Backlog **„Social Media Analyzer"** (CEO-Wunsch) — monatlicher Import
  von Instagram-/Facebook-Insights -> Aufbereitung -> **automatisches Befuellen des Media-Kits in Canva**
  (Canva-Autofill-API/MCP), Veroeffentlichen bleibt CEO-Tor. (2) Phase 17 **MVP-Status (M1–M4 ✅)** +
  Milestone **M5 „Tiefes App-Verstaendnis: Inhalte SEHEN & BEARBEITEN"** (CEO-Prio): heute kennt LUNA nur
  App-Namen, nicht den Inhalt (z. B. XMind-Knoten) — Wege Vision/Accessibility/Dateiformat/Computer-Use
  dokumentiert. Voice-Latenz + NAS-Bruecke als offene Punkte vermerkt.
- **Warum:** CEO-Anweisungen 2026-06-29 (neuer Tool-Wunsch + Kern-Faehigkeit „Inhalte sehen & bearbeiten").
- **Betroffen:** ROADMAP.md, projekt_changelog.md.

## [2026-06-29 10:05] — Claude Code (Phase 17: Voice robust (Halbduplex) + app_oeffnen + Diagnose)
- **Was:** (1) **VoiceSession neu als Halbduplex** (`mac/LunaOrb/.../VoiceSession.swift`): waehrend LUNA
  spricht, ist das Mikrofon AUS (kein Feedback-Loop, kein fragiles Voice-Processing); je Runde hoeren ->
  Sprechpause -> `/api/chat` -> ElevenLabs/`/api/tts` (Fallback System-Stimme) -> wieder hoeren. **Sichtbare
  Diagnose** ueber onInfo/onTranscript (Menue-Zeile „Stimme: …"). Neuer Menuepunkt **„Stimme testen"**
  (`speakTest`, reiner Ausgabe-Test unabhaengig vom Mikrofon). main.swift: Status-Refactor (gespeicherter
  serverOnline), Diagnosezeile. Barge-in zurueckgestellt (braucht Echo-Cancellation) — Stabilitaet zuerst.
  (2) **Aktuator `app_oeffnen`** (`runner/actuator.py`): generisches benignes Verb fuer JEDE installierte App
  (`open -a`), unter dem gleichen Tor; `rechner_aktion`-Beschreibung erweitert. **Verifiziert:** Suite 217/217;
  `build_app.sh` gruen; `/api/tts` liefert MP3 (Ausgabe ok); Chat „oeffne XMind" -> XMind startet real.
- **Warum:** CEO meldete: beim Gespraech keine hoerbare Antwort, „oeffne XMind" passierte nichts. Ursache 1:
  fragile Vollduplex-Audiokette -> Halbduplex + Diagnose. Ursache 2: es gab gar kein Tool zum App-Oeffnen ->
  `app_oeffnen` ergaenzt.
- **Betroffen:** mac/LunaOrb/Sources/LunaOrb/{VoiceSession.swift, main.swift}, runner/actuator.py,
  orchestrator/core/hoa_tools.py, projekt_changelog.md.

## [2026-06-29 09:45] — Claude Code (Roadmap: Gemini-Omni-Pruefung fuer den Cutter)
- **Was:** ROADMAP.md Backlog um den Punkt „**ZEITNAH PRUEFEN — Gemini Omni fuer den Cutter**" ergaenzt
  (CEO-Wunsch): pruefen, ob Googles multimodales/Omni-Modell den Cutter verbessert (Szenen-/Highlight-
  Verstaendnis, Reihenfolge/Schnittauswahl, bester Ausschnitt); Modellname/Verfuegbarkeit/Kosten/Datenschutz
  klaeren -> entscheidungsreifer Antrag (CEO-Tor). Prioritaet zeitnah.
- **Warum:** CEO-Anweisung 2026-06-29.
- **Betroffen:** ROADMAP.md, projekt_changelog.md.

## [2026-06-29 09:30] — Claude Code (Phase 17 M4-Fix: .app-Bundle + Umlaute im Orb)
- **Was:** (1) **Crash-Fix** „Orb verschwindet beim Gespraech-Start": Ursache laut Crash-Report = TCC-
  Privacy-Violation — das per Linker ins Binary eingebettete Info.plist wird von macOS fuer Spracherkennung
  NICHT akzeptiert. Loesung: echtes **`.app`-Bundle** (Info.plist in `Contents/`). Neues `build_app.sh`
  (swift build -> LunaOrb.app zusammensetzen -> ad-hoc codesign); Info.plist um CFBundleExecutable/
  CFBundlePackageType ergaenzt. Start jetzt via `./build_app.sh && open LunaOrb.app`. (2) **Umlaute in der
  sichtbaren Oberflaeche** (CEO-Wunsch): alle Nutzer-Texte in `main.swift` (Menue/Dialoge), die Voice-
  Hinweise und die Info.plist-Berechtigungstexte auf echte ä/ö/ü/ß umgestellt (Code/Bezeichner bleiben
  ASCII). LunaOrb.app gitignored. **Verifiziert:** `build_app.sh` gruen; Bundle traegt UsageDescriptions +
  Bundle-ID + Ad-hoc-Signatur; Orb startet stabil als App-Bundle (kein Crash beim Start).
- **Warum:** CEO meldete Crash + fehlende Umlaute. Das `.app`-Bundle ist zugleich der geplante „installierbar"-
  Haerteschritt und Voraussetzung fuer Mikrofon/Spracherkennung.
- **Betroffen:** mac/LunaOrb/{build_app.sh (neu), Info.plist, .gitignore, README.md,
  Sources/LunaOrb/{main.swift, VoiceSession.swift}}, projekt_changelog.md.

## [2026-06-29 09:05] — Claude Code (Phase 17 M4: Live-Gespraech am Orb, Lunas Kern)
- **Was:** Native Duplex-Sprachschleife im Swift-Orb. Neu `mac/LunaOrb/Sources/LunaOrb/VoiceSession.swift`:
  Mikrofon (AVAudioEngine mit Voice-Processing = **Echo-Cancellation**) -> **SFSpeechRecognizer (de-DE)** ->
  bei Sprechpause Aeusserung an die lokale LUNA (`/api/chat`) -> Antwort per **ElevenLabs** (`/api/tts`,
  Fallback NSSpeechSynthesizer). **Barge-in**: reinreden stoppt die Wiedergabe sofort; Orb spiegelt
  zuhoeren/sprechen. `LunaClient.tts()` ergaenzt. Menue „Live-Gespraech starten/beenden" (Tipp-Chat
  umbenannt „Mit LUNA tippen…"). **Berechtigungen:** `Info.plist` mit Mikrofon-/Sprach-Texten +
  Bundle-ID, via Linker (`-sectcreate __TEXT __info_plist`) ins Binary eingebettet (Package.swift).
  **Verifiziert:** `swift build` gruen; Section `__info_plist` + beide UsageDescriptions im Binary; Orb
  startet. Echter Mikrofon-/Sprach-Loop wird vom CEO live getestet (TCC-Dialoge + Audio nur am Geraet).
- **Warum:** Phase-17-Milestone M4 (PHASE17_PLAN.md) — das Live-Gespraech ist Lunas Kern: zuhoeren, in der
  Sprache des CEO antworten, unterbrechbar, Kontext + On-Screen-Awareness kombinieren und live handeln.
- **Betroffen:** mac/LunaOrb/Sources/LunaOrb/{VoiceSession.swift (neu), main.swift, LunaClient.swift},
  mac/LunaOrb/Info.plist (neu), mac/LunaOrb/Package.swift, mac/LunaOrb/README.md, projekt_changelog.md.

## [2026-06-29 08:40] — Claude Code (Phase 17 M3: Aktuator mit Tor + zwei Modi)
- **Was:** `runner/actuator.py` (neu) — Aktuator hinter vier Schutzschichten: **Allowlist** (Start nur
  TextEdit/text_schreiben), **Vorschau->Bestaetigung**, **Not-Aus** (`~/.luna_orb_killswitch`), **Audit**.
  **Zwei Modi** (CEO-Wunsch): `bestaetigen` (Default: erst Vorschau, dann Ja) und `sofort` (benigne,
  freigegebene Aktionen ohne Rueckfrage) — umschaltbar; **CEO-Tor (Geld/Recht/Oeffentlichkeit/Loeschen)
  bleibt in BEIDEN Modi bestaetigungspflichtig**. Modus liegt in `~/.luna_orb_mode` (gemeinsam Python+Orb).
  Neue LUNA-Tools `rechner_aktion` + `steuerung_modus` (`orchestrator/core/hoa_tools.py`). Swift-Orb
  (`mac/LunaOrb/.../main.swift`): Menue-Schalter „Modus: Sofort/Bestaetigen". TextEdit-Executor startet die App
  robust (open -a + warten) und uebergibt Text als argv (keine AppleScript-Injection). Test
  `orchestrator/tests/test_phase17_actuator.py`. **Verifiziert:** Suite 217/217; Vorschau (kein Eingriff),
  Allowlist-Block, echte TextEdit-Ausfuehrung, Audit-Log; voller Loop ueber `/api/chat` (LUNA fragt im
  Bestaetigen-Modus zurueck statt still auszufuehren).
- **Warum:** Phase-17-Milestone M3 (PHASE17_PLAN.md) — LUNA bedient den Rechner kontrolliert; CEO-Wunsch nach
  einem aktivierbaren Sofort-Modus umgesetzt, ohne die harte CEO-Tor-Regel aufzuweichen.
- **Betroffen:** runner/actuator.py (neu), orchestrator/core/hoa_tools.py,
  mac/LunaOrb/Sources/LunaOrb/main.swift, orchestrator/tests/test_phase17_actuator.py, projekt_changelog.md.

## [2026-06-28 18:10] — Claude Code (Phase 17 M2: On-Screen-Awareness + App-Wissen)
- **Was:** Neues Paket `runner/` (additiv, Mac-lokal): `awareness.py` (vorderste App + Fenstertitel +
  laufende Apps via osascript/System Events; degradiert auf Nicht-macOS ohne Crash) und `capabilities.py`
  (scannt installierte Programme, fuehrt automatisch fortgeschriebene Markdown-Registry
  `runner/app_register.md` [gitignored, maschinenspezifisch], empfiehlt zur Aufgabe passende Apps samt
  Steuerungsweg). Zwei neue LUNA-Tools in `orchestrator/core/hoa_tools.py`: **`bildschirm_sehen`**
  (On-Screen-Awareness, nur Lesen) und **`apps_kennen`** (App-Wissen + Empfehlung). Test
  `orchestrator/tests/test_phase17_mac_tools.py` (plattform-sicher). `.gitignore` um die generierte Registry
  ergaenzt. **Verifiziert:** Suite 203/203 + 6 neue gruen; `bildschirm_sehen` liefert real die Vordergrund-App
  + laufende Apps; `apps_kennen` scannt 107 Apps und empfiehlt korrekt (Text -> TextEdit/Notes).
- **Warum:** Phase-17-Milestone M2 (PHASE17_PLAN.md) — LUNA „sieht" die App-Lage und kennt die installierten
  Programme/ihre Eignung. Grundlage fuer gezieltes Handeln + Vorschlaege (M3). NAS-LUNA unberuehrt (Tools
  degradieren auf Linux).
- **Betroffen:** runner/** (neu), orchestrator/core/hoa_tools.py, orchestrator/tests/test_phase17_mac_tools.py,
  .gitignore, projekt_changelog.md.

## [2026-06-28 17:45] — Claude Code (Phase 17: CEO-Klarstellungen in den Plan aufgenommen)
- **Was:** `PHASE17_PLAN.md` Abschnitt „3a. Klarstellungen CEO (2. Runde)" ergaenzt: (1) **„Eine LUNA, zwei
  Gesichter"** als Architektur-Invariante — Mac-Orb + NAS-LUNA sind dieselbe LUNA (gleicher Code/Regeln/
  Charten); lebender Zustand (brain/Antraege/Verlauf) liegt live auf der NAS, Mac-Orb liest/schreibt ihn ueber
  die NAS-Bruecke (keine divergente lokale Insel). (2) **App-Wissen als automatisch fortgeschriebene
  `.md`-Registry** (Scan installierter Programme -> wofuer/wie steuerbar; bei Neuinstallation aktualisiert).
  (3) **Cursor-Steuerung** ausdruecklich gewollt/erlaubt (unter dem Aktuator-Tor). (4) **Live-Gespraech
  (Duplex, Barge-in, Kontext+On-Screen-Awareness) ist Lunas KERN** (M4; nativ SFSpeechRecognizer+AVAudioEngine).
- **Warum:** CEO-Rueckfragen/Vorgaben (2026-06-28) verbindlich verankern, bevor M2 gebaut wird.
- **Betroffen:** PHASE17_PLAN.md, projekt_changelog.md.

## [2026-06-28 17:30] — Claude Code (Phase 17 M1: Swift-Menueleisten-Orb)
- **Was:** Neues Swift-Paket `mac/LunaOrb/` (SwiftPM) — nativer macOS-Menueleisten-Orb (NSStatusItem,
  `.accessory`-Policy, kein Dock-Icon). Drei Orb-Zustaende (idle/listening/speaking via SF-Symbol + Tint),
  Menue „Mit LUNA sprechen…" -> `/api/chat` der **lokalen** LUNA (127.0.0.1:8765, nur localhost),
  „Verbindung pruefen" (Ping), „Not-Aus" schreibt Sperr-Flag `~/.luna_orb_killswitch` (vom kuenftigen
  Aktuator zu pruefen). Dateien: Package.swift, Sources/LunaOrb/{main,OrbState,LunaClient}.swift,
  README.md, .gitignore. **Verifiziert:** `swift build` gruen; Orb laeuft als Menueleisten-App; lokale LUNA
  gestartet -> Ping 200; `/api/chat`-Round-Trip liefert echte LUNA-Antwort (Gemini-Fallback).
- **Warum:** Phase-17-Milestone M1 (PHASE17_PLAN.md) — die Shell des Co-Working-Orbs steht und spricht mit
  der bestehenden lokalen LUNA, ohne die NAS-Container anzufassen (additiv, separater Prozess).
- **Betroffen:** mac/LunaOrb/** (neu), projekt_changelog.md.

## [2026-06-28 17:05] — Claude Code (Phase 17: MVP-Teilplan „LUNA am Mac" beschlossen)
- **Was:** `PHASE17_PLAN.md` angelegt — vereinbarter MVP-Zuschnitt fuer Phase 17 (Live-Co-Working am
  Rechner). CEO-Entscheidungen 2026-06-28: **native Swift `.app`** als Menueleisten-Orb; erster Build
  **L1+L2 mit EINER App** (On-Screen-Awareness + eine benigne, gegatete Steuer-Aktion in TextEdit);
  Steuerung **lokal am Mac**, kein NAS->Mac-Kanal im MVP. Architektur (Swift-Orb = Augen/Haende/UI <->
  lokale Python-LUNA = Verstand/Wissen/Tor), neue Bausteine (`mac/LunaOrb/`, `runner/awareness.py`,
  `runner/capabilities.py`, `runner/actuator.py`, web-Endpunkte/Tools), Governance (vier Schutzschichten,
  CEO-Tor, Not-Aus, Audit, Least-Privilege; L1+L2, kein L3), GATE + Milestones M0–M4.
- **Warum:** CEO startet Phase 17; vor dem Bau ein kleiner, sicherer MVP-Plan mit GATE (AGENTS.md/
  autonomie-stufen.md). Bestehende LUNA (NAS-Container) bleibt unberuehrt — Mac-Teil ist additiv.
- **Betroffen:** PHASE17_PLAN.md (neu), projekt_changelog.md.

## [2026-06-28 16:30] — Claude Code (Roadmap: Phase 17 = Live-Co-Working am Rechner)
- **Was:** ROADMAP.md Phase 17 um die CEO-Vision **„Paralleles Co-Working"** erweitert: nicht nur
  Einzelauftraege (Computer-Use), sondern **gemeinsames Live-Arbeiten im Gespraech** -- CEO sieht die offene
  App, erzaehlt/weist an, LUNA setzt live um, CEO justiert per Sprache, LUNA schlaegt selbst vor (Beispiele
  XMind: Prozess-Knoten anlegen/aendern; Mail: diktieren/aendern, Senden bleibt Mensch-Tor). Bausteine
  ergaenzt: App-Steuerung (Claude Computer-Use ODER lokale Automatisierung), **Bildschirm-/App-Wahrnehmung**
  (LUNA muss sehen, was auf dem Schirm ist), Gespraechs-Schleife (Live-Voice-Orb), lokaler Mac-Runner +
  NAS->Mac-Kanal. Status-Tabelle aktualisiert. Governance bleibt HART (nur auf Anweisung, CEO-Tor fuer
  Geld/Recht/Oeffentlichkeit/Loeschen, Not-Aus, Audit, Least-Privilege).
- **Warum:** CEO-Wunsch, parallel mit LUNA arbeiten zu koennen („ich sehe, sie setzt um"); eingeordnet als
  Vollausbaustufe von Phase 17.
- **Betroffen:** ROADMAP.md.

## [2026-06-28 16:10] — Claude Code (Watchlist-Autocomplete + Entfernen + automatisches Backup)
- **Was:** (1) **Symbol-Autovervollstaendigung** fuer die Watchlist: `MarketData.suche` (Aktien via Finnhub
  `/search`, Krypto via CoinGecko `/search`; Krypto-Symbol = CoinGecko-ID) + Endpunkt `/api/investment/suche` +
  Frontend-Dropdown (debounced, asset-bewusst). Live verifiziert (apple -> AAPL/AppLovin/Applied Materials).
  (2) **Aus der Watchlist entfernen:** Chips mit ✕ + Endpunkt `/api/investment/watchlist/remove`. Add/Remove im
  Preview verifiziert. (3) **Automatisches Off-NAS-Backup:** `deploy/backup-from-nas.sh` self-contained
  umgebaut (schreibt nach `~/LUNA-Backups`, AUSSERHALB ~/Documents, damit launchd ohne Full-Disk-Access laeuft
  -- macOS-TCC; Aufbewahrung: letzte 30, neuestes hat die volle Historie). **launchd-Agent**
  `com.hanserautisch.investment-backup` (taeglich 03:00 + bei Login) installiert + live verifiziert (Exit 0,
  9 Stores/3972 Events gesichert). Kein manuelles Anfassen noetig. Cache ?v=14. Suite **203/203**.
- **Warum:** CEO-Wuensche: Autocomplete + Loeschen in der Watchlist; Backup automatisch.
- **Betroffen:** orchestrator/investment/providers.py, channels/web/{app.py,static/*},
  tests/test_investment_providers.py, deploy/backup-from-nas.sh,
  deploy/com.hanserautisch.investment-backup.plist (neu). (launchd-Agent + ~/LUNA-Backups ausserhalb des Repos.)

## [2026-06-28 15:40] — Claude Code (Investment-Datenhaltung: All-Time-Historie + Off-NAS-Backup)
- **Was:** Sichergestellt, dass die Investment-Daten **vollstaendig + dauerhaft** sind (CEO-Anliegen „nichts
  darf verloren gehen"): (1) **Auswertungen lesen die KOMPLETTE Historie** -- `InvestmentStore.list`
  Default-Limit von 500 auf praktisch unbegrenzt; bestaetigt append-only/event-sourced (nur `"a"`-Schreiben,
  nichts wird ueberschrieben/geloescht). (2) **`store.historie()`** (All-Time-Zaehlung je Tabelle + Zeitraum) ->
  in `/api/investment` + Investment-App sichtbar („Historie (append-only): N Einträge…"). (3)
  **`deploy/backup-from-nas.sh`** -- zieht eine zeitgestempelte Off-NAS-Kopie ALLER Live-Stores (investment,
  antraege, research, notifications, agenda, aktivitaet, watch, brain, kosten, memory) auf den Mac; live
  getestet (9 Stores, 3.969 Events gesichert). `backups/` gitignored. (4) **governance/investment.md** um
  „Datenhaltungs-Garantie" erweitert (append-only, Basis-Preis je Prognose, Backup, Supabase als durables Ziel).
- **Warum:** CEO fragte, ob alle Investment-Daten gespeichert werden + eine All-Time-Historie existiert. Antwort:
  ja (append-only), gehaertet um Komplett-Reads + Sichtbarkeit + Off-NAS-Backup. **Durables Ziel bleibt
  Supabase** (Roadmap, noch nicht verdrahtet). Cache ?v=13. Suite 201/201.
- **Betroffen:** orchestrator/investment/store.py, channels/web/{app.py,static/*}, deploy/backup-from-nas.sh
  (neu), governance/investment.md, .gitignore.

## [2026-06-28 15:10] — Claude Code (Detailansicht-Plus + Investment Phase 3 gestartet)
- **Was:** (1) **Detailansicht angereichert:** RSI (Alpha Vantage, mit Label ueberkauft/ueberverkauft/neutral),
  Links-Sektion (Unternehmens-Website, SEC-Filings/EDGAR, TradingView-Chart), Krypto: Rang + 24h-Volumen.
  MarketData.aktie_rsi + crypto_detail (rang/volumen); engine.detail um rsi/links erweitert. Live verifiziert
  (AAPL RSI 41.3 neutral + 3 Links; Apple-Profil). (2) **Phase 3 gestartet -- Walk-forward-Track-Record:**
  Wochenprognose speichert jetzt Basis-Preis + Asset; neu `engine.scorecard_aktualisieren` (faellige Prognosen
  >7T gegen aktuellen Kurs auswerten -> Actual = Wochen-Rendite %, Anomalie-Meldung bei starker Abweichung),
  scorecard() um mittleren Betrag erweitert. Taeglich im Investment-Loop ausgewertet. Sichtbar: Scorecard in
  /api/investment + Investment-App (Track-Record) + Dashboard-Panel (Trefferquote) + LUNA-Tool
  `investment_scorecard`. Cache ?v=12. Suite **201/201**.
- **Warum:** CEO: Detailansicht anreichern + Phase 3 starten. Phase 3 = advisory laufen lassen und
  Track-Record/Scorecard sammeln (Vertrauensbasis); Paper-Modus (Alpaca) bleibt GATE C. Hinweis:
  Alpha-Vantage-Free ~25 Calls/Tag -> RSI im Detail ist best-effort (faellt sonst weg).
- **Betroffen:** orchestrator/investment/{providers,engine,store}.py, channels/telegram/bot.py,
  channels/web/{app.py,static/*}, core/hoa_tools.py, tests/test_investment_engine.py, INVESTMENT_ROADMAP.md.

## [2026-06-28 14:40] — Claude Code (Investment Phase 2 Rest: anklickbare Details + Auto-Screen)
- **Was:** (1) **Anklickbare Ergebnisse:** Shortlist-Zeilen + Vorschlags-Karten sind klickbar -> **Detail-
  Fenster** mit Infos. Neu in MarketData: `aktie_profil` (Finnhub profile2: Name/Branche/Marktkap./Boerse/
  Land/Web), `aktie_news` (company-news), `crypto_detail` (CoinGecko /coins/{id}: Preis/Marktkap./ATH/ATL/
  Beschreibung/Homepage). `InvestmentEngine.detail(symbol, asset)` aggregiert; Endpunkt `/api/investment/detail`;
  Frontend `openInvestDetail` (Aktie: Profil+Quote+News, Krypto: Infos), `.klick`-Styling. Live verifiziert:
  Klick auf SDOT -> „Sadot Group Inc · Food Products · NASDAQ · +247% · Hoch/Tief"; Apple/Bitcoin-Details OK.
  (2) **Auto-Screen-Loop (Rest Phase 2):** `_start_investment_loop` im Bot -- werktags 16:00 DE ein Markt-Screen
  -> Risk-gepruefte Vorschlaege + Alert ueber Notifier; montags 09:00 Wochenprognose. **Default AUS**, Aktivierung
  via `INVESTMENT_AUTO_SCREEN=1` (Autonomie-Stufe L1: nur Melden, keine Trades; dedup ueber Store-Datum).
  Cache ?v=11. Suite **200/200**.
- **Warum:** CEO: „Rest Phase 2" + Ergebnisse anklickbar mit Detailinfos. Damit ist Phase 2 vollstaendig
  (advisory). Naechstes: Phase 3 (Track-Record sammeln, dann Paper-Modus GATE C).
- **Betroffen:** orchestrator/investment/{providers,engine}.py, channels/telegram/bot.py, channels/web/{app.py,
  static/*}, tests/test_investment_engine.py, INVESTMENT_ROADMAP.md.

## [2026-06-28 14:00] — Claude Code (Investment Phase 2 — die drei Schleifen, advisory)
- **Was:** CIO-Engine + Risk-Agent gebaut und in LUNA verdrahtet (advisory, **keine Trades**):
  **`orchestrator/investment/risk.py`** (`RiskAgent` -- regelbasierter Checker: Label konservativ/spekulativ,
  Veto bei Extrem-Bewegung >=80%, Nachschaerfung bei Konfidenz <0.4, max. Positionsgroesse) +
  **`orchestrator/investment/engine.py`** (`InvestmentEngine`: `markt_screen` [FMP-Gewinner + CoinGecko-Krypto
  -> sortierte Shortlist], `vorschlag`/`screen_und_vorschlagen` [Maker -> Risk-Checker -> nur Freigegebene
  gespeichert/gemeldet], `wochenprognose`+`scorecard` [walk-forward]). **LUNA-OS:** App + Dashboard-Panel
  **Investment** + Endpunkte `/api/investment` (GET status/shortlist/vorschlaege), `/screen`, `/watchlist`.
  **LUNA-Tools:** investment_status/investment_screen/investment_vorschlaege/watchlist_hinzufuegen +
  ToolContext.investment + _build_ctx (Notifier-Alerts -> Telegram) + System-Prompt (advisory-Hinweis). Cache ?v=10.
- **Warum:** CEO „Phase 2 starten". **Live verifiziert** (echte Keys): Markt-Screen liefert reale Shortlist
  (LCDL +32%, AAPL-Quotes, BTC/ETH), Risk-Agent **vetoed Extrem-Mover** (SDOT +247% etc.) und gibt moderatere
  als „spekulativ, max 1-2%" frei; LUNA-OS-Panel + Tools getestet. Suite **199/199** (10 Engine/Risk-Tests).
  **Offen:** Auto-Schedule (taeglicher Screen ueber WatchScheduler) + Wochenzyklus-Automatik.
- **Betroffen:** orchestrator/investment/{risk,engine}.py (neu), tests/test_investment_engine.py (neu),
  orchestrator/core/{hoa_tools,hoa_conversation}.py, channels/telegram/bot.py, channels/web/{app.py,static/*},
  INVESTMENT_ROADMAP.md.

## [2026-06-28 13:30] — Claude Code (Investment GATE B bestanden + FMP-Fix /stable)
- **Was:** CEO hat die 3 gratis Keys (FINNHUB/ALPHAVANTAGE/FMP) in beide .env (Mac+NAS) eingetragen. Live vom
  Mac verifiziert (ohne Key-Werte auszugeben): **CoinGecko** (BTC/EUR), **Finnhub** (AAPL-Quote), **Alpha
  Vantage** (RSI) OK. **FMP** gab 403 -> Ursache: FMP hat auf die neue **`/stable/`-API** umgestellt, die alten
  `/api/v3/`-Endpunkte sind fuer neue Free-Keys gesperrt. Fix: `screener_gewinner` nutzt jetzt
  `/stable/biggest-gainers` -> live OK (Top-Gewinner geliefert). **GATE B bestanden.** SEC EDGAR optional offen
  (braucht nur SEC_EDGAR_USER_AGENT-Kontaktzeile).
- **Warum:** Datenschicht der Investment-Abteilung live (advisory, keine Trades). Naechstes: Phase 2
  (die drei Schleifen + Verdrahtung CIO/Risk-Agent in den Orchestrator + Investment-Panel im LUNA-OS).
- **Betroffen:** orchestrator/investment/providers.py (FMP /stable), INVESTMENT_ROADMAP.md.

## [2026-06-28 13:10] — Claude Code (Investment Phase 1 — Datenschicht ohne Keys, Mock-getestet)
- **Was:** Investment-Datenanbindung + Speicher gebaut, **so weit ohne API-Keys moeglich** (Self-Checks gegen
  Mock): **`orchestrator/investment/providers.py`** -- `MarketData`-Fassade ueber 5 Provider (CoinGecko,
  SEC EDGAR, Finnhub, Alpha Vantage, FMP) im **Capability-Muster**: liest Keys aus `.env`, liefert **Fall-B**
  (kein Crash/keine Kosten) ohne Key, HTTP injizierbar (Tests ohne Netz). `provider_status()`/`fehlende_keys()`
  fuer GATE B. **`orchestrator/investment/store.py`** -- `InvestmentStore` (event-sourced JSONL, dateibasierter
  Stand-in fuer Supabase `inv_*`: watchlist/screening/forecasts/actuals/scorecard/suggestions/mode/positions;
  Modus default **advisory**; leck-geschuetzt). 15 neue Tests (Mock), Suite **189/189**. `investment/log.jsonl`
  gitignored + vom NAS-Sync ausgeschlossen.
- **Warum:** CEO: „mach weiter bis du die Keys brauchst". Live-Anbindung wird erst durch gratis Keys aktiv
  (**GATE B**). CoinGecko + SEC EDGAR sind keyless; Finnhub/Alpha Vantage/FMP brauchen je einen gratis Key.
  **Keine Trades, keine Kosten.** Noch nicht in den Orchestrator/LUNA-Tools verdrahtet (Phase 2).
- **Betroffen:** orchestrator/investment/{__init__,providers,store}.py,
  orchestrator/tests/{test_investment_providers,test_investment_store}.py, INVESTMENT_ROADMAP.md, .gitignore,
  deploy/sync-to-nas.sh.

## [2026-06-28 12:45] — Head of Agents / Claude Code (Investment Phase 0 — GATE A, CEO-freigegeben)
- **Was:** Investment-Abteilung Phase 0 angelegt (nach CEO-Freigabe GATE A):
  **`agents/16_cio.md`** (Chief Investment Officer, Status **Entwurf**, advisory-only, keine autonomen Trades) +
  **`agents/16a_risk-agent.md`** (Risk-Agent, Status **aktiv** — erster aktiver Unter-Agent ueberhaupt,
  Pflicht-Gegenpruefer/Checker mit Veto, auf ausdrueckliche CEO-Anweisung von Anfang an aktiv) +
  **`governance/investment.md`** (Modi advisory/paper/live + GATES, Risiko-Limits-Platzhalter, Freigabe-/
  Eskalations-Regeln, Maker/Checker). **REGISTRY.md** + **organigramm.md** um CIO (16) und Risk-Agent (16a)
  ergaenzt; INVESTMENT_ROADMAP.md Phase 0 = erledigt.
- **Warum:** CEO-Anweisung „GATE A freigegeben; Risk-Agent als eigener aktiver Unter-Agent von Anfang an".
  Charta-Anlage gemaess AGENTS.md 3.3 (Diff gezeigt + CEO bestaetigt). **Keine** Datenanbindung, keine Keys,
  keine Trades — reine Governance-Grundlage. Naechstes: Phase 1 (gratis Daten, GATE B).
- **Betroffen:** agents/16_cio.md (neu), agents/16a_risk-agent.md (neu), governance/investment.md (neu),
  agents/REGISTRY.md, governance/organigramm.md, INVESTMENT_ROADMAP.md.

## [2026-06-28 12:25] — Claude Code (Loop Engineering als Governance-Regel uebernommen)
- **Was:** Neues lebendes Steuerungsdokument **`governance/autonomie-stufen.md`** -- macht die aus „Loop
  Engineering" (cobusgreyling, MIT) uebernommenen Konzepte **verbindlich**: Autonomie-Treppe **L1→L2→L3**
  (Report→Assisted→Unattended, Start immer L1, Stufenwechsel = CEO-Tor), **Maker/Checker** (ab L2),
  **Kosten je Schleife** (CFO), + Checkliste fuer neue autonome Schleifen. Referenziert aus
  `governance/orchestrierung.md` (neuer §12) und `governance/README.md`; INVESTMENT_ROADMAP.md §10 auf
  „uebernommen" aktualisiert. **Kein** Code-/CLI-Import (npm-CLIs zielen auf Coding-Agenten; LUNA hat die
  Bausteine bereits).
- **Warum:** CEO-Anweisung, das Loop-Engineering-Konzept zu uebernehmen, bevor Phase 0 der Investment-Roadmap
  startet. Reine Governance-Doku; AGENTS.md bleibt kanonisch.
- **Betroffen:** governance/autonomie-stufen.md (neu), governance/orchestrierung.md, governance/README.md,
  INVESTMENT_ROADMAP.md.

## [2026-06-28 12:00] — Claude Code (UI.md Identitaet + loop-engineering-Pruefung + Investment-Roadmap)
- **Was:** (1) **UI.md** ergaenzt: neuer Abschnitt „1a. Feste Identitaet (nicht entfernen)" -- der **LUNA-Orb**
  (#luna-orb, idle/listening/speaking, audio-reaktiv) UND die deutsche **ElevenLabs-Stimme „Lola"**
  (voice_id SiMvlSW9cKKHDYT4BzOp, eleven_turbo_v2_5) sind als unveraenderliche Identitaet verankert; veralteten
  Orb-Hinweis korrigiert. (2) **cobusgreyling/loop-engineering geprueft** (MIT; Design-Philosophie + 3 npm-CLIs
  loop-init/audit/cost fuer Coding-Agenten/GitHub-Actions): Empfehlung = **kein Code-/CLI-Einbau** (falscher
  Runtime/Scope; LUNA hat das meiste schon: WatchScheduler=Scheduling, Second Brain=Skills, MCP=Connectors,
  delegate+Execution=Maker/Checker+Worktrees), aber **Konzepte uebernehmen** -- v. a. die Autonomie-Treppe
  L1->L2->L3 (= advisory->paper->live), Maker/Checker, Loop-Kostenbudget. (3) **INVESTMENT_ROADMAP.md** aus dem
  CEO-`Investment_Abteilung_Bauplan.md` abgeleitet: lebende Roadmap (CIO + Unter-Agenten, Modi advisory/paper/
  live mit GATES A–D, drei Kern-Schleifen, Daten/MCP, Supabase-Speicher, Governance, LUNA-Anbindung, Kosten,
  Loop-Engineering-Lehre). **Advisory-only, keine Trades, alles Geld = CEO-Tor.** Status: geplant.
- **Warum:** CEO-Auftrag: Orb+Lola in UI.md festschreiben; loop-engineering-Einbau pruefen; Investment-Plan in
  eine schrittweise Roadmap ueberfuehren. Reine Doku -- kein Code/Deploy noetig.
- **Betroffen:** UI.md, INVESTMENT_ROADMAP.md (neu).

## [2026-06-28 11:20] — Claude Code (Command-Center-Redesign im Jarvis-Stil + UI.md)
- **Was:** (1) **UI.md** als globales **Design-System** angelegt (Farb-Tokens, Typografie, Layout
  Sidebar/Topbar/Panel-Grid/Voicebar, Komponenten, Motion, Sprache, technische Regeln + Checkliste fuer neue
  Funktionen) -- damit alle neuen Features demselben Look folgen. (2) **LUNA-OS auf „Command Center"
  umgebaut** (CEO-Vorlage Jarvis-HUD): linke **Sidebar-Navigation** (mit Live-Counts, aktivem Cyan-Balken,
  Mobil-Menue), neue **Topbar** (System-Status, Datum/Uhr, Suche, LIVE), zentraler **AI-Core/Globe** mit dem
  audio-reaktiven Orb, **Panel-Grid** mit HUD-Eckwinkeln: AI Core Overview, Live Intelligence Feed (Meldungen),
  Active Agents, Mission Timeline (heutige Termine), Quick Commands, System Monitor (SVG-Gauges mit **echten**
  LUNA-Zahlen), Memory Insights, LLM/Provider-Status. Durchgehende **„TALK TO LUNA"-Leiste** (= toggleVoice).
  Die bestehenden App-**Fenster** (WinBox) bleiben und oeffnen aus Sidebar/Panels. Neuer Endpunkt
  **`/api/overview`** (Counts + Provider-Status aus .env + Agentenliste). Cache-Bust ?v=9.
- **Warum:** CEO: „bau dieses Jarvis-Command-Center-Design nach + halte unser Design global in einer UI.md
  fest". Echte Daten statt Mock (Antraege/Meldungen/Research/Wissen/Provider). Verifiziert im Preview
  (Desktop-Grid + Mobil mit Menue-Toggle, Nav oeffnet Fenster, Provider-Status live, keine Konsolenfehler),
  Suite 174/174.
- **Betroffen:** UI.md (neu), orchestrator/channels/web/app.py, .../static/{index.html,style.css,app.js}.

## [2026-06-28 11:00] — Claude Code (Second Brain + proaktive Tages-Insights)
- **Was:** Zwei neue Faehigkeiten (CEO-Wunsch nach OpenJarvis-Vorbild):
  (1) **Your Second Brain** -- durchsuchbare persoenliche Wissensbasis. Neues Modul `core/brain.py`
  (event-sourced JSONL, merken/suchen/vergessen, lexikalische Suche, Dedup, leck-geschuetzt). LUNA-Tools
  `brain_merken`/`brain_suchen`; `brain_suchen` sucht **quellenuebergreifend** (gemerktes Wissen + interne
  Stores [Research/Antraege] + -- falls verbunden -- Gmail + Drive, `_brain_suchen`-Foederation in hoa_tools).
  (2) **Jarvis Intelligent Feature: proaktive Tages-Insights** -- `core/insights.py` (Lagebild: offene
  Entscheidungen/Antraege, heutige Termine [Kalender live], ungelesene Mails [Gmail live], offene Tickets,
  Agenda; rein regelbasiert/token-frugal). LUNA-Tool `lagebild`; **ans Morgen-Briefing angehaengt** (proaktiv).
  ToolContext um `brain`/`insights` erweitert, in `_build_ctx` verdrahtet; LUNA-System-Prompt ergaenzt.
  **LUNA-OS:** neue Apps **Wissen** (durchsuchen inkl. Gmail/Drive + Wissen merken) und **Lagebild**
  (Tagesstand), Endpunkte `/api/brain` (GET/POST) + `/api/lagebild`. Cache-Bust ?v=8.
- **Warum:** CEO: „weiter mit Jarvis Intelligent Features und Second Brain". Verifiziert: Tests (brain 7/7,
  insights 4/4, Suite 174/174); Endpunkte live im Preview -- brain_suchen fand quellenuebergreifend sogar eine
  Drive-Datei, Lagebild fragte Gmail live ab; Wissen-/Lagebild-App rendern sauber, keine Konsolenfehler.
  Stores `brain/log.jsonl` gitignored + vom NAS-Sync ausgeschlossen.
- **Betroffen:** orchestrator/core/{brain.py,insights.py,hoa_tools.py,hoa_conversation.py},
  orchestrator/channels/telegram/bot.py, orchestrator/channels/web/{app.py,static/*},
  orchestrator/tests/{test_brain.py,test_insights.py}, .gitignore, deploy/sync-to-nas.sh.

## [2026-06-27 22:45] — Claude Code (Voice-LUNA: Barge-in + Jarvis-Visualisierung)
- **Was:** (1) **Barge-in/Unterbrechen (CEO-Feedback):** Orb antippen, waehrend LUNA spricht -> sie verstummt
  sofort (`stopAudio` ueber `BufferSource.stop()` -> onended loest die Sprech-Schleife, die danach automatisch
  wieder zuhoert); Status zeigt „Orb antippen zum Unterbrechen". (2) **Jarvis-Visualisierung:**
  **audio-reaktiver Orb** -- AnalyserNode im Audio-Graph treibt eine CSS-Variable `--energy`, der Orb pulsiert/
  glueht mit Lolas echter Stimme; **rotierender Reaktor-Ring** am Orb; **dezenter HUD-Scan-Sweep** ueber die
  Oberflaeche (#scan); Orb leicht groesser. prefers-reduced-motion respektiert. Cache-Bust ?v=7.
  (3) **ROADMAP:** Live-Voice-Stand dokumentiert; CEO-Wunsch-Cluster nach OpenJarvis-Vorbild geparkt --
  Complete Device Control (= Phase 17), Jarvis Intelligent Features, „Your Second Brain" (Wissensbasis/RAG,
  knuepft an Memory + Partner-/Akten-System).
- **Warum:** CEO: „kann LUNA nicht unterbrechen" + „Oberflaeche schoener/moderner, schau bei Jarvis".
  Verifiziert im Preview: Barge-in verstummt LUNA (Tap-Test), Reaktor-Ring/Scan/Energie-Glow sichtbar, keine
  Konsolenfehler, Suite 163/163. Echtes hands-free Barge-in (ohne Tap) braucht Echo-Cancellation (Pipecat) ->
  geparkt. Stand „Gespraech auf Mac+Safari laeuft" vom CEO bestaetigt.
- **Betroffen:** orchestrator/channels/web/static/{app.js,style.css,index.html}, ROADMAP.md.

## [2026-06-27 22:10] — Claude Code (Voice-LUNA Finetuning: Ton-Fix + Kontext-Anzeige + Satz-Streaming)
- **Was:** (1) **Ton-Fix (Hauptproblem „LUNA nicht hoerbar"):** Audio laeuft jetzt ueber einen
  **Web-Audio-Context, der beim Orb-/Gespraech-/Sende-Tap entsperrt wird** (`unlockAudio` in der Nutzer-Geste).
  Safari/iOS/Chrome erlauben Audio nur nach einer Geste -- vorher wurde `Audio.play()` still abgewiesen.
  Premium-Stimme (Lola) wird per `decodeAudioData` ueber den entsperrten Context gespielt; Browser-Stimme als
  Fallback. (2) **Kontext-Anzeige (CEO-Wunsch):** Fragen, die eine Ansicht betreffen („welche Anträge sind
  offen?", „wie viele Tickets?", „mein Budget?"), oeffnen jetzt **automatisch das passende Panel**
  (Auftraege/Research/Finanzen/Meldungen/Aktivität) UND LUNA erklaert die Daten gesprochen dazu
  (`panelFuerFrage`). Reine „zeig X"-Befehle bleiben kurz. (3) **Satz-fuer-Satz-TTS** (OpenJARVIS-Muster):
  Antwort wird in Saetze zerlegt, LUNA faengt frueher an zu sprechen (kuerzere Latenz). (4) **iOS:** wo der
  Browser keine Sprach-Eingabe kann (iOS Safari hat keine Web-Speech-Erkennung), bleibt der Knopf
  „🔊 Stimme aktivieren" + Tippen -> LUNA spricht trotzdem (Lola). Cache-Bust ?v=6.
- **Warum:** CEO-Feedback: Stimme auf Mac/iPhone/iPad nicht hoerbar + Kontext soll angezeigt statt nur als Text
  beantwortet werden; Anregung „schau bei OpenJARVIS". Uebernommen: Satz-Streaming + Intent->UI-Aktion.
  Verifiziert im Preview: Frage oeffnet Panel + LUNA antwortet mit echten Daten, inSaetze/panelFuerFrage
  korrekt, keine Konsolenfehler, Suite 163/163. Echte Tonausgabe nur auf Geraet mit Lautsprecher pruefbar.
  **Offen/empfohlen (next):** Sprach-EINGABE auf iPhone/iPad via Deepgram-STT (MediaRecorder -> /api/stt),
  da iOS Safari keine Web-Speech-Erkennung hat.
- **Betroffen:** orchestrator/channels/web/static/{app.js,index.html}.

## [2026-06-27 21:35] — Claude Code (LUNA-OS-Stimme: Lola)
- **Was:** LUNA-OS spricht jetzt mit der deutschen ElevenLabs-Stimme **„Lola"**
  (voice_id SiMvlSW9cKKHDYT4BzOp, aus voice/voices.py per Name aufgeloest -> keine Magic-ID im Code);
  per `.env` `LUNA_OS_VOICE_ID` weiterhin ueberschreibbar. Beeinflusst nur den LUNA-OS-Orb, nicht den
  separaten Voice-Kanal (dessen Default/Auswahl bleibt unveraendert).
- **Warum:** CEO-Wahl -- „Lola" wie frueher genutzt. Lola-ID-Aufloesung verifiziert; /api/tts-Integration
  war bereits gruen (nur voice_id geaendert -> kein erneuter ElevenLabs-Call). Suite 163/163.
- **Betroffen:** orchestrator/channels/web/app.py.

## [2026-06-27 21:15] — Claude Code (LUNA-OS: Live-Voice-LUNA am Orb mit ElevenLabs-Stimme)
- **Was:** Der Mond-Orb ist jetzt die **sprechende Live-LUNA** (CEO-Prioritaet vor dem Tipp-Chat). Orb antippen
  -> freihaendiges Sprach-Gespraech: Browser-Ohren (Web Speech `SpeechRecognition`, de-DE, kontinuierliche
  Hoer-/Antwort-Schleife) + **ElevenLabs-Premium-Stimme** fuer LUNAs Antworten. Backend:
  (1) **`/api/chat` nutzt jetzt die VOLLE LUNA** (`HoaConversation` mit Persona + Tools + Verlauf, persistente
  Sitzung) statt einfachem Gemini-Call -- der Orb spricht mit derselben LUNA wie Telegram (Fallback: einfacher
  Persona-LLM ohne Anthropic-Key). (2) **Neuer `/api/tts`** -> ElevenLabs (`eleven_turbo_v2_5`, Stimme aus
  voice/voices.py `get_selected_voice_id`, Default „Niklas"/Jarvis; via `LUNA_OS_VOICE_ID` ueberschreibbar);
  liefert MP3, 503/502 -> Frontend faellt auf Browser-Stimme zurueck. ElevenLabs-Key aus .env (`_secret`,
  unabhaengig vom Anthropic-Zugang). Frontend: Voice-Leiste mit „Gespraech starten/beenden", Orb-Klick =
  toggleVoice, Barge-/Stopp ueber Orb; Kontext-Sprachbefehle bleiben. Tipp-Chat als Rueckfallebene. Cache-Bust ?v=5.
- **Warum:** CEO: „ueber den Orb die LIVE-LUNA, die sprachlich antwortet und mit der ich ein Gespraech fuehre"
  hat Prioritaet; Stimmenwahl = ElevenLabs (vorhandenes Abo). Verifiziert im Preview: `/api/tts` liefert MP3
  (ElevenLabs), `/api/chat` antwortet als echte LUNA mit Tool-Daten („0 offene Auftraege"), Voice-Fenster
  rendert, keine Konsolenfehler. Mikrofon-Aufnahme nur auf echtem Geraet/HTTPS testbar. Suite 163/163.
- **Betroffen:** orchestrator/channels/web/app.py, .../static/{app.js,style.css,index.html}.

## [2026-06-27 20:30] — Claude Code (LUNA-OS V3 deployt + HTTPS/externer Zugriff LIVE)
- **Was:** (1) V3-Commits (b94a1d3 Features, dbda8f3 Umlaute/Design/Sprach-Kontext) per sync-to-nas.sh auf den
  NAS deployt (Code volume-gemountet -> Frontend sofort live; luna-os-Container vom CEO in DSM neu gestartet
  fuer app.py). (2) **HTTPS + externer Zugriff jetzt LIVE:** Synology Reverse-Proxy
  (HTTPS os.hanserautisch.synology.me:443 -> HTTP localhost:8765, WebSocket-Header), Let's-Encrypt-Zertifikat
  `luna-encrypt` (bis 25.09.2026) dem Dienst zugeordnet, **Fritz!Box 7530 AX Portfreigabe TCP 443->443**.
  Ergebnis: **ein Lesezeichen `https://os.hanserautisch.synology.me` funktioniert im Heim-WLAN
  (NAT-Loopback) UND unterwegs (Mobilfunk)**. Verifiziert (curl ueber oeffentliche IP + normale DNS:
  HTTP 401 + TLS verifiziert). Schaltet das Mikrofon/Sprach-Eingabe frei (secure context).
- **Warum:** CEO-Anweisung „mach alles fertig + lotse mich durch externen Zugriff". Die DSM-/Router-
  Sicherheitseinstellungen + Login hat der CEO selbst ausgefuehrt (System-/Sicherheitseinstellungen bleiben
  beim Menschen); der Assistent hat live gelotst, read-only mitgelesen und technisch verifiziert.
- **Betroffen:** ROADMAP.md (Status-Tabelle + Phase-16-Block); NAS-Deployment (luna-os); Infrastruktur
  (DSM Reverse-Proxy/Zertifikat, Fritz!Box-Portfreigabe -- ausserhalb des Repos).

## [2026-06-27 19:45] — Claude Code (Roadmap-Pflege: HTTPS als CEO-Schritt + Backlog)
- **Was:** ROADMAP.md aktualisiert: V3-Stand fortgeschrieben (Umlaute/Design/Sprach-Kontextbefehl ✅,
  beide Commits lokal aber noch nicht deployt). **HTTPS** als **manueller CEO-Schritt** markiert
  (Reverse-Proxy/Zertifikat/Firewall = System-/Sicherheitseinstellungen + DSM-Login -> fuehrt der CEO selbst
  aus; Assistent lotst/liest read-only mit/verifiziert, fuehrt aber keine Sicherheitseinstellungen in seinem
  Namen aus). „Alles andere fuer spaeter" geparkt: echtes Mikrofon nach HTTPS, agentische
  Voice-Kontext-Steuerung (Panels/Visualisierung), „Mehr Info" mit eigener Session, Mobil-Feinschliff, TTS-
  Feintuning. Backlog ergaenzt: **Cutter Stil-Analyzer** (aus Profi-Videos „lernen" = Stil-Profil
  extrahieren -> ffmpeg-Pipeline steuern; echter Edit-Style-Transfer bleibt out-of-scope).
- **Warum:** CEO-Anweisung, HTTPS umzusetzen + „alles andere auf der Roadmap fuer spaeter vermerken". HTTPS-
  Sicherheitseinstellungen kann der Assistent regelkonform nicht selbst vornehmen -> als CEO-Schritt
  dokumentiert; uebrige Punkte als Roadmap-Backlog festgehalten.
- **Betroffen:** ROADMAP.md.

## [2026-06-27 19:15] — Claude Code (LUNA-OS: Umlaute + futuristisches Design + Sprach-Kontext)
- **Was:** LUNA-OS-Oberflaeche ueberarbeitet:
  (1) **Echte Umlaute ueberall** (CEO-Wunsch): UI-Beschriftungen mit ä/ö/ü/ß (Aufträge, Aktivität,
  Löschen, „löschen?", Finanz-Labels) in index.html/app.js; nutzersichtbare Strings in app.py
  (LUNA-Persona, „nicht verfügbar", „Kein Modell verfügbar", „Login nötig"). Code-Bezeichner bleiben ASCII.
  (2) **Futuristisches Zukunftsdesign** (Sci-Fi-HUD): style.css komplett neu -- animiertes Sternenfeld +
  perspektivisches Neon-Gitter + Aurora-Glow als Hintergrund, Glasmorphismus-Fenster (WinBox `.modern`
  umgestylt), Neon-Cyan/Violett-Akzente, gluehende Buttons/Badges, Mono-Akzentschrift, holografisches Dock.
  (3) **Sprach-/Text-Kontextbefehl** (CEO-Anforderung „auf Sprachanweisung Kontext zeigen, geraeteuebergreifend"):
  client-seitiger Parser im LUNA-Chat erkennt „zeig/öffne <app>" und blendet die passende App
  (Aufträge/Meldungen/Aktivität/Research/Finanzen) ein -- per Tippen UND Mikrofon (Web Speech API), auf
  Handy/Rechner/iPad. Asset-Cache-Bust ?v=4. viewport-fit=cover + safe-area fuer Notch-Geraete.
- **Warum:** CEO-Anweisungen (2026-06-27): Oberflaeche immer mit Umlauten, futuristisches Design,
  Sprach-gesteuerte Kontextanzeige auf allen Geraeten. Zusaetzlich finance/kosten-log.jsonl gitignored
  (Runtime-Store). Verifiziert im Preview (Desktop + mobil 375px): Design, Umlaute, Kontextbefehle
  (5 Faelle inkl. Negativfall). Suite 163/163.
- **Betroffen:** orchestrator/channels/web/static/{style.css,app.js,index.html}, .../app.py, .gitignore.

## [2026-06-27 18:30] — Claude Code (Phase 16 V3: Rest umgesetzt)
- **Was:** LUNA-OS V3 vervollstaendigt (ausser HTTPS, das bleibt ein DSM-GUI-Schritt):
  (1) **Antrags-Detailansicht** -- neuer Endpoint `GET /api/antraege/{id}` mit vollem Verlauf/Evidenz;
  Klick auf Antrags-Titel oder „Details"-Button oeffnet ein Detail-Fenster (Status, Beschreibung,
  Betroffen, Verlaufs-Schritte).
  (2) **Mobil-Feinschliff** -- WinBox-Fenster fuellen auf schmalen Screens (<=640px) den Bildschirm und
  lassen Top-Bar + Dock frei (Chat-Eingabe nicht mehr hinterm Dock); Dock ueber volle Breite, groessere
  Touch-Buttons (CSS-Media-Query + responsives `winGeom()`).
  (3) **Mikrofon-Eingabe + TTS am Orb** -- Web Speech API (browser-nativ): 🎤-Knopf diktiert in den Chat
  (de-DE, schickt gesprochenen Satz direkt ab, Orb zeigt „listening"), 🔊-Toggle laesst LUNA Antworten
  vorlesen (SpeechSynthesis). Funktioniert auf localhost/HTTPS -> bereit fuer den HTTPS-Schalter.
  (4) **„Mehr Info" agentisch via voller HoaConversation** -- statt einfachem Gemini-Call laeuft jetzt die
  echte Tool-Schleife (delegate an CTO/CFO, recherche_beauftragen) ueber die wiederverwendete
  Telegram-Verdrahtung (`_build_ctx`); sicherer Fallback auf den einfachen LLM-Call, wenn kein
  Anthropic-Key/Abhaengigkeiten da sind. Asset-Cache-Bust `?v=3`. `__main__` liest jetzt `PORT` (Preview).
- **Warum:** CEO-Anweisung „erst den Rest von V3 umsetzen" (Phase 16). Verifiziert im Browser-Preview
  (Desktop + mobil 375px): Detailansicht, Karte/Buttons, Chat-Eingabe mit Mic/TTS, agentische Bewertung
  (lokal real durchgelaufen: delegate -> Researcher-Brave-Suche -> CEO-Bewertung). Suite 163/163.
- **Betroffen:** orchestrator/channels/web/app.py, .../__main__.py, .../static/{app.js,index.html,style.css},
  .claude/launch.json (autoPort fuer Preview).

## [2026-06-27 17:00] — Claude Code (Roadmap: Phase 17 + Doku-Pflege fuer neuen Chat)
- **Was:** ROADMAP.md um **Phase 17** ergaenzt: „LUNA bedient auf Anweisung den Rechner" (Computer-Use --
  Apps/Maus/Tastatur steuern; Wege: Claude Computer-Use oder lokale macOS-Automatisierung; **harte
  Governance**: nur auf Anweisung, CEO-Tor, Least-Privilege, Not-Aus, Audit; Backlog). V3-Teilstand der
  Phase 16 dokumentiert (Chat-Panel + agentisches Mehr-Info erledigt; HTTPS offen). Einstiegs-Memory
  `projekt-status.md` auf Stand 2026-06-27 gebracht (Phasen 5-16 + Cutter + LUNA-OS live), damit ein neuer
  Chat sauber startet (Kontextfenster fast voll).
- **Warum:** CEO-Anweisung: Computer-Steuerung in die Roadmap; alle Start-Dokumente fuer einen frischen Chat
  pflegen.
- **Betroffen:** ROADMAP.md, projekt_changelog.md; Memory projekt-status.md + MEMORY.md.

## [2026-06-27 16:30] — Claude Code (LUNA-OS: animierter Orb + Chat + agentisches Mehr-Info)
- **Was:** (1) **Animiertes LUNA-Mond-Symbol** in der Top-Bar mit drei Zustaenden: idle (atmende Mondsichel),
  **listening** (cyan, Ringe nach innen = LUNA hoert zu), **speaking** (gruen, Ringe nach aussen + Puls = LUNA
  spricht). Klick -> LUNA-**Chat-Fenster**. (2) **/api/chat** (LUNA-Persona ueber Gemini, leck-geschuetzt);
  Antwort laeuft als Schreibmaschine ein, Orb zeigt solange 'speaking'. (3) **Agentisches 'Mehr Info'**:
  mehr-info ruft jetzt einen LLM-Berater (CTO/CFO-Sicht), der den Antrag sofort kurz bewertet -> als Meldung
  + Research-Ticket. (4) Asset-Versionierung (?v=2) gegen Browser-Cache. Lokal verifiziert: Chat antwortet,
  Bewertung sinnvoll, alle 3 Orb-Zustaende gerendert (Screenshots). Deployt auf NAS.
- **Warum:** CEO will ein lebendiges LUNA-Symbol (Zuhoeren/Sprechen sichtbar) + Chat im OS.
- **Betroffen:** orchestrator/channels/web/app.py + static/{index.html,style.css,app.js}.
- **Hinweis:** Echte Sprach-Eingabe (Mikrofon) braucht HTTPS (Browser-Sicherheitskontext) -> mit V3
  (Reverse-Proxy). Aktuell Text-Chat; die Orb-Zustaende sind schon voll funktionsfaehig.

## [2026-06-27 15:30] — Claude Code (LUNA-OS V2: NAS-Deploy + Login)
- **Was:** LUNA-OS auf den NAS gebracht. (1) **HTTP-Basic-Login** in `channels/web/app.py` (LUNA_OS_USER/LUNA_OS_PASSWORD aus .env; nur aktiv wenn Passwort gesetzt -> lokal offen, NAS geschuetzt). (2) `deploy/Dockerfile`: fastapi==0.138 + uvicorn==0.49 ergaenzt. (3) `docker-compose.yml`: zweiter Dienst **luna-os** (gleiches Image+Volume+env_file, Befehl `python -m orchestrator.channels.web`, LUNA_OS_HOST=0.0.0.0, Port 8765:8765). (4) Login (User ceo, zufaelliges Passwort) in NAS-.env gesetzt (nicht im Chat). Deployt (--build). Verifiziert: luna-os Up, ohne Login 401, mit Login 200, Statik 200, Bot weiter gesund. **Zugriff LAN: http://192.168.178.129:8765**.
- **Warum:** taegliche Arbeitsoberflaeche muss 24/7 ohne Terminal erreichbar sein.
- **Betroffen:** orchestrator/channels/web/app.py, deploy/Dockerfile, deploy/docker-compose.yml, NAS-.env. Roadmap Phase 16 -> LIVE.
- **Offen (V3):** HTTPS + extern (Synology Reverse-Proxy/Let's Encrypt), Chat-Panel, Mehr-Info agentisch.

## [2026-06-27 14:30] — Claude Code (Phase 16: LUNA-OS MVP)
- **Was:** Neue Web-Arbeitsoberflaeche **LUNA-OS** (Desktop-aehnliches Browser-OS) -- Phase-16-MVP. Modul `orchestrator/channels/web`: FastAPI-Backend (`app.py`) ueber den echten Stores + statisches Frontend mit **WinBox.js** (Desktop, Top-Bar, Dock, draggbare Fenster). Apps: **Auftraege** (Live-Inbox offener Antraege als Evidenz-Karten mit Buttons Freigeben/Ablehnen/Loeschen/Mehr-Info), Meldungen, Aktivitaet, Research, Finanzen. Aktionen ueber die echten Antraege-Store-Methoden (Changelog + CEO-Tor); Mehr-Info erstellt ein Research-Ticket. Live-Updates per SSE (mtime). `core/antraege.py`: Status **geloescht** ergaenzt (auditierbar). Lokal verifiziert: Screenshot + alle 4 Aktionen HTTP 200; Orchestrator-Suite 163/163. Start: `python -m orchestrator.channels.web`. WinBox vendored (Apache-2.0). Recherche: AG-UI/Approval-Dashboard-Muster.
- **Warum:** CEO will eine taegliche, OS-aehnliche Live-Arbeitsoberflaeche zum Bearbeiten von Antraegen.
- **Betroffen:** orchestrator/channels/web/* (neu), orchestrator/core/antraege.py, .gitignore, .claude/launch.json. Roadmap Phase 16 -> in Umsetzung.
- **Offen (V2):** NAS-Deployment (fastapi/uvicorn ins Image, HTTPS, Auth nur CEO), LUNA-Chat-Panel, Mehr-Info wirklich agentisch.

## [2026-06-27 13:30] — Claude Code (Roadmap: UI-Phase + Cutter nach hinten)
- **Was:** ROADMAP.md aktualisiert. (1) Neue **Phase 16 — LUNA Live-Arbeitsoberflaeche (Browser-Dashboard)**, HOHE Prioritaet: taegliche Arbeitsoberflaeche mit priorisierter Antrags-Inbox, Buttons (Freigeben/Ablehnen/Loeschen/Agent-Recherche), Echtzeit-Updates (WebSocket/SSE, AG-UI-Muster), LUNA-Chat + Panels; ueber bestehende Tools/Antrags-Logik (Changelog+CEO-Tor bleiben). (2) **Cutter (Phase 15) nach hinten** -- CEO: noch nicht intelligent genug; ffmpeg-Ansatz regelbasiert; Engine-Kandidat fuer 'intelligenter': **OpenCut** (Headless-Modus + Editor-API + MCP-Server, MIT, im Umbau). (3) Markt-Recherche (AG-UI, Agent-Inbox/Approval-Dashboards) in die Phase eingearbeitet.
- **Warum:** CEO-Anweisung: Browser-Oberflaeche als echte taegliche Arbeitsumgebung priorisieren; Cutter spaeter intelligenter machen.
- **Betroffen:** ROADMAP.md (Status-Tabelle, Header, Phase 15 + neue Phase 16).

## [2026-06-27 13:00] — Claude Code (Cutter: randlos + fester Ueberblenden-Uebergang)
- **Was:** (1) **Schwarzrand-Entfernung**: `ffmpeg_ops._schwarzrand_crop` erkennt eingebrannte schwarze Balken per cropdetect und schneidet sie VOR dem Crop-to-Fill weg -> Inhalt fuellt 9:16 garantiert randlos (verifiziert: Letterbox-Clip -> ohne Balken). (2) **Fester Uebergang**: immer weiches Ueberblenden (xfade transition=fade) fuer ALLE Schnitte statt rotierender Effekte. segment_normalisieren bekam Param randschnitt. Tests 6/6.
- **Warum:** CEO: keine schwarzen Raender (Inhalt muss fuellen), immer Ueberblenden als fester Effekt.
- **Betroffen:** cutter/ffmpeg_ops.py, cutter/README.md.

## [2026-06-27 12:30] — Claude Code (Cutter: Telegram-Groessenlimit)
- **Was:** `ffmpeg_ops.auf_groesse_begrenzen` -- Reel wird nach dem Schnitt auf <48 MB re-encodet, falls groesser (Telegram-Bot-sendVideo-Limit = 50 MB). In Pipeline eingehaengt. Grund: echter Test mit dem TEST-Ordner (7 HSV-Clips 1080p/4K -> 5 verwendet, 32s) ergab 57 MB -> Telegram-Versand schlug fehl. Nach Fix 46 MB, erfolgreich gesendet. Crop-to-Fill + Uebergaenge auf echtem Material visuell bestaetigt.
- **Warum:** Reels (v. a. aus 4K-Quellen) ueberschreiten sonst das Telegram-Limit.
- **Betroffen:** cutter/ffmpeg_ops.py, cutter/pipeline.py. Tests 6/6.

## [2026-06-27 12:00] — Claude Code (Cutter professioneller)
- **Was:** Cutter-Qualitaet deutlich verbessert. (1) **Crop-to-Fill** statt Blur-Balken: Querformat wird vergroessert + mittig beschnitten -> fuellt 9:16 ganz, KEIN Strecken (frueher wirkten Clips gestreckt/mit Balken). (2) **Effekte:** dezenter Farb-Grade (eq: Kontrast/Saettigung) + sanfter Ken-Burns-Zoom (zoompan) auf B-Roll. (3) **Uebergaenge:** weiche xfade-Uebergaenge (Crossfade/Smooth-Slides, rotierend) + acrossfade fuer Audio, statt harter Aneinanderreihung. Neue ffmpeg_ops: _vertikal_filter, zusammenfuegen_xfade, dauer_von; Pipeline nutzt xfade-Assembly (Fallback harte Schnitte). Visuell verifiziert (Crop-to-Fill + Crossfade-Frames), Tests 6/6. Watcher-Dienst neu gestartet.
- **Warum:** CEO: 'professioneller machen' -- nichts strecken, Uebergaenge + Effekte.
- **Betroffen:** cutter/ffmpeg_ops.py, cutter/pipeline.py, cutter/README.md.
- **Hinweis (ehrlich):** ffmpeg hat keine manuellen Key-Frames wie ein GUI-Editor; Bewegung via zoompan/xfade (programmatisch). 'Bester Ausschnitt' bei B-Roll = aktuell mittig/zeitlich ~20%; subjekt-bewusster Crop waere ein Upgrade.

## [2026-06-27 11:30] — Claude Code (Cutter: Untertitel aus)
- **Was:** Untertitel im Cutter standardmaessig AUS (CEO-Wunsch). `schneide_ordner(untertitel=False)` Default; keine `.srt` mehr. Sprach-Erkennung (Whisper) bleibt INTERN fuer Silence-Trimmen + Gemini-Reihenfolge. CLI-Flag `--mit-untertitel` als Opt-in. Watcher-Dienst neu gestartet (laedt neuen Code).
- **Warum:** CEO will keine Untertitel.
- **Betroffen:** cutter/pipeline.py, cutter/__main__.py, cutter/README.md. Tests 6/6.

## [2026-06-27 11:00] — Claude Code (Cutter Agent V2: Autostart + Telegram)
- **Was:** Cutter Agent V2. (1) **Autostart**: launchd-LaunchAgent `cutter/com.hanserautisch.cutter.watch.plist`
  (PATH inkl. /opt/homebrew/bin fuer ffmpeg/whisper, RunAtLoad+KeepAlive) -- der Watcher startet bei jedem
  Login automatisch; installiert + geladen, laeuft. (2) **Telegram-Meldung**: `cutter/melden.py` schickt das
  fertige Reel als Video an den LUNA-Chat (gleiches Bot-Token, TELEGRAM_* aus .env); in watch.py eingebunden.
  Live verifiziert: Clips in ~/CutterInbox -> Dienst schneidet -> Reel in ~/CutterOutbox + per Telegram.
- **Warum:** CEO-Wunsch: unbeaufsichtigt (Mac anlassen) + LUNA meldet das Ergebnis aufs Handy.
- **Betroffen:** cutter/melden.py (neu), cutter/watch.py, cutter/com.hanserautisch.cutter.watch.plist (neu),
  cutter/README.md, ROADMAP.md (Phase 15 V1+V2). Senden an den CEO ist kein CEO-Tor; Instagram-Posten bleibt es.

## [2026-06-27 10:00] — Claude Code (Cutter Agent V1)
- **Was:** Neuer **Cutter Agent** (Paket `cutter/`): Ordner mit Clips -> automatisches 9:16-Instagram-Reel,
  lokal auf dem Mac, kostenlos, ohne externe Dienste. Module: `ffmpeg_ops` (probe/normalisieren/concat,
  9:16 mit Blur-Hintergrund, loudnorm), `transkription` (whisper.cpp lokal -> faster-whisper -> Deepgram ->
  leer), `pipeline` (Sprach-Erkennung je Clip, Sprech-Clips mit Untertiteln, B-Roll-Ausschnitt, Gemini-
  Reihenfolge), `watch` (unbeaufsichtigter Inbox/Outbox-Watcher), CLI (`python -m cutter <ordner>`). Auf dem
  Mac installiert: whisper.cpp (brew) + Modell `~/whisper-models/ggml-base.bin`. Untertitel als `.srt`
  (Einbrennen braucht ffmpeg mit libass -- aktuelles Build hat das nicht). Tests 6/6 (cutter/tests). ROADMAP
  um Phase 15 ergaenzt.
- **Warum:** CEO-Wunsch: Clips-Ordner -> Instagram-Schnitt ohne manuelle Arbeit. **palmier-pro geprueft und
  verworfen** (macOS-GUI-Editor, interaktiv, generiert nur neue Videos, keine Batch-Automatik). Keine neuen
  kostenpflichtigen Dienste noetig (FFmpeg + lokales Whisper + vorhandenes Gemini).
- **Betroffen:** cutter/ (neu: ffmpeg_ops.py, transkription.py, pipeline.py, watch.py, __main__.py,
  __init__.py, README.md, tests/test_cutter.py), ROADMAP.md. Instagram-Posten bleibt CEO-Tor.

## [2026-06-26 12:30] — Claude Code (Phase 14 + lebende Roadmap)
- **Was:** **Phase 14 (freie Visualisierung) umgesetzt.** Neues Modul `core/visualisierung.py`: generische
  Schicht, die aus einer Spezifikation (mindmap/organigramm/graph/balken) ein **reines SVG** erzeugt -- ohne
  Fremd-Bibliothek, ohne externen Render-Dienst. LUNA-Tool **`visualisiere(art, titel, inhalt)`** (hoa_tools);
  im Telegram-Kanal wird das SVG als Bild-Datei gesendet (neuer `_send_document`-Multipart-Pfad in bot.py,
  ToolContext-Feld `visuals`, Versand im Hauptloop), im Browser als generisches `visualisierung`-Panel
  (panels.py + app.js). Bestehende Panels bleiben Spezialfaelle. **ROADMAP.md** auf lebenden Stand gebracht
  (Status-Tabelle als Single Source of Truth; Phasen 5–14 umgesetzt, 10b zurueckgestellt; Backlog inkl.
  Execution-Modellzugang/lokales LLM). Ab jetzt wird die Roadmap bei jeder Phasenaenderung mitgepflegt.
- **Warum:** CEO-Auftrag: Phase 14 umsetzen + Roadmap immer aktuell halten.
- **Betroffen:** orchestrator/core/visualisierung.py (neu), orchestrator/tests/test_visualisierung.py (neu),
  orchestrator/core/hoa_tools.py, orchestrator/channels/telegram/bot.py, orchestrator/channels/voice/panels.py,
  orchestrator/channels/voice/static/app.js, ROADMAP.md. Suite 163/163.

## [2026-06-26 11:10] — Claude Code
- **Was:** Produktions-Container laeuft jetzt als **Non-root-User** (luna, UID 1026 : GID 100 = NAS-Eigentuemer
  nilskrueger:users). `deploy/Dockerfile`: Git-Identitaet/safe.directory von --global auf **--system**
  (/etc/gitconfig, gilt fuer jeden User), neuer User luna + `USER luna` + HOME=/home/luna. Auf dem NAS die
  bisher root-erstellten Daten-/Worktree-Pfade auf 1026:100 umgeeignet (chown), damit der Prozess sie
  schreiben kann.
- **Warum:** Die Claude-CLI verweigert `--dangerously-skip-permissions` als root -> Execution (Phase 7) war
  blockiert und der riskante IS_SANDBOX-root-Bypass die einzige Alternative. Als Non-root entfaellt der
  Bypass komplett: Execution funktioniert sicher, sobald Anthropic-Modellzugang da ist (ab 2026-07-01 oder
  mit Guthaben). Der root-Guard in execution_live.py bleibt als Sicherheitsnetz (greift nur noch bei root).
- **Betroffen:** deploy/Dockerfile; NAS-Dateieigentum unter /volume1/docker/ki-unternehmen. Suite 156/156.
- **Was:** Freigegebenen Antrag adc5 ("Einfuehrung eines zentralen Agenten-Aktivitaetsprotokolls") direkt
  umgesetzt (kostenlos, ohne externe Dienste): neues Modul `core/aktivitaet.py` (event-sourced JSONL
  `aktivitaet/log.jsonl`, leck-geschuetzt, durable) mit log/letzte/seit/zusammenfassung. Zentrale Einspeisung
  ueber den **Changelog-Callback** (`channels/telegram/bot.py`) -> jeder Governance-Eintrag (Antrags-
  Lebenszyklus, Execution, Charta) landet zugleich strukturiert im Protokoll, ohne jeden Agenten zu
  instrumentieren. Neues LUNA-Tool `aktivitaet_protokoll` (Filter Akteur/Anzahl + 24h-Zusammenfassung je
  Akteur/Kategorie), ToolContext-Feld `aktivitaet`. Vom Code-Sync ausgenommen (Live-Daten).
- **Warum:** CEO-Freigabe des Antrags adc5; Umsetzung durch Claude Code (LUNA-Autonomie-Execution braucht
  Anthropic-Guthaben, daher direkt umgesetzt).
- **Betroffen:** orchestrator/core/aktivitaet.py (neu), orchestrator/tests/test_aktivitaet.py (neu),
  orchestrator/channels/telegram/bot.py, orchestrator/core/hoa_tools.py, deploy/sync-to-nas.sh. Suite 156/156.

## [2026-06-26 10:10] — Claude Code
- **Was:** GitHub-Watcher listet jetzt **jedes auffaellige Repo einzeln** in der Meldung
  (`core/scheduler.py` github_tick): nummerierte Liste mit Kurzbeschreibung, Sternen/Wachstum, URL und
  Repo-Name statt nur des Top-Treffers.
- **Warum:** CEO-Feedback: Watcher soll alle Funde einzeln auffuehren, nicht nur den Top-Treffer.
- **Betroffen:** orchestrator/core/scheduler.py. Suite 147/147.
- **Offen (CEO-Tor, nicht umgesetzt):** Execution-Root-Bypass via `IS_SANDBOX=1` (erlaubt der Claude-CLI
  `--dangerously-skip-permissions` als root) -- bewusst NICHT committet, weil es autonome Code-Ausfuehrung als
  root freischaltet (Sicherheits-/Kostenentscheidung des CEO). Wartet auf ausdrueckliche Freigabe.

## [2026-06-26 09:20] — Claude Code (im Auftrag des CEO)
- **Was:** Operative Antrags-/Agenda-Status auf CEO-Anweisung bereinigt (direkt in den Live-Stores auf dem NAS,
  da diese vom Code-Sync ausgenommen sind): (1) Antrag "Kalender-Integration: Zeitzonen-Fehler beheben" ->
  **erledigt**. (2) Antrag "(nicht verfuegbar: Modellaufruf fuer 'cfo' fehlgeschlagen ...)" -> **abgelehnt**
  (ungueltiger Antrag aus fehlgeschlagenem Modellaufruf). (3) Agenda-Aufgabe "Mail-Markieren erneut versuchen"
  -> **erledigt/ausgesetzt**.
- **Warum:** CEO-Anweisung im Chat (Kalender + CFO-Modellaufruf erledigt, Mail-Markieren aussetzen).
- **Betroffen:** NAS-Stores antraege/log.jsonl + agenda/log.jsonl (nicht im Repo). Verbleibend offen:
  Trend-Radar (Twitter API), zentrales Agenten-Aktivitaetsprotokoll.

## [2026-06-26 09:10] — Claude Code
- **Was:** Kritischer Bot-Crash behoben. `core/execution_live.py` (`_arun`) bricht jetzt **vor** dem CLI-Start
  ab, wenn der Prozess als root laeuft (geteuid==0), mit klarer Fehlermeldung. Grund: Die Claude-CLI verweigert
  `--dangerously-skip-permissions` als root; der bisherige CLI-Start im root-Container crashte den SDK-Transport
  ("Fatal error in message reader") und riss den **gesamten Telegram-Message-Reader** mit -> LUNA reagierte nicht
  mehr auf Chat (Hintergrund-Loops/Briefings liefen weiter). Trigger war am 25.06. 17:20 die Freigabe von Antrag
  A-...e7a9 (Execution). Der Fehler wird nun von der ExecutionEngine sauber als 'fehlgeschlagen' gefangen.
- **Warum:** CEO-Meldung "LUNA antwortet nicht". Ursache: toter Message-Reader nach Execution-Crash.
- **Betroffen:** orchestrator/core/execution_live.py. Suite 147/147. Offen (Backlog): Container als Non-root-User
  laufen lassen, damit Execution nach Anthropic-Zugang (ab 2026-07-01) tatsaechlich funktioniert.

## [2026-06-26 09:00] — Claude Code
- **Was:** Telegram-Anzeige weiter aufgeraeumt + Referenz-IDs in Briefings.
  (1) `core/briefing.py`: Header ohne rohe `*...*`-Marker (sauberer Klartext statt Sternchen, die teils
  durchrutschten); offene/erledigte Antraege zeigen jetzt ihre **Antrags-ID** `[A-...]`, Agenda-Aufgaben ihre
  `[AG-...]`-ID -> CEO kann Punkte direkt referenzieren/freigeben.
  (2) `channels/telegram/bot.py`: nutzersichtbare ASCII-Texte auf Umlaute umgestellt -- CFO-Kostenpruefung
  ("Taegliche Kostenpruefung" -> "Tägliche Kostenprüfung — Vorschläge liegen vor."), /reset-Antwort und
  Chat-Fehlertext.
- **Warum:** CEO-Feedback: Briefing-Formatierung weiterhin mit Sternchen + teils ohne Umlaute; anstehende
  Punkte ohne Referenz-ID nicht ansprechbar.
- **Betroffen:** orchestrator/core/briefing.py, orchestrator/channels/telegram/bot.py. Suite 147/147.

## [2026-06-25 21:55] — Claude Code
- **Was:** Telegram-Anzeige aufgeraeumt. Neuer Filter `core/telegram_format.py` (`fuer_telegram`) wird vor
  JEDEM Senden angewendet (Chat-Antworten + proaktive Meldungen/Briefings): entfernt rohe Markdown-Marker
  (`**fett**`, `*betont*`, `# Header` -> Text; `* Punkt` -> `• Punkt`) und schreibt C-Level-Kuerzel gross
  (cto->CTO, cfo->CFO ...). Grund: der Bot sendet reinen Text ohne parse_mode, daher erschienen die Sterne
  woertlich und sorgten fuer Unuebersichtlichkeit. 5 neue Self-Checks; Gesamtsuite **147/147 OK**.
- **Warum:** CEO-Feedback aus den Telegram-Screenshots (Sterne unleserlich; Abteilungen sollen gross).
- **Betroffen:** `orchestrator/core/telegram_format.py` (neu), `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_telegram_format.py` (neu).


## [2026-06-25 19:15] — Claude Code
- **Was:** (1) **Finance Live-Dashboard:** neues `governance/dienste_register.py` (Live-Register aller
  KI-Modelle + Dienstleister aus den .env-Keys: Provider, Zweck, Kostenart, Key-Status, Erfassung) + Tool
  `finance_dashboard` (Register + gemessene Monatskosten je Provider, klar gekennzeichnet gemessen/geschaetzt/
  gratis). Gemini-Provider/Rate-Fix (Gratis-Tier=0). (2) **Proaktive Vorschlaege aus dem System:**
  `SelfDevelopment.vorschlag_fuer(modus='intern')` -- Luecken-/Mandatsanalyse: ein Bereich prueft seine Charta
  gegen seine Faehigkeiten und schlaegt PROAKTIV vor, was ihm fehlt -> Antrag + Freigabe-Push. Der taegliche
  Self-Dev-Loop wechselt ab: gerade Tage intern (Luecken), ungerade extern (Web). Tool `selbstentwicklung`
  bekommt `intern`-Flag. 4 neue Self-Checks; Gesamtsuite **139/139 OK**.
- **Warum:** CFO soll Gesamtueberblick ueber Modelle/Token/Dienstleister/Kosten haben; und Verbesserungs-
  vorschlaege (wie genau dieses Dashboard) sollen proaktiv aus dem System/den Agenten kommen, statt dass der
  CEO an alles denken muss.
- **Betroffen:** `orchestrator/governance/dienste_register.py` (neu), `orchestrator/core/hoa_tools.py`,
  `orchestrator/core/self_development.py`, `orchestrator/core/kosten.py`,
  `orchestrator/channels/telegram/bot.py`, `orchestrator/core/hoa_conversation.py`,
  `orchestrator/tests/test_dashboard_luecken.py` (neu).

## [2026-06-25 18:55] — Claude Code
- **Was:** Chat-Ausfall behoben + **Gemini als Fallback** vorbereitet. Ursache: Anthropic meldet das harte
  Monatslimit als **400 invalid_request_error** ("usage limits ... regain access on 2026-07-01"). Zwei Bugs:
  (1) `_ist_fallback_fehler` erkannte das NICHT -> kein Fallback; (2) `_ist_verlauf_fehler` wertete jeden
  400+invalid_request als Verlauf-Korruption -> Reset -> generische Fehlermeldung im Chat. Fix:
  `_ist_fallback_fehler` erkennt jetzt usage-limit/limit; `_ist_verlauf_fehler` matcht NUR noch
  tool_use/tool_result (echte Verlauf-Korruption). `ModelRouter` unterstuetzt eine **Fallback-Liste**
  (OpenAI-kompatibel) -> Gemini (Gratis-Tier, via `GEMINI_BASE_URL`) zuerst, dann OpenAI. Bot baut
  `_fallbacks` aus `GEMINI_API_KEY`/`OPENAI_API_KEY`. Klarere Fehlermeldung bei "alle Anbieter erschoepft".
  Gesamtsuite **135/135 OK**.
- **Warum:** LUNA-Chat antwortete nur noch mit "technischer Fehler" -- Anthropic gesperrt bis 2026-07-01,
  OpenAI ohne Guthaben. Gemini-Gratis-Tier funktioniert -> sobald `GEMINI_API_KEY` in .env, laeuft der Chat.
- **Betroffen:** `orchestrator/core/model_router.py`, `orchestrator/core/hoa_conversation.py`,
  `orchestrator/channels/telegram/bot.py`, `orchestrator/tests/test_model_router.py`. OFFEN: GEMINI_API_KEY
  setzen (CEO liefert).

## [2026-06-25 18:30] — Claude Code
- **Was:** Funde-Handling verbessert (kein Ticket pro Fund -> Flut vermieden). **(A) Drill-down sichtbar:**
  proaktive Meldungen mit Detail haengen jetzt den Hinweis `Details: schreib mir "zeig #xxxx"` an; LUNA loest
  das ueber `meldung_details` auf. **(B) Funde -> Entscheidung:** neues Tool `funde_bewerten(abteilung)` --
  buendelt die gesammelten Fachbereichs-Funde ueber die Innovations-Pipeline zu EINEM entscheidungsreifen
  Antrag (Fachbereich-Idee + CTO-Machbarkeit + CFO-Kosten), statt 15 Rohlinks. System-Prompt erklaert beides.
  Gesamtsuite **134/134 OK**.
- **Warum:** CEO bekam Sammelmeldungen ("15 neue Funde"), konnte aber weder den Inhalt sehen noch entscheiden.
  Jetzt: Inhalt auf Abruf + gebuendelte Entscheidungs-Antraege.
- **Betroffen:** `orchestrator/channels/telegram/bot.py`, `orchestrator/core/hoa_tools.py`,
  `orchestrator/core/hoa_conversation.py`.

## [2026-06-25 18:10] — Claude Code
- **Was:** **Multi-Provider-Chat (Anthropic-first + OpenAI-Fallback)** gebaut. Neues `core/model_router.py`
  (`ModelRouter`): der Chat ruft zuerst Anthropic; bei Guthaben-/Rate-/Ueberlastungsfehler automatisch
  Umschalten auf OpenAI. Tool-Calling bleibt im Anthropic-Format; Router uebersetzt Verlauf/Tools nach OpenAI
  und zurueck (`b*`-Helfer lesen SDK-Objekte UND dicts). `HoaConversation` nutzt den Router; Kostenerfassung
  bucht den real genutzten Provider. Bot reicht `OPENAI_API_KEY` + `gpt-4o-mini` durch; `openai`-Lib ins Image.
  5 neue Self-Checks; Gesamtsuite **134/134 OK**.
- **Warum:** Anthropic-Guthaben staendig leer -> Fallback haelt den Chat am Laufen. **OFFEN:** gelieferter
  OpenAI-Key authentifiziert, Konto hat aber **kein Guthaben** (insufficient_quota/429) -> Fallback greift erst
  nach OpenAI-Billing (gpt-4o-mini sehr guenstig) oder Anthropic-Aufladung.
- **Betroffen:** `orchestrator/core/model_router.py` (neu), `orchestrator/core/hoa_conversation.py`,
  `orchestrator/channels/telegram/bot.py`, `deploy/Dockerfile`, `orchestrator/tests/test_model_router.py` (neu).

## [2026-06-25 17:45] — Claude Code
- **Was:** CEO-Tor-Fehlalarm behoben -- "kostenlos/kostenfrei/gratis/open-source" loesten faelschlich das
  Geld-Tor aus (Teilstring "kosten") und blockierten legitime Recherchen (z. B. MCP-Scan). `detect_ceo_tor`
  neutralisiert diese "kein-Geld"-Begriffe vor der Pruefung; echtes Geld (kostenpflichtig/bezahlen/Abo) bleibt
  blockiert. Suite 129/129.
- **Warum:** Researcher-Anfrage "kostenlose MCP Server" wurde faelschlich geblockt.
- **Betroffen:** `orchestrator/core/routing.py`.

## [2026-06-25 17:35] — Claude Code
- **Was:** CFO **Stufe 2 -- echte Token-/Kostenerfassung.** Neues `core/kosten.py` (`KostenStore`,
  append-only `finance/kosten-log.jsonl`, leck-geschuetzt): jeder echte Modell-Aufruf meldet Token-Nutzung;
  Monats-Aggregation je Quelle/Provider, EUR-geschaetzt (Richtwert-Raten Anthropic + OpenAI). `HoaConversation`
  erfasst `resp.usage` je Chat-Antwort; `ToolContext.kosten`; Tool `kosten_statistik` (laufender Monat). Der
  CFO-Tagesloop (03:00) zeigt jetzt die echten laufenden Modellkosten je Provider mit an. Sync excludet
  `finance/kosten-log.jsonl` (NAS-Live). 4 neue Self-Checks; Gesamtsuite **129/129 OK**. Vorbereitung fuer
  die Anthropic/OpenAI-Lastverteilung (provider-Feld im Log).
- **Warum:** CEO will echte Kostentransparenz (Token je Agent/Provider) -- Grundlage, um die staendig
  aufgebrauchten Anthropic-API-Token sinnvoll auf Anthropic+OpenAI zu verteilen.
- **Betroffen:** `orchestrator/core/kosten.py` (neu), `orchestrator/core/hoa_conversation.py`,
  `orchestrator/core/hoa_tools.py`, `orchestrator/channels/telegram/bot.py`, `deploy/sync-to-nas.sh`,
  `orchestrator/tests/test_kosten.py` (neu).

## [2026-06-25 17:05] — Claude Code
- **Was:** (1) **GitHub-Push live + hart gesperrt:** `GITHUB_TOKEN` (CEO-PAT) in `.env` (Mac+NAS, gitignored);
  Auth read-only verifiziert (ls-remote). Push **ausschliesslich** auf `hsvnils/agent-OS` -- doppelt gesperrt
  (Tool-Handler hardcodet + Guard in `push_branch`). (2) **CFO-Tagesloop:** neuer Daemon `_start_cfo_loop`
  prueft taeglich 03:00 (DE) automatisch Freeware-Alternativen/ungenutzte Abos/Token-Sparpotenziale (CFO,
  1 LLM-Lauf/Tag) und meldet die Vorschlaege proaktiv; manuell weiter ueber `kosten_optimierung`. Respektiert
  Notbremse. (3) **Obsidian:** `vault/Dashboard.md` (versioniert) macht das Repo zu einem navigierbaren
  Vault; Tool `obsidian_export` schreibt Live-Wissensstand + offene Tickets als Markdown nach `vault/`
  (gitignored). Gesamtsuite **125/125 OK**.
- **Warum:** CEO-Wuensche: Push nach GitHub (nur agent-OS!), taegliche CFO-Kostenpruefung, Obsidian als
  kostenfreie Wissensoberflaeche.
- **Betroffen:** `orchestrator/core/hoa_tools.py`, `orchestrator/core/execution_live.py`,
  `orchestrator/channels/telegram/bot.py`, `vault/Dashboard.md` (neu), `.gitignore`. Token nur in `.env`
  (NICHT versioniert).

## [2026-06-25 16:35] — Claude Code
- **Was:** (1) **IT-Selbstheilung (CEO-Delegation):** neues `core/self_healing.py` (`ist_technisch_kostenfrei`
  + `SelfHealing.heilen`) + Tool `technische_freigabe(antrag_id)`. LUNA darf rein TECHNISCHE, KOSTENFREIE
  Antraege (Kategorie `technisch-kostenfrei`) selbst freigeben, umsetzen (Branch+Tests) und bei gruenen Tests
  mergen -- der CEO wird informiert. **Harte Grenzen (Code):** Kategorie-Pflicht + Stichwort-Scan (Geld/Recht/
  Oeffentlichkeit/Secrets/Charta/Loeschung -> immer CEO) + Tests-gruen-Pflicht + Notbremse + Git-Reversibel.
  Governance in `zugriffs-policy.md` dokumentiert. (2) **GitHub-Push:** `execution_live.push_branch` + Tool
  `antrag_pushen(antrag_id)` -- pusht den Antrag-Branch zu GitHub fuer CEO-Review per PR; gated auf
  `GITHUB_TOKEN` (sonst Fall-B), Token wird in der Ausgabe redigiert. System-Prompt erklaert beide. 4 neue
  Self-Checks; Gesamtsuite **125/125 OK**.
- **Warum:** CEO-Wunsch (volle Variante): IT+Self-Maintenance behebt technische, kostenfreie Probleme selbst;
  zusaetzlich Push nach GitHub fuer den Review.
- **Betroffen:** `orchestrator/core/self_healing.py` (neu), `orchestrator/core/execution_live.py`,
  `orchestrator/core/hoa_tools.py`, `orchestrator/core/hoa_conversation.py`, `governance/zugriffs-policy.md`,
  `orchestrator/tests/test_self_healing.py` (neu).

## [2026-06-25 16:05] — Claude Code
- **Was:** (1) **Restbaustelle Execution behoben:** `real_make_workspace(..., snapshot=True)` committet in der
  Produktion (NAS) vor dem Branchen einen Deploy-Snapshot der aktuellen Dateien -> der Worktree bekommt den
  AKTUELLEN deployten Code (vorher branchte er vom veralteten HEAD). Flag `EXECUTION_AUTO_SNAPSHOT=1` nur auf
  NAS; Mac aus. Git-Identitaet (user.name/email) ins Image. (2) **Ticket-Management:** `offene_tickets`
  (alle offenen Antraege+Research abteilungsuebergreifend = LUNAs aktiver, schlanker Stand) und
  `abteilung_tickets(abteilung, status?)` (geschlossene aus dem Abteilungsarchiv, nur auf Abruf). Prompt
  erklaert das schlanke Modell. (3) **Finance-Kostencheck:** `kosten_optimierung(fokus?)` -- CFO prueft
  Freeware-/Token-Sparpotenziale (Vorschlag, kein Ausfuehren). 5 neue Self-Checks; Gesamtsuite **121/121 OK**.
- **Warum:** CEO-Wunsch -- Execution gegen aktuellen Code; offene Tickets bei LUNA, geschlossene im
  Abteilungsarchiv (Wissen schlank halten); Finance soll Kosten senken.
- **Betroffen:** `orchestrator/core/execution_live.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/core/hoa_tools.py`, `orchestrator/core/hoa_conversation.py`, `deploy/Dockerfile`,
  `orchestrator/tests/test_tickets_finance.py` (neu).

## [2026-06-25 15:35] — Claude Code
- **Was:** Zwei produktive Bugs (vom CEO via Telegram gemeldet) behoben. **(1) Git „dubious ownership" (exit
  128):** der Container laeuft als root, das Bind-Mount-Repo gehoert nilskrueger -> `git worktree add` brach
  ab, `antrag_umsetzen` schlug fehl. Fix: `git config --global --add safe.directory /app` + `'*'` im
  Dockerfile; defensiv auch in `execution_live.real_make_workspace` (+ `worktree prune`). **(2) Vergifteter
  Gespraechsverlauf (400 'tool_use ids without tool_result'):** der git-Fehler flog aus dem Tool-Loop, der
  Verlauf behielt ein tool_use ohne tool_result -> JEDE weitere Nachricht scheiterte dauerhaft. Fix in
  `hoa_conversation`: jedes tool_use bekommt IMMER ein tool_result (Tool-Fehler werden gefangen);
  `_repariere_verlauf` schneidet kaputte Tails ab; Selbstheilung bei Verlauf-Fehler (Reset + 1 Retry);
  saubere Fehlertexte. Bot: Session bei Fehler verwerfen + `/reset`-Befehl. **(3) Prompt:** LUNA verspricht
  keine zeitlich versprochenen Selbst-Meldungen mehr (kein Timer). 4 neue Self-Checks; Gesamtsuite
  **116/116 OK**. Backlog-Idee (Partner-Akten-System) in ROADMAP aufgenommen (niedrige Prio).
- **Warum:** CEO konnte unterwegs nicht mehr mit LUNA chatten (Dauer-400) und die Antrags-Umsetzung schlug
  fehl; Ursache war die Kette git-128 -> Verlaufskorruption.
- **Betroffen:** `orchestrator/core/hoa_conversation.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/core/execution_live.py`, `deploy/Dockerfile`,
  `orchestrator/tests/test_hoa_conversation.py`, `ROADMAP.md`.

## [2026-06-25 14:45] — Claude Code
- **Was:** Vier weitere CEO-Wuensche umgesetzt. (1) **Geplanter Selbst-Entwicklungs-Loop scharf** -- taeglich
  09:00 (DE) EIN rotierender Bereich -> bewerteter Antrag -> **proaktiver Freigabe-Push** an den CEO
  (SelfDevelopment.notify); nur mit `SELF_DEV_ENABLED=1` (gesetzt, CEO-Freigabe), respektiert die Notbremse.
  (2) **Proaktiver Mail-/Kalender-Watcher** -- `WatchScheduler.mail_tick`/`kalender_tick` (neue ungelesene
  Mails + Termin-Kollisionen, kostenlos, dedupliziert); Poll alle ~15 min im Hauptloop. (3) **Mehr
  Google-Aktionen** (gated): `termin_aendern`, `termin_loeschen`, `drive_anlegen`, `mail_markieren` (benigne),
  + Read-Tools `posteingang`, `kalender_kollisionen`. (4) **Ticket-Auto-Close** -- `ResearchTickets.aufraeumen`
  schliesst steckengebliebene Tickets (offen/in_arbeit > 1 h) automatisch; laeuft im 15-min-Poll. 7 neue
  Self-Checks; Gesamtsuite **113/113 OK**.
- **Warum:** CEO will den Selbst-Entwicklungs-Loop aktiv (mit Freigabe ueber LUNA), proaktive Mail-/Termin-
  Meldungen, mehr Google-Aktionen und dass erledigte/haengende Tickets selbststaendig geschlossen werden.
- **Betroffen:** `orchestrator/governance/google_workspace.py`, `orchestrator/core/scheduler.py`,
  `orchestrator/core/self_development.py`, `orchestrator/core/research_tickets.py`,
  `orchestrator/core/hoa_tools.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_google_actions_watcher.py` (neu). Flag/Secret nur in `.env`.

## [2026-06-25 14:15] — Claude Code
- **Was:** Vier CEO-Wuensche umgesetzt. (1) **Meldungen v2:** proaktive Nachrichten beginnen mit der
  **Abteilung**, tragen eine **Kurz-ID** (#xxxx) und ein **Detail** (Hintergrund); neues Tool
  `meldung_details(id)` fuer Rueckfragen ("was steckt hinter #xxxx?"). (2) **Self-Maintenance:** die IT
  ueberwacht jetzt kontinuierlich die eigenen Prozesse (`core/self_maintenance.py`: Keys, Google, Stores,
  Watcher-Heartbeat) -- laeuft je Watch-Tick + meldet Probleme proaktiv (abteilung "IT/Self-Maintenance");
  Tool `systemcheck`; Watch-Loop-Fehler werden jetzt auch proaktiv gemeldet. (3) **Briefings:** Morgen-
  (08:00) und Abend-Briefing (20:00, **Europe/Berlin**) als Daemon-Loop -- regelbasiert/kostenlos aus den
  Stores (ueber Nacht/heute erledigt + offene Punkte + manuell Hinzugefuegtes); `core/briefing.py` mit
  `Agenda` (Tools `notiz_hinzufuegen`, `agenda_zeigen`) + `briefing_jetzt`. tzdata ins Image. (4) **Umlaute:**
  LUNA-System-Prompt fordert ä/ö/ü/ß in Telegram; nutzersichtbare Template-Texte (Briefing/Watcher/Self-
  Maintenance) auf Umlaute umgestellt. 9 neue Self-Checks; Gesamtsuite **106/106 OK**.
- **Warum:** CEO will Rueckfragen zu Meldungen, kontinuierliche IT-Prozessueberwachung, feste Morgen-/Abend-
  Briefings inkl. manueller Punkte und Umlaute in der Telegram-Kommunikation.
- **Betroffen:** `orchestrator/core/notifications.py`, `orchestrator/core/self_maintenance.py` (neu),
  `orchestrator/core/briefing.py` (neu), `orchestrator/core/scheduler.py`, `orchestrator/core/hoa_tools.py`,
  `orchestrator/core/hoa_conversation.py`, `orchestrator/channels/telegram/bot.py`, `deploy/Dockerfile`,
  `deploy/sync-to-nas.sh`, `orchestrator/tests/test_briefing_maintenance.py` (neu),
  `orchestrator/tests/test_notifications.py`.

## [2026-06-25 13:45] — Claude Code
- **Was:** Kritischer Leck-Schutz-Bugfix. Kurze/flag-/numerische/E-Mail-Werte aus `.env` (z. B.
  `WEB_RESEARCH_ANTHROPIC=1`, Chat-ID, iCloud-Adresse) wurden faelschlich als Secrets behandelt -> redact()
  ersetzte **jede '1' ueberall** und verstuemmelte IDs/Zeitstempel/Logs (Changelog, Antraege, Tickets) sowie
  die Notifier-„sent"-IDs (-> Endlos-Resend derselben Push-Nachricht). Fix: neuer Filter
  `is_redactable_secret` (Laenge >= 12, nicht rein numerisch, kein '@') -- genutzt in `load_env_secrets`
  und in der Bot-Secret-Liste. Nur echte Keys/Token werden noch redigiert. Test ergaenzt; Suite **97/97 OK**.
- **Warum:** Beim Live-Test des Notifiers fiel auf, dass Push-Meldungen mehrfach zugestellt wurden und IDs
  verstuemmelt waren -- Ursache war die uebergriffige Redaktion durch den Flag-Wert '1'.
- **Betroffen:** `orchestrator/governance/leak_guard.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_secret_governance.py`.

## [2026-06-25 13:30] — Claude Code
- **Was:** Proaktiver Telegram-Notifier gebaut -- LUNA/Watcher/Abteilungen melden sich **unaufgefordert** beim
  CEO. Neu: `core/notifications.py` (`Notifications`-Outbox, durable JSONL `notifications/log.jsonl`,
  queued->sent, Dedup im Zeitfenster, leck-geschuetzt). Telegram-Bot stellt die Outbox im Hauptloop zu
  (<=~35 s Latenz, keine Token). WatchScheduler bekommt `notify`-Callback und meldet GitHub-Auffaelligkeiten
  + neue Fachbereichs-Funde proaktiv. HoA-Tools `melde_an_ceo(text,kategorie?)` (LUNA/Abteilungs-Anliegen ->
  Push) und `benachrichtigungen_zeigen`. `ToolContext.notifications`; Sync-Skript excludet
  `notifications/log.jsonl`. 7 neue Self-Checks; Gesamtsuite **96/96 OK**.
- **Warum:** CEO will, dass LUNA sich von selbst meldet (Researcher findet etwas, Abteilung wendet sich mit
  einer Bitte an LUNA, Aufgabe erledigt) -- nicht nur auf Anfrage antwortet.
- **Betroffen:** `orchestrator/core/notifications.py` (neu), `orchestrator/core/scheduler.py`,
  `orchestrator/core/hoa_tools.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_notifications.py` (neu), `deploy/sync-to-nas.sh`.

## [2026-06-25 13:05] — Claude Code
- **Was:** IT-Bugfix Kalender -- Zeitzonen-Fehler behoben (betrifft Antrag A-20260625 „Kalender-Integration:
  Zeitzonen-Fehler beheben", von LUNA, Kategorie IT-Bug). `termin_anlegen` schickte `start`/`end` ohne
  `timeZone`; die Google Calendar API verlangt das bei ISO-Zeiten ohne Offset und scheiterte mit „Missing
  time zone definition". Fix: `GoogleWorkspace` traegt jetzt eine konfigurierbare Zeitzone
  (`GOOGLE_CALENDAR_TIMEZONE`, Default Europe/Berlin) in start/end; neuer testbarer Helfer `_event_body`.
  Regressionstest ergaenzt; Suite **89/89 OK**. Live verifiziert (echter Termin angelegt + danach geloescht).
- **Warum:** LUNA konnte keine Kalendertermine anlegen; der Bug stammte aus dem Phase-11-Code.
- **Betroffen:** `orchestrator/governance/google_workspace.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_google_workspace.py`.

## [2026-06-25 12:45] — Claude Code
- **Was:** Phase 13 (Self-Development-Loop, Apex) gebaut + abgesichert. Der Kreis schliesst sich:
  Fachbereichs-Wissensstand (Phase 12) -> Agent leitet Verbesserung in SEINEM Bereich ab -> CTO/CFO-Bewertung
  -> **Antrag** (Phase 6) -> CEO-Freigabe -> Execution (Phase 7). Neu: `core/self_development.py`
  (`SelfDevelopment.vorschlag_fuer(abteilung)` on-demand, `lauf()` geplant+gated); `InnovationPipeline.run`
  um `abteilung`/`wissen` erweitert (abteilungs- & wissensbasierte Vorschlaege, spart Web-Recherche).
  HoA-Tools `selbstentwicklung(abteilung?)`, `autonomie_pausieren`, `autonomie_status`. **Notbremse:**
  `WatchStore.set_pause/paused`; Bot-Hintergrund-Loop und Selbst-Entwicklung respektieren die Pause.
  **Harte Invarianten:** nur Vorschlaege (Antrag, kein Ausfuehren); token-frugal (LLM nur on-demand; geplanter
  Loop per Default AUS, `SELF_DEV_ENABLED`); CEO-Tor/Charta-Rechte/Leck-Schutz unveraendert. 6 neue
  Self-Checks; Gesamtsuite **88/88 OK**. Plan: `PHASE13_PLAN.md`.
- **Warum:** Roadmap-Apex -- die Agenten entwickeln sich auf Basis ihres aktuellen Fachbereichs-Wissens selbst
  weiter, kontrolliert ueber den freigegebenen Antrags-/Execution-Pfad und token-bewusst.
- **Betroffen:** `orchestrator/core/self_development.py` (neu), `orchestrator/core/innovation.py`,
  `orchestrator/core/scheduler.py` (Pause), `orchestrator/core/hoa_tools.py` (3 Tools),
  `orchestrator/channels/telegram/bot.py` (Loop respektiert Pause),
  `orchestrator/tests/test_self_development.py` (neu), `PHASE13_PLAN.md` (neu).

## [2026-06-25 12:25] — Claude Code
- **Was:** Phase-12/13-Bruecke -- Fachbereichs-Recherche ueber den **Researcher** + Wissensstand zurueck an
  die Agenten. (1) `dept_tick` laeuft jetzt ueber den Researcher: erzeugt je Lauf ein Research-Ticket
  (Nachverfolgbarkeit: welche Abteilung, was, Quellen) und pflegt den Fachbereichs-Wissensstand (kostenlos,
  Brave). (2) **Phase-13-Substrat:** beim Konsultieren eines Fachagenten (`delegate`) wird sein aktueller
  Fachbereichs-Wissensstand (Top-Funde aus dem 24/7-Monitoring) als Kontext injiziert -> Agent antwortet „auf
  dem neuesten Stand". (3) Neues read-only Tool `wissensstand <abteilung>` (keine Suche/Token). (4) Watch-
  Themen je Bereich um **neue Dienstleister/Tools** und **IT-Richtlinien/Compliance** erweitert (cto, ciso).
  WatchScheduler bekommt `research` injiziert (Bot-Verdrahtung). 2 neue Self-Checks; Gesamtsuite **82/82 OK**.
- **Warum:** CEO-Vorgabe -- der Researcher soll spezialisiert fuer ALLE Abteilungen suchen, damit sich die
  Agenten in ihren Bereichen weiterentwickeln und stets aktuell sind (Fundament fuer Phase 13).
- **Betroffen:** `orchestrator/core/scheduler.py`, `orchestrator/core/hoa_tools.py` (delegate-Injektion +
  Tool `wissensstand`), `orchestrator/core/watch_config.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_watch.py`, `PHASE12_PLAN.md`.

## [2026-06-25 12:10] — Claude Code
- **Was:** Phase 12 (Durable Watch-Queue + Scheduler, 24/7) gebaut + Hintergrund-Loop live. **Token-frugal
  by design:** der 24/7-Loop macht NUR kostenlose Datenarbeit (GitHub-API + Brave-Gratis) und flaggt
  regelbasiert -- **kein LLM im Hintergrund** (`llm_enabled=False`). Neu: `governance/github_watch.py`
  (GitHub-Search frei + `flag_fast_growers` per Sterne-Velocity/Neuheit + Mock), `core/watch_config.py`
  (kuratierte Watch-Themen je Fachbereich: Suche + GitHub-Topics), `core/scheduler.py` (`WatchStore`
  event-sourced JSONL `watch/log.jsonl` mit Sterne-Historie/Funde-Dedup/Lauf-Zeiten + `WatchScheduler`).
  LUNA-Tools `github_trends`, `dept_briefing`, `watch_digest`, `watch_tick` (alle kostenlos). Bot:
  Daemon-Thread `_start_watch_loop` -- GitHub jeden Tick, **eine** Abteilung je Tick (Brave-Quota schonen),
  Intervall `WATCH_INTERVAL_HOURS` (Default 6 h); Fehler nie fatal. Sync-Skript excludet `watch/log.jsonl`.
  7 Offline-Self-Checks; Gesamtsuite **80/80 OK**. Live-GitHub-API (frei) verifiziert.
- **Warum:** CEO will 24/7-Beobachtung der Aussenwelt OHNE Token zu verbrennen, abteilungsrelevante Suchen je
  Fachbereich und schnell wachsende High-Star-GitHub-Repos im Blick.
- **Betroffen:** `orchestrator/governance/github_watch.py` (neu), `orchestrator/core/watch_config.py` (neu),
  `orchestrator/core/scheduler.py` (neu), `orchestrator/core/hoa_tools.py`, `orchestrator/channels/telegram/
  bot.py`, `orchestrator/tests/test_watch.py` (neu), `deploy/sync-to-nas.sh`, `PHASE12_PLAN.md` (neu).

## [2026-06-25 11:50] — Claude Code
- **Was:** Phase 9 (Innovations-Pipeline) gebaut. Neues Modul `orchestrator/core/innovation.py` mit
  `InnovationPipeline`: orchestriert Web-Recherche (Phase 8) -> Idee (Unternehmensberater, Agent 01) ->
  Bewertung (CTO-Machbarkeit + CFO-Kostenvoranschlag) -> **entscheidungsreifer Antrag** (Phase 6, Status
  `eingereicht`, von „Unternehmensberater (Innovation)"). **Kein Ausfuehren** -- CEO entscheidet (Mensch-Tor
  bleibt hart). Neues LUNA-Tool `innovation_scouting(thema?)`. Robust (Backend-Fehler -> Antrag trotzdem,
  kein Absturz), leck-geschuetzt, Backend injizierbar. 6 Offline-Self-Checks; Gesamtsuite **73/73 OK**.
  Plan: `PHASE9_PLAN.md`.
- **Warum:** Roadmap Phase 9 -- der Berater liefert fundierte, bewertete Weiterentwicklungs-Vorschlaege als
  Antrag; schliesst den kontrollierten Selbst-Verbesserungs-Kreis (Vorschlag -> CEO-Freigabe -> Phase-7-Umsetzung).
- **Betroffen:** `orchestrator/core/innovation.py` (neu), `orchestrator/core/hoa_tools.py`
  (Tool `innovation_scouting`), `orchestrator/tests/test_innovation.py` (neu), `PHASE9_PLAN.md` (neu).

## [2026-06-25 11:35] — Claude Code
- **Was:** Google-Kalender: **Standard-Einladung** ergaenzt. `termin_anlegen` laedt jetzt automatisch eine
  konfigurierte Adresse als Teilnehmer ein (CEO: private iCloud `hsvnils@icloud.com`) und verschickt die
  Einladung (`sendUpdates=all`). Adresse in `GOOGLE_CALENDAR_DEFAULT_ATTENDEE` (orchestrator/.env, Mac + NAS,
  nicht versioniert -> PII bleibt aus dem Git). `GoogleWorkspace(standard_einladung=...)` + Bot-Verdrahtung
  aus den Secrets; Vorschau zeigt die Einladung mit. Test ergaenzt; Suite **67/67 OK**. NAS: Code-Sync +
  Restart, im Container verifiziert (Vorschau-Einladung = iCloud).
- **Warum:** CEO will bei Google-Kalender-Terminen immer seine private Mailadresse mit eingeladen bekommen.
- **Betroffen:** `orchestrator/governance/google_workspace.py`, `orchestrator/channels/telegram/bot.py`,
  `orchestrator/tests/test_google_workspace.py`. Adresse nur in `.env` (NICHT versioniert).

## [2026-06-25 11:20] — Claude Code
- **Was:** Phase 11 (Google Workspace) **live geschaltet** fuer `hanserautisch@gmail.com`. OAuth-Desktop-Client
  in der Google Cloud (Projekt LUNA) angelegt; einmalige Autorisierung ueber `deploy/google_oauth_authorize.py`
  (Werte direkt in `.env` geschrieben, kein Echo). `GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN` in
  `orchestrator/.env` (Mac + NAS, gitignored). NAS-Image per `sync-to-nas.sh --build` neu gebaut (google-api-
  python-client + google-auth), Container recreated. **Live-Test Mac UND NAS-Container OK:** Gmail (Treffer),
  Kalender (ok), Drive (ok); `verfuegbar=True`. Schreib-Tools bleiben gated (bestaetigt=true). Mac-venv um
  google-Libs ergaenzt.
- **Warum:** CEO hat das Google-Konto + OAuth eingerichtet und die Zustimmung erteilt -> LUNA kann jetzt
  Mails/Termine/Dateien/Sheets lesen (Schreiben nach Bestaetigung).
- **Betroffen:** `governance/zugriffs-policy.md` (Status LIVE). Secrets/OAuth nur in `.env` (NICHT versioniert);
  kein Code-Change (Phase-11-Code lag bereits vor).

## [2026-06-25 11:05] — Claude Code
- **Was:** Phase 11 (Google Workspace) **offline gebaut** (Go-Live wartet auf CEO-Tor + CISO). LUNA bekommt
  Zugriff auf ein **separates Google-Konto** -- Gmail, Kalender, Drive, Sheets. Neues Modul
  `orchestrator/governance/google_workspace.py`: `GoogleAuth` (OAuth-Refresh-Token aus .env, lazy
  Client-Bau), `GoogleWorkspace` (Lesen direkt; Senden/Aendern/Schreiben **gated** -- ohne `bestaetigt=true`
  nur Vorschau, Mensch-Tor AGENTS.md 4; `mail_entwurf` sicher), `MockGoogleWorkspace` (Offline). 10 HoA-Tools
  (`mail_suchen/lesen/entwurf/senden`, `kalender_agenda`, `termin_anlegen`, `drive_suchen/lesen`,
  `tabelle_lesen/schreiben`); `ToolContext.google` + Bot-Verdrahtung aus den .env-Secrets. Ohne Credentials ->
  Fall-B-Hinweis (kein Absturz, kein Netz, keine google-Libs noetig). Least-Privilege-Scopes (readonly +
  compose/events/file/spreadsheets). 8 Offline-Self-Checks; Gesamtsuite **66/66 OK**. Dazu CEO-Anleitung
  `deploy/google-oauth-setup.md` + Helfer `deploy/google_oauth_authorize.py` (einmaliger Refresh-Token);
  Dockerfile um google-api-python-client + google-auth ergaenzt; `.gitignore` schuetzt client_secret/token.
  Zugriffs-Policy + `PHASE11_PLAN.md` fortgeschrieben.
- **Warum:** CEO will LUNA Zugriff auf die Google-Produkte geben (Mail/Kalender/Drive/Tabellen); Modell
  „Lesen frei, Schreiben nur nach Bestaetigung", separates Konto. Offline-first -> Go-Live = OAuth-Credentials.
- **Betroffen:** `orchestrator/governance/google_workspace.py` (neu), `orchestrator/core/hoa_tools.py`,
  `orchestrator/channels/telegram/bot.py`, `orchestrator/tests/test_google_workspace.py` (neu),
  `governance/zugriffs-policy.md`, `deploy/Dockerfile`, `deploy/google-oauth-setup.md` (neu),
  `deploy/google_oauth_authorize.py` (neu), `.gitignore`, `PHASE11_PLAN.md` (neu).

## [2026-06-25 10:35] — Claude Code
- **Was:** Anthropic-Web **freigeschaltet** (CEO) + **Brave-first-Eskalations-Policy** umgesetzt.
  `WEB_RESEARCH_ANTHROPIC=1` in `orchestrator/.env` (Mac + NAS, nicht versioniert). Router neu: **Brave ist
  Default fuer alle Recherchen**; Anthropic-Web (billbar) nur als **Eskalation**, wenn Brave nicht verfuegbar
  ist, Limit/Fehler liefert, keine Treffer bringt, ODER der CEO eine Revision/weitere Recherche beauftragt
  (`recherche_beauftragen(..., eskalation=true)`). Schlaegt Anthropic-Web fehl (Guthaben/Limit), faellt der
  Researcher automatisch auf Brave zurueck. Live verifiziert: Eskalations-Call erreicht die echte Anthropic-
  API; diese meldet aktuell **'credit balance too low'** (web_search laeuft ueber raw-API-Guthaben, nicht CLI-
  Abo) -> Fallback auf Brave greift sauber. Code fing den Fehler ab (kein Absturz). Suite **58/58 OK**
  (Eskalation, Auto-Eskalation bei leer/Fehler/nicht-verfuegbar, Anthropic-Fehler-Fallback getestet).
- **Warum:** CEO-Freigabe mit klarer kostenbewusster Policy (Brave zuerst, Anthropic nur bei Bedarf/Revision).
  Offen: Anthropic-API-Guthaben aufladen (console.anthropic.com/Billing), damit die Eskalation real greift.
- **Betroffen:** `orchestrator/governance/web_research.py` (Brave-first-Router + Eskalation + Fehler-Fallback),
  `orchestrator/core/hoa_tools.py` (`eskalation`-Param), `orchestrator/tests/test_web_research.py`,
  `governance/zugriffs-policy.md`, `PHASE8_PLAN.md`. Flag/Secret nur in `.env` (NICHT versioniert).

## [2026-06-25 10:15] — Claude Code
- **Was:** Phase 8.5 -- **Researcher (Agent 15) + Research-Tickets** gebaut (auf CEO-Freigabe der Charta).
  Neuer Agent `agents/15_researcher.md` (zentraler Web-Recherche-Dienst; einziger Halter der Capability
  `web_research`, Least-Privilege). Neuer event-sourced Ticket-Store `orchestrator/core/research_tickets.py`
  (`research/log.jsonl`, append-only, leck-geschuetzt; Lebenszyklus offen->in_arbeit->erledigt|fehlgeschlagen)
  -- bewusst abgegrenzt von Antraegen (Entscheidungs-Tickets). LUNA-Tools: `recherche_beauftragen(frage,
  abteilung,tiefe?)` (legt Ticket an, sucht ueber den Web-Router, schreibt Befund+Quellen), `recherche_
  tickets_zeigen(status?)`, `recherche_ticket(id)`. Direktes `web_recherche` aus dem LUNA-Toolset entfernt --
  jede Suche laeuft jetzt ueber den ticketenden Researcher (Nachverfolgbarkeit: welche Abteilung, was, wann,
  Befund, Quellen). `res` als konsultierbarer Subagent + in der delegate-Liste verdrahtet; Bot baut den
  Research-Store in den ToolContext. Sync-Skript excludet `research/log.jsonl` (NAS-Produktionsdaten).
  Registry + Zugriffs-Policy fortgeschrieben (web_research auf `res` verengt). 16 neue/aktualisierte
  Self-Checks; Gesamtsuite **58/58 OK**. Live-Smoke (echtes Brave) OK: Ticket angelegt, 5 Quellen.
- **Warum:** CEO-Wunsch -- ein dedizierter Research-Agent kapselt die Web-Recherche fuer alle Abteilungen
  (ueber LUNA) mit lueckenloser Ticket-Nachverfolgung; getrennt vom Innovation-Agenten (01), der ihn nutzt.
- **Betroffen:** `agents/15_researcher.md` (neu), `agents/REGISTRY.md`, `governance/zugriffs-policy.md`,
  `orchestrator/core/research_tickets.py` (neu), `orchestrator/core/hoa_tools.py`,
  `orchestrator/core/subagents.py`, `orchestrator/channels/telegram/bot.py`, `deploy/sync-to-nas.sh`,
  `orchestrator/tests/test_research_tickets.py` (neu), `orchestrator/tests/test_web_research.py`.

## [2026-06-25 10:05] — Claude Code
- **Was:** Phase 8 **Brave-Provider live geschaltet** (CEO lieferte `BRAVE_API_KEY`). Key in `orchestrator/.env`
  (Mac + NAS, gitignored, nicht committet). Live-Smoke-Tests OK (Mac + im NAS-Container, echte Treffer).
  Zwei Fixes: (1) `web_recherche`-Handler/Bot nutzten `os.environ`, die App laedt `.env` aber in ein
  `secrets`-Dict -> `ToolContext.web` wird jetzt in `telegram/bot.py` aus `secrets` gebaut
  (`WebResearch.from_env(env=secrets, ...)`). (2) **Governance-Gate:** Der `ANTHROPIC_API_KEY` ist ohnehin da,
  daher waere die **billbare** Anthropic-Web-Suche sonst sofort „verfuegbar" -- jetzt hinter explizitem Flag
  `WEB_RESEARCH_ANTHROPIC=1` gesperrt (bleibt aus bis CEO-Kostenfreigabe; komplexe Anfragen laufen bis dahin
  ueber Brave). NAS-Code-Sync + Container-Restart; LUNA recherchiert live ueber Telegram. Suite **50/50 OK**.
- **Warum:** CEO hat Brave freigegeben (Gratis-Kontingent); Anthropic-Web bleibt kostengesperrt bis separate
  Freigabe -- kein Suchkosten-Risiko ohne ausdrueckliche Zustimmung.
- **Betroffen:** `orchestrator/governance/web_research.py` (Anthropic-Kosten-Flag), `orchestrator/channels/
  telegram/bot.py` (ToolContext.web aus secrets), `orchestrator/tests/test_web_research.py` (+Gating-Test),
  `governance/zugriffs-policy.md` (Brave live), `PHASE8_PLAN.md`. Secret nur in `.env` (NICHT versioniert).

## [2026-06-25 09:35] — Claude Code
- **Was:** Phase 8 (Web-Research / Self-Education) **offline gebaut** (Go-Live wartet auf CEO-Tor). Neues
  Modul `orchestrator/governance/web_research.py` mit Provider-Abstraktion + Router: `MockProvider` (offline,
  kostenlos), `BraveProvider` (rohe Treffer, `BRAVE_API_KEY`) und `AnthropicProvider` (agentische Recherche +
  Synthese via nativem web_search-Tool, vorhandener `ANTHROPIC_API_KEY`, lazy import). `route_komplexitaet`
  waehlt einfache Lookups -> Brave, komplexe Recherche -> Anthropic; Verfuegbarkeits-Fallback. Neues
  HoA-Tool `web_recherche(query, tiefe?)` (gated, Leck-Schutz; `ToolContext.web` injizierbar). Externe
  Inhalte werden als Daten behandelt (Injection-Schutz); ohne freigegebene Keys kommt ein Fall-B-Hinweis
  (CEO-Tor) statt Ergebnissen/Absturz. 8 Offline-Self-Checks; Gesamtsuite **49/49 OK** (vorher 41).
  Zugriffs-Policy: Capability `web_research` fuer berater+cto als „vorbereitet -- CEO-Tor offen" eingetragen.
  Plan: `PHASE8_PLAN.md`.
- **Warum:** Roadmap Phase 8 (vom CEO als naechster Schritt gewaehlt) -- Augen nach aussen fuer Berater
  (Innovations-Scouting) und IT (Self-Education); Offline-first, damit Go-Live nur noch ein Key-/Freigabe-Flip ist.
- **Betroffen:** `orchestrator/governance/web_research.py` (neu), `orchestrator/core/hoa_tools.py`
  (Tool `web_recherche` + `ToolContext.web`), `orchestrator/tests/test_web_research.py` (neu),
  `governance/zugriffs-policy.md`, `PHASE8_PLAN.md` (neu).

## [2026-06-25 09:10] — Claude Code
- **Was:** NAS-Code-Sync Mac->NAS eingerichtet und live getestet. Neues Skript `deploy/sync-to-nas.sh`
  schiebt **nur den Code** auf die NAS und startet den `luna-telegram`-Container neu. Es ueberschreibt
  **keine NAS-Live-Daten** (NAS ist Produktions-Datenquelle): `orchestrator/.env`, `finance/budget.md`,
  `orchestrator/memory/log.jsonl`, `antraege/log.jsonl`, `projekt_changelog.md` (+ `.git/`, `.venv/`,
  `.worktrees/`, Caches) sind ausgeschlossen, und es wird nichts geloescht (kein --delete). Verifiziert per
  Vorher/Nachher-`stat`: die vier Live-Dateien blieben byte-genau identisch. Flags: `--build` (Image-Rebuild
  bei Dep-Aenderung), `--no-restart`, `--dry-run`. Technik: **tar-over-ssh** statt rsync, weil macOS
  „openrsync" die Remote-Shell (-e/RSYNC_RSH/Key) nicht zuverlaessig nutzt; ssh-Key via neuem
  `~/.ssh/config`-Eintrag (`Host luna-nas`). NAS-sudo-Passwort nur fluechtig (stdin an `sudo -S`), nie im
  Repo. End-to-End getestet: Sync + Restart OK, Log „Telegram-Bot bereit.".
- **Warum:** Bei Weiterentwicklung am Mac soll der Code auf der 24/7-NAS aktuell bleiben, ohne die dort live
  geschriebenen Produktionsdaten zu gefaehrden (offener naechster Schritt laut Roadmap/Memory).
- **Betroffen:** `deploy/sync-to-nas.sh` (neu), `deploy/synology-luna-hosting.md` (Abschnitt „Code-Updates"),
  `~/.ssh/config` (neu, ausserhalb Repo; SSH-Key-Alias luna-nas).

## [2026-06-25 01:29] — Claude Code
- **Was:** LUNA-Telegram-Bot **live auf der Synology DS923+** deployed (24/7, unabhaengig vom Mac). Per SSH
  (dedizierter Key `~/.ssh/luna_nas`, Synology-Rechte gesetzt) eingerichtet: NAS-IP ist 192.168.178.129
  (LAN3; .1 war die FritzBox). Repo nach `/volume1/docker/ki-unternehmen` uebertragen (tar-over-ssh, ohne
  .venv, mit .git + orchestrator/.env) -- Home-Ordner war ungeeignet (verschluesselt/nur bei Login gemountet),
  daher Container-Manager-Ordner. Docker 24.0.2 + Compose v2 vorhanden; Image gebaut (claude-agent-sdk +
  anthropic), Container `luna-telegram` laeuft (Log „Telegram-Bot bereit.", restart unless-stopped).
  PYTHONUNBUFFERED fuer sichtbare Logs (Dockerfile + compose). Lokaler Mac-Telegram-Bot gestoppt (nur ein
  Poller pro Token); Voice-Server am Mac laeuft weiter.
- **Warum:** CEO will 24/7 von unterwegs auf LUNA zugreifen; die NAS ist dauerhaft online -- Telegram-Bot
  braucht nur ausgehendes Internet (keine Portfreigabe/HTTPS).
- **Betroffen:** `deploy/Dockerfile`, `deploy/docker-compose.yml` (NAS-Deployment; Secrets nur in
  orchestrator/.env, nicht versioniert).

## [2026-06-25 00:32] — Claude Code
- **Was:** Hosting fuer 24/7-Zugriff von aussen vorbereitet (Synology DS923+). Schlankes Docker-Deployment
  des **Telegram-Bots** (nur ausgehendes Internet -- keine Portfreigabe/HTTPS noetig): `deploy/Dockerfile`
  (python:3.12-slim + git + claude-agent-sdk + anthropic; ohne Pipecat), `deploy/docker-compose.yml`
  (Bind-Mount des Repos inkl. .git + orchestrator/.env, restart unless-stopped) und
  `deploy/synology-luna-hosting.md` (Anleitung: Repo auf NAS, Container Manager/SSH bauen+starten, testen).
  Voice-Browser von aussen (HTTPS + Reverse-Proxy + WebRTC/TURN) bewusst spaeter; Execution auf der NAS
  arbeitet auf dem NAS-Repo-Klon. Kein Code-/Verhaltensaenderung am Orchestrator.
- **Warum:** CEO will von unterwegs 24/7 auf LUNA zugreifen; die DS923+ (x86-64, Container Manager, dauerhaft
  online) ist dafuer ideal -- Telegram-Bot als einfachster, robuster Weg.
- **Betroffen:** `deploy/Dockerfile` (neu), `deploy/docker-compose.yml` (neu),
  `deploy/synology-luna-hosting.md` (neu).

## [2026-06-25 00:23] — Claude Code
- **Was:** Telegram live geschaltet + Head of Agents heisst jetzt **LUNA**. Bot-Token (@luna_headofagents_bot)
  in orchestrator/.env (gitignored), via getMe verifiziert; CEO-Chat-ID 8594240885 als
  TELEGRAM_ALLOWED_CHAT_ID gesetzt (Bot bedient nur den CEO). Name LUNA in beide System-Prompts aufgenommen
  (Voice `pipeline.py` + Text `hoa_conversation.py`). Telegram-Bot + Voice-Server gestartet (je ein Prozess);
  Self-Checks 41/41 OK.
- **Warum:** CEO hat den BotFather-Token geliefert und LUNA als Namen bestimmt; mobiler Telegram-Zugang aktiv.
- **Betroffen:** `orchestrator/channels/voice/pipeline.py`, `orchestrator/core/hoa_conversation.py`
  (Secrets nur in orchestrator/.env, nicht versioniert).

## [2026-06-25 00:07] — Claude Code
- **Was:** Phase 10 Teil A (Telegram) -- Offline-Grundlage gebaut. Neues kanal-unabhaengiges HoA-Gehirn
  `core/hoa_conversation.py` (Anthropic-Tool-Schleife, injizierbarer Client) + geteilte Werkzeugschicht
  `core/hoa_tools.py` (frage_finance, set_budget, delegate, antrag_stellen/zeigen/freigeben/ablehnen/umsetzen/
  mergen; Leck-Schutz, CEO-Tor) + `core/channels_common.py` (finance-Helfer, SSoT ueber Voice-Panels).
  Telegram-Adapter `channels/telegram/bot.py` (Long-Polling, Text + Sprachnachricht via Deepgram-STT,
  Antwort als Text; bedient nur autorisierte Chat-ID -- Sicherheits-Guard). `.env.example` um
  TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_CHAT_ID. Fuenf neue Self-Checks (`tests/test_hoa_conversation.py`:
  Tool-Loop, CEO-Tor, Finance-Inhalt, Leck-Schutz, Tool-Specs). Gesamt **41/41 OK**. Voice-Pfad bewusst
  unangetastet (spaetere Vereinheitlichung als Aufraeumschritt notiert). Handy-Browser/Hosting: vom CEO
  vorerst zurueckgestellt; echter Anruf (Twilio) bleibt Phase 10b am Ende.
- **Warum:** CEO: zuerst Telegram (mobil), Hosting/Anruf spaeter. Offline-Teil ohne Kosten; Live-Betrieb
  braucht Bot-Token (GATE).
- **Betroffen:** `orchestrator/core/hoa_conversation.py` (neu), `orchestrator/core/hoa_tools.py` (neu),
  `orchestrator/core/channels_common.py` (neu), `orchestrator/channels/telegram/*` (neu),
  `orchestrator/tests/test_hoa_conversation.py` (neu), `orchestrator/.env.example`.

## [2026-06-24 23:58] — Claude Code
- **Was:** Mobile Kontaktwege vorbereitet. CFO-Kostenvoranschlag in `finance/kosten-statistik.md`: Telegram
  praktisch fixkostenfrei (Bot-Token gratis; nur nutzungsabhaengig STT/TTS/LLM wie bisher); Handy-Browser
  24/7 = nur Hosting (kostenlos per Dev-Tunnel solange der Mac laeuft, oder ~4-8 EUR/Monat kleiner VPS;
  nicht Vercel); Telefon-Anruf via Twilio spaeter (~1 USD/Mon + ~1-2 ct/Min). Detailplan `PHASE10_PLAN.md`
  (Telegram-Adapter am kanal-agnostischen Kern mit geteiltem HoA-Gehirn inkl. Tools; Text + Sprachnachricht +
  Push; Handy-Browser via HTTPS; 5 Offline-Self-Checks; GATE = Bot-Token + Hosting-Wahl). Echter Anruf
  (Phase 10b) ans Ende verschoben. Noch KEINE Umsetzung -- wartet auf GATE.
- **Warum:** CEO: zuerst unterwegs erreichbar (Telegram + Handy-Browser), Anruf spaeter; Finance soll vorab
  Kosten schaetzen (AGENTS.md 5.9, CEO-Tor-Vorbereitung).
- **Betroffen:** `finance/kosten-statistik.md`, `PHASE10_PLAN.md` (neu).

## [2026-06-24 23:45] — Claude Code
- **Was:** Phase 7 LIVE bestanden + verdrahtet. Reale Abhaengigkeiten `core/execution_live.py`
  (Git-Worktree auf Branch `antrag/<id>`, Coding-Agent via Claude Agent SDK mit Datei-/Bash-Tools
  `permission_mode=bypassPermissions` im isolierten Worktree, Self-Checks-Runner, Diff, commit/merge/cleanup).
  **Erster echter Lauf erfolgreich:** freigegebener Test-Antrag -> Branch + Datei real angelegt
  (`docs/phase7-test.md`, Umlaut-Regel eingehalten) -> Self-Checks 36/36 gruen -> Bericht; danach
  Verifikations-Worktree/Branch aufgeraeumt (nicht in main). HoA-Tools `antrag_umsetzen` (nur freigegeben,
  Branch+Tests, kein Merge) und `antrag_mergen` (nur erledigt, nach CEO-Bestaetigung) im Voice-Kanal
  verdrahtet (`build_pipeline` + `server.py` mit `repo_root`); System-Prompt um die Ausloesungs-Nuance
  ergaenzt. ROADMAP: Phase 10b (Telefon-Anruf via Telefonie/Twilio) + Hosting-Hinweis (persistenter Host,
  nicht Vercel; HTTPS fuer mobiles Mikrofon). Self-Checks **36/36 OK**, Server-Boot verifiziert (ein Prozess).
- **Warum:** CEO: LIVE-GATE freigegeben; Frage nach Online-/mobilem Betrieb + Anrufmoeglichkeit beantwortet
  und in die Roadmap aufgenommen.
- **Betroffen:** `orchestrator/core/execution_live.py` (neu), `orchestrator/channels/voice/pipeline.py`,
  `orchestrator/channels/voice/server.py`, `ROADMAP.md`.

## [2026-06-24 23:29] — Claude Code
- **Was:** Phase 7 — Execution-Engine (Offline-Teil) gebaut. Neu `core/execution.py` (`ExecutionEngine`):
  setzt nur `freigegebene` Antraege um, mit injizierbaren Abhaengigkeiten (Workspace/Worktree, Coding-Agent,
  Tests, Diff) -> offline mit Mocks testbar. Guards: nur freigegeben; Status freigegeben -> in_umsetzung ->
  erledigt/fehlgeschlagen; Tests-Gate (rot = fehlgeschlagen); Charta-/Regel-Schutz (agents/, AGENTS.md,
  CLAUDE.md nur mit Kategorie `mandat`); Leck-Schutz im Bericht; Changelog je Transition. Sechs Mock-Self-Checks
  (`tests/test_execution.py`). `governance/execution.md` (Policy, inkl. Ausloesungs-Nuance: CEO-Auftrag =
  kurze Rueckfrage genuegt; Agenten-Idee = Plan zuerst vorlegen) und `.gitignore` (.worktrees/) ergaenzt.
  Gesamt **36/36 OK**. CEO-Designentscheidungen: Merge = beides (manuell + sprachbestaetigtes antrag_mergen);
  Ausfuehrung nach Freigabe. Noch KEINE echte Coding-Ausfuehrung -- die ist das separate Live-GATE.
- **Warum:** Roadmap Phase 7 (staerkster GATE), GATE freigegeben. Offline-Grundlage + Sicherheits-Guards vor
  dem ersten echten Branch-Lauf.
- **Betroffen:** `orchestrator/core/execution.py` (neu), `orchestrator/tests/test_execution.py` (neu),
  `governance/execution.md` (neu), `.gitignore`.

## [2026-06-24 23:21] — Claude Code
- **Was:** `PHASE7_PLAN.md` (Detailplan Execution-Engine / handelnde Agenten) angelegt: freigegebene Antraege
  werden von einem Ausfuehrungs-Agenten (Claude Agent SDK mit Coding-Tools) in einem Git-Worktree auf Branch
  `antrag/<id>` umgesetzt, Self-Checks laufen, Bericht (Diff/Tests/zu pruefen) entsteht; **kein Merge ohne
  CEO**. Sicherheits-Invarianten (nur freigegebene Antraege, Isolation/Branch, Tests-Pflicht, Werkzeug-Grenzen,
  Charta-/Governance-Schutz, CEO-Tor, Notbremse/Limits), Ablauf, Dateien, 6 Mock-Self-Checks und zwei offene
  Designfragen (Merge-Weg; Ausloesung nur auf Befehl). Noch KEINE Umsetzung -- wartet auf Phase-7-GATE.
- **Warum:** Roadmap Phase 7 (staerkster GATE): Abteilungen sollen freigegebene Aenderungen wirklich umsetzen
  (wie der CEO selbst in Claude Code) -- kontrolliert, reversibel, getestet.
- **Betroffen:** `PHASE7_PLAN.md` (neu).

## [2026-06-24 19:34] — Claude Code
- **Was:** Changelog-Integritaet repariert: 8 Eintraege hatten ueber die Sitzung ihre `## [Datum] — Akteur`-
  Kopfzeile verloren (u. a. der CFO-Budget-Eintrag und mehrere Claude-Code-Eintraege). Kopfzeilen mit den aus
  den Commits bekannten Zeitstempeln wiederhergestellt; jetzt 50/50 Header/Bodies, keine verwaisten Eintraege.
- **Warum:** `projekt_changelog.md` ist kanonisches Governance-Dokument (AGENTS.md 3.2) -- Format muss
  vollstaendig sein.
- **Betroffen:** `projekt_changelog.md`.

## [2026-06-24 19:28] — Claude Code
- **Was:** (1) Anleitung `docs/localhost-starten.md` angelegt (Start der Live-Voice-Oberflaeche, Beenden,
  Self-Checks). (2) Ursache des „technischen Fehlers" beim CTO-Auftrag „Datei anlegen" diagnostiziert: der
  delegate-Aufruf an den CTO lief in `Reached maximum number of turns (4)` -- der Agent versuchte zu HANDELN
  (Datei erstellen), was Fachagenten bis Phase 7 nicht koennen. Fix: der delegate-Handler stellt der Aufgabe
  jetzt eine Vorgabe voran (nur BERATEN/Text, kein Handeln/keine Datei-/Code-Aenderung bis zum
  Freigabe-/Execution-Workflow) -> Konsultationen liefern Text statt ins Turn-Limit zu laufen.
- **Warum:** CEO-Beobachtung: HoA meldete technischen Fehler, als der CTO eine Datei anlegen sollte. Datei-
  Erstellung durch Abteilungen ist Phase 7; bis dahin bleiben Konsultationen beratend. Die gewuenschte
  Anleitung wurde direkt von Claude Code erstellt.
- **Betroffen:** `docs/localhost-starten.md` (neu), `orchestrator/channels/voice/pipeline.py`.

## [2026-06-24 19:17] — CFO
- **Was:** Monatsbudget gesetzt: 100 EUR/Monat (CEO-Ansage)
- **Warum:** CEO-Ansage ueber Sprachkanal
- **Betroffen:** finance/budget.md

## [2026-06-24 18:18] — Claude Code
- **Was:** Phase 6 (Antrags-/Freigabe-Workflow) umgesetzt -- GATE freigegeben (Freigabe per Sprache/Text).
  Neuer event-sourced Store `core/antraege.py` (`Antraege`: stellen/freigeben/ablehnen/status_setzen, list/get
  via Event-Folding; append-only `antraege/log.jsonl`, leck-geschuetzt, Changelog je Transition). Vier neue
  HoA-Tools im Voice-Kanal: `antrag_stellen`, `antraege_zeigen` (Panel `antraege` + Kurzfassung),
  `antrag_freigeben`, `antrag_ablehnen` -- Freigabe nur nach ausdruecklicher CEO-Bestaetigung; es wird NICHTS
  ausgefuehrt (Ausfuehrung erst Phase 7). System-Prompt erweitert; `server.py` reicht den Store-Pfad durch;
  `app.js` rendert das Antraege-Panel; `governance/antraege.md` (Policy) neu; `.gitignore` um Dry-Run-Store.
  Sechs neue Self-Checks (`tests/test_antraege.py`): Round-Trip, Freigabe/Ablehnung, Event-Sourcing,
  Leck-Schutz, Changelog-Callback, Status-Filter. Gesamt **30/30 OK**; Boot verifiziert (ein Prozess).
- **Warum:** Roadmap Phase 6 (Rueckgrat der Mensch-im-Spiel-Steuerung): Abteilungen/HoA schlagen vor, der CEO
  gibt frei, erst dann (Phase 7) wird umgesetzt.
- **Betroffen:** `orchestrator/core/antraege.py` (neu), `orchestrator/tests/test_antraege.py` (neu),
  `orchestrator/channels/voice/pipeline.py`, `orchestrator/channels/voice/server.py`,
  `orchestrator/channels/voice/static/app.js`, `governance/antraege.md` (neu), `.gitignore`.

## [2026-06-24 18:12] — Claude Code
- **Was:** `ROADMAP.md` ergaenzt: Phase 5 als umgesetzt markiert; neue **Phase 14 — Oberflaechen-Erweiterung /
  generische Visualisierung** (ganz hinten) fuer frei konfigurierbare/visuelle Darstellungen, u. a.
  Organigramm/Strukturen als **MindMap** auf Anfrage (heutige Grenze: feste Panel-Typen). Neuer Detailplan
  `PHASE6_PLAN.md` (Antrags-/Freigabe-Workflow): event-sourced Store `antraege/log.jsonl`, Lebenszyklus
  (eingereicht -> freigegeben/abgelehnt -> in_umsetzung -> erledigt/fehlgeschlagen), HoA-Tools
  (antrag_stellen/antraege_zeigen/antrag_freigeben/ablehnen, Freigabe nur nach CEO-Bestaetigung),
  `antraege`-Panel, 6 Self-Checks, Governance. Noch KEINE Umsetzung -- wartet auf Phase-6-GATE.
- **Warum:** CEO: MindMap-/visuelle Darstellung muss spaeter moeglich sein -> als Oberflaechen-Erweiterung
  ganz nach hinten; mit Phase 6 (Rueckgrat) weitermachen, davor Detailplan + GATE (Roadmap-Vorgabe).
- **Betroffen:** `ROADMAP.md`, `PHASE6_PLAN.md` (neu).

## [2026-06-24 14:31] — Claude Code
- **Was:** Phase 5 (Live-Kontext & Organigramm) umgesetzt. Neues Agenten-Verzeichnis
  `channels/voice/directory.py` (eine Quelle fuer Routing, Anzeige-Labels, Organigramm). Im Gespraech zeigt
  die Oberflaeche jetzt live, mit welchem Agenten der HoA spricht: `delegate` und `frage_finance` senden
  `agent_activity`-RTVI-Events (start/end), die Browser-Seite zeigt "spricht mit <Agent>" und hebt die
  Abteilung im Organigramm hervor. Neuer Panel-Typ `organigramm` (CEO -> HoA -> 14 Abteilungen) via
  `show_panel(typ='organigramm')`; `panels.build_panel` + `app.js`/`index.html` rendern ihn. `pipeline._AGENTS`
  wird aus dem Verzeichnis abgeleitet (keine Dublette). Self-Checks 24/24 OK; Boot verifiziert.
- **Warum:** GATE D freigegeben, Start mit Phase 5 (Roadmap): sichtbarer Quick Win -- der CEO sieht im
  Gespraech den relevanten Kontext und mit welchem exakten Agenten der HoA gerade kommuniziert.
- **Betroffen:** `orchestrator/channels/voice/directory.py` (neu), `orchestrator/channels/voice/pipeline.py`,
  `orchestrator/channels/voice/panels.py`, `orchestrator/channels/voice/static/app.js`,
  `orchestrator/channels/voice/static/index.html`.

## [2026-06-24 14:23] — Claude Code
- **Was:** `ROADMAP.md` angelegt: Ablaufplan mit GATES vom aktuellen Stand zum selbst-entwickelnden
  Agenten-Unternehmen (24/7-Assistent). Phasen 5-13: Live-Kontext/Organigramm, Antrags-/Freigabe-Workflow
  (Rueckgrat), Execution-Engine (handelnde Agenten auf Git-Branch + Tests), Web-Research, Innovations-Pipeline
  (Berater), Telegram-Kanal, E-Mail/Kalender, Durable Task-Queue + Scheduler (24/7, fortsetzbar bei
  Limit), Self-Development-Loop. Invarianten: Mensch-Freigabe hart, Aenderungen nur auf Branch+Tests+Rollback,
  Selbst-Modifikation nur via freigegebenem Antrag, Kosten/Secrets governt. Enthaelt ehrliche Luecken-Analyse
  („was fehlt zum Selbst-Entwickeln") und GATES-Uebersicht. Noch KEINE Umsetzung -- wartet auf GATE D.
- **Warum:** CEO-Auftrag: klarer Plan mit Gates Richtung selbst-aufbauendes/-verbesserndes System.
- **Betroffen:** `ROADMAP.md` (neu).

## [2026-06-24 09:08] — Claude Code
- **Was:** (1) Konsultation fuer ALLE Fachagenten vorbereitet: `core/subagents.load_all_subagents()` laedt
  alle 14 Charten als konsultierbare Spezialisten (berater, cao, cfo, cro, ciso, cbo, cpo, cto, cxo, cco,
  cdo, chro, clo, cko); der Voice-Server nutzt sie, und das `delegate`-Tool akzeptiert jetzt jeden dieser
  Spezialisten (HoA kuendigt an + fasst Ergebnis gesprochen zusammen). (2) Budget per Sprache: neues Tool
  `set_budget(betrag_eur)` -- der HoA traegt das vom CEO genannte Monatsbudget ueber den CFO in
  `finance/budget.md` ein (`panels.set_monatsbudget`: aktualisiert Monatsbudget + Gueltig-ab + Historienzeile,
  .md bleibt ASCII), mit gesprochener Rueckbestaetigung der Zahl und Changelog-Eintrag (Akteur CFO,
  CEO-Ansage). Self-Checks 24/24 OK; Budget-Schreiben auf Kopie verifiziert.
- **Warum:** CEO-Wunsch: inhaltliche Auskuenfte nicht nur fuer Finance, sondern fuer alle Agenten; und das
  Budget per Sprache ansagen, das der CFO dann in budget.md eintraegt (Governance 5.9: CEO legt Budget fest).
- **Betroffen:** `orchestrator/core/subagents.py`, `orchestrator/channels/voice/pipeline.py`,
  `orchestrator/channels/voice/panels.py`, `orchestrator/channels/voice/server.py`.

## [2026-06-24 09:01] — Claude Code
- **Was:** HoA kann jetzt zu Finance-INHALTEN sprechen (nicht nur Panel einblenden). `show_panel` liefert dem
  HoA zusaetzlich den Inhalt zurueck (`finance_summary` aus finance/: Budget-Status + Kostenstatistik). Neues
  Tool `frage_finance(frage)` -- der HoA holt damit die echten Zahlen aus finance/ (Domaene des CFO) und
  antwortet inhaltlich; System-Prompt instruiert ihn, kurz anzukuendigen ("Einen Moment, ich schaue bei
  Finance nach.") und konkrete Werte/Status zu nennen. Neue Funktion `panels.finance_summary` (+ `_plain`),
  leck-geschuetzt. Tools jetzt: show_panel, frage_finance, delegate. Self-Checks 24/24 OK; Boot verifiziert
  (ein Prozess).
- **Warum:** CEO-Feedback: der HoA blendete die Kostenuebersicht ein, konnte den Inhalt aber nicht
  sprachlich wiedergeben. Gewuenscht: Nachfragen bei Finance + inhaltliche Auskunft.
- **Betroffen:** `orchestrator/channels/voice/pipeline.py`, `orchestrator/channels/voice/panels.py`.

## [2026-06-24 08:50] — Claude Code
- **Was:** Stimmen-Fehler behoben. ElevenLabs-Streaming (Pipecat nutzt die Websocket-API) akzeptiert nur
  Stimmen, die **im Account** sind -- Library-Stimmen muessen einmalig hinzugefuegt werden (der fruehere
  REST-Test war irrefuehrend; die erste Konversation lief nur, weil die Default-Stimme eine Account-Stimme
  war). Alle 8 kuratierten deutschen Stimmen dem ElevenLabs-Account hinzugefuegt (voice_id bleibt dabei
  gleich -> `voices.py` unveraendert korrekt). Zusaetzlich Client-Fehlermeldung verbessert: zeigt jetzt den
  echten Text statt "[object Object]". Verifiziert: alle 8 Stimmen jetzt im Account.
- **Warum:** CEO meldete "Pipecat-Fehler" beim Wechsel auf Lola -- Ursache: "voice does not exist" im
  Streaming, da die Library-Stimme nicht im Account war.
- **Betroffen:** ElevenLabs-Account (8 Stimmen hinzugefuegt), `orchestrator/channels/voice/static/app.js`.

## [2026-06-24 08:41] — Claude Code
- **Was:** Deutsche Stimme + Stimmen-Dropdown. Ursache des englischen Akzents war die Platzhalter-Stimme
  (Rachel, US-englisch); mehrsprachiges Modell + `language=de` waren korrekt. Neu `voices.py` mit 8
  kuratierten **deutschen** Stimmen (ElevenLabs Voice Library, direkt per voice_id nutzbar -- per Test
  bestaetigt) inkl. Beschreibungen; Auswahl wird in `selected_voice.json` (gitignored) gespeichert.
  `pipeline.build_tts` nutzt die gespeicherte Auswahl. Server-Endpoints `GET /api/voices` und
  `POST /api/voice`; Oberflaeche um ein **Dropdown mit Beschreibung** ergaenzt (vor dem Gespraech waehlbar,
  wird beim naechsten Gespraech aktiv). Self-Checks 24/24 OK; Endpoints + Boot verifiziert.
- **Warum:** CEO-Feedback: Stimme klang teils englisch akzentuiert; Wunsch nach umschaltbarer, speicherbarer
  Stimme zum Durchprobieren.
- **Betroffen:** `orchestrator/channels/voice/voices.py` (neu), `orchestrator/channels/voice/pipeline.py`,
  `orchestrator/channels/voice/server.py`, `orchestrator/channels/voice/static/index.html`,
  `orchestrator/channels/voice/static/app.js`, `.gitignore`.

## [2026-06-24 08:28] — Claude Code
- **Was:** Live-Voice zu echtem Conversation-Loop umgebaut (CEO-Entscheidung: direkt antworten + bei Bedarf
  delegieren; schnelles Modell). `pipeline.py` nutzt jetzt Pipecat-nativ ein streamendes Anthropic-LLM als
  HoA (`AnthropicLLMService`, Modell `claude-haiku-4-5`) mit Context-Aggregatoren (Gespraechsgedaechtnis) und
  Function-Calling: `show_panel(typ)` (Kostenuebersicht aus finance/ via RTVI-Server-Message an den Browser)
  und `delegate(aufgabe, an)` (CTO/Berater ueber den Opus-Kern, mit CEO-Tor-Pruefung + Changelog). Dadurch
  Barge-in, Streaming und niedrige Latenz **nativ**; der HoA antwortet kurz/gesprochen und delegiert nur bei
  echten Aufgaben. Panels laufen ueber `RTVIProcessor`/`RTVIObserver`/`RTVIServerMessageFrame` (zuverlaessig
  an `onServerMessage`). `server.py` reicht den HoA-Kern an die Pipeline; `config.toml [voice].llm_model`.
  Tool-/LLM-/Context-/RTVI-APIs gegen Pipecat 1.4.0 verifiziert; Server-Boot bestaetigt (HTTP 200, ein
  Prozess). Offline-Self-Checks 24/24 OK. (`AnthropicLLMService` via `pip install pipecat-ai[anthropic]`.)
- **Warum:** CEO-Ziel: natuerliches Vollduplex-Gespraech (Reinreden jederzeit) mit smart zusammengefassten
  Antworten -- statt blockierender Einzelauftrags-Verarbeitung mit vorgelesenem Bundle-Rahmen. Tool-Frage
  geklaert: Pipecat ist das richtige Werkzeug; OpenJarvis ist ein textbasiertes Agenten-Framework ohne
  Echtzeit-Voice/Barge-in -- kein Wechsel.
- **Betroffen:** `orchestrator/channels/voice/pipeline.py`, `orchestrator/channels/voice/server.py`,
  `orchestrator/config.toml`, `orchestrator/channels/voice/requirements.txt` (anthropic-Extra).

## [2026-06-24 02:53] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Was sind deine Aufgaben?
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater

## [2026-06-24 02:53] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Was sind deine Aufgaben?
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater

## [2026-06-24 02:50] — Claude Code
- **Was:** Live-Voice Stabilitaet + Sprechqualitaet. (1) Reconnect-Loop (alle ~10 s `clearing track`, neue
  Pipeline, abgeschnittene laengere Antworten): Client-Verbindung von der veralteten `connection_url`-API auf
  die aktuelle umgestellt -- `new SmallWebRTCTransport({ iceServers })` + `connect({ webrtcUrl: "/api/offer" })`.
  (2) Gesprochener Text war der komplette Bundle-Rahmen ("Konsolidierte Antwort an den CEO: Auftrag: ..."):
  neue `_voice_clean()` in `bridge.py` spricht nur die eigentliche Antwort (ohne Rahmen/Agenten-Praefix/grobes
  Markdown); CEO-Tor-Antworten bleiben unveraendert. Self-Checks 24/24 OK (Kanal-Gleichheit auf Antwortinhalt
  umgestellt).
- **Warum:** CEO-Sprachtest: kurze Antwort (Kostenübersicht) hoerbar, laengere abgeschnitten; anderer
  Frageninhalt wurde verarbeitet, aber durch Reconnects nicht sauber ausgegeben.
- **Betroffen:** `orchestrator/channels/voice/static/app.js`, `orchestrator/channels/voice/bridge.py`,
  `orchestrator/tests/test_voice_bridge.py`.

## [2026-06-24 02:43] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Was sind deine Aufgaben?
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater

## [2026-06-24 02:43] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Was sind deine Aufgaben?
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater

## [2026-06-24 02:43] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Kannst Du einmal deine Aufgaben zusammenfassen?
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater

## [2026-06-24 02:41] — Claude Code
- **Was:** Live-Voice Audio-Wiedergabe ergaenzt. Log-Befund: die Pipeline laeuft vollstaendig (Deepgram-STT
  verbindet, HoA antwortet, ElevenLabs erzeugt Sprache), aber der Browser-Client spielt die empfangene
  Bot-Audiospur nicht automatisch ab. In `static/app.js` `onTrackStarted(track, participant)`-Callback
  ergaenzt: haengt die Bot-Audiospur (nicht das eigene Mikrofon) an ein `<audio autoplay>`-Element ->
  hoerbare Ausgabe. Additive Aenderung, Verbindungslogik unveraendert. Ausserdem Betriebshinweis: stets
  GENAU EIN Server-Prozess auf Port 7860 -- doppelte Prozesse fuehren zu Reconnect-Schleifen und
  "clearing track"-Warnungen (Offer/PATCH landen bei wechselnden Prozessen, pc_id unbekannt).
- **Warum:** CEO-Sprachtest: Zustaende wechselten und TTS lief, aber keine hoerbare Ausgabe.
- **Betroffen:** `orchestrator/channels/voice/static/app.js`.

## [2026-06-24 02:35] — Claude Code
- **Was:** Live-Voice 422 (Offer/PATCH) behoben. Zwei Ursachen: (1) Mehrere Server-Prozesse hingen
  gleichzeitig auf Port 7860 -- ein alter (typisierter) Stand beantwortete die Requests; hart aufgeraeumt.
  (2) Eigentlicher Bug: `from __future__ import annotations` in `server.py` machte die Routen-Annotationen
  zu Strings, sodass FastAPI `Request`/`BackgroundTasks` nicht als Injektion erkannte und sie als fehlende
  Query-Parameter ablehnte (422 "missing query raw"). Future-Import entfernt (3.14 hat `str | None` nativ);
  zusaetzlich Offer/PATCH auf robustes rohes Body-Parsing umgestellt (camelCase<->snake_case, ICE-Candidates
  sdpMid/sdpMLineIndex). Verifiziert: direkter POST erreicht jetzt den Handler (Log `offer keys: [sdp, type]`,
  kein 422 mehr; 500 nur bei absichtlich ungueltigem Test-SDP).
- **Warum:** CEO-Sprachtest scheiterte mit 422 auf POST/PATCH; Verbindung kam nie zustande.
- **Betroffen:** `orchestrator/channels/voice/server.py`.

## [2026-06-24 02:24] — Claude Code
- **Was:** Live-Voice: kein Ton behoben. Ursache: der SmallWebRTC-Client schickt nach dem Offer ein
  **PATCH /api/offer** zur Audio-Renegotiation; unser Server kannte nur POST -> 405 -> Bot-Audiospur wurde
  nie ausgehandelt (stumm). `server.py` auf Pipecats `SmallWebRTCRequestHandler` umgestellt: POST via
  `handle_web_request` (Transport/Pipeline im connection-callback, Bot als BackgroundTask), PATCH via
  `handle_patch_request` (pc_id/Renegotiation). PATCH liefert jetzt 422 statt 405 (Methode akzeptiert).
- **Warum:** CEO-Sprachtest: Verbindung + Pipeline liefen (Zustaende wechselten), aber keine Audioausgabe.
- **Betroffen:** `orchestrator/channels/voice/server.py`.

## [2026-06-24 02:17] — Claude Code
- **Was:** Live-Voice Browser-Client repariert + Umlaut-Konvention fuer die Agenten-Oberflaeche. (1) Bugfix:
  Die Pipecat-JS-Hauptklasse heisst `PipecatClient` (nicht `RTVIClient`); `static/app.js` entsprechend
  umgestellt (Import aus `@pipecat-ai/client-js`, Transport aus `@pipecat-ai/small-webrtc-transport`,
  Verbindung via `connect({ connection_url: "/api/offer" })`, robuste Callbacks + Fehlerausgabe). Behebt den
  Konsolen-Fehler "does not provide an export named 'RTVIClient'", durch den der Start-Button nichts tat.
  (2) Neue Konvention: **Anzeige-/Kommunikationstexte der Agenten-Oberflaeche nutzen echte Umlaute (ae->ä,
  oe->ö, ue->ü, ss->ß)**; Code-Bezeichner/Protokoll-Keys, Dateipfade und `.md`-Dateien bleiben ASCII.
  Umgesetzt in `app.js`/`index.html` (Buttons, Zustaende hört zu/denkt/spricht), `bridge.py` (gesprochene
  Texte) und `panels.py` (Panel-Titel/Hinweis); Protokoll-Key `type=kostenuebersicht` bleibt ASCII.
  Self-Check-Assertion angepasst. Self-Checks 24/24 OK. Server neu gestartet, liefert korrigiertes app.js.
- **Warum:** CEO-Test: Start-Button reagierte nicht (falscher JS-Export). Zusaetzlich CEO-Vorgabe: in der
  Agenten-Kommunikation/Oberflaeche Umlaute verwenden (nicht in Code/.md).
- **Betroffen:** `orchestrator/channels/voice/static/app.js`, `static/index.html`,
  `orchestrator/channels/voice/bridge.py`, `orchestrator/channels/voice/panels.py`,
  `orchestrator/tests/test_voice_bridge.py`.

## [2026-06-24 01:05] — Claude Code
- **Was:** Voice-Builder gegen die echten Provider-APIs (Pipecat 1.4.0) finalisiert: Deepgram-STT nutzt
  `settings=DeepgramSTTService.Settings(model="nova-2", language="de", smart_format=True)` statt des
  veralteten dict-`live_options`; ElevenLabs-TTS nutzt `settings=ElevenLabsTTSService.Settings(voice=...,
  model="eleven_turbo_v2_5", language="de")` mit Default-Stimme (multilingual) -> keine Deprecations mehr
  aus eigenem Code. Mit den hinterlegten Keys konstruieren STT und TTS fehlerfrei (kostenlos, kein Netz beim
  Init). Damit sind alle Live-API-Details verifiziert; offen bleibt nur der echte Sprachtest (Mikrofon/Browser,
  billbar). Offline-Self-Checks 24/24 OK.
- **Warum:** Letzte GATE-Absicherung vor dem Sprachtest -- Provider-Wiring an der installierten Version
  bestaetigt, nicht geraten.
- **Betroffen:** `orchestrator/channels/voice/pipeline.py`. (Keys liegen in `orchestrator/.env`, gitignored.)

## [2026-06-24 00:44] — Claude Code
- **Was:** Phase-2-GATE vorbereitet/teilverifiziert. CEO-Wahl TTS = **ElevenLabs** (`config.toml [voice]`
  tts_provider). Pipecat 1.4.0 + Extras installiert (`webrtc,deepgram,silero,elevenlabs`) sowie
  fastapi/uvicorn. Laufzeit-Importe gegen die installierte Version verifiziert und korrigiert:
  `StartInterruptionFrame` entfaellt (Barge-in macht die Pipeline via allow_interruptions selbst),
  Transport-Message heisst `OutputTransportMessageUrgentFrame`; SmallWebRTC-Signaling (`initialize`/
  `get_answer`) bestaetigt. **Kostenloser Boot-Test bestanden:** Server startet und liefert Browser-Seite
  und app.js (HTTP 200) aus -- ohne STT/TTS (Keys erst bei Verbindungsaufbau noetig). Neu:
  `channels/voice/requirements.txt`; Install-Hinweis in `server.py` ergaenzt. Offline-Self-Checks 24/24 OK.
- **Warum:** Vor dem echten Sprachtest die Laufzeit-API gegen das installierte Pipecat absichern (kein
  Raten) und den nicht-billbaren Teil (Server-Boot/UI) verifizieren. Echter Sprachtest = letzter
  GATE-Schritt: Keys (DEEPGRAM_API_KEY, ELEVENLABS_API_KEY) eintragen, im Browser sprechen.
- **Betroffen:** `orchestrator/channels/voice/pipeline.py`, `orchestrator/channels/voice/server.py`,
  `orchestrator/channels/voice/requirements.txt` (neu), `orchestrator/config.toml`.

## [2026-06-24 00:36] — Claude Code
- **Was:** Phase 2 (Live-Voice-Oberflaeche, Browser) -- Offline-Teil gebaut und getestet, Laufzeit-Teil
  als GATE-verifiziertes Geruest. Neuer Kanal-Adapter `orchestrator/channels/voice/`: `bridge.py`
  (framework-unabhaengige Andockstelle Sprache<->HoA-Kern; reine Anzeige-Wuensche lesend ohne Tor, sonst
  durch den HoA-Kern), `panels.py` (show_panel: `kostenuebersicht` aus `finance/`, `tabelle`,
  `text/markdown`; leck-geschuetzt), `pipeline.py` (Pipecat-Pipeline STT -> Bruecke -> TTS, WebRTC,
  Barge-in; HoA-Kern im Executor gegen Event-Loop-Verschachtelung), `server.py` (SmallWebRTC lokal +
  FastAPI, statische Seite; bricht ohne Pipecat mit Install-Hinweis ab), `static/index.html`+`app.js`
  (minimale Oberflaeche: Zustaende hoert zu/denkt/spricht + Panel-Bereich, Pipecat-JS-Client via CDN).
  Fuenf neue Self-Checks (`tests/test_voice_bridge.py` + Intent-Test): Bruecke offline, Kanal-Gleichheit
  Terminal==Voice, show_panel inkl. kostenuebersicht, Leck-Schutz in Panels, CEO-Tor im Voice-Pfad.
  Gesamt **24/24 OK**. `config.toml [voice]` (Provider/Port/Sprache), `.env.example` um Voice-Keys
  (Capability-Muster), `governance/schnittstellen.md` (Live-Voice jetzt, Roadmap Stufe 2/3),
  `finance/kosten-statistik.md` (geschaetzte Voice-Kosten, niedriger Centbereich/Min; Dominanz Opus).
- **Warum:** CEO-Auftrag Phase 2. STT/TTS = neue kostenpflichtige Dienste (CEO-Tor); dieser Build ist die
  Freigabe, der echte Sprachtest folgt am GATE (Provider-Wahl + Keys). WebRTC-Transport lokal/kostenlos.
  HoA-Kern unveraendert (nur Ein-/Ausgabe ergaenzt). Pipecat-Importe lazy; exakte API wird am GATE gegen
  die installierte Version bestaetigt.
- **Betroffen:** `orchestrator/channels/voice/*` (neu), `orchestrator/tests/test_voice_bridge.py` (neu),
  `orchestrator/config.toml`, `orchestrator/.env.example`, `governance/schnittstellen.md`,
  `finance/kosten-statistik.md`.

## [2026-06-23 20:08] — Claude Code
- **Was:** Phase 1 (Auto-Memory-Isolation) abgeschlossen. Hebel ermittelt: ENV-Variable
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY` (aus dem CLI-Binary extrahiert). Strukturell verifiziert ueber die
  `init`-Nachricht: ohne Variable `memory_paths = {"auto": ".../memory/"}`, mit `=1` `memory_paths = null`.
  In `core/backends.py` gesetzt (`ClaudeAgentOptions.env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}`; SDK merged
  ueber `os.environ`, PATH/Key bleiben). Danach zwei echte Auftraege live gefahren (Latenz-Strategie, dann
  deren Risiken): (a) Isolation greift auch im Verhalten -- die Antworten zitieren das persoenliche
  Claude-Code-Memory nicht mehr; (b) das dateibasierte Gedaechtnis traegt -- der zweite Auftrag bezog sich
  praezise auf die im ersten skizzierte Strategie. Kanonischer Store `orchestrator/memory/log.jsonl` mit zwei
  Eintraegen (kein persoenlicher Memory-Inhalt, leck-geschuetzt). Self-Checks 18/18 OK; `dry_run` wieder true.
- **Warum:** CEO-Auftrag Phase 1: Isolation zuerst strukturell bestaetigen, erst dann echte Auftraege.
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/memory/log.jsonl` (neu, kanonischer Store).

## [2026-06-23 20:07] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Nenne die zwei groessten Risiken der eben besprochenen Latenz-Strategie aus dem vorherigen Auftrag -- technisch und strategisch.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 20:06] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Skizziere kurz eine schlanke technische Strategie, wie wir die Latenz unseres Prozesses senken. Der CTO liefert die technische Sicht, der Berater die strategische.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 19:38] — Claude Code
- **Was:** Schritt B implementiert (GATE C freigegeben): dateibasiertes Agenten-Gedaechtnis. Neu
  `orchestrator/core/memory.py` (`Memory` mit append-only JSONL, `recall` = letzte N + stichwort-relevante
  aeltere ohne Embeddings, `render_context`, Leck-Schutz via `redact`; `MemoryRecord` mit Feldern
  ts/session_id/instruction/delegated_to/status/result_digest/eskalationen/tags). `core/hoa.py` verdrahtet:
  Recall wird vor der Delegation als „Gedaechtnis-Kontext" dem Subagenten-Auftrag vorangestellt (Tor/Routing
  nutzen den Original-Auftrag), nach dem Buendeln ein Eintrag (Status ok|mit_fehler|eskalation). `run.py`
  erzeugt den Store (Dry-Run -> `memory/log_dryrun.jsonl`, gitignored; Live -> `memory/log.jsonl`).
  `config.toml [memory]` (enabled/path/recall_limit), `.gitignore` um Dry-Run-Store ergaenzt.
  Doku: `orchestrator/memory/README.md`, `governance/gedaechtnis.md` (Policy: Abgrenzung zum Changelog,
  Isolation vom persoenlichen Claude-Code-Memory, Leck-Schutz, Retention). Sechs neue Self-Checks
  (`tests/test_memory.py`): Round-Trip, Relevanz, Leck-Schutz, HoA-Integration, Dry-Run-Trennung, Isolation.
  Gesamt **18/18 OK**. Dry-Run-Smoke bestaetigt: zweiter Auftrag sieht den Kontext des ersten; kanonischer
  Store bleibt sauber. Offline, ohne Kosten.
- **Warum:** CEO-Freigabe GATE C; Umfang schlank/dateibasiert gemaess `MEMORY_PLAN.md`. Offene Ausbaustufen
  (Abschalten des CLI-Auto-Memory in Live-Subagenten, semantische Suche, Supabase) bleiben spaeteren GATES
  vorbehalten.
- **Betroffen:** `orchestrator/core/memory.py` (neu), `orchestrator/core/hoa.py`, `orchestrator/run.py`,
  `orchestrator/config.toml`, `.gitignore`, `orchestrator/memory/README.md` (neu),
  `governance/gedaechtnis.md` (neu), `orchestrator/tests/test_memory.py` (neu).

## [2026-06-23 19:31] — Claude Code
- **Was:** `MEMORY_PLAN.md` (Plan-Dokument) fuer Schritt B angelegt: schlankes, dateibasiertes,
  git-versioniertes Agenten-Gedaechtnis (`orchestrator/memory/log.jsonl`, append-only), abgegrenzt vom
  Changelog, mit Lese-Pfad (`recall` vor Delegation) und Schreib-Pfad (`append` nach Buendeln), Leck-Schutz,
  Dry-Run-Trennung und Isolation vom persoenlichen Claude-Code-Memory (inkl. Abschalten des CLI-Auto-Memory in
  Subagenten). Sechs neue Self-Checks geplant (Ziel >= 18/18). Kein externer Dienst -> kein CEO-Tor, keine
  Kosten. GATE C = Freigabe dieses Plans; danach Offline-Implementierung. Noch KEIN Memory-Laufzeit-Code.
- **Warum:** CEO-Entscheidung: mit B (Kontext & Gedaechtnis) weitermachen, Umfang schlank/dateibasiert,
  Vorgehen Plan-erst (GATE).
- **Betroffen:** `MEMORY_PLAN.md` (neu).

## [2026-06-23 16:12] — Claude Code
- **Was:** GATE B **bestanden**: der echte Mini-Lauf laeuft nach Guthaben-Aufladung vollstaendig durch
  (CEO -> HoA -> echte Opus-Aufrufe an CTO und Berater -> eine konsolidierte Antwort; HoA-Auto-Changelog
  16:05/16:08). Vorher trat `Reached maximum number of turns (1)` auf, weil die gebundelte CLI vollen
  Projekt-/Skill-Kontext laedt und das Modell den einzigen Turn fuer Tool-Versuche verbraucht. Fix in
  `core/backends.py`: Subagenten laufen jetzt schlank -- `setting_sources=[]` (kein Projekt-CLAUDE.md/Skills),
  `mcp_servers={}` + `strict_mcp_config=True` (keine externen MCP), `max_turns` konfigurierbar
  (`config.toml [run] max_turns`, Default 4; in `run.py` durchgereicht). Senkt zugleich den Kontext-Overhead.
  Self-Checks weiterhin **12/12 OK**. `dry_run` wieder auf `true` gesetzt (sicherer Default; fuer Live-Lauf
  diese eine Zeile auf false). Ausserdem drei Changelog-Kopfzeilen (14:40, 15:06, 15:29) wiederhergestellt,
  die durch fehlerhaft formulierte vorherige Edits (Anker-Header im Ersatztext nicht erneut eingefuegt)
  verloren gegangen waren -- Format gemaess AGENTS.md 3.2 wieder vollstaendig.
- **Warum:** CEO-Freigabe fuer GATE B; Guthaben aufgeladen. Live-Pfad sollte vor dem naechsten Schritt
  (Agenten-Gedaechtnis) verifiziert und stabil sein.
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/run.py`, `orchestrator/config.toml`,
  `projekt_changelog.md` (Kopfzeilen-Reparatur).

## [2026-06-23 16:08] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Skizziere kurz, wie wir die Beobachtbarkeit des Orchestrators technisch verbessern (Logging, Infrastruktur) und welcher strategische Nutzen fuer unsere Prozesse und Effizienz daraus entsteht. Der CTO liefert die technische Sicht, der Unternehmensberater die strategische -- buendle beides zu EINER Empfehlung.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 16:05] — Head of Agents
- **Was:** Auftrag mit Fehler(n) bearbeitet: Skizziere kurz, wie wir die Beobachtbarkeit des Orchestrators technisch verbessern (Logging, Infrastruktur) und welcher strategische Nutzen fuer unsere Prozesse und Effizienz daraus entsteht. Der CTO liefert die technische Sicht, der Unternehmensberater die strategische -- buendle beides zu EINER Empfehlung.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 15:52] — Claude Code
- **Was:** Robustheit des Live-Pfads: SDK-/CLI-/API-Fehler werden nicht mehr als Traceback durchgereicht.
  Neue Ausnahme `BackendError` in `core/backends.py`; `AgentSdkBackend` faengt SDK-Ausnahmen und erzeugt eine
  umlautfreie, CEO-taugliche Meldung (`_readable_error`, mit Hinweis bei erkennbarem Guthaben-/Auth-/Modell-
  Problem -- da das SDK den konkreten API-Grund verwirft, sonst Auflistung der haeufigen Ursachen). `core/hoa.py`
  faengt `BackendError` je Delegation ab, schreibt das Ergebnis als `FEHLER: ...` in die konsolidierte Antwort,
  startet bei echten Fehlern keinen CTO-Workaround und kennzeichnet den Changelog wahrheitsgemaess
  („erfolgreich" vs. „mit Fehler(n)"). Zwei neue Self-Checks (`tests/test_backend_fehler.py`). Self-Checks
  jetzt **12/12 OK** (vorher 10/10; MockBackend-Verhalten unveraendert).
- **Warum:** Beim GATE-B-Mini-Lauf brach der Orchestrator bei „Credit balance is too low" mit Traceback ab;
  CEO-Anweisung: saubere Meldung statt Traceback. Robustheit fuer den naechsten Live-Lauf nach Guthaben-Aufladung.
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/core/hoa.py`,
  `orchestrator/tests/test_backend_fehler.py` (neu).

## [2026-06-23 15:29] — Claude Code
- **Was:** GATE-B-Mini-Lauf vorbereitet und erstmals real versucht. `claude-agent-sdk` (0.2.107) im venv
  installiert; Claude-CLI lokalisiert (`~/.npm-global/bin/claude`, 2.1.186; das SDK nutzt jedoch seine
  mitgelieferte gebundelte CLI gleicher Version). `orchestrator/.env` aus der Vorlage angelegt und
  `ANTHROPIC_API_KEY` eingetragen (gitignored, nie committet). GitHub-Remote `origin`
  (https://github.com/hsvnils/agent-OS.git) angebunden, Token sicher in der macOS-Keychain (nicht in
  `.git/config`), `main` gepusht. Live-Lauf (dry_run voruebergehend false): (1) Erste Test-Anweisung mit dem
  Wort „Kostenschaetzung" wurde korrekt vom CEO-Tor (Kategorie geld) **vor** jeder Delegation blockiert und in
  eine Freigabe-Anfrage verwandelt -- Governance greift real, kein Modellaufruf. (2) Zweite, tor-freie
  Anweisung erreichte den echten SDK-Pfad; die Anthropic-API antwortete mit HTTP 400 „Credit balance is too
  low". Wiring (Auth via API-Key, Modell, CLI, SDK, Delegation) ist damit verifiziert; einziger Blocker ist
  das **zu niedrige Guthaben des Anthropic-API-Kontos**. `config.toml` wieder auf `dry_run = true`
  zurueckgesetzt (sicherer Default; fuer den Live-Lauf nach Guthaben-Aufladung nur diese eine Zeile auf false).
- **Warum:** CEO-Freigabe fuer GATE B und Repo-Anbindung erteilt. Beobachtung fuer CFO/Budget: jeder
  CLI-basierte Agent-Turn laedt den vollen Claude-Code-Kontext (Skills/Memory, ~10k Cache-Tokens) -> grob
  ~0,12 USD Overhead pro Aufruf; spaeter optimierbar (minimaler System-Prompt, Skills/MCP in der SDK-Session
  abschalten oder fuer Subagenten die `anthropic`-API direkt nutzen).
- **Betroffen:** `orchestrator/config.toml` (netto unveraendert), `orchestrator/.env` (neu, nicht versioniert),
  Git-Remote `origin` (neu), Keychain (Token). Kein Quellcode geaendert.

## [2026-06-23 15:06] — Claude Code
- **Was:** Git-Hygiene: `.gitattributes` neu angelegt (`* text=auto eol=lf` zur Zeilenenden-Normalisierung,
  `*.xmind binary`). `.gitignore` um macOS-`.DS_Store` (auch `**/.DS_Store`) ergaenzt; die ungetrackten
  `.DS_Store` und `orchestrator/.DS_Store` aus dem Arbeitsbaum entfernt. `git add --renormalize .` ausgefuehrt
  — alle getrackten Textdateien sind bereits LF, keine Inhaltsaenderung noetig.
- **Warum:** Wechsel von Windows auf macOS; Zeilenenden plattformneutral fixieren und OS-Cruft vom Repo
  fernhalten, bevor GATE B beginnt.
- **Betroffen:** `.gitattributes` (neu), `.gitignore`.

## [2026-06-23 14:40] — Claude Code
- **Was:** GATE-B-Vorbereitung: `AgentSdkBackend` echt implementiert, gebaut gegen die verifizierten Bindings
  des Claude Agent SDK (`query`, `ClaudeAgentOptions`, `HookMatcher`, `AssistantMessage`/`TextBlock`;
  PreToolUse-Hook mit `permissionDecision: deny` fuer CEO-Tor). Lazy import, damit die Offline-Self-Checks
  ohne SDK gruen bleiben (weiterhin 10/10 OK). `run.py` verdrahtet das Backend inkl. CEO-Tor-Hook;
  `orchestrator/README.md` um GATE-B-Voraussetzungen ergaenzt (claude-agent-sdk, Claude CLI,
  ANTHROPIC_API_KEY; Live-Lauf ist billbar).
- **Warum:** SDK-Bindings waren nach kurzer Nichtverfuegbarkeit des Klassifizierers per WebFetch verifizierbar;
  damit kann der echte Mini-Lauf am GATE B ohne geratene API-Namen erfolgen. Ausfuehrung erst nach
  CEO-Freigabe (Key + billbarer Lauf).
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/run.py`, `orchestrator/README.md`.

## [2026-06-23 14:30] — Claude Code
- **Was:** Orchestrator Phase 2-4 (lauffaehiger, offline getesteter Kern) umgesetzt: `core/charter_loader.py`
  (Charta -> System-Prompt, Single Source of Truth), `core/subagents.py` (CTO+Berater aus Charten),
  `core/routing.py` (Delegation + CEO-Tor-Erkennung), `core/backends.py` (MockBackend jetzt; AgentSdkBackend
  als markierter Stub bis GATE B), `core/hoa.py` (kanal-agnostischer Kern: Auftrag -> delegieren -> EINE
  Antwort, mit CEO-Tor-Vorpruefung, Eskalation an CTO, Changelog, Leck-Schutz), Kanal-Adapter
  (`channels/base.py`, `terminal.py`, `mock.py`), Governance (`governance/ceo_gate_hook.py`,
  `changelog_tool.py` umlautfrei, `capability.py` Fall A/B, `leak_guard.py`), Beobachtbarkeit
  (`observability/logging.py`), Einstieg `run.py`. Sechs Self-Checks (`orchestrator/tests/`, unittest)
  **real ausgefuehrt: 10/10 OK** (Durchstich, Kanal-Abstraktion, Autonomie, Eskalation, Secret-Governance,
  Changelog). Dry-Run schreibt in separates `orchestrator/logs/changelog_dryrun.md` (gitignored), damit das
  kanonische Changelog sauber bleibt.
- **Warum:** GATE A freigegeben; Python 3.12.10 nun verfuegbar, daher ausfuehrbare Umsetzung + reale
  Self-Checks. Offline/Mock ohne Kosten; echtes Agent-SDK-Backend erst ab GATE B.
- **Betroffen:** `orchestrator/core/*.py`, `orchestrator/channels/*.py`, `orchestrator/governance/*.py`,
  `orchestrator/observability/*.py`, `orchestrator/tests/*.py`, `orchestrator/run.py`,
  `orchestrator/__init__.py` (Paketgeruest).

## [2026-06-23 10:55] — Claude Code
- **Was:** Orchestrator Phase 1 (Foundation, ohne Laufzeit-Code): Ordner `orchestrator/` mit `.env.example`,
  `config.toml` (dry_run-Default, Modelle/effort/Flags), `README.md` angelegt; `.gitignore` ergaenzt
  (schliesst `orchestrator/.env` aus). Governance-Dokumente `governance/schnittstellen.md` (kanal-agnostischer
  Kern + Adapter-Roadmap: Terminal jetzt, Live-Voice/Telegram geplant) und `governance/zugriffs-policy.md`
  (Least-Privilege, grant_capability Fall A/B) neu. `agents/REGISTRY.md` um Spalte „Orchestrator"
  (verdrahtet: HoA, CTO, Berater) erweitert; `agents/01_unternehmensberater.md` Status `Entwurf` -> `aktiv`.
  `governance/orchestrierung.md` Status-/Verweis-Hinweis aktualisiert (Bootstrap begonnen, Verweis auf
  schnittstellen.md).
- **Warum:** GATE A freigegeben; Start der phasenweisen Umsetzung. Foundation ohne Python-Laufzeit, da auf
  diesem Rechner kein Python-Interpreter installiert ist (nur Store-Platzhalter) — die ausfuehrbaren
  Python-Module + Offline-Self-Checks folgen, sobald Python verfuegbar ist (Self-Check-Pflicht).
- **Betroffen:** `.gitignore`, `orchestrator/.env.example`, `orchestrator/config.toml`,
  `orchestrator/README.md`, `governance/schnittstellen.md`, `governance/zugriffs-policy.md`,
  `agents/REGISTRY.md`, `agents/01_unternehmensberater.md`, `governance/orchestrierung.md`.

## [2026-06-23 10:30] — Claude Code
- **Was:** `ORCHESTRATOR_PLAN.md` (Plan-Dokument) fuer den Bootstrap-Orchestrator angelegt — Dreiergruppe
  Head of Agents + CTO + Unternehmensberater auf Basis des Claude Agent SDK (Python), mit kanal-agnostischem
  Kern (Adapter-Pattern, Terminal-Adapter jetzt; Live-Voice/Telegram nur architektonisch vorgesehen),
  Governance-Durchsetzung (Changelog-Hook, CEO-Tor-PreToolUse-Hook), Secret-/Capability-Mechanik
  (orchestrator/.env, grant_capability Fall A/B, Leck-Schutz-Hook, zugriffs-policy.md), Beobachtbarkeit,
  Self-Checks und GATES. Noch KEIN Laufzeit-Code.
- **Warum:** CEO-Anweisung „Bootstrap-Orchestrator": erst Plan, dann GATE A (Freigabe), erst danach
  Implementierung. Scope strikt auf die Dreiergruppe begrenzt.
- **Betroffen:** `ORCHESTRATOR_PLAN.md` (neu).

## [2026-06-23 09:45] — Claude Code
- **Was:** `governance/organigramm.xmind` passend zur erweiterten `governance/organigramm.md` neu aufgebaut.
  Vier Ebenen: CEO -> Head of Agents -> Abteilungsleiter (14 C-Rollen/Berater) -> geplante Unter-Agenten.
  CCO (Research, Konzept/Strategie, Copywriter/Caption je Plattform, Video-Cutter eingehaengt, Reviewer) und
  CTO (Backend, Frontend/iOS, DevOps/Infra) explizit als „geplant"; alle uebrigen Abteilungen mit einem
  Knoten „Unter-Agenten bei Bedarf". Status-Labels aktiv/Entwurf je Abteilungsleiter, geplant je
  Unter-Agent. Datei als gueltiger XMind-ZIP-Container (content.json/metadata.json/manifest.json) erzeugt
  und verifiziert.
- **Warum:** CEO-Anweisung: XMind-Map an die erweiterte Organigramm-Struktur angleichen. Map ist nur
  Visualisierung; `agents/REGISTRY.md` bleibt Quelle der Wahrheit.
- **Betroffen:** `governance/organigramm.xmind`.

## [2026-06-23 09:30] — Claude Code
- **Was:** Alle 15 Charten unter `agents/` um die Abschnitte „Aufgabenkatalog (wiederkehrende To-dos)",
  „Workflows" und „Unter-Agenten (geplant)" erweitert (hinten angehaengt, vor der Aenderungsregel-Fussnote).
  `agents/_TEMPLATE.md` um dieselben Abschnitte ergaenzt, damit kuenftige Charten die Struktur erben.
  Unter-Agenten nur als Skizze (Name + Einzeiler-Zweck + Status: geplant); wo kein Mehrwert: „vorerst keine
  Unter-Agenten noetig". `governance/organigramm.md` um die geplante Unter-Agenten-Ebene erweitert (CCO und
  CTO explizit, uebrige Abteilungen „bei Bedarf"); Diagrammblock ASCII-bereinigt.
- **Warum:** CEO-Anweisung „Charten anreichern: Aufgabenkataloge, Workflows, Unter-Agenten (Skizze)".
  Leitprinzip nicht ueberbauen — Unter-Agenten nur skizziert, kein Laufzeit-Verhalten, keine separaten
  Unter-Agenten-Dateien, keine Orchestrierungs-Implementierung.
- **Betroffen:** `agents/_TEMPLATE.md`, `agents/00_head-of-agents.md` … `agents/14_cko.md` (alle 15 Charten),
  `governance/organigramm.md`.

## [2026-06-22 16:20] — Claude Code
- **Was:** Neue Konvention eingefuehrt und umgesetzt: In .md-Dateien werden keine Umlaute und kein scharfes
  S mehr verwendet (ASCII-Transliteration ae/oe/ue/ss, gross Ae/Oe/Ue). Regel in `AGENTS.md` (Abschnitt 6
  Konventionen) festgehalten. Lesbarer Text in ALLEN 28 .md-Dateien des Repos transliteriert; Code-Bloecke,
  Inline-Code, URLs und Dateipfade blieben unveraendert. Verifikation: 0 Vorkommen von Umlauten/scharfem S
  ausserhalb von Code/Inline-Code; verbleibende 16 Zeilen mit Umlauten liegen ausschliesslich innerhalb von
  Code-Bloecken (bewusst bewahrt, z. B. Changelog-Format-Vorlage, Anfrageformat, ASCII-Diagramme).
- **Warum:** CEO-Anweisung: ASCII-only fuer Markdown, um Umlaut-/Encoding-Probleme zu vermeiden; gilt ab
  sofort auch fuer kuenftige .md-Dateien. Gilt nicht fuer Nicht-.md-Dateien.
- **Betroffen:** alle .md-Dateien des Repos (`AGENTS.md`, `CLAUDE.md`, `README.md`, `projekt_changelog.md`,
  `agents/*.md`, `governance/*.md`, `finance/*.md`, `docs/*.md`).

## [2026-06-22 15:52] — Claude Code
- **Was:** Ordner `governance/` fuer lebende, autoritative Steuerungsdokumente (AGENTS.md untergeordnet)
  angelegt. Per `git mv` verschoben: `docs/orchestrierung.md` → `governance/orchestrierung.md`,
  `docs/orchestrierung.xmind` → `governance/orchestrierung.xmind`, `agents/Organigramm.xmind` →
  `governance/organigramm.xmind` (Dateiname vereinheitlicht). Neu: `governance/organigramm.md` (visuelle
  Hierarchie CEO → HoA → Abteilungsleiter → optionale Unter-Agenten, verweist auf `agents/REGISTRY.md` als
  Quelle der Wahrheit) und `governance/README.md`. `docs/README.md` bereinigt (nur noch Provenienz/Historie).
  Verweise aktualisiert in `AGENTS.md`, `README.md` und `agents/REGISTRY.md`.
- **Warum:** CEO-Anweisung: lebende Steuerungsdokumente von der eingefrorenen Provenienz in `docs/` trennen;
  Organigramm als eigenstaendiges, erweiterbares Dokument mit Unter-Agenten-Ebene fuehren; keine doppelte
  Pflege widerspruechlicher Inhalte (Registry = Quelle der Wahrheit, Organigramm = Visualisierung).
- **Betroffen:** `governance/orchestrierung.md`, `governance/orchestrierung.xmind`,
  `governance/organigramm.md` (neu), `governance/organigramm.xmind`, `governance/README.md` (neu),
  `docs/README.md`, `AGENTS.md`, `README.md`, `agents/REGISTRY.md`.

## [2026-06-22 15:35] — Claude Code
- **Was:** Kanonische Orchestrierungslogik als `docs/orchestrierung.md` festgehalten (Grundprinzip,
  Auftrags-Lebenszyklus, Delegations-/Ergebnisformat, Eskalation & Request-Protokoll, Kosten & Budget,
  CEO-Tore, Inter-Agenten-Zusammenarbeit, Konfliktloesung, Status & Gedaechtnis, erste aktive Welle).
  Verweise ergaenzt: `AGENTS.md` (Org-Prinzip + Dateiuebersicht), `README.md` und `docs/README.md`. Die vom
  CEO abgelegte Visualisierung `docs/orchestrierung.xmind` aufgenommen und mitcommittet.
- **Warum:** CEO-Anweisung „Orchestrierungslogik festhalten" — verbindliche Ablaufbeschreibung dokumentieren
  und XMind-Map einbinden. Noch keine Implementierung/kein Laufzeit-Code (folgt nach Framework-Entscheidung).
- **Betroffen:** `docs/orchestrierung.md` (neu), `docs/orchestrierung.xmind` (neu, vom CEO), `AGENTS.md`,
  `README.md`, `docs/README.md`.

## [2026-06-22 11:20] — Claude Code
- **Was:** XMind-Organigramm `agents/Organigramm.xmind` angelegt (Top-Down-Org-Chart: CEO → Head of Agents →
  14 Abteilungs-Agenten, mit Status-Labels „aktiv"/„Entwurf", Kurznotizen je Rolle und Hanserautisch-Farben).
  Querverweis dazu in `agents/REGISTRY.md` ergaenzt.
- **Warum:** CEO-Anweisung: Organigramm zusaetzlich als XMind-Map ablegen.
- **Betroffen:** `agents/Organigramm.xmind` (neu), `agents/REGISTRY.md`.

## [2026-06-22 11:05] — Claude Code
- **Was:** Governance-Modell in zwei Schritten erweitert. **(Teil 1 — Autonomie-Prinzip:** `AGENTS.md`
  Abschnitt 5 ein uebergeordnetes Autonomie-Prinzip vorangestellt (eigenstaendige Loesung ist Standard,
  Eskalation die Ausnahme; Request-Protokoll greift nur im Eskalationsfall, IT-Regel als Spezialfall);
  Standard-Eskalationszeile „Zuerst eigenstaendig … nur eskalieren, wenn nicht selbst loesbar …" in
  `agents/_TEMPLATE.md` und allen 15 Charten im Feld „Eskalation" ergaenzt. **(Teil 2 — Kosten & Budget:**
  `AGENTS.md` um Abschnitt 5.9 „Kosten & Budget" ergaenzt (laufende Kostenueberwachung/-statistik durch CFO,
  Kostenvoranschlag bei neuen Modellen/Diensten/Abos, CEO-Monatsbudget als einzige Quelle
  `finance/budget.md`, Budgetverwaltung durch HoA, Entscheidungslogik, CEO-Tor bleibt); `03_cfo.md` und
  `00_head-of-agents.md` im Auftrag entsprechend erweitert; `finance/budget.md` (Platzhalter-Budget +
  Aenderungshistorie) und `finance/kosten-statistik.md` (monatlich, mit Historie) angelegt; Dateiuebersicht in
  `AGENTS.md` um `finance/` und `docs/` ergaenzt.
- **Warum:** CEO-Anweisung „Governance-Modell in zwei zusammenhaengenden Schritten erweitern" — Autonomie als
  Leitprinzip verankern und eine nachvollziehbare Kosten-/Budget-Governance einfuehren.
- **Betroffen:** `AGENTS.md`, `agents/_TEMPLATE.md`, `agents/00_head-of-agents.md` … `agents/14_cko.md`
  (alle 15 Charten), `finance/budget.md`, `finance/kosten-statistik.md`.

## [2026-06-22 10:48] — Claude Code
- **Was:** (1) `AGENTS.md` um Abschnitt 5 „Request-/Freigabe-Protokoll" erweitert — Grundsatz, Anfrageformat,
  Entscheidungsbaum, CEO-Tor-Kategorien, Routing nach Bedarfstyp (technischer Bedarf → CTO/IT), proaktive
  Bedarfsermittlung durch die IT und Zugriffs-Governance (CISO autorisiert, CTO setzt um); Folgeabschnitte
  zu 6./7. umnummeriert. (2) Alle 14 Abteilungs-Charten mit recherchierten Verantwortlichkeiten,
  Modell-Richtwerten und der Standard-Eskalationszeile (Request-Protokoll) befuellt; HoA-Charta um Verweis
  auf das Request-Protokoll ergaenzt. (3) `05_ciso.md` (Zugriffs-Autorisierung/Policy) und `08_cto.md`
  (zentrale Anlaufstelle fuer technischen Bedarf + proaktive Bedarfsermittlung) entsprechend angepasst.
  (4) `agents/REGISTRY.md` aktualisiert: Welle 1 (HoA, CFO, CBO, CTO, CCO) = aktiv, uebrige = Entwurf.
- **Warum:** CEO-autorisierte Setup-Aufgabe „Agenten-Verantwortlichkeiten + Request-Protokoll": Charten mit
  echten C-Level-abgeleiteten Mandaten fuellen und das universelle Request-/Freigabe- sowie
  Bedarfs-Routing-Protokoll verankern. Weiterhin keine Orchestrierungslogik/kein Laufzeit-Verhalten.
- **Betroffen:** `AGENTS.md`, `agents/REGISTRY.md`, `agents/00_head-of-agents.md` …
  `agents/14_cko.md` (alle 14 Abteilungs-Charten).

## [2026-06-22 10:32] — Claude Code
- **Was:** Ausgangs-Prompt nach `docs/bootstrap-prompt.md` verschoben (per `git mv`, Historie erhalten) und
  `docs/`-Ordner fuer Projektdokumente angelegt; `docs/README.md` mit Zweck des Ordners (Historie/Provenienz)
  ergaenzt.
- **Warum:** CEO-Anweisung: Ausgangs-Prompt nicht loeschen, sondern als Herkunftsnachweis dokumentieren;
  `docs/` als Ablage fuer Briefs, Bootstrap- und spaetere Build-Prompts etablieren.
- **Betroffen:** `docs/bootstrap-prompt.md` (vormals `Claude_Code_Bootstrap_Prompt_Agenten.md`),
  `docs/README.md`.

## [2026-06-22 10:24] — Claude Code
- **Was:** Projekt initialisiert — Governance, Charta-System und 14 Agenten-Entwuerfe angelegt.
- **Warum:** Bootstrap-Anweisung des CEO (Datei `Claude_Code_Bootstrap_Prompt_Agenten.md`): Fundament des
  Hanserautisch Agenten-Unternehmens errichten (Struktur + Governance + Charta-Vorlagen, noch ohne
  Agenten-Verhalten).
- **Betroffen:** `AGENTS.md`, `CLAUDE.md`, `README.md`, `projekt_changelog.md`, `agents/_TEMPLATE.md`,
  `agents/REGISTRY.md`, `agents/00_head-of-agents.md`, `agents/01_unternehmensberater.md`,
  `agents/02_cao.md`, `agents/03_cfo.md`, `agents/04_cro.md`, `agents/05_ciso.md`, `agents/06_cbo.md`,
  `agents/07_cpo.md`, `agents/08_cto.md`, `agents/09_cxo.md`, `agents/10_cco-content.md`,
  `agents/11_cdo.md`, `agents/12_chro.md`, `agents/13_clo.md`, `agents/14_cko.md`.
