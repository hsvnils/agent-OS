"""Self-Checks: Ticket-Uebersicht (offen/Archiv), kosten_optimierung, Snapshot-Execution."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.research_tickets import ResearchTickets
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


def _ctx(**kw):
    base = dict(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[],
                research=ResearchTickets(Path(tempfile.mkdtemp()) / "r.jsonl"))
    base.update(kw)
    return ToolContext(**base)


class TestTicketsFinance(unittest.TestCase):
    def test_1_offene_tickets_nur_offene(self):
        ctx = _ctx()
        a_offen = ctx.antraege.stellen("Offen X", "..", von="cto")
        a_zu = ctx.antraege.stellen("Zu Y", "..", von="cto")
        ctx.antraege.ablehnen(a_zu, grund="nope")
        ctx.research.erstellen("offene frage", abteilung="cfo")
        res = run_tool("offene_tickets", {}, ctx)
        ids = {t["id"] for t in res["antraege"]}
        self.assertIn(a_offen, ids)
        self.assertNotIn(a_zu, ids)           # geschlossener Antrag NICHT im aktiven Stand
        self.assertEqual(len(res["research"]), 1)

    def test_2_abteilung_archiv(self):
        ctx = _ctx()
        a = ctx.antraege.stellen("CTO-Sache", "..", von="cto")
        ctx.antraege.ablehnen(a, grund="x")    # -> geschlossen
        res = run_tool("abteilung_tickets", {"abteilung": "cto"}, ctx)
        self.assertEqual(res["anzahl"], 1)
        self.assertEqual(res["antraege"][0]["status"], "abgelehnt")
        # andere Abteilung sieht es nicht
        self.assertEqual(run_tool("abteilung_tickets", {"abteilung": "cfo"}, ctx)["anzahl"], 0)

    def test_3_kosten_optimierung_fragt_cfo(self):
        ctx = _ctx(secret_dict={"ANTHROPIC_API_KEY": "x", "BRAVE_API_KEY": "y"})
        res = run_tool("kosten_optimierung", {"fokus": "Token"}, ctx)
        self.assertTrue(res["ok"])
        self.assertIn("cfo", res["vorschlaege"])   # MockBackend echo enthaelt den Agenten-Key

    def test_4_tools_vorhanden(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("offene_tickets", "abteilung_tickets", "kosten_optimierung"):
            self.assertIn(n, names)

    def test_5_snapshot_execution_flag(self):
        # real_make_workspace nimmt snapshot-Flag (Produktion) entgegen.
        from orchestrator.core import execution_live
        mk = execution_live.real_make_workspace(ROOT, snapshot=False)
        self.assertTrue(callable(mk))


if __name__ == "__main__":
    unittest.main()
