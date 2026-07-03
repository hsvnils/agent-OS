"""Risk-Agent (CIO-RISK) -- Pflicht-Gegenpruefer (Checker) der Investment-Abteilung.

Regelbasiert, token-frugal: vergibt ein Risiko-Label, empfiehlt eine max. Positionsgroesse und faellt eine
Entscheidung (freigabe / nachschaerfung / veto). KEIN Vorschlag verlaesst die Abteilung ohne dieses Urteil
(Maker/Checker, siehe governance/autonomie-stufen.md + governance/investment.md). Keine Trades.

Limits gelten im advisory-Modus als **Empfehlung**; ab paper/live werden sie hart durchgesetzt. Werte sind
Startwerte (in `governance/investment.md` dokumentiert; Aenderung = CEO-Tor).
"""
from __future__ import annotations


class RiskAgent:
    # Startwerte (advisory = Empfehlung). Aenderung dieser Limits = CEO-Tor.
    SPEKULATIV_PCT = 25.0     # Tagesbewegung ab hier -> Label "spekulativ"
    VETO_PCT = 80.0           # extreme Bewegung -> Veto (zu spaet/zu riskant)
    KONFIDENZ_MIN = 0.40      # darunter -> Nachschaerfung verlangen
    # Harte Order-Limits ab paper/live (konservativ; Erhoehung = CEO-Tor, GATE C/D).
    MAX_POSITION_PCT = 5.0    # max. Wert EINER Position in % des Depot-Equity
    MIN_EQUITY = 1.0          # unter diesem Equity keine Orders

    def pruefe(self, vorschlag: dict) -> dict:
        """vorschlag: {symbol, aktion, asset, veraenderung_pct, konfidenz}. -> Risiko-Urteil."""
        chg = abs(_zahl(vorschlag.get("veraenderung_pct")))
        konfidenz = _zahl(vorschlag.get("konfidenz"))
        asset = (vorschlag.get("asset") or "aktie").lower()

        label = "spekulativ" if (chg >= self.SPEKULATIV_PCT or asset == "krypto") else "konservativ"
        gruende: list[str] = []
        entscheidung = "freigabe"

        if chg >= self.VETO_PCT:
            entscheidung = "veto"
            gruende.append(f"Extrem-Bewegung {chg:.0f}% -- zu spaet/zu riskant fuer einen Einstieg.")
        elif konfidenz < self.KONFIDENZ_MIN:
            entscheidung = "nachschaerfung"
            gruende.append(f"Konfidenz {konfidenz:.2f} < {self.KONFIDENZ_MIN:.2f} -- mehr Belege noetig.")

        if asset == "krypto":
            gruende.append("Krypto ist generell spekulativ (hohe Volatilitaet).")

        max_position = "1-2% des Depots" if label == "spekulativ" else "3-5% des Depots"
        return {
            "label": label,
            "entscheidung": entscheidung,
            "max_position": max_position,
            "begruendung": "; ".join(gruende) or "Im Rahmen der Limits.",
            "veraenderung_pct": chg,
        }

    def pruefe_order(self, *, order_wert: float, konto_equity: float, buying_power: float,
                     side: str = "buy") -> dict:
        """Harte Vorab-Pruefung einer (Paper-)Order. -> {ok, grund}. Ab paper/live verbindlich.

        Konservativ: Kauf nur, wenn Ordervolumen <= verfuegbare Buying-Power UND <= MAX_POSITION_PCT des
        Equity. Verkaeufe (side='sell') sind risikoreduzierend -> durchgelassen (Deckung prueft der Broker).
        """
        order_wert = _zahl(order_wert); konto_equity = _zahl(konto_equity); buying_power = _zahl(buying_power)
        if (side or "buy").lower() == "sell":
            return {"ok": True, "grund": "Verkauf (risikoreduzierend)."}
        if konto_equity < self.MIN_EQUITY:
            return {"ok": False, "grund": f"Equity {konto_equity:.2f} zu niedrig."}
        if order_wert <= 0:
            return {"ok": False, "grund": "Ordervolumen unbekannt/0 (kein Kurs?)."}
        if order_wert > buying_power:
            return {"ok": False, "grund": f"Ordervolumen {order_wert:.2f} > Buying-Power {buying_power:.2f}."}
        limit = konto_equity * self.MAX_POSITION_PCT / 100.0
        if order_wert > limit:
            return {"ok": False,
                    "grund": f"Position {order_wert:.2f} > {self.MAX_POSITION_PCT:.0f}% des Equity ({limit:.2f})."}
        return {"ok": True, "grund": "Im Rahmen der harten Limits."}


def _zahl(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
