"""Live-Register aller angebundenen KI-Modelle und Dienstleister (CFO-Ueberblick).

Leitet sich live aus den vorhandenen .env-Keys ab. Markiert je Posten: Provider, Zweck, Kostenart und ob
die Nutzung **gemessen** wird (Chat/Fallbacks) oder nur **geschaetzt** (Fachagenten ueber die Claude-CLI,
die keine Token-Zahl liefert). Reine Anzeige -- keine Kosten.
"""
from __future__ import annotations


def register(secrets: dict | None = None) -> dict:
    s = secrets or {}

    def has(k):
        return bool(s.get(k))

    modelle = [
        {"name": "Chat (LUNA)", "modell": "claude-haiku-4-5", "provider": "anthropic",
         "fallback": "gemini-2.5-flash -> gpt-4o-mini", "zweck": "Telegram-Dialog",
         "kosten": "per Token", "erfassung": "gemessen"},
        {"name": "Fachagenten (CTO/Berater/...)", "modell": "claude-opus-4-8", "provider": "anthropic (CLI/Abo)",
         "fallback": "-", "zweck": "Konsultation, Innovation, Self-Dev", "kosten": "Abo/per Token",
         "erfassung": "geschaetzt (CLI liefert keine Tokenzahl)"},
        {"name": "Web-Recherche-Eskalation", "modell": "claude-sonnet-4-6", "provider": "anthropic-web",
         "fallback": "Brave", "zweck": "komplexe Recherche", "kosten": "billbar",
         "erfassung": "nicht instrumentiert"},
    ]
    dienste = [
        {"name": "Anthropic API", "aktiv": has("ANTHROPIC_API_KEY"), "kategorie": "LLM",
         "kosten": "per Token -- Limit bis 2026-07-01"},
        {"name": "Gemini (Fallback)", "aktiv": has("GEMINI_API_KEY"), "kategorie": "LLM",
         "kosten": "GRATIS-Tier (aktiver Chat-Provider)"},
        {"name": "OpenAI (Fallback)", "aktiv": has("OPENAI_API_KEY"), "kategorie": "LLM",
         "kosten": "per Token -- aktuell ohne Guthaben"},
        {"name": "Brave Search", "aktiv": has("BRAVE_API_KEY"), "kategorie": "Recherche",
         "kosten": "Gratis-Kontingent"},
        {"name": "Google Workspace", "aktiv": has("GOOGLE_OAUTH_REFRESH_TOKEN"), "kategorie": "Office",
         "kosten": "gratis"},
        {"name": "GitHub", "aktiv": has("GITHUB_TOKEN"), "kategorie": "Code", "kosten": "gratis"},
        {"name": "Deepgram (Voice STT)", "aktiv": has("DEEPGRAM_API_KEY"), "kategorie": "Voice",
         "kosten": "paid -- nur Voice-Kanal (am Mac)"},
        {"name": "ElevenLabs (Voice TTS)", "aktiv": has("ELEVENLABS_API_KEY"), "kategorie": "Voice",
         "kosten": "paid -- nur Voice-Kanal (am Mac)"},
        {"name": "AgentOps", "aktiv": has("AGENTOPS_API_KEY"), "kategorie": "Observability",
         "kosten": "optional"},
    ]
    return {"modelle": modelle, "dienste": [d for d in dienste]}
