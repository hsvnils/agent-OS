"""Reel-Pipeline (Stufe B) -- themenbasierte Tages-Auswahl mit Anti-Doppel.

Waehlt fuer den Tag ein Thema (rotierend, deterministisch je Datum) und daraus einen bunten Mix an Clips
**ueber die Spiele hinweg**, ohne kurz zuvor genutzte Clips zu wiederholen. Rein lokal, kein LLM. Die
tatsaechliche Feinkuerzung auf die Ziel-Dauer macht die bestehende Cutter-Pipeline (`_auf_budget`).
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime
from pathlib import Path

# Thema: (Name, Energie-Praeferenz "hoch"|"mittel"|"mix", Caption-Vorlage).
THEMEN = [
    ("Tore & Highlights",    "hoch",   "Die besten Szenen ⚽️ #hsv #hanserautisch"),
    ("Fan-Stimmung",         "mittel", "Diese Stimmung! \U0001f9e1\U0001f5a4 #fans #hanserautisch"),
    ("Beste Momente",        "mix",    "Momente, die bleiben. #hanserautisch"),
    ("Emotionen pur",        "mix",    "Fussball ist Emotion \U0001f525 #hanserautisch"),
    ("Woche im Rueckblick",  "mix",    "Unser Rueckblick \U0001f4fd️ #hanserautisch"),
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
    rnd = random.Random(seed or datetime.now().strftime("%Y-%m-%d"))

    frisch = [c for c in passend if c["pfad"] not in genutzt]
    rueckfall = [c for c in passend if c["pfad"] in genutzt]
    rnd.shuffle(frisch)
    rnd.shuffle(rueckfall)
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
