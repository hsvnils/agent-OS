"""Finance 2.5 -- Usage-Extraktion aus SDK-ResultMessage + Fallback-Callback (offline)."""
import types
import unittest

from orchestrator.core.backends import FallbackBackend, sdk_usage


class TestSdkUsage(unittest.TestCase):
    def _result(self, usage, cost=None):
        # Simuliert eine SDK-ResultMessage (Erkennung ueber Typnamen).
        r = types.new_class("ResultMessage")()
        r.usage = usage
        if cost is not None:
            r.total_cost_usd = cost
        return r

    def test_usage_als_dict(self):
        r = self._result({"input_tokens": 1200, "output_tokens": 300}, cost=0.05)
        self.assertEqual(sdk_usage(r), (1200, 300, 0.05))

    def test_usage_als_objekt(self):
        u = types.SimpleNamespace(input_tokens=50, output_tokens=10)
        r = self._result(u)
        self.assertEqual(sdk_usage(r), (50, 10, None))

    def test_andere_nachricht_ist_none(self):
        assistant = types.new_class("AssistantMessage")()
        assistant.content = []
        self.assertIsNone(sdk_usage(assistant))

    def test_leere_usage_ist_none(self):
        r = self._result({"input_tokens": 0, "output_tokens": 0})
        self.assertIsNone(sdk_usage(r))

    def test_erkennung_ueber_total_cost_ohne_typname(self):
        m = types.SimpleNamespace(usage={"input_tokens": 5, "output_tokens": 2}, total_cost_usd=0.001)
        self.assertEqual(sdk_usage(m), (5, 2, 0.001))


class TestFallbackUsageCallback(unittest.TestCase):
    def test_fallback_ruft_on_usage(self):
        erfasst = []
        fb = FallbackBackend(primary=None, on_usage=lambda *a: erfasst.append(a))

        class FakeResp:
            usage = types.SimpleNamespace(prompt_tokens=400, completion_tokens=120)
            choices = [types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]

        class FakeClient:
            def __init__(self, **kw): pass
            class chat:  # noqa: N801
                class completions:  # noqa: N801
                    @staticmethod
                    def create(**kw): return FakeResp()

        import sys
        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = lambda **kw: FakeClient()
        sys.modules["openai"] = fake_openai
        try:
            out = fb._kompatibel({"key": "x", "model": "gpt-4o-mini"}, "CFO", "sys", "frage")
        finally:
            del sys.modules["openai"]
        self.assertEqual(out, "ok")
        self.assertEqual(len(erfasst), 1)
        self.assertEqual(erfasst[0][0], "CFO")            # agent_key
        self.assertEqual(erfasst[0][1], "gpt-4o-mini")    # modell
        self.assertEqual(erfasst[0][2], 400)              # input
        self.assertEqual(erfasst[0][3], 120)              # output


if __name__ == "__main__":
    unittest.main()
