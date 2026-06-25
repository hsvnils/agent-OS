"""Self-Checks proaktiver Notifier -- offline, ohne Netz."""
import tempfile
import time
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.notifications import Notifications
from orchestrator.core.scheduler import WatchScheduler, WatchStore
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.github_watch import MockGitHubWatch
from orchestrator.governance.web_research import MockProvider, WebResearch

ROOT = Path(__file__).resolve().parents[2]


def _outbox():
    return Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")


class TestNotifications(unittest.TestCase):
    def test_1_enqueue_pending_sent(self):
        nb = _outbox()
        nid = nb.enqueue("Hallo CEO", kategorie="info")
        self.assertTrue(nid)
        self.assertEqual(len(nb.pending()), 1)
        nb.mark_sent(nid)
        self.assertEqual(nb.pending(), [])

    def test_2_dedup(self):
        nb = _outbox()
        self.assertTrue(nb.enqueue("gleich"))
        self.assertIsNone(nb.enqueue("gleich"))   # innerhalb Fenster -> dedupliziert
        self.assertEqual(len(nb.pending()), 1)

    def test_3_leer_ignoriert(self):
        self.assertIsNone(_outbox().enqueue("   "))

    def test_4_watcher_meldet_funde(self):
        nb = _outbox()
        sched = WatchScheduler(WatchStore(Path(tempfile.mkdtemp()) / "w.jsonl"),
                               github=MockGitHubWatch(),
                               web=WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic")),
                               notify=nb.enqueue)
        sched.github_tick(["ai-agents"])
        sched.dept_tick("cto")
        texte = " ".join(n["text"] for n in nb.pending())
        self.assertIn("GitHub", texte)
        self.assertIn("cto", texte)

    def test_5_tools(self):
        names = {t["name"] for t in tool_specs()}
        self.assertIn("melde_an_ceo", names)
        self.assertIn("benachrichtigungen_zeigen", names)
        nb = _outbox()
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], notifications=nb)
        r = run_tool("melde_an_ceo", {"text": "Abteilung CTO bittet um Freigabe X", "kategorie": "anliegen"}, ctx)
        self.assertTrue(r["ok"])
        offen = run_tool("benachrichtigungen_zeigen", {}, ctx)["offen"]
        self.assertEqual(len(offen), 1)
        self.assertEqual(offen[0]["kategorie"], "anliegen")

    def test_6_leck_schutz(self):
        secret = "sk-ant-NOTISECRET"
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl", secrets=[secret])
        nb.enqueue(f"geheim {secret}")
        self.assertNotIn(secret, nb.pending()[0]["text"])

    def test_7_durable(self):
        path = Path(tempfile.mkdtemp()) / "n.jsonl"
        Notifications(path).enqueue("bleibt")
        self.assertEqual(len(Notifications(path).pending()), 1)  # ueberlebt Neustart


if __name__ == "__main__":
    unittest.main()
