"""Discovery-Universum -- die feste Kernliste, die der Loop ZUSAETZLICH zur Watchlist beobachtet.

Ziel (CEO): moeglichst viel Daten sammeln und Vorschlaege AUSSERHALB der eigenen Watchlist erhalten. Damit die
Walk-Forward-Historie ueberhaupt entstehen kann, braucht es eine **stabile** Liste (dieselben Werte ueber die
Zeit) -- taegliche Tages-Mover wechseln zu stark. Diese Kernliste ist bewusst kompakt (token-/rate-limit-frugal:
1 Kursabruf je Wert/Tag) und **frei erweiterbar**. Benchmarks SPY/BTC sind bewusst NICHT hier (sie laufen als
Baseline in `features.BASELINES`).

Anlageklassen sind explizit getaggt: aktie | etf | krypto -- so werden Prognosegenauigkeit und Feintuning je
Klasse getrennt gemessen.
"""
from __future__ import annotations

CORE_UNIVERSE: list[dict] = [
    # Aktien (Large-Cap, liquide)
    {"symbol": "AAPL", "asset": "aktie"}, {"symbol": "MSFT", "asset": "aktie"},
    {"symbol": "NVDA", "asset": "aktie"}, {"symbol": "AMZN", "asset": "aktie"},
    {"symbol": "GOOGL", "asset": "aktie"}, {"symbol": "META", "asset": "aktie"},
    {"symbol": "TSLA", "asset": "aktie"}, {"symbol": "AMD", "asset": "aktie"},
    {"symbol": "AVGO", "asset": "aktie"}, {"symbol": "JPM", "asset": "aktie"},
    # ETFs (Index/Sektor)
    {"symbol": "QQQ", "asset": "etf"}, {"symbol": "IWM", "asset": "etf"},
    {"symbol": "VTI", "asset": "etf"}, {"symbol": "DIA", "asset": "etf"},
    {"symbol": "VGT", "asset": "etf"},
    # Krypto (CoinGecko-IDs)
    {"symbol": "ethereum", "asset": "krypto"}, {"symbol": "solana", "asset": "krypto"},
    {"symbol": "cardano", "asset": "krypto"}, {"symbol": "ripple", "asset": "krypto"},
    {"symbol": "dogecoin", "asset": "krypto"},
]


def panel(watchlist) -> list[dict]:
    """Watchlist + Kernuniversum, dedupliziert (ohne Benchmarks). Das Panel, das Loop + Forecaster abdecken."""
    seen: set[str] = set()
    out: list[dict] = []
    for w in list(watchlist) + CORE_UNIVERSE:
        sym = (w.get("symbol") or "").strip()
        if sym and sym.upper() not in seen:
            seen.add(sym.upper())
            out.append(w)
    return out
