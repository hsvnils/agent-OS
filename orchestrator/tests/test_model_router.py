"""Self-Checks Multi-Provider-Router -- Anthropic-first + OpenAI-Fallback (offline, Fakes)."""
import json
import unittest

from orchestrator.core.model_router import (
    ModelRouter, _zu_openai_messages, _zu_openai_tools, btype, bname,
)


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, usage=None):
        self.content = content
        self.usage = usage


class _AnthroOK:
    def __init__(self, resp):
        self._resp = resp
        self.messages = self

    def create(self, **kw):
        return self._resp


class _AnthroFail:
    def __init__(self, exc):
        self._exc = exc
        self.messages = self

    def create(self, **kw):
        raise self._exc


class TestModelRouter(unittest.TestCase):
    def test_1_anthropic_pfad(self):
        r = ModelRouter(_AnthroOK(_Resp([_Block(type="text", text="hi")])), anthropic_model="claude-haiku-4-5")
        out = r.create(system="s", tools=[], messages=[{"role": "user", "content": "x"}])
        self.assertEqual(out.provider, "anthropic")
        self.assertEqual(btype(out.content[0]), "text")

    def test_2_kein_fallback_ohne_openai_key(self):
        r = ModelRouter(_AnthroFail(RuntimeError("credit balance too low")), anthropic_model="m")
        with self.assertRaises(RuntimeError):
            r.create(system="s", tools=[], messages=[])

    def test_3_tools_uebersetzung(self):
        ot = _zu_openai_tools([{"name": "f", "description": "d",
                               "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}}}])
        self.assertEqual(ot[0]["type"], "function")
        self.assertEqual(ot[0]["function"]["name"], "f")
        self.assertIn("properties", ot[0]["function"]["parameters"])

    def test_4_messages_uebersetzung_toolflow(self):
        msgs = [
            {"role": "user", "content": "frage"},
            {"role": "assistant", "content": [_Block(type="text", text="moment"),
                                              _Block(type="tool_use", id="t1", name="f", input={"a": 1})]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{\"ok\":true}"}]},
        ]
        o = _zu_openai_messages("SYS", msgs)
        self.assertEqual(o[0]["role"], "system")
        # Assistant-Turn hat tool_calls
        asst = [m for m in o if m["role"] == "assistant"][0]
        self.assertEqual(asst["tool_calls"][0]["function"]["name"], "f")
        self.assertEqual(json.loads(asst["tool_calls"][0]["function"]["arguments"]), {"a": 1})
        # tool_result -> role tool
        tool = [m for m in o if m["role"] == "tool"][0]
        self.assertEqual(tool["tool_call_id"], "t1")

    def test_5_fallback_uebersetzt_openai_antwort(self):
        # OpenAI-Client faken: liefert eine Tool-Call-Antwort -> Router macht Anthropic-Bloecke daraus.
        class _FakeOpenAIMsg:
            content = None

            class _TC:
                id = "c1"

                class function:
                    name = "frage_finance"
                    arguments = '{"frage":"Budget"}'
                tool_calls_inner = None
            tool_calls = [_TC()]

        class _FakeChoice:
            message = _FakeOpenAIMsg()

        class _FakeUsage:
            prompt_tokens = 12
            completion_tokens = 3

        class _FakeOAResp:
            choices = [_FakeChoice()]
            usage = _FakeUsage()

        class _FakeOAClient:
            def __init__(self, *a, **k):
                self.chat = self

            @property
            def completions(self):
                return self

            def create(self, **kw):
                return _FakeOAResp()

        import orchestrator.core.model_router as mr
        # openai-Modul faken
        import sys
        import types
        fake = types.ModuleType("openai")
        fake.OpenAI = lambda *a, **k: _FakeOAClient()
        sys.modules["openai"] = fake
        try:
            r = ModelRouter(_AnthroFail(RuntimeError("rate limit 429")), anthropic_model="m",
                            openai_key="sk-x", openai_model="gpt-4o-mini")
            out = r.create(system="s", tools=[], messages=[{"role": "user", "content": "Budget?"}])
        finally:
            del sys.modules["openai"]
        self.assertEqual(out.provider, "openai")
        self.assertEqual(bname(out.content[0]), "frage_finance")
        self.assertEqual(out.usage.input_tokens, 12)


if __name__ == "__main__":
    unittest.main()
