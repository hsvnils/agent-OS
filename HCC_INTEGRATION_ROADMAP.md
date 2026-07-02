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

### K1 -- content_ops-Datenschicht in LUNA-OS -- 🟡 Trends + Ideen live (generischer Store)
`orchestrator/core/content_store.py` (`ContentStore`, parametriert je Tabelle: select + PATCH-Status +
Cache-Fallback). **Live: trend_signals + ideas.** Drafts/Quellen/AI-Inbox = je eine weitere Instanz.

### K2 -- content_ops-Apps in LUNA-OS (Team-Flaeche) -- 🟡 Trends + Ideen + Drafts live (2026-07-02)
**Kern-Pipeline Trends -> Ideen -> Drafts live** (Inbox + Status-Buttons, lesen+schreiben gegen Supabase
bewiesen: 7 Trends / 6 Ideen / 10 Drafts). Verbleibend: **Sources** (name/is_active/priority, kein Status ->
Read-only + is_active-Toggle) + **AI-Inbox** (recommendation/scores -> eigene Form).

### K3 -- LUNA-Agenten fuettern content_ops
Social-Media-Researcher + Content-Agenten (Ausbaustufe des Researchers) -> schreiben Trends/Ideen/Drafts/
Findings nach Supabase. **Ersetzt den alten Dummy-Worker** endgueltig.

### K4 -- Team-Auth + Rollen in LUNA-OS
Mehr-Nutzer-Login (statt einzel-CEO-Basic-Auth) + Modul-/Rollen-Zugriff (wie HCC `allowed_modules`). CEO voll,
Team scoped. **Vor dem Team-Go-Live.**

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
