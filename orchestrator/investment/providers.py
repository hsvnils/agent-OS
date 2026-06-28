"""Investment-Datenanbindung (Phase 1) -- Capability-Muster, Multi-Provider, leck-/kosten-bewusst.

Jeder Provider braucht ggf. einen **gratis** API-Key (Capability ueber `.env`). Ohne Key liefert die jeweilige
Methode ein **Fall-B-Ergebnis** (`{"ok": False, "fall_b": True, "hinweis": ...}`) -- nie ein Crash, nie Kosten.
CoinGecko + SEC EDGAR funktionieren keyless (SEC braucht nur einen Kontakt-User-Agent). Der HTTP-Aufruf ist
**injizierbar**, damit Self-Checks ohne Netz/Keys gegen aufgezeichnete Mock-Daten laufen.

Keine Trades, keine Geldbewegungen -- nur Lesen von Marktdaten.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

# name · .env-Key · keyless? · Zweck · Anbieter-URL (zum Key-Besorgen)
PROVIDERS = [
    {"name": "CoinGecko", "key": "COINGECKO_API_KEY", "keyless": True,
     "zweck": "Krypto-Kurse (nahe-Echtzeit)", "url": "https://www.coingecko.com/en/api"},
    {"name": "SEC EDGAR", "key": "SEC_EDGAR_USER_AGENT", "keyless": False,
     "zweck": "US-Filings (braucht Kontakt-User-Agent, kostenlos)",
     "url": "https://www.sec.gov/os/accessing-edgar-data"},
    {"name": "Finnhub", "key": "FINNHUB_API_KEY", "keyless": False,
     "zweck": "Aktien-Quotes/News/Sentiment", "url": "https://finnhub.io/register"},
    {"name": "Alpha Vantage", "key": "ALPHAVANTAGE_API_KEY", "keyless": False,
     "zweck": "Technische Indikatoren (RSI/MACD/...)", "url": "https://www.alphavantage.co/support/#api-key"},
    {"name": "FMP", "key": "FMP_API_KEY", "keyless": False,
     "zweck": "Screener/Gewinner-Listen/Fundamentals", "url": "https://site.financialmodelingprep.com/developer/docs"},
]


def _http_json(url: str, headers: dict | None = None, timeout: int = 15):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


class MarketData:
    """Fassade ueber die Daten-Provider. `secrets` = geparste .env (Key->Wert). `fetch` injizierbar (Tests)."""

    def __init__(self, secrets: dict | None = None, *, fetch=None):
        self.secrets = secrets or {}
        self._fetch = fetch or _http_json

    def _key(self, env: str) -> str:
        return (self.secrets.get(env) or "").strip()

    def provider_status(self) -> list[dict]:
        out = []
        for p in PROVIDERS:
            has = bool(self._key(p["key"]))
            out.append({"name": p["name"], "key_env": p["key"], "keyless": p["keyless"],
                        "konfiguriert": has or p["keyless"], "zweck": p["zweck"], "url": p["url"]})
        return out

    def fehlende_keys(self) -> list[dict]:
        """Provider, die noch einen (gratis) Key brauchen -- fuer GATE B."""
        return [{"name": p["name"], "key_env": p["key"], "url": p["url"], "zweck": p["zweck"]}
                for p in PROVIDERS if not p["keyless"] and not self._key(p["key"])]

    @staticmethod
    def _fallb(name: str, env: str) -> dict:
        return {"ok": False, "fall_b": True, "provider": name,
                "hinweis": f"{name} nicht konfiguriert -- gratis API-Key/Wert {env} in .env noetig "
                           "(CTO provisioniert, CISO-Freigabe; CEO-Tor fuer neue Dienste)."}

    # ---- CoinGecko (keyless) -------------------------------------------------
    def crypto_preis(self, ids, vs: str = "eur") -> dict:
        ids_s = ",".join(ids) if isinstance(ids, (list, tuple)) else str(ids)
        key = self._key("COINGECKO_API_KEY")
        url = ("https://api.coingecko.com/api/v3/simple/price?ids="
               f"{urllib.parse.quote(ids_s)}&vs_currencies={urllib.parse.quote(vs)}&include_24hr_change=true")
        headers = {"x-cg-demo-api-key": key} if key else {}
        try:
            data = self._fetch(url, headers=headers)
        except Exception as exc:
            return {"ok": False, "provider": "CoinGecko", "fehler": str(exc)[:160]}
        return {"ok": True, "provider": "CoinGecko", "preise": data}

    # ---- Finnhub (key) ------------------------------------------------------
    def aktie_quote(self, symbol: str) -> dict:
        key = self._key("FINNHUB_API_KEY")
        if not key:
            return self._fallb("Finnhub", "FINNHUB_API_KEY")
        url = f"https://finnhub.io/api/v1/quote?symbol={urllib.parse.quote(symbol)}&token={key}"
        try:
            d = self._fetch(url)
        except Exception as exc:
            return {"ok": False, "provider": "Finnhub", "fehler": str(exc)[:160]}
        return {"ok": True, "provider": "Finnhub", "symbol": symbol.upper(),
                "preis": d.get("c"), "veraenderung_pct": d.get("dp"), "hoch": d.get("h"), "tief": d.get("l")}

    # ---- Alpha Vantage (key) ------------------------------------------------
    def indikator(self, symbol: str, indicator: str = "RSI", interval: str = "daily",
                  time_period: int = 14, series_type: str = "close") -> dict:
        key = self._key("ALPHAVANTAGE_API_KEY")
        if not key:
            return self._fallb("Alpha Vantage", "ALPHAVANTAGE_API_KEY")
        url = (f"https://www.alphavantage.co/query?function={urllib.parse.quote(indicator)}"
               f"&symbol={urllib.parse.quote(symbol)}&interval={interval}&time_period={time_period}"
               f"&series_type={series_type}&apikey={key}")
        try:
            d = self._fetch(url)
        except Exception as exc:
            return {"ok": False, "provider": "Alpha Vantage", "fehler": str(exc)[:160]}
        return {"ok": True, "provider": "Alpha Vantage", "symbol": symbol.upper(),
                "indikator": indicator, "roh": d}

    # ---- FMP (key) ----------------------------------------------------------
    def screener_gewinner(self) -> dict:
        key = self._key("FMP_API_KEY")
        if not key:
            return self._fallb("FMP", "FMP_API_KEY")
        url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={key}"
        try:
            d = self._fetch(url)
        except Exception as exc:
            return {"ok": False, "provider": "FMP", "fehler": str(exc)[:160]}
        movers = [{"symbol": x.get("symbol"), "name": x.get("name"),
                   "veraenderung_pct": x.get("changesPercentage")} for x in (d or [])][:25]
        return {"ok": True, "provider": "FMP", "gewinner": movers}

    # ---- SEC EDGAR (User-Agent) ---------------------------------------------
    def filings(self, cik) -> dict:
        ua = self._key("SEC_EDGAR_USER_AGENT")
        if not ua:
            return self._fallb("SEC EDGAR", "SEC_EDGAR_USER_AGENT")
        cik10 = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
        try:
            d = self._fetch(url, headers={"User-Agent": ua})
        except Exception as exc:
            return {"ok": False, "provider": "SEC EDGAR", "fehler": str(exc)[:160]}
        return {"ok": True, "provider": "SEC EDGAR", "name": d.get("name"), "cik": cik10}
