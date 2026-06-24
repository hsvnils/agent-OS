# ROADMAP.md — Vom aktuellen Stand zum selbst-entwickelnden Agenten-Unternehmen

> **Status: PLAN — wartet auf GATE D (CEO-Freigabe dieser Roadmap).** Beschreibt den Weg vom heutigen Stand
> bis zum Ziel: ein 24/7 erreichbarer persoenlicher Assistent (Head of Agents) mit Fachabteilungen, die
> Aufgaben eigenstaendig umsetzen, sich selbst weiterentwickeln und den CEO ueber den HoA auf dem Laufenden
> halten. `AGENTS.md` bleibt kanonisch und uebergeordnet; jede Phase ist ihr untergeordnet.

---

## 1. Ziel & Leitprinzipien

**Ziel:** Ein System, das sich **selbst aufbaut, selbst verbessert und selbst weiterentwickelt** — und dabei
den CEO ueber den Head of Agents (HoA) informiert und an den richtigen Stellen um Freigabe bittet.

**Invarianten (gelten in JEDER Phase):**
1. **Mensch-Freigabe-Tor bleibt hart:** Jede Aenderung mit Wirkung (Code, Dateien, Geld, Recht,
   Oeffentlichkeit, externe Aktionen) wird **erst nach CEO-Freigabe** ausgefuehrt. Abteilungen gehen zum HoA,
   der HoA geht zum CEO. Keine autonome Ausfuehrung ueber das Tor hinweg (AGENTS.md 4/5).
2. **Aenderungen immer auf Branch + Tests + Rollback:** Ausfuehrende Agenten arbeiten auf Git-Branches, fuehren
   Self-Checks aus, und mergen **nie** ohne CEO. Git ist das Sicherheitsnetz.
3. **Selbst-Modifikation nur ueber den Antrags-/Freigabe-Workflow** (Phase 6). Das System darf seinen eigenen
   Code/Charten nur via freigegebenem Antrag aendern.
4. **Kosten sind governt:** 24/7-Betrieb verursacht laufende Token-/Dienst-Kosten. Der CFO/das Budget
   (`finance/`) wird load-bearing; jede Phase nennt Kostenwirkung; Limits/Stopps sind Pflicht.
5. **Sicherheit/Secrets:** Externe Zugaenge (E-Mail, Kalender, Telegram, Web) laufen ueber das
   Capability-Muster + CISO-Freigabe; kein Key im Klartext (Leck-Schutz).

---

## 2. Aktueller Stand (Fundament steht)

- **Orchestrator-Kern (HoA):** kanal-agnostisch; im Voice-Kanal als streamendes LLM mit Function-Calling.
- **Agenten:** alle 14 Charten als **konsultierbare** Spezialisten (Antwort aus Charta/Domaene); CTO + Berater
  zusaetzlich ueber den schweren Pfad (Opus).
- **Governance:** CEO-Tor-Erkennung, Changelog-Pflicht, Leck-Schutz, Capability-/Zugriffs-Policy, Budget.
- **Gedaechtnis:** dateibasiert (JSONL), isoliert vom persoenlichen Claude-Code-Memory.
- **Voice-Kanal:** Pipecat/WebRTC lokal, Deutsch (ElevenLabs+Deepgram), Barge-in, Panels (show_panel),
  `frage_finance`, `delegate` (alle Agenten), `set_budget` (CFO schreibt finance/budget.md).
- **Was fehlt fuer das Ziel:** echtes **Ausfuehren** von Aenderungen, ein **Antrags-/Freigabe-Lebenszyklus**,
  **Web-Research**, **24/7-Queue/Resume**, **Telegram**, **E-Mail/Kalender**, proaktive Abteilungen,
  Live-Kontext/Organigramm im Gespraech.

---

## 3. Architektur-Bausteine (was neu gebaut wird)

| Baustein | Zweck |
|----------|-------|
| **Antrags-/Freigabe-Workflow** | Persistenter „Antrag" (Proposal) mit Status: eingereicht → CEO-gepruerft (frei/abgelehnt) → in Umsetzung → erledigt/fehlgeschlagen. Einzige Bruecke fuer Aenderungen. |
| **Execution-Engine (handelnde Agenten)** | Coding-/Aktions-Agent (Claude Agent SDK mit Datei-/Bash-/Web-Tools), der NUR freigegebene Antraege auf einem Git-Branch umsetzt, testet und berichtet. |
| **Durable Task-Queue + Scheduler** | Persistente Auftragswarteschlange + Hintergrund-Worker; bei Token-/Limit-Erschoepfung pausieren und automatisch fortsetzen; Retries/Backoff; 24/7. |
| **Kanal: Telegram** | Mobiler Text-/Sprachkanal (Auftraege unterwegs, Freigaben, Statusmeldungen/Push). |
| **Integrationen** | E-Mail (lesen/senden), Kalender (lesen/schreiben, Kollisionen), je via Capability + CISO; proaktiver Watcher/Notifier. |
| **Web-Research** | Internet-Zugriff (Such-/Fetch-Tools) fuer Berater (Innovations-Scouting) und IT (Self-Education). |
| **Live-Kontext & Organigramm** | Im Gespraech anzeigen, mit welchem Agenten der HoA gerade spricht; Organigramm-Panel; Kontext-Panel auf Anfrage. |
| **Innovations-Pipeline (Berater)** | Beobachten → Ideen → Bewertung (IT-Machbarkeit + Finance-Kostenvoranschlag + relevante Abteilungen) → Zusammenfassung → Vorstellung beim HoA (als Antrag). |

---

## 4. Phasen mit GATES

> Reihenfolge nach Abhaengigkeit + Wert. Jede Phase ist eigenstaendig testbar (Offline-Self-Checks zuerst),
> hat einen klaren GATE und einen Nutzen. „GATE" = CEO-Freigabe-Punkt vor billbaren/externen/riskanten Schritten.

### Phase 5 — Live-Kontext & Organigramm im Gespraech  (Quick Win, risikoarm)
- **Ziel:** Wenn der HoA einen Agenten konsultiert, zeigt die Oberflaeche live „HoA spricht mit Finance (CFO)";
  Organigramm-Panel; relevanter Kontext auf Anfrage einblendbar.
- **Bausteine:** Delegations-/Kommunikations-Events ueber RTVI an die Browser-Seite; Organigramm-Panel aus
  `agents/REGISTRY.md`.
- **GATE:** keiner (offline + bestehender Voice-Betrieb). **Kosten:** keine zusaetzlichen.

### Phase 6 — Antrags-/Freigabe-Workflow  (Rueckgrat der Mensch-im-Spiel-Steuerung)
- **Ziel:** Abteilungen und HoA koennen **Antraege** stellen (Aenderung/Beschaffung/Idee). Lebenszyklus mit
  Status; HoA legt sie dem CEO vor (Voice/Telegram); **erst nach Freigabe** Ausfuehrung. Persistenz +
  Changelog + Gedaechtnis.
- **Bausteine:** `antraege/`-Store (JSONL/Dateien), Zustandsmaschine, HoA-Tools `antrag_stellen`,
  `antraege_zeigen`, `antrag_freigeben` (nur CEO-bestaetigt).
- **GATE:** Design-Freigabe (governance-kritisch). **Kosten:** minimal.

### Phase 7 — Execution-Engine: handelnde Agenten  (Abteilungen setzen wirklich um)
- **Ziel:** „Wie wenn ich es selbst in Codex/Claude Code mache": ein Ausfuehrungs-Agent (Claude Agent SDK mit
  Datei-/Bash-/Test-Tools) setzt **freigegebene** Antraege auf einem **Git-Branch** um, laesst Self-Checks
  laufen, und meldet Ergebnis + was zu testen ist. **Kein Merge ohne CEO.**
- **Bausteine:** Execution-Runner (Branch anlegen, Tools im Sandbox-Mandat, Tests, Diff/Report), Rollback ueber
  Git; Verdrahtung an Phase 6 (nur freigegebene Antraege).
- **GATE:** stark — handelnde Tools + Selbst-Aenderung; Branch-only, Test-Pflicht, CEO-Merge. **Kosten:** Opus.

### Phase 8 — Web-Research / Self-Education  (Augen nach aussen)
- **Ziel:** Internet-Zugriff fuer Berater (Innovations-Scouting „was ist neu im KI-Agenten-Bereich") und IT
  (Self-Education/Maintenance).
- **Bausteine:** Web-Such-/Fetch-Capability (API-Web-Tools oder Such-API), leck-/quellen-sauber.
- **GATE:** externer Dienst/Kosten = CEO-Tor (klein) + CISO. **Kosten:** gering.

### Phase 9 — Innovations-Pipeline (Unternehmensberater)  (Selbst-Verbesserungs-Ideen)
- **Ziel:** Berater beobachtet Entwicklungen (Phase 8), generiert Weiterentwicklungs-Ideen fuers
  KI-Unternehmen, **bewertet** sie: technische Machbarkeit (IT/CTO), **Kostenvoranschlag (CFO)**, Input
  relevanter Abteilungen; **fasst zusammen** und stellt sie als **Antrag** (Phase 6) beim HoA vor.
- **Bausteine:** Mehr-Agenten-Workflow + Research; Output = entscheidungsreifer Antrag.
- **GATE:** nutzt freigegebene Research; Ergebnis ist Antrag (keine Ausfuehrung ohne Freigabe). **Kosten:** Opus.

### Phase 10 — Kanal: Telegram (mobil, 24/7)  (von unterwegs)
- **Ziel:** Text- UND Sprachnachrichten ueber Telegram: Auftraege/Ideen/Notizen unterwegs geben, Freigaben
  erteilen, Statusmeldungen/Push empfangen.
- **Bausteine:** Telegram-Kanal-Adapter am bestehenden kanal-agnostischen Kern; Voice-Notiz → STT → HoA;
  Push-Benachrichtigungen.
- **GATE:** Bot-Token (extern) = CEO-Tor + Capability + CISO. **Kosten:** gering.

### Phase 11 — Integrationen: E-Mail + Kalender  (ausfuehren + proaktiv melden)
- **Ziel:** HoA kann E-Mails lesen/senden und Kalender lesen/schreiben; meldet **proaktiv** (Antwort auf
  E-Mail eingegangen, Termin-Kollision). Ad-hoc „verschick eine Mail / trag einen Termin ein".
- **Bausteine:** Gmail-/Kalender-Capability (Capability-Muster + CISO + Secrets), Watcher/Notifier
  (Hintergrund-Polling) → Push ueber Telegram (Phase 10).
- **GATE:** externe, berechtigte Dienste = CEO-Tor + CISO + Capability. **Kosten:** ggf. gering/mittel.

### Phase 12 — Durable Task-Queue + Scheduler (24/7, fortsetzbar)  (Dauerbetrieb)
- **Ziel:** Persistente Auftragswarteschlange + Hintergrund-Worker, der Abteilungen „am Arbeiten haelt"
  (Wissensmanagement, Safe-Maintenance, Self-Education). **Bei Token-/Guthaben-Limit: pausieren und
  automatisch fortsetzen**, sobald wieder verfuegbar; Retries/Backoff. Abschluss-Meldung (was/welche
  Abteilung/Status/zu testen) ueber den HoA (Telegram).
- **Bausteine:** Queue + Scheduler (Dateien jetzt; **Supabase** als Backend spaeter, Pro-Plan vorhanden);
  Rate-Limit-/Credit-Erkennung + Resume; proaktive Ablaeufe.
- **GATE:** Design + Dauerbetriebs-Kosten (CEO-Tor: laufende Token-Nutzung) + ggf. Supabase. **Kosten:** real, laufend.

### Phase 13 — Self-Development-Loop (Ziel/Apex)  (selbst-entwickelndes System)
- **Ziel:** Das System schlaegt Verbesserungen an sich selbst vor (Phase 9), der CEO gibt ueber den HoA frei
  (Phase 6), die Execution-Engine setzt sie um (Phase 7, Branch+Tests), der Scheduler haelt es 24/7 am Laufen
  (Phase 12), Berichte/Freigaben laufen mobil (Phase 10/11). Der Kreis schliesst sich.
- **GATE:** der staerkste — Selbst-Modifikation **ausschliesslich** ueber freigegebene Antraege, Branch +
  Tests + CEO-Merge; harte Kosten-/Stopp-Limits.

---

## 5. Sicherheit & Kosten-Leitplanken (querschnittlich)

- **Niemals Auto-Merge/Auto-Deploy** ohne CEO. Selbst-Modifikation immer auf Branch, mit Tests, reversibel.
- **Kosten-Limits:** harte Monats-/Tages-Caps (CFO/`finance/budget.md`); bei Erreichen pausieren + melden.
- **Least-Privilege:** jede Capability nur fuer die zustaendige Abteilung (CISO-Policy); Secrets nur in `.env`.
- **Audit:** jede Aktion in Changelog + Gedaechtnis; Antrags-Historie nachvollziehbar.
- **Notbremse:** ein „Stopp/Pausieren"-Befehl (Voice/Telegram), der alle laufenden autonomen Arbeiten anhaelt.

---

## 6. Kann sich das System danach selbst entwickeln? Was fehlt heute?

**Antwort: Ja — nach Phasen 6–9 + 12–13, mit der harten Invariante „nur via CEO-Freigabe".** Heute fehlt dafuer:
1. **Handeln statt nur antworten** (Phase 7): Agenten brauchen echte Tools (Datei/Bash/Test) im Branch-Sandbox.
2. **Antrags-/Freigabe-Lebenszyklus** (Phase 6): die kontrollierte Bruecke „Vorschlag → Freigabe → Umsetzung".
3. **Augen nach aussen** (Phase 8) + **Innovations-Pipeline** (Phase 9): damit Vorschlaege fundiert entstehen.
4. **Dauerbetrieb + Fortsetzbarkeit** (Phase 12): 24/7, Resume bei Limit, proaktive Ablaeufe.
5. **Mobiler Draht + Aktionen** (Phase 10/11): Auftraege/Freigaben/Meldungen unterwegs; E-Mail/Kalender.

Das Fundament (Governance, Charten, Gedaechtnis, Delegation, Voice) ist die richtige Basis; die obigen Phasen
bauen kontrolliert darauf auf. Das groesste Risiko ist nicht technischer, sondern **Sicherheits-/Kontroll-Natur**
— exakt deshalb ist der Antrags-/Freigabe-Workflow (Phase 6) das Rueckgrat und kommt vor der Execution-Engine.

---

## 7. GATES-Uebersicht

- **GATE D (jetzt):** Freigabe dieser Roadmap + Reihenfolge.
- **Pro Phase:** eigener GATE wie oben (besonders streng bei Phase 7, 11, 12, 13).
- **Empfohlener Start:** Phase 5 (sichtbarer Quick Win, kostenlos) parallel zur Detailplanung von Phase 6
  (Rueckgrat). Erst danach Phase 7 (handelnde Agenten).
