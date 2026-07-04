"""Intraday-Markt-Monitor (Schritt 8): erkennt scharfe LIVE-Kursbewegungen zwischen den Batch-Laeufen.

Frugal + regelbasiert (kein LLM je Tick): haelt je Wert eine gleitende Referenz (Preis + Zeit) und meldet eine
**Kandidaten-Bewegung**, wenn der Kurs sich seit der Referenz um mehr als `schwelle_pct` innerhalb von
`fenster_sek` bewegt hat. Danach wird die Referenz nachgezogen -> kein Dauerfeuer. Der Aufrufer (Bot) macht aus
Kandidaten Vorschlaege (Dip = kleiner Paper-Kauf per 1-Tap-Freigabe; starker Anstieg = Info-Alert).

`clock` injizierbar -> deterministisch testbar. Kein Broker, kein Geld hier drin.
"""
from __future__ import annotations

import time


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def exit_signal(unrealized_plpc, *, stop_pct: float = 8.0, target_pct: float = 15.0) -> str | None:
    """Exit-Entscheidung fuer eine offene Position anhand ihres unrealisierten P/L (Bruchteil, z. B. -0.05).
    -> 'stop' (Verlust deckeln, automatisch verkaufen) | 'target' (Gewinnziel, Verkauf vorschlagen) | None."""
    p = _num(unrealized_plpc) * 100
    if p <= -abs(stop_pct):
        return "stop"
    if p >= abs(target_pct):
        return "target"
    return None


def krypto_order_symbol(symbol: str) -> str:
    """Positions-Symbol -> Order-Symbol fuer Krypto (Alpaca: Position 'BTCUSD' -> Order 'BTC/USD')."""
    s = (symbol or "").upper()
    if "/" in s:
        return s
    return s[:-3] + "/USD" if s.endswith("USD") else s


class MarketMonitor:
    def __init__(self, *, schwelle_pct: float = 4.0, fenster_sek: int = 1800, clock=None):
        self.schwelle = schwelle_pct
        self.fenster = fenster_sek
        self.refs: dict[str, tuple[float, float]] = {}   # symbol -> (referenz_preis, referenz_ts)
        self._clock = clock or time.time

    def beobachte(self, quotes: dict) -> list[dict]:
        """quotes: {symbol: {preis, asset}}. -> Liste auffaelliger Live-Bewegungen (seit der Referenz)."""
        jetzt = self._clock()
        cands: list[dict] = []
        for sym, q in quotes.items():
            preis = _num(q.get("preis"))
            if preis <= 0:
                continue
            ref = self.refs.get(sym)
            if not ref or (jetzt - ref[1]) > self.fenster:   # erstmalig gesehen / Fenster abgelaufen -> Referenz setzen
                self.refs[sym] = (preis, jetzt)
                continue
            move = (preis / ref[0] - 1) * 100 if ref[0] > 0 else 0.0
            if abs(move) >= self.schwelle:
                cands.append({"symbol": sym, "asset": q.get("asset", "aktie"),
                              "richtung": "faellt" if move < 0 else "steigt",
                              "move_pct": round(move, 2), "preis": preis})
                self.refs[sym] = (preis, jetzt)              # Referenz nachziehen -> kein Dauerfeuer
        return cands
