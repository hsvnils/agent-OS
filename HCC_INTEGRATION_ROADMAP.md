# HCC <-> LUNA Integration-Roadmap

> Ziel: Das **Hanserautisch Command Center (HCC)** wird das **Web-Gesicht fuer das Social-Media-Team**;
> **luna-os** bleibt Gehirn + Datenhoheit. Bestand siehe `docs/HCC_BESTAND.md`. Stand 2026-07-02 (Entwurf).

## Leitprinzipien (verbindlich)
1. **luna-os hat IMMER Vorrang.** Bei Konflikten gewinnt luna-os; HCC ist die Bedien-/Team-Oberflaeche.
2. **HCC = Web-Gesicht fuers Social-Media-Team.** Keine LUNA-/Investment-/Agenten-*Module* im HCC selbst.
3. **Gemeinsame Datenbasis, bidirektional.** Aenderungen im HCC-Web-Gesicht werden zurueckgeschrieben;
   LUNAs Fachagenten arbeiten im Hintergrund auf denselben Daten (wie das Collab-CRM schon jetzt).
4. **HCC hat keine eigenen Agenten.** LUNAs Agenten bedienen HCC im Hintergrund.
5. Governance wie gehabt: Oeffentlichkeit/Geld/Recht = CEO-Tor; kein Auto-Posten/Senden; Leck-Schutz auch bei
   Supabase-Writes; Charten nur HoA/CEO; Changelog-Pflicht; `.md` umlautfrei.

## Ziel-Scope HCC (was bleibt / was fliegt)
| HCC-Modul | Zukunft |
|---|---|
| content_ops (trends/content-radar/drafts/ideas/sources/ai-inbox) | **BLEIBT** (Team-Kern) -- aber die Logik dahinter kommt aus LUNA (Social-Media-Researcher + Agenten) |
| CRM (neu) | **NEU** -- Collab-CRM als erste geteilte Flaeche |
| video-cutter | **BLEIBT als Spiegel** -- ausgefuehrt von luna-os (Phase 15), HCC zeigt/triggert |
| administration (team/settings/security/profile/auth/notifications/activity) | **BLEIBT** (Team-Zugang/Rollen) |
| telegram (bots/intake) | **FLIEGT** -- im HCC nicht mehr benoetigt (LUNA besitzt Telegram). Spaetere Idee siehe „Backlog" |
| agents_workers (agents/agent-config/agents-office/eigener Worker) | **FLIEGT** -- LUNA uebernimmt; **alter Video-Cutter (Worker+UI+Logik+cutter_*-Schema) wird geloescht** (Phase 3) |
| invest | **FLIEGT** -- LUNAs CIO |

## Architektur-Kern: die eine grosse Entscheidung (Phase 1)
Wo liegt die Source of Truth + wie laeuft der **bidirektionale** Sync mit luna-os-Vorrang?
- **Option A -- Shared Supabase (empfohlen fuer geteilte Team-Entitaeten):** luna-os liest/schreibt Supabase
  direkt ueber austauschbare `SupabaseStore`-Backends (der `CrmStore`/`InvestmentStore` sind bereits als
  swappable Klassen gebaut). HCC nutzt Supabase wie gewohnt. Bidirektional „von Natur aus"; luna-os-Vorrang
  ueber Schreib-Logik + Timestamps. luna-os-**Interna** (Antraege, Watch, Memory, Aktivitaet) bleiben lokal.
- **Option B -- Sync-Bridge:** luna-os behaelt File-Stores; ein Bridge-Dienst synct bidirektional mit Supabase
  (Konfliktloesung: luna-os gewinnt). Mehr bewegliche Teile, aber luna-os bleibt voll offline-fest.
- **ENTSCHIEDEN (CEO 2026-07-02): Option A -- Shared Supabase, mit NAS-Offline-Fallback.** Supabase ist die
  **primaere gemeinsame Datenbasis** (Single Source, bidirektional). luna-os schreibt **write-through**: primaer
  nach Supabase UND haelt zusaetzlich eine **lokale Spiegel-/Fallback-Kopie** auf der NAS (JSONL). Ist Supabase
  nicht erreichbar, arbeitet luna-os lokal weiter und gleicht bei Wiederkehr ab (luna-os gewinnt bei Konflikt).
  So bleibt LUNA offline-fest, ohne die gemeinsame Basis aufzugeben. Gilt fuer die geteilten Team-Flaechen
  (CRM, Content, Cutter-Status); luna-os-Interna (Antraege, Watch, Memory, Aktivitaet) bleiben rein lokal.

## Phasen (mit GATES)
### Phase 0 -- Bestand + Ziel-Scope
`docs/HCC_BESTAND.md` (erledigt) + Scope-Tabelle oben. **GATE:** CEO bestaetigt „bleibt/fliegt".

### Phase 1 -- Datenbruecke (Fundament fuer alles) -- ✅ UMGESETZT 2026-07-02
- Architektur = **A (entschieden)**. Supabase-Zugang fuer luna-os: `SUPABASE_URL` + Service-Key in NAS-`.env`
  (CISO-Freigabe, CEO-Tor -- Dienst existiert bereits, keine neuen Kosten; Key NIE in den Chat).
- Generisches **`SupabaseStore`-Muster mit Write-Through + lokalem Fallback:** schreibt primaer nach Supabase
  und spiegelt in eine lokale JSONL-Kopie (NAS); Lesen bevorzugt Supabase, faellt bei Ausfall lokal zurueck;
  Abgleich bei Wiederkehr mit **Vorrang-Regel luna-os gewinnt**. Self-Checks gegen Mock.
- **GATE B:** Supabase-Key in `.env` + Verbindungstest.

### Phase 2 -- CRM-Pilot (erste geteilte Flaeche) -- 🟡 Write-Through UMGESETZT 2026-07-02 (Rueckschreiben offen)
- Gemeinsame `crm_*`-Tabellen in Supabase; luna-os-CRM auf die geteilte Basis (SupabaseCrmStore bzw. Bridge);
  CRM-View im HCC. Beweist **bidirektional + Vorrang** end-to-end. (Baut auf dem schon gebauten Collab-CRM auf.)
- **Self-Checks:** DM ueber LUNA -> in HCC sichtbar; Statuswechsel im HCC -> in LUNA sichtbar; Konflikt -> luna-os
  gewinnt.

### Phase 3 -- HCC ausmisten
- Aus dem HCC entfernen: Module `agents_workers` (agents/agent-config/agents-office/eigener Worker), `invest`,
  **`telegram`** (bots/intake), und den **alten Video-Cutter komplett** (Worker unter `worker/` + `worker-
  deploy.zip`, Routen `app/video-cutter/*` + `app/workers`, `app/api/video-cutter`, Lib/Components, sowie das
  `cutter_*`- und `worker_*`-Schema in Supabase -- per neuer Migration droppen). Mit Diff/Bestaetigung.
- HCC auf Team-Scope reduzieren: `content_ops`, CRM, Cutter-**Spiegel** (aus luna-os), `administration`.

### Phase 4 -- Cutter spiegeln
- luna-os-Cutter (Phase 15) ist die **ausfuehrende Instanz**. **Neue, schlanke** gemeinsame Cutter-Tabellen in
  Supabase (nachdem das alte `cutter_*`-Schema in Phase 3 entfernt wurde), zugeschnitten auf den luna-os-Cutter
  (Jobs/Status/Outputs). HCC zeigt Jobs/Historie + kann Jobs anstossen; luna-os verarbeitet und schreibt Status
  zurueck (Write-Through + lokaler Fallback).

### Phase 5 -- Social-Media-Researcher in luna-os (Ausbaustufe)
- HCCs Konzepte (trends/content-radar/sources/content_findings) als **neuen Social-Media-Researcher** in
  luna-os bauen (Ausbaustufe des bestehenden Researchers, Agent 15). Ergebnisse fliessen als Trends/Findings/
  Ideas/Drafts in die geteilte Basis -> HCC zeigt sie dem Team.

### Phase 6 -- LUNA-Agenten im Hintergrund fuers HCC
- LUNAs Fachagenten bearbeiten HCC-Content-Entitaeten im Hintergrund (Idee->Entwurf, Findings->Vorschlag),
  wie das CRM jetzt. HCC bleibt **agentenlos** (nur Ansicht/Freigabe durchs Team).

### Phase 7 -- Team-Zugang scharf schalten
- HCC Auth/Rollen/`allowed_modules` fuer das Social-Media-Team (Least-Privilege, CISO). Go-Live-Check.

## Reihenfolge / Abhaengigkeiten
Phase 1 (Datenbruecke) ist das Fundament. **Phase 2 (CRM-Pilot) validiert das Muster**, bevor Cutter (4),
Researcher (5) und Content-Agenten (6) folgen. Phase 3 (Ausmisten) kann parallel ab Phase 2 laufen.

## Entscheidungen (CEO 2026-07-02)
- **Architektur:** Option A -- Shared Supabase als primaere Basis + **NAS-Offline-Fallback** (Write-Through).
- **Telegram:** raus aus dem HCC (nicht mehr benoetigt). Spaetere Idee im Backlog.
- **Alter Cutter:** wird geloescht (Phase 3); LUNA-Cutter wird gespiegelt.
- **Datenschutz:** Team-/CRM-/Content-Daten in der Supabase-Cloud ist ok.
- In Haupt-`ROADMAP.md` als **Phase 18** verankert.

## Backlog / spaetere Ideen
- **Telegram-Reminder fuer Team-User:** ueber LUNAs Telegram bestimmte HCC-Nutzer an offene Aufgaben/To-dos
  erinnern (z. B. „Firma X seit 3 Tagen offen"). Nutzt den bestehenden Notifier; kein eigener HCC-Bot.
