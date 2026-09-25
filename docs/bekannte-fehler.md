# Bekannte Fehler, Stolperfallen und Lehren

- Status: lebend
- Stand: 2026-09-25
- Hinweis: Vor jeder Fehlersuche hier nachsehen (`AGENTS.md` 6). Neue Funde kommen mit Symptom, Ursache,
  Umgehung/Fix und Status hierher; erledigte bleiben im Archiv stehen (Suche nach Symptom!). Quellen:
  `CL` = `projekt_changelog.md` (Zeilen Stand 2026-09-25), Commit-SHAs, `docs/maco470-roadmap.md` (`MR`).

## Test-Baseline (Massstab fuer das Test-Gate)

Stand 2026-09-25 auf dem MACO470 (`.venv`, `python -m pytest`), nach Etappe 1 der `BETRIEBSLUECKEN_ROADMAP.md`:

| Suite | Ergebnis | Erwartet rot / uebersprungen |
|---|---|---|
| `orchestrator/tests` | 723 bestanden, 0 rot, 4 uebersprungen | uebersprungen: Phase 17 „plan() erfordert macOS" (BF-01 behoben 2026-09-25) |
| `cutter/tests` | 74 bestanden | – |

Regel: **Kein neuer roter Test.** Wer die Baseline aendert (Test repariert oder bewusst rot), schreibt diese
Tabelle fort.

## Offen

| ID | Symptom | Ursache | Umgehung / naechster Schritt | Seit |
|---|---|---|---|---|
| BF-19 | Web-Chat ueber `https://os.hanserautisch.synology.me` bricht ab, wenn die Antwort lokal erzeugt wird (erwartet, noch nicht beobachtet) | Synology-Reverse-Proxy beendet Anfragen standardmaessig nach 60 s; lokale Antworten brauchen 30-140 s | Umgehung: im LAN direkt `http://192.168.178.129:8765` oder Telegram. Fix (CEO, DSM): Reverse-Proxy-Regel -> Erweiterte Einstellungen -> Timeout auf 300 s | 2026-09-25 |
| BF-20 | Im Kostenlog steht beim lokalen Modell `modell: [REDACTED]` statt `qwen3:30b-a3b` | Leck-Schutz schwaerzt JEDEN `.env`-Wert ab 12 Zeichen (ohne `@`, nicht rein numerisch) als Geheimnis — auch Konfiguration wie `LOCAL_LLM_MODEL` | Kosten (0 EUR) und `provider: lokal` stimmen; nur die Statistik je Modell ist unscharf. Fix-Idee: nur Werte von Schluesseln mit KEY/TOKEN/SECRET/PASSWORD o. ae. als Geheimnis behandeln (eigene Freigabe) | 2026-09-25 |
| BF-21 | Nach „Quit Ollama" + Neustart ist der Windows-Speicher voll (0,2 GB frei, starke Auslagerung) | „Quit Ollama" beendet den Modell-Prozess `llama-server.exe` nicht; er bleibt verwaist (Eltern-Prozess weg) mit ~20 GB stehen, das neue Ollama laedt das Modell ein zweites Mal | Nach jedem Ollama-Neustart pruefen: `llama-server.exe` ohne lebenden Eltern-Prozess beenden (2026-09-25: PID 27788 beendet -> verfuegbar 7,2 GB). Dauerhafter Fix offen (z. B. Pruefung im Gesundheits-Check oder Neustart-Skript) | 2026-09-25 |
| BF-02 | Nach einem Neustart des MACO470 ohne Anmeldung startet nichts (Worker, Backup-Timer) | Windows-Aufgabe „Nur interaktiv", `AutoAdminLogon=0` | „Unabhaengig von der Anmeldung ausfuehren" oder Auto-Login — **CEO-Aufgabe** (Passwort) | 2026-08-17, MR |
| BF-05 | Intermittierend „alle Anbieter erschoepft" | Gemini-Gratis-Rate-Limit unter Last | zurueckgestellt; lokales LLM (M6) soll es loesen | 2026-07-08, CL:699 |
| BF-06 | Instagram liefert nicht alle Threads; eine Marken-DM kam nie an | `me/conversations` nur mit `limit=1` stabil; Webhook-Zustellung ungeklaert | Thread fuer Thread blaettern (`0b87833`); Meta-Grenze bleibt; Thema vom CEO abgehakt | 2026-07, CL:892, 981 |
| BF-09 | Uhrzeiten in Changelog-Koepfen stimmen nicht mit den Commits ueberein (z. B. Eintrag „10:25", Commit `466dcff` um 09:38) | Zeit geschaetzt statt abgelesen | Reihenfolge der Eintraege ist massgeblich und stimmt; alte Eintraege werden nicht umgeschrieben. Kuenftig Zeit per `date '+%Y-%m-%d %H:%M'` holen. | 2026-09-25 |
| BF-10 | `docs/maco470-roadmap.md` Zeile 101 nennt noch „drvfs" | Text vor E6 geschrieben | Tatsaechlich CIFS (`findmnt /mnt/nas-clips`, E6). Bei naechster Aenderung der Datei korrigieren. | 2026-09-25 |
| BF-11 | Einbrennen von Untertiteln und Verwacklungsmessung nicht moeglich | ffmpeg-Build ohne `libass` bzw. `vidstabdetect` | Einschraenkung; Untertitel sind ohnehin standardmaessig aus | CL:3350, 466 |
| BF-12 | Noch nicht verifiziert: Umlaute NFC/NFD ueber CIFS, Body-Limit des Reverse-Proxys fuer grosse Reels, OUTBOX muss lokal liegen | – | beim naechsten Auftreten pruefen | MR:259-265 |

## Umgehung aktiv

| ID | Symptom | Ursache | Umgehung | Beleg |
|---|---|---|---|---|
| BF-07 | MACO470-Worker tot, WSL faehrt herunter | WSL2 beendet die VM ohne offene Sitzung (`vmIdleTimeout=-1` reicht nicht) | Windows-Aufgabe `LUNA-WSL-Keepalive` (`sleep infinity`, alle 5 min Selbstheilung) | CL:196-203, MR:42-56 |
| BF-13 | `cmdkey` ueber SSH scheitert, Explorer-Laufwerk ist sitzungsgebunden | Netzwerk-Logon ohne Credential-Store | SMB nativ per CIFS (E6) | CL:222-225 |
| BF-14 | Facebook-Post scheitert trotz neuem Token in der `.env` | Token-Store (`orchestrator/state/instagram_token.json`) hat Vorrang vor dem `.env`-Seed | Store leeren, dann neu seeden | Gedaechtnis „Auto-Reel-Pipeline" |
| BF-15 | Alte Log-Eintraege (vor 2026-06-25) sind kosmetisch verstuemmelt | frueherer `leak_guard` redigierte Flag-Werte wie `'1'` | nur kosmetisch; Fix `e3b06ca` wirkt fuer neue Eintraege | CL:3630 |
| BF-16 | `app-v2.js` komplett lahmgelegt (zweimal) | gerades Anfuehrungszeichen in einem `"..."`-String | vor jedem Deploy `node --check` auf geaenderte JS-Dateien | `216759a`, `215ed41` |
| BF-17 | Ollama ueber die OpenAI-Schnittstelle (`/v1`) waehlt bei LUNAs Werkzeugliste das falsche Werkzeug, ohne Fehler | Server-Kontextfenster 4.096; `/v1` kann es nicht pro Aufruf setzen -> Prompt still auf 2.050 von ~11.800 Token gekuerzt | `OLLAMA_CONTEXT_LENGTH=16384` am Server gesetzt (2026-09-25), Probe: 11.837 Token, richtiges Werkzeug. **Wird die Werkzeugliste deutlich laenger (> ~15.000 Token), Wert erhoehen.** Pruefung: `prompt_tokens` in der Antwort | 2026-09-25 |

## Lehren (Regeln, die aus Fehlern entstanden sind)

- **„Erzeugt" ist nicht „angekommen".** Die Telegram-Zustellung war 5 Wochen tot, obwohl alles „lief"
  (BF-A01). Abnahme immer am Empfaenger; Container-Log ist die Wahrheit (`ssh -t luna-nas` + sudo, CEO).
- **Jeden Regressionstest gegenproben, bis er rot wird.** Der erste Test zum Telegram-Fehler blieb gruen,
  obwohl der Fehler noch drin war (BF-A01c).
- **Ein echter Lauf zaehlt, nicht „Zugang geht".** „SSH + Schreibrecht" wurde als „Deploy bereit" gemeldet,
  der erste echte Lauf scheiterte an GNU tar (BF-A05).
- **Aus indirekten Tests keine Diagnose ableiten.** „Kein 409 bei getUpdates -> Bot laeuft nicht" war falsch.
- **Autostart-Tests nicht vom Fremdgeraet aus.** Jeder Pruefbefehl vom MacBook startete WSL selbst und
  verfaelschte den Test (MR:44).
- **Web-Endpunkte liegen auf der NAS.** Nur auf den MACO470 zu deployen ergibt `404` — immer auch
  `sync-to-nas.sh` + Neustart `luna-os`.
- **Tests nie gegen echte Stores.** Ein Test schrieb echte Zeilen in `investment/log.jsonl` und den Changelog
  (BF-A02).
- **zsh:** kein `#`-Kommentar hinter kopierbaren Befehlen („Unbekanntes Argument: #").
- **NAS-sudo-Sperre** nach Fehlversuchen: NAS-Neustart (DSM) behebt sie. DSM-Container-Manager kann per CLI
  erstellte Container nicht steuern („Container undefined") -> CLI nutzen.
- **fstab:** `x-systemd.automount` erst eintragen, wenn die Credentials-Datei existiert (sonst
  `No such device`; Automount-Unit stoppen, dann mounten) (MR:158).
- **macOS/launchd:** Ziele unter `~/Documents` blockiert TCC -> `~/LUNA-Backups`.

## Archiv (behoben)

| ID | Symptom | Ursache | Fix | Datum / Beleg |
|---|---|---|---|---|
| BF-04 | Backup sicherte nur 10 von ~25 Live-Speichern | Liste in `deploy/backup-from-nas.sh` nicht nachgezogen | 9 append-only Stores ergaenzt (`5a8c44e`); Probelauf 17 Stores, 17/17 zeilengleich mit der NAS; Doku-Check prueft Backup jetzt blockierend. Reel-Videos + Instagram-Token bewusst nicht (CEO). Timer-Lauf 2026-09-26 03:20 noch zu pruefen. | 2026-09-25 |
| BF-08 | `orchestrator/memory/log.jsonl` im oeffentlichen Repo versioniert | vor der `.gitignore`-Regel angelegt (`618c8ae`) | aus dem Index genommen + ignoriert, dazu `nutzung/`, `cutter_ops/`; 2 harmlose Testeintraege bleiben in der Historie (kein Rewrite). **Andere Klone (MacBook): vor `git pull` die lokale Datei sichern** — der Pull loescht sie. | 2026-09-25 |
| BF-01 | 4 rote Tests (`test_watch` 1/2/7, `test_notifications` 4) | festes Mock-Datum `2026-06-01` in `MockGitHubWatch` und `test_watch.py`, seit 2026-07-31 nicht mehr „neu" (`neu_tage=60`) | Datum relativ zu heute (minus 10 Tage); Gegenprobe mit festem Datum: 4 rot (`BETRIEBSLUECKEN_ROADMAP.md` Etappe 1) | 2026-09-25 |
| BF-03 | `deploy/sync-to-nas.sh` schuetzte `crm/`, `content_ops/`, `nutzung/` nicht (eine lokale Kopie haette Live-Daten ueberschrieben) | Schutzliste nicht nachgezogen | Excludes ergaenzt; Probe: 3 Probedateien vorher im Paket, nachher 0 (Etappe 2) | 2026-09-25 |
| BF-18 | Chat (Telegram + Web) antwortete seit Juli nur „technischer Fehler" | Anthropic-Schluessel ungueltig (401), 401 war kein Fallback-Grund, Ausnahme nirgends protokolliert | 401 als Fallback-Grund + Fehlerprotokoll (`0d35a90`) und Chat lokal zuerst; Telegram-Test 2026-09-25 14:09/14:10: Hinweis + lokale Antwort, Kostenlog `provider: lokal`, 0 EUR | 2026-09-25 |
| BF-A01 | Keine proaktiven Telegram-Meldungen, 1106 in der Outbox | `NameError` (`tz`, dann `datetime`) in `main()` von `bot.py`, vom `except` verschluckt | `cff0063`, `f29f6e4`, `5f6f2e2`; alte Meldungen >3 h verwerfen (Lawinenschutz) | 2026-08-17, CL:124-169 |
| BF-A02 | Testlauf schrieb in echte Stores und Changelog | `TestSettingsEndpoint` gegen echte App | Temp-Verzeichnis, Daten bereinigt (`cff0063`) | 2026-08-17, CL:157 |
| BF-A03 | Backup loeschte bei nicht erreichbarer NAS gute Staende, Exit 0 | leerer Lauf rotiert; `ssh` ohne `-n` | kein Rotieren bei leerem/geschrumpftem Lauf, Exit 1 + Telegram (`f3c093f`) | 2026-09-25, CL:23 |
| BF-A04 | `.env`-Sicherung untracked aber nicht ignoriert (Leck-Gefahr ins oeffentliche Repo) | `.gitignore` nur fuer exakt `.env` | alle `.env`-Varianten gesperrt (`2fdcf92`) | 2026-09-25, CL:71 |
| BF-A05 | `sync-to-nas.sh` bricht unter Linux ab | `--no-mac-metadata` nur bei bsdtar | Option abhaengig vom tar-Typ (`2fdcf92`) | 2026-09-25, CL:79 |
| BF-A06 | Commits nie auf GitHub, MACO470 „Already up to date" | Deploy nur per tar | per `sync-to-maco.sh` nachgeholt | 2026-09-24, CL:114 |
| BF-A07 | Naechtliches Reel fiel an 6 Tagen aus, still | Spielordner ohne Video; Fehlschlag nur auf stdout | `nur_mit_video=True` + Telegram bei Fehlschlag (`1968452`) | 2026-08-17, CL:204 |
| BF-A08 | SMB-Fehler 13 | DSM-Konto `maco470` fehlte | Konto angelegt | 2026-08-12, CL:229 |
| BF-A09 | Worker-Passwort kurz/numerisch bei oeffentlichem LUNA-OS | – | starkes Passwort | 2026-08-12, CL:270 |
| BF-A10 | Zugaenge nicht in der Zugriffs-Policy | versaeumt | nachgetragen | CL:212 |
| BF-A11 | `permission denied: deploy/sync-to-nas.sh` | x-Bit fehlte in Git | Mode 100755 (`b5ec027`) | 2026-07-09 |
| BF-A12 | Chat dauerhaft 400 („tool_use ohne tool_result") | Fehler flog aus dem Tool-Loop | tool_result immer anhaengen, Verlauf reparieren (`8235e56`) | 2026-06-25 |
| BF-A13 | Git „dubious ownership", 580 `._*`-Dateien in `.git` | Container als root; macOS-tar-Reste | `safe.directory`, `--no-mac-metadata` (`8235e56`) | 2026-06-25 |
| BF-A14 | Push-Meldungen mehrfach, IDs verstuemmelt | `leak_guard` redigierte Flag-Werte | `is_redactable_secret` (`e3b06ca`) | 2026-06-25 |
| BF-A15 | Chat antwortet nur „technischer Fehler" | Monatslimit als 400 falsch eingeordnet | Fallback-Erkennung + Gemini-Fallback (`316ebd3`) | CL:3466 |
| BF-A16 | „LUNA antwortet nicht" | Execution-CLI als root crashte den Reader | Abbruch vor CLI-Start, Non-root-Container (`bd47bcc`) | 2026-06-26 |
| BF-A17 | Kalendertermin scheitert | `timeZone` fehlte | `ec6c83b` | CL:3656 |
| BF-A18 | Fachagent laeuft in `max turns` | CTO wollte handeln statt beraten | Beratungs-Vorgabe (`0add148`) | 2026-06-24 |
| BF-A19 | Traceback bei „Credit balance too low" | SDK-Fehler ungefangen | `BackendError` | 2026-06-23 |
| BF-A20 | „kostenlos/open-source" loeste Geld-Tor aus | Teilstring „kosten" | `9c5d35e` | – |
| BF-A21 | Gemini 2.0 Flash abgekuendigt | – | `gemini-2.5-flash` (`84663a8`) | – |
| BF-A22 | Sternchen im Telegram-Text | Markdown ohne parse_mode | Filter `fuer_telegram` (`f188a66`) | – |
| BF-A23 | Safari: Dashboard/Menue scrollt nicht, Panel ragt heraus | `min-height:0`-Kette, Safari-Grid | `79bdedd`, `0a5f247`, `d21b944` | CL:2221-2346 |
| BF-A24 | Linie ueber dem Hologramm | `display:flex` ueberschrieb `[hidden]` | `85a8f55` | CL:990 |
| BF-A25 | Grauer Schleier im Hell-Theme | hart kodierte Farben | `97a836b` | CL:1306 |
| BF-A26 | Depot-Tabelle widerspruechlich | Stueck- vs. Gesamtwert | `7bbb408` | CL:607 |
| BF-A27 | Roadmap-Backfill nahm zurueckgesetzte Antraege auf | falsche Statuspruefung | `7c272d4`, Roadmap geleert | CL:656 |
| BF-A28 | Insert `cutter_jobs` HTTP 400 | Namenskollision mit HCC | `luna_cutter_jobs` (`9e71a88`) | CL:2312 |
| BF-A29 | Trend-Status-Upsert 400 | NOT-NULL `title` | PATCH statt Upsert (`786b9c4`) | CL:2457 |
| BF-A30 | Instagram-Webhook blockiert | Basic-Auth griff auch dort | ausgenommen (`99618da`) | – |
| BF-A31 | FMP 403 / Alpha Vantage `full` fehlt | `/stable/`-API; Premium | `c412186`, Fallback `compact` (`6e60020`) | CL:3036 |
| BF-A32 | IG-Backfill 7 min ohne Antwort | viele sequenzielle Meta-Abfragen | Zeit-Budget (`b27a309`) | CL:945 |
| BF-A33 | Qualitaets-Score saettigt; lange Clips zu gut bewertet | an synthetischen Videos geeicht; Normierung | `fa33863`, `514583a` | CL:424-454 |
| BF-A34 | Reel > 50 MB (Telegram-Limit) | 4K-Quellen | Re-Encode < 48 MB (`e40185a`) | CL:3316 |
| BF-A35 | Voice-Serie: 422, 405, falscher JS-Export, fehlende Stimme | diverse | `7cda2d8`, `11f2404`, `39b3c73`, `0d68d9a` | 2026-06-24 |
| BF-A36 | Orb-Absturz, keine hoerbare Antwort, Ziel-Loop bricht ab | TCC/Info.plist, Vollduplex, Prosa statt JSON | `8c1f413`, `abe4f11`, `70b5276` (Mac-MVP, historisch) | CL:708-2850 |
| BF-A37 | Meldungs-Dedup bricht; Reel-Zeitstempel verfaelscht; Feature-Friedhof meldet alles | wechselnde Texte; `liste()`; fehlender Guard | konstante Texte, `zuletzt_eingereicht()`, Fairness-Guard | CL:181, 383 |
