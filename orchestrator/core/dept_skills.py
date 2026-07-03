"""Skills je Abteilung (Phase 24 -> live) -- laedt gegatete Skills in den System-Prompt eines Fachagenten.

Eine Abteilung `<key>` kann Skills unter `skills/<key>/<skill-name>/SKILL.md` tragen (Format:
`governance/skill-standard.md`). Beim Laden des Subagenten wird JEDER Skill zuerst durch das Security-Gate
(`skill_gate.pruefe_skill`) geprueft: ein **abgelehnter** Skill (hoch-Fund) wird NICHT geladen. Die Instruktion
(SKILL.md ohne Frontmatter) der bestandenen/zu-pruefenden Skills wird an den Charta-System-Prompt angehaengt.

Damit werden Abteilungen gezielt mit wiederverwendbaren, geprueften Arbeitsanleitungen angereichert -- ohne die
Charta selbst zu aendern (kein CEO-Tor fuers Hinzufuegen eines Skills; nur der Gate-Check entscheidet).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import skill_format
from .skill_gate import pruefe_skill


def _body(text: str) -> str:
    """SKILL.md ohne das skill-card-Frontmatter (nur die Instruktion)."""
    m = re.match(r"^\s*---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)", text or "", re.S)
    return (text[m.end():] if m else text).strip()


def lade_dept_skills(key: str, repo) -> tuple[str, list[dict]]:
    """Laedt die gegateten Skills der Abteilung `<key>` aus `skills/<key>/`. -> (prompt_block, meta)."""
    basis = Path(repo) / "skills" / key
    meta: list[dict] = []
    bloecke: list[str] = []
    if not basis.is_dir():
        return ("", meta)
    for d in sorted(p for p in basis.iterdir() if p.is_dir()):
        erg = pruefe_skill(d)
        md = d / "SKILL.md"
        if erg.blockiert or not md.exists():          # abgelehnt (hoch-Fund) oder kein SKILL.md -> nicht laden
            meta.append({"skill": d.name, "verdikt": erg.verdikt, "geladen": False})
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        name = skill_format.parse_skill_card(text).get("name") or d.name
        bloecke.append(f"### Skill: {name}\n{_body(text)}")
        meta.append({"skill": name, "verdikt": erg.verdikt, "geladen": True})
    if not bloecke:
        return ("", meta)
    block = ("\n\n## Verfuegbare Skills (gepruefte, wiederverwendbare Arbeitsanleitungen)\n"
             "Wende den passenden Skill an, wenn die Aufgabe dazu passt:\n\n" + "\n\n".join(bloecke))
    return (block, meta)
