"""Changelog-Tool: schreibt umlautfreie Eintraege in projekt_changelog.md.

Format gemaess AGENTS.md 3.2. Erzwingt ASCII-Transliteration (ae/oe/ue/ss).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

_UML = {
    ord("ä"): "ae", ord("ö"): "oe", ord("ü"): "ue",
    ord("Ä"): "Ae", ord("Ö"): "Oe", ord("Ü"): "Ue",
    ord("ß"): "ss",
}

_MARKER = "## Eintraege"


def to_ascii(s: str) -> str:
    return s.translate(_UML)


def format_entry(actor: str, was: str, warum: str, betroffen: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    stamp = when.strftime("%Y-%m-%d %H:%M")
    entry = (
        f"## [{stamp}] — {actor}\n"
        f"- **Was:** {was}\n"
        f"- **Warum:** {warum}\n"
        f"- **Betroffen:** {betroffen}\n"
    )
    return to_ascii(entry)


def append_changelog(path: str | Path, actor: str, was: str, warum: str,
                     betroffen: str, when: datetime | None = None) -> str:
    """Fuegt den Eintrag oben unter '## Eintraege' ein. Gibt den Eintragstext zurueck."""
    p = Path(path)
    entry = format_entry(actor, was, warum, betroffen, when)
    text = p.read_text(encoding="utf-8") if p.exists() else _MARKER + "\n"
    if _MARKER in text:
        head, _, tail = text.partition(_MARKER)
        new = head + _MARKER + "\n\n" + entry + "\n" + tail.lstrip("\n")
    else:
        new = text.rstrip("\n") + "\n\n" + _MARKER + "\n\n" + entry + "\n"
    p.write_text(new, encoding="utf-8")
    return entry
