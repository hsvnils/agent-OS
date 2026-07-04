"""Historie-Backfill + rueckwirkender Backtest (fuellt den Walk-Forward-Loop sofort).

Zieht echte **Tageskurs-Historie** (Alpha Vantage fuer Aktie/ETF, CoinGecko fuer Krypto) fuer Watchlist +
Universum + Benchmarks und schreibt sie als `inv_features`-Zeilen (mit denselben abgeleiteten Merkmalen wie
live gesammelte). Danach ein **Backtest ohne Look-ahead**: an woechentlichen As-of-Tagen wird -- nur aus der bis
dahin bekannten Historie -- eine Prognose gebildet und gegen den 7-Tage-spaeter tatsaechlich eingetretenen Kurs
ausgewertet -> Eintraege ins **Abweichungs-Register** (`backtest=True`). So sind KPIs/Fehler-Verlauf/Register
sofort mit echten Daten gefuellt. Backtest schaltet **keine** autonome Ausfuehrung frei (nur Live-Beweis zaehlt).

Backtest-Schreibvorgaenge laufen bewusst gegen einen **lokalen** LoopStore (kein Supabase-Write-through) --
Massen-Backfill soll nicht Tausende HTTP-Upserts ausloesen.
"""
from __future__ import annotations

from datetime import date, timedelta

from .features import derive
from .forecaster import Forecaster, forecast_fields


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _richtung(ret_pct: float) -> str:
    if ret_pct > 1.0:
        return "steigt"
    if ret_pct < -1.0:
        return "faellt"
    return "seitwaerts"


def _iso_woche(datum: str) -> str:
    try:
        y, w, _ = date.fromisoformat((datum or "")[:10]).isocalendar()
        return f"{y}-W{w:02d}"
    except (ValueError, TypeError):
        return ""


class Backfill:
    def __init__(self, market, store):
        self.market = market      # investment.providers.MarketData
        self.store = store        # investment.loop_store.LoopStore (idealerweise lokal, ohne Supabase)

    def lade_historie(self, ziele, *, seit: str = "2026-01-01") -> dict:
        """ziele: [{symbol, asset}]. Holt Historie >= `seit` und schreibt fehlende inv_features-Zeilen."""
        heute = date.today()
        tage = max(1, (heute - date.fromisoformat(seit)).days + 2)
        geladen, hinweise = 0, []
        for w in ziele:
            sym = (w.get("symbol") or "").strip()
            asset = w.get("asset", "aktie")
            if not sym:
                continue
            if asset == "krypto":
                r = self.market.crypto_historie(sym, tage=tage)
            else:                                             # Aktie/ETF: FMP (grosszuegiger) zuerst, dann Alpha Vantage
                r = self.market.aktie_historie_fmp(sym)
                if not r.get("ok"):
                    r = self.market.aktie_historie(sym, outputsize="compact")   # 'full' = AV-Premium -> compact (frei)
            if not r.get("ok"):
                hinweise.append(f"{sym}: {r.get('hinweis') or r.get('fehler') or 'nicht verfuegbar'}")
                continue
            items = sorted((t, _num(c)) for t, c in (r.get("closes") or {}).items() if t >= seit and _num(c) > 0)
            if not items:
                continue
            vorhanden = {e.get("datum") for e in self.store.list("inv_features") if e.get("symbol") == sym.upper()}
            reihe: list[float] = []
            for tag, close in items:
                reihe.append(close)
                if tag in vorhanden:
                    continue
                self.store.feature_add(sym, asset, tag, round(close, 6), 0.0, derive(reihe), quelle="backfill")
                geladen += 1
        return {"ok": True, "zeilen_neu": geladen, "hinweise": hinweise[:6]}

    def backtest(self, *, step_tage: int = 7, horizont: int = 7) -> dict:
        """Rueckwirkender Walk-Forward-Backtest ueber die vorhandene Historie -> Abweichungs-Register."""
        per_sym: dict = {}
        for e in self.store.list("inv_features"):
            per_sym.setdefault(e.get("symbol"), []).append(
                (e.get("datum"), _num(e.get("close")), e.get("asset", "aktie")))
        erledigt = {(d.get("symbol"), d.get("erstellt_am")) for d in self.store.list("inv_deviations")
                    if d.get("backtest")}
        neu = 0
        for sym, rows in per_sym.items():
            rows = sorted(r for r in rows if r[0] and r[1] > 0)
            if len(rows) < Forecaster.MIN_HISTORIE + 1:
                continue
            dates = [r[0] for r in rows]
            closes = [r[1] for r in rows]
            asset = rows[0][2]
            i = Forecaster.MIN_HISTORIE - 1
            while i < len(rows) - 1:
                d_i = dates[i]
                faellig = (date.fromisoformat(d_i) + timedelta(days=horizont)).isoformat()
                j = next((k for k in range(i + 1, len(rows)) if dates[k] >= faellig), None)
                if j is None:
                    break
                if (sym, d_i) not in erledigt:
                    ff = forecast_fields(closes[:i + 1])
                    real_ret = round((closes[j] / closes[i] - 1) * 100, 3) if closes[i] > 0 else 0.0
                    ziel = ff["ziel_return_pct"]
                    fehler = round(abs(ziel - real_ret), 3)
                    base_fehler = round(abs(real_ret), 3)          # naive Baseline = 0 %
                    self.store.deviation_add({
                        "symbol": sym, "asset": asset, "modell_version": Forecaster.MODELL_VERSION,
                        "signale": ff["treiber"], "backtest": True, "erstellt_am": d_i, "faellig_am": faellig,
                        "prognose_return_pct": ziel, "real_return_pct": real_ret, "fehler_abs_pct": fehler,
                        "richtungstreffer": ff["richtung"] == _richtung(real_ret),
                        "baseline_fehler_abs_pct": base_fehler, "besser_als_baseline": fehler < base_fehler,
                        "konfidenz": ff["konfidenz"], "regime": ("hohe_vola" if ff["vola_20d"] >= 3.0 else "niedrige_vola")})
                    neu += 1
                nxt = next((k for k in range(i + 1, len(rows)) if dates[k] >= (
                    date.fromisoformat(d_i) + timedelta(days=step_tage)).isoformat()), None)
                if nxt is None:
                    break
                i = nxt
        return {"ok": True, "auswertungen_neu": neu}
