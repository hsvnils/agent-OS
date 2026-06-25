"""Self-Checks: Finance-Dashboard (Register) + interne Luecken-/Mandatsanalyse (offline)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.kosten import KostenStore
from orchestrator.core.self_development import SelfDevelopment
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.dienste_register import register

ROOT = Path(__file__).resolve().parents[2]


class TestDashboardLuecken(unittest.TestCase):
    def test_1_register_live_aus_keys(self):
        reg = register({"GEMINI_API_KEY": "x", "BRAVE_API_KEY": "y"})
        gemini = [d for d in reg["dienste"] if d["name"].startswith("Gemini")][0]
        self.assertTrue(gemini["aktiv"])
        openai = [d for d in reg["dienste"] if d["name"].startswith("OpenAI")][0]
        self.assertFalse(openai["aktiv"])
        self.assertTrue(reg["modelle"])

    def test_2_finance_dashboard_tool(self):
        self.assertIn("finance_dashboard", {t["name"] for t in tool_specs()})
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        ks.record(quelle="chat", modell="gemini-2.5-flash", input_tokens=100, output_tokens=20)
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], kosten=ks,
                          secret_dict={"GEMINI_API_KEY": "x"})
        res = run_tool("finance_dashboard", {}, ctx)
        self.assertIn("modelle", res)
        self.assertIn("dienste", res)
        self.assertEqual(res["gemessene_kosten_monat"]["je_provider"].get("gemini", None), 0.0)

    def test_3_interne_luecken_analyse(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        sd = SelfDevelopment(HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                             antraege=antraege)
        erg = sd.vorschlag_fuer("cfo", modus="intern")
        self.assertIsNotNone(erg.antrag_id)
        self.assertEqual(antraege.get(erg.antrag_id)["von"], "cfo (Selbst-Entwicklung)")

    def test_4_selbstentwicklung_tool_intern(self):
        from orchestrator.core.scheduler import WatchScheduler, WatchStore
        from orchestrator.governance.github_watch import MockGitHubWatch
        watch = WatchScheduler(WatchStore(Path(tempfile.mkdtemp()) / "w.jsonl"), github=MockGitHubWatch())
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], watch=watch)
        res = run_tool("selbstentwicklung", {"abteilung": "cfo", "intern": True}, ctx)
        self.assertTrue(res["ok"])
        self.assertTrue(res["antrag_id"])


if __name__ == "__main__":
    unittest.main()
