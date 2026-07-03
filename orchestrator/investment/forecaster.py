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

SCHWELLE_PCT = 1.0   # ab hier gilt eine Bewegung als steigt/faellt (sonst seitwaerts)


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
    MODELL_VERSION = "v1-momentum"
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
            basis = closes[-1]
            ret5 = round((basis / closes[-6] - 1) * 100, 3) if closes[-6] > 0 else 0.0
            tages = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1] > 0]
            vola = round(statistics.pstdev(tages[-20:]) * 100, 3) if len(tages) >= 2 else 0.0
            ziel = round(0.5 * ret5, 3)                       # gedaempfte Momentum-Fortschreibung
            band = round(vola * math.sqrt(self.HORIZONT_TAGE), 3)
            konf = round(min(0.85, 0.4 + abs(ziel) / 50.0), 2)
            fid = str(uuid.uuid4())
            self.store.forecast_add({
                "id": fid, "symbol": sym, "asset": asset, "erstellt_am": datum, "faellig_am": faellig,
                "richtung": _richtung(ziel), "ziel_return_pct": ziel,
                "spanne_low": round(ziel - band, 3), "spanne_high": round(ziel + band, 3),
                "konfidenz": konf, "modell_version": self.MODELL_VERSION,
                "features_ref": {"ret_5d": ret5, "vola_20d": vola, "basis_close": basis},
                "rationale": f"Momentum {ret5:+.1f}% gedaempft (v1)",
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
                "forecast_id": fid, "symbol": f.get("symbol"), "modell_version": f.get("modell_version"),
                "erstellt_am": f.get("erstellt_am"), "faellig_am": f.get("faellig_am"),
                "prognose_return_pct": ziel, "real_return_pct": real_ret, "fehler_abs_pct": fehler,
                "richtungstreffer": f.get("richtung") == _richtung(real_ret),
                "baseline_fehler_abs_pct": base_fehler, "besser_als_baseline": fehler < base_fehler,
                "konfidenz": _num(f.get("konfidenz")),
                "regime": _regime(_num((f.get("features_ref") or {}).get("vola_20d")))})
            neu += 1
        return {"ok": True, "neu_bewertet": neu, "kennzahlen": self.kennzahlen()}

    # -- 3) Kennzahlen aus dem Register (wird der Fehler kleiner?) --
    def kennzahlen(self) -> dict:
        devs = self.store.list("inv_deviations")
        if not devs:
            return {"n": 0}
        je_version: dict[str, list] = {}
        for d in devs:
            je_version.setdefault(d.get("modell_version", "?"), []).append(d)
        return {"gesamt": _agg(devs), "je_version": {k: _agg(v) for k, v in je_version.items()}}


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
