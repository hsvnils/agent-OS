"""Self-Checks fuer das kanal-unabhaengige HoA-Gehirn (Text/Telegram), offline mit Mock-Client."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.hoa_conversation import HoaConversation
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, outer):
        self.outer = outer

    def create(self, **kw):
        r = self.outer.scripted[self.outer.i]
        self.outer.i += 1
        return r


class FakeClient:
    def __init__(self, scripted):
        self.scripted = scripted
        self.i = 0
        self.messages = _FakeMessages(self)


def _ctx(backend=None, antraege=None, secrets=None):
    core = HeadOfAgents(backend or MockBackend(), load_all_subagents(), gate=CeoGate())
    return ToolContext(core=core, antraege=antraege or Antraege(Path(tempfile.mkdtemp()) / "log.jsonl"),
                       engine=None, finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=secrets or [])


class TestHoaConversation(unittest.TestCase):
    def test_1_tool_loop(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "log.jsonl")
        ctx = _ctx(antraege=antraege)
        client = FakeClient([
            _Resp([_Block(type="tool_use", id="t1", name="antrag_stellen",
                          input={"titel": "Logging", "beschreibung": "JSON-Logging", "von": "cto"})]),
            _Resp([_Block(type="text", text="Antrag eingereicht.")]),
        ])
        conv = HoaConversation(ctx, client=client)
        out = conv.respond("Stell einen Antrag fuer Logging.")
        self.assertEqual(out, "Antrag eingereicht.")
        self.assertEqual(len(antraege.list()), 1)
        self.assertEqual(antraege.list()[0]["status"], "eingereicht")

    def test_2_ceo_tor_delegate(self):
        res = run_tool("delegate", {"aufgabe": "ein neues kostenpflichtiges Tool beschaffen", "an": "cto"},
                       _ctx())
        self.assertTrue(res.get("blockiert"))

    def test_3_frage_finance_inhalt(self):
        res = run_tool("frage_finance", {"frage": "Budget?"}, _ctx())
        self.assertIn("Monatsbudget", res["finance"])

    def test_4_leck_schutz(self):
        secret = "sk-ant-CONVSECRET-3"
        backend = MockBackend(scripted={"berater": lambda m, c: f"nutze {secret}"})
        res = run_tool("delegate", {"aufgabe": "Strategie", "an": "berater"},
                       _ctx(backend=backend, secrets=[secret]))
        self.assertNotIn(secret, res["ergebnis"])
        self.assertIn("[REDACTED]", res["ergebnis"])

    def test_5_tool_specs(self):
        names = {t["name"] for t in tool_specs()}
        self.assertIn("antrag_umsetzen", names)
        self.assertIn("frage_finance", names)
        self.assertIn("delegate", names)

    def test_6_tool_fehler_zerstoert_chat_nicht(self):
        # Ein Tool-Fehler darf NICHT durchschlagen -- jedes tool_use bekommt ein tool_result,
        # danach laeuft das Gespraech normal weiter (Regression zum 'tool_use ohne tool_result'-400).
        import orchestrator.core.hoa_conversation as hc
        orig = hc.run_tool
        hc.run_tool = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("git exit 128"))
        try:
            client = FakeClient([
                _Resp([_Block(type="tool_use", id="t1", name="antrag_umsetzen", input={"antrag_id": "A-1"})]),
                _Resp([_Block(type="text", text="Die Umsetzung ist leider fehlgeschlagen.")]),
            ])
            conv = HoaConversation(_ctx(), client=client)
            out = conv.respond("Setz Antrag A-1 um.")
        finally:
            hc.run_tool = orig
        self.assertIn("fehlgeschlagen", out)
        # Verlauf ist gueltig: jedes tool_use hat ein tool_result.
        results = [m for m in conv.messages if m["role"] == "user" and isinstance(m["content"], list)]
        self.assertTrue(any(c.get("type") == "tool_result" for m in results for c in m["content"]))

    def test_7_repariert_kaputten_verlauf(self):
        conv = HoaConversation(_ctx(), client=FakeClient([]))
        # Simuliere kaputten Tail: Assistant-tool_use ohne folgendes tool_result.
        conv.messages = [{"role": "user", "content": "frueher"},
                         {"role": "assistant", "content": [_Block(type="tool_use", id="x", name="f", input={})]}]
        conv._repariere_verlauf()
        self.assertEqual(conv.messages[-1]["role"], "user")  # kaputter Assistant-Tail entfernt

    def test_8_selbstheilung_bei_verlauf_fehler(self):
        # create() wirft zuerst den 'tool_result'-400, dann (nach Reset) liefert es Text.
        class _HealClient:
            def __init__(self):
                self.calls = 0
                self.messages = self

            def create(self, **kw):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("400 invalid_request_error: tool_use ids without tool_result")
                return _Resp([_Block(type="text", text="Ja, ich bin da!")])
        conv = HoaConversation(_ctx(), client=_HealClient())
        conv.messages = [{"role": "assistant",
                          "content": [_Block(type="tool_use", id="x", name="f", input={})]}]
        out = conv.respond("Bist du da?")
        self.assertEqual(out, "Ja, ich bin da!")


if __name__ == "__main__":
    unittest.main()
