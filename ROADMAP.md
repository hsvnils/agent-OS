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
| 16 | **LUNA-OS (Browser-Arbeitsoberflaeche)** | ✅ **VOLL LIVE 2026-06-27** -- LAN + **HTTPS extern** (`https://os.hanserautisch.synology.me`, ein Lesezeichen ueberall), Login, Mond-Orb/Chat, agentisches Mehr-Info, Detailansicht, Mobil, echte Umlaute, futuristisches Design, Sprach-Kontextbefehle |
| 17 | **LUNA bedient den Rechner / Live-Co-Working** (Computer-Use; paralleles Arbeiten im Gespraech -- ich sehe, sie setzt um, justiert per Sprache, schlaegt vor; z. B. XMind/Mail) | 🔲 geplant (Backlog) |
| 18 | **HCC -> LUNA-OS Konsolidierung** (EIN System = LUNA-OS; nilshubv2/Worker stillgelegt; Supabase = DB; content_ops/CRM/Team/Cutter als LUNA-OS-Apps; Team-Auth/Rollen) | ✅ **K0-K6 KOMPLETT 2026-07-02** -- nur noch 10 LUNA-Tabellen, Vercel/Worker weg; `HCC_INTEGRATION_ROADMAP.md` |
| 19 | **CRM-Akte: Mail-Tracking** (Gmail-Mails je Unternehmen in die CRM-Akte) | ✅ **gebaut 2026-07-03** (`core/crm_mail.py`, quelle='mail', L1-Loop im Bot-Poll; luna-telegram-Neustart fuer den Tick) |
| 20 | **Kanaluebergreifende Nachrichten-Timeline** (Instagram/Mail/Telegram chronologisch) | ✅ **gebaut 2026-07-03** (`CrmStore.timeline`, `/api/crm/timeline`, LUNA-OS-App „Timeline" mit Kanal-Badges) |
| 21 | **Cybersecurity-Agent** (CISO-Ausbau: Zugriffe verhindern · Luecken finden · Luecken schliessen) | ✅ **gebaut 2026-07-03** (`core/security_agent.py`, Checks Secret-Hygiene/Hardening/Dependencies; L1 melden + L2 Antrag; Tool `sicherheits_audit`; gated Loop `SECURITY_AUDIT_ENABLED`; kein Auto-Change = CEO-Tor) |
| 22 | **CISO-Agent ausbauen** (Static-Security-Scan nach SkillSpector-Muster) | ✅ **Kern fertig 2026-07-03** (AST-Code-Scan + Risiko-Score 0-100; OSV.dev-Check der Dockerfile-Pins; unser Code + Pins = 0 Funde). **Optionaler Backlog:** Taint-Tracking, Injection-Muster (-> Phase 23), SARIF |
| 23 | **Haertung externer Eingaben** (Prompt-Injection-/PII-Filter fuer Mail/DM/Web) | 🔨 im Bau — **Inkr. 1 gebaut 2026-07-03** (`core/input_guard.py`: Injection-/PII-Erkennung + Untrusted-Wrap + PII-Redaktion; verankert in `crm_mail`); offen: Wiring web_research + Instagram-DMs |
| 24 | **Skill-/Charta-Standard + gepruefter Skill-Import** (Agent-Skills-Format + Erfolgsmetriken je Charta; Import via Phase-22-Gate) | 🔲 geplant — MITTEL |
| 25 | **Execution-Sandbox-Policy** (deklarativ; Blaupause fuer Phase 17, aus OpenShell/NemoClaw) | 🔲 geplant — MITTEL (an Phase 17 gekoppelt) |
| 26 | **Gedaechtnis: Vektor-Recall + Trajektorien-Lernen** (optional, aus MemPalace/ruflo) | 🔲 optional — NIEDRIG |

**Quer dazu live:** Notifier, Briefings (08:00/20:00), Self-Maintenance/Healing, CFO-Kostenerfassung,
Multi-Provider-Fallback (Gemini/OpenAI), Non-root-Container, zentrales Aktivitaetsprotokoll (adc5).

**Design-Prinzip fuer ALLE autonomen Schleifen -- Loop Engineering:** Neue Loops (Watcher, Briefings,
Self-Dev, Investment-Screen, kuenftig content_ops-Fuetterung) werden nicht als Einzel-Prompts, sondern als
**Loop** entworfen: Ziel (messbar) · Trigger · Lauf · Verifikation/Eval (Maker/Checker) · Stop-Bedingung --
plus Autonomie-Treppe **L1→L2→L3** und Kostenrahmen je Loop. Verbindlich in `governance/autonomie-stufen.md`
(Grundidee: „den Loop entwerfen, der den Agenten ansteuert", statt jeden Prompt von Hand; Osmani u. a., 2026).

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
- **V3 (2026-06-27):** ✅ **LUNA-Chat-Panel** im OS (animiertes Mond-Symbol mit Zustaenden
  idle/listening/speaking; Klick -> Chat ueber `/api/chat`, Gemini). ✅ **Antrags-Detailansicht**
  (`GET /api/antraege/{id}` + Detail-Fenster mit vollem Verlauf/Evidenz). ✅ **Mobil-Feinschliff** (Fenster
  vollflaechig auf schmalen Screens, Dock voll breit, Touch-Buttons; Chat-Eingabe nicht mehr hinterm Dock).
  ✅ **Mikrofon-Eingabe + TTS am Orb** (Web Speech API, browser-nativ -- diktieren + Vorlesen; aktiv auf
  localhost/HTTPS). ✅ **„Mehr Info" agentisch** ueber die volle HoaConversation (echte Tool-Schleife:
  delegate CTO/CFO + recherche_beauftragen; Fallback auf einfachen LLM-Call ohne Anthropic-Key).
  ✅ **Echte Umlaute** in der gesamten Oberflaeche (CEO-Wunsch). ✅ **Futuristisches Design** (Sci-Fi-HUD:
  Sternenfeld + Neon-Gitter, Glasmorphismus, Cyan/Violett-Glow). ✅ **Sprach-/Text-Kontextbefehl**
  („zeig/öffne <app>" blendet die App ein -- per Tippen UND Mikrofon, geraeteuebergreifend; erste Stufe der
  geraeteuebergreifenden Sprach-Kontextanzeige). **Diese beiden V3-Commits sind lokal committet (b94a1d3,
  dbda8f3), aber noch NICHT auf den NAS deployt** (Deploy braucht ausdrueckliche CEO-Freigabe).
- ✅ **HTTPS + externer Zugriff LIVE (2026-06-27):** Synology Reverse-Proxy (Quelle HTTPS
  `os.hanserautisch.synology.me`:443 -> Ziel HTTP localhost:8765, WebSocket-Header fuer SSE) + Let's-Encrypt-
  Zertifikat (`luna-encrypt`, gueltig bis 25.09.2026, dem Reverse-Proxy-Dienst zugeordnet) + **Port-443-
  Freigabe in der Fritz!Box 7530 AX** (TCP 443->443). **Ein Lesezeichen fuer ueberall:**
  **`https://os.hanserautisch.synology.me`** -- funktioniert im Heim-WLAN (Fritz!Box-NAT-Loopback) UND
  unterwegs (Mobilfunk), Login ceo + LUNA_OS_PASSWORD. Verifiziert (curl ueber oeffentliche IP + normale DNS:
  HTTP 401 + TLS ok). Der CEO hat die DSM-/Router-Sicherheitseinstellungen selbst ausgefuehrt; der Assistent
  hat live gelotst + read-only mitgelesen + technisch verifiziert. **Schaltet das Mikrofon/Sprach-Eingabe frei**
  (secure context).
- **Command-Center-Redesign (2026-06-28):** LUNA-OS im **Jarvis-HUD-Stil** -- linke Sidebar-Navigation,
  Topbar (System-Status/Uhr/Suche), zentraler AI-Core/Globe mit audio-reaktivem Orb, Panel-Grid (AI Core
  Overview, Live Intelligence Feed, Active Agents, Mission Timeline, Quick Commands, System Monitor mit Gauges,
  Memory Insights, LLM/Provider-Status), durchgehende „TALK TO LUNA"-Leiste; App-Fenster (WinBox) bleiben.
  **Globales Design-System in `UI.md`** (SSOT fuer den Look -- alle neuen Funktionen folgen ihm). Endpunkt
  `/api/overview`. Echte Daten statt Mock.
- **Live-Voice-LUNA am Orb (2026-06-27):** Orb = sprechende LUNA (Browser-STT + ElevenLabs-Stimme „Lola",
  volle HoaConversation). Hoeren auf Mac+Safari verifiziert (CEO); Sprechen+Hoeren auf Safari ok.
  **Web-Audio-Unlock** (Ton auf Safari/iOS), **Kontext-Anzeige** (Frage zu Anträgen/Tickets -> Panel auf +
  gesprochene Erklaerung), **Satz-Streaming-TTS** + **Barge-in** (Orb antippen unterbricht LUNA) +
  **audio-reaktiver Jarvis-Orb** (Reaktor-Ring, pulsiert mit der Stimme) + HUD-Scan-Sweep.
- **Offen (spaeter, auf Roadmap geparkt):** (a) **Sprach-EINGABE auf iPhone/iPad** via Deepgram-STT
  (MediaRecorder -> /api/stt), da iOS Safari keine Web-Speech-Erkennung hat; (b) **echtes hands-free Barge-in**
  (in LUNA reinreden ohne Tap) braucht Echo-Cancellation -> Pipecat-Vollkanal; (c) **agentische
  Voice-Kontext-Steuerung** -- volle HoaConversation/Tools emittieren „zeige Panel X"/Visualisierung (Phase 14)
  fuer komplexe Anfragen; (d) „Mehr Info" mit eigener Session je Antrag; (e) weiterer Mobil-Feinschliff.

#### Naechste Ausbau-Cluster (CEO-Wunsch 2026-06-27, nach OpenJarvis-Vorbild)
- ✅ **Jarvis Intelligent Features -- proaktive Tages-Insights (MVP, 2026-06-28):** `core/insights.py`
  (Lagebild: offene Entscheidungen, heutige Termine, ungelesene Mails, offene Tickets, Agenda; regelbasiert).
  Tool `lagebild`, ans Morgen-Briefing angehaengt, LUNA-OS-App **Lagebild**. **Ausbau:** Erinnerungen/Routinen,
  Kontext-Vorschlaege („naechste Schritte"), echte Anomalie-Erkennung.
- ✅ **„Your Second Brain" (MVP, 2026-06-28):** `core/brain.py` (Wissensbasis, lexikalische Suche), Tools
  `brain_merken`/`brain_suchen` (quellenuebergreifend: Wissen + Research/Antraege + Gmail + Drive), LUNA-OS-App
  **Wissen**. **Ausbau:** Drive-Volltext-Ingest, semantische Suche (Embeddings), Auto-Ingest aus Mails/
  Research, Verknuepfung mit dem geparkten **Partner-/Akten-System (CRM-artig)**.
- 🔲 **Complete Device Control** (LUNA bedient Geraete/Rechner wie OpenJarvis) = **deckt sich mit Phase 17**
  (Computer-Use). Dort weiterfuehren -- harte Governance (nur auf Anweisung, CEO-Tor, Not-Aus, Audit).
- 🔲 **Investmentagent (CEO-Wunsch 2026-06-28, als Naechstes):** Agent, der Maerkte/Werte **recherchiert +
  analysiert** und **Entscheidungsvorlagen/Entwuerfe** erstellt. HART: **keine personalisierte Anlageberatung,
  keine Trades/Geldbewegungen** -- alles Geld-/Recht-relevante bleibt CEO-/Mensch-Tor (AGENTS.md 4). Nur
  Vorschlaege; Ausfuehrung nie autonom.

### Phase 17 — LUNA bedient den Rechner / Live-Co-Working am Rechner — GEPLANT (Backlog)
- **Ziel:** Auf **ausdrueckliche CEO-Anweisung** kann LUNA den Rechner des CEO **bedienen** -- Apps oeffnen
  und steuern, klicken, tippen, Workflows/Dateiaktionen ausfuehren („mach X in App Y", „lade das hoch",
  „raeum den Ordner auf"). Wie ein Assistent, der Maus/Tastatur uebernimmt.
- **VISION „Paralleles Co-Working" (CEO 2026-06-28):** Nicht nur Einzelauftraege, sondern **gemeinsames
  Live-Arbeiten im Gespraech**: Der CEO **sieht** die offene App, **erzaehlt/bespricht/weist an**, und LUNA
  **setzt es live um** -- der CEO sieht das Ergebnis sofort und **justiert per Sprache** („nein, den Knoten
  woanders", „aendere die Mail so"), LUNA passt an und **schlaegt selbst Dinge vor**. Beispiele:
  **XMind** offen -> CEO beschreibt einen Prozess -> LUNA legt die Knoten/Aeste an, der CEO korrigiert im
  Dialog; **Mail** -> diktieren/besprechen -> LUNA schreibt/aendert (Senden bleibt Mensch-Tor); generell:
  **alles, was der CEO am Rechner tun kann, im Gespraech anweisen/besprechen und LUNA macht es live**. Das ist
  die Vollausbaustufe von Computer-Use (kollaborativ, sprachgesteuert, vorschlagend) -- nicht nur „Befehl ->
  Tat".
- **Bausteine:** (1) **App-Steuerung**: (a) **Claude Computer-Use** (Anthropic; braucht Modellzugang -- gleiches
  Tor wie Execution), (b) **lokale Automatisierung** (AppleScript/osascript, cliclick, macOS-Accessibility-API;
  app-spezifisch tiefer, wo Scripting existiert, z. B. Mail/XMind-Export). (2) **Bildschirm-/App-Wahrnehmung**:
  LUNA muss **sehen**, was auf dem Schirm/in der App ist (Screenshot + ggf. Accessibility-Baum), um praezise
  zu handeln UND um Vorschlaege zu machen. (3) **Gespraechs-Schleife**: bestehende Live-Voice-LUNA (Orb) treibt
  das Co-Working (du sprichst, sie handelt, du justierst). (4) **Lokaler Mac-Runner** (wie der Cutter) fuehrt
  aus; LUNA (NAS) erteilt den Auftrag -> braucht den **NAS->Mac-Kanal**.
- **Governance (HART -- maechtige, riskante Faehigkeit):** **nur auf ausdrueckliche Anweisung, nie autonom**.
  Jede Aktion mit **Geld/Recht/Oeffentlichkeit/Loeschen** = CEO-Tor mit Bestaetigung. **Least-Privilege**
  (nur freigegebene Apps/Ordner), **Not-Aus** (Stopp jederzeit), **Audit** jeder Aktion im
  Aktivitaetsprotokoll (adc5). Voller Rechnerzugriff = hohes Risiko -> strenge Bestaetigungen, Sandbox/
  eingeschraenkter Scope wo moeglich.
- **GATE:** sehr stark (Kontrolle ueber den Rechner). **Kosten:** ggf. Modellzugang (Computer-Use-Modell).

#### MVP-Status „LUNA am Mac" (Stand 2026-06-29)
- ✅ **M1–M4 umgesetzt:** nativer Menueleisten-Orb (`mac/LunaOrb/`, Swift-`.app`), On-Screen-Awareness
  (welche App vorne/laufend) + App-Wissen (Registry installierter Apps, Empfehlung), Aktuator mit Tor
  (Allowlist, Vorschau/Bestaetigung, Not-Aus, Audit, zwei Modi bestaetigen/sofort), `app_oeffnen` (jede
  installierte App), `text_schreiben` (TextEdit), Live-Gespraech (halbduplex, ElevenLabs, Diagnose).
- 🔲 **M5 — Tiefes App-Verstaendnis: Inhalte SEHEN & BEARBEITEN (CEO-Prio 2026-06-29).** Heute kennt LUNA nur
  App-Namen/Fenstertitel, **nicht den Inhalt** (z. B. die Knoten in XMind). Ziel: Inhalte lesen UND
  bearbeiten. Wege: (a) **Vision** — Screenshot -> multimodales Modell „liest" den Schirm (funktioniert generisch,
  auch fuer Electron/Canvas wie XMind; Sehen geht mit Gemini schon heute). (b) **Accessibility-Baum** (AXUIElement)
  fuer native Apps (begrenzt bei Electron-Apps wie XMind). (c) **App-spezifisch ueber Dateiformat/Scripting**
  (z. B. `.xmind` = ZIP+JSON direkt lesen/schreiben; AppleScript fuer Mail/Notes) — praeziser, aber je App
  einzeln. (d) **Bearbeiten generisch** = **Claude Computer-Use** (Vision -> simulierte Maus/Tastatur; gleiches
  Anthropic-Tor, ab 2026-07-01). **Empfehlung:** zuerst „Sehen" (Vision, Screenshot vom Orb -> Modell), dann
  Bearbeiten gegated (Computer-Use generisch oder app-spezifische Recipe je freigegebenem Verb). Screen-Capture
  = neue Berechtigung (Screen Recording am `.app`).
- 🔲 **Voice-Latenz** spaeter optimieren (CEO 2026-06-29: laeuft, aber langsam) — Streaming-TTS, schnelleres
  Modell fuer kurze Antworten, fruehzeitiges Senden.
- 🔲 **NAS-Bruecke „eine LUNA, zwei Gesichter"** — gemeinsamer Live-Zustand (brain/Antraege) statt lokaler Insel.

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

### Neu — CEO 2026-07-02 (Phasen 19-21 + Recherche-Backlog)

- **Phase 19 — CRM-Akte: Mail-Tracking (CEO 2026-07-02):** Die CRM-Akte eines Unternehmens (`crm_companies`
  + `crm_messages`) soll auch **E-Mails** mit tracken. Baustein vorhanden: Google Workspace (Phase 11) ist live
  (`governance/google_workspace.py`, Gmail-Lesen frei). Umsetzung: je CRM-Unternehmen die zugehoerigen Gmail-
  Mails (Match ueber Domain/Absender/Empfaenger) als CRM-Nachricht-Zeilen (Kanal `mail`) in die Akte spiegeln
  -> erscheinen in der Collab-CRM-App neben Instagram-DMs. **Als Loop** (governance/autonomie-stufen.md): Mail-
  Watcher (schon im Bot-Poll) -> Zuordnung zu Unternehmen -> Write-Through nach Supabase (wie CRM-Projektion).
  Sicher: nur Lesen/Spiegeln; Senden bleibt gated.

- **Phase 20 — Kanaluebergreifende Nachrichten-Timeline (CEO 2026-07-02):** Eine **Timeline**, die Nachrichten
  **kanaluebergreifend chronologisch** zeigt (Instagram-DMs + Mails + Telegram + spaeter weitere) -- je Kontakt/
  Unternehmen und/oder global. Baut auf Phase 19 auf (einheitliches `crm_messages`-Schema mit `kanal`-Feld als
  gemeinsamer Nenner). Umsetzung: LUNA-OS-App/Panel „Timeline" -- ein Endpunkt liefert die gemergten, nach Zeit
  sortierten Nachrichten aller Kanaele; Filter je Kanal/Kontakt. Kein Auto-Antworten (Oeffentlichkeit = CEO-Tor).

- **Phase 21 — Cybersecurity-Agent (CISO-Ausbau) (CEO 2026-07-02, recherchiert):** Dedizierter Security-Agent,
  der drei Stossrichtungen bedient: **(a) Zugriffe verhindern · (b) Luecken finden · (c) Luecken schliessen.**
  **Marktstand/Ablaeufe 2026 (recherchiert):** Security-Agenten laufen als **kontinuierlicher Loop** Scoping ->
  Discovery (Angriffsflaeche/Assets) -> Priorisierung -> **Exploitability-Validation** (nicht nur „CVE da",
  sondern „wirklich ausnutzbar?") -> Remediation/Mobilization. Bausteine anderer: Vulnerability-Discovery im
  eigenen Code inkl. Zero-Days + Auto-Patch (Google DeepMind **CodeMender**), Alert-Triage/Investigation
  (SOC-Tier-1-Automatisierung, Torq **Socrates** ~90 %), autonome Remediation-Pipelines (IBM **Autonomous
  Security**, „Repair Agent"), **Abwehr agentischer Angriffe** (IBM 2026: eigene Agenten koennen Ziel werden).
  **Fuer LUNA (L1->L2, KEINE autonome Systemaenderung):** Loop wie unsere anderen -- L1 melden (Findings), L2
  Vorschlag als **Antrag/Branch+Tests** (CEO-Merge). Kostenlose Bausteine: Dependency-CVEs (`pip-audit`/
  `npm audit`), Secret-Scan (unser `leak_guard` + gitleaks), statische Code-Sicherheitspruefung (Fachagent /
  `security-review`-Skill), Config-/Permission-Audit (Non-root-Container ✓, Supabase-RLS ✓, `.env`-Rechte,
  offene Ports). Nutzt vorhandene **Zugriffs-Governance** (AGENTS.md 5.7: CISO autorisiert, CTO setzt um) +
  Self-Maintenance. **Wirkung (Zugriff sperren/aendern, Keys rotieren) bleibt CEO-Tor.** Verwandt: NVIDIA
  **SkillSpector** (Security-Scanner fuer Agent-Skills) + **OpenShell** (sichere Agenten-Sandbox) -- s. u.

- **PRUEFEN — NVIDIA Agent Skills (Open Source, GitHub) (CEO 2026-07-02):** NVIDIA hat 2026 Agent-Skills/Tools
  frei veroeffentlicht (`github.com/NVIDIA/skills`, `skills.sh`, NeMo-Agent-Toolkit). **Befund:** die Kern-Skills
  sind **NVIDIA-software- + Physical-AI/Robotik-spezifisch** (CUDA-X, Simulation, autonome Fahrzeuge) -> fuer
  unser Content-/Business-Agentenunternehmen **NICHT 1:1** uebernehmbar. **ABER wertvoll:** (1) **SkillSpector**
  (`github.com/NVIDIA/skillspector`) -- Security-Scanner fuer Agent-Skills (Schwachstellen/malicious patterns);
  passt direkt zu Phase 21, da wir Claude-Code-Skills nutzen. (2) **OpenShell** (`github.com/NVIDIA/openshell`)
  -- sichere Sandbox-Runtime fuer autonome Agenten; relevant fuer unsere Execution-Engine (Phase 7). (3)
  Skill-Oekosystem **VoltAgent/awesome-agent-skills** (1000+ Claude-Code-kompatible Skills) gezielt nach fuer uns
  nutzbaren Skills durchsuchen. **Ergebnis = Antrag (CEO-Tor).**

- **PRUEFEN — MemPalace (persistentes Gedaechtnis) (CEO 2026-07-02):** Viral gewordenes Open-Source-Langzeit-
  gedaechtnis: **verlustfrei** + hierarchisch nach **Method-of-Loci** (Wings/Rooms/Halls), local-first
  (ChromaDB+SQLite), **inkrementelles/token-frugales Laden** (~170 Token Startup), Schichten (working/episodic/
  semantic/procedural), Spitzenwerte auf LongMemEval. **Wir haben schon:** Second Brain (`core/brain.py`),
  Memory (`core/memory.py`, JSONL append-only + Recall), Datei-Auto-Memory -- aber **flacher/einfacher**.
  **Lernbar:** hierarchische statt flache Organisation · verlustfreie Speicherung + inkrementelles Recall (passt
  zu unserem Kostenprinzip) · local-first. **Vorsicht:** Provenienz/Hype fragwuerdig („Promi-Entwickler", 22k
  Stars in 48h) -> **Substanz + Lizenz verifizieren** vor Uebernahme; wahrscheinlich **Konzepte** uebernehmen,
  nicht das Tool. **Ergebnis = Second-Brain-Ausbau-Antrag (CEO-Tor).**

- **PRUEFEN — „The Agency" (agency-agents Issue #525) (CEO 2026-07-02):** Sammlung rollen-/persona-basierter
  Spezialisten-Agenten, **deliverable-fokussiert**, „battle-tested" Workflows mit Erfolgsmetriken. **Wir haben
  schon:** 14 Abteilungs-Agenten mit Charten (AGENTS.md). **Uebernehmen-Kandidaten:** staerkerer **Ergebnis-/
  Deliverable-Fokus** + **Erfolgsmetriken je Charta**, ausgepraegtere Personas, validierte Workflows. Umsetzung
  nur ueber den **Head of Agents auf CEO-Anweisung** (Charta-Schreibrecht, AGENTS.md 3.3). Quelle:
  `github.com/msitarzewski/agency-agents/issues/525`. **Ergebnis = Charta-Diff-Vorlage (CEO-Tor).**

### Neu — CEO 2026-07-03 (Phasen 22-26: aus Recherche „Agent-Oekosystem" konkretisiert)

> Ergebnis der Recherche zu **NVIDIA SkillSpector/Skills/OpenShell, MemPalace, ruflo, agency-agents #525**.
> Die drei „PRUEFEN"-Punkte oben (NVIDIA Skills, MemPalace, The Agency) sind hiermit in konkrete Phasen
> ueberfuehrt; ruflo ist neu bewertet. Kurzfazit: **SkillSpector = Volltreffer** (direkter Phase-21-Ausbau),
> NVIDIA-Skills-**Format** + OpenShell-**Prinzip** uebernehmbar, MemPalace **validiert** unseren Ist-Stand,
> ruflo grossteils Overkill (zwei Rosinen). Reihenfolge = Prioritaet. **Volle Begruendung je Quelle (uebernehmen/
> teilweise/verworfen) + Quellen: `docs/entscheidungs-register.md` (Eintrag 2026-07-03).**

- **Phase 22 — CISO-Agent ausbauen (Static-Security-Scan nach SkillSpector-Muster) [HOCH]:**
  - **Ziel:** Phase-21-Agent von 3 Checks (Secret-Hygiene/Hardening/`pip-audit`) auf ein breiteres, regel-
    basiertes Set heben, das SkillSpector-Kategorien nachbaut -- angewandt auf UNSEREN eigenen Code + genutzte
    Tools/Skills. Klarster „1:1 lernbar"-Kandidat (gleicher Stack: Python, regelbasiert wie `security_agent.py`).
  - **Bausteine:** (a) AST-Scan gefaehrlicher Aufrufe (`exec`/`eval`/`subprocess`/`os.system`/`shell=True`);
    (b) Taint-Tracking Credential/Datei -> Netzwerk-Sink (ergaenzt `leak_guard`); (c) **OSV.dev**-Abfrage als
    Ergaenzung zu `pip-audit` (kein API-Key, Offline-Fallback, mehr Oekosysteme); (d) Muster fuer Prompt-
    Injection/Excessive-Agency/Tool-/Memory-Poisoning gegen unsere Tool-Definitionen; (e) **Risiko-Score 0-100**
    + Ausgabe (Terminal/JSON/**SARIF**) + Exit-Code-Gate.
  - **Quelle:** NVIDIA **SkillSpector** (`github.com/nvidia/skillspector`; 68 Muster/17 Kategorien; Studie
    Liu et al. 2026: 26,1% Skills verwundbar, 5,2% boesartig).
  - **Governance/GATE:** reiner Melde-/Vorschlags-Loop (L1 melden, L2 Antrag); jede WIRKUNG (Fix/Sperre/
    Rotation) bleibt CEO-Tor. Scan selbst lokal/kostenlos = kein GATE. **Lizenz vor Code-Uebernahme pruefen**
    (Regel-Nachbau ist unproblematisch). Baut direkt auf Phase 21.
  - **Umsetzung (Inkrement 1, 2026-07-03):** `_check_code_security()` in `core/security_agent.py` -- AST-Scan
    des `orchestrator/`-Codes auf `os.system/os.popen`, `subprocess(..., shell=True)`, `eval/exec`,
    `__import__`, `pickle.load(s)`, `yaml.load` ohne Loader; praezise (nur echte Calls, Tests uebersprungen,
    sicheres Listen-`subprocess.run` bleibt unbeanstandet). **Risiko-Score 0-100** im `lauf()`-Ergebnis + in der
    Meldung. +4 Tests (16 gruen); realer Scan unseres Codes = **0 Funde** (clean). **Offen (naechste Inkremente):**
    Taint-Tracking Credential->Netz, Prompt-Injection-/Tool-Poisoning-Muster, SARIF-Ausgabe. Wirkt nach
    `luna-telegram`-Neustart (reiner Code-Change).
  - **Umsetzung (Inkrement 2, 2026-07-03):** `_check_osv()` -- prueft die **gepinnten** Dependencies aus
    `deploy/Dockerfile` (`name==version`, `>=`-Pins ignoriert) unabhaengig von `pip-audit` gegen **OSV.dev**
    (kein API-Key; injizierbarer HTTP-Client -> offline/testbar; nur aktiv wenn verdrahtet, sonst kein Rauschen).
    HTTP-Client in `hoa_tools.sicherheits_audit` per `urllib` (Timeout 10s, Fehler -> uebersprungen). Live gegen
    unsere 7 Pins verifiziert = 0 CVEs. Ergaenzt `_check_dependencies` (installierte Umgebung) um die DEKLARIERTE
    Pin-Ebene. +4 Tests (Suite 20 gruen, Gesamt 344 gruen).
  - **Status 2026-07-03: KERN FERTIG.** Die zwei hochwertigsten Bausteine (AST-Code-Scan + OSV.dev) sind live.
    **Optionaler Backlog (abnehmender Grenznutzen fuer unser Setup):** (3) Taint-Tracking Credential->Netz --
    `leak_guard` deckt das Kernrisiko schon; (4) Injection-/Tool-Poisoning-Muster -- greift real erst bei
    externen Eingaben -> in **Phase 23** verschoben; (5) SARIF-Ausgabe -- erst sinnvoll mit einer CI, die sie
    konsumiert.

- **Phase 23 — Haertung externer Eingaben (Prompt-Injection-/PII-Filter) [HOCH-MITTEL]:**
  - **Ziel:** Inhalte, die LUNA von aussen verarbeitet (Gmail, Instagram-DMs, Web-Recherche, spaeter weitere),
    werden VOR Modell-/Tool-Nutzung auf Injection-Muster + PII gefiltert/markiert -- Schutz vor „indirect
    prompt injection" ueber Fremdinhalte.
  - **Bausteine:** regelbasierter Input-Sanitizer/Klassifikator (Injection-Muster aus Phase 22 wiederverwenden);
    PII-Erkennung vor Ausleitung nach aussen (ergaenzt `leak_guard` beim Senden). Als Loop mit Not-Aus.
  - **Quelle:** SkillSpector (Injection-Muster) + `ruvnet/ruflo` (AIDefence, 14-Typ-Pipeline).
  - **Governance/GATE:** rein defensiv (filtern/markieren), keine autonome Aktion; verdaechtige Inhalte ->
    Meldung. Lokal = kein GATE. Haengt logisch an Phase 22.
  - **Umsetzung (Inkrement 1, 2026-07-03):** `core/input_guard.py` -- regelbasiert/deterministisch (kein LLM):
    `pruefe(text)` erkennt Prompt-Injection-Muster (Instruktions-Override DE/EN, Rollen-Uebernahme,
    System-Prompt-Leak, Anti-Refusal, Exfiltration, Tool-Schmuggel, versteckte HTML-Anweisung, unsichtbare/
    Bidi-Zeichen) + PII (email/iban/kreditkarte mit Luhn-Check); `umschliesse_extern()` (Untrusted-Boundary
    gegen indirect injection), `redigiere_pii()`, `markiere_wenn_verdaechtig()`. Konservativ -> kein Fehlalarm
    auf harmlosen Nachrichten (verifiziert). **Verankert in `core/crm_mail.py`:** eingehende Mails werden vor
    dem Speichern gescannt und bei Verdacht sichtbar markiert (erscheint in CRM/Timeline). +12 Tests
    (Gesamt 356 gruen). **Offen (naechste Inkremente):** gleiche Verankerung in Web-Recherche-Ergebnissen und
    Instagram-DM-Eingang; optional Injection-Meldung an CISO/Security. Wirkt nach `luna-telegram`-Neustart.

- **Phase 24 — Skill-/Charta-Standard + gepruefter Skill-Import [MITTEL]:**
  - **Ziel:** Unsere Agenten/Faehigkeiten als portable, versionierbare Skills nach dem offenen „Agent Skills"-
    Format formalisieren; Tuer fuer geprueften Import von Community-Skills oeffnen.
  - **Bausteine:** (a) Schema `SKILL.md` (Instruktion) + `skill-card` (Identitaet/Governance/Version) + Eval-/
    Testset + optional `BENCHMARK.md` + optionale Signatur -- unsere `agents/*.md`-Charten darauf heben; (b) je
    Charta **Ergebnis-/Deliverable-Fokus + Erfolgsmetriken** (aus „The Agency" #525); (c) Import-Pipeline fuer
    Fremd-Skills -- **JEDER Import zuerst durch das Security-Gate aus Phase 22** (Skills mit Skripten 2,12x
    haeufiger verwundbar).
  - **Quelle:** `NVIDIA/skills` (Format), `VoltAgent/awesome-agent-skills` (1000+ Skills), agency-agents #525
    (Metriken). **Inhaltliche** NVIDIA-Skills (CUDA/Jetson) bleiben irrelevant -- nur das Format zaehlt.
  - **Governance/GATE:** Charta-Aenderungen NUR Head of Agents auf ausdrueckliche CEO-Anweisung mit Diff
    (AGENTS.md 3.3); jeder externe Skill = CEO-Tor + Security-Gate.

- **Phase 25 — Execution-Sandbox-Policy (deklarativ) fuer Phase 17 [MITTEL, konzeptionell]:**
  - **Ziel:** Formale, deklarative Sicherheits-Policy fuer die Execution/Computer-Use-Faehigkeit (Phase 7/17):
    allow-listed Dateipfade, Egress-Regeln, Syscall-/Prozess-Deny, Credentials nur als Env (nie im Sandbox-FS)
    -- ergaenzt unser bestehendes „Branch+Tests+CEO-Merge, non-root".
  - **Bausteine:** Policy-Schema (YAML) + Enforcement-Punkt vor Datei-/Netz-/Prozess-Aktionen. Als **Blaupause**,
    nicht Voll-Adoption (OpenShell ist Rust/schwer).
  - **Quelle:** `NVIDIA/openshell` (Defense-in-Depth, deklarative YAML-Policy) + `NVIDIA/NemoClaw` (24/7-Agenten-
    Referenzstack).
  - **Governance/GATE:** staerkt genau die Phase-17-Governance (Least-Privilege, Not-Aus, Audit). Design-Freigabe;
    greift erst mit Phase 17 (daran gekoppelt).

- **Phase 26 — Gedaechtnis: Vektor-Recall + Trajektorien-Lernen (optional) [NIEDRIG]:**
  - **Ziel:** Optionaler Ausbau von `brain.py`/`memory.py`, WENN das Volumen waechst: semantischer Recall via
    Embeddings + „was hat funktioniert"-Lernen aus vergangenen Laeufen.
  - **Bausteine:** (a) Vektor-Recall-Schicht (lokal, z. B. ChromaDB/SQLite) ueber den bestehenden verlustfreien
    Stores -- unsere Zwei-Ebenen-Struktur (`MEMORY.md`-Index ~ „Closets", Fakt-Dateien/JSONL ~ „Drawers")
    entspricht schon MemPalace; (b) Trajektorien-Store fuer erfolgreiche Ablaeufe.
  - **Quelle:** **MemPalace** (Method-of-Loci, ~170-Token-Wake-up, Zero-LLM-Writes -- **validiert** unseren
    Ansatz) + `ruflo` (Trajektorien-Learning).
  - **Governance/GATE:** local-first, token-frugal, keine externe Ausleitung; kein GATE. Heute reicht
    Index+Keyword -> bewusst optional/spaeter. Substanz/Lizenz von MemPalace vor Tool-Uebernahme pruefen
    (eher Konzepte als das Tool uebernehmen).

- **Nicht weiterverfolgen (aus derselben Recherche):** NVIDIA-Skill-**Inhalte** (CUDA/Jetson), **ruflo als
  Framework** (Foederation/Byzantine-Consensus = Overkill fuer ein Ein-CEO-Unternehmen; TS-Stack), **OpenShell
  als Voll-Adoption** (Rust). agency-agents #525 liefert nur den Metrik-/Deliverable-Gedanken (in Phase 24).

### Aelterer Backlog

- **Social Media Analyzer (CEO-Wunsch 2026-06-29):** Agent/Tool, in das der CEO **monatlich** die Zahlen aus
  **Instagram- und Facebook-Insights** laedt (Export/CSV oder manuell), das daraus die Kennzahlen aufbereitet
  und **automatisch das Media-Kit in Canva befuellt**. Bausteine: (1) Insights-Import (CSV/Screenshot/spaeter
  Meta-Graph-API), (2) Kennzahlen-Aufbereitung + Monats-Historie (wie die CFO-Kostenstatistik), (3)
  **Canva-Autofill** ueber Canva Connect API (Brand-Template-Autofill: Datensatz -> Design) ODER Canva-MCP.
  Abklaeren: Canva-Plan/API-Zugang + Kosten (CFO), Meta-API-Zugang vs. manueller Export, Datenschutz. Posten/
  Veroeffentlichen bleibt CEO-Tor; Tool liefert das befuellte Media-Kit als Entwurf. Ergebnis = Antrag (CEO-Tor).
- **ZEITNAH PRUEFEN — „Gemini Omni" fuer den Cutter (CEO-Wunsch 2026-06-29):** pruefen, ob Googles
  multimodales/Omni-Modell den Cutter (Phase 15) verbessert — z. B. inhaltliches Szenen-/Highlight-Verstaendnis,
  bessere Reihenfolge/Schnittauswahl, Auswahl des „besten Ausschnitts", evtl. Untertitel/Sprachverstaendnis.
  Abklaeren: konkreter Modellname/Verfuegbarkeit, Kosten (CFO-Kostenvoranschlag), Datenschutz (Clips gehen an
  Google), Mehrwert vs. lokale Gratis-Pipeline. Ergebnis = entscheidungsreifer Antrag (CEO-Tor). **Prioritaet:
  zeitnah** (nicht „ganz nach hinten").
- **Cutter „aus Profi-Videos lernen" (Stil-Analyzer, CEO-Idee 2026-06-27):** Realistische Stufe = ein
  **Stil-Profil-Extraktor**: Profi-Reels einlesen -> Schnitt-Grammatik messen (Szenenwechsel/Cliplaengen via
  Scene-Detection, Uebergangs-Typ Hartschnitt-vs-Crossfade, Farbstatistik/Grade, Zoom/Crop-Verhalten,
  Beat-/Musik-Sync) -> `stil-profil.json`, das die bestehende ffmpeg-Pipeline steuert (datengetriebenes
  Tuning, kostenlos, lokal). **Nicht** realistisch: beliebige Effekte/Plugins/LUTs exakt erkennen + 1:1
  reproduzieren (neuronaler Edit-Style-Transfer, Forschungsniveau). Reine Analyse ist lokal/gratis; Feature =
  CTO-Antrag. Gehoert zu „Cutter intelligenter machen" (Phase 15) / OpenCut-Richtung.
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
  **Erster Baustein umgesetzt 2026-07-01 (Branch feat/insider-crm, noch nicht deployt):** Collab-CRM unter dem
  CRO -- kanalagnostischer `CrmStore` (`orchestrator/core/crm.py`), Instagram-Webhook, regelbasierte
  Klassifikation + To-do-Vorschlaege, LUNA-OS-App „Collab-CRM". Das kanalagnostische Fundament (Quelle
  instagram|telegram|gmail) ist die Basis fuer den Rest dieses Systems. Live-Empfang wartet auf die Meta-App
  (GATE B). Details in `CRM_PLAN.md`.
