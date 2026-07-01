import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.store import InvestmentStore


class TestInvestmentStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.s = InvestmentStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_mode_default_advisory(self):
        self.assertEqual(self.s.mode(), "advisory")

    def test_mode_wechsel(self):
        self.s.set_mode("paper", grund="Track-Record gut")
        self.assertEqual(self.s.mode(), "paper")
        self.s.set_mode("advisory")
        self.assertEqual(self.s.mode(), "advisory")

    def test_mode_ungueltig(self):
        with self.assertRaises(ValueError):
            self.s.set_mode("yolo")

    def test_watchlist_add_remove(self):
        self.s.watchlist_add("aapl")
        self.s.watchlist_add("BTC", asset="krypto")
        self.assertEqual({w["symbol"] for w in self.s.watchlist()}, {"AAPL", "BTC"})
        self.s.watchlist_remove("aapl")
        self.assertEqual({w["symbol"] for w in self.s.watchlist()}, {"BTC"})

    def test_forecast_und_suggestion(self):
        fid = self.s.forecast_add("AAPL", prognose="steigt", konfidenz=0.7, horizont="1W", rationale="RSI")
        self.assertTrue(fid.startswith("FOR-"))
        sid = self.s.suggestion_add("AAPL", aktion="beobachten", grund="Ausbruch", konfidenz=0.6,
                                    risiko_label="spekulativ", quellen=["http://x"])
        self.assertTrue(sid.startswith("SUG-"))
        self.assertEqual(len(self.s.list("forecasts")), 1)
        self.assertEqual(self.s.list("suggestions")[0]["risiko_label"], "spekulativ")

    def test_insider_signal_add_und_list(self):
        self.s.insider_signal_add("aapl", insider="Doe John", rolle="CEO", transaktion="kauf",
                                  betrag=10000, anzahl=1000, datum="2026-06-20", quelle="SEC Form 4",
                                  filing_url="http://sec.gov/x", cluster=2, konfidenz=0.6)
        sigs = self.s.insider_signals()
        self.assertEqual(len(sigs), 1)
        self.assertEqual(sigs[0]["symbol"], "AAPL")
        self.assertEqual(sigs[0]["cluster"], 2)
        self.assertEqual(sigs[0]["status"], "offen")
        self.assertTrue(self.s.list("insider_signals"))

    def test_unbekannte_tabelle(self):
        with self.assertRaises(ValueError):
            self.s.add("gibtsnicht", {})

    def test_leak_schutz_beim_schreiben(self):
        s = InvestmentStore(Path(self.dir.name) / "l2.jsonl", secrets=["GEHEIM123456"])
        s.suggestion_add("AAPL", aktion="kaufen", grund="enthaelt GEHEIM123456 im Text")
        roh = (Path(self.dir.name) / "l2.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("GEHEIM123456", roh)


if __name__ == "__main__":
    unittest.main()
