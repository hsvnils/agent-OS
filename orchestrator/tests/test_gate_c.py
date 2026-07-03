"""GATE C -- Alpaca-Paper-Broker + harte Risk-Order-Pruefung + Paper-Ausfuehrungspfad (offline)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.broker import AlpacaPaperBroker
from orchestrator.investment.engine import InvestmentEngine
from orchestrator.investment.providers import MarketData
from orchestrator.investment.risk import RiskAgent
from orchestrator.investment.store import InvestmentStore


def _fake_http(method, path, body=None):
    if path == "/v2/account":
        return {"equity": "100000", "buying_power": "100000", "cash": "5000", "status": "ACTIVE"}
    if path == "/v2/positions":
        return [{"symbol": "AAPL", "qty": "10", "market_value": "1500", "unrealized_pl": "20"}]
    if path == "/v2/orders":
        return {"id": "ord-xyz", "symbol": body["symbol"], "qty": body["qty"]}
    return {}


class FakeBroker:
    def __init__(self, konto=None, verfuegbar=True):
        self._konto = konto or {"equity": "100000", "buying_power": "100000", "cash": "100000"}
        self._verf = verfuegbar
        self.orders = []

    @property
    def verfuegbar(self):
        return self._verf

    def konto(self):
        return self._konto

    def positionen(self):
        return []

    def order(self, symbol, qty, side, **kw):
        self.orders.append((symbol, qty, side))
        return {"id": "ord-1"}


class TestBroker(unittest.TestCase):
    def test_ohne_keys_inert(self):
        b = AlpacaPaperBroker("", "")
        self.assertFalse(b.verfuegbar)
        self.assertIsNone(b.konto())
        self.assertEqual(b.positionen(), [])
        self.assertIsNone(b.order("AAPL", 1, "buy"))

    def test_mit_http(self):
        b = AlpacaPaperBroker("k", "s", http=_fake_http)
        self.assertTrue(b.verfuegbar)
        self.assertEqual(b.konto()["equity"], "100000")
        self.assertEqual(b.positionen()[0]["symbol"], "AAPL")
        self.assertEqual(b.order("aapl", 5, "buy")["id"], "ord-xyz")


class TestRiskOrder(unittest.TestCase):
    def setUp(self):
        self.r = RiskAgent()

    def test_kauf_im_rahmen_ok(self):
        self.assertTrue(self.r.pruefe_order(order_wert=4000, konto_equity=100000, buying_power=100000)["ok"])

    def test_ueber_position_limit(self):
        # 5% von 100000 = 5000; 6000 > Limit
        u = self.r.pruefe_order(order_wert=6000, konto_equity=100000, buying_power=100000)
        self.assertFalse(u["ok"])
        self.assertIn("%", u["grund"])

    def test_ueber_buying_power(self):
        u = self.r.pruefe_order(order_wert=3000, konto_equity=100000, buying_power=1000)
        self.assertFalse(u["ok"])
        self.assertIn("Buying-Power", u["grund"])

    def test_verkauf_immer_ok(self):
        self.assertTrue(self.r.pruefe_order(order_wert=99999, konto_equity=1, buying_power=0, side="sell")["ok"])

    def test_kein_kurs(self):
        self.assertFalse(self.r.pruefe_order(order_wert=0, konto_equity=100000, buying_power=100000)["ok"])


class TestPaperExecution(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = InvestmentStore(Path(self.dir.name) / "inv.jsonl")
        self.broker = FakeBroker()
        self.eng = InvestmentEngine(MarketData(), self.store, broker=self.broker)
        self.eng._aktueller_preis = lambda symbol, asset="aktie": 100.0    # 100 $/Stueck

    def tearDown(self):
        self.dir.cleanup()

    def test_advisory_blockt(self):
        r = self.eng.paper_order("AAPL", 5, "buy", bestaetigt=True)
        self.assertFalse(r["ok"])
        self.assertIn("nicht 'paper'", r["hinweis"])
        self.assertEqual(self.broker.orders, [])

    def test_paper_ohne_bestaetigung_ist_vorschau(self):
        self.store.set_mode("paper")
        r = self.eng.paper_order("AAPL", 5, "buy")
        self.assertTrue(r.get("bestaetigung_noetig"))
        self.assertEqual(r["geschaetzter_wert"], 500.0)
        self.assertEqual(self.broker.orders, [])                # nichts platziert

    def test_paper_bestaetigt_platziert(self):
        self.store.set_mode("paper")
        r = self.eng.paper_order("AAPL", 5, "buy", bestaetigt=True)
        self.assertTrue(r["ok"])
        self.assertTrue(r["platziert"])
        self.assertEqual(self.broker.orders, [("AAPL", 5.0, "buy")])
        pos = self.store.list("positions")
        self.assertEqual(pos[-1]["status"], "platziert")

    def test_paper_risk_lehnt_zu_grosse_order_ab(self):
        self.store.set_mode("paper")
        # 100 Stueck * 100 $ = 10000 > 5% von 100000 (=5000) -> abgelehnt, kein Broker-Call
        r = self.eng.paper_order("AAPL", 100, "buy", bestaetigt=True)
        self.assertFalse(r["ok"])
        self.assertTrue(r["abgelehnt"])
        self.assertEqual(self.broker.orders, [])
        self.assertEqual(self.store.list("positions")[-1]["status"], "abgelehnt")

    def test_paper_ohne_broker_meldet_setup(self):
        eng = InvestmentEngine(MarketData(), self.store, broker=FakeBroker(verfuegbar=False))
        self.store.set_mode("paper")
        r = eng.paper_order("AAPL", 1, "buy", bestaetigt=True)
        self.assertFalse(r["ok"])
        self.assertIn("nicht konfiguriert", r["hinweis"])

    def test_paper_konto_ohne_keys(self):
        eng = InvestmentEngine(MarketData(), self.store, broker=FakeBroker(verfuegbar=False))
        self.assertFalse(eng.paper_konto()["ok"])


if __name__ == "__main__":
    unittest.main()
