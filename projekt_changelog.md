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
