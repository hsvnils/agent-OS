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
MARKT_BENCHMARK = "SPY"   # Marktdrift-Kontrolle: Vergleich gegen den Gesamtmarkt ueber dasselbe 30-Tage-Fenster
KONTROLLE_TYP = "insider_markt_kontrolle"


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

    @staticmethod
    def _ret_ueber(reihe: list[tuple[str, float]], von: str, bis: str) -> float | None:
        """Prozentuale Rendite einer (datum, close)-Reihe vom ersten Kurs >= `von` bis zum ersten Kurs >= `bis`."""
        c0 = next((c for t, c in reihe if t >= von), None)
        c1 = next((c for t, c in reihe if t >= bis), None)
        if not c0 or not c1 or c0 <= 0:
            return None
        return round((c1 / c0 - 1) * 100, 3)

    # -- 1) Rueckwirkender Backtest + Marktdrift-Kontrolle (fuellt das Register/Dashboard sofort) --
    def backtest(self, *, seit: str = "2026-01-01", step_tage: int = 7,
                 horizont: int = INSIDER_HORIZONT_TAGE) -> dict:
        """Walk-Forward ueber das Screen-Universum: an woechentlichen As-of-Tagen NUR bei aktivem Insider-Cluster
        eine 30-Tage-Prognose bilden und gegen den tatsaechlich eingetretenen Kurs auswerten -> inv_deviations
        (backtest=True). Kein Look-ahead (nur bis `as_of` gemeldete Filings).

        **Marktdrift-Kontrolle:** je Fenster wird zusaetzlich der SPY-Return ueber DASSELBE 30-Tage-Fenster
        berechnet. So laesst sich trennen, ob Insider-Werte den Markt schlagen (echter Edge) oder nur mit dem
        Markt mitsteigen. Zusaetzlich eine **Basisrate** ueber ALLE Wochen-Fenster (auch ohne Insider) -- der
        Vergleichsmassstab fuer die Insider-Trefferquote. Die Kontrolle wird als Summary (inv_model_runs)
        gespeichert (frisch je Lauf, unabhaengig von schon persistierten Zeilen)."""
        erledigt = {(d.get("symbol"), d.get("erstellt_am"))
                    for d in self.store.list("inv_deviations")
                    if d.get("backtest") and d.get("modell_version") == MODELL_VERSION_INSIDER}
        # Insider-Historie muss vor dem ersten As-of-Tag beginnen (Lookback), darum grosszuegiger Vorlauf.
        insider_seit = (date.fromisoformat(seit) - timedelta(days=LOOKBACK_TAGE + 30)).isoformat()
        spy = self._preise(MARKT_BENCHMARK)                    # Benchmark einmal laden (Marktdrift-Referenz)
        neu, geprueft, mit_signal, hinweise = 0, 0, 0, []
        # In-Memory-Zaehler fuer die Kontroll-Summary (frisch je Lauf):
        ins_n = ins_up = ins_beat = 0; ins_alpha = 0.0         # Insider-Fenster
        bas_n = bas_up = bas_beat = bas_markt_n = 0            # alle Wochen-Fenster (Basisrate)
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
                faellig = (date.fromisoformat(as_of) + timedelta(days=horizont)).isoformat()
                j = next((k for k in range(i + 1, len(reihe)) if d_index[k] >= faellig), None)
                if j is None:
                    break                                      # Zukunft (as_of+30d) noch nicht eingetreten
                real_ret = round((closes[j] / closes[i] - 1) * 100, 3) if closes[i] > 0 else 0.0
                markt_ret = self._ret_ueber(spy, as_of, faellig)   # SPY ueber dasselbe Fenster (None ohne Benchmark)
                schlaegt_markt = (markt_ret is not None and real_ret > markt_ret)
                # Basisrate: JEDES Wochen-Fenster (unkonditioniert) -- der ehrliche Vergleichsmassstab.
                bas_n += 1
                bas_up += 1 if real_ret > 1.0 else 0
                if markt_ret is not None:
                    bas_markt_n += 1
                    bas_beat += 1 if schlaegt_markt else 0
                cl = self._cluster_at(kaeufe, as_of)
                if cl:
                    mit_signal += 1
                    ff = insider_forecast_fields(closes[:i + 1], cl, horizont=horizont)
                    ins_n += 1
                    ins_up += 1 if real_ret > 1.0 else 0
                    if markt_ret is not None:
                        ins_beat += 1 if schlaegt_markt else 0
                        ins_alpha += real_ret - markt_ret
                    if (sym, as_of) not in erledigt:
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
                            "markt_return_pct": markt_ret, "schlaegt_markt": schlaegt_markt,
                            "excess_return_pct": (round(real_ret - markt_ret, 3) if markt_ret is not None else None),
                            "regime": ("hohe_vola" if ff["vola_20d"] >= 3.0 else "niedrige_vola")})
                        neu += 1
                # naechster As-of-Tag (>= step_tage spaeter)
                nxt = next((k for k in range(i + 1, len(reihe))
                            if d_index[k] >= (date.fromisoformat(as_of) + timedelta(days=step_tage)).isoformat()), None)
                if nxt is None:
                    break
                i = nxt
        kontrolle = self._kontroll_summary(seit, horizont, spy_ok=bool(spy),
                                            ins=(ins_n, ins_up, ins_beat, ins_alpha),
                                            bas=(bas_n, bas_up, bas_beat, bas_markt_n))
        self.store.model_run_add(kontrolle)
        return {"ok": True, "auswertungen_neu": neu, "insider_wochen": mit_signal, "symbole_geprueft": geprueft,
                "hinweise": hinweise[:6], "modell_version": MODELL_VERSION_INSIDER, "markt_kontrolle": kontrolle}

    @staticmethod
    def _kontroll_summary(seit: str, horizont: int, *, spy_ok: bool, ins, bas) -> dict:
        """Baut die Marktdrift-Kontroll-Zusammenfassung: Insider-Fenster vs. unkonditionierte Basisrate.
        `edge_*_pp` = Vorsprung der Insider-Wochen in Prozentpunkten. Positiv = echter Edge ueber die Marktdrift."""
        ins_n, ins_up, ins_beat, ins_alpha = ins
        bas_n, bas_up, bas_beat, bas_markt_n = bas
        def q(z, n):
            return round(z / n, 3) if n else None
        i_rich, i_markt = q(ins_up, ins_n), q(ins_beat, ins_n)
        b_rich, b_markt = q(bas_up, bas_n), q(bas_beat, bas_markt_n)
        return {
            "typ": KONTROLLE_TYP, "stand": date.today().isoformat(), "benchmark": MARKT_BENCHMARK,
            "horizont_tage": horizont, "seit": seit, "benchmark_ok": spy_ok,
            "insider": {"n": ins_n, "richtung_pct": i_rich, "schlaegt_markt_pct": i_markt,
                        "alpha_schnitt_pct": (round(ins_alpha / ins_n, 3) if ins_n else None)},
            "basisrate": {"n": bas_n, "richtung_pct": b_rich, "schlaegt_markt_pct": b_markt},
            "edge_richtung_pp": (round((i_rich - b_rich) * 100, 1) if i_rich is not None and b_rich is not None else None),
            "edge_markt_pp": (round((i_markt - b_markt) * 100, 1) if i_markt is not None and b_markt is not None else None),
        }

    def markt_kontrolle(self) -> dict | None:
        """Juengste gespeicherte Marktdrift-Kontroll-Zusammenfassung (fuer das Dashboard)."""
        runs = [r for r in self.store.list("inv_model_runs") if r.get("typ") == KONTROLLE_TYP]
        return runs[-1] if runs else None

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
