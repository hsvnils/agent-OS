"""Self-Checks Phase 13 (Self-Development-Loop) -- offline, Mock-Backend, ohne Netz."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.scheduler import WatchScheduler, WatchStore
from orchestrator.core.self_development import SelfDevelopment
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.github_watch import MockGitHubWatch
from orchestrator.governance.web_research import MockProvider, WebResearch

ROOT = Path(__file__).resolve().parents[2]


def _core():
    return HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())


def _watch_mit_wissen():
    store = WatchStore(Path(tempfile.mkdtemp()) / "w.jsonl")
    sched = WatchScheduler(store, github=MockGitHubWatch(),
                           web=WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic")))
    sched.dept_tick("cto")  # Wissensstand fuer cto fuellen
    return sched


class TestSelfDevelopment(unittest.TestCase):
    def test_1_vorschlag_erzeugt_antrag_vom_bereich(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        sd = SelfDevelopment(_core(), watch=_watch_mit_wissen(), antraege=antraege)
        erg = sd.vorschlag_fuer("cto")
        self.assertIsNotNone(erg.antrag_id)
        a = antraege.get(erg.antrag_id)
        self.assertEqual(a["status"], "eingereicht")
        self.assertEqual(a["von"], "cto (Selbst-Entwicklung)")
        # Idee kam vom Bereich cto, Bewertung von cto/cfo.
        self.assertIn("cto", erg.idee)
        self.assertIn("cfo", erg.kostenvoranschlag)

    def test_2_geplanter_lauf_ist_per_default_aus(self):
        sd = SelfDevelopment(_core(), watch=_watch_mit_wissen(),
                             antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"))
        res = sd.lauf()
        self.assertFalse(res["ok"])
        self.assertIn("aus", res["hinweis"])

    def test_3_geplanter_lauf_aktiviert(self):
        sd = SelfDevelopment(_core(), watch=_watch_mit_wissen(),
                             antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), enabled=True)
        res = sd.lauf()
        self.assertTrue(res["ok"])
        self.assertTrue(res["antraege"])

    def test_4_notbremse_stoppt_lauf(self):
        watch = _watch_mit_wissen()
        watch.store.set_pause(True)
        sd = SelfDevelopment(_core(), watch=watch,
                             antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), enabled=True)
        res = sd.lauf()
        self.assertFalse(res["ok"])
        self.assertIn("pausiert", res["hinweis"].lower())

    def test_5_tools(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("selbstentwicklung", "autonomie_pausieren", "autonomie_status"):
            self.assertIn(n, names)
        watch = _watch_mit_wissen()
        ctx = ToolContext(core=_core(), antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"),
                          engine=None, finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[],
                          watch=watch, web=watch.web)
        r = run_tool("selbstentwicklung", {"abteilung": "cto"}, ctx)
        self.assertTrue(r["ok"])
        self.assertTrue(r["antrag_id"])

    def test_6_notbremse_tool(self):
        watch = _watch_mit_wissen()
        ctx = ToolContext(core=_core(), antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"),
                          engine=None, finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[],
                          watch=watch, web=watch.web)
        self.assertTrue(run_tool("autonomie_pausieren", {"pausieren": True}, ctx)["pausiert"])
        self.assertTrue(run_tool("autonomie_status", {}, ctx)["pausiert"])
        # Bei Pause keine Selbst-Entwicklung.
        self.assertFalse(run_tool("selbstentwicklung", {"abteilung": "cto"}, ctx)["ok"])
        run_tool("autonomie_pausieren", {"pausieren": False}, ctx)
        self.assertFalse(run_tool("autonomie_status", {}, ctx)["pausiert"])


if __name__ == "__main__":
    unittest.main()
