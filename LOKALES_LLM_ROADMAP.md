# Roadmap: Lokales LLM (M6) — LUNA mit Ollama auf dem MACO470

- Status: in Umsetzung
- Stand: 2026-09-25
- Arbeitsbranch: `ai/lokales-llm`
- Basiscommit: `01e9919`
- Naechster Schritt: CEO-Go fuer Merge + Deploy + Neustart von Etappe 3b; danach `.wslconfig` `memory=8GB`
  (unterbricht WSL); danach Etappe 2.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel

**CEO-Vorgabe (2026-09-25):** Die API-Token-Nutzung Richtung Claude und ChatGPT so niedrig wie moeglich halten.
Laengere Denkprozesse sind — vor allem nachts — unkritisch. Deshalb wird das lokale LLM je Bereich **zuerst**
gefragt; die Cloud bleibt Fallback.

LUNA nutzt das lokale LLM auf dem MACO470 (Ollama, `qwen3:30b-a3b`) — zuerst fuer Fachagenten und Hintergrund-Jobs,
dann im Chat. Wirkung: weniger Cloud-Kosten, **BF-05** („alle Anbieter erschoepft" beim Gemini-Gratis-Limit)
behoben, LUNA bleibt ohne Anthropic-Guthaben arbeitsfaehig.

## Register und bekannte Fehler (B3)

- Register: „Lokales LLM auf dem MACO470: 7-30B ja, 120B-Klasse nein" (BESCHLOSSEN 2026-07-14);
  „Modell-Guthaben/Provider-Robustheit -> lokales LLM (M6)" (ZURUECKGESTELLT 2026-07-08); Nemotron 3 Ultra
  (SPAETER/OPTIONAL). `docs/maco470-roadmap.md` M6: Anbindung „trivial ueber den OpenAI-kompatiblen
  FallbackBackend", nur LAN, keine Portfreigabe (CISO-Notiz).
- Bekannte Fehler: BF-05 (Ziel dieser Roadmap), BF-02 (MACO470 nach Neustart ohne Anmeldung tot — betrifft
  auch Ollama -> Fallback auf Cloud muss immer bleiben).

## Analyse (Belege, gemessen am 2026-09-25)

**Server**
- Ollama **0.34.0** auf Windows, erreichbar unter `http://192.168.178.184:11434` aus WSL **und von der NAS**
  (`ssh luna-nas curl …/api/version`). Modelle: `qwen3:30b-a3b` (18,6 GB, Q4_K_M, Tools + Thinking),
  `gemma3:27b` (17,4 GB, keine Tools).
- **Keine Authentifizierung:** `GET /api/tags` von jedem LAN-Geraet -> `200`. -> CISO-Thema.
- Hardware: AMD Ryzen AI 9 HX 470, Radeon 890M, 32 GB verloetet (WSL sieht 14 GB). Modell geladen:
  **20,4 GB, davon 12,7 GB auf der iGPU** (Rest CPU).
- Kontextfenster Server-Standard: **4.096 Token** (`/api/ps`).

**Geschwindigkeit `qwen3:30b-a3b`**
| Messung | Ergebnis |
|---|---|
| Modell laden (kalt) | ~30 s |
| Prompt einlesen, 11.836 Token (volle Werkzeugliste) | 48,5 s (244 Tok/s) — **mit Cache beim naechsten Aufruf 0,2 s** |
| Antwort erzeugen | 14,7–18,8 Tok/s |
| Tool-Wahl mit allen 97 Werkzeugen, 16k Kontext | 3/3 richtig (`kalender_agenda` 2x, `antraege_zeigen`), 25–55 s je Aufruf |
| Einfacher Tool-Aufruf, kleine Liste (`/v1`) | 13,6 s, richtig |

- **Die Zeit geht ins Denken:** 250–950 Token Denkschritte je Aufruf. `think:false` (nativ) und `/no_think`
  werden von diesem Modell-Tag **nicht befolgt** (Denktext landet im Inhalt bzw. verbraucht `max_tokens`).
  Ein LUNA-Chat-Zug braucht meist 2 Aufrufe (Tool + Antwort) -> **~1–2 Minuten**. Fuer Hintergrund-Jobs ok,
  fuer den Chat als Hauptmodell zu langsam.

**Stilles Fehlverhalten (kritisch)**
- LUNAs Code spricht Ollama ueber die OpenAI-Schnittstelle (`/v1`) an; dort laesst sich das Kontextfenster
  **nicht pro Aufruf** setzen. Mit Server-Standard 4.096 wurde die Werkzeugliste auf **2.050 Token
  abgeschnitten** -> **falsches Werkzeug** (`crm_zeigen` statt `antraege_zeigen`), ohne Fehlermeldung.
  -> Das Kontextfenster muss **am Server** auf mindestens 16.384 stehen, bevor LUNA das Modell nutzt.

**Code (Anbindungspunkte)**
- `core/model_router.py`: Chat immer zuerst Anthropic; Fallback nur bei Fehlertext-Stichworten
  (`_ist_fallback_fehler` :51-55) — **Verbindungsfehler/Timeouts loesen keinen Fallback aus** (:81).
  Fallback-Kette `bot.py:1155-1164` / `web/app.py:599-604`: Gemini -> OpenAI. Kein Timeout gesetzt (SDK-Standard
  600 s). Der OpenAI-kompatible Pfad **kann Tools** (`_zu_openai_tools`, `_zu_openai_messages`).
- `core/backends.py` `FallbackBackend` (Fachagenten, CFO 03:00, Self-Dev 09:00, Content-Feed 07:00,
  Innovation): faengt jeden Fehler, ohne Tools, `max_tokens=1024` — mit Denk-Modell zu knapp.
- `core/ig_analyse.py` hat schon einen lokalen Schalter (`IG_ANALYSE_BASE_URL/_KEY/_MODELL`, Test vorhanden).
- `core/kosten.py`: unbekannte Modelle werden mit **1/5 USD je 1 Mio. Token** gebucht, Provider „?" -> lokal
  wuerde faelschlich Kosten zeigen.
- Nicht geeignet: Execution (Claude-CLI), Vision/Video (Gemini), Web-Recherche-Eskalation (Anthropic-Servertool),
  Sprachkanal (Streaming, pipecat).
- 97 HoA-Werkzeuge, ~12.000 Token Definitionen.

## Scope

Server-Einstellungen (Etappe 0, durch den CEO), lokaler Provider im Code mit Schalter, Hintergrund-Jobs auf lokal,
lokal als Chat-Fallback, Kosten/Monitoring/Doku. Optional: nicht-denkende Modellvariante (CEO-Tor).

## Nicht-Scope

- Execution/Code-Umsetzung (Claude-CLI) — eigenes Vorhaben (Nicht-CLI-Ausfuehrungs-Agent)
- Vision (`/api/sehen`), Cutter-Video-KI, Cutter-Reihenfolge, Web-Recherche-Eskalation, Sprachkanal
- Lokal als **Haupt**modell fuer den Chat (erst nach Etappe 4 und eigener Entscheidung)
- Modell-Zeilen in den Charten (`agents/`, nur HoA auf CEO-Anweisung)
- Hardware (eGPU), Portfreigabe nach aussen, Loeschen vorhandener Modelle
- Schutzbereiche laut `governance/roadmap-workflow.md` B4

## Etappen

### Etappe 0: Server absichern und einstellen (CEO am Windows-Rechner, CISO-Freigabe)

- Status: verifiziert (2026-09-25; Pruefung 3 vom MacBook steht noch aus) — Firewall `RemoteAddress`
  = `192.168.178.129`, `172.16.0.0/12`; `OLLAMA_CONTEXT_LENGTH=16384`, `OLLAMA_KEEP_ALIVE=30m`. Pruefung 1 NAS ok,
  2 WSL ok, 4: `prompt_tokens` **11.837** (vorher 2.050), Werkzeug **`antraege_zeigen`** richtig, `context_length`
  16384, Entladen nach 30 min. Stolperstein: Ollama startete nach „Quit" erst beim zweiten Versuch.
- Ziel / Scope: (a) **Windows-Firewall:** Port 11434 eingehend nur von der NAS (`192.168.178.129`), dem
  WSL-Netz und localhost; (b) Umgebungsvariable **`OLLAMA_CONTEXT_LENGTH=16384`**; (c) **`OLLAMA_KEEP_ALIVE=30m`**
  (Modell bleibt 30 min geladen, spart 30 s Ladezeit; danach wird RAM fuer den Cutter frei); Ollama neu starten.
  Der Agent liefert die fertigen Befehle (PowerShell).
- Gate: alle Pruefungen unten wie erwartet.
- Verifikation:
  1. von der NAS: `ssh luna-nas curl -s -m 5 http://192.168.178.184:11434/api/version` -> erwartet `{"version":…}`
  2. aus WSL: `curl -s -m 5 http://192.168.178.184:11434/api/version` -> erwartet `{"version":…}`
  3. vom MacBook (anderes LAN-Geraet): `curl -m 5 http://192.168.178.184:11434/api/tags` -> erwartet **Timeout**
  4. `/v1`-Aufruf mit voller Werkzeugliste „Zeig mir offene Antraege." -> erwartet `prompt_tokens` ≈ 11.800 (nicht
     2.050) und Werkzeug `antraege_zeigen`; `/api/ps` -> `context_length` 16384
- Dry-Run: Firewall-Regel zuerst nur anlegen und mit Pruefung 1–3 testen, bevor die offene Standardregel
  entfernt wird.
- Risiko / Rueckweg: falsche Regel sperrt die NAS aus -> Pruefung 1 schlaegt fehl -> Regel loeschen. RAM:
  16k-Kontext = 20,4 GB geladen (gemessen); mit Cutter-Last knapp -> Keep-Alive begrenzt die Dauer.
- Abhaengig von: – · Aufwand: klein (CEO ~15 min) · Risiko: niedrig
- Freigaben: CISO (Zugriffs-Policy `governance/zugriffs-policy.md`), CEO fuehrt aus.

### Etappe 1: Lokaler Provider im Code (ohne Wirkung bis zur Aktivierung)

- Status: deployt (2026-09-25) — `core/lokal_llm.py`; Schalter je Bereich
  `LOCAL_LLM_FACHAGENTEN` / `LOCAL_LLM_CHAT` = `zuerst|zuletzt|aus` (ersetzt das geplante `LOCAL_LLM_FUER`), Timeout
  300 s, max_tokens 4096, keine Wiederholungen. Tests 809 passed / 0 failed (11 neue, 4 Gegenproben rot wie erwartet).
  Live-Probe Fachagenten-Pfad gegen Ollama: 98 s, saubere deutsche Antwort, Claude-CLI nicht aufgerufen.
  Gesundheits-Check nur in `self_maintenance` (meldet proaktiv, Dedup) — Betriebs-Wacht bewusst nicht doppelt.
  **Deployt 2026-09-25** (Merge `271c3e9`, `sync-to-nas.sh --no-restart`, 362 Dateien, keine `.env`; Neustart beider
  Container durch den CEO; Web 401/200 wie erwartet). Chat-Probe zeigte BF-18 (Anthropic-Schluessel ungueltig,
  seit Juli, unabhaengig von dieser Etappe).
  Verhaltensaenderung auch ohne Schalter: Verbindungsfehler/Timeouts bei Anthropic loesen jetzt den Fallback aus;
  leere Fallback-Antworten gelten als Fehler (naechster Anbieter statt leerem Text).
- Ziel / Scope: neue `.env`-Schluessel `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_TIMEOUT` (Standard
  120 s), `LOCAL_LLM_MAX_TOKENS` (Standard 4096) und `LOCAL_LLM_FUER` (`jobs`, `chat` oder leer = aus).
  - Fallback-Kette in `bot.py`/`web/app.py` um Eintrag „lokal" erweitern (Position je nach `LOCAL_LLM_FUER`).
  - `model_router._ist_fallback_fehler`: Verbindungsfehler/Timeouts loesen den naechsten Anbieter aus.
  - Denktext (`<think>…</think>`) aus Antworten entfernen; `finish_reason=length` ohne Inhalt = Fehler ->
    naechster Anbieter.
  - `core/kosten.py`: Provider „lokal", 0 EUR. `dienste_register`: Eintrag „Ollama (lokal)".
  - Gesundheits-Check in `self_maintenance` + Betriebs-Wacht („lokales LLM nicht erreichbar", nur wenn aktiv).
  - Doku: `docs/datenfluesse.md` (neuer Dienst, IP statt Hostname -> von Hand), `.env`-Schluessel in der Doku.
- Gate: Tests gruen (neue Tests: Fallback bei Verbindungsfehler, Denktext-Filter, Kosten 0, Schalter aus =
  Verhalten unveraendert); Doku-Check ok.
- Verifikation: `pytest orchestrator/tests -q` -> `0 failed`; Test „Schalter aus" beweist identische
  Fallback-Kette wie heute; Gegenprobe je neuem Test.
- Dry-Run: `deploy/sync-to-nas.sh --dry-run` vor dem Deploy.
- Risiko / Rueckweg: ohne `LOCAL_LLM_FUER` keine Verhaltensaenderung; `git revert`.
- Abhaengig von: – (Code), Aktivierung erst nach Etappe 0 · Aufwand: mittel · Risiko: niedrig
- Freigaben: Etappe, Merge, **Deploy auf die NAS + Neustart beider Container (CEO, sudo)**.

### Etappe 1b: Chat-Fallback bei ungueltigem Schluessel + Kuerzungsschutz (BF-18, CEO-Go 2026-09-25)

- Status: deployt (2026-09-25, `0d35a90`)
- Ziel / Scope: `401`/`authentication_error` gilt im `ModelRouter` als Fallback-Grund (Gemini springt ein);
  Chat-Fehler werden mit echter Ursache ins Container-Log und ins Aktivitaetsprotokoll geschrieben (Kategorie
  `fehler`); Telegram meldet „⏳ Ich denke lokal nach" wenn `LOCAL_LLM_CHAT=zuerst`; **Kuerzungsschutz**: meldet
  Ollama weniger als die Haelfte der geschaetzten Prompt-Token, wird die Antwort verworfen und der naechste
  Anbieter gefragt (BF-17 kann sonst bei langem Verlauf wiederkehren).
- Verifikation: Tests 813 passed / 0 failed (4 neue, Gegenproben rot); Probelauf mit NAS-Konfiguration: „Hallo"
  -> Antwort in 2,7 s ueber Gemini (vorher 401-Fehler); mit `LOCAL_LLM_CHAT=zuerst`: „Hallo" 141 s lokal (kalt),
  „Welche Antraege sind offen?" 28 s lokal mit Werkzeug `antraege_zeigen`; Schaetzung 14.634 vs. gemeldet 13.614.
- Risiko: Prompt hat schon ohne Verlauf ~13.600 Token bei 16.384 Kontext -> nach wenigen Nachrichten greift der
  Kuerzungsschutz und Gemini antwortet. Folgeschritt: `OLLAMA_CONTEXT_LENGTH=32768` (mehr RAM, ~+1,6 GB).

### Etappe 2: Hintergrund-Jobs auf lokal

- Status: geplant
- Ziel / Scope: `LOCAL_LLM_FACHAGENTEN=zuerst` in der NAS-`.env`: FallbackBackend-Jobs (CFO 03:00, Content-Feed 07:00,
  Self-Dev/Innovation 09:00) nutzen zuerst lokal, Cloud bleibt Fallback. Zusaetzlich Collab-Radar ueber
  `IG_ANALYSE_BASE_URL/_MODELL` (vorhandener Schalter).
- Gate: je Job ein Lauf mit Ergebnis im erwarteten Format; Kostenlog zeigt `provider=lokal, eur=0`.
- Verifikation: nach dem naechsten Lauf je Job: `finance/kosten-log.jsonl` auf der NAS, gefiltert auf das Datum
  und `quelle` des Jobs -> erwartet `provider: lokal`, `eur: 0`; Content-Feed-Entwurf enthaelt `HOOK:` und
  `CAPTION:`; Self-Dev legt Antraege mit allen Pflichtfeldern an; Collab-Radar-JSON parsebar.
  Qualitaetsvergleich: 3 Ergebnisse lokal vs. bisher dem CEO vorlegen (Abnahme durch CEO).
- Dry-Run: vorab je Job einen manuellen Lauf auf dem MACO470 gegen Ollama mit Testdaten (schreibt nicht in
  Live-Stores).
- Risiko / Rueckweg: schlechtere Qualitaet oder Zeitueberschreitung -> Fallback greift / Schalter zuruecknehmen
  (`.env`, Neustart). RAM-Konkurrenz um 03:00–03:30 (Backup, Reel) -> beobachten.
- Abhaengig von: Etappe 0 + 1 · Aufwand: klein · Risiko: niedrig
- Freigaben: Etappe, `.env`-Aenderung auf der NAS + Neustart (CEO).

### Etappe 3: Lokal im Chat (BF-05)

- Status: **verifiziert** (2026-09-25) — `LOCAL_LLM_CHAT=zuerst` in der NAS-`.env` (Sicherung
  `.env.bak-20260925-lokal`), Neustart durch den CEO. Telegram-Test: Hinweis 14:09, lokale Antwort 14:10; Kostenlog
  `quelle: chat, provider: lokal, in 13614, out 234, eur 0.0`; keine Chat-Fehler. Die 7-Tage-Beobachtung laeuft
  (Gate). Befund BF-20 (Modellname im Kostenlog geschwaerzt).
- Ziel / Scope: `LOCAL_LLM_CHAT=zuletzt` (Notnagel nach Gemini/OpenAI) **oder** — passend zur CEO-Vorgabe —
  `LOCAL_LLM_CHAT=zuerst` (jede Chat-Nachricht erst lokal, ~1–2 min Antwortzeit, Cloud nur noch bei Ausfall).
  Entscheidung beim Go fuer diese Etappe.
- Gate: Test „Gemini 429 -> lokal antwortet"; 7 Tage Betrieb ohne „alle Anbieter erschoepft".
- Verifikation: Unit-Test mit simuliertem Gemini-Rate-Limit -> Antwort von „lokal"; live 7 Tage:
  `aktivitaet/log.jsonl` und Chat-Antworten ohne „alle Anbieter erschoepft" (gefiltert auf den Zeitraum);
  jeder Einsatz sichtbar im Kostenlog als `provider=lokal`.
- Dry-Run: Chat-Anfrage mit abgeschaltetem Gemini-Key in einer Test-Instanz auf dem MACO470 (nicht Produktion).
- Risiko / Rueckweg: sehr langsame Antworten statt Fehlermeldung -> LUNA kuendigt „lokales Modell, dauert
  etwas" an; Schalter zuruecknehmen.
- Abhaengig von: Etappe 1 (+0) · Aufwand: klein · Risiko: niedrig
- Freigaben: Etappe, `.env` + Neustart (CEO). Danach BF-05 -> Archiv.

### Etappe 3b: Kontext-Management — LUNA fuehlt sich an wie ein normaler Chatbot (CEO-Go 2026-09-25)

- Status: in Umsetzung
- Ziel: Kein `/reset` mehr noetig, lange Unterhaltungen bleiben lokal. Die Unterhaltung wird nie „beendet",
  sondern das Kontextbudget im Hintergrund verwaltet (wie bei ChatGPT/Claude). Keine LLM-Erkennung von
  Gespraechsenden (kostet je Nachricht einen zusaetzlichen lokalen Aufruf und ist unzuverlaessig).
- Analyse (gemessen 2026-09-25): Modell kann 262.144 Token; KV-Cache ~96 KB je Token (16.384 -> +1,2 GB gemessen);
  Windows 29,6 GB, mit geladenem Modell 5,5 GB frei; WSL darf ohne Grenze bis 14 GB (Cutter-Worker). Fester Anteil
  je Aufruf ~13.600 Token (davon ~12.000 Werkzeug-Beschreibungen); der Verlauf waechst v. a. durch Werkzeug-Ergebnisse.
- Baustein 1 (CEO, Windows): `OLLAMA_CONTEXT_LENGTH=32768`, dazu `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0`
  (KV-Cache halb so gross -> 32.768 Token etwa zum RAM-Preis von heute 16.384; ob die Radeon-iGPU das unterstuetzt,
  zeigt die Messung — sonst ignoriert Ollama es, 32.768 bleibt auch ohne gefahrlos: ~3,9 GB frei).
  Spaeter, zuletzt (unterbricht WSL): `.wslconfig` `memory=8GB`.
- Baustein 1 Ergebnis (2026-09-25 14:22): gesetzt vom CEO; **KV-Cache-Kompression greift** — Modell mit 32.768 Token
  braucht 20,5 GB (vorher 20,4 GB bei 16.384); volle Werkzeugliste 11.837 Token, richtiges Werkzeug. Verfuegbar mit
  geladenem Modell: **7,2 GB** (vorher 5,5 GB). Stolperstein BF-21: verwaister `llama-server.exe` vom alten Ollama
  hielt 20,7 GB -> beendet.
- Baustein 2 (Code): Verlauf automatisch verdichten, bevor das Fenster voll ist — alte Werkzeug-Ergebnisse durch
  Kurzfassungen ersetzen, bei Bedarf die aeltesten Wechsel gleitend entfernen; kein zusaetzlicher LLM-Aufruf.
- Baustein 3 (Code): Nach einer Pause (Standard 2 h) neue Sitzung mit kurzer Notiz zur letzten Unterhaltung.
- Probelauf 2026-09-25 (MACO470, Test-Ablagen, 8 CEO-Nachrichten, 12 Modellaufrufe): **11 von 12 lokal**, 1 Aufruf
  lief in das 300-s-Zeitlimit (Denkschleife) -> Gemini uebernahm nahtlos; Kuerzungsschutz **nie** ausgeloest;
  Prompt max. 15.739 Token von 32.768; Verlauf nach 8 Nachrichten ~1.800 Token (Budget 11.668) -> Verdichten war noch
  nicht noetig. Antworten inhaltlich korrekt (15 Antraege, Verteilung, Budget 100 EUR, Zusammenfassung). Dauer je
  Nachricht 36-135 s, einmal 220 s. Auffaellig: LUNA siezt lokal gelegentlich („Ihnen").
- Gate: Tests gruen; Messung Speicherbedarf bei 32.768; Probelauf mit langer Unterhaltung (>= 8 Nachrichten mit
  Werkzeugen) bleibt vollstaendig lokal, kein Kuerzungsschutz-Treffer.
- Verifikation: `/api/ps` -> `context_length` 32768 und Groesse notiert; Probelauf-Protokoll: jede Antwort
  `provider=lokal`; live in Telegram: Kostenlog ueber einen Tag nur `provider: lokal` fuer `quelle: chat`.
- Risiko / Rueckweg: RAM-Konkurrenz mit Schnittjobs -> WSL-Grenze; Verdichtung verliert Details alter
  Werkzeug-Ergebnisse (LUNA kann sie erneut abrufen) -> Schalter/Budget per `.env`; `git revert`.
- Freigaben: CEO-Go fuer 3b erteilt; Merge, Deploy, Neustart und `.wslconfig` je eigenes Go.

### Etappe 4 (optional, CEO-Tor): nicht-denkende Modellvariante

- Status: geplant
- Ziel / Scope: `qwen3:30b-a3b-instruct-2507` (gleiche Groesse, ohne Denkschritte) laden und mit denselben
  Messungen benchmarken. Erwartung (nicht gemessen): Tool-Wahl in wenigen Sekunden statt 25–55 s. Wenn ja:
  Grundlage fuer die spaetere Entscheidung „lokal als Chat-Hauptmodell".
- Gate: Tool-Wahl 3/3 richtig, Chat-Zug < 15 s.
- Verifikation: dieselben 3 Fragen mit voller Werkzeugliste wie in der Analyse -> erwartet 3/3 richtige
  Werkzeuge, Zeiten notiert.
- Risiko / Rueckweg: ~18 GB Download und Plattenplatz; Modell wieder entfernen (Loeschen = CEO-Tor).
- Abhaengig von: Etappe 0 · Aufwand: klein · Risiko: niedrig
- Freigaben: **CEO-Tor „neues Modell"** (kostenlos, aber neues Modell laut `AGENTS.md` 5.4).

## Reihenfolge

0 und 1 parallel moeglich (0 = CEO am Windows-Rechner, 1 = Code). 2 braucht 0+1, 3 braucht 1 (sinnvoll nach 2),
4 ist unabhaengig und optional.

## Kosten (CFO-Kostenvoranschlag, grob)

Einmalig 0 EUR (Ollama und Modelle vorhanden, Etappe 4 ebenfalls kostenlos). Laufend: Strom des MACO470 unter
Last (Groessenordnung einige EUR/Monat, nicht gemessen). Einsparung: Cloud-Tokens der Hintergrund-Jobs und
Fallback-Aufrufe (Hoehe aus `finance/kosten-log.jsonl` in Etappe 2 messen). Budget laut `finance/budget.md`
unberuehrt.

## Dokumentationspflichten

`projekt_changelog.md` (jede Etappe), Etappen-Status + `Naechster Schritt` hier, `docs/datenfluesse.md` (Ollama als
Dienst, LAN-Weg NAS -> MACO470), `docs/bekannte-fehler.md` (BF-05 -> Archiv nach Etappe 3; neue Stolperfalle
„Kontextfenster am Server"), `docs/entscheidungs-register.md` (Modellwahl, Firewall), `governance/zugriffs-policy.md`
(CISO: Ollama-Zugriff), `docs/maco470-roadmap.md` (M6-Status), `ROADMAP.md`.

## Definition of Done

Etappen 0–3 `verifiziert`: Hintergrund-Jobs laufen lokal mit 0 EUR, Chat faellt bei Cloud-Ausfall auf lokal statt
auf eine Fehlermeldung, Ollama nur fuer NAS/WSL erreichbar, BF-05 im Archiv, M6 in `docs/maco470-roadmap.md` auf
„erledigt". Etappe 4 ist optional. Abnahme durch den CEO.
