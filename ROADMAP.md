# ROADMAP.md — Vom aktuellen Stand zum selbst-entwickelnden Agenten-Unternehmen

> **Status: GROSSTEILS UMGESETZT & LIVE (Stand 2026-06-26).** Diese Datei ist die **lebende** Roadmap und wird
> bei jeder Phasenaenderung aktualisiert. Ziel: ein 24/7 erreichbarer persoenlicher Assistent (Head of Agents,
> „LUNA") mit Fachabteilungen, die Aufgaben eigenstaendig umsetzen, sich selbst weiterentwickeln und den CEO
> ueber den HoA auf dem Laufenden halten. `AGENTS.md` bleibt kanonisch und uebergeordnet; jede Phase ist ihr
> untergeordnet.
>
> **Live-Stand:** LUNA laeuft 24/7 als Telegram-Bot (Docker, Synology-NAS, Non-root). **Phasen 5–15 umgesetzt.**
> **Aktueller Fokus (HOCH):** Phase 16 — eine taeglich nutzbare **Live-Arbeitsoberflaeche im Browser**.
> Zurueckgestellt: Phase 10b (Telefonie), Cutter „intelligenter machen" (Backlog). **Funktionaler Blocker:**
> Execution braucht Anthropic-Modellzugang (Guthaben/ab 2026-07-01) ODER ein lokales LLM (siehe Abschnitt 9).

## Status-Uebersicht (Single Source of Truth)

| Phase | Thema | Status |
|------:|-------|--------|
| 5  | Live-Kontext & Organigramm | ✅ umgesetzt |
| 6  | Antrags-/Freigabe-Workflow | ✅ umgesetzt |
| 7  | Execution-Engine (Branch+Tests) | ✅ gebaut (wartet auf Modellzugang) |
| 8 / 8.5 | Web-Research + Researcher | ✅ umgesetzt (Brave live) |
| 9  | Innovations-Pipeline | ✅ umgesetzt |
| 10 / 10A | Telegram (Text+Voice) | ✅ live |
| 10b | Telefon-Anruf (Twilio) | 🔲 zurueckgestellt |
| 11 | Gmail + Kalender | ✅ live |
| 12 | Durable Queue + 24/7-Watcher | ✅ umgesetzt |
| 13 | Self-Development-Loop (Apex) | ✅ umgesetzt |
| 14 | Freie Visualisierung (MindMap/Graph/Chart) | ✅ umgesetzt 2026-06-26 |
| 15 | Cutter Agent (Video-Schnitt, lokal auf dem Mac) | ✅ V1+V2 live 2026-06-27 — funktioniert; „intelligenter machen" = Backlog (spaeter) |
| 16 | **LUNA-OS (Browser-Arbeitsoberflaeche)** | ✅ **LIVE auf dem NAS 2026-06-27** (LAN-Zugriff + Login); HTTPS/extern + Chat-Panel offen |

**Quer dazu live:** Notifier, Briefings (08:00/20:00), Self-Maintenance/Healing, CFO-Kostenerfassung,
Multi-Provider-Fallback (Gemini/OpenAI), Non-root-Container, zentrales Aktivitaetsprotokoll (adc5).

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

### Phase 5 — Live-Kontext & Organigramm im Gespraech  (Quick Win, risikoarm) — UMGESETZT 2026-06-24
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

### Phase 7 — Execution-Engine: handelnde Agenten  (Abteilungen setzen wirklich um) — UMGESETZT (wartet auf Modellzugang)
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
- **Hinweis:** Ein echter Telegram-**Anruf** an einen Bot ist nicht moeglich (Bots nehmen keine Anrufe an).
  Telegram liefert **Sprachnachrichten** (Push-to-talk) + Push -- ideal fuer unterwegs.
- **GATE:** Bot-Token (extern) = CEO-Tor + Capability + CISO. **Kosten:** gering.

### Phase 10b — Telefon-Anruf (Telefonie, „Jarvis anrufen")  (optional, parallel zu 10)
- **Ziel:** Eine **Telefonnummer**, die man anruft und **live** mit dem HoA spricht (Streaming, Barge-in) --
  das echte „Anruf"-Gefuehl. **Status: ZURUECKGESTELLT** (bewusst spaeter; Twilio = laufende Kosten).
- **Bausteine:** Telefonie-Transport (z. B. Twilio) an die bestehende Pipecat-Pipeline (Pipecat hat fertige
  Telefonie-Transports); derselbe HoA-Kern.
- **GATE:** Telefonnummer + Minuten (extern, kostenpflichtig) = CEO-Tor + Capability + CISO. **Kosten:** real.

### Hosting / Online-Betrieb (querschnittlich, vor 10/10b/12 noetig)
- Der Voice-/Agent-Server ist **dauerhaft laufend** (WebRTC/Pipecat + Claude-CLI + Orchestrator) -> braucht
  einen **persistenten Host** (VPS/Container: Fly.io, Railway, Render, Hetzner, oder ein Always-on-Mac/mini),
  **nicht Vercel** (serverless, ungeeignet fuer Langlauf/WebRTC). Mobil im Browser: Host mit **HTTPS**
  (Mikrofon-Zugriff). Eigene Phase/Entscheidung sobald 24/7 mobil gewuenscht ist.

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

### Phase 14 — Oberflaechen-Erweiterung / generische Visualisierung — UMGESETZT 2026-06-26
- **Ziel:** Der HoA kann Inhalte **frei und visuell** darstellen, nicht nur feste Panel-Typen. Insbesondere:
  **Organigramm/Strukturen als MindMap**, dynamische Diagramme/Charts, frei konfigurierbare Ansichten — auf
  Sprach-/Textanfrage („zeig mir das als MindMap").
- **Umsetzung:** Generische Visualisierungs-Schicht `core/visualisierung.py` — LUNA emittiert eine
  **Spezifikation** (mindmap/organigramm/graph/balken), aus der ein **reines SVG** erzeugt wird (keine
  Fremd-Bibliothek, kein externer Render-Dienst). LUNA-Tool **`visualisiere(art, titel, inhalt)`**; im
  **Telegram**-Kanal wird das SVG als Bild-Datei gesendet (neuer `sendDocument`-Pfad), im **Browser** als
  generisches `visualisierung`-Panel gerendert. Bestehende Panels bleiben Spezialfaelle. Suite +7 Tests.
- **GATE:** keiner (lokal/UI, keine externen Kosten).

---

### Phase 15 — Cutter Agent: automatischer Video-Schnitt — V1 UMGESETZT 2026-06-27
- **Ziel:** Ordner mit Clips -> fertiges **9:16-Instagram-Reel**, vollautomatisch, **lokal auf dem Mac**,
  ohne externe Dienste/Kosten. Pro Clip Sprach-Erkennung (lokales Whisper), Sprech-Clips mit Untertiteln,
  B-Roll mit praegnantem Ausschnitt; Gemini ordnet die Reihenfolge; 9:16 mit Blur-Hintergrund, Ton normalisiert.
- **Umsetzung (V1):** Paket `cutter/` (ffmpeg_ops, transkription [whisper.cpp/faster-whisper/Deepgram],
  pipeline, watch, CLI). Einmal-Lauf `python -m cutter <ordner>`; unbeaufsichtigt `python -m cutter.watch`
  (Inbox/Outbox). Untertitel werden als `.srt` abgelegt (Einbrennen braucht ffmpeg mit libass -- aktuelles
  Build hat das nicht). Tests 6/6. **palmier-pro geprueft und verworfen** (macOS-GUI-Editor, interaktiv, keine
  Batch-Automatik).
- **Governance:** Instagram-**Posten bleibt CEO-Tor** (Oeffentlichkeit) -- der Cutter erzeugt nur die Datei.
- **V2 (umgesetzt 2026-06-27):** **Autostart** via launchd (`com.hanserautisch.cutter.watch.plist` -> startet
  den Watcher bei jedem Login, KeepAlive); **Telegram-Meldung** -- fertiges Reel geht als Video an den
  LUNA-Chat (`cutter/melden.py`, gleiches Bot-Token). Live verifiziert.
- **Offen (Tuning, kleiner):** Untertitel einbrennen (libass-ffmpeg statt .srt), besseres Whisper-Modell
  (`small` DE), Musik/Beat-Sync, subjekt-bewusster Crop; Schnitt per Chat anstossen (NAS->Mac-Trigger).
- **„Intelligenter machen" (Backlog, CEO: noch nicht intelligent genug -> nach hinten):** der ffmpeg-Ansatz
  ist regelbasiert. Fuer echten Profi-Schnitt spaeter einen **echten Editor headless steuern**.
  **Kandidat: OpenCut** (github.com/opencut-app/opencut, MIT) -- die Neufassung bringt **Headless-Modus,
  Editor-API und MCP-Server fuer KI-Agenten**; damit koennte LUNA einen vollwertigen Editor programmatisch
  bedienen (Effekte, Timeline, Plugins) statt nur ffmpeg-Filter. Heute noch im Umbau -> beobachten, spaeter
  evaluieren.

### Phase 16 — LUNA Live-Arbeitsoberflaeche (Browser-Dashboard) — GEPLANT, HOHE PRIORITAET (jetzt)
- **Ziel:** Eine **taeglich nutzbare, echte Arbeitsoberflaeche im Browser**, mit der der CEO arbeitet und auf
  der **LUNA mitarbeitet**. Sie zeigt **live und proaktiv die wichtigsten zu erledigenden Dinge** und man
  bearbeitet **Antraege direkt per Buttons**: Freigeben, Ablehnen, Loeschen, „Mehr Infos durch Agenten holen".
  Keine reine Anzeige -- ein Arbeits-Werkzeug, das sich gut bedienen laesst.
- **Kern-Ansicht „Was muss ich erledigen":** priorisierte **Inbox** offener Antraege + Aufgaben (offene
  Freigaben zuerst). Jeder Eintrag ist eine **Karte mit Evidenz** -- Begruendung, CTO-Machbarkeit,
  CFO-Kostenvoranschlag -- damit eine Entscheidung in Sekunden faellt (evidenzbasiert; LUNA erklaert wie ein
  Teammate, nicht als Debug-Log).
- **Aktionen je Antrag (Buttons):** Freigeben · Ablehnen (mit Grund) · Loeschen · **„Recherche/Bewertung
  beauftragen"** (ein Agent holt mehr Infos: funde_bewerten / recherche_beauftragen / delegate). Alles laeuft
  ueber die **bestehenden LUNA-Tools + Antrags-/Freigabe-Logik (Phase 6)** -> Changelog + CEO-Tor bleiben
  hart; die UI ist nur der bequeme Weg fuer dieselben kontrollierten Aktionen (kein Auto-Merge).
- **Live:** Echtzeit-Updates (WebSocket/SSE, Event-Stream-Muster vgl. **AG-UI**-Protokoll) -> neue Antraege,
  Meldungen, Aktivitaeten erscheinen **sofort ohne Reload**.
- **Weitere Panels:** LUNA-**Chat** (direkt schreiben, wie Telegram), proaktive **Meldungen**,
  **Aktivitaetsprotokoll** (adc5), **Finance-Dashboard**, **Research-Tickets**, Mail-/Kalender-Kurzansicht,
  freie **Visualisierungen** (Phase 14).
- **Bausteine:** Backend-API ueber dem Orchestrator (z. B. FastAPI) -- exponiert Stores
  (antraege/notifications/aktivitaet/research/agenda) + Tools als Endpunkte + einen Event-Stream;
  eigenstaendiges Web-Frontend (echtes Dashboard, nicht das Voice-Panel); **Auth (nur CEO)**; persistenter
  **HTTPS-Host** (der NAS-Container kann die Web-UI mitliefern, sonst kleiner Web-Service).
- **Design-Prinzipien (aus Marktrecherche 2026):** priorisierte/aktionsfaehige Signale, evidenzbasierte
  Approval-Karten, Echtzeit-State-Streaming, sichtbare Governance/Rollback. Referenzmuster: AG-UI
  (Agent<->Frontend-Event-Protokoll), „Agent-Inbox"/Approval-Queue-Dashboards.
- **Abgrenzung:** erweitert/ersetzt das bisherige Voice-Panel (das nur fuer den Voice-Kanal war) durch eine
  eigenstaendige, mobil- und desktop-taugliche **Arbeits-Oberflaeche**.
- **GATE:** Hosting/HTTPS + Auth (nur CEO). **Kosten:** gering (eigener Host/Container).
- **Umsetzung (MVP, 2026-06-27):** „LUNA-OS" als **Desktop-aehnliches Browser-OS** -- `orchestrator/channels/web`
  (FastAPI + statisches Frontend mit **WinBox.js**: Desktop, Top-Bar, Dock, draggbare/resizbare Fenster).
  Apps: **Auftraege** (Live-Inbox offener Antraege als Evidenz-Karten mit Buttons **Freigeben/Ablehnen/Loeschen/
  Mehr-Info**), Meldungen, Aktivitaet, Research, Finanzen. Aktionen ueber die echten Store-Methoden
  (Changelog + CEO-Tor); Mehr-Info legt ein Research-Ticket an. Live per SSE. Lokal verifiziert (Screenshot,
  alle Aktionen ok). Start: `python -m orchestrator.channels.web`.
- **V2 (2026-06-27): NAS-Deployment LIVE.** Zweiter Compose-Dienst `luna-os` (gleiches Image, Befehl
  `python -m orchestrator.channels.web`, Port **8765**), fastapi/uvicorn im Image, **HTTP-Basic-Login**
  (LUNA_OS_USER/LUNA_OS_PASSWORD aus .env; nur aktiv wenn Passwort gesetzt). Verifiziert: ohne Login 401,
  mit Login 200. **Zugriff im LAN: http://192.168.178.129:8765** (User `ceo`, Passwort in orchestrator/.env).
- **V3 (2026-06-27, teilweise):** ✅ **LUNA-Chat-Panel** im OS (animiertes Mond-Symbol mit Zustaenden
  idle/listening/speaking; Klick -> Chat ueber `/api/chat`, Gemini). ✅ **Agentisches „Mehr Info"**
  (LLM-Berater bewertet den Antrag sofort -> Meldung). 🔲 **HTTPS + externer Zugriff offen** (Synology
  Reverse-Proxy + Let's Encrypt auf z. B. `https://os.hanserautisch.synology.me` -> localhost:8765; DSM-GUI-
  Schritt, schaltet zugleich **Mikrofon/Sprach-Eingabe** fuer den Orb frei, da Browser dafuer HTTPS braucht).
- **Offen (spaeter):** echte Sprach-Eingabe (Mikrofon) + TTS am Orb (nach HTTPS), Antrags-Detailansicht,
  mobil-Feinschliff, „Mehr Info" via voll-tool-faehigem HoaConversation statt einfachem LLM-Call.

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

---

## 8. Backlog (niedrige Prioritaet, „ganz nach hinten")

- **Execution-Modellzugang (einziger funktionaler Blocker):** Die Code-Ausfuehrung (Phase 7) nutzt die
  Claude-CLI (claude-opus-4-8). Drei Wege: (a) ~5–10 USD Anthropic-Guthaben, (b) automatisch ab 2026-07-01,
  (c) **lokales LLM** auf gesponserter Hardware -> macht Execution dauerhaft kostenlos. Ziel-Hardware:
  Mini-PC mit **128 GB Unified Memory** (NVIDIA DGX Spark / AMD Ryzen AI Max+ 395 / Mac Studio) + 1 TB SSD;
  Modell z. B. GPT-OSS-120B oder Qwen3-Coder. Anbindung: Chat/Fachagenten trivial (OpenAI-kompatibler
  FallbackBackend), Execution braucht einen neuen Nicht-CLI-Ausfuehrungs-Agenten (eigener Bau). Hardware
  laeuft ueber Produkt-Sponsoring.
- **Container als Non-root:** ✅ erledigt 2026-06-26 (sichere Execution ohne IS_SANDBOX-root-Bypass).
- **Supabase** als Queue-/Store-Backend (laeuft aktuell dateibasiert -- funktioniert; Supabase robuster).
- **Finance Stufe 2.5:** echte Token-Erfassung je Agent/Subagent (CLI-Subagenten liefern keine Tokenzahl).
- **Secrets rotieren (operativ):** im Chat geteilte Keys (GitHub-PAT, OpenAI, Gemini) + NAS-Passwort neu erzeugen.
- **Partner-/Akten-System (CRM-artig):** Mail-Router (sortiert neue Mails in Partner-Akten), Context-Parser
  (versteht Inhalte, leitet naechste Schritte ab), Calendar-Sync (Termine zu Akten), zentraler Akte-Manager
  (Verwaltung, Suche, Bericht, Alerts), optionaler Trend-Monitor je Partner. Idee aus einem LUNA-Self-Dev-Lauf
  (2026-06-25); bewusst zurueckgestellt. Baut auf Gmail/Kalender (Phase 11) + Notifier auf.
