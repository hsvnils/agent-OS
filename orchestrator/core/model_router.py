"""Multi-Provider-Router fuer den Chat -- Anthropic zuerst, OpenAI als Fallback.

Loest den Anthropic-Credit-Engpass: schlaegt der Anthropic-Aufruf wegen Guthaben/Rate-Limit/Ueberlastung
fehl, wird automatisch auf OpenAI umgeschaltet. Die Tool-Calling-Schleife bleibt im Anthropic-Format; dieser
Router uebersetzt Verlauf/Tools nach OpenAI und die Antwort zurueck in Anthropic-faehige Bloecke (dicts).

Bloecke koennen SDK-Objekte (Anthropic) ODER dicts (OpenAI/Folgeturns) sein -> die `b*`-Helfer lesen beides.
"""
from __future__ import annotations

import json

from .lokal_llm import geschaetzte_tokens, gekuerzt, ohne_denktext


# -- Block-Helfer: lesen sowohl Anthropic-SDK-Objekte als auch dicts --

def btype(b):
    return b.get("type") if isinstance(b, dict) else getattr(b, "type", None)


def btext(b):
    return (b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")) or ""


def bid(b):
    return b.get("id") if isinstance(b, dict) else getattr(b, "id", None)


def bname(b):
    return b.get("name") if isinstance(b, dict) else getattr(b, "name", None)


def binput(b):
    return (b.get("input") if isinstance(b, dict) else getattr(b, "input", None)) or {}


class _Usage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Norm:
    """Normalisierte Antwort: content (Bloecke), usage, model, provider."""
    def __init__(self, content, usage, model, provider):
        self.content = content
        self.usage = usage
        self.model = model
        self.provider = provider


def _ist_fallback_fehler(exc: Exception) -> bool:
    s = f"{exc.__class__.__name__} {exc}".lower()
    return any(w in s for w in ("credit", "balance", "insufficient", "rate", "overloaded",
                                "429", "529", "quota", "too low", "usage limit", "usage limits",
                                "reached your", "regain access", "limit",
                                # Anbieter nicht erreichbar -> naechster Anbieter statt Abbruch (M6, 2026-09-25)
                                "connection", "timeout", "timed out",
                                # Schluessel ungueltig/gesperrt -> Anbieter unbrauchbar, naechster (BF-18, 2026-09-25)
                                "401", "authentication", "invalid x-api-key", "api key is invalid"))


# Gemini ist OpenAI-kompatibel erreichbar -> dieselbe Uebersetzung wie OpenAI nutzen.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class ModelRouter:
    """Anthropic zuerst; bei Engpass/Limit der Reihe nach durch die Fallbacks (OpenAI-kompatibel: OpenAI, Gemini).

    Fallbacks mit `zuerst=True` (lokales LLM, `core/lokal_llm.py`) werden VOR Anthropic gefragt -- scheitern sie,
    geht es normal weiter (Anthropic, dann die uebrigen Fallbacks)."""

    def __init__(self, anthropic_client, *, anthropic_model: str, fallbacks: list[dict] | None = None,
                 max_tokens: int = 1024):
        self.anthropic_client = anthropic_client
        self.anthropic_model = anthropic_model
        # fallbacks: [{"name","key","base_url"(opt),"model"}] -- nur mit gesetztem key genutzt.
        self.fallbacks = [f for f in (fallbacks or []) if f.get("key")]
        self.max_tokens = max_tokens

    def create(self, *, system: str, tools: list, messages: list) -> _Norm:
        for fb in [f for f in self.fallbacks if f.get("zuerst")]:
            try:
                return self._kompatibel(fb, system, tools, messages)
            except Exception:
                continue
        danach = [f for f in self.fallbacks if not f.get("zuerst")]
        try:
            r = self.anthropic_client.messages.create(
                model=self.anthropic_model, max_tokens=self.max_tokens, system=system,
                tools=tools, messages=messages)
            return _Norm(r.content, getattr(r, "usage", None), self.anthropic_model, "anthropic")
        except Exception as exc:
            if not (danach and _ist_fallback_fehler(exc)):
                raise
            letzter = exc
            for fb in danach:
                try:
                    return self._kompatibel(fb, system, tools, messages)
                except Exception as e:
                    letzter = e
                    continue
            raise letzter

    # -- OpenAI-kompatibler Fallback (OpenAI, Gemini) --

    def _kompatibel(self, fb: dict, system: str, tools: list, messages: list) -> _Norm:
        import openai
        client = openai.OpenAI(api_key=fb["key"], base_url=fb.get("base_url") or None, **_client_opts(fb))
        oa_messages, oa_tools = _zu_openai_messages(system, messages), _zu_openai_tools(tools)
        r = client.chat.completions.create(
            model=fb["model"], max_tokens=fb.get("max_tokens") or self.max_tokens,
            messages=oa_messages, tools=oa_tools or None, tool_choice="auto")
        u = getattr(r, "usage", None)
        if fb.get("kuerzung_pruefen"):
            geschaetzt = geschaetzte_tokens(oa_messages, oa_tools)
            if gekuerzt(getattr(u, "prompt_tokens", 0) or 0, geschaetzt):
                # Kontextfenster des Servers zu klein -> Werkzeugliste/Verlauf gekuerzt -> Antwort unzuverlaessig.
                raise RuntimeError(f"{fb.get('name')}: Prompt vom Server gekuerzt ({getattr(u, 'prompt_tokens', 0)} "
                                   f"statt ~{geschaetzt} Token) -- OLLAMA_CONTEXT_LENGTH erhoehen (BF-17)")
        msg = r.choices[0].message
        bloecke: list = []
        text = ohne_denktext(msg.content)
        if text:
            bloecke.append({"type": "text", "text": text})
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            bloecke.append({"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": args})
        if not bloecke:
            # z. B. Denkschritte haben max_tokens aufgebraucht -> leere Antwort ist ein Fehler, kein Ergebnis.
            raise RuntimeError(f"{fb.get('name', 'fallback')}: leere Antwort "
                               f"(finish_reason={getattr(r.choices[0], 'finish_reason', '?')})")
        usage = _Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)
        return _Norm(bloecke, usage, fb["model"], fb.get("name", "fallback"))


def _client_opts(fb: dict) -> dict:
    """Optionale Client-Einstellungen je Anbieter (lokales LLM: langer Timeout, keine Wiederholungen)."""
    return {k: fb[k] for k in ("timeout", "max_retries") if fb.get(k) is not None}


def _zu_openai_tools(tools: list) -> list:
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t.get("input_schema", {"type": "object",
                                                                                   "properties": {}})}}
            for t in tools]


def _zu_openai_messages(system: str, messages: list) -> list:
    out = [{"role": "system", "content": system}]
    for m in messages:
        role, content = m["role"], m["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            texte = [btext(b) for b in content if btype(b) == "text"]
            tool_calls = [{"id": bid(b), "type": "function",
                           "function": {"name": bname(b), "arguments": json.dumps(binput(b))}}
                          for b in content if btype(b) == "tool_use"]
            msg = {"role": "assistant", "content": (" ".join(t for t in texte if t) or None)}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
        else:  # user: tool_results ODER text
            results = [b for b in content if btype(b) == "tool_result"]
            if results:
                for b in results:
                    tid = b.get("tool_use_id") if isinstance(b, dict) else getattr(b, "tool_use_id", None)
                    inhalt = b.get("content") if isinstance(b, dict) else getattr(b, "content", "")
                    out.append({"role": "tool", "tool_call_id": tid,
                                "content": inhalt if isinstance(inhalt, str) else json.dumps(inhalt)})
            else:
                txt = " ".join(btext(b) for b in content if btype(b) == "text")
                out.append({"role": "user", "content": txt})
    return out
