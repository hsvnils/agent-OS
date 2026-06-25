"""Self-Check: FallbackBackend -- Fachagenten fallen bei CLI-Ausfall auf Gemini/OpenAI zurueck."""
import sys
import types
import unittest

from orchestrator.core.backends import FallbackBackend


class _FailPrimary:
    def respond(self, *a, **k):
        raise RuntimeError("Claude Code returned an error result")


class _OkPrimary:
    def respond(self, *a, **k):
        return "vom CLI"


def _fake_openai(antwort="vom Fallback"):
    mod = types.ModuleType("openai")

    class _Msg:
        content = antwort

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Client:
        def __init__(self, *a, **k):
            self.chat = self

        @property
        def completions(self):
            return self

        def create(self, **kw):
            return _Resp()
    mod.OpenAI = lambda *a, **k: _Client()
    return mod


class TestFallbackBackend(unittest.TestCase):
    def test_1_primary_ok_kein_fallback(self):
        b = FallbackBackend(_OkPrimary(), fallbacks=[{"name": "gemini", "key": "x", "model": "m"}])
        self.assertEqual(b.respond("cfo", "sys", "frage", {}), "vom CLI")

    def test_2_primary_fehlt_fallback_greift(self):
        sys.modules["openai"] = _fake_openai("Gemini-Antwort")
        try:
            b = FallbackBackend(_FailPrimary(),
                                fallbacks=[{"name": "gemini", "key": "x", "base_url": "u", "model": "m"}])
            self.assertEqual(b.respond("cfo", "sys", "frage", {}), "Gemini-Antwort")
        finally:
            del sys.modules["openai"]

    def test_3_ohne_fallback_wird_fehler_durchgereicht(self):
        with self.assertRaises(RuntimeError):
            FallbackBackend(_FailPrimary(), fallbacks=[]).respond("cfo", "s", "m", {})


if __name__ == "__main__":
    unittest.main()
