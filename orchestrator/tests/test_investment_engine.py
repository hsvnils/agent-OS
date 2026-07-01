import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.engine import InvestmentEngine
from orchestrator.investment.risk import RiskAgent
from orchestrator.investment.store import InvestmentStore


class FakeMarket:
    """Mock-MarketData fuer die Engine-Tests (kein Netz)."""
    def __init__(self, gainers=None, crypto=None, quote=None, price=100, insider=None):
        self._gainers = gainers
        self._crypto = crypto
        self._quote = quote
        self._price = price
        self._insider = insider   # dict symbol->antwort, oder None = Fall-B (kein Finnhub-Key)

    def provider_status(self):
        return [{"name": "FMP", "konfiguriert": True}]

    def fehlende_keys(self):
        return []

    def screener_gewinner(self):
        return {"ok": True, "provider": "FMP", "gewinner": self._gainers} if self._gainers is not None \
            else {"ok": False, "fall_b": True, "hinweis": "FMP nicht konfiguriert -- FMP_API_KEY noetig."}

    def crypto_preis(self, ids, vs="eur"):
        return {"ok": True, "provider": "CoinGecko", "preise": self._crypto or {}}

    def aktie_quote(self, symbol):
        return {"ok": True, "preis": self._price, "veraenderung_pct": (self._quote or {}).get(symbol, 0.0)}

    def aktie_profil(self, symbol):
        return {"ok": True, "name": symbol + " Inc.", "branche": "Tech", "boerse": "NASDAQ"}

    def aktie_news(self, symbol, von="", bis="", limit=3):
        return {"ok": True, "news": [{"titel": "Headline", "quelle": "Reuters", "url": "http://x"}]}

    def aktie_rsi(self, symbol):
        return {"wert": 55.0, "label": "neutral", "stand": "2026-06-28"}

    def crypto_detail(self, coin_id):
        return {"ok": True, "name": coin_id.title(), "symbol": coin_id[:3].upper(), "preis_eur": 50000,
                "veraenderung_pct": 1.2, "beschreibung": "Eine Kryptowaehrung."}

    def insider_transactions(self, symbol, seit=""):
        if self._insider is None:
            return {"ok": False, "fall_b": True,
                    "hinweis": "Finnhub nicht konfiguriert -- FINNHUB_API_KEY noetig."}
        return self._insider.get(symbol, {"ok": True, "transaktionen": [], "quelle": "SEC Form 4",
                                          "filing_url": "http://sec.gov/x"})


class TestRiskAgent(unittest.TestCase):
    def test_konservativ_vs_spekulativ(self):
        r = RiskAgent()
        self.assertEqual(r.pruefe({"veraenderung_pct": 3, "konfidenz": 0.6})["label"], "konservativ")
        self.assertEqual(r.pruefe({"veraenderung_pct": 40, "konfidenz": 0.6})["label"], "spekulativ")

    def test_krypto_immer_spekulativ(self):
        self.assertEqual(RiskAgent().pruefe({"asset": "krypto", "veraenderung_pct": 1, "konfidenz": 0.7})["label"],
                         "spekulativ")

    def test_veto_bei_extrem(self):
        self.assertEqual(RiskAgent().pruefe({"veraenderung_pct": 120, "konfidenz": 0.9})["entscheidung"], "veto")

    def test_nachschaerfung_bei_niedriger_konfidenz(self):
        self.assertEqual(RiskAgent().pruefe({"veraenderung_pct": 5, "konfidenz": 0.2})["entscheidung"],
                         "nachschaerfung")


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = InvestmentStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def _engine(self, **kw):
        return InvestmentEngine(FakeMarket(**kw), self.store)

    def test_markt_screen_sortiert_und_speichert(self):
        eng = self._engine(
            gainers=[{"symbol": "AAA", "name": "A", "veraenderung_pct": 12.0},
                     {"symbol": "BBB", "name": "B", "veraenderung_pct": 30.0}],
            crypto={"bitcoin": {"eur": 50000, "eur_24h_change": -8.0}})
        r = eng.markt_screen()
        self.assertTrue(r["ok"])
        self.assertEqual(r["shortlist"][0]["symbol"], "BBB")   # groesste Bewegung zuerst
        self.assertEqual(len(self.store.list("screening")), 1)

    def test_vorschlag_durch_risk_freigegeben(self):
        eng = self._engine()
        r = eng.vorschlag("AAA", aktion="beobachten", grund="Test", veraenderung_pct=10, konfidenz=0.6)
        self.assertTrue(r["ok"])
        self.assertEqual(r["urteil"]["label"], "konservativ")
        self.assertEqual(len(self.store.list("suggestions")), 1)

    def test_vorschlag_veto_kein_store(self):
        eng = self._engine()
        r = eng.vorschlag("ZZZ", aktion="kaufen", grund="Extrem", veraenderung_pct=150, konfidenz=0.9)
        self.assertFalse(r["ok"])
        self.assertEqual(r["entscheidung"], "veto")
        self.assertEqual(len(self.store.list("suggestions")), 0)   # nichts gespeichert

    def test_screen_und_vorschlagen_nutzt_risk_gate(self):
        eng = self._engine(
            gainers=[{"symbol": "AAA", "name": "A", "veraenderung_pct": 9.0},      # -> Vorschlag
                     {"symbol": "EXT", "name": "E", "veraenderung_pct": 95.0}],     # -> Risk-Veto
            crypto={})
        r = eng.screen_und_vorschlagen(schwelle_pct=5.0)
        erstellt = {x["symbol"] for x in r["erstellt"]}
        abgelehnt = {x["symbol"] for x in r["vom_risk_abgelehnt"]}
        self.assertIn("AAA", erstellt)
        self.assertIn("EXT", abgelehnt)   # vom Risk-Agent geblockt

    def test_screen_fall_b_ohne_fmp_key(self):
        eng = self._engine(gainers=None, crypto={"bitcoin": {"eur": 50000, "eur_24h_change": 5.0}})
        r = eng.markt_screen()
        self.assertTrue(r["ok"])  # Krypto liefert trotzdem
        self.assertTrue(any("FMP" in h for h in r["hinweise"]))

    def test_detail_aktie_und_krypto(self):
        eng = self._engine(quote={"AAA": 2.0})
        da = eng.detail("AAA", "aktie")
        self.assertEqual(da["asset"], "aktie")
        self.assertEqual(da["profil"]["name"], "AAA Inc.")
        self.assertTrue(da["news"])
        dk = eng.detail("bitcoin", "krypto")
        self.assertEqual(dk["asset"], "krypto")
        self.assertTrue(dk["info"]["ok"])

    def test_scorecard_walkforward(self):
        from datetime import datetime, timedelta
        eng = InvestmentEngine(FakeMarket(price=110), self.store)
        self.store.forecast_add("AAA", prognose="steigt", konfidenz=0.6, horizont="1W",
                                basis_preis=100, asset="aktie")
        # vor Ablauf des Horizonts: keine Auswertung
        r0 = eng.scorecard_aktualisieren(jetzt=datetime.now() + timedelta(days=1))
        self.assertEqual(r0["neu_bewertet"], 0)
        # nach Ablauf: +10% (110 vs 100) -> "steigt" Treffer
        r1 = eng.scorecard_aktualisieren(jetzt=datetime.now() + timedelta(days=8))
        self.assertEqual(r1["neu_bewertet"], 1)
        self.assertEqual(r1["scorecard"]["trefferquote"], 1.0)
        # idempotent: kein doppeltes Auswerten
        r2 = eng.scorecard_aktualisieren(jetzt=datetime.now() + timedelta(days=9))
        self.assertEqual(r2["neu_bewertet"], 0)

    def test_insider_scan_cluster_und_alert(self):
        meldungen, gemerkt = [], []
        insider = {"XYZ": {"ok": True, "quelle": "SEC Form 4", "filing_url": "http://sec.gov/xyz",
                   "transaktionen": [
                       {"insider": "Doe", "rolle": "CEO", "transaktion": "kauf", "wert": 60000, "datum": "2026-06-20"},
                       {"insider": "Roe", "rolle": "CFO", "transaktion": "kauf", "wert": 40000, "datum": "2026-06-21"},
                       {"insider": "Sam", "rolle": "VP", "transaktion": "verkauf", "wert": 5000, "datum": "2026-06-22"},
                   ]}}
        eng = InvestmentEngine(FakeMarket(insider=insider), self.store,
                               notify=lambda text, **kw: meldungen.append(text),
                               brain=lambda text, **kw: gemerkt.append(text))
        r = eng.insider_scan(symbols=["XYZ"])
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["signale"]), 1)
        self.assertEqual(r["signale"][0]["cluster"], 2)          # nur die 2 KAUFENDEN Insider zaehlen
        self.assertEqual(r["signale"][0]["summe"], 100000.0)
        self.assertTrue(r["signale"][0]["alert"])
        self.assertEqual(len(self.store.list("insider_signals")), 1)
        self.assertEqual(len(self.store.list("suggestions")), 1)  # Risk-freigegebener Alert -> Vorschlag
        self.assertTrue(meldungen and "XYZ" in meldungen[0])
        self.assertTrue(gemerkt and "XYZ" in gemerkt[0])
        self.assertIn("sec.gov", self.store.list("insider_signals")[0]["filing_url"])

    def test_insider_scan_unauffaellig_kein_signal(self):
        insider = {"AAA": {"ok": True, "quelle": "SEC Form 4", "filing_url": "http://x",
                   "transaktionen": [{"insider": "Solo", "rolle": "VP", "transaktion": "kauf",
                                      "wert": 1000, "datum": "2026-06-20"}]}}
        eng = InvestmentEngine(FakeMarket(insider=insider), self.store)
        r = eng.insider_scan(symbols=["AAA"])   # 1 Insider + kleiner Betrag -> unter Schwelle
        self.assertEqual(len(r["signale"]), 0)
        self.assertEqual(len(self.store.list("insider_signals")), 0)

    def test_insider_scan_fall_b_ohne_key(self):
        eng = InvestmentEngine(FakeMarket(insider=None), self.store)
        r = eng.insider_scan(symbols=["AAA"])
        self.assertEqual(len(r["signale"]), 0)
        self.assertTrue(any("FINNHUB" in h for h in r["hinweise"]))

    def test_wochenprognose_und_scorecard(self):
        self.store.watchlist_add("AAA")
        eng = self._engine(quote={"AAA": 3.0})
        p = eng.wochenprognose()
        self.assertEqual(p["prognosen"][0]["prognose"], "steigt")
        # actual passend -> Treffer
        fid = self.store.list("forecasts")[0]["id"]
        self.store.actual_add("AAA", wert=2.0, bezug_forecast=fid)
        sc = eng.scorecard()
        self.assertEqual(sc["ausgewertet"], 1)
        self.assertEqual(sc["treffer"], 1)


if __name__ == "__main__":
    unittest.main()
