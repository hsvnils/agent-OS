import unittest

from orchestrator.investment.monitor import MarketMonitor


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class TestMarketMonitor(unittest.TestCase):
    def setUp(self):
        self.clk = _Clock()
        self.m = MarketMonitor(schwelle_pct=4.0, fenster_sek=1800, clock=self.clk)

    def test_erste_sicht_setzt_nur_referenz(self):
        self.assertEqual(self.m.beobachte({"AAPL": {"preis": 100.0, "asset": "aktie"}}), [])

    def test_kleine_bewegung_kein_signal(self):
        self.m.beobachte({"AAPL": {"preis": 100.0, "asset": "aktie"}})
        self.clk.t += 300
        self.assertEqual(self.m.beobachte({"AAPL": {"preis": 101.0, "asset": "aktie"}}), [])

    def test_scharfer_dip_meldet_faellt(self):
        self.m.beobachte({"AAPL": {"preis": 100.0, "asset": "aktie"}})
        self.clk.t += 300
        cands = self.m.beobachte({"AAPL": {"preis": 94.0, "asset": "aktie"}})   # -6%
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["richtung"], "faellt")
        self.assertAlmostEqual(cands[0]["move_pct"], -6.0, places=1)

    def test_scharfer_anstieg_meldet_steigt(self):
        self.m.beobachte({"BTC": {"preis": 100.0, "asset": "krypto"}})
        self.clk.t += 60
        cands = self.m.beobachte({"BTC": {"preis": 106.0, "asset": "krypto"}})
        self.assertEqual(cands[0]["richtung"], "steigt")

    def test_referenz_wird_nachgezogen_kein_dauerfeuer(self):
        self.m.beobachte({"AAPL": {"preis": 100.0, "asset": "aktie"}})
        self.clk.t += 300
        self.m.beobachte({"AAPL": {"preis": 94.0, "asset": "aktie"}})    # feuert einmal
        self.clk.t += 300
        self.assertEqual(self.m.beobachte({"AAPL": {"preis": 94.5, "asset": "aktie"}}), [])   # kein erneutes Feuer

    def test_fenster_abgelaufen_setzt_referenz_neu(self):
        self.m.beobachte({"AAPL": {"preis": 100.0, "asset": "aktie"}})
        self.clk.t += 2000     # > Fenster
        self.assertEqual(self.m.beobachte({"AAPL": {"preis": 90.0, "asset": "aktie"}}), [])   # Referenz neu, kein Signal


if __name__ == "__main__":
    unittest.main()
