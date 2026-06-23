"""Charta -> System-Prompt (Single Source of Truth).

Liest die kanonischen Dateien zur Laufzeit und erzeugt deterministisch die
System-Prompts. Es werden KEINE Charta-Inhalte dupliziert.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


def repo_root() -> Path:
    # .../orchestrator/core/charter_loader.py -> Repo-Wurzel
    return Path(__file__).resolve().parents[2]


def load_text(rel: str) -> str:
    return (repo_root() / rel).read_text(encoding="utf-8")


@dataclass
class SubagentSpec:
    key: str
    name: str
    model_richtwert: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)


def _extract_title(text: str) -> str:
    m = re.search(r"^#\s*Agent:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "Agent"


def _extract_model(text: str) -> str:
    m = re.search(r"^Modell:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return ""
    raw = m.group(1)
    # Erster Modell-Token vor ' -- '/Klammer; nur Richtwert, Laufzeitmodell aus config.toml.
    raw = re.split(r"\s[-—]\s", raw)[0]
    raw = raw.split("(")[0]
    return raw.strip()


def _extract_tools(text: str) -> list[str]:
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip().lower().startswith("## tools")
            continue
        if in_section and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip())
    return out


def compose_hoa_system_prompt() -> str:
    """HoA-System-Prompt zur Laufzeit aus Regeln + Orchestrierung + Charta."""
    parts = [
        "# Kanonische Regeln (AGENTS.md)\n\n" + load_text("AGENTS.md"),
        "# Orchestrierung (governance/orchestrierung.md)\n\n"
        + load_text("governance/orchestrierung.md"),
        "# Charta Head of Agents (agents/00_head-of-agents.md)\n\n"
        + load_text("agents/00_head-of-agents.md"),
    ]
    return "\n\n---\n\n".join(parts)


def load_subagent(rel: str, key: str) -> SubagentSpec:
    text = load_text(rel)
    return SubagentSpec(
        key=key,
        name=_extract_title(text),
        model_richtwert=_extract_model(text),
        system_prompt=text,
        tools=_extract_tools(text),
    )
