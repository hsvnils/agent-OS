"""Self-Checks: Briefings, Agenda, Self-Maintenance, Meldungs-Details -- offline."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.briefing import Agenda, Briefing
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.notifications import Notifications
from orchestrator.core.scheduler import WatchScheduler, WatchStore
from orchestrator.core.self_maintenance import SelfMaintenance
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.github_watch import MockGitHubWatch

ROOT = Path(__file__).resolve().parents[2]


def _ctx(**kw):
    base = dict(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[])
    base.update(kw)
    return ToolContext(**base)


class TestBriefingMaintenance(unittest.TestCase):
    def test_1_agenda_lebenszyklus(self):
        ag = Agenda(Path(tempfile.mkdtemp()) / "ag.jsonl")
        nid = ag.notiz("Steuerberater anrufen")
        self.assertEqual(len(ag.offene()), 1)
        self.assertTrue(ag.erledigen(nid))
        self.assertEqual(ag.offene(), [])

    def test_2_briefing_enthaelt_offene_und_manuelle(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        antraege.stellen("Neues Tool X", "Beschreibung", von="cto")
        ag = Agenda(Path(tempfile.mkdtemp()) / "ag.jsonl")
        ag.notiz("Vertrag pruefen")
        text = Briefing(antraege=antraege, agenda=ag).erstellen("morgen")
        self.assertIn("Morgen-Briefing", text)
        self.assertIn("Neues Tool X", text)       # offener Antrag
        self.assertIn("Vertrag pruefen", text)     # manuelle Notiz

    def test_3_briefing_fenster(self):
        b = Briefing()
        morgen = b._fenster_start("morgen", datetime(2026, 6, 25, 8, 0))
        self.assertEqual((morgen.hour, morgen.day), (20, 24))  # gestern 20:00
        abend = b._fenster_start("abend", datetime(2026, 6, 25, 20, 0))
        self.assertEqual((abend.hour, abend.day), (8, 25))     # heute 08:00

    def test_4_self_maintenance_erkennt_fehlende_keys(self):
        sm = SelfMaintenance(secrets={"ANTHROPIC_API_KEY": "x"})  # Telegram/Brave fehlen
        probleme = [c for c in sm.pruefe() if not c["ok"]]
        self.assertTrue(any("Telegram" in p["komponente"] for p in probleme))

    def test_5_self_maintenance_meldet_proaktiv(self):
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        sm = SelfMaintenance(secrets={}, notify=nb.enqueue)
        sm.lauf()
        self.assertTrue(nb.pending())
        self.assertEqual(nb.pending()[0]["abteilung"], "IT/Self-Maintenance")

    def test_6_meldung_details_und_abteilung(self):
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        ctx = _ctx(notifications=nb)
        run_tool("melde_an_ceo", {"text": "Bitte X freigeben", "abteilung": "CTO",
                                  "detail": "Hintergrund: Server-Upgrade noetig."}, ctx)
        nid = nb.pending()[0]["id"]
        # per Kurz-Suffix abrufbar
        det = run_tool("meldung_details", {"id": nid.split("-")[-1]}, ctx)
        self.assertEqual(det["abteilung"], "CTO")
        self.assertIn("Server-Upgrade", det["detail"])

    def test_7_tools_vorhanden(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("briefing_jetzt", "notiz_hinzufuegen", "agenda_zeigen", "systemcheck", "meldung_details"):
            self.assertIn(n, names)

    def test_8_briefing_tool_und_agenda_tool(self):
        ag = Agenda(Path(tempfile.mkdtemp()) / "ag.jsonl")
        ctx = _ctx(agenda=ag)
        run_tool("notiz_hinzufuegen", {"text": "Rechnung zahlen"}, ctx)
        self.assertEqual(len(run_tool("agenda_zeigen", {}, ctx)["offen"]), 1)
        b = run_tool("briefing_jetzt", {"art": "abend"}, ctx)
        self.assertIn("Abend-Briefing", b["briefing"])
        self.assertIn("Rechnung zahlen", b["briefing"])

    def test_9_systemcheck_tool(self):
        watch = WatchScheduler(WatchStore(Path(tempfile.mkdtemp()) / "w.jsonl"), github=MockGitHubWatch())
        ctx = _ctx(watch=watch, secret_dict={"ANTHROPIC_API_KEY": "x", "TELEGRAM_BOT_TOKEN": "y",
                                             "TELEGRAM_ALLOWED_CHAT_ID": "1", "BRAVE_API_KEY": "z"})
        res = run_tool("systemcheck", {}, ctx)
        self.assertIn("checks", res)
        self.assertIsInstance(res["alles_ok"], bool)


if __name__ == "__main__":
    unittest.main()
