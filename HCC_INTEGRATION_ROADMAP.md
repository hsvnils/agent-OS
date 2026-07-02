# HCC -> LUNA-OS Konsolidierung (Roadmap)

> **Richtungswechsel (CEO 2026-07-02): EIN System = LUNA-OS** (Gehirn + Web-Gesicht). Das alte HCC
> (`~/Documents/nilshubv2`, Next.js) + der Synology-Worker werden **stillgelegt**. Die behaltenen Teile
> (content_ops, CRM, Team) werden **in LUNA-OS nachgebaut**. **Supabase = primaere DB + NAS-Offline-Fallback.**
> Bestand des alten HCC: `docs/HCC_BESTAND.md`.

## Leitprinzipien
1. **Eine Codebasis, ein Deploy:** LUNA-OS (FastAPI + JS) ist Gehirn UND Team-Web-Gesicht.
2. **Daten:** Supabase = geteilte Datenbank; luna-os haelt lokale Fallback-/Offline-Kopie; **luna-os Vorrang**.
3. **Team-Zugang:** Mehr-Nutzer-Login + Rollen/Modul-Zugriff im LUNA-OS (CEO voll, Team scoped).
4. **LUNA-Agenten fuettern** content_ops/CRM im Hintergrund (keine eigenen Agenten im „Gesicht").
5. **nilshubv2 (Next.js) + Synology-Worker: raus.** Kein alter Deploy mehr.
6. Governance wie gehabt: CEO-Tor (Oeffentlichkeit/Geld/Recht), kein Auto-Posten, Leck-Schutz auch bei
   Supabase-Writes, Changelog-Pflicht, `.md` umlautfrei, Datenschutz (Supabase-Cloud ok).

## Uebernommen aus HCC (in LUNA-OS nachbauen) vs. raus
| Aus HCC | Zukunft in LUNA-OS |
|---|---|
| content_ops (sources/trends/ideas/drafts/ai-inbox) | **Nachbauen** als LUNA-OS-Apps (Team-Flaeche) |
| CRM | **Schon da** (Collab-CRM-App + Store + Supabase-Projektion) -- Blaupause |
| Team/Rollen/Auth | **Nachbauen** (Mehr-Nutzer + Modul-Zugriff) |
| eigener Worker, agents-office-3D, invest, telegram-intake, Video-Cutter | **Raus** (LUNA-CIO/-Cutter/-Telegram/-Agenten uebernehmen) |

## Auswirkung auf bereits Gebautes
- **Passt direkt:** `SupabaseClient` (governance/supabase.py), `SupabaseCrmProjection`, CRM-Store, Collab-CRM-App
  in LUNA-OS, CRM-Tabellen in Supabase. Das ist die neue Architektur im Kleinen.
- **Wird ueberfluessig (Ein-App-Welt):** der Read-back-Sync `crm_sync` (war fuer die Zwei-App-Welt gedacht) --
  bleibt vorerst harmlos, spaeter entfernbar.
- **Video-Cutter + Invest im HCC** bereits entfernt (Branch `chore/ausmisten-cutter-invest`); DROP-SQL fuer
  cutter_* in `docs/hcc_drop_cutter.sql`.

## Phasen (K = Konsolidierung)
### K0 -- Datenbruecke + CRM-Pilot -- ✅ ERLEDIGT
SupabaseClient + CRM-Store/Projektion + Collab-CRM-App in LUNA-OS, live bewiesen (Supabase = DB).

### K1 -- content_ops-Datenschicht in LUNA-OS -- ✅ ERLEDIGT (2026-07-02)
`orchestrator/core/content_store.py` (`ContentStore`, parametriert je Tabelle: select + PATCH via `status_feld`
+ generisches `patch` + Cache-Fallback). Live fuer alle content_ops-Tabellen (trend_signals/ideas/
content_drafts/sources/ai_intel_items).

### K2 -- content_ops-Apps in LUNA-OS (Team-Flaeche) -- ✅ ERLEDIGT (2026-07-02)
**Alle content_ops-Apps live** (lesen+schreiben gegen Supabase bewiesen): Trends(7) · Ideen-Labor(6) ·
Drafts(10) · Quellen(6, is_active-Toggle) · AI-Inbox(24, recommendation). Cache-Bust v24.

### K3 -- LUNA-Agenten fuettern content_ops (als Loop, Loop Engineering) -- ✅ CODE-KOMPLETT (2026-07-02)
Social-Media-Researcher + Content-Agenten -> schreiben Trends/Ideen/Drafts nach Supabase. **Ersetzt den alten
Dummy-Worker.** Entworfen nach `governance/autonomie-stufen.md` (Loop-Anatomie + L1→L2→L3):
- **Ziel:** N neue, relevante Kandidaten je Lauf (Trends/Ideen/Draft-Vorschlaege).
- **Trigger:** Zeitplan (`_start_content_feed_loop`, taeglich 07:00 DE, nur mit `CONTENT_FEED_ENABLED=1`) oder
  manuell (LUNA-Tool `content_feed_lauf`, stufe = trends|ideen|drafts|alles).
- **Lauf:** Trends = Brave-Web-Recherche (kostenlos); Ideen/Drafts = Content-Fachagent (`cco`, LLM,
  guenstiges Modell). Bulk je Stufe.
- **Verifikation:** Dedup (`source_url`; Status-Progression) + **Team-Review** in LUNA-OS.
- **Stop:** max. Kandidaten/Lauf + Notbremse (`autonomie_pausieren`/`WatchStore.paused`).
- **Autonomie:** **L1/L2** -- Kandidaten fuers **Team-Review** (kein Auto-Publish; Oeffentlichkeit = CEO-Tor).

**Umgesetzt:** `orchestrator/core/content_feed.py` (`ContentFeed`: `trend_lauf`/`ideen_lauf`/`drafts_lauf`/
`pipeline_lauf`) + `ContentStore.add()` (Insert). Pipeline: Trends `new` -> Ideen `inbox` -> Drafts `idea`;
verarbeitete Quellen ruecken vor (Trend->`reviewing`, Idee->`sorted`), damit nichts doppelt laeuft. Suite 294.
**OFFEN:** deployen + **live gegen Supabase verifizieren** (`CONTENT_FEED_ENABLED=1` in NAS-.env, luna-telegram
neu starten; oder `content_feed_lauf` via Telegram). Feinschliff: LLM-Relevanzfilter der Roh-Trends (Checker),
`trend_id`-Verknuepfung Idee->Draft, `sources`-Tabelle als zusaetzlicher Trigger.

### K4 -- Team-Auth + Rollen in LUNA-OS -- ✅ CODE-KOMPLETT (2026-07-02)
Mehr-Nutzer-Login (statt einzel-CEO-Basic-Auth) + Modul-/Rollen-Zugriff (wie HCC `allowed_modules`). CEO voll,
Team scoped. **Umgesetzt:** `orchestrator/core/team_auth.py` (TeamAuth gegen Supabase-Tabelle `luna_os_users`;
PBKDF2-Passwort-Hash stdlib; Module content_ops/crm/invest/administration; Rolle `owner`=Superuser; Pfad->Modul-
Gating). `web/app.py`: Auth loest env-CEO (owner) ODER Team-Nutzer auf, setzt `request.state.user`, gated
sensible Endpunkte (403); neuer `/api/me`. Frontend (`app.js`): laedt `/api/me`, blendet nicht-erlaubte Apps in
Sidebar/Dock aus, Nutzer-Chip (Name+Rolle); Cache-Bust v25. Nutzerverwaltung per CLI
`python -m orchestrator.core.team_auth add|list|deactivate` (Passwort bleibt ausserhalb des Chats). Migration:
`docs/hcc_k4_luna_os_users.sql`. Suite 314; im Preview verifiziert (Owner=alle Apps; Content-Rolle=6 Apps).
**Graceful:** ohne Tabelle bleibt env-CEO-Basic-Auth unveraendert. **OFFEN (CEO):** SQL-Migration in Supabase
ausfuehren + Team-Nutzer anlegen (CLI); luna-os ist bereits neu gestartet (Code kommt beim naechsten Sync).
Feinschliff spaeter: Team-Admin-App im Frontend, Kern-Endpunkte (state/lagebild) feiner scopen, Logout-Flow.

### K5 -- Cutter-App in LUNA-OS
LUNA-Cutter (Phase 15) Job-Status/Historie direkt als LUNA-OS-App zeigen + anstossen (kein App-zu-App-Spiegel
mehr noetig).

### K6 -- nilshubv2 + Worker stilllegen
Wenn alles in LUNA-OS laeuft: Next.js-App + Synology-Worker abschalten/Deploy entfernen; nicht mehr genutzte
Supabase-Tabellen bereinigen (cutter_*/worker_*/agent_*/telegram_* -- mit Backup, DROP-SQL wie
`docs/hcc_drop_cutter.sql`).

## Reihenfolge / Hinweise
K1->K2 (Datenschicht dann UI) ist das Fundament der Team-Flaeche; K3 (Agenten) fuettert sie; K4 (Team-Auth) vor
Go-Live; K5 (Cutter) unabhaengig; **K6 (Stilllegen) ganz am Ende**, erst wenn LUNA-OS alles ersetzt. Ehrlich:
das Nachbauen der content_ops-UI ist der groesste Brocken (das alte HCC hatte dafuer schon fertige Next.js-
Seiten -- die bauen wir in LUNA-OS neu).

## Backlog / spaetere Ideen
- Telegram-Reminder fuer Team-User (ueber LUNAs Telegram, kein eigener Bot).
- CRM-Read-back `crm_sync` entfernen (Ein-App-Welt).
