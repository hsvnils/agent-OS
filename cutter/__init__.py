"""Cutter Agent -- lokaler, kostenloser Auto-Schnitt: Ordner mit Clips -> Instagram-Reel (9:16).

Laeuft auf dem Mac (FFmpeg + lokales Whisper + Gemini). Posten bleibt CEO-Tor.
"""
from .pipeline import schneide_ordner

__all__ = ["schneide_ordner"]
