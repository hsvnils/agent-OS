"""Tests fuer manuelle Themen-Reels: Themen-Aufloesung + Reel-Job-Erkennung im Watcher."""
import json
import unittest

from cutter import reel_select
from cutter.watch import _reel_params


class TestManuelleThemen(unittest.TestCase):
    def test_torjubel_vorhanden(self):
        self.assertEqual(reel_select.THEMA_TAGS["Torjubel"], {"tor", "jubel"})
        self.assertIn("Torjubel", reel_select.MANUELLE_THEMEN)

    def test_thema_by_name(self):
        t = reel_select.thema_by_name("torjubel")            # case-insensitive
        self.assertIsNotNone(t)
        self.assertEqual(t[0], "Torjubel")
        self.assertIsNone(reel_select.thema_by_name("gibtsnicht"))
        self.assertIsNone(reel_select.thema_by_name(""))
        self.assertIsNone(reel_select.thema_by_name(None))


class TestReelJobErkennung(unittest.TestCase):
    def test_reel_note(self):
        note = json.dumps({"typ": "reel", "thema": "Torjubel", "spiel": None, "alle_spiele": True,
                           "min_dauer": 15, "max_dauer": 45})
        p = _reel_params({"note": note})
        self.assertIsNotNone(p)
        self.assertEqual(p["thema"], "Torjubel")
        self.assertTrue(p["alle_spiele"])
        self.assertEqual(p["min_dauer"], 15)

    def test_kein_reel_job(self):
        self.assertIsNone(_reel_params({"note": "nur ein normaler Ordner-Job"}))
        self.assertIsNone(_reel_params({"note": json.dumps({"typ": "cut"})}))
        self.assertIsNone(_reel_params({}))
        self.assertIsNone(_reel_params({"note": None}))


if __name__ == "__main__":
    unittest.main()
