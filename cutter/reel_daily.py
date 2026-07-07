"""Reel-Pipeline (Stufe A+B, Orchestrator) -- taeglicher Lauf am Mac.

Ablauf: Clip-Index aktualisieren -> Tages-Thema + gemischte Clip-Auswahl (Anti-Doppel) -> ausgewaehlte Clips
in einen Arbeitsordner verlinken -> bestehende Cutter-Pipeline schneidet ein 45s-Reel -> Ablage in
`outbox/<datum>/reel.mp4` + `metadata.json` -> genutzte Clips protokollieren (`state/used.jsonl`).

**Kein Upload, keine Veroeffentlichung.** Das fertige Reel wartet auf die 1-Tap-Freigabe (Stufe C/D).
Rein lokal/gratis. Pfade per CLI/Env konfigurierbar (Quelle liegt auf der gemounteten NAS).

CLI:  python -m cutter.reel_daily [--source ..] [--outbox ..] [--state ..] [--dauer 45] [--datum YYYY-MM-DD]
Env:  REEL_SOURCE / REEL_OUTBOX / REEL_STATE
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

from . import reel_select as rs
from . import reel_source as rq
from .pipeline import schneide_ordner


def _stage(clips: list[dict], arbeit: Path) -> list[Path]:
    """Verlinkt die ausgewaehlten Clips (in Reihenfolge) in einen Arbeitsordner. Numerisches Praefix haelt
    die Reihenfolge (die Pipeline sortiert nach Dateiname, wenn Gemini aus ist). Symlink -> kein Kopieren
    grosser Dateien; bei fehlgeschlagenem Symlink (z. B. Cross-Device) wird hart kopiert."""
    staged: list[Path] = []
    for i, c in enumerate(clips):
        quelle = Path(c["pfad"])
        if not quelle.exists():
            continue
        ziel = arbeit / f"{i:03d}_{quelle.name}"
        try:
            os.symlink(quelle, ziel)
        except OSError:
            try:
                shutil.copy2(quelle, ziel)
            except OSError:
                continue
        staged.append(ziel)
    return staged


def lauf(*, source: Path, outbox: Path, state: Path, tag: date | None = None,
         ziel_dauer: float = 45.0, gemini: bool = False) -> dict:
    """Ein Tages-Reel erzeugen. Gibt einen Bericht (dict). Kein Upload."""
    tag = tag or date.today()
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    index_pfad = state / "clip_index.json"
    used_pfad = state / "used.jsonl"

    idx_res = rq.baue_index(source, index_pfad)
    if not idx_res.get("ok"):
        return idx_res
    index = rq.lade_index(index_pfad)
    if not index:
        return {"ok": False, "fehler": "Clip-Index leer -- keine Clips in der Quelle."}

    thema = rs.thema_fuer_tag(tag)
    genutzt = rs.lade_genutzte(used_pfad)
    auswahl = rs.waehle_clips(index, thema, genutzt=genutzt, seed=tag.isoformat())
    if not auswahl:
        return {"ok": False, "fehler": "Keine passenden Clips fuer die Auswahl."}

    tag_dir = Path(outbox) / tag.isoformat()
    tag_dir.mkdir(parents=True, exist_ok=True)
    ausgabe = tag_dir / "reel.mp4"

    arbeit = Path(tempfile.mkdtemp(prefix="reel_"))
    try:
        staged = _stage(auswahl, arbeit)
        if not staged:
            return {"ok": False, "fehler": "Kein Clip konnte bereitgestellt werden (Pfade pruefen)."}
        # Themen-Mix ueber Spiele: unsere Reihenfolge steht schon -> keine Gemini-Umsortierung (Default).
        bericht = schneide_ordner(arbeit, ausgabe, ziel_dauer=ziel_dauer, gemini=gemini)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)

    if not bericht.get("ok"):
        return {"ok": False, "fehler": bericht.get("fehler", "Schnitt fehlgeschlagen."), "schnitt": bericht}

    # Welche Clips wurden tatsaechlich verwendet (Pipeline kann am Budget kuerzen)? -> ueber Staging-Namen.
    verwendet_namen = {d["datei"] for d in bericht.get("details", [])}
    verwendet = [c for c, s in zip(auswahl, staged) if s.name in verwendet_namen] or auswahl

    meta = {"datum": tag.isoformat(), "thema": thema[0], "caption": thema[2],
            "status": "fertig_wartet_auf_freigabe", "fb_video_id": None,
            "ziel_dauer": ziel_dauer, "dauer_sek": bericht.get("dauer_sek"), "reel": str(ausgabe),
            "verwendete_clips": [c["pfad"] for c in verwendet],
            "spiele": sorted({c.get("spiel", "?") for c in verwendet}), "schnitt": bericht}
    (tag_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    with used_pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "datum": tag.isoformat(), "thema": thema[0],
                            "clips": [c["pfad"] for c in verwendet]}) + "\n")

    return {"ok": True, "datum": tag.isoformat(), "thema": thema[0], "reel": str(ausgabe),
            "verwendet": len(verwendet), "dauer_sek": bericht.get("dauer_sek"), "caption": thema[2],
            "metadata": str(tag_dir / "metadata.json")}


def _pfad(cli: str | None, env_key: str, fallback: str) -> Path:
    return Path(cli).expanduser() if cli else Path(os.environ.get(env_key, fallback)).expanduser()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Reel-Pipeline -- taegliches themenbasiertes 45s-Reel (kein Upload).")
    p.add_argument("--source", default=None, help="Quell-Verzeichnis (Spiel-Unterordner). Env REEL_SOURCE.")
    p.add_argument("--outbox", default=None, help="Ausgabe-Verzeichnis. Env REEL_OUTBOX.")
    p.add_argument("--state", default=None, help="Status-Verzeichnis (Index/used). Env REEL_STATE.")
    p.add_argument("--dauer", type=float, default=45.0, help="Ziel-Gesamtlaenge in Sekunden (Default 45).")
    p.add_argument("--datum", default=None, help="Datum YYYY-MM-DD (Default heute) -- fuer Tests/Nachlauf.")
    p.add_argument("--mit-gemini", action="store_true", help="Gemini-Reihenfolge zulassen (Default aus).")
    a = p.parse_args(argv)

    source = _pfad(a.source, "REEL_SOURCE", "~/ReelSource")
    outbox = _pfad(a.outbox, "REEL_OUTBOX", "~/ReelOutbox")
    state = _pfad(a.state, "REEL_STATE", "~/ReelState")
    tag = date.fromisoformat(a.datum) if a.datum else None

    res = lauf(source=source, outbox=outbox, state=state, tag=tag, ziel_dauer=a.dauer, gemini=a.mit_gemini)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
