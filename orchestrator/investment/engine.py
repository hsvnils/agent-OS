"""CIO-Engine (Phase 2) -- die drei Kern-Schleifen im advisory-Modus, regelbasiert und token-frugal.

- markt_screen(): Bulk-Scan (FMP-Gewinner + CoinGecko-Krypto) -> Shortlist (gespeichert).
- screen_und_vorschlagen(): erzeugt aus der Shortlist Vorschlaege (Maker) und laesst JEDEN vom **Risk-Agent**
  (Checker) pruefen -- nur freigegebene werden gespeichert/gemeldet.
- wochenprognose(): regelbasierte Prognose je Watchlist-Wert (Momentum) -> gespeichert (walk-forward).
- scorecard(): Soll-Ist aus Prognosen + eingetretenen Werten (Trefferquote/Fehler).

Keine Trades, keine Geldbewegungen. Alle Alerts tragen Grund/Quelle/Konfidenz/Risiko-Label.
"""
from __future__ import annotations

from .providers import MarketData
from .risk import RiskAgent
from .store import InvestmentStore

KRYPTO_DEFAULT = ["bitcoin", "ethereum", "solana"]


class InvestmentEngine:
    def __init__(self, market: MarketData, store: InvestmentStore, *, risk: RiskAgent | None = None,
                 notify=None):
        self.market = market
        self.store = store
        self.risk = risk or RiskAgent()
        self.notify = notify  # optional: callback(text, abteilung=, kategorie=, detail=)

    # -- Status --
    def status(self) -> dict:
        return {
            "modus": self.store.mode(),
            "provider": self.market.provider_status(),
            "fehlende_keys": self.market.fehlende_keys(),
            "watchlist": self.store.watchlist(),
            "offene_vorschlaege": [s for s in self.store.list("suggestions") if s.get("status") == "offen"],
        }

    # -- 1) Markt-Screen --
    def markt_screen(self, *, krypto_ids=None, limit: int = 10) -> dict:
        shortlist: list[dict] = []
        hinweise: list[str] = []

        g = self.market.screener_gewinner()
        if g.get("ok"):
            for x in g["gewinner"][:limit]:
                shortlist.append({"symbol": x.get("symbol"), "name": x.get("name"), "asset": "aktie",
                                  "veraenderung_pct": _zahl(x.get("veraenderung_pct")), "quelle": "FMP"})
        elif g.get("fall_b"):
            hinweise.append(g["hinweis"])

        c = self.market.crypto_preis(krypto_ids or KRYPTO_DEFAULT, vs="eur")
        if c.get("ok"):
            for cid, v in (c.get("preise") or {}).items():
                shortlist.append({"symbol": cid, "asset": "krypto",
                                  "veraenderung_pct": _zahl(v.get("eur_24h_change")), "preis_eur": v.get("eur"),
                                  "quelle": "CoinGecko"})

        # nach Betrag der Bewegung sortieren (auffaelligste zuerst)
        shortlist.sort(key=lambda s: abs(s.get("veraenderung_pct") or 0), reverse=True)
        sid = self.store.add("screening", {"shortlist": shortlist, "anzahl": len(shortlist)})
        return {"ok": True, "screening_id": sid, "anzahl": len(shortlist), "shortlist": shortlist,
                "hinweise": hinweise}

    # -- 2) Vorschlag (Maker) -> Risk (Checker) --
    def vorschlag(self, symbol: str, *, aktion: str, grund: str, asset: str = "aktie",
                  veraenderung_pct: float = 0.0, konfidenz: float = 0.5, quellen=None) -> dict:
        urteil = self.risk.pruefe({"symbol": symbol, "aktion": aktion, "asset": asset,
                                   "veraenderung_pct": veraenderung_pct, "konfidenz": konfidenz})
        if urteil["entscheidung"] != "freigabe":
            return {"ok": False, "entscheidung": urteil["entscheidung"], "urteil": urteil,
                    "hinweis": f"Risk-Agent: {urteil['entscheidung']} -- kein Alert ({urteil['begruendung']})."}
        sid = self.store.suggestion_add(symbol, aktion=aktion, grund=grund, quellen=quellen or [],
                                        konfidenz=konfidenz, risiko_label=urteil["label"])
        if self.notify:
            txt = (f"{aktion.upper()} {symbol} ({asset}) -- {grund}. "
                   f"Risiko: {urteil['label']}, Konfidenz {konfidenz:.0%}, max. {urteil['max_position']}.")
            try:
                self.notify(txt, abteilung="CIO", kategorie="investment", detail=urteil["begruendung"])
            except Exception:
                pass
        return {"ok": True, "suggestion_id": sid, "urteil": urteil}

    def screen_und_vorschlagen(self, *, schwelle_pct: float = 5.0, max_vorschlaege: int = 5,
                               krypto_ids=None) -> dict:
        """Voll-Schleife: screenen -> auffaellige Werte als 'beobachten'-Vorschlaege durch den Risk-Agent."""
        screen = self.markt_screen(krypto_ids=krypto_ids)
        erstellt, abgelehnt = [], []
        for s in screen["shortlist"]:
            chg = abs(s.get("veraenderung_pct") or 0)
            if chg < schwelle_pct:
                continue
            konfidenz = min(0.85, 0.4 + chg / 100.0)  # groessere Bewegung -> etwas hoehere Konfidenz
            r = self.vorschlag(
                s["symbol"], aktion="beobachten",
                grund=f"Auffaellige Bewegung {s.get('veraenderung_pct'):+.1f}% ({s['quelle']})",
                asset=s["asset"], veraenderung_pct=s.get("veraenderung_pct") or 0, konfidenz=konfidenz,
                quellen=[s["quelle"]])
            (erstellt if r.get("ok") else abgelehnt).append({"symbol": s["symbol"], **r})
            if len(erstellt) >= max_vorschlaege:
                break
        return {"ok": True, "screening_id": screen["screening_id"], "erstellt": erstellt,
                "vom_risk_abgelehnt": abgelehnt, "hinweise": screen.get("hinweise", [])}

    # -- 3) Wochenprognose + Scorecard --
    def wochenprognose(self) -> dict:
        erstellt = []
        for w in self.store.watchlist():
            sym, asset = w["symbol"], w.get("asset", "aktie")
            chg = 0.0
            if asset == "krypto":
                c = self.market.crypto_preis([sym], vs="eur")
                if c.get("ok"):
                    chg = _zahl((c["preise"].get(sym) or {}).get("eur_24h_change"))
            else:
                q = self.market.aktie_quote(sym)
                if q.get("ok"):
                    chg = _zahl(q.get("veraenderung_pct"))
            richtung = "steigt" if chg > 1 else ("faellt" if chg < -1 else "seitwaerts")
            konfidenz = min(0.8, 0.5 + abs(chg) / 100.0)
            fid = self.store.forecast_add(sym, prognose=richtung, konfidenz=konfidenz, horizont="1W",
                                          rationale=f"Momentum {chg:+.1f}%")
            erstellt.append({"symbol": sym, "prognose": richtung, "konfidenz": round(konfidenz, 2),
                             "forecast_id": fid})
        return {"ok": True, "prognosen": erstellt}

    def scorecard(self) -> dict:
        forecasts = self.store.list("forecasts")
        actuals = {a.get("bezug_forecast"): a for a in self.store.list("actuals")}
        bewertet = [f for f in forecasts if f.get("id") in actuals]
        treffer = sum(1 for f in bewertet if _traf_zu(f, actuals[f["id"]]))
        return {"prognosen_gesamt": len(forecasts), "ausgewertet": len(bewertet),
                "treffer": treffer,
                "trefferquote": round(treffer / len(bewertet), 2) if bewertet else None}


def _traf_zu(forecast: dict, actual: dict) -> bool:
    chg = _zahl(actual.get("wert"))
    p = forecast.get("prognose")
    return (p == "steigt" and chg > 0) or (p == "faellt" and chg < 0) or (p == "seitwaerts" and abs(chg) <= 1)


def _zahl(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
