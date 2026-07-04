"""Signal-Bausteine fuer die Prognose (Mehr-Signal-Modell v2).

Bildet die menschlichen Entscheidungs-Schulen als einzeln nachvollziehbare, gerichtete Signale ab -- berechnet
aus unserer eigenen angesammelten Kurs-Historie (Tages-Closes). Jedes Signal: `typ`, `richtung`
(steigt/faellt/neutral), `staerke` (0..1), `detail`. Der Forecaster kombiniert sie (Mehrheit) und zaehlt die
uebereinstimmenden Signale -- das speist die Autonomie-Leitplanke „>= 2 Signale" mit echten Daten, und das
Abweichungs-Register misst spaeter, WELCHE Signale wirklich treffen (Attribution = das Lernen).

Startsignale: Momentum, Trend (SMA), Breakout (Position in der 20-Tage-Range). Weitere (Insider, News,
Fundamental) sind als zusaetzliche Signaltypen andockbar. Keine Trades, kein Geld.
"""
from __future__ import annotations


def berechne(closes: list[float]) -> list[dict]:
    """closes: chronologische Tages-Schlusskurse (inkl. heute). -> Liste gerichteter Signale."""
    out: list[dict] = []
    n = len(closes)
    if n < 2:
        return out
    c = closes[-1]

    # 1) Momentum (5-Tage-Rendite)
    if n > 5 and closes[-6] > 0:
        ret5 = (c / closes[-6] - 1) * 100
        out.append(_gerichtet("momentum", ret5, schwelle=2.0, staerke=abs(ret5) / 10, detail=f"5T {ret5:+.1f}%"))

    # 2) Trend (SMA-5 ueber/unter SMA-20)
    sma5 = sum(closes[-5:]) / min(n, 5)
    sma20 = sum(closes[-20:]) / min(n, 20)
    if sma20 > 0:
        gap = (sma5 / sma20 - 1) * 100
        out.append(_gerichtet("trend", gap, schwelle=0.5, staerke=abs(gap) / 5, detail=f"SMA5 vs SMA20 {gap:+.1f}%"))

    # 3) Breakout (Position in der 20-Tage-Range)
    fenster = closes[-20:]
    lo, hi = min(fenster), max(fenster)
    if hi > lo:
        pos = (c - lo) / (hi - lo)
        richtung = "steigt" if pos >= 0.8 else ("faellt" if pos <= 0.2 else "neutral")
        out.append({"typ": "breakout", "richtung": richtung, "staerke": round(min(1.0, abs(pos - 0.5) * 2), 2),
                    "detail": f"Range-Position {pos:.0%}"})
    return out


def _gerichtet(typ: str, wert: float, *, schwelle: float, staerke: float, detail: str) -> dict:
    richtung = "steigt" if wert > schwelle else ("faellt" if wert < -schwelle else "neutral")
    return {"typ": typ, "richtung": richtung, "staerke": round(min(1.0, staerke), 2), "detail": detail}


def insider_signal(cluster: int, summe: float) -> dict:
    """Nicht-Preis-Signal aus SEC Form 4: ein frischer Insider-KAUF-Cluster ist bullisch (dokumentierte
    Vorhersagekraft, v. a. bei Small/Mid-Caps). `cluster` = Zahl kaufender Insider, `summe` = Kaufwert USD.
    Staerke steigt mit Cluster-Groesse und Kaufsumme. Immer richtung=steigt (nur Kaeufe werden gemeldet)."""
    staerke = min(1.0, 0.3 + 0.2 * max(0, cluster - 1) + min(0.4, summe / 1_000_000.0))
    return {"typ": "insider", "richtung": "steigt", "staerke": round(staerke, 2),
            "detail": f"{cluster} Insider-Kaeufer, ~{summe:,.0f} USD"}
