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
                 notify=None, brain=None, broker=None):
        self.market = market
        self.store = store
        self.risk = risk or RiskAgent()
        self.notify = notify  # optional: callback(text, abteilung=, kategorie=, detail=)
        self.brain = brain    # optional: callback(text, *, titel, tags, quelle, ref) -- Second Brain
        self.broker = broker  # GATE C: Paper-Broker (Alpaca) oder None (advisory)

    # -- GATE C: Paper-Trading (simuliert, echte Kurse) --
    def paper_konto(self) -> dict:
        """Konto + Positionen des Paper-Brokers. Read-only; Modus/Keys werden gemeldet, nichts ausgefuehrt."""
        modus = self.store.mode()
        if self.broker is None or not self.broker.verfuegbar:
            return {"ok": False, "modus": modus,
                    "hinweis": "Alpaca-Paper nicht konfiguriert (ALPACA_API_KEY/ALPACA_API_SECRET in .env)."}
        konto = self.broker.konto()
        if konto is None:
            return {"ok": False, "modus": modus, "hinweis": "Konto-Abruf fehlgeschlagen (Keys/Netz pruefen)."}
        return {"ok": True, "modus": modus,
                "konto": {k: konto.get(k) for k in ("cash", "buying_power", "equity", "last_equity",
                                                    "portfolio_value", "status") if k in konto},
                "positionen": [{"symbol": p.get("symbol"), "qty": p.get("qty"),
                                "marktwert": p.get("market_value"), "pl": p.get("unrealized_pl")}
                               for p in self.broker.positionen()]}

    def paper_order(self, symbol: str, qty: float, side: str, *, asset: str = "aktie",
                    bestaetigt: bool = False) -> dict:
        """Platziert eine PAPER-Order -- nur in modus 'paper', mit CEO-Bestaetigung und harter Risk-Pruefung."""
        modus = self.store.mode()
        if modus != "paper":
            return {"ok": False, "hinweis": f"Modus ist '{modus}', nicht 'paper'. paper aktivieren = CEO-Tor "
                                            "(GATE C) ueber 'investment_modus'."}
        if self.broker is None or not self.broker.verfuegbar:
            return {"ok": False, "hinweis": "Alpaca-Paper nicht konfiguriert (Keys fehlen)."}
        symbol = (symbol or "").upper().strip()
        side = (side or "buy").lower().strip()
        qty = _zahl(qty)
        if not symbol or qty <= 0 or side not in ("buy", "sell"):
            return {"ok": False, "hinweis": "Ungueltige Order (symbol/qty/side)."}
        preis = _zahl(self._aktueller_preis(symbol, asset))
        order_wert = preis * qty
        konto = self.broker.konto() or {}
        urteil = self.risk.pruefe_order(order_wert=order_wert, konto_equity=_zahl(konto.get("equity")),
                                        buying_power=_zahl(konto.get("buying_power")), side=side)
        if not urteil["ok"]:
            self.store.add("positions", {"symbol": symbol, "qty": qty, "side": side, "status": "abgelehnt",
                                         "grund": urteil["grund"], "order_wert": round(order_wert, 2)})
            return {"ok": False, "abgelehnt": True, "grund": urteil["grund"]}
        if not bestaetigt:                                   # CEO-Tor je Order
            return {"ok": False, "bestaetigung_noetig": True, "symbol": symbol, "qty": qty, "side": side,
                    "geschaetzter_wert": round(order_wert, 2), "risk": urteil["grund"],
                    "hinweis": "Paper-Order (simuliert). Mit bestaetigt=true ausfuehren."}
        res = self.broker.order(symbol, qty, side)
        if res is None:
            self.store.add("positions", {"symbol": symbol, "qty": qty, "side": side, "status": "fehler"})
            return {"ok": False, "hinweis": "Broker-Order fehlgeschlagen (Keys/Markt/Zeitfenster?)."}
        oid = self.store.add("positions", {"symbol": symbol, "qty": qty, "side": side, "status": "platziert",
                                           "order_wert": round(order_wert, 2),
                                           "broker_order_id": res.get("id", ""), "modus": "paper"})
        if self.notify:
            try:
                self.notify(f"Paper-Order platziert: {side} {qty} {symbol} (~{_geld(order_wert)}).",
                            abteilung="CIO/Investment", kategorie="investment", quelle="paper-trade")
            except Exception:
                pass
        return {"ok": True, "platziert": True, "order_id": oid, "broker_order_id": res.get("id", ""),
                "symbol": symbol, "qty": qty, "side": side, "geschaetzter_wert": round(order_wert, 2)}

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

    # -- Insider-Screen (SEC Form 4, oeffentliche Pflichtmeldungen) --
    def insider_scan(self, symbols=None, *, min_kauf_wert: float = 50_000.0, cluster_min: int = 2,
                     max_alerts: int = 5, seit: str = "") -> dict:
        """Insider-Screen ueber die Watchlist (oder uebergebene Aktien-Symbole): oeffentliche Form-4-**KAEUFE**
        ziehen, je Symbol aggregieren (Cluster = Zahl kaufender Insider, Summe der Kaufwerte). Auffaellige
        Cluster ODER Grosskaeufe -> Signal (gespeichert) + Risk-gepruefter 'beobachten'-Alert + Second-Brain-
        Notiz. Nur Kaeufe, nur oeffentliche Filings, keine Trades."""
        syms = symbols if symbols is not None else [
            w["symbol"] for w in self.store.watchlist() if w.get("asset", "aktie") == "aktie"]
        signale, hinweise = [], []
        for sym in syms:
            r = self.market.insider_transactions(sym, seit=seit)
            if r.get("fall_b"):
                if r["hinweis"] not in hinweise:
                    hinweise.append(r["hinweis"])
                continue
            if not r.get("ok"):
                continue
            kaeufe = [t for t in r.get("transaktionen", []) if t.get("transaktion") == "kauf"]
            if not kaeufe:
                continue
            insider_namen = sorted({t.get("insider") for t in kaeufe if t.get("insider")})
            cluster = len(insider_namen)
            summe = round(sum(_zahl(t.get("wert")) for t in kaeufe), 2)
            if cluster < cluster_min and summe < min_kauf_wert:
                continue  # weder Insider-Cluster noch grosser Einzelkauf -> unauffaellig
            konfidenz = round(min(0.85, 0.4 + 0.1 * cluster + min(0.25, summe / 1_000_000.0)), 2)
            rollen = ", ".join(sorted({t.get("rolle") for t in kaeufe if t.get("rolle")}))[:80]
            sig_id = self.store.insider_signal_add(
                sym, insider="; ".join(insider_namen)[:120], rolle=rollen, transaktion="kauf",
                betrag=summe, anzahl=cluster, datum=(kaeufe[0].get("datum") or ""),
                quelle=r.get("quelle", "SEC Form 4"), filing_url=r.get("filing_url", ""),
                konfidenz=konfidenz, cluster=cluster)
            grund = (f"Insider-Kauf: {cluster} Insider ({rollen or 'k.A.'}) kauften zusammen ~{_geld(summe)} "
                     f"(SEC Form 4).")
            v = self.vorschlag(sym, aktion="beobachten", grund=grund, asset="aktie",
                               veraenderung_pct=0.0, konfidenz=konfidenz,
                               quellen=[r.get("filing_url") or "SEC Form 4"])
            if self.brain:
                try:
                    self.brain(f"{sym}: Insider-Kauf-Cluster ({cluster} Insider, ~{_geld(summe)}, "
                               f"{rollen or 'k.A.'}). Quelle SEC Form 4: {r.get('filing_url', '')}",
                               titel=f"Insider-Kauf {sym}", tags=["insider", "cio", sym.lower()],
                               quelle="insider", ref=f"insider:{sym}:{kaeufe[0].get('datum', '')}")
                except Exception:
                    pass
            signale.append({"symbol": sym, "cluster": cluster, "summe": summe, "signal_id": sig_id,
                            "alert": bool(v.get("ok")), "konfidenz": konfidenz})
            if len(signale) >= max_alerts:
                break
        return {"ok": True, "signale": signale, "hinweise": hinweise, "geprueft": len(syms)}

    # -- Detail zu einem Wert (fuer die anklickbare Detailansicht) --
    def detail(self, symbol: str, asset: str = "aktie") -> dict:
        symbol = (symbol or "").strip()
        if not symbol:
            return {"ok": False, "fehler": "Kein Symbol."}
        if asset == "krypto":
            d = self.market.crypto_detail(symbol)
            return {"ok": d.get("ok", False), "asset": "krypto", "symbol": symbol, "info": d}
        sym = symbol.upper()
        quote = self.market.aktie_quote(symbol)
        profil = self.market.aktie_profil(symbol)
        news = self.market.aktie_news(symbol)
        rsi = getattr(self.market, "aktie_rsi", lambda _s: None)(symbol)  # best-effort (AV-Free-Limit)
        links = [
            {"label": "SEC-Filings (EDGAR)", "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={sym}&type=10-K&dateb=&owner=include&count=10"},
            {"label": "Chart (TradingView)", "url": f"https://www.tradingview.com/symbols/{sym}/"},
        ]
        if profil.get("ok") and profil.get("web"):
            links.insert(0, {"label": "Unternehmens-Website", "url": profil["web"]})
        return {"ok": True, "asset": "aktie", "symbol": sym,
                "quote": quote if quote.get("ok") else None,
                "profil": profil if profil.get("ok") else None,
                "rsi": rsi, "links": links,
                "news": news.get("news", []) if news.get("ok") else [],
                "hinweise": [x.get("hinweis") for x in (quote, profil, news) if x.get("fall_b")]}

    # -- 3) Wochenprognose + Scorecard --
    def _aktueller_preis(self, symbol: str, asset: str):
        if asset == "krypto":
            c = self.market.crypto_preis([symbol], vs="eur")
            return _zahl((c.get("preise", {}).get(symbol) or {}).get("eur")) if c.get("ok") else None
        q = self.market.aktie_quote(symbol)
        return _zahl(q.get("preis")) if q.get("ok") else None

    def wochenprognose(self) -> dict:
        erstellt = []
        for w in self.store.watchlist():
            sym, asset = w["symbol"], w.get("asset", "aktie")
            chg, basis = 0.0, None
            if asset == "krypto":
                c = self.market.crypto_preis([sym], vs="eur")
                if c.get("ok"):
                    v = c["preise"].get(sym) or {}
                    chg = _zahl(v.get("eur_24h_change")); basis = _zahl(v.get("eur")) or None
            else:
                q = self.market.aktie_quote(sym)
                if q.get("ok"):
                    chg = _zahl(q.get("veraenderung_pct")); basis = _zahl(q.get("preis")) or None
            richtung = "steigt" if chg > 1 else ("faellt" if chg < -1 else "seitwaerts")
            konfidenz = min(0.8, 0.5 + abs(chg) / 100.0)
            fid = self.store.forecast_add(sym, prognose=richtung, konfidenz=konfidenz, horizont="1W",
                                          rationale=f"Momentum {chg:+.1f}%", basis_preis=basis, asset=asset)
            erstellt.append({"symbol": sym, "prognose": richtung, "konfidenz": round(konfidenz, 2),
                             "forecast_id": fid})
        return {"ok": True, "prognosen": erstellt}

    def scorecard_aktualisieren(self, *, tage: int = 7, jetzt=None) -> dict:
        """Walk-forward: faellige Prognosen (aelter als `tage`) gegen den aktuellen Kurs auswerten
        -> Actual (Wochen-Rendite %) speichern. Bei starker Abweichung Anomalie melden."""
        from datetime import datetime, timedelta
        jetzt = jetzt or datetime.now()
        bewertet = {a.get("bezug_forecast") for a in self.store.list("actuals")}
        neu = 0
        for f in self.store.list("forecasts"):
            fid = f.get("id")
            if fid in bewertet:
                continue
            try:
                ts = datetime.fromisoformat(f.get("ts", ""))
            except ValueError:
                continue
            if (jetzt - ts) < timedelta(days=tage):
                continue  # Horizont noch nicht erreicht
            basis = _zahl(f.get("basis_preis"))
            akt = self._aktueller_preis(f.get("symbol"), f.get("asset", "aktie"))
            if not basis or not akt:
                continue
            ret = round((akt - basis) / basis * 100, 2)
            self.store.actual_add(f.get("symbol"), wert=ret, bezug_forecast=fid)
            neu += 1
            # Anomalie-Obduktion: Prognose lag deutlich daneben -> melden (Researcher-Hook spaeter)
            if self.notify and not _traf_zu(f, {"wert": ret}) and abs(ret) >= 8:
                try:
                    self.notify(f"Prognose-Anomalie {f.get('symbol')}: erwartet '{f.get('prognose')}', "
                                f"real {ret:+.1f}% in {tage}T. Ursache pruefen.",
                                abteilung="CIO", kategorie="investment")
                except Exception:
                    pass
        return {"neu_bewertet": neu, "scorecard": self.scorecard()}

    def scorecard(self) -> dict:
        forecasts = self.store.list("forecasts")
        actuals = {a.get("bezug_forecast"): a for a in self.store.list("actuals")}
        bewertet = [f for f in forecasts if f.get("id") in actuals]
        treffer = sum(1 for f in bewertet if _traf_zu(f, actuals[f["id"]]))
        fehler = [abs(_zahl(actuals[f["id"]].get("wert"))) for f in bewertet]
        return {"prognosen_gesamt": len(forecasts), "ausgewertet": len(bewertet),
                "treffer": treffer,
                "trefferquote": round(treffer / len(bewertet), 2) if bewertet else None,
                "mittlerer_betrag_pct": round(sum(fehler) / len(fehler), 1) if fehler else None}


def _traf_zu(forecast: dict, actual: dict) -> bool:
    chg = _zahl(actual.get("wert"))
    p = forecast.get("prognose")
    return (p == "steigt" and chg > 0) or (p == "faellt" and chg < 0) or (p == "seitwaerts" and abs(chg) <= 1)


def _zahl(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _geld(x) -> str:
    """Kompakte Geldangabe (Form 4 = US-Filings -> USD), deutsche Tausenderpunkte."""
    try:
        return f"{float(x):,.0f} USD".replace(",", ".")
    except (TypeError, ValueError):
        return "? USD"
