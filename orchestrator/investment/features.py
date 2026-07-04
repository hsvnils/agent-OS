"""Taeglicher Merkmals-/Preis-Sammler fuer den Walk-Forward-Lern-Loop (Schritt 1).

Nimmt die Watchlist (+ Benchmark-Serien SPY/BTC), holt je Wert den aktuellen Kurs (Aktie via Finnhub, Krypto
via CoinGecko) und leitet aus unserer **eigenen, ueber die Zeit angesammelten** Kurs-Historie Merkmale ab
(Renditen 1/5/20 Tage, realisierte Volatilitaet, gleitende Durchschnitte, Momentum). Ein Snapshot je Wert je
Tag -> `LoopStore` (lokal + Supabase). Token-/call-frugal: nur 1 Kursabruf je Wert/Tag, keine bezahlten Dienste.

Keine Trades, keine Geldbewegungen -- reines Lesen + Speichern. So baut sich die Datenbasis auf, an der wir
spaeter messen, ob Anreicherung die Prognosefehler verkleinert.
"""
from __future__ import annotations

import statistics

# Benchmark-Serien: die Messlatte fuer "schlaegt die Strategie den Markt?" (mitgesammelt wie normale Werte).
BASELINES = [{"symbol": "SPY", "asset": "aktie"}, {"symbol": "bitcoin", "asset": "krypto"}]
_BASE_SYMS = {b["symbol"].upper() for b in BASELINES}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class FeatureCollector:
    def __init__(self, market, store):
        self.market = market      # investment.providers.MarketData
        self.store = store        # investment.loop_store.LoopStore

    def _preis(self, symbol: str, asset: str):
        """(close, change_pct) oder (None, 0.0) bei fehlendem Kurs/Fall-B. ETF laeuft ueber den Aktien-Pfad."""
        if asset == "krypto":
            c = self.market.crypto_preis([symbol], vs="eur")
            if c.get("ok"):
                v = (c.get("preise") or {}).get(symbol) or {}
                return _num(v.get("eur")) or None, _num(v.get("eur_24h_change"))
            return None, 0.0
        q = self.market.aktie_quote(symbol)
        if q.get("ok"):
            return _num(q.get("preis")) or None, _num(q.get("veraenderung_pct"))
        return None, 0.0

    def collect(self, watchlist, *, universe=None, datum: str | None = None) -> dict:
        """Sammelt Merkmale fuer Watchlist + Discovery-Universum (Standard: universe.CORE_UNIVERSE) + Benchmarks.
        `universe=[]` beschraenkt bewusst auf die Watchlist (z. B. in Tests)."""
        from datetime import date

        from .universe import CORE_UNIVERSE
        datum = datum or date.today().isoformat()
        uni = CORE_UNIVERSE if universe is None else universe
        gesammelt, uebersprungen, hinweise = [], [], []

        seen: set[str] = set()
        ziele: list[dict] = []
        for w in list(watchlist) + list(uni) + BASELINES:
            sym = (w.get("symbol") or "").strip()
            if not sym or sym.upper() in seen:
                continue
            seen.add(sym.upper())
            ziele.append(w)

        for w in ziele:
            sym = w["symbol"]
            asset = w.get("asset", "aktie")
            if self.store.has_feature(sym, datum):
                uebersprungen.append(sym)
                continue
            close, change = self._preis(sym, asset)
            if close is None or close <= 0:
                hinweise.append(f"{sym}: kein Kurs (Fall-B/Key?)")
                continue
            feats = self._derive(sym, close)
            self.store.feature_add(sym, asset, datum, round(close, 6), round(change, 3), feats,
                                   baseline=(sym.upper() in _BASE_SYMS),
                                   quelle=("CoinGecko" if asset == "krypto" else "Finnhub"))
            gesammelt.append(sym)
        return {"ok": True, "datum": datum, "gesammelt": gesammelt, "uebersprungen": uebersprungen,
                "hinweise": hinweise}

    def _derive(self, symbol: str, close: float) -> dict:
        """Merkmale aus der eigenen Historie (inkl. des heutigen close). None, solange zu wenig Historie da ist."""
        hist = self.store.features_for(symbol)
        closes = [_num(h["close"]) for h in hist if _num(h["close"]) > 0]
        closes.append(_num(close))
        return derive(closes)


def derive(closes: list[float]) -> dict:
    """Abgeleitete Merkmale aus einer chronologischen Close-Reihe (inkl. aktuellem Wert am Ende).
    Pure Funktion -- auch vom Backfill genutzt, damit historische Zeilen wie live-gesammelte aussehen."""
    def ret(n: int):
        return round((closes[-1] / closes[-1 - n] - 1) * 100, 3) if len(closes) > n and closes[-1 - n] > 0 else None

    tages_rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1] > 0]
    vola_20d = round(statistics.pstdev(tages_rets[-20:]) * 100, 3) if len(tages_rets) >= 2 else None
    sma_5 = round(sum(closes[-5:]) / min(len(closes), 5), 6) if closes else None
    sma_20 = round(sum(closes[-20:]) / min(len(closes), 20), 6) if closes else None
    return {"ret_1d": ret(1), "ret_5d": ret(5), "ret_10d": ret(10), "ret_20d": ret(20),
            "vola_20d": vola_20d, "sma_5": sma_5, "sma_20": sma_20,
            "ueber_sma20": (closes[-1] > sma_20) if sma_20 else None, "n_hist": len(closes)}
