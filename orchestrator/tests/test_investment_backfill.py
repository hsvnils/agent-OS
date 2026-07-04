import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.backfill import Backfill
from orchestrator.investment.forecaster import forecast_fields
from orchestrator.investment.loop_store import LoopStore
from orchestrator.investment.providers import MarketData


class TestForecastFields(unittest.TestCase):
    def test_aufwaerts_ist_steigt(self):
        ff = forecast_fields([100, 102, 104, 106, 108, 110, 112])
        self.assertEqual(ff["richtung"], "steigt")
        self.assertGreater(ff["ziel_return_pct"], 0)
        self.assertIn("basis_close", ff)


class TestProviderHistorie(unittest.TestCase):
    def test_aktie_historie_parst_alpha_vantage(self):
        def fake(url, headers=None):
            return {"Time Series (Daily)": {"2026-06-02": {"4. close": "101.0"},
                                            "2026-06-01": {"4. close": "100.0"}}}
        md = MarketData({"ALPHAVANTAGE_API_KEY": "x"}, fetch=fake)
        r = md.aktie_historie("AAPL")
        self.assertTrue(r["ok"])
        self.assertEqual(r["closes"]["2026-06-01"], 100.0)

    def test_aktie_historie_ratelimit_note(self):
        md = MarketData({"ALPHAVANTAGE_API_KEY": "x"}, fetch=lambda u, headers=None: {"Note": "rate limit"})
        self.assertFalse(md.aktie_historie("AAPL")["ok"])

    def test_crypto_historie_parst_coingecko(self):
        def fake(url, headers=None):
            return {"prices": [[1717200000000, 60000.0], [1717286400000, 61000.0]]}
        r = MarketData({}, fetch=fake).crypto_historie("bitcoin", tage=30)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["closes"]), 2)


class _StubMarket:
    """Liefert eine steigende Kurshistorie fuer beliebige Symbole (Aktie + Krypto)."""
    def __init__(self, start="2026-05-01", n=40):
        from datetime import date, timedelta
        d = date.fromisoformat(start)
        self.hist = {}
        for i in range(n):
            self.hist[(d + timedelta(days=i)).isoformat()] = 100.0 + i    # + Aufwaertstrend
    def aktie_historie(self, symbol, *, outputsize="full"):
        return {"ok": True, "closes": dict(self.hist)}
    def crypto_historie(self, coin_id, *, tage=180, vs="usd"):
        return {"ok": True, "closes": dict(self.hist)}


class TestBackfill(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = LoopStore(Path(self.dir.name) / "features.jsonl")
        self.bf = Backfill(_StubMarket(), self.store)

    def tearDown(self):
        self.dir.cleanup()

    def test_lade_historie_schreibt_features(self):
        r = self.bf.lade_historie([{"symbol": "AAPL", "asset": "aktie"}], seit="2026-05-01")
        self.assertGreater(r["zeilen_neu"], 20)
        self.assertGreater(len(self.store.features_for("AAPL")), 20)

    def test_backtest_fuellt_register_als_backtest(self):
        self.bf.lade_historie([{"symbol": "AAPL", "asset": "aktie"}], seit="2026-05-01")
        r = self.bf.backtest()
        self.assertGreater(r["auswertungen_neu"], 0)
        devs = self.store.list("inv_deviations")
        self.assertTrue(devs and all(d.get("backtest") for d in devs))

    def test_backtest_idempotent(self):
        self.bf.lade_historie([{"symbol": "AAPL", "asset": "aktie"}], seit="2026-05-01")
        self.bf.backtest()
        n1 = len(self.store.list("inv_deviations"))
        self.bf.backtest()
        self.assertEqual(len(self.store.list("inv_deviations")), n1)   # keine Doppel-Auswertung


if __name__ == "__main__":
    unittest.main()
