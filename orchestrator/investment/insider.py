"""Modell v4 -- Insider-Discovery (SEC Form 4), 30-Tage-Horizont.

Anders als v2/v3 (feste Universe, reine Preis-Signale, 7 Tage) sucht v4 gezielt Werte MIT einem frischen
Insider-KAUF-Cluster und prognostiziert genau diese. Grund (empirisch geprueft 2026-07-04): Offenmarkt-Kaeufe
(Form-4-Code P) kommen bei Mega-Caps praktisch nie vor -- der dokumentierte Insider-Edge liegt bei Small/Mid-
Caps und abgestraften Werten. Darum ein eigenes **Screen-Universum** + **eigener, laengerer Horizont**.

Point-in-time-korrekt: ein Filing zaehlt erst ab seinem `filing_datum` (SEC-Meldung bis zu 2 Boersentage nach
der Transaktion). Der Backtest bildet an jedem As-of-Tag den Cluster NUR aus bis dahin gemeldeten Kaeufen --
kein Look-ahead.

Vollstaendig getrennt von v2/v3: schreibt eigene `inv_deviations` (modell_version=v4-insider-30d) bzw. eigene
`inv_forecasts`. Beruehrt die geteilte `inv_features` (v3-Backtest-Basis) NICHT -> v2/v3-Zahlen bleiben
unveraendert. Keine Trades, keine Geldbewegung -- advisory.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from .forecaster import INSIDER_HORIZONT_TAGE, MODELL_VERSION_INSIDER, insider_forecast_fields
from .insider_universe import INSIDER_SCREEN_UNIVERSE

LOOKBACK_TAGE = 90        # ein Cluster gilt, wenn die Kaeufe in den letzten 90 Tagen vor dem As-of-Tag gemeldet wurden
CLUSTER_MIN = 2           # >= 2 verschiedene kaufende Insider = Cluster
MIN_KAUF_WERT = 50_000.0  # ODER ein einzelner Grosskauf >= 50k USD
MIN_HISTORIE = 6          # ohne genug Kurs-Historie keine Prognose


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


class InsiderModel:
    """Kapselt v4: Kauf-Cluster-Erkennung (point-in-time), rueckwirkender Backtest und Live-Produktion."""

    def __init__(self, market, store):
        self.market = market     # investment.providers.MarketData
        self.store = store       # investment.loop_store.LoopStore

    # -- Datenzugriff --
    def _kaeufe(self, symbol: str, *, seit: str) -> list[dict]:
        """Alle Form-4-KAEUFE (Code P) eines Symbols ab `seit`, mit filing_datum + Wert. Ein Aufruf je Symbol."""
        r = self.market.insider_transactions(symbol, seit=seit)
        if not r.get("ok"):
            return []
        out = []
        for t in r.get("transaktionen", []):
            if t.get("transaktion") != "kauf":
                continue
            out.append({"insider": t.get("insider") or "",
                        "filing_datum": (t.get("filing_datum") or t.get("datum") or "")[:10],
                        "wert": _num(t.get("wert"))})
        return [k for k in out if k["filing_datum"]]

    def _cluster_at(self, kaeufe: list[dict], as_of: str) -> dict | None:
        """Aktiver Kauf-Cluster am Stichtag `as_of`: nur Filings, die bis `as_of` und innerhalb der Lookback-
        Frist gemeldet wurden. -> {cluster, summe, insider} oder None (kein auffaelliger Cluster)."""
        frueh = (date.fromisoformat(as_of) - timedelta(days=LOOKBACK_TAGE)).isoformat()
        fenster = [k for k in kaeufe if frueh <= k["filing_datum"] <= as_of]
        if not fenster:
            return None
        namen = sorted({k["insider"] for k in fenster if k["insider"]})
        cluster = len(namen)
        summe = round(sum(k["wert"] for k in fenster), 2)
        if cluster < CLUSTER_MIN and summe < MIN_KAUF_WERT:
            return None
        return {"cluster": cluster, "summe": summe, "insider": namen}

    def _preise(self, symbol: str) -> list[tuple[str, float]]:
        """Chronologische (datum, close)-Reihe via FMP (5 Jahre Free-Historie). Leer bei Ausfall."""
        r = self.market.aktie_historie_fmp(symbol)
        if not r.get("ok"):
            r = self.market.aktie_historie(symbol, outputsize="compact")
        if not r.get("ok"):
            return []
        return sorted((str(t)[:10], _num(c)) for t, c in (r.get("closes") or {}).items() if _num(c) > 0)

    # -- 1) Rueckwirkender Backtest (fuellt das Register/Dashboard sofort) --
    def backtest(self, *, seit: str = "2026-01-01", step_tage: int = 7,
                 horizont: int = INSIDER_HORIZONT_TAGE) -> dict:
        """Walk-Forward ueber das Screen-Universum: an woechentlichen As-of-Tagen NUR bei aktivem Insider-Cluster
        eine 30-Tage-Prognose bilden und gegen den tatsaechlich eingetretenen Kurs auswerten -> inv_deviations
        (backtest=True). Kein Look-ahead (nur bis `as_of` gemeldete Filings)."""
        erledigt = {(d.get("symbol"), d.get("erstellt_am"))
                    for d in self.store.list("inv_deviations")
                    if d.get("backtest") and d.get("modell_version") == MODELL_VERSION_INSIDER}
        # Insider-Historie muss vor dem ersten As-of-Tag beginnen (Lookback), darum grosszuegiger Vorlauf.
        insider_seit = (date.fromisoformat(seit) - timedelta(days=LOOKBACK_TAGE + 30)).isoformat()
        neu, geprueft, mit_signal, hinweise = 0, 0, 0, []
        for w in INSIDER_SCREEN_UNIVERSE:
            sym = (w.get("symbol") or "").upper()
            if not sym:
                continue
            geprueft += 1
            kaeufe = self._kaeufe(sym, seit=insider_seit)
            if not kaeufe:
                continue
            preise = self._preise(sym)
            if len(preise) < MIN_HISTORIE + 1:
                hinweise.append(f"{sym}: zu wenig Kurs-Historie")
                continue
            # Auf die relevante Zeitspanne begrenzte, indizierbare Reihe (Vorlauf fuer Momentum/Vola):
            vorlauf = (date.fromisoformat(seit) - timedelta(days=200)).isoformat()
            reihe = [(t, c) for t, c in preise if t >= vorlauf]
            d_index = [t for t, _ in reihe]
            closes = [c for _, c in reihe]
            i = MIN_HISTORIE - 1
            while i < len(reihe) - 1:
                as_of = d_index[i]
                if as_of < seit:
                    i += 1
                    continue
                cl = self._cluster_at(kaeufe, as_of)
                if cl:
                    faellig = (date.fromisoformat(as_of) + timedelta(days=horizont)).isoformat()
                    j = next((k for k in range(i + 1, len(reihe)) if d_index[k] >= faellig), None)
                    if j is None:
                        break                                  # Zukunft (as_of+30d) noch nicht eingetreten
                    if (sym, as_of) not in erledigt:
                        ff = insider_forecast_fields(closes[:i + 1], cl, horizont=horizont)
                        real_ret = round((closes[j] / closes[i] - 1) * 100, 3) if closes[i] > 0 else 0.0
                        ziel = ff["ziel_return_pct"]
                        fehler = round(abs(ziel - real_ret), 3)
                        base_fehler = round(abs(real_ret), 3)  # naive Baseline = 0 %
                        self.store.deviation_add({
                            "symbol": sym, "asset": "aktie", "modell_version": MODELL_VERSION_INSIDER,
                            "signale": ff["treiber"], "backtest": True, "erstellt_am": as_of, "faellig_am": faellig,
                            "prognose_return_pct": ziel, "real_return_pct": real_ret, "fehler_abs_pct": fehler,
                            "richtungstreffer": ff["richtung"] == _richtung(real_ret),
                            "baseline_fehler_abs_pct": base_fehler, "besser_als_baseline": fehler < base_fehler,
                            "konfidenz": ff["konfidenz"], "horizont_tage": horizont,
                            "insider_cluster": cl["cluster"], "insider_summe": cl["summe"],
                            "regime": ("hohe_vola" if ff["vola_20d"] >= 3.0 else "niedrige_vola")})
                        neu += 1
                    mit_signal += 1
                # naechster As-of-Tag (>= step_tage spaeter)
                nxt = next((k for k in range(i + 1, len(reihe))
                            if d_index[k] >= (date.fromisoformat(as_of) + timedelta(days=step_tage)).isoformat()), None)
                if nxt is None:
                    break
                i = nxt
        return {"ok": True, "auswertungen_neu": neu, "insider_wochen": mit_signal, "symbole_geprueft": geprueft,
                "hinweise": hinweise[:6], "modell_version": MODELL_VERSION_INSIDER}

    # -- 2) Live-Prognosen (out-of-sample -- sammeln fuer den echten Beweis) --
    def live_prognosen(self, *, datum: str | None = None, horizont: int = INSIDER_HORIZONT_TAGE) -> dict:
        """Je Screen-Symbol mit AKTUELL aktivem Cluster eine 30-Tage-Prognose in inv_forecasts schreiben
        (modell_version=v4-insider-30d). Dedup je (symbol, datum). Advisory, keine Trades."""
        datum = datum or date.today().isoformat()
        faellig = (date.fromisoformat(datum) + timedelta(days=horizont)).isoformat()
        seit = (date.fromisoformat(datum) - timedelta(days=LOOKBACK_TAGE)).isoformat()
        schon = {(f.get("symbol"), f.get("erstellt_am")) for f in self.store.list("inv_forecasts")
                 if f.get("modell_version") == MODELL_VERSION_INSIDER}
        erstellt, hinweise = [], []
        for w in INSIDER_SCREEN_UNIVERSE:
            sym = (w.get("symbol") or "").upper()
            if not sym or (sym, datum) in schon:
                continue
            kaeufe = self._kaeufe(sym, seit=seit)
            cl = self._cluster_at(kaeufe, datum) if kaeufe else None
            if not cl:
                continue
            preise = self._preise(sym)
            closes = [c for _, c in preise]
            if len(closes) < MIN_HISTORIE:
                hinweise.append(f"{sym}: zu wenig Kurs-Historie")
                continue
            ff = insider_forecast_fields(closes, cl, horizont=horizont)
            self.store.forecast_add({
                "id": str(uuid.uuid4()), "symbol": sym, "asset": "aktie", "erstellt_am": datum,
                "faellig_am": faellig, "richtung": ff["richtung"], "ziel_return_pct": ff["ziel_return_pct"],
                "spanne_low": ff["spanne_low"], "spanne_high": ff["spanne_high"], "konfidenz": ff["konfidenz"],
                "modell_version": MODELL_VERSION_INSIDER, "signale": ff["signale"],
                "signale_zahl": ff["signale_zahl"], "treiber": ff["treiber"], "horizont_tage": horizont,
                "insider_cluster": cl["cluster"], "insider_summe": cl["summe"],
                "features_ref": {"ret_5d": ff["ret_5d"], "vola_20d": ff["vola_20d"], "basis_close": ff["basis_close"]},
                "rationale": ff["rationale"], "baseline_richtung": "seitwaerts", "baseline_return_pct": 0.0,
                "status": "offen"})
            erstellt.append(sym)
        return {"ok": True, "datum": datum, "faellig_am": faellig, "erstellt": erstellt, "hinweise": hinweise[:6]}

    # -- 3) Auswertung faelliger Live-Prognosen (eigener Pfad -- unabhaengig von inv_features) --
    def auswerten(self, *, heute: str | None = None) -> dict:
        """Faellige v4-Live-Prognosen gegen den real eingetretenen Kurs (FMP) abgleichen -> inv_deviations."""
        heute = heute or date.today().isoformat()
        fertig = {d.get("forecast_id") for d in self.store.list("inv_deviations") if d.get("forecast_id")}
        preis_cache: dict[str, list[tuple[str, float]]] = {}
        neu = 0
        for f in self.store.list("inv_forecasts"):
            if f.get("modell_version") != MODELL_VERSION_INSIDER:
                continue
            fid = f.get("id")
            if fid in fertig or (f.get("faellig_am") or "9999-99-99") > heute:
                continue
            basis = _num((f.get("features_ref") or {}).get("basis_close"))
            sym = (f.get("symbol") or "").upper()
            if sym not in preis_cache:
                preis_cache[sym] = self._preise(sym)
            real_close = next((c for t, c in preis_cache[sym] if t >= f.get("faellig_am", "")), None)
            if not basis or not real_close:
                continue
            real_ret = round((real_close / basis - 1) * 100, 3)
            ziel = _num(f.get("ziel_return_pct"))
            fehler = round(abs(ziel - real_ret), 3)
            base_fehler = round(abs(real_ret), 3)
            self.store.deviation_add({
                "forecast_id": fid, "symbol": sym, "asset": "aktie", "modell_version": MODELL_VERSION_INSIDER,
                "signale": f.get("treiber", []), "backtest": False, "erstellt_am": f.get("erstellt_am"),
                "faellig_am": f.get("faellig_am"), "prognose_return_pct": ziel, "real_return_pct": real_ret,
                "fehler_abs_pct": fehler, "richtungstreffer": f.get("richtung") == _richtung(real_ret),
                "baseline_fehler_abs_pct": base_fehler, "besser_als_baseline": fehler < base_fehler,
                "konfidenz": _num(f.get("konfidenz")), "horizont_tage": int(_num(f.get("horizont_tage")) or INSIDER_HORIZONT_TAGE),
                "insider_cluster": f.get("insider_cluster"), "insider_summe": f.get("insider_summe"),
                "regime": ("hohe_vola" if _num((f.get("features_ref") or {}).get("vola_20d")) >= 3.0 else "niedrige_vola")})
            neu += 1
        return {"ok": True, "neu_bewertet": neu}
