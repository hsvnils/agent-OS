"""Multi-Provider-Router fuer den Chat -- Anthropic zuerst, OpenAI als Fallback.

Loest den Anthropic-Credit-Engpass: schlaegt der Anthropic-Aufruf wegen Guthaben/Rate-Limit/Ueberlastung
fehl, wird automatisch auf OpenAI umgeschaltet. Die Tool-Calling-Schleife bleibt im Anthropic-Format; dieser
Router uebersetzt Verlauf/Tools nach OpenAI und die Antwort zurueck in Anthropic-faehige Bloecke (dicts).

Bloecke koennen SDK-Objekte (Anthropic) ODER dicts (OpenAI/Folgeturns) sein -> die `b*`-Helfer lesen beides.
"""
from __future__ import annotations

import json


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
    s = str(exc).lower()
    return any(w in s for w in ("credit", "balance", "insufficient", "rate", "overloaded",
                                "429", "529", "quota", "too low", "usage limit", "usage limits",
                                "reached your", "regain access", "limit"))


# Gemini ist OpenAI-kompatibel erreichbar -> dieselbe Uebersetzung wie OpenAI nutzen.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class ModelRouter:
    """Anthropic zuerst; bei Engpass/Limit der Reihe nach durch die Fallbacks (OpenAI-kompatibel: OpenAI, Gemini)."""

    def __init__(self, anthropic_client, *, anthropic_model: str, fallbacks: list[dict] | None = None,
                 max_tokens: int = 1024):
        self.anthropic_client = anthropic_client
        self.anthropic_model = anthropic_model
        # fallbacks: [{"name","key","base_url"(opt),"model"}] -- nur mit gesetztem key genutzt.
        self.fallbacks = [f for f in (fallbacks or []) if f.get("key")]
        self.max_tokens = max_tokens

    def create(self, *, system: str, tools: list, messages: list) -> _Norm:
        try:
            r = self.anthropic_client.messages.create(
                model=self.anthropic_model, max_tokens=self.max_tokens, system=system,
                tools=tools, messages=messages)
            return _Norm(r.content, getattr(r, "usage", None), self.anthropic_model, "anthropic")
        except Exception as exc:
            if not (self.fallbacks and _ist_fallback_fehler(exc)):
                raise
            letzter = exc
            for fb in self.fallbacks:
                try:
                    return self._kompatibel(fb, system, tools, messages)
                except Exception as e:
                    letzter = e
                    continue
            raise letzter

    # -- OpenAI-kompatibler Fallback (OpenAI, Gemini) --

    def _kompatibel(self, fb: dict, system: str, tools: list, messages: list) -> _Norm:
        import openai
        client = openai.OpenAI(api_key=fb["key"], base_url=fb.get("base_url") or None)
        r = client.chat.completions.create(
            model=fb["model"], max_tokens=self.max_tokens,
            messages=_zu_openai_messages(system, messages),
            tools=_zu_openai_tools(tools) or None, tool_choice="auto")
        msg = r.choices[0].message
        bloecke: list = []
        if msg.content:
            bloecke.append({"type": "text", "text": msg.content})
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            bloecke.append({"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": args})
        u = getattr(r, "usage", None)
        usage = _Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)
        return _Norm(bloecke, usage, fb["model"], fb.get("name", "fallback"))


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
