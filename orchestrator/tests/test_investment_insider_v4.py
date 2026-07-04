import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from orchestrator.investment import insider as insider_mod
from orchestrator.investment.forecaster import (
    INSIDER_HORIZONT_TAGE,
    MODELL_VERSION_INSIDER,
    insider_forecast_fields,
)
from orchestrator.investment.insider import InsiderModel
from orchestrator.investment.loop_store import LoopStore
from orchestrator.investment.providers import MarketData
from orchestrator.investment.signals import insider_signal


class TestProviderFilingDatum(unittest.TestCase):
    def test_insider_transactions_liefert_filing_datum(self):
        def fake(url, headers=None):
            return {"data": [
                {"transactionCode": "P", "name": "Jane Insider", "change": 1000,
                 "transactionPrice": 12.0, "transactionDate": "2026-03-01", "filingDate": "2026-03-03"},
                {"transactionCode": "S", "name": "Sell Guy", "change": -500,
                 "transactionPrice": 12.0, "transactionDate": "2026-03-01", "filingDate": "2026-03-03"},
            ]}
        md = MarketData({"FINNHUB_API_KEY": "x"}, fetch=fake)
        r = md.insider_transactions("SOFI", seit="2026-01-01")
        self.assertTrue(r["ok"])
        kaeufe = [t for t in r["transaktionen"] if t["transaktion"] == "kauf"]
        self.assertEqual(len(kaeufe), 1)                       # nur der Kauf (P), nicht der Verkauf (S)
        self.assertEqual(kaeufe[0]["filing_datum"], "2026-03-03")   # Filing-Datum getrennt von transactionDate


class TestInsiderSignalUndModell(unittest.TestCase):
    def test_insider_signal_immer_bullisch(self):
        s = insider_signal(3, 500_000)
        self.assertEqual(s["typ"], "insider")
        self.assertEqual(s["richtung"], "steigt")
        self.assertGreater(s["staerke"], 0.3)

    def test_insider_forecast_fields_bullisch_und_felder(self):
        closes = [100, 101, 102, 103, 104, 105, 106, 107]
        ff = insider_forecast_fields(closes, {"cluster": 3, "summe": 400_000})
        self.assertEqual(ff["richtung"], "steigt")
        self.assertGreater(ff["ziel_return_pct"], 0)
        self.assertIn("insider", ff["treiber"])
        for k in ("spanne_low", "spanne_high", "konfidenz", "basis_close", "vola_20d"):
            self.assertIn(k, ff)

    def test_groesseres_cluster_hoehere_konfidenz(self):
        closes = [100, 101, 102, 103, 104, 105, 106, 107]
        k1 = insider_forecast_fields(closes, {"cluster": 1, "summe": 60_000})["konfidenz"]
        k3 = insider_forecast_fields(closes, {"cluster": 4, "summe": 60_000})["konfidenz"]
        self.assertGreater(k3, k1)


class TestClusterPointInTime(unittest.TestCase):
    def setUp(self):
        self.im = InsiderModel(market=None, store=None)

    def test_cluster_ab_zwei_kaeufern(self):
        kaeufe = [{"insider": "A", "filing_datum": "2026-03-01", "wert": 10_000},
                  {"insider": "B", "filing_datum": "2026-03-02", "wert": 10_000}]
        cl = self.im._cluster_at(kaeufe, "2026-03-10")
        self.assertIsNotNone(cl)
        self.assertEqual(cl["cluster"], 2)

    def test_einzelner_grosskauf_zaehlt(self):
        kaeufe = [{"insider": "A", "filing_datum": "2026-03-01", "wert": 80_000}]
        self.assertIsNotNone(self.im._cluster_at(kaeufe, "2026-03-10"))          # >= 50k -> aktiv

    def test_einzelner_kleinkauf_zaehlt_nicht(self):
        kaeufe = [{"insider": "A", "filing_datum": "2026-03-01", "wert": 5_000}]
        self.assertIsNone(self.im._cluster_at(kaeufe, "2026-03-10"))

    def test_zukuenftiges_filing_unsichtbar(self):
        kaeufe = [{"insider": "A", "filing_datum": "2026-03-01", "wert": 10_000},
                  {"insider": "B", "filing_datum": "2026-03-02", "wert": 10_000}]
        self.assertIsNone(self.im._cluster_at(kaeufe, "2026-02-15"))             # vor dem Filing -> kein Look-ahead

    def test_ausserhalb_lookback_verfaellt(self):
        kaeufe = [{"insider": "A", "filing_datum": "2026-01-01", "wert": 10_000},
                  {"insider": "B", "filing_datum": "2026-01-02", "wert": 10_000}]
        self.assertIsNone(self.im._cluster_at(kaeufe, "2026-06-01"))             # > 90 Tage her -> nicht mehr aktiv


class _InsiderStubMarket:
    """Steigende Aktien-Kurse + FLACHER Markt (SPY) + fixe Form-4-Kaeufe (Test steuert Universum ueber Patch).
    Der flache Benchmark macht das Insider-Alpha (Aktie steigt, Markt nicht) messbar."""
    def __init__(self, filings, *, start="2026-01-01", n=200, slope=1.0):
        d = date.fromisoformat(start)
        self.tage = [(d + timedelta(days=i)).isoformat() for i in range(n)]
        self.aktie = {t: 100.0 + slope * i for i, t in enumerate(self.tage)}
        self.markt = {t: 100.0 for t in self.tage}          # SPY flach -> Marktdrift = 0
        self.filings = filings
        self.cutoff = None            # simuliert "heute": Kurse nach cutoff sind noch nicht bekannt

    def _closes(self, symbol):
        src = self.markt if symbol.upper() == "SPY" else self.aktie
        return {t: c for t, c in src.items() if not self.cutoff or t <= self.cutoff}

    def insider_transactions(self, symbol, *, seit=""):
        txns = [dict(transaktion="kauf", **f) for f in self.filings if not seit or f["filing_datum"] >= seit]
        return {"ok": True, "transaktionen": txns}

    def aktie_historie_fmp(self, symbol):
        return {"ok": True, "closes": self._closes(symbol)}

    def aktie_historie(self, symbol, *, outputsize="compact"):
        return {"ok": True, "closes": self._closes(symbol)}


class TestInsiderBacktest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = LoopStore(Path(self.dir.name) / "features.jsonl")
        filings = [{"insider": "A", "filing_datum": "2026-03-02", "wert": 60_000},
                   {"insider": "B", "filing_datum": "2026-03-02", "wert": 60_000}]
        self.market = _InsiderStubMarket(filings)
        self.patcher = patch.object(insider_mod, "INSIDER_SCREEN_UNIVERSE", [{"symbol": "SOFI", "asset": "aktie"}])
        self.patcher.start()
        self.im = InsiderModel(self.market, self.store)

    def tearDown(self):
        self.patcher.stop()
        self.dir.cleanup()

    def test_backtest_nur_ab_filing_datum(self):
        r = self.im.backtest(seit="2026-01-01")
        self.assertGreater(r["auswertungen_neu"], 0)
        devs = self.store.list("inv_deviations")
        self.assertTrue(devs)
        self.assertTrue(all(d["modell_version"] == MODELL_VERSION_INSIDER for d in devs))
        self.assertTrue(all(d["backtest"] for d in devs))
        self.assertTrue(all(d["erstellt_am"] >= "2026-03-02" for d in devs))     # kein Look-ahead vor dem Filing
        self.assertTrue(all(d.get("horizont_tage") == INSIDER_HORIZONT_TAGE for d in devs))

    def test_backtest_idempotent(self):
        self.im.backtest(seit="2026-01-01")
        n1 = len(self.store.list("inv_deviations"))
        self.im.backtest(seit="2026-01-01")
        self.assertEqual(len(self.store.list("inv_deviations")), n1)            # keine Doppel-Auswertung

    def test_live_prognose_und_auswerten(self):
        # Prognose am 2026-03-05 (Cluster aktiv), faellig +30d; danach Auswertung nach Faelligkeit.
        self.market.cutoff = "2026-03-05"                     # zur Prognose-Zeit nur Kurse bis heute bekannt
        p = self.im.live_prognosen(datum="2026-03-05")
        self.assertIn("SOFI", p["erstellt"])
        fcs = [f for f in self.store.list("inv_forecasts") if f["modell_version"] == MODELL_VERSION_INSIDER]
        self.assertEqual(len(fcs), 1)
        heute = (date.fromisoformat("2026-03-05") + timedelta(days=INSIDER_HORIZONT_TAGE + 1)).isoformat()
        self.market.cutoff = heute                            # 30 Tage spaeter: Realkurs liegt vor
        a = self.im.auswerten(heute=heute)
        self.assertEqual(a["neu_bewertet"], 1)
        live_devs = [d for d in self.store.list("inv_deviations")
                     if d["modell_version"] == MODELL_VERSION_INSIDER and not d["backtest"]]
        self.assertEqual(len(live_devs), 1)
        self.assertTrue(live_devs[0]["richtungstreffer"])                        # steigende Kurse -> Richtung getroffen

    def test_ohne_cluster_keine_prognose(self):
        self.market.filings = [{"insider": "A", "filing_datum": "2026-03-02", "wert": 5_000}]   # zu klein
        p = self.im.live_prognosen(datum="2026-03-05")
        self.assertEqual(p["erstellt"], [])

    def test_marktdrift_kontrolle_alpha_und_edge(self):
        r = self.im.backtest(seit="2026-01-01")
        mk = r["markt_kontrolle"]
        self.assertEqual(mk["typ"], "insider_markt_kontrolle")
        self.assertEqual(mk["benchmark"], "SPY")
        self.assertGreater(mk["insider"]["n"], 0)
        # Aktie steigt, Markt (SPY) flach -> Insider-Wochen schlagen den Markt zu 100 %, Alpha positiv.
        self.assertEqual(mk["insider"]["schlaegt_markt_pct"], 1.0)
        self.assertGreater(mk["insider"]["alpha_schnitt_pct"], 0)
        # Basisrate existiert (alle Wochen-Fenster) und ist groesser als die Insider-Teilmenge.
        self.assertGreaterEqual(mk["basisrate"]["n"], mk["insider"]["n"])
        # Kontrolle ist per markt_kontrolle() abrufbar (Dashboard-Pfad).
        self.assertEqual(self.im.markt_kontrolle()["insider"]["n"], mk["insider"]["n"])

    def test_deviation_traegt_markt_felder(self):
        self.im.backtest(seit="2026-01-01")
        devs = [d for d in self.store.list("inv_deviations") if d["modell_version"] == MODELL_VERSION_INSIDER]
        self.assertTrue(devs)
        self.assertTrue(all("schlaegt_markt" in d and "excess_return_pct" in d for d in devs))
        self.assertTrue(all(d["schlaegt_markt"] for d in devs))          # Aktie schlaegt den flachen Markt


if __name__ == "__main__":
    unittest.main()
