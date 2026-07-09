"""Tests fuer manuelle Themen-Reels: Themen-Aufloesung (der Bau selbst laeuft im NAS-Container)."""
import unittest

from cutter import reel_select


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


if __name__ == "__main__":
    unittest.main()
