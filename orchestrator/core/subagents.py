"""Subagent-Definitionen aus den Charten erzeugen (nicht von Hand duplizieren)."""
from __future__ import annotations

from .charter_loader import SubagentSpec, load_subagent


def load_default_subagents() -> dict[str, SubagentSpec]:
    """Bootstrap-Subagenten: CTO + Unternehmensberater, je aus ihrer Charta."""
    return {
        "cto": load_subagent("agents/08_cto.md", "cto"),
        "berater": load_subagent("agents/01_unternehmensberater.md", "berater"),
    }


# Kurzname -> Charta-Datei (alle konsultierbaren Fachagenten; HoA ist der Hauptagent).
ALL_AGENT_CHARTERS: dict[str, str] = {
    "berater": "agents/01_unternehmensberater.md",
    "cao": "agents/02_cao.md",
    "cfo": "agents/03_cfo.md",
    "cro": "agents/04_cro.md",
    "ciso": "agents/05_ciso.md",
    "cbo": "agents/06_cbo.md",
    "cpo": "agents/07_cpo.md",
    "cto": "agents/08_cto.md",
    "cxo": "agents/09_cxo.md",
    "cco": "agents/10_cco-content.md",
    "cdo": "agents/11_cdo.md",
    "chro": "agents/12_chro.md",
    "clo": "agents/13_clo.md",
    "cko": "agents/14_cko.md",
    "res": "agents/15_researcher.md",
}


def load_all_subagents() -> dict[str, SubagentSpec]:
    """Alle Fachagenten als konsultierbare Spezialisten, je aus ihrer Charta."""
    return {key: load_subagent(rel, key) for key, rel in ALL_AGENT_CHARTERS.items()}
