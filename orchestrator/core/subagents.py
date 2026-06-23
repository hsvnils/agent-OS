"""Subagent-Definitionen aus den Charten erzeugen (nicht von Hand duplizieren)."""
from __future__ import annotations

from .charter_loader import SubagentSpec, load_subagent


def load_default_subagents() -> dict[str, SubagentSpec]:
    """Bootstrap-Subagenten: CTO + Unternehmensberater, je aus ihrer Charta."""
    return {
        "cto": load_subagent("agents/08_cto.md", "cto"),
        "berater": load_subagent("agents/01_unternehmensberater.md", "berater"),
    }
