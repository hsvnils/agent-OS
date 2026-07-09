"""Portfolio-/Depot-Ansicht -- normalisiert Bestaende zu einer lesbaren Uebersicht.

Zwei getrennte Quellen:
  1. Paper-Depot  -- das simulierte Alpaca-Paper-Konto, das LUNA fuehrt (`paper_portfolio`). Alpaca liefert
     Aktien, ETFs und Krypto in EINEM Konto (asset_class us_equity|crypto) inkl. Einstand + Marktwert.
  2. Echtes Depot -- manuell gepflegte reale Bestaende des CEO (`real_portfolio`); live bewertet ueber die
     vorhandenen Marktdaten (Aktien/ETF via Aktien-Quote, Krypto via CoinGecko).

Read-only -- keine Order, kein CEO-Tor. Anlageklassen: aktie / etf / krypto.
"""
from __future__ import annotations

# Gaengige ETFs, um sie von Einzelaktien zu trennen (Alpaca kennzeichnet ETFs nicht separat).
KNOWN_ETFS = {"SPY", "QQQ", "VOO", "VTI", "IVV", "VEA", "VWO", "VUG", "VTV", "IWM", "DIA", "ARKK",
              "SCHD", "VYM", "VXUS", "BND", "AGG", "GLD", "SLV", "XLK", "XLF", "XLE", "SOXX", "SMH"}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _klasse_paper(pos: dict) -> str:
    if (pos.get("asset_class") or "").lower() == "crypto":
        return "krypto"
    sym = (pos.get("symbol") or "").upper().split("/")[0]
    return "etf" if sym in KNOWN_ETFS else "aktie"


def normalisiere_position(pos: dict) -> dict:
    """Eine rohe Alpaca-Position -> vereinheitlichtes Feldset."""
    return {
        "symbol": (pos.get("symbol") or "").upper(),
        "klasse": _klasse_paper(pos),
        "stueck": _num(pos.get("qty")),
        "einstand_preis": _num(pos.get("avg_entry_price")),
        "einstand_wert": _num(pos.get("cost_basis")),
        "kurs": _num(pos.get("current_price")),
        "wert": _num(pos.get("market_value")),
        "gv_abs": _num(pos.get("unrealized_pl")),
        "gv_pct": _num(pos.get("unrealized_plpc")) * 100.0,
        "tag_pct": _num(pos.get("change_today")) * 100.0,
    }


def _gruppiere(positionen: list[dict]) -> dict:
    gruppen: dict = {}
    for p in positionen:
        g = gruppen.setdefault(p["klasse"], {"wert": 0.0, "einstand": 0.0, "gv_abs": 0.0, "anzahl": 0})
        g["wert"] += _num(p.get("wert"))
        g["einstand"] += _num(p.get("einstand_wert"))
        g["gv_abs"] += _num(p.get("gv_abs"))
        g["anzahl"] += 1
    return gruppen


def paper_portfolio(broker) -> dict:
    """Depot-Uebersicht des Paper-Kontos. Inert (verfuegbar=False) ohne Alpaca-Keys."""
    if broker is None or not getattr(broker, "verfuegbar", False):
        return {"verfuegbar": False,
                "grund": "Alpaca-Paper nicht konfiguriert (ALPACA_API_KEY/ALPACA_API_SECRET in .env).",
                "konto": {}, "positionen": [], "gruppen": {}}
    konto = broker.konto() or {}
    positionen = [normalisiere_position(p) for p in (broker.positionen() or [])]
    positionen.sort(key=lambda p: p["wert"], reverse=True)
    equity = _num(konto.get("equity"))
    last_equity = _num(konto.get("last_equity"))
    return {
        "verfuegbar": True,
        "konto": {
            "gesamtwert": equity,
            "cash": _num(konto.get("cash")),
            "kaufkraft": _num(konto.get("buying_power")),
            "positionswert": _num(konto.get("long_market_value")),
            "tag_abs": equity - last_equity,
            "tag_pct": ((equity - last_equity) / last_equity * 100.0) if last_equity else 0.0,
            "waehrung": konto.get("currency") or "USD",
        },
        "positionen": positionen,
        "gruppen": _gruppiere(positionen),
    }


def depot_hinweise(positionen, *, stop_pct: float = 8.0, target_pct: float = 15.0) -> list[dict]:
    """Rein BERATENDE Hinweise fuer bewertete Positionen (echtes Depot) -- keine Ausfuehrung, keine Order.
    Meldet Stop-Loss- (-stop_pct) und Take-Profit-Schwellen (+target_pct) anhand der unrealisierten G/V.
    -> Liste {symbol, klasse, signal:'stop'|'target', gv_pct, text}."""
    from .monitor import exit_signal
    out: list[dict] = []
    for p in positionen or []:
        gvp = p.get("gv_pct")
        if gvp is None:
            continue
        sig = exit_signal(gvp / 100.0, stop_pct=stop_pct, target_pct=target_pct)
        if not sig:
            continue
        if sig == "stop":
            text = (f"{p['symbol']} liegt bei {gvp:+.1f}% — Stop-Loss-Schwelle (-{stop_pct:g}%) erreicht. "
                    f"Verkauf erwaegen (in deinem Broker).")
        else:
            text = (f"{p['symbol']} liegt bei {gvp:+.1f}% — Gewinnziel (+{target_pct:g}%) erreicht. "
                    f"Gewinn mitnehmen erwaegen.")
        out.append({"symbol": p["symbol"], "klasse": p.get("klasse"), "signal": sig,
                    "gv_pct": round(gvp, 2), "text": text})
    return out


def _live_kurs(market, holding: dict, vs: str = "usd") -> float | None:
    """Aktueller Kurs einer realen Position ueber die vorhandenen Marktdaten. None wenn nicht ermittelbar."""
    if market is None:
        return None
    klasse = (holding.get("klasse") or "aktie").lower()
    kurs_id = (holding.get("kurs_id") or holding.get("symbol") or "").strip()
    try:
        if klasse == "krypto":
            r = market.crypto_preis(kurs_id, vs=vs)
            if r.get("ok"):
                eintrag = (r.get("preise") or {}).get(kurs_id.lower()) or {}
                p = _num(eintrag.get(vs))
                return p or None
        else:
            r = market.aktie_quote(kurs_id.upper())
            if r.get("ok"):
                p = _num(r.get("preis"))
                return p or None
    except Exception:
        return None
    return None


def real_portfolio(holdings: list[dict], market=None, *, vs: str = "usd", realisiert: float = 0.0) -> dict:
    """Manuell gepflegte reale Bestaende, live bewertet. Positionen ohne ermittelbaren Kurs -> kurs=None.
    `realisiert` = bereits realisierte G/V aus Verkaeufen (fliesst in die Summe)."""
    positionen: list[dict] = []
    for h in holdings or []:
        stueck = _num(h.get("stueck"))
        einstand_preis = _num(h.get("einstand_preis"))
        einstand_wert = stueck * einstand_preis
        kurs = _live_kurs(market, h, vs=vs)
        wert = (stueck * kurs) if kurs is not None else None
        gv_abs = (wert - einstand_wert) if wert is not None else None
        gv_pct = (gv_abs / einstand_wert * 100.0) if (gv_abs is not None and einstand_wert) else None
        positionen.append({
            "id": h.get("id"),
            "symbol": (h.get("symbol") or "").upper(),
            "klasse": (h.get("klasse") or "aktie").lower(),
            "stueck": stueck,
            "einstand_preis": einstand_preis,
            "einstand_wert": einstand_wert,
            "kurs": kurs,
            "wert": wert,
            "gv_abs": gv_abs,
            "gv_pct": gv_pct,
            "waehrung": (h.get("waehrung") or "USD").upper(),
            "kurs_id": h.get("kurs_id", ""),
        })
    positionen.sort(key=lambda p: (p["wert"] if p["wert"] is not None else p["einstand_wert"]), reverse=True)
    bewertbar = [p for p in positionen if p["wert"] is not None]
    gesamtwert = sum(p["wert"] for p in bewertbar)
    einstand_ges = sum(p["einstand_wert"] for p in bewertbar)
    return {
        "positionen": positionen,
        "gruppen": _gruppiere([p for p in positionen if p["wert"] is not None]),
        "summe": {
            "gesamtwert": gesamtwert,
            "einstand": einstand_ges,
            "gv_abs": gesamtwert - einstand_ges,
            "gv_pct": ((gesamtwert - einstand_ges) / einstand_ges * 100.0) if einstand_ges else 0.0,
            "realisiert": round(realisiert, 2),
            "waehrung": vs.upper(),
            "unbewertet": len(positionen) - len(bewertbar),
        },
    }
