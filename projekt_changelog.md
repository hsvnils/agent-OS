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
