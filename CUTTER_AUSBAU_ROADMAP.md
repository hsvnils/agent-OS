# Roadmap: Cutter-Ausbau (Schnittwissen ins echte Video)
- Status: in Umsetzung
- Stand: 2026-11-09
- Arbeitsbranch: `ai/plan-cutter-ausbau` (Plan); Umsetzung je Etappe auf eigenem `ai/`-Branch
- Basiscommit: `ea47a7b`
- Naechster Schritt: C2 ist gemergt (Standard bleibt `v1`). Offen: CEO-Sichtprobe zur Verzerrung (BF-94) und Wahl der Variante; C1-Nachweis im Nachtlauf.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-11-09)

„Ich will, dass wir unsere Cutter Kuenste aufstocken.“ Der Skill `davinci-resolve-schnitt` liefert das Wissen; diese Roadmap
bringt es in die Videos, die der Cutter wirklich erzeugt. CEO-Angabe: Auf dem MACO470 laeuft die **kostenlose** Resolve-Version.

## Analyse (read-only, 2026-11-09)

Nachweise:
- Resolve Free: externe Skriptsteuerung und MCP-Server sind Studio-only (lokales Scripting-README, Handbuch S.4318). Eine automatische
  Steuerung von Resolve scheidet damit aus. Keyframes auf Edit-Clips kann auch die Studio-API nicht setzen.
- ffmpeg 6.1.1 auf dem MACO470 hat `zoompan`, `xfade`, `sidechaincompress`, `loudnorm`, `vidstabdetect`, `vidstabtransform`, `minterpolate`,
  `rubberband`, `deesser`, `afftdn`, `lut3d`, `ass` (Befehl `ffmpeg -filters`). Der Grossteil der Techniken geht also ohne Resolve und kostenlos.
- Der Cutter widerspricht heute dem Skill:

| Stelle | Heute | Laut Skill |
|---|---|---|
| `cutter/ffmpeg_ops.py:25` | Zoom linear (`zoom+0.0008`) auf B-Roll | Nie linear, S-Kurve |
| `cutter/pipeline.py:116`, `ffmpeg_ops.py:176` | Crossfade 0,35 s zwischen allen Clips | Harter Schnitt ist Standard |
| `ffmpeg_ops.py:19` | Ein fester Grade fuer alles | Grundkorrektur je Clip, dann Look |
| `ffmpeg_ops.py:186,213,234` | `loudnorm` einstufig auf -16 LUFS, 44,1 kHz | Um -14 LUFS, -1 dBTP, 48 kHz |
| `reel_daily.py`, `worker.py` | Keine Kontrolle des fertigen Videos | Am Ergebnis pruefen |

Umfang: `cutter/` hat 2455 Zeilen Python und eigene Tests unter `cutter/tests`.

## Scope

Schnittplan-Format, Qualitaetskontrolle, neue ffmpeg-Bewegungen und Tonkette, FCPXML-Ausgabe zum Nacharbeiten von Hand in Resolve Free.

## Nicht-Scope (nur mit eigener CEO-Freigabe)

- Kauf von Resolve Studio; automatisches Posten (CEO-Tor Oeffentlichkeit); Import fremder Skills (CEO-Regel 2026-10-16).
- Aushebeln der Skript-Sperre der Free-Version ueber In-App-Bruecken (Lua, Scripts-Menue) und UI-Automation.
- Standard fuer Untertitel: bleibt AUS (CEO-Wunsch), solange der CEO nichts anderes sagt. Musikauswahl: bleibt beim CEO.
- Schutzbereiche nach `governance/roadmap-workflow.md` B4: `.env`, Telegram-Bot, Live-Daten, NAS-Clip-Archiv, Zeitplaene.

## Etappen

Reihenfolge: C1 zuerst, weil sie jede weitere Etappe messbar macht. C2 vor C3. C4, C5 und C6 sind unabhaengig. Alles, was das Bild aendert, haengt am Schalter
`CUTTER_STIL` (`v1` = heute, `v2` = neu), Standard bleibt `v1` bis zur CEO-Abnahme. Rueckweg jeweils: Schalter auf `v1`.

### Etappe C1: Kontrolle am fertigen Video (deployt 2026-11-09)
- **Ziel:** Nach jedem Render prueft der Cutter das Ergebnis selbst: Masse, fps, Tonspur, Dauer, Lautheit und True Peak (`ebur128`), Schwarzbild, Standbild, lange Stille.
- **Wirkung:** Schlechte Reels gehen nicht zur Freigabe, sondern werden mit Grund gemeldet. Erst nur messen und melden, Sperren erst nach CEO-Freigabe.
- **Gate:** Tests mit erzeugten Fehlvideos (schwarz, stumm, falsches Format) werden rot erkannt, gesundes Video gruen; Gegenprobe.
- **Pruefung:** Lauf auf Probeclips, Bericht zeigt erwartete Werte; nach Deploy der naechste echte Job mit Bericht im Log.
- **Stand 2026-11-09:** `cutter/qualitaet.py`, eingebunden in `pipeline.py`, `reel_daily.py`, `worker.py`; sechs echte Reels nachgemessen (je ca. 2 s). Reine B-Roll-Reels sind absichtlich leise, dort wird der Tonpegel nicht bewertet.
- **Befund:** siehe BF-92.

### Etappe C2: Schnitt-Grundlagen (gemergt, Stil v2 aus, Sichtabnahme offen)
- **Vorab CEO-Entscheidung:** Der CEO hat am 2026-06-27 „immer Ueberblenden als fester Effekt“ vorgegeben; der harte Schnitt als Standard weicht davon ab. Nur nach ausdruecklicher Aenderung, sonst bleibt Ueberblenden.
- **Ziel:** Harter Schnitt als Standard, Push-in mit S-Kurve statt linear, Schnitt auf Wortgrenzen und Stille, staerkster Moment nach vorne, 48 kHz, Lautheit zweistufig auf -14 LUFS / -1 dBTP.
- **Gate:** Tests gruen; dasselbe Spiel als `v1` und `v2` nebeneinander, **CEO-Sichtabnahme am iPhone**.
- **Pruefung:** ffprobe und C1-Bericht je Variante; ein Vergleichspaar liegt dem CEO vor.
- **Stand 2026-11-09:** Schalter `CUTTER_STIL` (Standard `v1`) und `CUTTER_UEBERGANG` (Standard `weich`, CEO-Vorgabe 2026-06-27). v2: S-Kurve, `fps` vor `zoompan` (BF-93), Tonblende am harten Schnitt, 48 kHz, Lautheit zweistufig -14 LUFS (B-Roll -24 LUFS, Startwert), Sprech-Clips enden an Satzgrenze oder Pause, lauteste Stelle als Ausschnitt, staerkster Clip vorn. Drei Varianten aus HSV gegen BMG gerendert, C1-Bericht ohne Befund.

### Etappe C3: Bewegung aus dem Schnittplan (geplant, gross, Risiko mittel)
- **Ziel:** JSON-Schnittplan je Reel (Clip, Zeiten, Bewegung, Uebergang). Bausteine: Punch-in-Stufen 100/110/120 %, Speed Ramp, Freeze, kurzer Impact-Shake, Whip- und Zoom-Uebergang, Dosierregel „hoechstens eine Hauptbewegung“. Regeln und Grenzen aus dem Skill, Zoom nur innerhalb der Pixelreserve.
- **Gate:** Tests rechnen Kurven nach (Anfang, Ende, keine Spruenge); Plan ohne gueltige Reserve wird abgelehnt; CEO-Sichtabnahme.

### Etappe C4: Ton (geplant, mittel, Risiko niedrig)
- **Ziel:** Dialog-Kette in ffmpeg (Hochpass, Rauschminderung, De-Esser, Kompressor), Ducking per `sidechaincompress`, Stadion-Atmo nach Aktion. Eigene Musik nur, wenn der CEO sie liefert.
- **Gate:** Messwerte im C1-Bericht im Ziel, CEO hoert Vergleichspaar am Handy.

### Etappe C5: Clip-Beschreibungen als Text (geplant, mittel; eigene Freigabe)
- **Ziel:** Textbeschreibung mit Zeitmarken je Clip im Clip-Archiv (eigene Umsetzung der Idee), damit Auswahl und Hook-Suche Clips nicht neu ansehen muessen. Verzahnt mit M4e/M5 in `docs/maco470-roadmap.md`.
- **Offen:** Beschreibung lokal oder mit Gemini; Gemini-Stufe ist CEO-Tor. Vor Umsetzung Entscheidung einholen.

### Etappe C6: Uebergabe an Resolve Free (geplant, klein, Ausgang offen)
- **Ziel:** Cutter schreibt zum Reel eine FCPXML-Datei, die der CEO per `File > Import > Timeline` zum Nacharbeiten oeffnet.
- **Probe zuerst:** Ob Keyframes und Uebergaenge beim Import ankommen, ist nicht dokumentiert. Eine Testdatei entscheidet, was gebaut wird.
- **Gate:** CEO importiert die Probe in Resolve Free; Schnitte und Zeiten stimmen. Scheitert das Wesentliche, faellt die Etappe weg; erst dann waere ein Kostenvoranschlag fuer Studio (CFO) sinnvoll.

## Dokumentationspflicht

`projekt_changelog.md` immer; Etappen-Status hier; `ROADMAP.md`; `docs/entscheidungs-register.md`; `docs/bekannte-fehler.md`; `docs/datenfluesse.md` bei neuen Dateien oder Verbindungen; `cutter/README.md`. Deploy auf den MACO470 per `deploy/sync-to-maco.sh`, Neustart `cutter-worker` je mit eigener Freigabe.

## Definition of Done

C1 bis C4 verifiziert und `CUTTER_STIL=v2` nach CEO-Abnahme Standard; C5 und C6 entschieden (gebaut oder begruendet verworfen). Der CEO nimmt ab.
