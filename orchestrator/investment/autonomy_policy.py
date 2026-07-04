"""Autonomie-Leitplanken (CEO-abgesegnet 2026-07-03) als ausfuehrbare, testbare Logik.

Prueft einen geplanten Trade gegen die harten K.-o.-Gates + globalen Schutzschalter. Ergebnis:
`erlaubt_autonom` (der Agent darf ohne Rueckfrage handeln) oder `benoetigt_freigabe` (1-Tap-Anfrage per
Telegram). **Voellig inert**, solange kein Broker/Paper-Modus aktiv ist -- dann steckt dieses Modul im
Order-Pfad (analog `risk.RiskAgent.pruefe_order`). Kein Geld, kein Trade hier drin.

Grundsatz: Jeder autonome Trade muss ALLE Gates erfuellen; faellt eines, gibt es keinen autonomen Trade,
sondern eine Freigabe-Anfrage. Verkaeufe sind risikoreduzierend -> durchgelassen (auch unter Kill-Switch).
Werte-Aenderung = CEO-Tor (governance/investment.md, Abschnitt 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Leitplanken:
    # Harte Gates je Trade (autonom = enger als mit CEO-Freigabe)
    max_position_pct: float = 2.0        # autonom max. % des Equity je Trade (mit Freigabe bis 5 %)
    max_position_eur: float = 50.0       # autonom max. EUR je Trade
    min_konfidenz: float = 0.70          # darunter -> Freigabe
    min_signale: int = 2                 # Mehrfach-Signal-Pflicht (unabhaengige Signale)
    max_trades_fenster: int = 3          # max. autonome Trades je Fenster (z. B. Nacht)
    nacht_budget_eur: float = 200.0      # autonomes Gesamtvolumen je Fenster
    whitelist_pflicht: bool = True       # nur freigegebene, liquide Werte autonom
    nur_konservativ: bool = True         # "spekulativ" (Risk-Agent) -> immer Freigabe
    # Exit-Automatik (Vorgabe fuer den spaeteren Order-Pfad)
    pflicht_stop_loss_pct: float = 8.0
    nur_limit_orders: bool = True
    # Globale Schutzschalter
    tagesverlust_stop_pct: float = 3.0   # ab hier ALLE Autonomie aus (nur risikoreduzierende Verkaeufe)

    @classmethod
    def nacht_krypto(cls) -> "Leitplanken":
        """Enge Leitplanke fuer den Nacht-Krypto-Handel: nur die seltene Top-Chance, winziger Einsatz.
        `nur_konservativ=False` -> Krypto (spekulativ) autonom erlaubt, ABER nur nachdem der strenge
        Nacht-Chance-Filter (hohe Konfidenz + alle Signale einig + hohes Ziel) bestanden ist."""
        return cls(max_position_pct=1.0, max_position_eur=30.0, min_konfidenz=0.80, min_signale=3,
                   max_trades_fenster=1, nacht_budget_eur=60.0, whitelist_pflicht=False, nur_konservativ=False,
                   pflicht_stop_loss_pct=5.0, tagesverlust_stop_pct=3.0)


def _default_whitelist() -> set[str]:
    from .universe import CORE_UNIVERSE
    return {u["symbol"].upper() for u in CORE_UNIVERSE} | {"SPY", "BITCOIN"}


@dataclass
class AutonomyPolicy:
    lp: Leitplanken = field(default_factory=Leitplanken)
    whitelist: set[str] = field(default_factory=_default_whitelist)

    def pruefe(self, trade: dict, kontext: dict) -> dict:
        """trade: {symbol, asset, side, betrag_eur, konfidenz, risiko_label, signale}.
        kontext: {equity, nacht_budget_genutzt, trades_im_fenster, tagesverlust_pct, kill_switch,
                  autonomie_freigeschaltet}. -> Urteil mit einzeln nachvollziehbaren Checks."""
        side = (trade.get("side") or "buy").lower()
        checks: list[dict] = []

        def check(name: str, ok: bool, detail: str):
            checks.append({"name": name, "ok": bool(ok), "detail": detail})

        # Globale Schutzschalter zuerst (blocken ALLE Autonomie)
        kill = bool(kontext.get("kill_switch"))
        tagesverlust = _num(kontext.get("tagesverlust_pct"))
        verlust_stop = tagesverlust >= self.lp.tagesverlust_stop_pct
        check("kill_switch", not kill, "aktiv -- Autonomie gesperrt" if kill else "inaktiv")
        check("tagesverlust", not verlust_stop,
              f"{tagesverlust:.1f}% >= Stop {self.lp.tagesverlust_stop_pct:.1f}%" if verlust_stop
              else f"{tagesverlust:.1f}% < Stop {self.lp.tagesverlust_stop_pct:.1f}%")

        # Verkauf ist risikoreduzierend -> auch unter Kill-Switch autonom erlaubt
        if side == "sell":
            check("verkauf", True, "risikoreduzierend -- durchgelassen")
            return _urteil(checks, autonom=True)

        betrag = _num(trade.get("betrag_eur"))
        equity = _num(kontext.get("equity"))
        pos_pct = (betrag / equity * 100) if equity > 0 else 999.0
        konfidenz = _num(trade.get("konfidenz"))
        signale = int(_num(trade.get("signale")))
        label = (trade.get("risiko_label") or "").lower()
        sym = (trade.get("symbol") or "").upper()
        budget_neu = _num(kontext.get("nacht_budget_genutzt")) + betrag
        trades = int(_num(kontext.get("trades_im_fenster")))
        freigeschaltet = bool(kontext.get("autonomie_freigeschaltet"))

        check("track_record", freigeschaltet,
              "freigeschaltet" if freigeschaltet else "Autonomie erst nach gutem Track-Record")
        check("position_pct", pos_pct <= self.lp.max_position_pct,
              f"{pos_pct:.2f}% (max {self.lp.max_position_pct:.1f}%)")
        check("position_eur", 0 < betrag <= self.lp.max_position_eur,
              f"{betrag:.2f} EUR (max {self.lp.max_position_eur:.0f})")
        check("konfidenz", konfidenz >= self.lp.min_konfidenz,
              f"{konfidenz:.2f} (min {self.lp.min_konfidenz:.2f})")
        check("signale", signale >= self.lp.min_signale,
              f"{signale} (min {self.lp.min_signale})")
        if self.lp.nur_konservativ:
            check("risiko_label", label == "konservativ", label or "unbekannt")
        if self.lp.whitelist_pflicht:
            check("whitelist", sym in self.whitelist, sym + (" ok" if sym in self.whitelist else " nicht gelistet"))
        check("nacht_budget", budget_neu <= self.lp.nacht_budget_eur,
              f"{budget_neu:.0f}/{self.lp.nacht_budget_eur:.0f} EUR")
        check("trade_frequenz", trades < self.lp.max_trades_fenster,
              f"{trades} (max {self.lp.max_trades_fenster})")

        return _urteil(checks, autonom=all(c["ok"] for c in checks))

    def konfiguration(self) -> list[dict]:
        """Anzeige-freundliche Aufstellung der aktiven Leitplanken (fuer das Dashboard)."""
        lp = self.lp
        return [
            {"label": "Max. Position (autonom)", "wert": f"{lp.max_position_pct:.0f}% Equity / {lp.max_position_eur:.0f} EUR"},
            {"label": "Mindest-Konfidenz", "wert": f"{lp.min_konfidenz:.2f}"},
            {"label": "Mehrfach-Signal-Pflicht", "wert": f">= {lp.min_signale}"},
            {"label": "Nacht-Budget", "wert": f"{lp.nacht_budget_eur:.0f} EUR"},
            {"label": "Max. Trades / Fenster", "wert": str(lp.max_trades_fenster)},
            {"label": "Tagesverlust-Stop", "wert": f"-{lp.tagesverlust_stop_pct:.0f}%"},
            {"label": "Pflicht-Stop-Loss", "wert": f"-{lp.pflicht_stop_loss_pct:.0f}%"},
            {"label": "Nur Whitelist / konservativ / Limit-Orders",
             "wert": _janein(lp.whitelist_pflicht and lp.nur_konservativ and lp.nur_limit_orders)},
        ]


def _urteil(checks: list[dict], *, autonom: bool) -> dict:
    gruende = [c["detail"] for c in checks if not c["ok"]]
    return {"erlaubt_autonom": autonom, "benoetigt_freigabe": not autonom,
            "checks": checks, "gruende": gruende}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _janein(b: bool) -> str:
    return "ja" if b else "nein"
