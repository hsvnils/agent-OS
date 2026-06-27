# Cutter Agent — automatischer Instagram-Reel-Schnitt (lokal, kostenlos)

Uebergib einen **Ordner mit Clips** und bekommst ein fertiges **9:16-Reel** (1080x1920) — vollautomatisch,
ohne externe Dienste. Laeuft lokal auf dem Mac. **Posten bleibt CEO-Tor** (der Cutter erzeugt nur die Datei).

## Was er macht

- Pro Clip wird erkannt, ob **Sprache** enthalten ist (lokales Whisper).
  - **Sprech-Clip:** Stille am Rand wird getrimmt, Untertitel werden erzeugt.
  - **B-Roll:** ein praegnanter Ausschnitt, Ton leise (Musik kommst du in Instagram dazu).
- Alles wird auf **9:16** gebracht (scharfes Bild zentriert, unscharfer Hintergrund — Reel-Look),
  Lautheit normalisiert, sauber zusammengeschnitten.
- **Gemini** (gratis) ordnet die Clips zu einer stimmigen Reihenfolge (Hook zuerst).

## Voraussetzungen

| Werkzeug | Zweck | Status |
|---|---|---|
| **ffmpeg/ffprobe** | Schnitt/Format/Export | vorhanden (brew) |
| **whisper.cpp** + Modell (`~/whisper-models/ggml-*.bin`) | lokale Transkription | installiert (Modell `base`; `small` ist fuer Deutsch besser) |
| **GEMINI_API_KEY** (in `orchestrator/.env`) | KI-Reihenfolge | vorhanden |

> **Untertitel einbrennen** braucht ein ffmpeg **mit libass**. Das aktuelle Build hat das nicht — daher wird
> der Text als **`.srt`-Datei** neben das Reel gelegt (in Instagram die Auto-Captions nutzen oder die .srt
> importieren). Mit einem libass-ffmpeg werden die Untertitel direkt ins Bild gebrannt.

## Bedienung

**Einmal-Lauf:**
```bash
cd /Users/nilskrueger/Documents/KI-Unternehmen
source .venv/bin/activate
python -m cutter /Pfad/zum/Clip-Ordner            # -> <ordner>/<name>_reel.mp4
python -m cutter <ordner> --dauer 30 --ohne-gemini # Optionen
```

**Unbeaufsichtigt (Mac anlassen, Clips reinlegen — fertig):**
```bash
python -m cutter.watch        # Inbox ~/CutterInbox  ->  Outbox ~/CutterOutbox
```
Lege deine Clips in einen **Unterordner** von `~/CutterInbox` (z. B. `~/CutterInbox/reel_montag/`).
Sobald dort ~30 s nichts Neues mehr dazukommt, wird automatisch geschnitten; das Reel landet in
`~/CutterOutbox/`. Du musst nicht am Rechner sitzen.

**Automatisch beim Mac-Start (eingerichtet):** Ein `launchd`-Dienst startet den Watcher bei jedem Login.
```bash
cp cutter/com.hanserautisch.cutter.watch.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hanserautisch.cutter.watch.plist
launchctl list | grep cutter            # laeuft?
tail -f ~/Library/Logs/cutter-watch.log # Live-Log
# Stoppen: launchctl bootout gui/$(id -u)/com.hanserautisch.cutter.watch
```

**Telegram-Meldung (V2):** Ist ein Reel fertig, schickt der Watcher es **als Video an deinen LUNA-Chat**
(gleiches Bot-Token, `TELEGRAM_*` aus `orchestrator/.env`). Du bekommst das Ergebnis aufs Handy, ohne am
Rechner zu sitzen. Senden an dich selbst ist kein CEO-Tor; Instagram-Posten machst du weiter manuell.

## Grenzen (ehrlich)

- **Sprech-Content** (Talking-Head/Vlog): sehr gutes automatisches Ergebnis.
- **Reine B-Roll/Montage:** solider Auto-Schnitt, aber „echtes Profi-Niveau" ist mit keiner Technik
  vollautomatisch garantiert. Qualitaet wird iterativ getunt.
- Musik kommt bewusst **nicht** automatisch dazu (Lizenz/Copyright) — in Instagram beim Posten hinzufuegen.
