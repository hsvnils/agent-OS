"""Self-Checks Phase 9 (Innovations-Pipeline) -- offline, Mock-Backend, ohne Netz."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.innovation import InnovationPipeline, _titel
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.web_research import MockProvider, WebResearch

ROOT = Path(__file__).resolve().parents[2]


def _core(scripted=None):
    return HeadOfAgents(MockBackend(scripted=scripted or {}), load_all_subagents(), gate=CeoGate())


def _web():
    return WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic"))


class TestInnovation(unittest.TestCase):
    def test_1_pipeline_erzeugt_antrag(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        erg = InnovationPipeline(_core(), web=_web(), antraege=antraege).run("Test-Thema")
        # Befund aus Web, Idee/Bewertung aus den jeweiligen Agenten.
        self.assertTrue(erg.befund)
        self.assertTrue(erg.quellen)
        self.assertIn("berater", erg.idee)
        self.assertIn("cto", erg.machbarkeit)
        self.assertIn("cfo", erg.kostenvoranschlag)
        # Antrag wurde eingereicht (kein Ausfuehren).
        self.assertIsNotNone(erg.antrag_id)
        a = antraege.get(erg.antrag_id)
        self.assertEqual(a["status"], "eingereicht")
        self.assertEqual(a["von"], "Unternehmensberater (Innovation)")

    def test_2_ohne_web_laeuft_trotzdem(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        erg = InnovationPipeline(_core(), web=None, antraege=antraege).run()
        self.assertEqual(erg.befund, "")
        self.assertIsNotNone(erg.antrag_id)

    def test_3_backend_fehler_kein_absturz(self):
        def boom(msg, ctx):
            raise RuntimeError("Modell weg")
        core = _core(scripted={"berater": boom, "cto": boom, "cfo": boom})
        erg = InnovationPipeline(core, web=_web(),
                                 antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")).run()
        self.assertIn("nicht verfuegbar", erg.idee)
        self.assertIsNotNone(erg.antrag_id)  # Antrag entsteht trotzdem (mit Hinweis)

    def test_4_leck_schutz(self):
        secret = "sk-ant-INNOSECRET-1"
        core = _core(scripted={"berater": lambda m, c: f"Idee mit {secret}"})
        erg = InnovationPipeline(core, web=_web(),
                                 antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"),
                                 secrets=[secret]).run()
        self.assertNotIn(secret, erg.idee)
        self.assertIn("[REDACTED]", erg.idee)

    def test_5_tool(self):
        ctx = ToolContext(core=_core(), antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"),
                          engine=None, finance_dir=ROOT / "finance", repo_root=ROOT,
                          leak_secrets=[], web=_web())
        res = run_tool("innovation_scouting", {"thema": "Agenten-Frameworks"}, ctx)
        self.assertIn("innovation_scouting", {t["name"] for t in tool_specs()})
        self.assertTrue(res["antrag_id"])
        self.assertIn("Antrag", res["hinweis"])

    def test_6_titel_helfer(self):
        self.assertEqual(_titel("# Mein Titel\nNutzen..."), "Mein Titel")
        self.assertEqual(_titel(""), "Innovations-Vorschlag")


if __name__ == "__main__":
    unittest.main()
