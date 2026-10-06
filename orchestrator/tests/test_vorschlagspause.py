"""VORSCHLAGSPAUSE P1 (CEO 2026-10-06): ein Schalter stoppt systemweit alle automatischen Investment-Vorschlaege
(Telegram + LUNA-OS), das Tracking laeuft weiter; Auto-Trader pausiert mit, Paper-Stop-Loss schuetzt weiter."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from orchestrator.channels.telegram import bot
from orchestrator.investment.engine import InvestmentEngine
from orchestrator.investment.store import InvestmentStore
from orchestrator.tests.test_investment_engine import FakeMarket


class FakeApprovals:
    def __init__(self):
        self.neu = []

    def add(self, typ, payload, *, frage):
        self.neu.append((typ, payload, frage))
        return "APV-1"

    def offen(self):
        return []


class FakeNotes:
    def __init__(self):
        self.neu = []

    def enqueue(self, text, **kw):
        self.neu.append((text, kw))


class TestPause(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = InvestmentStore(Path(self.dir.name) / "log.jsonl")
        self.notiz = []
        self.eng = InvestmentEngine(FakeMarket(), self.store, notify=lambda *a, **k: self.notiz.append(a))
        self.ctx = SimpleNamespace(investment=self.eng, approvals=FakeApprovals(), notifications=FakeNotes())

    def tearDown(self):
        self.dir.cleanup()

    def test_1_store_und_engine(self):
        self.assertEqual(self.store.pause_info()["pausiert"], False)
        self.assertTrue(self.eng.vorschlag("AAA", aktion="beobachten", grund="vorher", veraenderung_pct=10, konfidenz=0.6)["ok"])
        self.store.set_setting("vorschlaege_pausiert", True, akteur="CEO")
        r = self.eng.vorschlag("BBB", aktion="beobachten", grund="Bewegung", veraenderung_pct=10, konfidenz=0.6)
        self.assertEqual((r["ok"], r.get("pausiert")), (False, True))
        self.assertEqual(len(self.store.list("suggestions")), 1)                      # kein neuer Vorschlag
        self.assertEqual(len(self.notiz), 1)                                           # keine neue Meldung
        p = self.store.pause_info()
        self.assertEqual((p["pausiert"], p["von"], p["unterdrueckt"]), (True, "CEO", 1))
        self.assertIn("BBB", p["letzte"][0]["text"])
        self.store.set_setting("vorschlaege_pausiert", False)
        self.assertTrue(self.eng.vorschlag("CCC", aktion="beobachten", grund="danach", veraenderung_pct=10, konfidenz=0.6)["ok"])
        self.assertEqual(self.store.pause_info()["unterdrueckt"], 0)

    def test_2_bot_freigaben_depot_und_autotrader(self):
        self.assertEqual(bot._auto_freigabe(self.ctx, "monitor", {"symbol": "X"}, "Kaufen?"), "APV-1")
        self.store.set_setting("vorschlaege_pausiert", True)
        self.assertIsNone(bot._auto_freigabe(self.ctx, "take-profit", {"symbol": "Y"}, "Gewinn mitnehmen?"))
        self.assertEqual(len(self.ctx.approvals.neu), 1)                               # nur die von vorher
        self.assertEqual(self.store.pause_info()["unterdrueckt"], 1)
        bot._real_depot_monitor_tick(self.ctx, self.eng)                               # Echtdepot-Hinweise ruhen
        self.assertEqual(self.ctx.notifications.neu, [])
        with mock.patch.object(self.eng, "paper_konto", return_value={"konto": {"equity": 1000, "last_equity": 1000}}):
            fc = SimpleNamespace(live_gesamt=lambda: {"n": 0})
            k = bot._autonomie_kontext(self.eng, fc, None, "2026-10-06")
        self.assertTrue(k["kill_switch"])                                              # Auto-Trader pausiert mit
        self.store.set_setting("vorschlaege_pausiert", False)
        with mock.patch.object(self.eng, "paper_konto", return_value={"konto": {"equity": 1000, "last_equity": 1000}}):
            self.assertFalse(bot._autonomie_kontext(self.eng, fc, None, "2026-10-06")["kill_switch"])


class TestPauseWeb(unittest.TestCase):
    """Echte Repo-Daten werden nie angefasst (Store und Changelog umgelenkt, wie test_investment_settings)."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        self.w = webapp
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = (webapp.inv_store, webapp._changelog)
        webapp.inv_store = InvestmentStore(Path(self._tmp.name) / "log.jsonl")
        webapp._changelog = lambda *a, **k: None
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.inv_store, self.w._changelog = self._orig
        self._tmp.cleanup()

    def test_3_schalter_und_glocke(self):
        apv = [{"id": "APV-20991231-101500-ab12", "frage": "NVDA kaufen?", "ts": "2099-12-31T10:15:00", "status": "offen"}]
        with mock.patch("orchestrator.investment.approvals.ApprovalStore.offen", return_value=apv):
            vorher = [p["id"] for p in self.c.get("/api/handlungsbedarf").json()["punkte"]]
            self.assertIn("investment-freigaben", vorher)
            r = self.c.post("/api/settings", json={"vorschlaege_pausiert": True}).json()
            self.assertTrue(r["ok"], r)
            self.assertTrue(self.c.get("/api/investment/pause").json()["pausiert"])
            nachher = [p["id"] for p in self.c.get("/api/handlungsbedarf").json()["punkte"]]
            self.assertNotIn("investment-freigaben", nachher)                         # Glocke ohne Investment
            self.c.post("/api/settings", json={"vorschlaege_pausiert": "false"})
            self.assertFalse(self.c.get("/api/investment/pause").json()["pausiert"])


class TestAnbieter(unittest.TestCase):
    """P2: Anbieter-Liste -- nie Schluesselwerte, Stand je Anbieter, Doku-Check gegen Veralten."""

    GEHEIM = "sk-test-1234567890abcdef"

    def test_4_liste_ohne_werte(self):
        from orchestrator.governance.dienste_register import ANBIETER, anbieter
        liste = anbieter({"FINNHUB_API_KEY": self.GEHEIM, "ALPACA_API_KEY": self.GEHEIM})
        self.assertNotIn(self.GEHEIM, str(liste))
        st = {a["id"]: a["stand"] for a in liste}
        self.assertEqual((st["finnhub"], st["alpaca"], st["fmp"], st["ezb"]),
                         ("eingerichtet", "teilweise", "nicht eingerichtet", "ohne Zugang"))
        inv = {a["id"] for a in ANBIETER if a["bereich"] == "Investment"}
        self.assertEqual(inv, {"finnhub", "fmp", "alphavantage", "coingecko", "sec", "alpaca"})

    def test_5_endpunkt_und_rechte(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        c = TestClient(webapp.app)
        with mock.patch.object(webapp, "_google_secrets", return_value={"BRAVE_API_KEY": self.GEHEIM}):
            r = c.get("/api/anbieter")
            self.assertEqual(r.status_code, 200)
            self.assertNotIn(self.GEHEIM, r.text)
            brave = next(a for a in r.json()["anbieter"] if a["id"] == "brave")
            self.assertEqual((brave["stand"], brave["kann_kosten"]), ("eingerichtet", True))
            self.assertEqual({a["bereich"] for a in c.get("/api/anbieter?bereich=Investment").json()["anbieter"]}, {"Investment"})
            with mock.patch.object(webapp, "hat_modul", side_effect=lambda u, m: m == "invest"):
                self.assertEqual(c.get("/api/anbieter").status_code, 403)              # Gesamtliste nur fuer den CEO
                self.assertEqual(c.get("/api/anbieter?bereich=Investment").status_code, 200)

    def test_6_doku_check_meldet_neuen_anbieter(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("doku_check", Path(__file__).resolve().parents[2] / "scripts" / "doku_check.py")
        dc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dc)
        self.assertEqual(dc.pruefe_anbieter(), [])
        with tempfile.TemporaryDirectory() as d:
            neu = Path(d) / "neu.py"
            neu.write_text('KEY = secrets.get("NEUERDIENST_API_KEY")\n', encoding="utf-8")
            with mock.patch.object(dc, "_code_dateien", return_value=[neu]), mock.patch.object(dc, "ROOT", Path(d)):
                f = [x for x in dc.pruefe_anbieter() if "NEUERDIENST" in x]
        self.assertEqual(len(f), 1)



if __name__ == "__main__":
    unittest.main()
