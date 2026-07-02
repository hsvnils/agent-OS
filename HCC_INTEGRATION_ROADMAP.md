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
| telegram (bots/intake) | **ZU KLAEREN** -- LUNA besitzt den Bot (nur ein Poller/Token); HCC-Intake TBD |
| agents_workers (agents/agent-config/agents-office/eigener Worker) | **FLIEGT** -- LUNA uebernimmt |
| invest | **FLIEGT** -- LUNAs CIO |

## Architektur-Kern: die eine grosse Entscheidung (Phase 1)
Wo liegt die Source of Truth + wie laeuft der **bidirektionale** Sync mit luna-os-Vorrang?
- **Option A -- Shared Supabase (empfohlen fuer geteilte Team-Entitaeten):** luna-os liest/schreibt Supabase
  direkt ueber austauschbare `SupabaseStore`-Backends (der `CrmStore`/`InvestmentStore` sind bereits als
  swappable Klassen gebaut). HCC nutzt Supabase wie gewohnt. Bidirektional „von Natur aus"; luna-os-Vorrang
  ueber Schreib-Logik + Timestamps. luna-os-**Interna** (Antraege, Watch, Memory, Aktivitaet) bleiben lokal.
- **Option B -- Sync-Bridge:** luna-os behaelt File-Stores; ein Bridge-Dienst synct bidirektional mit Supabase
  (Konfliktloesung: luna-os gewinnt). Mehr bewegliche Teile, aber luna-os bleibt voll offline-fest.
- **Empfehlung:** A fuer die geteilten Flaechen (CRM, Content, Cutter-Status). Entscheidung ist GATE in Phase 1.

## Phasen (mit GATES)
### Phase 0 -- Bestand + Ziel-Scope
`docs/HCC_BESTAND.md` (erledigt) + Scope-Tabelle oben. **GATE:** CEO bestaetigt „bleibt/fliegt".

### Phase 1 -- Datenbruecke (Fundament fuer alles)
- Architektur A/B entscheiden. Supabase-Zugang fuer luna-os: `SUPABASE_URL` + Service-Key in NAS-`.env`
  (CISO-Freigabe, CEO-Tor -- Dienst existiert bereits, keine neuen Kosten). Generisches `SupabaseStore`-Muster
  + **Vorrang-Regel** (luna-os gewinnt). Self-Checks gegen Mock. **GATE B:** Keys in `.env` + Verbindungstest.

### Phase 2 -- CRM-Pilot (erste geteilte Flaeche)
- Gemeinsame `crm_*`-Tabellen in Supabase; luna-os-CRM auf die geteilte Basis (SupabaseCrmStore bzw. Bridge);
  CRM-View im HCC. Beweist **bidirektional + Vorrang** end-to-end. (Baut auf dem schon gebauten Collab-CRM auf.)
- **Self-Checks:** DM ueber LUNA -> in HCC sichtbar; Statuswechsel im HCC -> in LUNA sichtbar; Konflikt -> luna-os
  gewinnt.

### Phase 3 -- HCC ausmisten
- Module `agents_workers` (agents/agent-config/agents-office/eigener Worker) + `invest` aus dem HCC entfernen;
  HCC auf Team-Scope reduzieren (content_ops, CRM, cutter-Spiegel, administration, telegram TBD). Alte
  HCC-Worker-/Agentenlogik stilllegen.

### Phase 4 -- Cutter spiegeln
- luna-os-Cutter (Phase 15) ist die **ausfuehrende Instanz**; Job-Status/Outputs in die geteilte Basis
  (HCC-`cutter_*`-Schema wiederverwenden). HCC zeigt Jobs/Historie + kann Jobs anstossen; luna-os verarbeitet.
  Der alte, offline HCC-Worker wird durch den luna-os-Pfad abgeloest.

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

## Offene Punkte fuer den CEO
- Architektur A vs. B (Phase 1).
- Telegram: bleibt der HCC-Intake, oder besitzt LUNA Telegram allein? (nur ein Poller/Token moeglich).
- Datenschutz: Team-/CRM-/Content-Daten liegen dann in der Supabase-Cloud (bewusst entscheiden).
- Verhaeltnis zur Haupt-`ROADMAP.md`: als neue Phase (z. B. „Phase 18 -- HCC als Team-Web-Gesicht") eintragen.
