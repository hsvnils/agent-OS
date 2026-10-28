"""Sprach-Arbeiter (JARVIS_ALLTAG J2b) -- laeuft als systemd-Dienst `sprachdienst` auf dem MACO470.

Holt Sprachauftraege ueber die LUNA-OS-API (`/api/sprache/naechster`), spricht den Text mit der festgehaltenen
LUNA-Stimme C (CEO-Wahl 2026-10-28) und laedt die MP3 hoch (`/api/sprache/ergebnis`). Alles lokal auf dem Prozessor,
kein Cloud-Dienst; das Modell kommt aus dem lokalen Zwischenspeicher (`HF_HUB_OFFLINE=1` im Dienst).

Stimme: Qwen3-TTS-Basismodell klont die Referenzprobe C (`referenz.wav` + `referenz.txt` im Stimmordner, ausserhalb
des Repos). Modell 0.6B (CEO: „klingt gut“, Faktor ~6 Rechenzeit je Sekunde Sprache); 1.7B als Alternative vorgemerkt
(`SPRACHE_MODELL`). Das Modell wird nur fuer Auftraege geladen und nach `LEERLAUF_S` wieder freigegeben.

Start: `python -m sprachdienst.worker` (eigene Umgebung mit qwen-tts, siehe `deploy/sprachdienst.service`),
Probe ohne LUNA-OS: `python -m sprachdienst.worker --probe "Text" --aus probe.mp3`.
"""
from __future__ import annotations

import argparse
import base64
import gc
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from cutter.luna_bridge import LunaBridge
from cutter.pipeline import _lade_env

MODELL = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
STIMME = "~/luna-sprache/stimme_c"
MAX_ABSCHNITT = 350        # Zeichen je Erzeugung -- lange Texte am Stueck driften, Saetze bleiben ganz
PAUSE_S = 0.35
SEED = 7
LEERLAUF_S = 600


def _log(text: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}", flush=True)


def abschnitte(text: str, max_zeichen: int = MAX_ABSCHNITT) -> list[str]:
    """Text in Abschnitte aus ganzen Saetzen (je hoechstens `max_zeichen`); ueberlange Saetze an Kommas, notfalls hart."""
    saetze = [s for s in re.split(r"(?<=[.!?…])\s+", " ".join((text or "").split())) if s]
    teile: list[str] = []
    for s in saetze:
        while len(s) > max_zeichen:
            schnitt = s.rfind(", ", 0, max_zeichen)
            schnitt = schnitt + 1 if schnitt > max_zeichen // 3 else max_zeichen
            teile.append(s[:schnitt].strip())
            s = s[schnitt:].strip()
        teile.append(s)
    out: list[str] = []
    for t in teile:
        if out and len(out[-1]) + 1 + len(t) <= max_zeichen:
            out[-1] += " " + t
        else:
            out.append(t)
    return out


class Stimme:
    """Qwen3-TTS mit festgehaltener Stimme C. Laedt beim ersten Gebrauch, `freigeben()` gibt den Speicher zurueck."""

    def __init__(self, modell: str, ordner: str | Path, *, threads: int = 12):
        self.modell, self.ordner, self.threads = modell, Path(ordner).expanduser(), threads
        self._m = self._prompt = None
        self.zuletzt = 0.0

    def _laden(self):
        import torch
        from qwen_tts import Qwen3TTSModel
        from huggingface_hub import snapshot_download
        torch.set_num_threads(self.threads)
        t = time.time()
        # Lokaler Ordner statt Modellname: transformers 4.57 fragt bei Namen trotz HF_HUB_OFFLINE online nach
        # (`_patch_mistral_regex` -> model_info) und bricht offline ab.
        pfad = self.modell if Path(self.modell).is_dir() else snapshot_download(self.modell, local_files_only=True)
        self._m = Qwen3TTSModel.from_pretrained(pfad, device_map="cpu", dtype=torch.float32)
        self._prompt = self._m.create_voice_clone_prompt(
            ref_audio=str(self.ordner / "referenz.wav"),
            ref_text=(self.ordner / "referenz.txt").read_text(encoding="utf-8").strip())
        _log(f"Stimme geladen ({self.modell}) in {time.time() - t:.0f} s")

    def sprechen(self, text: str):
        """-> (Samples als numpy-Array, Abtastrate)."""
        import numpy as np
        import torch
        if self._m is None:
            self._laden()
        stuecke, sr = [], 24000
        for teil in abschnitte(text):
            torch.manual_seed(SEED)
            wavs, sr = self._m.generate_voice_clone(text=[teil], language=["German"], voice_clone_prompt=self._prompt)
            stuecke += [np.asarray(wavs[0], dtype=np.float32), np.zeros(int(sr * PAUSE_S), dtype=np.float32)]
        self.zuletzt = time.time()
        return (np.concatenate(stuecke) if stuecke else np.zeros(0, dtype=np.float32)), sr

    def freigeben(self, jetzt: float | None = None) -> None:
        if self._m is not None and (jetzt or time.time()) - self.zuletzt > LEERLAUF_S:
            self._m = self._prompt = None
            gc.collect()
            _log("Stimme nach Leerlauf freigegeben")


def als_mp3(samples, sr: int) -> bytes:
    import soundfile as sf
    with tempfile.TemporaryDirectory() as d:
        wav, mp3 = Path(d) / "a.wav", Path(d) / "a.mp3"
        sf.write(wav, samples, sr)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-b:a", "96k", str(mp3)],
                       check=True, timeout=300)
        return mp3.read_bytes()


def verarbeite(auftrag: dict, stimme, *, mp3=als_mp3) -> dict:
    """Einen Auftrag sprechen -> Nutzdaten fuer /api/sprache/ergebnis. Wirft nie."""
    t = time.time()
    try:
        samples, sr = stimme.sprechen(auftrag.get("text") or "")
        if len(samples) < sr:
            return {"id": auftrag["id"], "ok": False, "grund": "keine Sprache erzeugt"}
        daten = mp3(samples, sr)
        return {"id": auftrag["id"], "ok": True, "mp3_b64": base64.b64encode(daten).decode(),
                "modell": getattr(stimme, "modell", ""), "dauer_s": round(time.time() - t, 1),
                "sprache_s": round(len(samples) / sr, 1)}
    except Exception as exc:
        return {"id": auftrag["id"], "ok": False, "grund": f"{type(exc).__name__}: {str(exc)[:200]}"}


def durchlauf(bridge, stimme, *, mp3=als_mp3) -> int:
    n = 0
    while True:
        auftrag = (bridge._req("/api/sprache/naechster") or {}).get("auftrag")
        if not auftrag:
            return n
        _log(f"Sprachauftrag {auftrag['id']} ({len(auftrag.get('text') or '')} Zeichen)")
        daten = verarbeite(auftrag, stimme, mp3=mp3)
        bridge._req("/api/sprache/ergebnis", method="POST", data=daten, timeout=180)
        _log(f"{auftrag['id']} -> " + (f"fertig: {daten['sprache_s']} s Sprache in {daten['dauer_s']} s" if daten["ok"]
                                       else f"fehlgeschlagen: {daten['grund']}"))
        n += 1


def _stimme(env: dict) -> Stimme:
    return Stimme(os.environ.get("SPRACHE_MODELL") or env.get("SPRACHE_MODELL") or MODELL,
                  os.environ.get("SPRACHE_STIMME") or env.get("SPRACHE_STIMME") or STIMME,
                  threads=int(os.environ.get("SPRACHE_THREADS") or env.get("SPRACHE_THREADS") or 12))


def loop(*, intervall: float = 30.0) -> None:
    env = _lade_env()
    bridge = LunaBridge.from_env(env)
    bridge.timeout = 30
    stimme = _stimme(env)
    _log(f"Sprach-Arbeiter aktiv (Modell {stimme.modell}, Stimme {stimme.ordner}).")
    while True:
        try:
            if bridge.aktiv():
                durchlauf(bridge, stimme)
            stimme.freigeben()
        except Exception as exc:                             # nie den Worker mitreissen
            _log(f"Schleifen-Fehler: {exc}")
        time.sleep(intervall)


def main() -> None:
    ap = argparse.ArgumentParser(description="LUNA-Sprach-Arbeiter (lokale Stimme)")
    ap.add_argument("--probe", help="Text sprechen und als MP3 speichern (ohne LUNA-OS)")
    ap.add_argument("--aus", default="probe.mp3")
    a = ap.parse_args()
    if a.probe:
        t = time.time()
        samples, sr = _stimme(_lade_env()).sprechen(a.probe)
        Path(a.aus).write_bytes(als_mp3(samples, sr))
        _log(f"{len(samples) / sr:.1f} s Sprache in {time.time() - t:.0f} s -> {a.aus}")
        return
    loop()


if __name__ == "__main__":
    main()
