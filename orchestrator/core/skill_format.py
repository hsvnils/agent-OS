"""Phase 24 Baustein (a) -- Skill-/Charta-Format-Standard (Validator).

Definiert und prueft das offene Skill-Format (`SKILL.md` + `skill-card`-Frontmatter), auf das unsere
`agents/*.md`-Charten gehoben werden. Rein regelbasiert, **dependency-frei** und deterministisch.

Bewusst KEIN `yaml.load` auf Fremd-Cards (das flaggt unser eigenes Security-Gate zu Recht) -- die
`skill-card` ist ein flaches `key: value`-Frontmatter, das ein Minimal-Parser sicher liest. Siehe
`governance/skill-standard.md` fuer die menschenlesbare Spezifikation.
"""
from __future__ import annotations

import re

from .security_agent import Finding

# Pflichtfelder der skill-card (Identitaet/Governance/Version).
PFLICHTFELDER = ("name", "version", "beschreibung", "lizenz")
# Optionale, empfohlene Felder.
EMPFOHLEN = ("autor", "governance", "modell")

_KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def parse_skill_card(text: str) -> dict:
    """Liest das Frontmatter (zwischen den ersten beiden '---'-Zeilen) als flaches key:value-Dict.

    Deterministisch, ohne YAML-Bibliothek. Werte werden getrimmt; umschliessende Quotes entfernt.
    Gibt {} zurueck, wenn kein Frontmatter vorhanden ist.
    """
    t = text or ""
    m = re.match(r"^\s*---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", t, re.S)
    if not m:
        return {}
    card: dict[str, str] = {}
    for zeile in m.group(1).splitlines():
        s = zeile.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        schluessel, _, wert = s.partition(":")
        schluessel = schluessel.strip()
        wert = wert.strip().strip('"').strip("'").strip()
        if schluessel:
            card[schluessel] = wert
    return card


def validiere(skill_dir) -> list[Finding]:
    """Prueft die Format-Konformitaet eines Skill-Ordners. Gibt Finding-Liste (kein Security-Urteil).

    Schweren bewusst niedrig gehalten (Format = Hygiene, kein Sicherheitsrisiko): fehlende SKILL.md =
    'mittel' (ohne Instruktion kein Skill), fehlende/unvollstaendige skill-card = 'niedrig'.
    """
    from pathlib import Path
    root = Path(skill_dir)
    md = root / "SKILL.md"
    if not md.exists():
        return [Finding("skill-format", "mittel", "Keine SKILL.md im Skill", "",
                        "Skill-Standard verlangt SKILL.md (Instruktion) -- siehe governance/skill-standard.md.")]
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return [Finding("skill-format", "mittel", "SKILL.md nicht lesbar", md.name, "Datei pruefen.")]

    card = parse_skill_card(text)
    out: list[Finding] = []
    if not card:
        out.append(Finding("skill-format", "niedrig", "skill-card (Frontmatter) fehlt",
                           "SKILL.md hat kein '---'-Frontmatter mit Metadaten.",
                           "skill-card ergaenzen (name, version, beschreibung, lizenz)."))
        return out

    fehlend = [f for f in PFLICHTFELDER if not card.get(f)]
    if fehlend:
        out.append(Finding("skill-format", "niedrig", "Pflichtfelder der skill-card fehlen",
                           "Fehlt: " + ", ".join(fehlend),
                           "Pflichtfelder ergaenzen: " + ", ".join(PFLICHTFELDER) + "."))
    name = card.get("name", "")
    if name and not _KEBAB.match(name):
        out.append(Finding("skill-format", "niedrig", "Feld 'name' nicht kebab-case",
                           f"name='{name}'", "Kleinbuchstaben/Ziffern mit Bindestrich (z. B. mein-skill)."))
    version = card.get("version", "")
    if version and not _SEMVER.match(version):
        out.append(Finding("skill-format", "niedrig", "Feld 'version' nicht semver-artig",
                           f"version='{version}'", "Format MAJOR.MINOR[.PATCH] (z. B. 1.0 oder 1.0.0)."))
    return out


def ist_konform(skill_dir) -> bool:
    """True, wenn keine Format-Findings vorliegen (SKILL.md + vollstaendige, gueltige skill-card)."""
    return not validiere(skill_dir)
