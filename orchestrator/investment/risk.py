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


def _zahl(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
