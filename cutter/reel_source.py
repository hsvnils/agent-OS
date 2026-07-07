"""Reel-Pipeline (Stufe A) -- Clip-Index ueber die Spiel-Ordner der Quelle.

Scannt das Quell-Verzeichnis (pro Spiel ein Unterordner, z. B. "HSV vs FCB - 2026-05-01"), erfasst je Clip
Dauer + Audio + eine **heuristische Energie** (0..1: laut/aktiv vs. ruhig -- v0 ohne KI, rein lokal ueber
ffmpeg) und legt das Ergebnis gecacht als JSON ab. Fundament fuer die themenbasierte Tages-Auswahl
(`reel_select`).

Kostenlos/lokal. KEIN Upload, KEINE Cloud. Spaeter kann die Gemini-Video-KI (CEO-Tor) reichere Themen-Tags
in dasselbe Index-Schema schreiben (Feld `themen`).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import ffmpeg_ops as fo

# Erkennt echte Spielordner am Namen ("... vs ...", "HSV 2vs1 ...", "29. Spieltag - ..."). Damit fallen
# Nicht-Spiel-Ordner (z. B. "DanceForGood-Website", "A Message for Ludo", "Community-Einsendungen") raus.
_SPIEL_MUSTER = re.compile(r"\bvs\b|\dvs\d|spieltag", re.IGNORECASE)


def ist_spielordner(name: str) -> bool:
    """True, wenn der Ordnername nach einem Spiel aussieht (Allowlist-Heuristik). Ueberschreibbar per
    expliziter Allowlist-Datei (siehe `reel_daily`)."""
    return bool(_SPIEL_MUSTER.search(name or ""))


def _energie(info) -> float:
    """Heuristische Energie 0..1: Anteil NICHT-stiller Zeit (laute Momente = Tore/Jubel) + Szenendichte.
    Rein lokal ueber ffmpeg. Ohne Audio -> nur Szenendichte (halbes Gewicht)."""
    dauer = max(0.1, info.dauer)
    szenen = fo.szenen_zeiten(info.pfad)
    dichte = min(1.0, len(szenen) / (dauer / 3.0)) if dauer > 0 else 0.0   # ~1 Schnitt / 3 s = 1.0
    if not info.hat_audio:
        return round(0.5 * dichte, 3)
    stille = sum(max(0.0, e - s) for s, e in fo.stille_spannen(info.pfad))
    aktiv = max(0.0, min(1.0, 1.0 - stille / dauer))
    return round(0.7 * aktiv + 0.3 * dichte, 3)                            # Audio (Jubel) dominiert


def baue_index(source_dir, index_pfad, *, neu: bool = False, nur_spiele: bool = True,
               allowlist: set[str] | None = None, energie_analyse: bool = True) -> dict:
    """Scannt `source_dir` (Spiel-Unterordner) und schreibt/aktualisiert den Clip-Index (JSON).

    Filtert die Ordner: ist `allowlist` gesetzt, werden nur Ordner mit exakt diesem Namen beruecksichtigt;
    sonst (bei `nur_spiele`) nur Ordner, die `ist_spielordner` erkennt. Cacht ueber die Datei-Signatur
    (mtime_ns, groesse): unveraenderte Clips werden nicht neu geprobed (spart die teure ffmpeg-Analyse).

    `energie_analyse=False` (Schnell-Modus): ueberspringt die teure Szenen-/Stille-Analyse (nur ffprobe fuer
    Dauer/Aufloesung) -> Minuten statt Stunden beim Erst-Aufbau grosser Archive (z. B. auf der NAS). Die
    Inhaltserkennung uebernimmt dann Gemini-Tagging; die Energie ist neutral (0.5).
    Gibt {ok, clips, spiele, neu, ausgeschlossen}.
    """
    source_dir = Path(source_dir)
    index_pfad = Path(index_pfad)
    if not source_dir.exists():
        return {"ok": False, "fehler": f"Quell-Verzeichnis fehlt: {source_dir}"}
    if not fo.ffmpeg_vorhanden():
        return {"ok": False, "fehler": "ffmpeg/ffprobe nicht gefunden (brew install ffmpeg)."}

    alt: dict[str, dict] = {}
    if index_pfad.exists() and not neu:
        try:
            for c in json.loads(index_pfad.read_text("utf-8")).get("clips", []):
                alt[c["pfad"]] = c
        except Exception:
            alt = {}

    clips: list[dict] = []
    spiele: set[str] = set()
    neu_gezaehlt = 0
    ausgeschlossen = 0
    for spiel_dir in sorted(p for p in source_dir.iterdir() if p.is_dir()):
        spiel = spiel_dir.name
        if allowlist is not None:
            if spiel not in allowlist:
                ausgeschlossen += 1
                continue
        elif nur_spiele and not ist_spielordner(spiel):
            ausgeschlossen += 1
            continue
        for pfad in fo.clips_im_ordner(spiel_dir):
            key = str(pfad)
            try:
                st = pfad.stat()
                sig = [st.st_mtime_ns, st.st_size]
            except OSError:
                continue
            vorhanden = alt.get(key)
            if vorhanden and vorhanden.get("sig") == sig:          # unveraendert -> Cache uebernehmen
                if "hoehe" not in vorhanden:                       # Altbestand: Aufloesung guenstig nachtragen
                    pi = fo.probe(pfad)                            # nur ffprobe (schnell) -- KEINE Szenen-Analyse
                    if pi is not None:
                        vorhanden = {**vorhanden, "breite": pi.breite, "hoehe": pi.hoehe}
                clips.append(vorhanden)
                spiele.add(vorhanden.get("spiel", spiel))
                continue
            info = fo.probe(pfad)
            if info is None or info.dauer <= 0:
                continue
            clips.append({"pfad": key, "spiel": spiel, "dauer": round(info.dauer, 2),
                          "hat_audio": info.hat_audio, "breite": info.breite, "hoehe": info.hoehe,
                          "energie": (_energie(info) if energie_analyse else 0.5),
                          "themen": [], "sig": sig})
            spiele.add(spiel)
            neu_gezaehlt += 1

    index_pfad.parent.mkdir(parents=True, exist_ok=True)
    index_pfad.write_text(json.dumps({"stand": time.strftime("%Y-%m-%dT%H:%M:%S"), "clips": clips},
                                     ensure_ascii=False, indent=2), "utf-8")
    return {"ok": True, "clips": len(clips), "spiele": len(spiele), "neu": neu_gezaehlt,
            "ausgeschlossen": ausgeschlossen}


def lade_index(index_pfad) -> list[dict]:
    """Liest den gecachten Clip-Index (Liste von Clip-Dicts). [] bei fehlender/kaputter Datei."""
    p = Path(index_pfad)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text("utf-8")).get("clips", [])
    except Exception:
        return []
