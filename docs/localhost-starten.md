# Localhost starten — Live-Voice-Oberflaeche (Head of Agents)

Kurzanleitung, um die Sprach-Oberflaeche lokal im Browser zu starten.

## Voraussetzungen (einmalig)

- Python-Umgebung ist eingerichtet (`.venv` im Projektordner).
- Voice-Abhaengigkeiten installiert (siehe `orchestrator/channels/voice/requirements.txt`):
  ```sh
  pip install "pipecat-ai[webrtc,deepgram,silero,elevenlabs,anthropic]" fastapi uvicorn
  ```
- Keys liegen in `orchestrator/.env` (`ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`).

## Starten

Im Projektordner (`/Users/nilskrueger/Documents/KI-Unternehmen`):

```sh
source .venv/bin/activate
export PATH="$HOME/.npm-global/bin:$PATH"      # Claude CLI im PATH (fuer den Live-Pfad)
python -m orchestrator.channels.voice.server
```

Dann im Browser oeffnen: **http://localhost:7860**

Auf der Seite: links **„Gespraech starten"** klicken, Mikrofon erlauben, einfach lossprechen
(Barge-in aktiv — du kannst dem Head of Agents ins Wort fallen). Stimme oben links im Dropdown waehlbar.

## Beenden

Im Terminal **Strg + C**. Wichtig: es sollte **genau ein** Server-Prozess laufen.
Pruefen / hart beenden, falls noetig:

```sh
lsof -ti :7860 | xargs -r kill -9
```

## Hinweise

- Laeuft alles lokal ueber WebRTC (kein kostenpflichtiger Transport); STT/TTS und die HoA-Antworten
  verursachen echte API-Kosten.
- **Terminal statt Browser** (Text-Orchestrator, ohne Sprache): `python -m orchestrator.run`.
- **Offline-Self-Checks** (ohne Kosten): `python -m unittest discover -s orchestrator/tests -t .`
