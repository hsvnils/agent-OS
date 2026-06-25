"""Self-Checks Phase 12 (Watch-Scheduler) -- offline, ohne Netz/Token, Mock-GitHub."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.scheduler import WatchScheduler, WatchStore
from orchestrator.core.subagents import load_all_subagents
from orchestrator.core.watch_config import themen_fuer
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.github_watch import MockGitHubWatch, Repo, flag_fast_growers
from orchestrator.governance.web_research import MockProvider, WebResearch

ROOT = Path(__file__).resolve().parents[2]


def _store():
    return WatchStore(Path(tempfile.mkdtemp()) / "watch.jsonl")


def _web():
    return WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic"))


class TestWatch(unittest.TestCase):
    def test_1_fast_grower_erkennung(self):
        repos = [Repo(name="a/x", url="u1", sterne=1000, erstellt="2020-01-01T00:00:00Z"),
                 Repo(name="a/y", url="u2", sterne=80, erstellt="2026-06-01T00:00:00Z")]
        hist = {"a/x": 900}  # x ist um 100 gewachsen
        flagged = flag_fast_growers(repos, hist, min_zuwachs=50)
        namen = {r.name for r in flagged}
        self.assertIn("a/x", namen)   # +100 Sterne
        self.assertIn("a/y", namen)   # neu + >=50 Sterne
        self.assertEqual(hist["a/x"], 1000)  # Historie fortgeschrieben

    def test_2_github_tick_speichert_und_dedupliziert(self):
        store = _store()
        sched = WatchScheduler(store, github=MockGitHubWatch(), web=_web())
        n1 = sched.github_tick(["ai-agents"])
        self.assertTrue(n1)                       # erster Lauf: Fund
        n2 = sched.github_tick(["ai-agents"])
        self.assertEqual(n2, [])                  # zweiter Lauf: dedupliziert (kein neuer Fund)
        self.assertTrue(store.findings())

    def test_3_keine_llm_kosten_im_hintergrund(self):
        # Scheduler nutzt KEIN Backend -> garantiert keine Token im Hintergrund.
        sched = WatchScheduler(_store(), github=MockGitHubWatch(), web=_web())
        self.assertFalse(sched.llm_enabled)

    def test_4_dept_tick_nutzt_brave(self):
        store = _store()
        sched = WatchScheduler(store, github=MockGitHubWatch(), web=_web())
        neue = sched.dept_tick("cto")
        self.assertTrue(neue)
        self.assertTrue(all(f["abteilung"] == "cto" for f in neue))
        self.assertTrue(store.last_run("dept:cto"))

    def test_5_watch_config_fachbereiche(self):
        self.assertTrue(themen_fuer("ciso")["suche"])
        self.assertIn("ai-agents", themen_fuer("cto")["github"])
        self.assertEqual(themen_fuer("gibtsnicht"), {"suche": [], "github": []})

    def test_6_tools(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("github_trends", "dept_briefing", "watch_digest", "watch_tick"):
            self.assertIn(n, names)
        sched = WatchScheduler(_store(), github=MockGitHubWatch(), web=_web())
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], watch=sched)
        r = run_tool("github_trends", {"thema": "ai-agents"}, ctx)
        self.assertTrue(r["ok"])
        d = run_tool("dept_briefing", {"abteilung": "cfo"}, ctx)
        self.assertEqual(d["abteilung"], "cfo")
        self.assertTrue(run_tool("watch_digest", {}, ctx)["funde"])

    def test_7_durable_resume(self):
        # Store ueberlebt Neustart (neue Instanz, gleiche Datei) -> Historie/Funde bleiben.
        path = Path(tempfile.mkdtemp()) / "w.jsonl"
        WatchScheduler(WatchStore(path), github=MockGitHubWatch(), web=_web()).github_tick(["ai-agents"])
        store2 = WatchStore(path)
        self.assertTrue(store2.findings())
        self.assertTrue(store2.star_history())


if __name__ == "__main__":
    unittest.main()
