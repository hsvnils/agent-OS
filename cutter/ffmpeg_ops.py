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

# Crop-to-Fill: Bild wird vergroessert, bis es das 9:16-Format ganz fuellt, dann mittig beschnitten.
# KEIN Strecken (Seitenverhaeltnis bleibt), KEINE Blur-Balken. Plus dezenter Farb-Grade (Kontrast/Saettigung).
_GRADE = "eq=contrast=1.06:saturation=1.12:brightness=0.01"
_FUELLEN = (f"scale={BREITE}:{HOEHE}:force_original_aspect_ratio=increase,"
            f"crop={BREITE}:{HOEHE},setsar=1,fps={FPS}")
# Sanfter, langsamer Zoom (Ken-Burns) -- gibt B-Roll Leben. Quelle vorher leicht groesser skalieren.
_ZOOM = (f"scale={int(BREITE*1.25)}:{int(HOEHE*1.25)}:force_original_aspect_ratio=increase,"
         f"crop={int(BREITE*1.25)}:{int(HOEHE*1.25)},"
         f"zoompan=z='min(zoom+0.0008,1.18)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
         f"s={BREITE}x{HOEHE}:fps={FPS},setsar=1")


def _vertikal_filter(zoom: bool) -> str:
    return (f"{_ZOOM},{_GRADE}" if zoom else f"{_FUELLEN},{_GRADE}")


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


def _schwarzrand_crop(quelle: Path, start: float, dauer: float) -> str | None:
    """Erkennt eingebrannte schwarze Raender (cropdetect) -> 'crop=W:H:X:Y' oder None.

    Nur wenn wirklich ein Rand entfernt wird (>=4 % einer Dimension), damit nichts faelschlich
    beschnitten wird. So fuellt der Inhalt nach dem Scale-to-Fill garantiert ohne schwarze Balken.
    """
    info = probe(quelle)
    if not info or not info.breite or not info.hoehe:
        return None
    mid = max(0.0, start + dauer / 2)
    try:
        r = subprocess.run(["ffmpeg", "-ss", f"{mid:.2f}", "-t", "2", "-i", str(quelle),
                            "-vf", "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    crops = [line.split("crop=")[1].strip().split()[0]
             for line in (r.stderr or "").splitlines() if "crop=" in line]
    if not crops:
        return None
    try:
        w, h, x, y = (int(v) for v in crops[-1].split(":"))
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    if h <= info.hoehe * 0.96 or w <= info.breite * 0.96:     # echter Rand vorhanden
        return f"crop={w}:{h}:{x}:{y}"
    return None


def segment_normalisieren(quelle: Path, ziel: Path, *, start: float, dauer: float,
                          hat_audio: bool, zoom: bool = False, randschnitt: bool = True) -> bool:
    """Schneidet [start, start+dauer], entfernt schwarze Raender, fuellt 9:16 (Crop-to-Fill), graded.

    `zoom=True` legt einen sanften Ken-Burns-Zoom drueber (fuer B-Roll). `randschnitt` entfernt
    eingebrannte schwarze Balken vor dem Fuellen. Clips ohne Ton bekommen eine stille Tonspur.
    """
    vorfilter = ""
    if randschnitt:
        crop = _schwarzrand_crop(quelle, start, dauer)
        if crop:
            vorfilter = crop + ","
    cmd = ["ffmpeg", "-y", "-ss", f"{max(0.0, start):.3f}", "-t", f"{max(0.1, dauer):.3f}",
           "-i", str(quelle)]
    if not hat_audio:
        cmd += ["-f", "lavfi", "-t", f"{max(0.1, dauer):.3f}", "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-vf", vorfilter + _vertikal_filter(zoom), "-r", str(FPS),
            "-map", "0:v:0", "-map", ("1:a:0" if not hat_audio else "0:a:0?"),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(ziel)]
    return _run(cmd)


def dauer_von(pfad: Path) -> float:
    info = probe(pfad)
    return info.dauer if info else 0.0


def auf_groesse_begrenzen(pfad: Path, *, max_mb: float = 48.0) -> bool:
    """Re-encodet das Reel auf eine Ziel-Bitrate, falls > max_mb (Telegram-Bot-Limit ist 50 MB).

    Gibt True zurueck, wenn die Datei danach unter dem Limit liegt.
    """
    try:
        mb = Path(pfad).stat().st_size / 1024 / 1024
    except OSError:
        return False
    if mb <= max_mb:
        return True
    d = dauer_von(pfad) or 1.0
    ziel_bits = max_mb * 8 * 1024 * 1024 * 0.93           # etwas Reserve
    vbit = max(800_000, int(ziel_bits / d) - 128_000)     # minus Audio ~128k
    tmp = Path(pfad).with_suffix(".tmp.mp4")
    ok = _run(["ffmpeg", "-y", "-i", str(pfad),
               "-c:v", "libx264", "-preset", "medium", "-b:v", str(vbit),
               "-maxrate", str(int(vbit * 1.5)), "-bufsize", str(int(vbit * 2)), "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)])
    if ok and tmp.exists():
        tmp.replace(pfad)
        return Path(pfad).stat().st_size / 1024 / 1024 <= max_mb
    tmp.unlink(missing_ok=True)
    return False


def zusammenfuegen_xfade(segmente: list[Path], ziel: Path, *, uebergang: float = 0.35,
                         leiser_ton: bool = False) -> bool:
    """Fuegt Segmente mit weichen Uebergaengen (xfade) + Audio-Crossfade (acrossfade) zusammen.

    Tasteful rotierende Uebergaenge (Crossfade/Smooth-Slides). Lautheit am Ende normalisiert.
    """
    n = len(segmente)
    if n == 0:
        return False
    if n == 1:
        af = "loudnorm=I=-16:TP=-1.5:LRA=11"
        if leiser_ton:
            af = "volume=0.15," + af
        return _run(["ffmpeg", "-y", "-i", str(segmente[0]), "-af", af,
                     "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(ziel)])

    T = uebergang
    # Fester Uebergang fuer ALLE Schnitte: weiches Ueberblenden (Crossfade).
    typ = "fade"
    dauern = [max(0.5, dauer_von(s)) for s in segmente]
    filters: list[str] = []
    # Video: xfade-Kette mit kumulativem Offset.
    vlabel, cum = "[0:v]", dauern[0]
    for i in range(1, n):
        out = f"[v{i}]"
        offset = max(0.1, cum - T)
        filters.append(f"{vlabel}[{i}:v]xfade=transition={typ}:"
                       f"duration={T}:offset={offset:.3f}{out}")
        vlabel, cum = out, cum + dauern[i] - T
    # Audio: acrossfade-Kette.
    alabel = "[0:a]"
    for i in range(1, n):
        out = f"[a{i}]"
        filters.append(f"{alabel}[{i}:a]acrossfade=d={T}{out}")
        alabel = out
    af = f"{alabel}aresample=44100" + (",volume=0.15" if leiser_ton else "") + \
        ",loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    filters.append(af)

    cmd = ["ffmpeg", "-y"]
    for s in segmente:
        cmd += ["-i", str(s)]
    cmd += ["-filter_complex", ";".join(filters), "-map", vlabel, "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(ziel)]
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
