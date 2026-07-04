"""Autonomer Paper-Trader (Schritt 6) -- entscheidet je Handels-Chance eine von drei Aktionen.

Reine, testbare Entscheidungslogik auf Basis der Autonomie-Leitplanken (`autonomy_policy`):
- **auto**     -> alle Gates erfuellt UND Autonomie freigeschaltet (Track-Record) -> autonome Paper-Order.
- **freigabe** -> nicht (voll) autonom, aber kein globaler Stopp -> 1-Tap-Freigabe an den CEO (Ja/Nein).
- **skip**     -> globaler Schutzschalter aktiv (Kill-Switch ODER Tagesverlust-Stop) -> gar nicht anbieten.

Kein Broker, kein Geld hier drin -- nur die Entscheidung. Die Ausfuehrung (paper_order bzw. Freigabe-Anfrage)
macht der Aufrufer. Standardmaessig ist der Loop AUS und autonom erst nach belegtem Track-Record.
"""
from __future__ import annotations

from .autonomy_policy import AutonomyPolicy


class AutoTrader:
    def __init__(self, policy: AutonomyPolicy | None = None):
        self.policy = policy or AutonomyPolicy()

    def entscheide(self, trade: dict, kontext: dict) -> dict:
        urteil = self.policy.pruefe(trade, kontext)
        ok = {c["name"]: c["ok"] for c in urteil["checks"]}
        # Globaler Schutzschalter -> nichts anbieten (auch keine Freigabe)
        if not ok.get("kill_switch", True) or not ok.get("tagesverlust", True):
            return {"aktion": "skip", "urteil": urteil, "grund": "globaler Schutzschalter aktiv"}
        if urteil["erlaubt_autonom"]:
            return {"aktion": "auto", "urteil": urteil}
        return {"aktion": "freigabe", "urteil": urteil}
