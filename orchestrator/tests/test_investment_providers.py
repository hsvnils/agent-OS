import unittest

from orchestrator.investment.providers import MarketData, PROVIDERS


class FakeFetch:
    """Injizierbarer HTTP-Ersatz -- liefert aufgezeichnete Antworten nach URL-Substring (kein Netz)."""
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, url, headers=None, timeout=15):
        self.calls.append((url, headers))
        for key, val in self.mapping.items():
            if key in url:
                return val
        raise AssertionError("Unerwartete URL: " + url)


class TestProviders(unittest.TestCase):
    def test_provider_status_ohne_keys(self):
        md = MarketData(secrets={})
        st = {p["name"]: p for p in md.provider_status()}
        self.assertTrue(st["CoinGecko"]["konfiguriert"])       # keyless
        self.assertFalse(st["Finnhub"]["konfiguriert"])         # braucht Key
        self.assertFalse(st["SEC EDGAR"]["konfiguriert"])       # braucht User-Agent

    def test_fehlende_keys(self):
        md = MarketData(secrets={})
        fehlen = {p["name"] for p in md.fehlende_keys()}
        # CoinGecko keyless -> nicht in der Liste; die anderen schon
        self.assertNotIn("CoinGecko", fehlen)
        self.assertSetEqual(fehlen, {"SEC EDGAR", "Finnhub", "Alpha Vantage", "FMP"})

    def test_fall_b_ohne_key(self):
        md = MarketData(secrets={})
        r = md.aktie_quote("AAPL")
        self.assertFalse(r["ok"])
        self.assertTrue(r["fall_b"])
        self.assertIn("FINNHUB_API_KEY", r["hinweis"])

    def test_crypto_keyless_normalisiert(self):
        fetch = FakeFetch({"simple/price": {"bitcoin": {"eur": 60000, "eur_24h_change": 2.5}}})
        md = MarketData(secrets={}, fetch=fetch)
        r = md.crypto_preis(["bitcoin"], vs="eur")
        self.assertTrue(r["ok"])
        self.assertEqual(r["preise"]["bitcoin"]["eur"], 60000)

    def test_finnhub_mit_key_normalisiert(self):
        fetch = FakeFetch({"finnhub.io": {"c": 190.5, "dp": 1.8, "h": 192, "l": 188}})
        md = MarketData(secrets={"FINNHUB_API_KEY": "abc"}, fetch=fetch)
        r = md.aktie_quote("AAPL")
        self.assertTrue(r["ok"])
        self.assertEqual(r["preis"], 190.5)
        self.assertEqual(r["veraenderung_pct"], 1.8)
        # Key landet als token im URL, nicht im Ergebnis
        self.assertNotIn("abc", str(r))

    def test_fmp_screener(self):
        fetch = FakeFetch({"gainers": [{"symbol": "XYZ", "name": "Xyz Inc", "changesPercentage": 12.3}]})
        md = MarketData(secrets={"FMP_API_KEY": "k"}, fetch=fetch)
        r = md.screener_gewinner()
        self.assertTrue(r["ok"])
        self.assertEqual(r["gewinner"][0]["symbol"], "XYZ")

    def test_sec_edgar_braucht_user_agent(self):
        md = MarketData(secrets={})
        self.assertTrue(md.filings("320193")["fall_b"])
        fetch = FakeFetch({"data.sec.gov": {"name": "Apple Inc."}})
        md2 = MarketData(secrets={"SEC_EDGAR_USER_AGENT": "Hanserautisch contact@example.com"}, fetch=fetch)
        r = md2.filings("320193")
        self.assertTrue(r["ok"])
        self.assertEqual(r["name"], "Apple Inc.")

    def test_suche_aktie_und_krypto(self):
        fetch = FakeFetch({
            "finnhub.io": {"result": [{"symbol": "AAPL", "description": "APPLE INC"},
                                      {"symbol": "AAPL.SW", "description": "Apple Schweiz"}]},
            "coingecko.com": {"coins": [{"id": "apecoin", "name": "ApeCoin", "symbol": "ape"}]},
        })
        md = MarketData(secrets={"FINNHUB_API_KEY": "k"}, fetch=fetch)
        r = md.suche("ap")
        paare = {(t["symbol"], t["asset"]) for t in r["treffer"]}
        self.assertIn(("AAPL", "aktie"), paare)
        self.assertNotIn(("AAPL.SW", "aktie"), paare)   # Symbole mit Punkt werden gefiltert
        self.assertIn(("apecoin", "krypto"), paare)     # Krypto-symbol = CoinGecko-ID

    def test_suche_leer(self):
        self.assertEqual(MarketData(secrets={}).suche("")["treffer"], [])

    def test_alle_provider_haben_url(self):
        for p in PROVIDERS:
            self.assertTrue(p["url"].startswith("http"))


if __name__ == "__main__":
    unittest.main()
