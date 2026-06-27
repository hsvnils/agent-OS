"""Transkription fuer den Cutter Agent -- lokal & kostenlos bevorzugt.

Reihenfolge: (1) whisper.cpp-Binary (offline, gratis) -> (2) faster-whisper (offline) ->
(3) Deepgram-API (vorhandener Key, kleine Kosten) -> (4) leer (dann keine Untertitel).
Gibt Segmente [{"start": s, "ende": s, "text": ..}] zurueck. Robuste, fehlertolerante Subprozesse.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def verfuegbar() -> str:
    """Welcher Transkriptions-Weg ist nutzbar? -> 'whisper.cpp' | 'faster-whisper' | 'deepgram' | ''."""
    if _whisper_cpp_binary() and _whisper_cpp_modell():
        return "whisper.cpp"
    try:
        import faster_whisper  # noqa: F401
        return "faster-whisper"
    except Exception:
        pass
    if os.environ.get("DEEPGRAM_API_KEY"):
        return "deepgram"
    return ""


def transkribiere(pfad: Path, *, sprache: str = "de", deepgram_key: str = "") -> list[dict]:
    weg = verfuegbar()
    try:
        if weg == "whisper.cpp":
            return _whisper_cpp(pfad, sprache)
        if weg == "faster-whisper":
            return _faster_whisper(pfad, sprache)
        if weg == "deepgram" and (deepgram_key or os.environ.get("DEEPGRAM_API_KEY")):
            return _deepgram(pfad, deepgram_key or os.environ["DEEPGRAM_API_KEY"], sprache)
    except Exception:
        return []
    return []


def _wav16k(pfad: Path) -> Path:
    ziel = Path(tempfile.mkdtemp()) / "audio.wav"
    subprocess.run(["ffmpeg", "-y", "-i", str(pfad), "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", str(ziel)], capture_output=True, timeout=300)
    return ziel


def _whisper_cpp_binary() -> str:
    for name in ("whisper-cli", "whisper-cpp", "whisper"):
        p = shutil.which(name)
        if p:
            return p
    return ""


def _whisper_cpp_modell() -> str:
    env = os.environ.get("WHISPER_CPP_MODEL", "")
    if env and Path(env).exists():
        return env
    # Bessere Modelle bevorzugen (fuer Deutsch deutlich genauer): large > medium > small > base > tiny.
    rang = {"large": 0, "medium": 1, "small": 2, "base": 3, "tiny": 4}

    def schluessel(p: Path) -> int:
        return min((r for n, r in rang.items() if n in p.name.lower()), default=9)

    for kand in (Path.home() / "whisper-models", Path("/opt/homebrew/share/whisper-cpp")):
        if kand.is_dir():
            treffer = sorted(kand.glob("ggml-*.bin"), key=schluessel)
            if treffer:
                return str(treffer[0])
    return ""


def _whisper_cpp(pfad: Path, sprache: str) -> list[dict]:
    wav = _wav16k(pfad)
    out = wav.parent / "out"
    subprocess.run([_whisper_cpp_binary(), "-m", _whisper_cpp_modell(), "-f", str(wav),
                    "-l", sprache, "-oj", "-of", str(out)], capture_output=True, timeout=900)
    j = out.with_suffix(".json")
    if not j.exists():
        return []
    d = json.loads(j.read_text(encoding="utf-8"))
    segmente = []
    for s in d.get("transcription", []):
        off = s.get("offsets", {})
        text = (s.get("text") or "").strip()
        if text:
            segmente.append({"start": off.get("from", 0) / 1000.0,
                             "ende": off.get("to", 0) / 1000.0, "text": text})
    return segmente


def _faster_whisper(pfad: Path, sprache: str) -> list[dict]:
    from faster_whisper import WhisperModel
    modell = WhisperModel(os.environ.get("FASTER_WHISPER_MODEL", "base"),
                          device="cpu", compute_type="int8")
    segmente, _ = modell.transcribe(str(pfad), language=sprache)
    return [{"start": s.start, "ende": s.end, "text": s.text.strip()}
            for s in segmente if s.text.strip()]


def _deepgram(pfad: Path, key: str, sprache: str) -> list[dict]:
    import urllib.request
    wav = _wav16k(pfad)
    url = (f"https://api.deepgram.com/v1/listen?model=nova-2&language={sprache}"
           f"&smart_format=true&punctuate=true&utterances=true")
    req = urllib.request.Request(url, data=wav.read_bytes(), method="POST",
                                 headers={"Authorization": f"Token {key}",
                                          "Content-Type": "audio/wav"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    utts = d.get("results", {}).get("utterances", [])
    return [{"start": u.get("start", 0.0), "ende": u.get("end", 0.0),
             "text": (u.get("transcript") or "").strip()} for u in utts if u.get("transcript")]
