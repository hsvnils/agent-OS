"""7-Tage-Prognose + Abgleich + Abweichungs-Register (Walk-Forward-Lern-Loop, Schritt 2).

Zum Zeitpunkt T erstellt der Forecaster je Watchlist-Wert eine Prognose fuer T+7 (Richtung + Renditespanne +
Konfidenz, getaggt mit `modell_version`). Nach Ablauf gleicht `auswerten()` sie mit der eingetretenen Realitaet
ab und schreibt je Prognose EINEN Eintrag ins **separate, dauerhafte Abweichungs-Register** (`inv_deviations`)
-- inklusive Vergleich gegen eine **naive Baseline** (Random-Walk: erwartete 7-Tage-Rendite = 0 %). Nur so ist
"besser als die Messlatte?" und "wird der Fehler ueber die Zeit kleiner?" messbar.

Startmodell `v1-momentum` ist bewusst einfach + ehrlich (gedaempfte Momentum-Fortschreibung). Es ist der
Nullpunkt, den kuenftige Anreicherung schlagen muss. Keine Trades, keine Geldbewegungen.
"""
from __future__ import annotations

import math
import statistics
import uuid
from datetime import date, timedelta

from .signals import berechne as berechne_signale
from .signals import insider_signal as _insider_signal

SCHWELLE_PCT = 1.0   # ab hier gilt eine Bewegung als steigt/faellt (sonst seitwaerts)

# v4 = Insider-Discovery: nicht auf feste Universe geschraubt, sondern Werte MIT frischem Form-4-Cluster-Kauf.
# Eigener 30-Tage-Horizont (Insider-Edge wirkt ueber Wochen-Monate, nicht 7 Tage). Version traegt den Horizont
# im Namen -> im Dashboard sofort erkennbar, dass v4 NICHT 1:1 gegen die 7-Tage-MAE von v2/v3 zu lesen ist.
MODELL_VERSION_INSIDER = "v4-insider-30d"
INSIDER_HORIZONT_TAGE = 30


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _richtung(ret_pct: float) -> str:
    if ret_pct > SCHWELLE_PCT:
        return "steigt"
    if ret_pct < -SCHWELLE_PCT:
        return "faellt"
    return "seitwaerts"


class Forecaster:
    HORIZONT_TAGE = 7
    MODELL_VERSION = "v3-perasset"   # Aktien=Momentum, Krypto=Mean-Reversion, gedaempfte Magnitude
    MIN_HISTORIE = 6      # ohne genug Historie keine Prognose

    def __init__(self, store):
        self.store = store   # investment.loop_store.LoopStore

    # -- 1) Prognose T -> T+7 --
    def prognostizieren(self, watchlist, *, datum: str | None = None) -> dict:
        datum = datum or date.today().isoformat()
        faellig = (date.fromisoformat(datum) + timedelta(days=self.HORIZONT_TAGE)).isoformat()
        schon = {(f.get("symbol"), f.get("erstellt_am")) for f in self.store.list("inv_forecasts")}
        erstellt, uebersprungen = [], []
        for w in watchlist:
            sym = (w.get("symbol") or "").upper()
            asset = w.get("asset", "aktie")
            if not sym or (sym, datum) in schon:
                uebersprungen.append(sym)
                continue
            hist = self.store.features_for(sym)
            closes = [_num(h["close"]) for h in hist if _num(h["close"]) > 0]
            if len(closes) < self.MIN_HISTORIE:
                uebersprungen.append(sym)
                continue
            ff = forecast_fields(closes, asset)
            fid = str(uuid.uuid4())
            self.store.forecast_add({
                "id": fid, "symbol": sym, "asset": asset, "erstellt_am": datum, "faellig_am": faellig,
                "richtung": ff["richtung"], "ziel_return_pct": ff["ziel_return_pct"],
                "spanne_low": ff["spanne_low"], "spanne_high": ff["spanne_high"],
                "konfidenz": ff["konfidenz"], "modell_version": self.MODELL_VERSION,
                "signale": ff["signale"], "signale_zahl": ff["signale_zahl"], "treiber": ff["treiber"],
                "features_ref": {"ret_5d": ff["ret_5d"], "vola_20d": ff["vola_20d"], "basis_close": ff["basis_close"]},
                "rationale": ff["rationale"],
                "baseline_richtung": "seitwaerts", "baseline_return_pct": 0.0, "status": "offen"})
            erstellt.append(sym)
        return {"ok": True, "datum": datum, "faellig_am": faellig, "erstellt": erstellt,
                "uebersprungen": uebersprungen}

    # -- 2) Abgleich faelliger Prognosen -> Abweichungs-Register --
    def auswerten(self, *, heute: str | None = None) -> dict:
        heute = heute or date.today().isoformat()
        fertig = {d.get("forecast_id") for d in self.store.list("inv_deviations")}
        neu = 0
        for f in self.store.list("inv_forecasts"):
            fid = f.get("id")
            if fid in fertig or (f.get("faellig_am") or "9999-99-99") > heute:
                continue
            basis = _num((f.get("features_ref") or {}).get("basis_close"))
            hist = self.store.features_for(f.get("symbol"))
            real_close = next((_num(h["close"]) for h in reversed(hist)
                               if (h.get("datum") or "") >= f.get("faellig_am", "")), None)
            if not basis or not real_close:
                continue                                       # Realitaet noch nicht erfasst -> spaeter
            real_ret = round((real_close / basis - 1) * 100, 3)
            ziel = _num(f.get("ziel_return_pct"))
            fehler = round(abs(ziel - real_ret), 3)
            base_fehler = round(abs(_num(f.get("baseline_return_pct")) - real_ret), 3)
            self.store.actual_add({"forecast_id": fid, "symbol": f.get("symbol"),
                                   "faellig_am": f.get("faellig_am"), "real_return_pct": real_ret,
                                   "real_richtung": _richtung(real_ret)})
            self.store.deviation_add({
                "forecast_id": fid, "symbol": f.get("symbol"), "asset": f.get("asset", "aktie"),
                "modell_version": f.get("modell_version"), "signale": f.get("treiber", []), "backtest": False,
                "erstellt_am": f.get("erstellt_am"), "faellig_am": f.get("faellig_am"),
                "prognose_return_pct": ziel, "real_return_pct": real_ret, "fehler_abs_pct": fehler,
                "richtungstreffer": f.get("richtung") == _richtung(real_ret),
                "baseline_fehler_abs_pct": base_fehler, "besser_als_baseline": fehler < base_fehler,
                "konfidenz": _num(f.get("konfidenz")),
                "regime": _regime(_num((f.get("features_ref") or {}).get("vola_20d")))})
            neu += 1
        return {"ok": True, "neu_bewertet": neu, "kennzahlen": self.kennzahlen()}

    # -- 3) Kennzahlen aus dem Register (wird der Fehler kleiner? -- gesamt, je Version, je Anlageklasse) --
    def kennzahlen(self) -> dict:
        devs = self.store.list("inv_deviations")
        if not devs:
            return {"n": 0}
        je_version: dict[str, list] = {}
        je_asset: dict[str, list] = {}
        je_signal: dict[str, list] = {}
        for d in devs:
            je_version.setdefault(d.get("modell_version", "?"), []).append(d)
            je_asset.setdefault(d.get("asset", "aktie"), []).append(d)
            for typ in (d.get("signale") or []):        # Attribution: je Signaltyp, der die Richtung trug
                je_signal.setdefault(typ, []).append(d)
        return {"gesamt": _agg(devs),
                "je_version": {k: _agg(v) for k, v in je_version.items()},
                "je_asset": {k: _agg(v) for k, v in je_asset.items()},
                "je_signal": {k: _agg(v) for k, v in je_signal.items()}}

    def live_gesamt(self) -> dict:
        """Aggregat NUR der Live-Auswertungen (Backtest ausgenommen) -- Basis fuer die Autonomie-Freischaltung.
        Backtest fuellt das Dashboard, darf aber echtes autonomes Handeln nicht freischalten."""
        return _agg([d for d in self.store.list("inv_deviations") if not d.get("backtest")])

    # -- 4) Chancen AUSSERHALB der Watchlist (Vorschlaege) --
    def chancen(self, watchlist_symbols, *, max_n: int = 5, min_konfidenz: float = 0.6) -> list[dict]:
        """Aus dem juengsten Prognose-Lauf die staerksten bullischen Werte, die NICHT auf der Watchlist stehen.
        Der Loop reicht sie durch den Risk-Agent (engine.vorschlag) -> Alert. So kommen Vorschlaege von aussen."""
        fcs = self.store.list("inv_forecasts")
        if not fcs:
            return []
        letzter = fcs[-1].get("erstellt_am")
        wl = {(s or "").upper() for s in watchlist_symbols}
        kand = [f for f in fcs
                if f.get("erstellt_am") == letzter and (f.get("symbol") or "").upper() not in wl
                and f.get("richtung") == "steigt" and _num(f.get("konfidenz")) >= min_konfidenz]
        kand.sort(key=lambda f: _num(f.get("konfidenz")), reverse=True)
        return [{"symbol": f.get("symbol"), "asset": f.get("asset", "aktie"),
                 "ziel_return_pct": _num(f.get("ziel_return_pct")), "konfidenz": _num(f.get("konfidenz")),
                 "signale_zahl": int(_num(f.get("signale_zahl"))), "rationale": f.get("rationale", "")}
                for f in kand[:max_n]]


    # -- 5) Fehler-Verlauf je Auswertungs-Woche (wird der Fehler ueber die Zeit kleiner?) --
    def verlauf(self) -> list[dict]:
        buckets: dict[str, list] = {}
        for d in self.store.list("inv_deviations"):
            wk = _iso_woche(d.get("faellig_am"))
            if wk:
                buckets.setdefault(wk, []).append(d)
        out = []
        for wk in sorted(buckets):
            v = buckets[wk]
            out.append({"woche": wk, "n": len(v),
                        "mae_pct": round(sum(_num(x.get("fehler_abs_pct")) for x in v) / len(v), 3),
                        "baseline_mae_pct": round(sum(_num(x.get("baseline_fehler_abs_pct")) for x in v) / len(v), 3)})
        return out


DAEMPFUNG = 0.3   # gedaempfte Magnitude (war 0.5) -- das Modell ueberschoss (MAE > Baseline)


def forecast_fields(closes: list[float], asset: str = "aktie") -> dict:
    """Kern des v3-Modells: aus einer Close-Reihe (bis zum As-of-Tag) die Prognose-Felder bauen.
    **Aktien/ETF = Momentum** (Trend setzt sich fort), **Krypto = Mean-Reversion** (Signale invertiert -- 7-Tage-
    Krypto lief in der Historie gegen den Trend). Magnitude gedaempft. Pure Funktion -- live UND Backtest."""
    basis = closes[-1]
    ret5 = round((basis / closes[-6] - 1) * 100, 3) if len(closes) > 5 and closes[-6] > 0 else 0.0
    tages = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1] > 0]
    vola = round(statistics.pstdev(tages[-20:]) * 100, 3) if len(tages) >= 2 else 0.0
    signale = berechne_signale(closes)
    krypto = (asset == "krypto")

    def eff(s):   # effektive Richtung nach Anlageklassen-Haltung (Krypto: invertiert = Mean-Reversion)
        if s["richtung"] == "neutral" or not krypto:
            return s["richtung"]
        return "faellt" if s["richtung"] == "steigt" else "steigt"

    up = sum(1 for s in signale if eff(s) == "steigt")
    dn = sum(1 for s in signale if eff(s) == "faellt")
    if up > dn:
        richtung, zahl = "steigt", up
    elif dn > up:
        richtung, zahl = "faellt", dn
    else:
        richtung, zahl = "seitwaerts", 0
    betrag = abs(round(DAEMPFUNG * ret5, 3))
    ziel = betrag if richtung == "steigt" else (-betrag if richtung == "faellt" else 0.0)
    band = round(vola * math.sqrt(Forecaster.HORIZONT_TAGE), 3)
    konf = round(min(0.9, 0.4 + 0.15 * zahl + abs(ziel) / 60.0), 2)
    treiber = [s["typ"] for s in signale if eff(s) == richtung and richtung != "seitwaerts"]
    stance = "mean-reversion" if krypto else "momentum"
    return {"richtung": richtung, "ziel_return_pct": ziel, "spanne_low": round(ziel - band, 3),
            "spanne_high": round(ziel + band, 3), "konfidenz": konf, "signale_zahl": zahl, "treiber": treiber,
            "signale": [{"typ": s["typ"], "richtung": s["richtung"]} for s in signale],
            "ret_5d": ret5, "vola_20d": vola, "basis_close": basis,
            "rationale": f"{zahl}/{len(signale)} Signale fuer {richtung} ({stance}: {', '.join(treiber) or 'uneins'})"}


INSIDER_DAEMPFUNG = 0.3   # gedaempfte Magnitude auf 30-Tage-Sicht (wie v3 -- ehrlich, kein Ueberschiessen)


def insider_forecast_fields(closes: list[float], insider: dict, *, horizont: int = INSIDER_HORIZONT_TAGE) -> dict:
    """Kern des v4-Modells (Insider-Discovery). Prognose fuer einen Wert MIT frischem Insider-KAUF-Cluster.
    Das Insider-Signal ist der **Haupttreiber** (bullisch); die Preis-Signale (Momentum/Trend/Breakout) reiten
    nur als Bestaetigung mit. `insider` = {cluster:int, summe:float, ...}. Pure Funktion -- live UND Backtest.
    Gibt bewusst dieselben Felder wie `forecast_fields` zurueck (Register/Dashboard sind versions-agnostisch)."""
    basis = closes[-1]
    ret5 = round((basis / closes[-6] - 1) * 100, 3) if len(closes) > 5 and closes[-6] > 0 else 0.0
    tages = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1] > 0]
    vola = round(statistics.pstdev(tages[-20:]) * 100, 3) if len(tages) >= 2 else 0.0
    cluster = int(_num(insider.get("cluster")))
    summe = _num(insider.get("summe"))
    isig = _insider_signal(cluster, summe)
    preis_signale = berechne_signale(closes)
    signale = [isig] + preis_signale

    # Insider entscheidet die Richtung (steigt); Preis-Signale modulieren nur Betrag/Konfidenz.
    richtung = "steigt"
    bestaetigend = sum(1 for s in preis_signale if s["richtung"] == "steigt")
    widersprechend = sum(1 for s in preis_signale if s["richtung"] == "faellt")
    zahl = 1 + bestaetigend                                   # Insider + zustimmende Preis-Signale
    # Erwartete 30-Tage-Rendite: Insider-Basis + gedaempftes Momentum, gedaempft bei Preis-Gegenwind.
    basis_ret = 2.0 + 1.0 * max(0, cluster - 1)               # Insider-Grundhaltung (bullisch), waechst mit Cluster
    momentum_add = INSIDER_DAEMPFUNG * max(0.0, ret5)
    gegenwind = 1.0 - 0.15 * widersprechend
    ziel = round(max(0.0, (basis_ret + momentum_add) * max(0.4, gegenwind)) * isig["staerke"] / 0.5, 3)
    band = round(vola * math.sqrt(horizont), 3)
    konf = round(min(0.9, 0.4 + 0.1 * cluster + 0.05 * bestaetigend + min(0.2, summe / 1_000_000.0)), 2)
    treiber = ["insider"] + [s["typ"] for s in preis_signale if s["richtung"] == "steigt"]
    return {"richtung": richtung, "ziel_return_pct": ziel, "spanne_low": round(ziel - band, 3),
            "spanne_high": round(ziel + band, 3), "konfidenz": konf, "signale_zahl": zahl, "treiber": treiber,
            "signale": [{"typ": s["typ"], "richtung": s["richtung"]} for s in signale],
            "ret_5d": ret5, "vola_20d": vola, "basis_close": basis,
            "rationale": f"Insider-Cluster ({cluster} Kaeufer, ~{summe:,.0f} USD) + {bestaetigend} bestaetigende "
                         f"Preis-Signale -> steigt auf {horizont}T"}


def _iso_woche(datum: str) -> str:
    try:
        y, w, _ = date.fromisoformat((datum or "")[:10]).isocalendar()
        return f"{y}-W{w:02d}"
    except (ValueError, TypeError):
        return ""


def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "mae_pct": round(sum(_num(d.get("fehler_abs_pct")) for d in rows) / n, 3),
        "baseline_mae_pct": round(sum(_num(d.get("baseline_fehler_abs_pct")) for d in rows) / n, 3),
        "richtungsquote": round(sum(1 for d in rows if d.get("richtungstreffer")) / n, 3),
        "anteil_besser_baseline": round(sum(1 for d in rows if d.get("besser_als_baseline")) / n, 3),
    }


def _regime(vola: float) -> str:
    return "hohe_vola" if vola >= 3.0 else "niedrige_vola"
