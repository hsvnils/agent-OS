"""Kontrolle am fertigen Video (CUTTER_AUSBAU C1): misst das gerenderte Reel und meldet Auffaelligkeiten.

Prueft Format, Bildrate, Tonspur, Dauer, Lautheit, True Peak, Schwarzbild, Standbild und lange Stille in EINEM
ffmpeg-Durchlauf. Misst und meldet nur -- ein Reel wird hier nicht gesperrt (CEO-Freigabe vor jeder Sperre).
`pruefe_video` wirft nie: Scheitert die Messung, steht das im Ergebnis und der Schnitt laeuft normal weiter.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import ffmpeg_ops as fo

ZIEL_LUFS = -16.0           # heutiges Render-Ziel (loudnorm in ffmpeg_ops); C2 stellt auf -14 um
LUFS_TOLERANZ = 3.0
MAX_TRUE_PEAK = -1.0
STUMM_LUFS = -60.0
MIN_DAUER = 1.0
FPS_TOLERANZ = 0.5
FAST_GANZ = 0.9             # Anteil der Laufzeit, ab dem „alles schwarz/eingefroren“ ein Fehler ist

_FILTER_V = "blackdetect=d=0.5:pix_th=0.10,freezedetect=n=0.003:d=2"
_FILTER_A = "ebur128=peak=true,silencedetect=n=-50dB:d=2"
_ZAHL = r"(-?\d+(?:\.\d+)?|-?inf)"


def _fps(text: str) -> float:
    z, _, n = str(text or "0/1").partition("/")
    try:
        return round(float(z) / float(n or 1), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _strom(pfad: Path) -> dict | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(pfad)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {"dauer": float((d.get("format") or {}).get("duration") or 0), "hat_video": v is not None,
            "breite": int((v or {}).get("width") or 0), "hoehe": int((v or {}).get("height") or 0),
            "fps": _fps((v or {}).get("avg_frame_rate")), "hat_ton": a is not None,
            "ton_hz": int((a or {}).get("sample_rate") or 0)}


def _zahl(text: str | None) -> float | None:
    if text is None or "inf" in text:
        return None
    return float(text)


def _spannen(text: str, start_re: str, dauer_re: str) -> list[dict]:
    starts, dauern = re.findall(start_re, text), re.findall(dauer_re, text)
    return [{"start": round(float(s), 2), "dauer": round(float(d), 2)} for s, d in zip(starts, dauern)]


def lies_messung(stderr: str, dauer: float | None = None) -> dict:
    """Zieht die Messwerte aus der ffmpeg-Ausgabe. Eigene Funktion, damit sie ohne ffmpeg testbar ist."""
    teil = stderr.rsplit("Summary:", 1)[-1] if "Summary:" in stderr else ""
    i, tp = re.search(rf"\bI:\s+{_ZAHL} LUFS", teil), re.search(rf"Peak:\s+{_ZAHL} dBFS", teil)
    schwarz = [{"start": round(float(a), 2), "dauer": round(float(d), 2)}
               for a, d in re.findall(r"black_start:([\d.]+) black_end:[\d.]+ black_duration:([\d.]+)", stderr)]
    standbild = _spannen(stderr, r"freeze_start: ([\d.]+)", r"freeze_duration: ([\d.]+)")
    starts = re.findall(r"freeze_start: ([\d.]+)", stderr)
    if dauer and len(starts) > len(standbild):          # Standbild bis zum Ende: freezedetect meldet dann keine Dauer
        standbild.append({"start": round(float(starts[-1]), 2), "dauer": round(dauer - float(starts[-1]), 2)})
    return {"lufs": _zahl(i.group(1)) if i else None, "true_peak": _zahl(tp.group(1)) if tp else None,
            "schwarz": schwarz, "standbild": standbild,
            "stille": _spannen(stderr, r"silence_start: ([\d.]+)", r"silence_duration: ([\d.]+)")}


def bewerte(w: dict, *, ziel_lufs: float | None = ZIEL_LUFS) -> list[dict]:
    """Regeln: Messwerte -> Befunde. `fehler` = technisch kaputt, `warnung` = bitte ansehen.

    `ziel_lufs=None`: Reel ist absichtlich leise (reine B-Roll, Musik kommt in der App dazu) -> Tonpegel nicht bewerten."""
    b: list[dict] = []

    def neu(art: str, stufe: str, text: str) -> None:
        b.append({"art": art, "stufe": stufe, "text": text})

    if not w.get("hat_video"):
        neu("video", "fehler", "Keine Bildspur.")
        return b
    if (w["breite"], w["hoehe"]) != (fo.BREITE, fo.HOEHE):
        neu("format", "fehler", f"Format {w['breite']}x{w['hoehe']} statt {fo.BREITE}x{fo.HOEHE}.")
    if abs(w["fps"] - fo.FPS) > FPS_TOLERANZ:
        neu("fps", "fehler", f"Bildrate {w['fps']:g} statt {fo.FPS}.")
    dauer = w.get("dauer") or 0.0
    if dauer < MIN_DAUER:
        neu("dauer", "fehler", f"Nur {dauer:.1f} s lang.")
    for art, name in (("schwarz", "Schwarzbild"), ("standbild", "Standbild")):
        spannen = w.get(art) or []
        summe = sum(s["dauer"] for s in spannen)
        if spannen and dauer and summe >= dauer * FAST_GANZ:
            neu(art, "fehler", f"{name} über fast die ganze Laufzeit.")
        elif spannen:
            neu(art, "warnung", f"{name} bei {spannen[0]['start']:.1f} s ({summe:.1f} s insgesamt).")
    if not w.get("hat_ton"):
        neu("ton", "fehler", "Keine Tonspur.")
        return b
    if ziel_lufs is None:
        return b
    lufs = w.get("lufs")
    if lufs is None or lufs < STUMM_LUFS:
        neu("stumm", "warnung", "Tonspur ist praktisch stumm.")
        return b
    if abs(lufs - ziel_lufs) > LUFS_TOLERANZ:
        neu("lautheit", "warnung", f"Lautheit {lufs:.1f} LUFS, Ziel {ziel_lufs:.0f}.")
    if w.get("true_peak") is not None and w["true_peak"] > MAX_TRUE_PEAK:
        neu("true_peak", "warnung", f"True Peak {w['true_peak']:.1f} dBFS, Grenze {MAX_TRUE_PEAK:.0f}.")
    if w.get("stille"):
        neu("stille", "warnung", f"Stille bei {w['stille'][0]['start']:.1f} s "
                                 f"({sum(s['dauer'] for s in w['stille']):.1f} s insgesamt).")
    return b


def pruefe_video(pfad, *, ziel_lufs: float | None = ZIEL_LUFS, timeout: int = 600) -> dict:
    """-> {gemessen, ok, befunde, werte}; `ok` ist None, wenn nicht gemessen werden konnte. Wirft nie."""
    try:
        pfad = Path(pfad)
        w = _strom(pfad)
        if w is None:
            return {"gemessen": False, "ok": None, "fehler": "ffprobe konnte die Datei nicht lesen.", "befunde": []}
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(pfad)]
        if w["hat_video"]:
            cmd += ["-vf", _FILTER_V]
        if w["hat_ton"]:
            cmd += ["-af", _FILTER_A]
        r = subprocess.run(cmd + ["-f", "null", "-"], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"gemessen": False, "ok": None, "fehler": (r.stderr or "ffmpeg-Fehler")[-300:], "befunde": []}
        w |= lies_messung(r.stderr, w["dauer"])
        befunde = bewerte(w, ziel_lufs=ziel_lufs)
        return {"gemessen": True, "ok": not any(x["stufe"] == "fehler" for x in befunde),
                "befunde": befunde, "werte": w}
    except Exception as exc:                            # Die Kontrolle darf nie den Schnitt mitreissen
        return {"gemessen": False, "ok": None, "fehler": f"{type(exc).__name__}: {exc}"[:300], "befunde": []}


def als_text(q: dict | None) -> str:
    """Kurztext fuer die Meldung an den CEO; leer, wenn es nichts zu melden gibt."""
    if not q:
        return ""
    if not q.get("gemessen"):
        return f"⚠️ Video-Kontrolle nicht möglich: {q.get('fehler', 'unbekannt')}"
    if not q.get("befunde"):
        return ""
    kopf = "❌ Video-Kontrolle: Fehler" if not q.get("ok") else "⚠️ Video-Kontrolle: bitte ansehen"
    return kopf + "\n" + "\n".join(f"- {x['text']}" for x in q["befunde"])
