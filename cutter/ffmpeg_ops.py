"""FFmpeg-Bausteine fuer den Cutter Agent (laeuft lokal auf dem Mac, kostenlos).

Reine Subprozess-Aufrufe an ffmpeg/ffprobe -- keine Python-Medien-Bibliothek, keine Cloud.
Erzeugt aus beliebigen Clips ein einheitliches **9:16-Instagram-Format** (1080x1920) mit
unscharfem Hintergrund (klassischer Reel-Look), normalisiertem Ton und sauberen Schnitten.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

BREITE, HOEHE, FPS = 1080, 1920, 30
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".hevc", ".mts"}

# Vertikales Format mit unscharfem, formatfuellendem Hintergrund + scharfem, eingepasstem Vordergrund.
_VERTIKAL = (
    f"split[a][b];"
    f"[a]scale={BREITE}:{HOEHE}:force_original_aspect_ratio=increase,"
    f"crop={BREITE}:{HOEHE},boxblur=24:2[bg];"
    f"[b]scale={BREITE}:{HOEHE}:force_original_aspect_ratio=decrease[fg];"
    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}"
)


@dataclass
class ClipInfo:
    pfad: Path
    dauer: float
    hat_audio: bool
    breite: int
    hoehe: int


def ffmpeg_vorhanden() -> bool:
    for werkzeug in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([werkzeug, "-version"], capture_output=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            return False
    return True


def hat_filter(name: str) -> bool:
    """Prueft, ob ein ffmpeg-Filter im Build vorhanden ist (z. B. 'subtitles' braucht libass)."""
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
        return any(f" {name} " in line for line in (r.stdout or "").splitlines())
    except (OSError, subprocess.SubprocessError):
        return False


def probe(pfad: Path) -> ClipInfo | None:
    """Liest Dauer/Aufloesung/Audio per ffprobe. None bei unlesbarer Datei."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(pfad)],
            capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None:
        return None
    hat_audio = any(s.get("codec_type") == "audio" for s in streams)
    try:
        dauer = float(d.get("format", {}).get("duration") or v.get("duration") or 0)
    except (TypeError, ValueError):
        dauer = 0.0
    return ClipInfo(pfad=Path(pfad), dauer=dauer, hat_audio=hat_audio,
                    breite=int(v.get("width") or 0), hoehe=int(v.get("height") or 0))


def clips_im_ordner(ordner: Path) -> list[Path]:
    """Alle Video-Dateien eines Ordners, alphabetisch (Reihenfolge = Dateiname)."""
    return sorted(p for p in Path(ordner).iterdir()
                  if p.is_file() and p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."))


def segment_normalisieren(quelle: Path, ziel: Path, *, start: float, dauer: float,
                          hat_audio: bool) -> bool:
    """Schneidet [start, start+dauer] und bringt es auf einheitliches 9:16-H.264-Format.

    Clips ohne Ton bekommen eine stille Tonspur, damit das spaetere Concat konsistente
    Streams hat. Gibt True bei Erfolg zurueck.
    """
    cmd = ["ffmpeg", "-y", "-ss", f"{max(0.0, start):.3f}", "-t", f"{max(0.1, dauer):.3f}",
           "-i", str(quelle)]
    if not hat_audio:
        cmd += ["-f", "lavfi", "-t", f"{max(0.1, dauer):.3f}", "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-vf", _VERTIKAL, "-r", str(FPS),
            "-map", "0:v:0", "-map", ("1:a:0" if not hat_audio else "0:a:0?"),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(ziel)]
    return _run(cmd)


def zusammenfuegen(segmente: list[Path], ziel: Path, *, untertitel_ass: Path | None = None,
                   leiser_ton: bool = False) -> bool:
    """Fuegt normalisierte Segmente zusammen, normalisiert die Lautheit, brennt optional Untertitel ein."""
    liste = ziel.parent / "_concat.txt"
    liste.write_text("".join(f"file '{s.as_posix()}'\n" for s in segmente), encoding="utf-8")
    vf = []
    # Untertitel nur einbrennen, wenn das ffmpeg-Build den subtitles-Filter (libass) hat.
    if untertitel_ass is not None and hat_filter("subtitles"):
        vf.append(f"subtitles={untertitel_ass.as_posix()}")
    af = ["loudnorm=I=-16:TP=-1.5:LRA=11"]
    if leiser_ton:
        af.append("volume=0.15")  # B-Roll: Ton leise lassen (Musik kommt in Instagram dazu)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste)]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-af", ",".join(af),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(ziel)]
    ok = _run(cmd)
    liste.unlink(missing_ok=True)
    return ok


def stille_spannen(pfad: Path, *, mindest_stille: float = 0.6, schwelle_db: int = -32) -> list[tuple]:
    """Erkennt Sprech-/Stille-Grenzen via ffmpeg silencedetect -> Liste (start, ende) der Stille."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(pfad), "-af",
             f"silencedetect=noise={schwelle_db}dB:d={mindest_stille}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return []
    spannen, start = [], None
    for line in (r.stderr or "").splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].strip().split()[0])
            except (ValueError, IndexError):
                start = None
        elif "silence_end:" in line and start is not None:
            try:
                ende = float(line.split("silence_end:")[1].split("|")[0].strip())
                spannen.append((start, ende))
            except (ValueError, IndexError):
                pass
            start = None
    return spannen


def _run(cmd: list[str]) -> bool:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
