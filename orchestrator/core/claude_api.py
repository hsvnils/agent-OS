"""Claude direkt ueber die API (CLAUDE_AKTIV C3, CEO 2026-10-26).

- `ClaudeApiBackend`: Fachagenten (CTO, Berater, CFO, ...) direkt ueber `messages.create` statt ueber die Claude-
  Kommandozeile -- gemessen 2026-10-26: Kommandozeile ~0,06 EUR je Anfrage (grosser eingebauter System-Prompt), direkt
  ~0,02 EUR. Reine Textantwort ohne Werkzeuge (wie bisher: `allowed_tools` war leer).
- `ClaudeChat`: kleiner Adapter mit der Form `client.chat.completions.create(model, messages, max_tokens)`, damit die
  bisherigen Gemini-Stellen (Content-Plan, Videograf, Kennzahlen-Screenshots, Gegenlesen, Kurzantworten) ohne Umbau auf
  Claude laufen. Intern das offizielle Anthropic-SDK; Bilder (`image_url` mit `data:`-URL) werden zu Bild-Bloecken.
- `cloud_client(secrets)`: Claude, sobald ein Anthropic-Schluessel gesetzt ist, sonst wie bisher Gemini (Schalter bis C4).
"""
from __future__ import annotations

from types import SimpleNamespace

from .model_router import claude_einstellungen

SCHNELL = "claude-haiku-5-5"      # Auslesen, Gegenlesen, Kurzantworten
STARK = "claude-sonnet-5-5"       # Vorschlaege, Fachagenten
GEMINI = {"schnell": "gemini-2.5-flash", "stark": "gemini-2.5-flash"}


def _text(content) -> str:
    return "".join(getattr(b, "text", "") or (b.get("text", "") if isinstance(b, dict) else "")
                   for b in content or [] if (getattr(b, "type", None) or (b.get("type") if isinstance(b, dict) else None)) == "text").strip()


def _anthropic(key: str, timeout: float, max_retries: int):
    import anthropic
    return anthropic.Anthropic(api_key=key, timeout=timeout, max_retries=max_retries)


class ClaudeApiBackend:
    """Fachagenten-Backend: ein `messages.create` je Anfrage, Modell/Aufwand je Agent aus `config.toml`."""

    def __init__(self, model_map: dict[str, str], effort_map: dict[str, str], *, api_key: str = "", client=None,
                 on_usage=None, max_tokens: int = 4000, timeout: float = 120):
        self.model_map, self.effort_map = model_map or {}, effort_map or {}
        self.client = client or (_anthropic(api_key, timeout, 2) if api_key else None)
        self.on_usage = on_usage          # (agent_key, modell, input_tokens, output_tokens, kosten_usd|None)
        self.max_tokens = max_tokens

    def respond(self, agent_key: str, system_prompt: str, message: str, context: dict) -> str:
        from .backends import BackendError
        if self.client is None:
            raise BackendError(f"Modellaufruf fuer '{agent_key}' nicht moeglich: kein ANTHROPIC_API_KEY.")
        modell = self.model_map.get(agent_key) or self.model_map.get("hoa") or STARK
        effort = self.effort_map.get(agent_key) or "medium"
        try:
            r = self.client.messages.create(model=modell, system=system_prompt,
                                            messages=[{"role": "user", "content": message}],
                                            **claude_einstellungen(modell, self.max_tokens, effort))
        except Exception as exc:
            raise BackendError(f"Modellaufruf fuer '{agent_key}' fehlgeschlagen ({str(exc)[:200]}).") from exc
        u = getattr(r, "usage", None)
        if self.on_usage is not None and u is not None:
            try:
                self.on_usage(agent_key, modell, getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0, None)
            except Exception:
                pass
        if getattr(r, "stop_reason", "") == "refusal":
            raise BackendError(f"Modellaufruf fuer '{agent_key}' abgelehnt (Sicherheitsfilter).")
        text = _text(r.content)
        if not text:
            raise BackendError(f"Modellaufruf fuer '{agent_key}': leere Antwort ({getattr(r, 'stop_reason', '?')}).")
        return text


def _bild_block(url: str) -> dict | None:
    """`data:<mime>;base64,<daten>` -> Anthropic-Bildblock (nur eingebettete Bilder, keine fremden URLs)."""
    if not url.startswith("data:") or ";base64," not in url:
        return None
    kopf, daten = url[5:].split(";base64,", 1)
    return {"type": "image", "source": {"type": "base64", "media_type": kopf or "image/jpeg", "data": daten}}


def _inhalt(content) -> list[dict] | str:
    if isinstance(content, str):
        return content
    out = []
    for teil in content or []:
        if teil.get("type") == "text":
            out.append({"type": "text", "text": teil.get("text", "")})
        elif teil.get("type") == "image_url":
            b = _bild_block((teil.get("image_url") or {}).get("url", ""))
            if b:
                out.append(b)
    return out


class _Completions:
    def __init__(self, chat: "ClaudeChat"):
        self._chat = chat

    def create(self, *, model: str, messages: list[dict], max_tokens: int = 4000, **_ignoriert):
        c = self._chat
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system" and isinstance(m.get("content"), str))
        nachrichten = [{"role": m["role"], "content": _inhalt(m.get("content"))} for m in messages
                       if m.get("role") in ("user", "assistant")]
        kw = {"system": system} if system else {}
        r = c.client.messages.create(model=model, messages=nachrichten, **kw,
                                     **claude_einstellungen(model, max_tokens, c.effort))
        u = getattr(r, "usage", None)
        ein, aus = (getattr(u, "input_tokens", 0) or 0), (getattr(u, "output_tokens", 0) or 0)
        if c.protokoll is not None:
            try:
                c.protokoll(model, ein, aus)
            except Exception:
                pass
        if getattr(r, "stop_reason", "") == "refusal":
            raise RuntimeError("Claude hat die Anfrage abgelehnt (Sicherheitsfilter).")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_text(r.content)),
                                                        finish_reason=getattr(r, "stop_reason", ""))],
                               usage=SimpleNamespace(prompt_tokens=ein, completion_tokens=aus))


class ClaudeChat:
    """Adapter: `ClaudeChat(key).chat.completions.create(model=..., messages=[...], max_tokens=...)`."""

    def __init__(self, key: str = "", *, effort: str = "low", timeout: float = 60, max_retries: int = 1, client=None,
                 protokoll=None):
        self.client = client or _anthropic(key, timeout, max_retries)
        self.effort = effort
        self.protokoll = protokoll        # (modell, input_tokens, output_tokens) -> Kostenerfassung
        self.chat = SimpleNamespace(completions=_Completions(self))


def cloud_client(secrets: dict, *, timeout: float = 60, protokoll=None, gemini_base: str = "") -> tuple[object | None, str]:
    """-> (client, anbieter): Claude, wenn ein Anthropic-Schluessel gesetzt ist; sonst Gemini (bis C4); sonst (None, "")."""
    s = secrets or {}
    key = (s.get("ANTHROPIC_API_KEY") or "").strip()
    if key:
        return ClaudeChat(key, timeout=timeout, protokoll=protokoll), "claude"
    gkey = (s.get("GEMINI_API_KEY") or "").strip()
    if gkey:
        import openai
        from .model_router import GEMINI_BASE_URL
        return openai.OpenAI(api_key=gkey, base_url=gemini_base or GEMINI_BASE_URL, timeout=timeout, max_retries=0), "gemini"
    return None, ""


def modell(anbieter: str, stufe: str = "schnell") -> str:
    if anbieter == "claude":
        return STARK if stufe == "stark" else SCHNELL
    return GEMINI.get(stufe, GEMINI["schnell"])


def kosten_protokoll(kosten, quelle: str):
    """(modell, ein, aus) -> Eintrag im KostenStore (`finance/kosten-log.jsonl`); Fehler nie durchreichen."""
    def _p(modell: str, ein: int, aus: int) -> None:
        if kosten is not None:
            kosten.record(quelle=quelle, modell=modell, input_tokens=ein, output_tokens=aus)
    return _p
