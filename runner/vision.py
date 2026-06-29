"""Bildschirm sehen (Phase 17, M5/#3) — LUNA „liest" einen Screenshot via multimodalem Modell.

Gratis ueber Gemini (Vision, OpenAI-kompatibel); Fallback OpenAI. Kein Anthropic noetig. Der Screenshot
kommt vom Orb (.app mit Screen-Recording-Recht) — serverseitiges `screencapture` ist TCC-blockiert.
"""
from __future__ import annotations

import base64
import os

_PROMPT = ("Du bist LUNAs Augen am Mac. Beschreibe praegnant und konkret, was auf diesem Bildschirm bzw. in "
           "dieser App zu sehen ist: welche App/welches Fenster, der Hauptinhalt und die wichtigsten sichtbaren "
           "Bedienelemente (Knoepfe, Felder, Menue). Antworte knapp auf Deutsch.")


def bild_lesen(image_bytes: bytes, frage: str = "") -> dict:
    """Schickt das Bild an ein Vision-Modell. {ok, text} oder {ok:False, grund}."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "grund": "Kein Vision-Modell konfiguriert (GEMINI_API_KEY/OPENAI_API_KEY)."}
    if not image_bytes:
        return {"ok": False, "grund": "Leeres Bild."}
    try:
        import openai

        from orchestrator.core.model_router import GEMINI_BASE_URL
        base = GEMINI_BASE_URL if os.environ.get("GEMINI_API_KEY") else None
        model = "gemini-2.5-flash" if base else "gpt-4o-mini"
        client = openai.OpenAI(api_key=key, base_url=base)
        b64 = base64.b64encode(image_bytes).decode()
        prompt = (frage or "").strip() or _PROMPT
        r = client.chat.completions.create(model=model, messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }])
        text = (r.choices[0].message.content or "").strip()[:1800]
        from orchestrator.governance.leak_guard import is_redactable_secret, redact
        sec = [v for v in os.environ.values() if is_redactable_secret(v)]
        return {"ok": True, "text": redact(text, sec)}
    except Exception as exc:
        return {"ok": False, "grund": str(exc)[:200]}
