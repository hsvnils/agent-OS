"""Live-Voice-Kanal (Browser, WebRTC lokal) auf Basis von Pipecat.

Schichten:
- `bridge.py`  -- framework-unabhaengige Andockstelle Sprache<->HoA-Kern (offline testbar).
- `panels.py`  -- show_panel: UI-Anweisungen (Kostenuebersicht aus finance/ etc.), leck-geschuetzt.
- `pipeline.py`-- Pipecat-Pipeline (STT -> Bruecke -> TTS, WebRTC). Laufzeit, erst am GATE aktiv.
- `server.py`  -- Einstieg: WebRTC-Server + statische Browser-Seite.

Der HoA-Kern bleibt das Gehirn; diese Schicht ist nur Ein-/Ausgabe.
"""
