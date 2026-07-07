"""Reel-Pipeline (Stufe B) -- themenbasierte Tages-Auswahl mit Anti-Doppel.

Waehlt fuer den Tag ein Thema (rotierend, deterministisch je Datum) und daraus einen bunten Mix an Clips
**ueber die Spiele hinweg**, ohne kurz zuvor genutzte Clips zu wiederholen. Rein lokal, kein LLM. Die
tatsaechliche Feinkuerzung auf die Ziel-Dauer macht die bestehende Cutter-Pipeline (`_auf_budget`).
"""
from __future__ import annotations

import json
import random
import statistics
from datetime import date, datetime
from pathlib import Path

# Thema -> bevorzugte Inhalts-Tags (aus dem Gemini-Video-Tagging, Feld `themen`). Leere Menge = alles passt.
# Wird nur wirksam, wenn Clips getaggt sind (sonst faellt die Auswahl auf die Energie-Heuristik zurueck).
THEMA_TAGS = {
    "Tore & Highlights": {"tor", "jubel", "spielszene"},
    "Fan-Stimmung": {"fans", "choreo", "stadion"},
    "Beste Momente": {"tor", "jubel", "choreo"},
    "Emotionen pur": {"jubel", "fans", "interview"},
    "Woche im Rueckblick": set(),
}


# Thema: (Name, Energie-Praeferenz "hoch"|"mittel"|"mix", Caption-Vorlage).
THEMEN = [
    ("Tore & Highlights",    "hoch",   "Beste Szenen ⚽️ #HSV"),
    ("Fan-Stimmung",         "mittel", "Diese Stimmung! \U0001f9e1\U0001f5a4 #HSV"),
    ("Beste Momente",        "mix",    "Unsere Momente \U0001f5a4 #HSV"),
    ("Emotionen pur",        "mix",    "Pure Emotionen \U0001f525 #HSV"),
    ("Woche im Rueckblick",  "mix",    "Rueckblick \U0001f4fd️ #HSV"),
]


def thema_fuer_tag(tag: date | None = None) -> tuple:
    """Deterministische Themen-Rotation nach Tages-Ordinalzahl -> nie zwei Tage am Stueck dasselbe."""
    tag = tag or date.today()
    return THEMEN[tag.toordinal() % len(THEMEN)]


def _passt_energie(clip: dict, praeferenz: str) -> bool:
    e = clip.get("energie", 0.0)
    if praeferenz == "hoch":
        return e >= 0.55
    if praeferenz == "mittel":
        return 0.3 <= e <= 0.8
    return True                                           # "mix": alles erlaubt


def _kurzseite(clip: dict):
    """Kurze Bildseite (orientierungsunabhaengiges Aufloesungsmass: 1080p -> 1080, egal ob hoch/quer).
    None, wenn die Aufloesung im Index nicht bekannt ist (Altbestand)."""
    b, h = clip.get("breite"), clip.get("hoehe")
    return min(b, h) if (b and h) else None


def filter_qualitaet(clips: list[dict], *, min_kurz: int = 480, rel_median: float = 0.5) -> list[dict]:
    """Wirft Clips raus, deren Aufloesung DEUTLICH unter dem Rest liegt: kurze Seite unter
    max(`min_kurz`, `rel_median` * Median). So bleibt z. B. 720p neben 1080p erhalten, aber ein 360p-Clip
    zwischen HD-Material fliegt raus. Clips ohne bekannte Aufloesung bleiben drin; faellt auf die Eingabe
    zurueck, wenn sonst nichts uebrig bliebe (z. B. wenn ALLES niedrig aufgeloest ist)."""
    kurz = [k for k in (_kurzseite(c) for c in clips) if k]
    if not kurz:
        return clips
    grenze = max(min_kurz, rel_median * statistics.median(kurz))
    gut = [c for c in clips if (_kurzseite(c) is None or _kurzseite(c) >= grenze)]
    return gut or clips


def _tag_treffer(clip: dict, thema: tuple) -> bool:
    """True, wenn die Inhalts-Tags des Clips zum Tagesthema passen. Ohne Themen-Mapping (leere Menge) oder
    ohne getaggte Clips gilt alles als Treffer -> kein Effekt (graceful, solange nicht getaggt wurde)."""
    ziel = THEMA_TAGS.get(thema[0]) or set()
    if not ziel:
        return True
    return bool(set(clip.get("themen") or []) & ziel)


def _nach_tags(clips: list, thema: tuple) -> list:
    """Stabile Umsortierung: thematisch passende Clips nach vorn (Rest behaelt seine Reihenfolge)."""
    treffer = [c for c in clips if _tag_treffer(c, thema)]
    rest = [c for c in clips if not _tag_treffer(c, thema)]
    return treffer + rest if rest else clips        # kein Effekt, wenn alle "treffen" (z. B. ungetaggt)


def lade_genutzte(used_pfad, *, tage: int = 14) -> set:
    """Clip-Pfade, die in den letzten `tage` Tagen schon in einem Reel waren (Anti-Doppel)."""
    p = Path(used_pfad)
    if not p.exists():
        return set()
    grenze = datetime.now().timestamp() - tage * 86400
    genutzt: set[str] = set()
    for line in p.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if float(ev.get("ts", 0)) >= grenze:
            genutzt.update(ev.get("clips", []))
    return genutzt


def waehle_clips(index: list[dict], thema: tuple, *, genutzt: set | None = None,
                 max_clips: int = 16, seed: str | None = None) -> list[dict]:
    """Themenbasierte, gemischte Auswahl ueber Spiele hinweg.

    Bevorzugt frische (nicht kuerzlich genutzte) Clips, faellt aber auf genutzte zurueck, wenn sonst zu wenige
    zusammenkommen. Streut per Round-Robin ueber die Spiele, damit nicht alles aus einem Spiel stammt.
    Deterministisch je `seed` (Default: heutiges Datum) -> reproduzierbar, aber taeglich anders.
    """
    genutzt = genutzt or set()
    _, praeferenz, _ = thema
    passend = [c for c in index if _passt_energie(c, praeferenz)] or list(index)
    passend = filter_qualitaet(passend)                  # Ausreisser mit schlechter Aufloesung aussortieren
    rnd = random.Random(seed or datetime.now().strftime("%Y-%m-%d"))

    frisch = [c for c in passend if c["pfad"] not in genutzt]
    rueckfall = [c for c in passend if c["pfad"] in genutzt]
    rnd.shuffle(frisch)
    rnd.shuffle(rueckfall)
    # Wenn Clips getaggt sind: thematisch passende innerhalb jeder Gruppe nach vorn (sonst kein Effekt).
    frisch = _nach_tags(frisch, thema)
    rueckfall = _nach_tags(rueckfall, thema)
    pool = frisch + rueckfall                             # frische zuerst, dann ggf. auffuellen

    nach_spiel: dict[str, list] = {}
    for c in pool:
        nach_spiel.setdefault(c.get("spiel", "?"), []).append(c)
    spiele = list(nach_spiel.keys())
    rnd.shuffle(spiele)

    auswahl: list[dict] = []
    runden = 0
    while len(auswahl) < max_clips and any(nach_spiel.values()):
        s = spiele[runden % len(spiele)]
        if nach_spiel[s]:
            auswahl.append(nach_spiel[s].pop(0))
        runden += 1
        if runden > max_clips * (len(spiele) + 1):        # Sicherheitsnetz gegen Endlosschleifen
            break
    return auswahl
