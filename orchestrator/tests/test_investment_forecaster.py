import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from orchestrator.investment.forecaster import Forecaster
from orchestrator.investment.loop_store import LoopStore


def _seed_historie(store, symbol, closes, *, start="2026-01-01"):
    d = date.fromisoformat(start)
    for c in closes:
        store.feature_add(symbol, "aktie", d.isoformat(), c, 0.0, {})
        d += timedelta(days=1)


class TestForecaster(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = LoopStore(Path(self.dir.name) / "features.jsonl")
        self.fc = Forecaster(self.store)

    def tearDown(self):
        self.dir.cleanup()

    def test_prognose_braucht_historie(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102])   # < MIN_HISTORIE
        r = self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-03")
        self.assertEqual(r["erstellt"], [])
        self.assertIn("AAPL", r["uebersprungen"])

    def test_prognose_steigt_bei_momentum(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105, 106])
        r = self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-07")
        self.assertIn("AAPL", r["erstellt"])
        f = self.store.list("inv_forecasts")[-1]
        self.assertEqual(f["richtung"], "steigt")
        self.assertGreater(f["ziel_return_pct"], 0)
        self.assertEqual(f["faellig_am"], "2026-01-14")
        self.assertEqual(f["baseline_return_pct"], 0.0)

    def test_prognose_idempotent_pro_tag(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105])
        self.fc.prognostizieren([{"symbol": "AAPL"}], datum="2026-01-06")
        r2 = self.fc.prognostizieren([{"symbol": "AAPL"}], datum="2026-01-06")
        self.assertEqual(r2["erstellt"], [])
        self.assertEqual(len(self.store.list("inv_forecasts")), 1)

    def test_auswertung_schreibt_abweichung_und_baseline(self):
        # Historie -> Prognose an Tag 6; danach faellt der Kurs nach 7 Tagen ein
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-06")
        # Realwert am Faelligkeitstag (2026-01-13): Kurs auf 110 (real +4.76% ggue. Basis 105)
        self.store.feature_add("AAPL", "aktie", "2026-01-13", 110.0, 0.0, {})
        r = self.fc.auswerten(heute="2026-01-13")
        self.assertEqual(r["neu_bewertet"], 1)
        dev = self.store.list("inv_deviations")[-1]
        self.assertAlmostEqual(dev["real_return_pct"], round((110 / 105 - 1) * 100, 3), places=2)
        # Baseline-Fehler = |0 - real| = real; besser_als_baseline nur wenn Modellfehler kleiner
        self.assertAlmostEqual(dev["baseline_fehler_abs_pct"], abs(dev["real_return_pct"]), places=2)
        self.assertIn("besser_als_baseline", dev)
        self.assertEqual(len(self.store.list("inv_actuals")), 1)

    def test_auswertung_nicht_faellig_wird_uebersprungen(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL"}], datum="2026-01-06")
        r = self.fc.auswerten(heute="2026-01-10")   # vor faellig_am 2026-01-13
        self.assertEqual(r["neu_bewertet"], 0)
        self.assertEqual(self.store.list("inv_deviations"), [])

    def test_auswertung_idempotent(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL"}], datum="2026-01-06")
        self.store.feature_add("AAPL", "aktie", "2026-01-13", 108.0, 0.0, {})
        self.fc.auswerten(heute="2026-01-13")
        self.fc.auswerten(heute="2026-01-13")
        self.assertEqual(len(self.store.list("inv_deviations")), 1)

    def test_kennzahlen_aggregiert_je_version(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL"}], datum="2026-01-06")
        self.store.feature_add("AAPL", "aktie", "2026-01-13", 106.0, 0.0, {})
        k = self.fc.auswerten(heute="2026-01-13")["kennzahlen"]
        self.assertEqual(k["gesamt"]["n"], 1)
        self.assertIn("v1-momentum", k["je_version"])
        self.assertIn("mae_pct", k["gesamt"])
        self.assertIn("anteil_besser_baseline", k["gesamt"])


    def test_kennzahlen_je_anlageklasse(self):
        _seed_historie(self.store, "AAPL", [100, 101, 102, 103, 104, 105], start="2026-01-01")
        _seed_historie(self.store, "ETHEREUM", [2000, 2020, 2040, 2060, 2080, 2100], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"},
                                 {"symbol": "ETHEREUM", "asset": "krypto"}], datum="2026-01-06")
        self.store.feature_add("AAPL", "aktie", "2026-01-13", 108.0, 0.0, {})
        self.store.feature_add("ETHEREUM", "krypto", "2026-01-13", 2200.0, 0.0, {})
        k = self.fc.auswerten(heute="2026-01-13")["kennzahlen"]
        self.assertIn("aktie", k["je_asset"])
        self.assertIn("krypto", k["je_asset"])
        self.assertEqual(k["je_asset"]["aktie"]["n"], 1)
        dev = next(d for d in self.store.list("inv_deviations") if d["symbol"] == "ETHEREUM")
        self.assertEqual(dev["asset"], "krypto")   # Anlageklasse im Register

    def test_verlauf_je_woche(self):
        # zwei Auswertungen in verschiedenen Wochen -> zwei Trend-Punkte
        for tag, close in [("2026-01-01", 100.0), ("2026-01-02", 101.0), ("2026-01-03", 102.0),
                           ("2026-01-04", 103.0), ("2026-01-05", 104.0), ("2026-01-06", 105.0)]:
            self.store.feature_add("AAPL", "aktie", tag, close, 0.0, {})
        self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-02")  # faellig 2026-01-09
        self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"}], datum="2026-01-06")  # faellig 2026-01-13
        self.store.feature_add("AAPL", "aktie", "2026-01-09", 106.0, 0.0, {})
        self.store.feature_add("AAPL", "aktie", "2026-01-13", 108.0, 0.0, {})
        self.fc.auswerten(heute="2026-01-13")
        v = self.fc.verlauf()
        self.assertGreaterEqual(len(v), 2)
        self.assertIn("mae_pct", v[0])
        self.assertIn("baseline_mae_pct", v[0])

    def test_chancen_nur_ausserhalb_watchlist(self):
        _seed_historie(self.store, "AAPL", [100, 105, 110, 116, 122, 128], start="2026-01-01")
        _seed_historie(self.store, "MSFT", [200, 210, 221, 233, 245, 258], start="2026-01-01")
        self.fc.prognostizieren([{"symbol": "AAPL", "asset": "aktie"},
                                 {"symbol": "MSFT", "asset": "aktie"}], datum="2026-01-06")
        chancen = self.fc.chancen(["AAPL"], min_konfidenz=0.6)
        symbole = [c["symbol"] for c in chancen]
        self.assertIn("MSFT", symbole)       # Vorschlag von aussen
        self.assertNotIn("AAPL", symbole)    # Watchlist ausgeschlossen


if __name__ == "__main__":
    unittest.main()
