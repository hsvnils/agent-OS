"""CTO-Tool grant_capability(agent, capability) -- die zwei bestaetigten Faelle.

Fall A: vorhandene, bereits bezahlte Capability, im Budget -> gewaehren,
        CEO informieren + Changelog (autonom durch IT auf HoA-Anforderung).
Fall B: neue Kosten / neuer externer Zugang / neuer Account -> NICHT gewaehren,
        CEO-Freigabe-Anfrage + Changelog (CEO-Tor). Budget-Pruefung gegen budget.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class CapabilityResult:
    granted: bool
    fall: str           # "A" oder "B"
    message: str
    freigabe_anfrage: str = ""


def grant_capability(
    agent: str,
    capability: str,
    *,
    exists_and_paid: bool,
    in_budget: bool,
    ceo_inform: Callable[[str, str], None] | None = None,
    changelog: Callable[..., None] | None = None,
) -> CapabilityResult:
    if exists_and_paid and in_budget:
        # Fall A
        if ceo_inform:
            ceo_inform(agent, capability)
        if changelog:
            changelog(
                "CTO",
                f"Capability '{capability}' an '{agent}' gewaehrt (Fall A)",
                "vorhanden, bereits bezahlt, im Budget; auf HoA-Anforderung",
                "governance/zugriffs-policy.md",
            )
        return CapabilityResult(
            True, "A",
            f"Capability '{capability}' an '{agent}' gewaehrt; CEO informiert.",
        )

    # Fall B
    fa = (
        "ANFRAGE an CEO (Freigabe noetig)\n"
        f"- Capability: {capability}\n"
        f"- Fuer Agent: {agent}\n"
        "- Grund: neue Kosten / neuer externer Zugang -> CEO-Tor\n"
        "- Status: nicht gewaehrt bis CEO-Freigabe"
    )
    if changelog:
        changelog(
            "CTO",
            f"Capability '{capability}' fuer '{agent}' NICHT gewaehrt (Fall B)",
            "neue Kosten/neuer externer Zugang -> CEO-Tor; Budget-Check gegen finance/budget.md",
            "governance/zugriffs-policy.md",
        )
    return CapabilityResult(
        False, "B",
        f"Capability '{capability}' nicht gewaehrt; CEO-Freigabe erforderlich.",
        fa,
    )
