"""OFC_TICKETVERSAND TV2: Spielplan des HSV als feste Datei (einmal geholt, keine laufende Verbindung nach aussen).

Quelle: OpenLigaDB (`bl1` und `dfb`, Saison 2026/2027), abgerufen am 2026-11-26 von Claude Code auf CEO-Auftrag
(„Den Spielplan des HSV fuer diese Saison musst du dir einmal irgendwo ziehen“). Spaetere Terminverlegungen aendern nichts
an der Zuordnung, solange das Datum hoechstens einen Tag abweicht; sonst traegt der CEO den Spieltag je Spiel selbst ein
(Ereignis `ofc_spiel` mit `spieltag_nr`). Fuer die naechste Saison wird die Liste neu geholt.

Kennung fuer den Verwendungszweck (E2): Bundesliga = Spieltag-Nummer („11“), DFB-Pokal = „P“ + Runde („P2“).
"""
from __future__ import annotations

from datetime import date

SAISON = "2026/27"
QUELLE = "OpenLigaDB bl1/dfb 2026, abgerufen 2026-11-26"

# (Kennung, Datum, Heim, Gast)
SPIELE: tuple[tuple[str, str, str, str], ...] = (
    ("P1", "2026-08-24", "SC Verl", "Hamburger SV"),
    ("1", "2026-08-29", "Borussia Dortmund", "Hamburger SV"),
    ("2", "2026-09-06", "Hamburger SV", "1. FSV Mainz 05"),
    ("3", "2026-09-13", "RB Leipzig", "Hamburger SV"),
    ("4", "2026-09-19", "Hamburger SV", "1. FC Köln"),
    ("5", "2026-10-10", "TSG Hoffenheim", "Hamburger SV"),
    ("6", "2026-10-17", "Hamburger SV", "VfB Stuttgart"),
    ("7", "2026-10-24", "SC Paderborn 07", "Hamburger SV"),
    ("P2", "2026-10-27", "Hamburger SV", "Eintracht Frankfurt"),
    ("8", "2026-11-01", "Eintracht Frankfurt", "Hamburger SV"),
    ("9", "2026-11-06", "Hamburger SV", "Borussia Mönchengladbach"),
    ("10", "2026-11-22", "SV Werder Bremen", "Hamburger SV"),
    ("11", "2026-11-28", "Hamburger SV", "FC Bayern München"),
    ("12", "2026-12-05", "1. FC Union Berlin", "Hamburger SV"),
    ("13", "2026-12-11", "Hamburger SV", "FC Schalke 04"),
    ("14", "2026-12-19", "SV 07 Elversberg", "Hamburger SV"),
    ("15", "2027-01-10", "Hamburger SV", "Bayer 04 Leverkusen"),
    ("16", "2027-01-13", "SC Freiburg", "Hamburger SV"),
    ("17", "2027-01-16", "Hamburger SV", "FC Augsburg"),
    ("18", "2027-01-23", "Hamburger SV", "Borussia Dortmund"),
    ("19", "2027-01-30", "1. FSV Mainz 05", "Hamburger SV"),
    ("20", "2027-02-06", "Hamburger SV", "RB Leipzig"),
    ("21", "2027-02-13", "1. FC Köln", "Hamburger SV"),
    ("22", "2027-02-20", "Hamburger SV", "TSG Hoffenheim"),
    ("23", "2027-02-27", "VfB Stuttgart", "Hamburger SV"),
    ("24", "2027-03-02", "Hamburger SV", "SC Paderborn 07"),
    ("25", "2027-03-06", "Hamburger SV", "Eintracht Frankfurt"),
    ("26", "2027-03-13", "Borussia Mönchengladbach", "Hamburger SV"),
    ("27", "2027-03-20", "Hamburger SV", "SV Werder Bremen"),
    ("28", "2027-04-03", "FC Bayern München", "Hamburger SV"),
    ("29", "2027-04-10", "Hamburger SV", "1. FC Union Berlin"),
    ("30", "2027-04-17", "FC Schalke 04", "Hamburger SV"),
    ("31", "2027-04-24", "Hamburger SV", "SV 07 Elversberg"),
    ("32", "2027-05-08", "Bayer 04 Leverkusen", "Hamburger SV"),
    ("33", "2027-05-15", "Hamburger SV", "SC Freiburg"),
    ("34", "2027-05-22", "FC Augsburg", "Hamburger SV"),
)


def kennung(spiel: dict) -> dict:
    """Spieltag-Kennung eines OFC-Spiels: zuerst die Eingabe des CEO (`spieltag_nr`), sonst Treffer im Spielplan ueber das
    Datum (+-1 Tag; der HSV spielt hoechstens einmal je Tag). -> {"kennung", "quelle": "hand"|"spielplan"|"", "spiel"}"""
    hand = str(spiel.get("spieltag_nr") or "").strip().upper()
    if hand:
        return {"kennung": hand, "quelle": "hand", "spiel": ""}
    try:
        d = date.fromisoformat(str(spiel.get("spieltag") or "")[:10])
    except ValueError:
        return {"kennung": "", "quelle": "", "spiel": ""}
    treffer = [s for s in SPIELE if abs((date.fromisoformat(s[1]) - d).days) <= 1]
    if len(treffer) != 1:
        return {"kennung": "", "quelle": "", "spiel": ""}
    k, _, heim, gast = treffer[0]
    return {"kennung": k, "quelle": "spielplan", "spiel": f"{heim} – {gast}"}


def kennung_gueltig(k: str) -> bool:
    """Bundesliga 1-34, Pokal P1-P6, sonst S<Nr> (eigene laufende Nummer fuer Test-/Europapokalspiele)."""
    import re
    k = (k or "").strip().upper()
    return bool(re.fullmatch(r"(?:[1-9]|[12]\d|3[0-4])|P[1-6]|S\d{1,2}", k))
