"""Kuratierte deutsche Stimmen (ElevenLabs Voice Library) + Auswahl-Persistenz.

Die Library-Stimmen sind direkt per voice_id nutzbar (kein Hinzufuegen zum Account noetig).
Die Auswahl wird in `selected_voice.json` gespeichert (lokal, gitignored) und beim naechsten
Gespraechsstart von der Pipeline gelesen. Beschreibungstexte sind Oberflaechentexte (Umlaute erlaubt);
voice_id ist ein Protokoll-/Code-Wert (ASCII).
"""
import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "selected_voice.json"

# Kuratierte, natuerlich klingende deutsche Stimmen (Geschlechter-Mix).
GERMAN_VOICES = [
    {"id": "PilDNXo1gkdLmfr2QGeB", "name": "Niklas",
     "beschreibung": "Männlich, professionell und sachlich – kompetenter Assistenten-Ton (Jarvis-Richtung)."},
    {"id": "Og1e3AcgYpEtYfxiG5Mh", "name": "Soufian",
     "beschreibung": "Männlich, deutsche Erzählerstimme – sehr natürlich und ruhig, hohe Aufnahmequalität."},
    {"id": "FHUR0i1dH4dqNNOZj5D0", "name": "Mirko",
     "beschreibung": "Männlich, ruhig und angenehm – entspannt und vertrauenswürdig."},
    {"id": "TFZslfosui5a1tIqcGVC", "name": "Ralf Benz",
     "beschreibung": "Männlich, angenehmer Sprecher – klar und seriös, Dokumentar-Stil."},
    {"id": "jcfbXPVv9bOPpYpBRqjF", "name": "Ken",
     "beschreibung": "Männlich, professionell und ruhig – nüchtern und zuverlässig."},
    {"id": "GZckiELWRyqX481UWTDl", "name": "Hannes",
     "beschreibung": "Männlich, geerdet und ruhig – freundlich, bodenständig."},
    {"id": "9fvtGcIyqtZAfzFcACPJ", "name": "Natalie",
     "beschreibung": "Weiblich, warm und engagiert – freundlich und zugewandt."},
    {"id": "SiMvlSW9cKKHDYT4BzOp", "name": "Lola",
     "beschreibung": "Weiblich, frisch und dynamisch – selbstbewusst und lebendig."},
]

DEFAULT_VOICE_ID = GERMAN_VOICES[0]["id"]
_VALID_IDS = {v["id"] for v in GERMAN_VOICES}


def get_selected_voice_id() -> str:
    try:
        vid = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("voice_id")
        return vid if vid in _VALID_IDS else DEFAULT_VOICE_ID
    except Exception:
        return DEFAULT_VOICE_ID


def set_selected_voice_id(voice_id: str) -> bool:
    """Speichert die Auswahl. Gibt False zurueck bei unbekannter voice_id."""
    if voice_id not in _VALID_IDS:
        return False
    STATE_FILE.write_text(json.dumps({"voice_id": voice_id}), encoding="utf-8")
    return True
