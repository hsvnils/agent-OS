"""Clip-Brain (Video-Second-Brain) -- Stufe 1: Technik + Qualitaet. Gratis, kein LLM, kein Upload.

Baut einen PERSISTENTEN, archivweiten Index ueber alle Spielordner. Jeder Clip bekommt eine "Clip-Karte":
  * Technik:   Aufloesung, Format (hoch/quer/quadrat), Dauer, fps, Ton ja/nein, Codec
  * Qualitaet: Lautheit (LUFS), Stille-Anteil, Schwarzbild-Anteil, Schaerfe-Proxy, Szenendichte
  * `qualitaet`: transparenter Score 0..100 aus den Teil-Scores (jede Teilnote wird mitgespeichert)

Signatur-Cache (mtime+groesse) -> jeder Clip wird genau EINMAL analysiert. `--limit` macht den Lauf
resumable: nachts N neue Clips, bis das Archiv durch ist.

Metriken, die der ffmpeg-Build nicht kann, werden **uebersprungen** (Wert None) statt geraten.
Verwacklung wird bewusst NICHT gemessen (braucht `vidstabdetect`, in unserem Build nicht vorhanden).

Spaetere Stufen (Transkript, KI-Beschreibung, Suche) schreiben in dieselbe Karte -- siehe
`docs/video-brain-plan.md`.

CLI:  python -m cutter.clip_brain --source /reelsrc --index /app/reel_work/state/clip_brain.json [--limit 200]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

from . import ffmpeg_ops as fo
from . import reel_source as rq

INDEX_VERSION = 1
_MAX_ANALYSE_SEK = 30          # nur die ersten 30 s je Clip analysieren -> beschraenkt die Rechenzeit


# ---------------------------------------------------------------- Parser (rein, gut testbar)

def _parse_lufs(text: str) -> float | None:
    """Integrierte Lautheit aus der ebur128-Zusammenfassung ('I:  -23.0 LUFS'). None wenn nicht gefunden."""
    treffer = re.findall(r"^\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", text or "", re.MULTILINE)
    return float(treffer[-1]) if treffer else None


def _parse_stille(text: str) -> float:
    """Summe der Stille-Sekunden aus silencedetect ('silence_duration: 1.23')."""
    return sum(float(x) for x in re.findall(r"silence_duration:\s*(\d+(?:\.\d+)?)", text or ""))


def _parse_schwarz(text: str) -> float:
    """Summe der Schwarzbild-Sekunden aus blackdetect ('black_duration:1.23')."""
    return sum(float(x) for x in re.findall(r"black_duration:\s*(\d+(?:\.\d+)?)", text or ""))


def _parse_yavg(text: str) -> float | None:
    """Mittlere Kantenenergie (signalstats YAVG nach edgedetect) -> Schaerfe-Proxy. None wenn nichts kam."""
    werte = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=(\d+(?:\.\d+)?)", text or "")]
    return round(sum(werte) / len(werte), 3) if werte else None


def format_label(breite: int, hoehe: int) -> str:
    """9:16-artig -> 'hoch', 16:9-artig -> 'quer', sonst 'quadrat'. Unbekannt -> ''."""
    if not breite or not hoehe:
        return ""
    v = breite / hoehe
    if v < 0.95:
        return "hoch"
    if v > 1.05:
        return "quer"
    return "quadrat"


# ---------------------------------------------------------------- Teil-Scores + Gesamtnote

def _score_aufloesung(breite: int, hoehe: int) -> float:
    kurz = min(breite, hoehe) if (breite and hoehe) else 0
    if not kurz:
        return 0.5                                     # unbekannt -> neutral
    if kurz >= 1080:
        return 1.0
    if kurz >= 720:
        return 0.7
    if kurz >= 480:
        return 0.4
    return 0.15


def _score_schaerfe(yavg: float | None, median: float | None = None) -> float:
    """Kantenenergie -> 0..1.

    Kantenenergie hat KEINEN universellen Massstab (haengt von Motiv/Kontrast ab). Darum bewerten wir
    **relativ zum Archiv-Median**, sobald der bekannt ist: halb so scharf wie der Median -> 0.2,
    Median -> ~0.56, ab 1.6x Median -> 1.0. Ohne Median (kleines Archiv) greift eine grosszuegige
    Absolut-Skala, die an echtem Material geeicht ist (real gemessen: ~9-38, synthetisch: ~0-6).
    """
    if yavg is None:
        return 0.5
    if median and median > 0:
        v = yavg / median
        if v <= 0.5:
            return 0.2
        if v >= 1.6:
            return 1.0
        return round(0.2 + 0.8 * (v - 0.5) / 1.1, 3)
    if yavg <= 4.0:
        return 0.2
    if yavg >= 25.0:
        return 1.0
    return round(0.2 + 0.8 * (yavg - 4.0) / 21.0, 3)


def _score_ton(hat_audio: bool, lufs: float | None) -> float:
    """Lautheit nahe -14 LUFS ist gut; sehr leise (< -35) schlecht. Ohne Ton/Messung -> neutral."""
    if not hat_audio:
        return 0.3
    if lufs is None:
        return 0.5
    if lufs <= -35:
        return 0.2
    if lufs >= -18:
        return 1.0
    return round(0.2 + 0.8 * (lufs + 35) / 17.0, 3)


def qualitaets_score(k: dict, *, median_schaerfe: float | None = None) -> dict:
    """Transparente Gesamtnote 0..100 aus Teil-Scores. Gibt {gesamt, teil:{...}} zurueck.

    Objektive Maengel (Aufloesung, Stille, Schwarzbild, Ton) werden **absolut** bewertet -> schlechte Clips
    bleiben schlecht. Nur die **Schaerfe** wird relativ zum Archiv bewertet (siehe `_score_schaerfe`).
    """
    dauer = max(0.1, float(k.get("dauer") or 0.1))
    stille = min(1.0, float(k.get("stille_sek") or 0.0) / dauer)
    schwarz = min(1.0, float(k.get("schwarz_sek") or 0.0) / dauer)
    teil = {
        "aufloesung": _score_aufloesung(k.get("breite") or 0, k.get("hoehe") or 0),
        "schaerfe": _score_schaerfe(k.get("schaerfe_yavg"), median_schaerfe),
        "ton": _score_ton(bool(k.get("hat_audio")), k.get("lufs")),
        "stille": round(1.0 - stille, 3),
        "schwarz": round(1.0 - schwarz, 3),
    }
    gewicht = {"aufloesung": 0.35, "schaerfe": 0.25, "stille": 0.15, "schwarz": 0.15, "ton": 0.10}
    gesamt = sum(teil[k2] * g for k2, g in gewicht.items())
    return {"gesamt": int(round(100 * max(0.0, min(1.0, gesamt)))), "teil": teil}


# ---------------------------------------------------------------- ffmpeg-Messungen (best-effort)

def _lauf(cmd: list[str], timeout: int = 180) -> str:
    """ffmpeg/ffprobe ausfuehren -> stdout+stderr als Text. Leerer String bei Fehler (nie werfen)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def _ffprobe(pfad: Path) -> dict | None:
    """Technik-Daten via ffprobe: breite/hoehe/dauer/fps/codec/bitrate/hat_audio."""
    roh = _lauf(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(pfad)])
    try:
        d = json.loads(roh)
    except (ValueError, TypeError):
        return None
    streams = d.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not v:
        return None
    try:
        num, den = (v.get("avg_frame_rate") or "0/1").split("/")
        fps = round(float(num) / float(den), 2) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    try:
        dauer = float((d.get("format") or {}).get("duration") or v.get("duration") or 0)
    except (TypeError, ValueError):
        dauer = 0.0
    try:
        bitrate = int((d.get("format") or {}).get("bit_rate") or 0)
    except (TypeError, ValueError):
        bitrate = 0
    breite, hoehe = int(v.get("width") or 0), int(v.get("height") or 0)
    return {"breite": breite, "hoehe": hoehe, "dauer": round(dauer, 2), "fps": fps,
            "codec": v.get("codec_name") or "", "bitrate": bitrate,
            "hat_audio": any(s.get("codec_type") == "audio" for s in streams),
            "format": format_label(breite, hoehe)}


def _messe_ton_und_schwarz(pfad: Path, hat_audio: bool) -> dict:
    """EIN ffmpeg-Durchlauf: Lautheit (ebur128) + Stille (silencedetect) + Schwarzbild (blackdetect)."""
    vf, af = [], []
    if fo.hat_filter("blackdetect"):
        vf.append("blackdetect=d=0.2:pix_th=0.10")
    if hat_audio and fo.hat_filter("ebur128"):
        af.append("ebur128=peak=true")
    if hat_audio and fo.hat_filter("silencedetect"):
        af.append("silencedetect=n=-32dB:d=0.6")
    if not vf and not af:
        return {}
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-t", str(_MAX_ANALYSE_SEK), "-i", str(pfad)]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if af:
        cmd += ["-af", ",".join(af)]
    else:
        cmd += ["-an"]
    cmd += ["-f", "null", "-"]
    txt = _lauf(cmd)
    out: dict = {}
    if vf:
        out["schwarz_sek"] = round(_parse_schwarz(txt), 2)
    if af:
        out["lufs"] = _parse_lufs(txt)
        out["stille_sek"] = round(_parse_stille(txt), 2)
    return out


def _messe_schaerfe(pfad: Path) -> float | None:
    """Schaerfe-Proxy: 1 Bild/s, 360p, Kantenerkennung -> mittlere Kantenenergie (YAVG)."""
    if not (fo.hat_filter("edgedetect") and fo.hat_filter("signalstats")):
        return None
    txt = _lauf(["ffmpeg", "-hide_banner", "-nostats", "-t", str(_MAX_ANALYSE_SEK), "-i", str(pfad),
                 "-vf", "fps=1,scale=-2:360,edgedetect,signalstats,metadata=mode=print:file=-",
                 "-an", "-f", "null", "-"])
    return _parse_yavg(txt)


def bewerte_index(index: dict) -> int:
    """Rechnet die Qualitaets-Noten ALLER Clips neu -- relativ zum Archiv-Median der Schaerfe.
    Rein rechnerisch (kein ffmpeg), daher billig. Gibt die Anzahl bewerteter Clips zurueck."""
    karten = index.get("clips") or {}
    werte = [k["schaerfe_yavg"] for k in karten.values() if k.get("schaerfe_yavg")]
    median = statistics.median(werte) if len(werte) >= 5 else None   # zu kleines Archiv -> Absolut-Skala
    index["median_schaerfe"] = round(median, 3) if median else None
    for k in karten.values():
        q = qualitaets_score(k, median_schaerfe=median)
        k["qualitaet"] = q["gesamt"]
        k["qualitaet_teil"] = q["teil"]
    return len(karten)


def analysiere_clip(pfad: Path, *, mit_szenen: bool = False) -> dict | None:
    """Vollstaendige Clip-Karte (Stufe 1). None, wenn der Clip nicht lesbar ist."""
    tech = _ffprobe(pfad)
    if not tech or tech["dauer"] <= 0:
        return None
    mess = _messe_ton_und_schwarz(pfad, tech["hat_audio"])
    schaerfe = _messe_schaerfe(pfad)
    szenen = len(fo.szenen_zeiten(pfad)) if mit_szenen else None
    k = {**tech, **mess, "schaerfe_yavg": schaerfe}
    if szenen is not None:
        k["szenen"] = szenen
        k["szenendichte"] = round(min(1.0, szenen / max(1.0, tech["dauer"] / 3.0)), 3)
    q = qualitaets_score(k)
    k["qualitaet"] = q["gesamt"]
    k["qualitaet_teil"] = q["teil"]
    return k


# ---------------------------------------------------------------- Archiv-Index (persistent, resumable)

def _lade_index(pfad: Path) -> dict:
    if not pfad.exists():
        return {"version": INDEX_VERSION, "clips": {}}
    try:
        d = json.loads(pfad.read_text("utf-8"))
        if isinstance(d, dict) and isinstance(d.get("clips"), dict):
            return d
    except (ValueError, OSError):
        pass
    return {"version": INDEX_VERSION, "clips": {}}


def _speichere_index(pfad: Path, index: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(pfad)                                  # atomar -> nie halb geschriebener Index


def _signatur(pfad: Path) -> list:
    st = pfad.stat()
    return [st.st_mtime_ns, st.st_size]


def baue_archiv_index(source, index_pfad, *, limit: int = 0, neu: bool = False,
                      mit_szenen: bool = False) -> dict:
    """Analysiert alle Clips aller Spielordner (Stufe 1) und schreibt den persistenten Index.

    Unveraenderte, bereits analysierte Clips werden uebersprungen (Signatur-Cache).
    `limit` > 0 -> hoechstens so viele NEUE Clips je Lauf (resumable). `neu=True` -> alles neu messen.
    """
    source, index_pfad = Path(source), Path(index_pfad)
    if not fo.ffmpeg_vorhanden():
        return {"ok": False, "fehler": "ffmpeg/ffprobe nicht gefunden."}
    if not source.exists():
        return {"ok": False, "fehler": f"Quelle nicht gefunden: {source}"}

    index = {"version": INDEX_VERSION, "clips": {}} if neu else _lade_index(index_pfad)
    karten = index["clips"]
    analysiert, uebersprungen, fehler, offen = 0, 0, 0, 0

    for spiel_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        if not rq.ist_spielordner(spiel_dir.name):
            continue
        for pfad in fo.clips_im_ordner(spiel_dir):
            key = str(pfad)
            try:
                sig = _signatur(pfad)
            except OSError:
                continue
            alt = karten.get(key)
            if alt and alt.get("sig") == sig and alt.get("stufe", 0) >= 1:
                uebersprungen += 1
                continue
            if limit and analysiert >= limit:           # Rest bleibt fuer den naechsten Lauf
                offen += 1
                continue
            karte = analysiere_clip(pfad, mit_szenen=mit_szenen)
            if karte is None:
                fehler += 1
                continue
            karten[key] = {**karte, "pfad": key, "spiel": spiel_dir.name, "datei": pfad.name,
                           "sig": sig, "stufe": 1, "ts": time.time()}
            analysiert += 1

    bewerte_index(index)                               # Noten archivweit neu (relativ zur Schaerfe-Verteilung)
    index["stand"] = time.time()
    _speichere_index(index_pfad, index)
    return {"ok": True, "gesamt": len(karten), "analysiert": analysiert,
            "uebersprungen": uebersprungen, "offen": offen, "fehler": fehler,
            "median_schaerfe": index.get("median_schaerfe"), "datei": str(index_pfad)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Clip-Brain Stufe 1 -- Technik + Qualitaet (gratis, kein LLM).")
    p.add_argument("--source", required=True, help="Archiv-Wurzel mit Spiel-Unterordnern (z. B. /reelsrc).")
    p.add_argument("--index", required=True, help="Ziel-Datei des Clip-Index (JSON).")
    p.add_argument("--limit", type=int, default=0, help="Max. NEUE Clips je Lauf (0 = alle). Resumable.")
    p.add_argument("--neu", action="store_true", help="Alles neu messen (Cache ignorieren).")
    p.add_argument("--mit-szenen", action="store_true",
                   help="Szenen-Analyse mitlaufen lassen (langsam; bei Einzelaufnahmen meist 0 Szenen).")
    p.add_argument("--nur-bewerten", action="store_true",
                   help="Nur die Noten neu berechnen (kein ffmpeg) -- z. B. nach Gewichts-Aenderung.")
    a = p.parse_args(argv)
    if a.nur_bewerten:
        index = _lade_index(Path(a.index))
        n = bewerte_index(index)
        _speichere_index(Path(a.index), index)
        res = {"ok": True, "bewertet": n, "median_schaerfe": index.get("median_schaerfe"), "datei": a.index}
    else:
        res = baue_archiv_index(a.source, a.index, limit=a.limit, neu=a.neu, mit_szenen=a.mit_szenen)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
