"""LUNA-Desktop -- Probe L1 „Ohr, Kopf, Mund“ (RECHNER_STEUERUNG_ROADMAP.md, CEO-Go 2026-10-29).

Laeuft unter **Windows** auf dem MACO470 (nicht im WSL), alles lokal und kostenlos:
- Ohr: Mikrofon (RODE NT-USB) -> Sprechpausen-Erkennung (webrtcvad) -> Whisper (faster-whisper, CPU);
- Aktivierungswort „LUNA“ (kleines Whisper-Modell), danach offene Sitzung bis „Danke LUNA“ oder 2 Min. Ruhe;
- Kopf: lokales Modell im Ollama (Standard `qwen3:14b`), Antwort wird gestreamt;
- Mund: Piper-Stimme (lokal), Satz fuer Satz -- LUNA beginnt zu sprechen, bevor die Antwort fertig ist;
- Unterbrechen: sprichst du, waehrend LUNA redet, verstummt sie und hoert zu.

**Kann nichts bedienen** und hat keinen Zugriff auf LUNAs Daten. Es wird **kein Ton gespeichert**; das Protokoll
`sitzung_log.jsonl` enthaelt nur Zeiten und den erkannten Text.

Start: `start_probe.bat` (Kopfhoerer am NT-USB) bzw. `start_probe_lautsprecher.bat`. Beenden: Fenster schliessen
oder Strg+C.
"""
from __future__ import annotations

import argparse
import json
import queue
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd
import webrtcvad

HIER = Path(__file__).resolve().parent
RATE = 16000
FRAME = 480                       # 30 ms bei 16 kHz
ENDE_STILLE_MS = 600              # so lange Pause = Satz zu Ende
START_FRAMES = 4                  # 120 ms Sprache = Beginn
UNTERBRECHEN_FRAMES = 8           # 240 ms Sprache waehrend LUNA redet = Unterbrechen
SITZUNG_RUHE_S = 120
WECKWORT = re.compile(r"\b(luna|lunar|luner|lona|luhna)\b", re.I)
ENDE = re.compile(r"\b(danke|tschüss|tschuess|bis später|bis spaeter)\b.*\bluna\b|\bluna\b.*\b(danke|tschüss)\b", re.I)
SATZ = re.compile(r"(.+?[.!?…])(\s+|$)", re.S)

SYSTEM = ("Du bist LUNA, die persoenliche Assistentin von Nils (Firma Hanserautisch, Hamburg). Du sprichst mit ihm "
          "per Stimme am Rechner. Antworte auf Deutsch, natuerlich und kurz: meist ein bis zwei Saetze, keine Listen, "
          "keine Sonderzeichen, kein Markdown. Duze ihn. Das ist eine Probe: du kannst noch nichts am Rechner bedienen "
          "und nicht auf Kunden oder Termine zugreifen -- sag das ehrlich, wenn er danach fragt. Heute ist {datum}.")


def jetzt() -> float:
    return time.perf_counter()


class Protokoll:
    def __init__(self, pfad: Path):
        self.pfad = pfad

    def schreibe(self, **d):
        d["ts"] = datetime.now().isoformat(timespec="seconds")
        with self.pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


class Ohr(threading.Thread):
    """Liest das Mikrofon, schneidet Aeusserungen aus, meldet Unterbrechungen."""

    def __init__(self, geraet, modus: str, aeusserungen: queue.Queue, mund):
        super().__init__(daemon=True)
        self.geraet, self.modus, self.q, self.mund = geraet, modus, aeusserungen, mund
        self.vad = webrtcvad.Vad(3 if modus == "lautsprecher" else 2)
        self.pegel = deque(maxlen=34)          # ~1 s Mikrofonpegel waehrend LUNA spricht (Echo-Schaetzung)
        self.grundrauschen = 200.0

    def run(self):
        puffer, stimme, stille, laeuft, start_t, unterbrechen = [], 0, 0, False, 0.0, 0
        vorlauf = deque(maxlen=10)
        with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME, device=self.geraet) as st:
            while True:
                daten, _ = st.read(FRAME)
                f = daten[:, 0].copy()
                rms = float(np.sqrt(np.mean(f.astype(np.float32) ** 2)))
                sprache = self.vad.is_speech(f.tobytes(), RATE)
                if self.mund.spricht():
                    self.pegel.append(rms)
                    echo = (sum(self.pegel) / len(self.pegel)) if self.pegel else 0.0
                    laut_genug = self.modus != "lautsprecher" or rms > max(echo * 2.5, self.grundrauschen * 6)
                    unterbrechen = unterbrechen + 1 if (sprache and laut_genug) else 0
                    if unterbrechen >= UNTERBRECHEN_FRAMES:
                        self.mund.unterbrechen(jetzt() - UNTERBRECHEN_FRAMES * 0.03)
                        unterbrechen, laeuft, puffer, stimme, stille = 0, True, list(vorlauf), START_FRAMES, 0
                        start_t = jetzt()
                    vorlauf.append(f)
                    if not laeuft:
                        continue
                else:
                    self.pegel.clear()
                    if not sprache:
                        self.grundrauschen = 0.98 * self.grundrauschen + 0.02 * rms
                if not laeuft:
                    vorlauf.append(f)
                    stimme = stimme + 1 if sprache else 0
                    if stimme >= START_FRAMES:
                        laeuft, puffer, stille, start_t = True, list(vorlauf), 0, jetzt()
                    continue
                puffer.append(f)
                stille = 0 if sprache else stille + 1
                if stille * 30 >= ENDE_STILLE_MS or len(puffer) > 30 * 1000 // 30:
                    audio = np.concatenate(puffer).astype(np.float32) / 32768.0
                    self.q.put({"audio": audio, "start": start_t, "ende": jetzt() - stille * 0.03})
                    laeuft, puffer, stimme, stille = False, [], 0, 0
                    vorlauf.clear()


class Mund:
    """Spricht Saetze nacheinander (Piper), kann jederzeit unterbrochen werden."""

    def __init__(self, stimme: Path, geraet, protokoll: Protokoll, sprecher: int | None = None):
        from piper import PiperVoice, SynthesisConfig
        self.voice = PiperVoice.load(str(stimme))
        self.syn = SynthesisConfig(speaker_id=sprecher) if sprecher is not None else None
        self.rate = self.voice.config.sample_rate
        self.geraet, self.prot = geraet, protokoll
        self.saetze: queue.Queue = queue.Queue()
        self._spricht = threading.Event()
        self.abbruch = threading.Event()
        self.unterbrochen = threading.Event()   # gilt fuer die ganze laufende Antwort (Kopf hoert auf zu streamen)
        self.erster_ton: float | None = None
        threading.Thread(target=self._lauf, daemon=True).start()

    def spricht(self) -> bool:
        return self._spricht.is_set()

    def sag(self, text: str):
        self.saetze.put(text)

    def unterbrechen(self, sprachbeginn: float):
        if not self._spricht.is_set():
            return
        self.unterbrochen.set()
        self.abbruch.set()
        sd.stop()
        while not self.saetze.empty():
            self.saetze.get_nowait()
        self.prot.schreibe(art="unterbrochen", s=round(jetzt() - sprachbeginn, 3))
        print("   ✋ unterbrochen")

    def _lauf(self):
        while True:
            text = self.saetze.get()
            if text is None:
                continue
            self.abbruch.clear()
            ton = np.concatenate([c.audio_int16_array for c in self.voice.synthesize(text, syn_config=self.syn)])
            if self.abbruch.is_set():
                continue
            self._spricht.set()
            if self.erster_ton is None:
                self.erster_ton = jetzt()
            sd.play(ton, self.rate, device=self.geraet)
            while sd.get_stream().active and not self.abbruch.is_set():
                time.sleep(0.02)
            if self.saetze.empty():
                time.sleep(0.15)                   # kurzes Nachklingen, bevor das Ohr wieder normal hoert
                if self.saetze.empty():
                    self._spricht.clear()


def _erste_phrase(text: str) -> int:
    """Ende der ersten sprechbaren Teil-Phrase (Komma/Doppelpunkt nach mind. 2 Woertern oder 7 Woerter), sonst 0."""
    for m in re.finditer(r"[,:;–—]\s", text):
        if len(text[:m.start()].split()) >= 2:
            return m.end()
    w = list(re.finditer(r"\S+\s", text))
    return w[6].end() if len(w) >= 8 else 0


def kopf(modell: str, verlauf: list[dict], mund: Mund, stopp: threading.Event) -> tuple[str, float | None]:
    """Streamt die Antwort und gibt Satz fuer Satz an den Mund. -> (Antwort, Zeit erstes Token)."""
    erst, rest, ganz, gesagt = None, "", "", False
    with requests.post("http://localhost:11434/api/chat", stream=True, timeout=120, json={
            "model": modell, "stream": True, "think": False, "keep_alive": "60m",
            "options": {"num_ctx": 4096, "temperature": 0.6}, "messages": verlauf}) as r:
        for z in r.iter_lines():
            if stopp.is_set():
                break
            if not z:
                continue
            d = json.loads(z)
            c = d.get("message", {}).get("content", "")
            if c:
                if erst is None:
                    erst = jetzt()
                rest += c
                ganz += c
                while True:
                    if (m := SATZ.match(rest)):
                        satz, rest = m.group(1), rest[m.end():]
                    elif not gesagt and (k := _erste_phrase(rest)):
                        satz, rest = rest[:k], rest[k:]      # erste Teil-Phrase sofort sprechen (Antwortbeginn)
                    elif len(rest) > 80 and "," in rest[40:]:
                        k = rest.index(",", 40) + 1
                        satz, rest = rest[:k], rest[k:]
                    else:
                        break
                    if satz.strip():
                        mund.sag(satz.strip())
                        gesagt = True
            if d.get("done"):
                break
    if rest.strip() and not stopp.is_set():
        mund.sag(rest.strip())
    return ganz.strip(), erst


def geraet(name: str, eingang: bool):
    for i, d in enumerate(sd.query_devices()):
        if name.lower() in d["name"].lower() and sd.query_hostapis(d["hostapi"])["name"] == "MME" \
                and (d["max_input_channels"] if eingang else d["max_output_channels"]) > 0:
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modell", default="qwen3:14b")
    ap.add_argument("--stimme", default="de_DE-thorsten-high")
    ap.add_argument("--modus", choices=("kopfhoerer", "lautsprecher"), default="kopfhoerer")
    ap.add_argument("--mikro", default="RODE NT-USB")
    ap.add_argument("--ausgabe", default="")
    ap.add_argument("--sprecher", type=int, default=None, help="bei de_DE-mls-medium: Nummer aus der Hoerprobe")
    ap.add_argument("--ohr", default="small", help="Whisper-Modell in der Sitzung: small | medium | turbo")
    a = ap.parse_args()
    aus_name = a.ausgabe or ("RODE NT-USB" if a.modus == "kopfhoerer" else "Creative")
    mic, out = geraet(a.mikro, True), geraet(aus_name, False)
    prot = Protokoll(HIER / "sitzung_log.jsonl")
    print(f"LUNA-Probe L1 -- Modell {a.modell}, Stimme {a.stimme}, Modus {a.modus}")
    print(f"Mikrofon: {sd.query_devices(mic)['name'] if mic is not None else 'Standard'} | "
          f"Ausgabe: {sd.query_devices(out)['name'] if out is not None else 'Standard'}")
    print("Lade Whisper-Modelle und Stimme ...")
    from faster_whisper import WhisperModel
    klein = WhisperModel("small", device="cpu", compute_type="int8")
    gross = klein if a.ohr == "small" else WhisperModel(
        "mobiuslabsgmbh/faster-whisper-large-v3-turbo" if a.ohr == "turbo" else a.ohr, device="cpu", compute_type="int8")
    stimmen = HIER.parent / "stimmen"
    mund = Mund(stimmen / f"{a.stimme}.onnx", out, prot, a.sprecher)
    requests.post("http://localhost:11434/api/chat", timeout=300, json={
        "model": a.modell, "stream": False, "think": False, "keep_alive": "60m",
        "messages": [{"role": "user", "content": "Hallo"}]})          # Modell vorab in den Speicher laden
    q: queue.Queue = queue.Queue()
    Ohr(mic, a.modus, q, mund).start()
    datum = datetime.now().strftime("%A, %d.%m.%Y")
    verlauf = [{"role": "system", "content": SYSTEM.format(datum=datum)}]
    sitzung_bis = 0.0
    print("\nBereit. Sag „LUNA, …“ – zum Beenden der Sitzung „Danke LUNA“.\n")
    while True:
        u = q.get()
        in_sitzung = jetzt() < sitzung_bis
        t0 = jetzt()
        segs, _ = (gross if in_sitzung else klein).transcribe(u["audio"], language="de", beam_size=1,
                                                               vad_filter=False, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        t_text = jetzt()
        if not text:
            continue
        if not in_sitzung:
            m = WECKWORT.search(text)
            if not m:
                print(f"   (ignoriert: {text})")
                continue
            sitzung_bis = jetzt() + SITZUNG_RUHE_S
            nach = text[m.end():].strip(" ,.!?")
            if len(nach) < 3:                                         # nur „LUNA?“ -> kurz melden
                mund.erster_ton = None
                mund.sag("Ja?")
                prot.schreibe(art="geweckt", text=text, stt_s=round(t_text - t0, 2))
                print(f"🟢 Sitzung offen  ({text})")
                continue
            if len(text.split()) > 3:                                 # Weckwort mit Satz -> Satz genauer erkennen
                segs, _ = gross.transcribe(u["audio"], language="de", beam_size=1, vad_filter=False)
                text = " ".join(s.text.strip() for s in segs).strip()
                t_text = jetzt()
            print("🟢 Sitzung offen")
        sitzung_bis = jetzt() + SITZUNG_RUHE_S
        print(f"🗣  Du: {text}")
        if ENDE.search(text):
            mund.sag("Gern. Bis gleich.")
            sitzung_bis = 0.0
            prot.schreibe(art="ende", text=text)
            print("⚪ Sitzung beendet")
            continue
        verlauf.append({"role": "user", "content": text})
        mund.erster_ton = None
        mund.unterbrochen.clear()
        antwort, erst = kopf(a.modell, verlauf, mund, mund.unterbrochen)
        if mund.unterbrochen.is_set():
            antwort += " [unterbrochen]"
        verlauf.append({"role": "assistant", "content": antwort})
        verlauf[1:] = verlauf[-12:] if len(verlauf) > 13 else verlauf[1:]
        for _ in range(200):                                          # bis zu 4 s auf den ersten Ton warten
            if mund.erster_ton:
                break
            time.sleep(0.02)
        prot.schreibe(art="wechsel", du=text, luna=antwort, modell=a.modell, stimme=a.stimme, modus=a.modus,
                      dauer_rede_s=round(u["ende"] - u["start"], 2), stt_s=round(t_text - t0, 2),
                      erstes_token_s=round((erst or t_text) - t_text, 2),
                      satzende_bis_erster_ton_s=round((mund.erster_ton or jetzt()) - u["ende"], 2))
        print(f"🌙 LUNA: {antwort}")
        if mund.erster_ton:
            print(f"   ⏱ {mund.erster_ton - u['ende']:.1f} s vom Ende deines Satzes bis zu LUNAs erstem Wort")


if __name__ == "__main__":
    main()
