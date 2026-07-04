import unittest

from orchestrator.investment.signals import berechne


class TestSignale(unittest.TestCase):
    def test_aufwaertstrend_alle_bullisch(self):
        closes = [100, 102, 104, 106, 108, 110, 112, 114]
        sig = {s["typ"]: s for s in berechne(closes)}
        self.assertEqual(sig["momentum"]["richtung"], "steigt")
        self.assertEqual(sig["trend"]["richtung"], "steigt")
        self.assertEqual(sig["breakout"]["richtung"], "steigt")

    def test_abwaertstrend_bearisch(self):
        closes = [120, 118, 116, 114, 112, 110, 108, 106]
        sig = {s["typ"]: s for s in berechne(closes)}
        self.assertEqual(sig["momentum"]["richtung"], "faellt")
        self.assertEqual(sig["breakout"]["richtung"], "faellt")

    def test_zu_wenig_historie(self):
        self.assertEqual(berechne([100]), [])

    def test_staerke_im_bereich(self):
        for s in berechne([100, 103, 101, 108, 99, 112, 105, 120]):
            self.assertGreaterEqual(s["staerke"], 0.0)
            self.assertLessEqual(s["staerke"], 1.0)


if __name__ == "__main__":
    unittest.main()
