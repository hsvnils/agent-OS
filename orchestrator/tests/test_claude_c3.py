"""CLAUDE_AKTIV C3 (CEO 2026-10-26): Fachagenten direkt ueber die API (statt Claude-Kommandozeile), bisherige Gemini-Wege
(Content-Plan, Videograf, Kennzahlen-Screenshots, Kurzantworten, Backoffice-Gegenlesen) ueber Claude, solange ein
Anthropic-Schluessel gesetzt ist; sonst wie bisher Gemini."""
import base64
import unittest
from types import SimpleNamespace

from orchestrator.core.backends import BackendError
from orchestrator.core.claude_api import ClaudeApiBackend, ClaudeChat, cloud_client, kosten_protokoll, modell


def _antwort(text="Antwort", stop="end_turn", ein=100, aus=20):
    return SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
                           stop_reason=stop, usage=SimpleNamespace(input_tokens=ein, output_tokens=aus))


class _Client:
    def __init__(self, antwort=None, fehler=None):
        self.aufrufe, self.antwort, self.fehler = [], antwort or _antwort(), fehler
        self.messages = self

    def create(self, **kw):
        self.aufrufe.append(kw)
        if self.fehler:
            raise self.fehler
        return self.antwort


class TestFachagenten(unittest.TestCase):
    def test_1_direkt_ueber_api(self):
        c, kosten = _Client(_antwort("Ja, sinnvoll.")), []
        b = ClaudeApiBackend({"cto": "claude-sonnet-5-5"}, {"cto": "medium"}, client=c,
                             on_usage=lambda *x: kosten.append(x))
        self.assertEqual(b.respond("cto", "Du bist CTO.", "Frage?", {}), "Ja, sinnvoll.")
        kw = c.aufrufe[0]
        self.assertEqual((kw["model"], kw["system"], kw["output_config"]), ("claude-sonnet-5-5", "Du bist CTO.", {"effort": "medium"}))
        self.assertNotIn("tools", kw)                                        # reine Textantwort wie bisher
        self.assertEqual(kosten, [("cto", "claude-sonnet-5-5", 100, 20, None)])
        for client, grund in ((_Client(_antwort("")), "leere"), (_Client(_antwort("x", stop="refusal")), "abgelehnt"),
                              (_Client(fehler=RuntimeError("401")), "fehlgeschlagen")):
            with self.assertRaisesRegex(BackendError, grund):
                ClaudeApiBackend({}, {}, client=client).respond("cto", "s", "m", {})
        with self.assertRaisesRegex(BackendError, "kein ANTHROPIC_API_KEY"):
            ClaudeApiBackend({}, {}).respond("cto", "s", "m", {})

    def test_2_ausweich_bei_fehler(self):
        from orchestrator.core.backends import FallbackBackend
        fb = FallbackBackend(ClaudeApiBackend({}, {}, client=_Client(fehler=RuntimeError("Limit"))),
                             fallbacks=[{"name": "gemini", "key": "g", "base_url": "https://x", "model": "gemini-2.5-flash"}])
        fb._kompatibel = lambda f, a, sp, m: f"{f['name']}-antwort"
        self.assertEqual(fb.respond("cto", "s", "m", {}), "gemini-antwort")


class TestAdapter(unittest.TestCase):
    def test_3_nachrichten_und_bilder(self):
        c, protokoll = _Client(_antwort('{"likes": 12}')), []
        chat = ClaudeChat(client=c, protokoll=lambda *x: protokoll.append(x))
        bild = base64.b64encode(b"\x89PNG").decode()
        r = chat.chat.completions.create(model="claude-haiku-5-5", max_tokens=2000, messages=[
            {"role": "system", "content": "Du liest Zahlen."},
            {"role": "user", "content": [{"type": "text", "text": "Lies das Bild."},
                                         {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{bild}"}},
                                         {"type": "image_url", "image_url": {"url": "https://fremd.example/x.png"}}]}])
        self.assertEqual(r.choices[0].message.content, '{"likes": 12}')
        kw = c.aufrufe[0]
        self.assertEqual(kw["system"], "Du liest Zahlen.")
        self.assertEqual(kw["messages"][0]["content"], [{"type": "text", "text": "Lies das Bild."},
                                                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": bild}}])
        self.assertEqual(protokoll, [("claude-haiku-5-5", 100, 20)])        # Kosten erfasst
        self.assertIn("thinking", kw)

    def test_4_anbieterwahl_und_kosten(self):
        cl, anb = cloud_client({"ANTHROPIC_API_KEY": "sk-ant-test", "GEMINI_API_KEY": "g"})
        self.assertEqual((anb, type(cl).__name__), ("claude", "ClaudeChat"))
        self.assertEqual(cloud_client({"GEMINI_API_KEY": "g"})[1], "gemini")
        self.assertEqual(cloud_client({}), (None, ""))
        self.assertEqual((modell("claude", "schnell"), modell("claude", "stark"), modell("gemini")),
                         ("claude-haiku-5-5", "claude-sonnet-5-5", "gemini-2.5-flash"))
        gebucht = []
        kosten_protokoll(SimpleNamespace(record=lambda **kw: gebucht.append(kw)), "videograf")("claude-sonnet-5-5", 10, 5)
        self.assertEqual(gebucht[0]["quelle"], "videograf")


class TestBackofficeGegenlesen(unittest.TestCase):
    def test_5_claude_dann_gemini(self):
        from backoffice import worker
        c = _Client(_antwort("Entwurf ok, Punkt 2 fehlt."))
        self.assertEqual(worker.gegenlesen({"ANTHROPIC_API_KEY": "k"}, {"aufgabe": "A"}, "E", client=c), "Entwurf ok, Punkt 2 fehlt.")
        self.assertEqual(c.aufrufe[0]["model"], "claude-haiku-5-5")
        alt = worker.gemini_gegenlesen
        try:
            worker.gemini_gegenlesen = lambda env, a, e: "gemini"
            self.assertEqual(worker.gegenlesen({"ANTHROPIC_API_KEY": "k"}, {}, "E", client=_Client(fehler=RuntimeError("401"))), "gemini")
            self.assertEqual(worker.gegenlesen({}, {}, "E"), "gemini")
        finally:
            worker.gemini_gegenlesen = alt


class TestVerdrahtung(unittest.TestCase):
    def test_6_bot_nutzt_api_backend(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "channels" / "telegram" / "bot.py").read_text(encoding="utf-8")
        self.assertIn("ClaudeApiBackend(cfg[\"models\"], cfg[\"effort\"]", src)
        self.assertNotIn("AgentSdkBackend(cfg", src)
        web = (Path(__file__).resolve().parents[1] / "channels" / "web" / "app.py").read_text(encoding="utf-8")
        self.assertNotIn('get("GEMINI_API_KEY") or "").strip()', web)       # keine direkten Gemini-Wege mehr in der Web-App


if __name__ == "__main__":
    unittest.main()
