import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.broker import alpaca_krypto_symbol
from orchestrator.investment.engine import InvestmentEngine
from orchestrator.investment.providers import MarketData
from orchestrator.investment.store import InvestmentStore


class _FakeBroker:
    verfuegbar = True

    def __init__(self):
        self.orders = []

    def konto(self):
        return {"equity": 100000.0, "buying_power": 400000.0}

    def positionen(self):
        return []

    def order(self, symbol, qty, side, *, typ="market", time_in_force="day"):
        self.orders.append({"symbol": symbol, "qty": qty, "side": side, "tif": time_in_force})
        return {"id": "ord-1"}


class TestKryptoSymbol(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(alpaca_krypto_symbol("bitcoin"), "BTC/USD")
        self.assertEqual(alpaca_krypto_symbol("ETHEREUM"), "ETH/USD")

    def test_unbekannt_none(self):
        self.assertIsNone(alpaca_krypto_symbol("cardano"))
        self.assertIsNone(alpaca_krypto_symbol(""))


class _StubMarketUSD:
    def crypto_preis(self, ids, vs="eur"):
        return {"ok": True, "preise": {ids[0]: {"usd": 60000.0}}}


class TestKryptoUsdResolve(unittest.TestCase):
    def setUp(self):
        self.eng = InvestmentEngine(_StubMarketUSD(), InvestmentStore("/tmp/_x.jsonl"))

    def test_coingecko_id(self):
        self.assertEqual(self.eng.krypto_usd("bitcoin"), ("BTC/USD", 60000.0))

    def test_ticker(self):
        self.assertEqual(self.eng.krypto_usd("BTC"), ("BTC/USD", 60000.0))

    def test_alpaca_symbol(self):
        self.assertEqual(self.eng.krypto_usd("BTC/USD"), ("BTC/USD", 60000.0))

    def test_unbekannt(self):
        self.assertEqual(self.eng.krypto_usd("cardano"), (None, 0.0))


class TestPaperOrderPreisUndTif(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = InvestmentStore(Path(self.dir.name) / "log.jsonl")
        self.store.set_mode("paper")
        self.broker = _FakeBroker()
        self.eng = InvestmentEngine(_StubMarketUSD(), self.store, broker=self.broker)

    def test_krypto_order_per_coingecko_id_wird_aufgeloest(self):
        r = self.eng.paper_order("bitcoin", 0.001, "buy", asset="krypto", bestaetigt=True)
        self.assertTrue(r["ok"])
        self.assertEqual(self.broker.orders[0]["symbol"], "BTC/USD")   # aufgeloest
        self.assertEqual(self.broker.orders[0]["tif"], "gtc")
        self.assertEqual(r["geschaetzter_wert"], 60.0)                 # 0.001 * 60000

    def tearDown(self):
        self.dir.cleanup()

    def test_krypto_order_nutzt_preis_und_gtc(self):
        r = self.eng.paper_order("BTC/USD", 0.01, "buy", asset="krypto", bestaetigt=True, preis=60000.0)
        self.assertTrue(r["ok"])
        self.assertEqual(self.broker.orders[0]["tif"], "gtc")        # Krypto = gtc
        self.assertEqual(self.broker.orders[0]["symbol"], "BTC/USD")
        self.assertEqual(r["geschaetzter_wert"], 600.0)              # 0.01 * 60000 aus vorgegebenem Preis

    def test_aktie_order_nutzt_day(self):
        r = self.eng.paper_order("AAPL", 1, "buy", asset="aktie", bestaetigt=True, preis=150.0)
        self.assertTrue(r["ok"])
        self.assertEqual(self.broker.orders[0]["tif"], "day")


if __name__ == "__main__":
    unittest.main()
