"""Self-Checks fuer den Antrags-/Freigabe-Workflow (Phase 6), offline und ohne Kosten."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege


class TestAntraege(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "log.jsonl"

    def test_1_round_trip_eingereicht(self):
        a = Antraege(self.path)
        aid = a.stellen("Neues Logging", "JSON-Logging je Turn einfuehren", von="cto")
        items = a.list()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["antrag_id"], aid)
        self.assertEqual(items[0]["status"], "eingereicht")
        self.assertEqual(items[0]["von"], "cto")

    def test_2_freigeben_und_ablehnen(self):
        a = Antraege(self.path)
        aid1 = a.stellen("A", "...")
        aid2 = a.stellen("B", "...")
        self.assertTrue(a.freigeben(aid1))
        self.assertTrue(a.ablehnen(aid2, grund="zu teuer"))
        self.assertEqual(a.get(aid1)["status"], "freigegeben")
        self.assertEqual(a.get(aid2)["status"], "abgelehnt")
        # Verlauf bleibt erhalten (eingereicht -> entscheidung)
        self.assertEqual(len(a.get(aid1)["verlauf"]), 2)
        self.assertEqual(a.get(aid2)["verlauf"][-1]["grund"], "zu teuer")

    def test_3_event_sourcing_fold(self):
        a = Antraege(self.path)
        aid = a.stellen("C", "...")
        a.freigeben(aid)
        a.status_setzen(aid, "in_umsetzung")
        a.status_setzen(aid, "erledigt")
        # Frischer Loader liest dieselbe Datei -> gefalteter Zustand korrekt
        b = Antraege(self.path)
        self.assertEqual(b.get(aid)["status"], "erledigt")
        self.assertEqual([s["event"] for s in b.get(aid)["verlauf"]],
                         ["eingereicht", "freigegeben", "in_umsetzung", "erledigt"])

    def test_4_leck_schutz(self):
        secret = "sk-ant-ANTRAGSECRET-9"
        a = Antraege(self.path, secrets=[secret])
        a.stellen("Key nutzen", f"Bitte {secret} verwenden")
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn(secret, raw)
        self.assertIn("[REDACTED]", raw)

    def test_5_changelog_callback(self):
        eintraege = []
        a = Antraege(self.path, changelog=lambda *args: eintraege.append(args))
        aid = a.stellen("D", "...")
        a.freigeben(aid)
        a.ablehnen(aid)  # bereits freigegeben -> trotzdem Transition + Log
        self.assertGreaterEqual(len(eintraege), 2)
        self.assertTrue(any("eingereicht" in e[1] for e in eintraege))
        self.assertTrue(any("freigegeben" in e[1] for e in eintraege))

    def test_6_status_filter(self):
        a = Antraege(self.path)
        aid1 = a.stellen("offen", "...")
        aid2 = a.stellen("entschieden", "...")
        a.freigeben(aid2)
        offen = a.list(status="eingereicht")
        self.assertEqual([x["antrag_id"] for x in offen], [aid1])


if __name__ == "__main__":
    unittest.main()
