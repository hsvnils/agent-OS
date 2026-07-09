"""Tests fuer die Depot-Ansichten (Paper + echtes Depot) und den real_depot-Store."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.portfolio import paper_portfolio, real_portfolio, normalisiere_position
from orchestrator.investment.store import InvestmentStore


class FakeBroker:
    def __init__(self, verfuegbar=True, konto=None, positionen=None):
        self.verfuegbar = verfuegbar
        self._konto = konto or {}
        self._pos = positionen or []

    def konto(self):
        return self._konto

    def positionen(self):
        return self._pos


class FakeMarket:
    def aktie_quote(self, symbol):
        return {"ok": True, "preis": 200.0} if symbol == "AAPL" else {"ok": False}

    def crypto_preis(self, ids, vs="usd"):
        return {"ok": True, "preise": {"bitcoin": {"usd": 50000.0}}}


PAPER_POS = [
    {"symbol": "AAPL", "asset_class": "us_equity", "qty": "10", "avg_entry_price": "100",
     "cost_basis": "1000", "current_price": "110", "market_value": "1100",
     "unrealized_pl": "100", "unrealized_plpc": "0.10", "change_today": "0.02"},
    {"symbol": "SPY", "asset_class": "us_equity", "qty": "5", "avg_entry_price": "400",
     "cost_basis": "2000", "current_price": "420", "market_value": "2100",
     "unrealized_pl": "100", "unrealized_plpc": "0.05", "change_today": "0.01"},
    {"symbol": "BTC/USD", "asset_class": "crypto", "qty": "0.1", "avg_entry_price": "40000",
     "cost_basis": "4000", "current_price": "50000", "market_value": "5000",
     "unrealized_pl": "1000", "unrealized_plpc": "0.25", "change_today": "0.03"},
]
KONTO = {"equity": "12345", "cash": "5000", "buying_power": "10000",
         "long_market_value": "8200", "last_equity": "12000", "currency": "USD"}


class TestPaperPortfolio(unittest.TestCase):
    def test_inert_ohne_broker(self):
        pf = paper_portfolio(None)
        self.assertFalse(pf["verfuegbar"])
        self.assertEqual(pf["positionen"], [])

    def test_inert_ohne_keys(self):
        pf = paper_portfolio(FakeBroker(verfuegbar=False))
        self.assertFalse(pf["verfuegbar"])

    def test_normalisierung_und_klassen(self):
        pf = paper_portfolio(FakeBroker(konto=KONTO, positionen=PAPER_POS))
        self.assertTrue(pf["verfuegbar"])
        self.assertEqual(pf["konto"]["gesamtwert"], 12345.0)
        self.assertEqual(pf["konto"]["tag_abs"], 345.0)
        klassen = {p["symbol"]: p["klasse"] for p in pf["positionen"]}
        self.assertEqual(klassen["AAPL"], "aktie")
        self.assertEqual(klassen["SPY"], "etf")     # bekannte ETF wird getrennt
        self.assertEqual(klassen["BTC/USD"], "krypto")
        # nach Wert absteigend sortiert
        werte = [p["wert"] for p in pf["positionen"]]
        self.assertEqual(werte, sorted(werte, reverse=True))
        self.assertEqual(set(pf["gruppen"].keys()), {"aktie", "etf", "krypto"})
        self.assertAlmostEqual(pf["gruppen"]["krypto"]["gv_abs"], 1000.0)

    def test_gv_prozent_skalierung(self):
        p = normalisiere_position(PAPER_POS[0])
        self.assertAlmostEqual(p["gv_pct"], 10.0)   # 0.10 -> 10 %
        self.assertAlmostEqual(p["tag_pct"], 2.0)


class TestRealPortfolio(unittest.TestCase):
    def test_bewertung_und_unbewertet(self):
        holdings = [
            {"id": "1", "symbol": "AAPL", "klasse": "aktie", "stueck": 5, "einstand_preis": 100, "kurs_id": "AAPL"},
            {"id": "2", "symbol": "BTC", "klasse": "krypto", "stueck": 0.1, "einstand_preis": 40000, "kurs_id": "bitcoin"},
            {"id": "3", "symbol": "XYZ", "klasse": "aktie", "stueck": 10, "einstand_preis": 5, "kurs_id": "XYZ"},
        ]
        dp = real_portfolio(holdings, FakeMarket())
        pos = {p["symbol"]: p for p in dp["positionen"]}
        self.assertAlmostEqual(pos["AAPL"]["wert"], 1000.0)
        self.assertAlmostEqual(pos["AAPL"]["gv_abs"], 500.0)
        self.assertAlmostEqual(pos["BTC"]["wert"], 5000.0)
        self.assertAlmostEqual(pos["BTC"]["gv_abs"], 1000.0)
        self.assertIsNone(pos["XYZ"]["wert"])         # kein Kurs -> unbewertet
        self.assertEqual(dp["summe"]["unbewertet"], 1)
        self.assertAlmostEqual(dp["summe"]["gesamtwert"], 6000.0)
        self.assertAlmostEqual(dp["summe"]["gv_abs"], 1500.0)

    def test_leeres_depot(self):
        dp = real_portfolio([], FakeMarket())
        self.assertEqual(dp["positionen"], [])
        self.assertEqual(dp["summe"]["gesamtwert"], 0)


class TestRealDepotStore(unittest.TestCase):
    def test_add_remove_fold(self):
        with tempfile.TemporaryDirectory() as d:
            st = InvestmentStore(Path(d) / "log.jsonl")
            rid = st.real_add("AAPL", klasse="aktie", stueck=5, einstand_preis=100)
            st.real_add("BTC", klasse="krypto", stueck=0.1, einstand_preis=40000, kurs_id="bitcoin")
            self.assertEqual(len(st.real_holdings()), 2)
            st.real_remove(rid)
            hold = st.real_holdings()
            self.assertEqual(len(hold), 1)
            self.assertEqual(hold[0]["symbol"], "BTC")
            self.assertEqual(hold[0]["kurs_id"], "bitcoin")


if __name__ == "__main__":
    unittest.main()
