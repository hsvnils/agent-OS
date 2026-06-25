"""Anzeige-Aufbereitung fuer Telegram-Nachrichten.

Der Bot sendet reinen Text (kein parse_mode) -> Markdown-Marker (`**fett**`, `# Ueberschrift`, `* Liste`)
wuerden roh als Sterne/Rauten erscheinen und den Text unuebersichtlich machen. Dieser Filter raeumt die
Marker sauber auf und schreibt die Abteilungs-Kuerzel gross (CTO, CFO ...). Wird unmittelbar vor dem
Senden angewendet (Chat-Antworten UND proaktive Meldungen/Briefings).
"""
from __future__ import annotations

import re

# C-Level-Kuerzel -> Grossschreibung in der Ausgabe.
_CODES = ("ciso", "chro", "cao", "cfo", "cro", "cbo", "cpo", "cto", "cxo", "cco", "cdo", "clo", "cko")


def fuer_telegram(text: str) -> str:
    if not text:
        return text or ""
    s = str(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s, flags=re.S)          # **fett** -> Text
    s = re.sub(r"__(.+?)__", r"\1", s, flags=re.S)              # __fett__ -> Text
    s = re.sub(r"\*(?=\S)(.+?)(?<=\S)\*", r"\1", s, flags=re.S)  # *betont* -> Text (kein Bullet)
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", s)                  # '# Ueberschrift' -> Ueberschrift
    s = re.sub(r"(?m)^(\s*)\*\s+", r"\1• ", s)                   # '* Punkt' -> '• Punkt'
    for c in _CODES:
        s = re.sub(rf"\b{c}\b", c.upper(), s)                    # cto -> CTO
    return s
