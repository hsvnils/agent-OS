import tempfile
import unittest
from pathlib import Path

from orchestrator.governance.supabase import MockSupabaseClient
from orchestrator.investment.features import FeatureCollector
from orchestrator.investment.loop_store import LoopStore


class StubMarket:
    """Injizierbarer Markt-Stub: liefert feste Kurse oder Fall-B (ok=False)."""

    def __init__(self, aktie=100.0, krypto=50000.0, ok=True):
        self.aktie = aktie
        self.krypto = krypto
        self.ok = ok

    def aktie_quote(self, symbol):
        if not self.ok:
            return {"ok": False, "fall_b": True}
        return {"ok": True, "preis": self.aktie, "veraenderung_pct": 1.5}

    def crypto_preis(self, ids, vs="eur"):
        if not self.ok:
            return {"ok": False, "fall_b": True}
        return {"ok": True, "preise": {ids[0]: {"eur": self.krypto, "eur_24h_change": 2.0}}}


class TestLoopStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.sb = MockSupabaseClient()
        self.s = LoopStore(Path(self.dir.name) / "features.jsonl", supabase=self.sb)

    def tearDown(self):
        self.dir.cleanup()

    def test_feature_add_und_write_through(self):
        self.s.feature_add("AAPL", "aktie", "2026-01-02", 101.0, 1.0, {"ret_1d": None})
        rows = self.s.list("inv_features")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "AAPL")
        # Supabase-Zweitschrift mit Upsert-Schluessel symbol,datum
        self.assertEqual(self.sb.upserts[0][0], "inv_features")
        self.assertEqual(self.sb.upserts[0][2], "symbol,datum")

    def test_has_feature_und_features_for_chronologisch(self):
        self.s.feature_add("AAPL", "aktie", "2026-01-03", 103.0, 0.0, {})
        self.s.feature_add("AAPL", "aktie", "2026-01-01", 100.0, 0.0, {})
        self.s.feature_add("AAPL", "aktie", "2026-01-02", 102.0, 0.0, {})
        self.assertTrue(self.s.has_feature("aapl", "2026-01-02"))
        self.assertFalse(self.s.has_feature("AAPL", "2026-01-09"))
        closes = [r["close"] for r in self.s.features_for("AAPL")]
        self.assertEqual(closes, [100.0, 102.0, 103.0])  # nach Datum sortiert

    def test_kurs_serie_mit_sma(self):
        self.s.feature_add("AAPL", "aktie", "2026-01-02", 102.0, 0.0, {"sma_20": 101.5})
        self.s.feature_add("AAPL", "aktie", "2026-01-01", 100.0, 0.0, {"sma_20": None})
        serie = self.s.kurs_serie("aapl")
        self.assertEqual([r["datum"] for r in serie], ["2026-01-01", "2026-01-02"])  # sortiert
        self.assertEqual(serie[1]["sma20"], 101.5)

    def test_abweichungs_register_getrennt(self):
        self.s.deviation_add({"symbol": "AAPL", "modell_version": "v1", "fehler_abs_pct": 2.3,
                              "richtungstreffer": True, "besser_als_baseline": True})
        self.assertEqual(len(self.s.list("inv_deviations")), 1)
        self.assertEqual(len(self.s.list("inv_features")), 0)  # sauber getrennt


class TestFeatureCollector(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = LoopStore(Path(self.dir.name) / "features.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_collect_schreibt_werte_plus_baselines(self):
        c = FeatureCollector(StubMarket(), self.store)
        r = c.collect([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-02")
        self.assertTrue(r["ok"])
        self.assertIn("AAPL", r["gesammelt"])
        self.assertIn("SPY", r["gesammelt"])        # Benchmark automatisch dabei
        self.assertIn("BITCOIN", [s.upper() for s in r["gesammelt"]])
        rows = {e["symbol"]: e for e in self.store.list("inv_features")}
        self.assertFalse(rows["AAPL"]["baseline"])
        self.assertTrue(rows["SPY"]["baseline"])

    def test_collect_idempotent_pro_tag(self):
        c = FeatureCollector(StubMarket(), self.store)
        c.collect([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-02")
        r2 = c.collect([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-02")
        self.assertEqual(r2["gesammelt"], [])
        self.assertIn("AAPL", r2["uebersprungen"])
        self.assertEqual(len([e for e in self.store.list("inv_features") if e["symbol"] == "AAPL"]), 1)

    def test_universe_wird_mitgesammelt_und_etf_getaggt(self):
        c = FeatureCollector(StubMarket(), self.store)
        c.collect([{"symbol": "XYZ", "asset": "aktie"}], datum="2026-01-02")
        rows = {e["symbol"]: e for e in self.store.list("inv_features")}
        self.assertIn("XYZ", rows)          # Watchlist
        self.assertIn("QQQ", rows)          # aus dem Kernuniversum
        self.assertEqual(rows["QQQ"]["asset"], "etf")
        self.assertIn("ETHEREUM", rows)     # Krypto aus dem Kernuniversum
        self.assertEqual(rows["ETHEREUM"]["asset"], "krypto")

    def test_universe_leer_beschraenkt_auf_watchlist(self):
        c = FeatureCollector(StubMarket(), self.store)
        c.collect([{"symbol": "XYZ", "asset": "aktie"}], universe=[], datum="2026-01-02")
        syms = {e["symbol"] for e in self.store.list("inv_features")}
        self.assertNotIn("QQQ", syms)       # ohne Universum kein Discovery
        self.assertIn("XYZ", syms)

    def test_kein_kurs_landet_in_hinweisen(self):
        c = FeatureCollector(StubMarket(ok=False), self.store)
        r = c.collect([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-02")
        self.assertEqual(r["gesammelt"], [])
        self.assertTrue(any("AAPL" in h for h in r["hinweise"]))

    def test_abgeleitete_merkmale_aus_historie(self):
        for tag, close in [("2026-01-01", 100.0), ("2026-01-02", 102.0), ("2026-01-03", 101.0)]:
            self.store.feature_add("AAPL", "aktie", tag, close, 0.0, {})
        feats = FeatureCollector(StubMarket(), self.store)._derive("AAPL", 105.0)
        self.assertEqual(feats["n_hist"], 4)
        self.assertAlmostEqual(feats["ret_1d"], (105.0 / 101.0 - 1) * 100, places=2)
        self.assertIsNotNone(feats["vola_20d"])
        self.assertTrue(feats["ueber_sma20"])  # 105 ueber dem Schnitt von 100/102/101/105


if __name__ == "__main__":
    unittest.main()
