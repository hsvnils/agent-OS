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


if __name__ == "__main__":
    unittest.main()
