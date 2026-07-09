"""Reel-Pipeline (Stufe A+B, Orchestrator) -- taeglicher Lauf am Mac.

Ablauf: **ein Spielordner pro Reel auswaehlen** (rotierend, am laengsten nicht dran zuerst) -> nur diesen
Ordner indizieren -> Tages-Thema + Clip-Auswahl (Anti-Doppel) -> ausgewaehlte Clips in einen Arbeitsordner
verlinken -> bestehende Cutter-Pipeline schneidet ein 45s-Reel -> Ablage in `outbox/<datum>/reel.mp4` +
`metadata.json` -> genutzte Clips + Spiel protokollieren (`state/used.jsonl`, `state/used_games.jsonl`).

Ein Reel = ein Spiel. So bleibt jedes Reel thematisch geschlossen und der Index-Aufbau ist schnell
(nur ein Ordner statt des ganzen Archivs).

**Kein Upload, keine Veroeffentlichung.** Das fertige Reel wartet auf die 1-Tap-Freigabe (Stufe C/D).
Rein lokal/gratis. Pfade per CLI/Env konfigurierbar (Quelle liegt auf der gemounteten NAS).

CLI:  python -m cutter.reel_daily [--source ..] [--outbox ..] [--state ..] [--dauer 45] [--datum YYYY-MM-DD]
      [--spiel "HSV vs FCB - 2026-05-01"]  # gezielt EIN Spiel (Default: automatische Rotation)
Env:  REEL_SOURCE / REEL_OUTBOX / REEL_STATE
"""
from __future__ import annotations

import argparse
import json
import os
import random
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


def _lade_allowlist(state: Path) -> set | None:
    """Optionale explizite Allowlist `state/source_allowlist.txt` (ein Ordnername je Zeile, '#'=Kommentar).
    Fehlt sie -> None (dann greift die Spielordner-Heuristik)."""
    p = state / "source_allowlist.txt"
    if not p.exists():
        return None
    namen = {ln.strip() for ln in p.read_text("utf-8").splitlines() if ln.strip() and not ln.startswith("#")}
    return namen or None


def _spielordner(source: Path, allowlist: set | None) -> list[str]:
    """Namen aller in Frage kommenden Spielordner in `source` (sortiert). Ist `allowlist` gesetzt, zaehlen
    nur diese Ordner; sonst die per `ist_spielordner` erkannten. Nur der Ordner-SCAN, kein ffprobe -> schnell."""
    if not source.exists():
        return []
    namen: list[str] = []
    for d in sorted(p for p in source.iterdir() if p.is_dir()):
        if allowlist is not None:
            if d.name in allowlist:
                namen.append(d.name)
        elif rq.ist_spielordner(d.name):
            namen.append(d.name)
    return namen


def waehle_spiel(spiele: list[str], used_games_pfad: Path, seed: str) -> str | None:
    """Waehlt EIN Spiel: das am laengsten nicht genutzte zuerst (nie genutzt = ganz vorn) -> alle Spiele
    kommen der Reihe nach durch, kein Doppel bis alle dran waren. Gleichstand -> deterministisch je `seed`."""
    if not spiele:
        return None
    last: dict[str, float] = {}
    p = Path(used_games_pfad)
    if p.exists():
        for line in p.read_text("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            s = ev.get("spiel")
            if s:
                last[s] = max(last.get(s, 0.0), float(ev.get("ts", 0)))
    rnd = random.Random(seed)
    return sorted(spiele, key=lambda s: (last.get(s, 0.0), rnd.random()))[0]


def lauf(*, source: Path, outbox: Path, state: Path, tag: date | None = None,
         ziel_dauer: float = 45.0, clip_laenge: float = 4.6, gemini: bool = False,
         transkribieren: bool = False, schnell_index: bool = False, spiel: str | None = None,
         thema_name: str | None = None, alle_spiele: bool = False, min_dauer: float = 15.0) -> dict:
    """Ein Reel erzeugen. Gibt einen Bericht (dict). Kein Upload.

    `clip_laenge` steuert das Tempo: ohne Transkription ist jeder Clip B-Roll dieser Laenge -> ziel_dauer /
    clip_laenge ergibt die Clip-Anzahl (Default ~4,6s -> ~9-10 Clips fuer ein 45s-Reel).
    `spiel`: gezielt EIN Spielordner (Name); ohne Angabe waehlt die Rotation automatisch eines aus.
    `thema_name`: gezieltes Thema (z. B. "Torjubel"); ohne Angabe die Tages-Rotation.
    `alle_spiele`: ueber ALLE Spiele hinweg suchen (statt einem Ordner) -- fuer manuelle Themen-Reels.
    `min_dauer`: Mindestlaenge in Sekunden (Default 15). Faellt das Reel darunter, wird es NICHT eingereicht.
    """
    tag = tag or date.today()
    source = Path(source)
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    index_pfad = state / "clip_index.json"
    used_pfad = state / "used.jsonl"
    used_games_pfad = state / "used_games.jsonl"

    # Einzelspiel (schnell, thematisch geschlossen) ODER ueber alle Spiele (manueller Themen-Reel).
    allow = _lade_allowlist(state)
    verfuegbar = _spielordner(source, allow)
    if not verfuegbar:
        return {"ok": False, "fehler": f"Keine Spielordner in der Quelle gefunden: {source}"}
    if alle_spiele:
        gewaehlt = None
        index_allow = set(verfuegbar)                     # ueber ALLE Spiele suchen
        label = "alle Spiele"
    else:
        gewaehlt = spiel or waehle_spiel(verfuegbar, used_games_pfad, tag.isoformat())
        if gewaehlt not in verfuegbar:
            return {"ok": False, "fehler": f"Spielordner '{gewaehlt}' nicht gefunden. "
                                           f"Verfuegbar: {', '.join(verfuegbar[:20])}"}
        index_allow = {gewaehlt}
        label = gewaehlt

    idx_res = rq.baue_index(source, index_pfad, neu=True, allowlist=index_allow,
                            energie_analyse=not schnell_index)
    if not idx_res.get("ok"):
        return idx_res
    index = rq.lade_index(index_pfad)
    if not index:
        return {"ok": False, "fehler": f"Keine Clips gefunden ({label})."}

    thema = rs.thema_by_name(thema_name) or rs.thema_fuer_tag(tag)
    spiel_tag = "" if alle_spiele else rq.spiel_hashtag(gewaehlt)   # z. B. "#HSVFCB" -- an die Caption
    caption = f"{thema[2]} {spiel_tag}" if spiel_tag else thema[2]
    genutzt = rs.lade_genutzte(used_pfad)
    # Nur so viele Clips waehlen (+ kleiner Puffer), wie ins Budget passen -> keine unnoetige Clip-Analyse.
    max_clips = int(ziel_dauer / max(1.0, clip_laenge)) + 3
    auswahl = rs.waehle_clips(index, thema, genutzt=genutzt, max_clips=max_clips,
                              seed=(thema_name or "") + tag.isoformat())
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
        # Transkription standardmaessig AUS (Fan-Montage mit Originalton -> viel schneller, kein Whisper).
        bericht = schneide_ordner(arbeit, ausgabe, ziel_dauer=ziel_dauer, broll_dauer=clip_laenge,
                                  gemini=gemini, transkribieren=transkribieren)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)

    if not bericht.get("ok"):
        return {"ok": False, "fehler": bericht.get("fehler", "Schnitt fehlgeschlagen."), "schnitt": bericht}

    # Mindestlaenge erzwingen: zu kurze Reels werden NICHT eingereicht (globale Regel, Default 15 s).
    dauer = float(bericht.get("dauer_sek") or 0)
    if dauer < min_dauer:
        return {"ok": False, "zu_kurz": True, "dauer_sek": dauer, "thema": thema[0], "spiel": label,
                "fehler": f"Reel nur {dauer:.0f}s (< Mindestlaenge {min_dauer:.0f}s) — nicht eingereicht. "
                          f"Zu wenige/zu kurze passende Clips ({label})."}

    # Welche Clips wurden tatsaechlich verwendet (Pipeline kann am Budget kuerzen)? -> ueber Staging-Namen.
    verwendet_namen = {d["datei"] for d in bericht.get("details", [])}
    verwendet = [c for c, s in zip(auswahl, staged) if s.name in verwendet_namen] or auswahl

    spiele = sorted({c.get("spiel", "?") for c in verwendet}) or ([gewaehlt] if gewaehlt else [])
    meta = {"datum": tag.isoformat(), "thema": thema[0], "caption": caption,
            "status": "fertig_wartet_auf_freigabe", "fb_video_id": None,
            "ziel_dauer": ziel_dauer, "dauer_sek": bericht.get("dauer_sek"), "reel": str(ausgabe),
            "verwendete_clips": [c["pfad"] for c in verwendet],
            "spiel": label, "spiele": spiele, "schnitt": bericht}
    (tag_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    with used_pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "datum": tag.isoformat(), "thema": thema[0],
                            "spiel": label, "clips": [c["pfad"] for c in verwendet]}) + "\n")
    if gewaehlt:                                                            # Spiel-Rotation nur bei Einzelspiel
        with used_games_pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "datum": tag.isoformat(), "spiel": gewaehlt}) + "\n")

    return {"ok": True, "datum": tag.isoformat(), "thema": thema[0], "spiel": label, "reel": str(ausgabe),
            "verwendet": len(verwendet), "dauer_sek": bericht.get("dauer_sek"), "caption": caption,
            "spiele": spiele, "metadata": str(tag_dir / "metadata.json")}


def _einreichen(res: dict) -> dict:
    """Reicht das fertige Reel bei LUNA-OS zur CEO-Freigabe ein (ueber die Mac-Bruecke). Best-effort."""
    from .luna_bridge import LunaBridge
    from .pipeline import _lade_env
    env = _lade_env()
    for k in ("LUNA_OS_URL", "LUNA_OS_USER", "LUNA_OS_PASSWORD"):   # Prozess-Env darf .env ueberschreiben
        if os.environ.get(k):                                       # (NAS-Job im Container: localhost:8765)
            env[k] = os.environ[k]
    br = LunaBridge.from_env(env)
    if not br.aktiv():
        return {"eingereicht": False, "hinweis": "LUNA-OS-Bruecke inaktiv (LUNA_OS_URL/PASSWORD fehlt)."}
    meta = {k: res.get(k) for k in ("datum", "thema", "caption", "dauer_sek", "spiele")}
    r = br.reel_einreichen(res["reel"], meta)
    return {"eingereicht": bool(r and r.get("ok")), "reel_id": (r or {}).get("id")}


def _pfad(cli: str | None, env_key: str, fallback: str) -> Path:
    return Path(cli).expanduser() if cli else Path(os.environ.get(env_key, fallback)).expanduser()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Reel-Pipeline -- taegliches themenbasiertes 45s-Reel (kein Upload).")
    p.add_argument("--source", default=None, help="Quell-Verzeichnis (Spiel-Unterordner). Env REEL_SOURCE.")
    p.add_argument("--outbox", default=None, help="Ausgabe-Verzeichnis. Env REEL_OUTBOX.")
    p.add_argument("--state", default=None, help="Status-Verzeichnis (Index/used). Env REEL_STATE.")
    p.add_argument("--dauer", type=float, default=45.0, help="Ziel-Gesamtlaenge in Sekunden (Default 45).")
    p.add_argument("--clip-laenge", type=float, default=4.6,
                   help="Laenge je Clip in Sekunden -> steuert die Anzahl (Default 4.6 -> ~9-10 Clips).")
    p.add_argument("--datum", default=None, help="Datum YYYY-MM-DD (Default heute) -- fuer Tests/Nachlauf.")
    p.add_argument("--spiel", default=None,
                   help="Gezielt EIN Spielordner (exakter Name). Ohne Angabe: automatische Rotation.")
    p.add_argument("--thema", default=None,
                   help="Gezieltes Thema (z. B. 'Torjubel'). Ohne Angabe: Tages-Rotation.")
    p.add_argument("--alle-spiele", action="store_true",
                   help="Ueber ALLE Spiele hinweg suchen (statt einem Ordner) -- fuer manuelle Themen-Reels.")
    p.add_argument("--min-dauer", type=float, default=15.0,
                   help="Mindestlaenge in Sekunden (Default 15). Kuerzere Reels werden nicht eingereicht.")
    p.add_argument("--mit-gemini", action="store_true", help="Gemini-Reihenfolge zulassen (Default aus).")
    p.add_argument("--mit-transkript", action="store_true",
                   help="Whisper-Transkription an (Sprach-Trimmen; Default aus -> schneller).")
    p.add_argument("--einreichen", action="store_true",
                   help="Fertiges Reel zur CEO-Freigabe an LUNA-OS senden (Stufe C). Kein Auto-Posten.")
    p.add_argument("--schnell-index", action="store_true",
                   help="Index ohne Szenen-/Ton-Analyse (nur Auflösung/Dauer) -> viel schneller beim Erst-"
                        "Aufbau grosser Archive (NAS). Inhaltserkennung uebernimmt Gemini-Tagging.")
    a = p.parse_args(argv)

    source = _pfad(a.source, "REEL_SOURCE", "~/ReelSource")
    outbox = _pfad(a.outbox, "REEL_OUTBOX", "~/ReelOutbox")
    state = _pfad(a.state, "REEL_STATE", "~/ReelState")
    tag = date.fromisoformat(a.datum) if a.datum else None

    res = lauf(source=source, outbox=outbox, state=state, tag=tag, ziel_dauer=a.dauer,
               clip_laenge=a.clip_laenge, gemini=a.mit_gemini, transkribieren=a.mit_transkript,
               schnell_index=a.schnell_index, spiel=a.spiel, thema_name=a.thema,
               alle_spiele=a.alle_spiele, min_dauer=a.min_dauer)
    if a.einreichen and res.get("ok"):
        res.update(_einreichen(res))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
