"""CEO-Tor-Durchsetzung (Pre-Aktions-Hook).

Blockiert Aktionen, die eine CEO-Tor-Kategorie beruehren, solange keine
Freigabe vorliegt, und erzeugt stattdessen eine entscheidungsreife
Freigabe-Anfrage. Spiegelt AGENTS.md 5.3/5.4.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.routing import detect_ceo_tor


@dataclass
class GateResult:
    blocked: bool
    category: str = ""
    freigabe_anfrage: str = ""


class CeoGate:
    def check(self, action_description: str) -> GateResult:
        cat = detect_ceo_tor(action_description)
        if cat is None:
            return GateResult(False)
        fa = (
            "ANFRAGE an CEO (Freigabe noetig)\n"
            f"- Kategorie: {cat}\n"
            f"- Aktion: {action_description}\n"
            "- Status: blockiert bis CEO-Freigabe (keine autonome Ausfuehrung)"
        )
        return GateResult(True, cat, fa)
