"""Self-Checks: neue Google-Aktionen, Mail-/Kalender-Watcher, Self-Dev-Notify, Ticket-Auto-Close."""
import tempfile
import time
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.notifications import Notifications
from orchestrator.core.research_tickets import ResearchTickets
from orchestrator.core.scheduler import WatchScheduler, WatchStore
from orchestrator.core.self_development import SelfDevelopment
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.github_watch import MockGitHubWatch
from orchestrator.governance.google_workspace import MockGoogleWorkspace

ROOT = Path(__file__).resolve().parents[2]


def _ctx(**kw):
    base = dict(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[])
    base.update(kw)
    return ToolContext(**base)


class TestGoogleActionsWatcher(unittest.TestCase):
    def test_1_neue_google_tools_vorhanden(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("posteingang", "kalender_kollisionen", "termin_aendern", "termin_loeschen",
                  "mail_markieren", "drive_anlegen"):
            self.assertIn(n, names)

    def test_2_termin_aendern_gated(self):
        ctx = _ctx(google=MockGoogleWorkspace())
        vor = run_tool("termin_aendern", {"event_id": "e1", "titel": "Neu"}, ctx)
        self.assertTrue(vor["bestaetigung_noetig"])
        ok = run_tool("termin_aendern", {"event_id": "e1", "titel": "Neu", "bestaetigt": True}, ctx)
        self.assertTrue(ok["ok"])

    def test_3_termin_loeschen_gated_und_mail_markieren_benigne(self):
        ctx = _ctx(google=MockGoogleWorkspace())
        self.assertTrue(run_tool("termin_loeschen", {"event_id": "e1"}, ctx)["bestaetigung_noetig"])
        self.assertTrue(run_tool("termin_loeschen", {"event_id": "e1", "bestaetigt": True}, ctx)["ok"])
        # mail_markieren ist benigne -> kein bestaetigt noetig
        self.assertTrue(run_tool("mail_markieren", {"message_id": "m1"}, ctx)["ok"])

    def test_4_drive_anlegen_gated(self):
        ctx = _ctx(google=MockGoogleWorkspace())
        self.assertTrue(run_tool("drive_anlegen", {"name": "x.txt", "inhalt": "hi"}, ctx)["bestaetigung_noetig"])
        self.assertTrue(run_tool("drive_anlegen",
                                 {"name": "x.txt", "inhalt": "hi", "bestaetigt": True}, ctx)["ok"])

    def test_5_mail_watcher_meldet(self):
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        sched = WatchScheduler(WatchStore(Path(tempfile.mkdtemp()) / "w.jsonl"),
                               github=MockGitHubWatch(), google=MockGoogleWorkspace(), notify=nb.enqueue)
        neue = sched.mail_tick()
        self.assertTrue(neue)
        self.assertEqual(nb.pending()[0]["abteilung"], "Postfach")
        # Dedup: zweiter Lauf meldet dieselbe Mail nicht erneut
        self.assertEqual(sched.mail_tick(), [])

    def test_6_selfdev_meldet_zur_freigabe(self):
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        sd = SelfDevelopment(HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                             antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), notify=nb.enqueue)
        erg = sd.vorschlag_fuer("cfo")
        self.assertIsNotNone(erg.antrag_id)
        texte = " ".join(n["text"] for n in nb.pending())
        self.assertIn("bitte", texte.lower())
        self.assertIn("freigeben", texte.lower())

    def test_7_research_auto_close(self):
        r = ResearchTickets(Path(tempfile.mkdtemp()) / "r.jsonl")
        tid = r.erstellen("haengende Frage", abteilung="cto")
        # Zeitstempel kuenstlich alt machen, indem wir direkt mit stunden=0 aufraeumen
        n = r.aufraeumen(stunden=0)
        self.assertEqual(n, 1)
        self.assertEqual(r.get(tid)["status"], "fehlgeschlagen")


if __name__ == "__main__":
    unittest.main()
