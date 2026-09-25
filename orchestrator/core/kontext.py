"""Kontext-Management fuer den Chat (LOKALES_LLM_ROADMAP.md, Etappe 3b) -- ohne zusaetzlichen LLM-Aufruf.

Ziel (CEO 2026-09-25): LUNA soll sich in Telegram wie ein normaler Chatbot anfuehlen -- kein `/reset`, lange
Unterhaltungen bleiben beim lokalen Modell. Die Unterhaltung wird nie „beendet"; stattdessen:

1. **Verdichten**, bevor das Kontextfenster voll ist: alte Werkzeug-Ergebnisse (der groesste Posten im Verlauf)
   werden gekuerzt; reicht das nicht, fallen die aeltesten Wechsel gleitend heraus. Der laufende Wechsel bleibt
   immer vollstaendig (tool_use/tool_result-Paare duerfen nie auseinanderreissen).
2. **Pause** statt Themenerkennung: nach laengerer Stille beginnt eine neue Sitzung mit einer kurzen Notiz zur
   letzten Unterhaltung („wie gesagt ..." funktioniert weiter, ohne den alten Ballast).

Ein „Wechsel" beginnt mit einer echten Nutzer-Nachricht (role=user, Text) und umfasst alle folgenden
Modell-Antworten, Werkzeug-Aufrufe und -Ergebnisse bis zur naechsten Nutzer-Nachricht.
"""
from __future__ import annotations

from .lokal_llm import geschaetzte_tokens
from .model_router import btext, btype

KURZ_ZEICHEN = 300


def wechsel_starts(messages: list[dict]) -> list[int]:
    """Indizes der echten Nutzer-Nachrichten (nicht der tool_result-Nachrichten)."""
    return [i for i, m in enumerate(messages) if m.get("role") == "user" and isinstance(m.get("content"), str)]


def kuerze_werkzeug_ergebnisse(messages: list[dict], bis: int) -> list[dict]:
    """Werkzeug-Ergebnisse VOR Index `bis` auf eine Kurzfassung bringen (IDs bleiben -> Verlauf bleibt gueltig)."""
    out = []
    for i, m in enumerate(messages):
        inhalt = m.get("content")
        if i < bis and m.get("role") == "user" and isinstance(inhalt, list):
            neu = []
            for b in inhalt:
                text = b.get("content") if isinstance(b, dict) and b.get("type") == "tool_result" else None
                if isinstance(text, str) and len(text) > KURZ_ZEICHEN:
                    b = {**b, "content": f"{text[:KURZ_ZEICHEN]} … [gekuerzt, {len(text)} Zeichen — "
                                         f"bei Bedarf Werkzeug erneut aufrufen]"}
                neu.append(b)
            m = {**m, "content": neu}
        out.append(m)
    return out


def verdichte(messages: list[dict], budget_tokens: int, schaetzer=geschaetzte_tokens) -> list[dict]:
    """Verlauf unter `budget_tokens` bringen. Unveraendert, wenn er schon passt."""
    if schaetzer(messages) <= budget_tokens:
        return messages
    starts = wechsel_starts(messages)
    m = kuerze_werkzeug_ergebnisse(messages, starts[-1] if starts else 0)
    while schaetzer(m) > budget_tokens:
        starts = wechsel_starts(m)
        if len(starts) < 2:
            break  # nur noch der laufende Wechsel -- der bleibt immer vollstaendig
        m = m[starts[1]:]
    return m


def pausen_notiz(messages: list[dict], pause_stunden: float) -> str:
    """Kurze Notiz zur letzten Unterhaltung (letzte CEO-Frage + letzte LUNA-Antwort), ohne LLM."""
    frage = next((m["content"] for m in reversed(messages)
                  if m.get("role") == "user" and isinstance(m.get("content"), str)), "")
    antwort = ""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            inhalt = m.get("content")
            texte = [inhalt] if isinstance(inhalt, str) else [btext(b) for b in inhalt or [] if btype(b) == "text"]
            antwort = " ".join(t for t in texte if t).strip()
            if antwort:
                break
    if not frage and not antwort:
        return ""
    return (f"Letzte Unterhaltung (vor mehr als {pause_stunden:g} Std.): CEO fragte „{_kurz(frage)}\" — "
            f"LUNA antwortete „{_kurz(antwort)}\".")


def _kurz(text: str, n: int = 200) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + " …"
