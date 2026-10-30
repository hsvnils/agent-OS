"""LUNA-Desktop -- Probe L1 „Ohr, Kopf, Mund“ (RECHNER_STEUERUNG_ROADMAP.md, CEO-Go 2026-10-29).

Laeuft unter **Windows** auf dem MACO470 (nicht im WSL), alles lokal und kostenlos:
- Ohr: Mikrofon (RODE NT-USB) -> Sprechpausen-Erkennung (webrtcvad) -> Whisper (faster-whisper, CPU);
- Aktivierungswort „LUNA“ (kleines Whisper-Modell), danach offene Sitzung bis „Danke LUNA“ oder 2 Min. Ruhe;
- Kopf: lokales Modell im Ollama (Standard `qwen3:30b-a3b-instruct-2507`), Antwort wird gestreamt;
- Mund: Pocket TTS `german/anna` (lokal), Satz fuer Satz -- LUNA beginnt zu sprechen, bevor die Antwort fertig ist;
- Unterbrechen: sprichst du, waehrend LUNA redet, verstummt sie und hoert zu.
- Echo (L1b, 2026-10-30): beim Lautsprecher (Creative Stage) zieht die WebRTC-Echo-Ausloeschung (Paket `livekit`,
  lokal) LUNAs eigene Stimme aus dem Mikrofon -- sie kennt jeden Block, den sie gerade abspielt. Rueckfallebene:
  was ihren eigenen gerade gesprochenen Worten gleicht, gilt nie als Eingabe.

**Kann nichts bedienen** und hat keinen Zugriff auf LUNAs Daten. Es wird **kein Ton gespeichert**; das Protokoll
`sitzung_log.jsonl` enthaelt nur Zeiten und den erkannten Text.

Start: `start_probe.bat` (Ton ueber die Creative Stage, CEO 2026-10-30) bzw. `start_probe_kopfhoerer.bat` (Kopfhoerer am NT-USB). Beenden: Fenster schliessen
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
BLOCK = 160                       # 10 ms -- Taktung der Echo-Ausloeschung
ENDE_STILLE_MS = 600              # so lange Pause = Satz zu Ende
START_FRAMES = 4                  # 120 ms Sprache = Beginn
UNTERBRECHEN_FRAMES = 8           # 240 ms Sprache waehrend LUNA redet = Unterbrechen
EINSCHWINGEN_FRAMES = 10          # die ersten 300 ms ihres Sprechens nie als Unterbrechen werten
ECHO_FENSTER_S = 8.0              # so lange zaehlen ihre gesprochenen Worte fuer die Echo-Sperre
SITZUNG_RUHE_S = 120
WECKWORT = re.compile(r"\b(luna|lunar|luner|lona|luhna)\b", re.I)
ENDE = re.compile(r"\b(danke|tschüss|tschuess|bis später|bis spaeter)\b.*\bluna\b|\bluna\b.*\b(danke|tschüss)\b", re.I)
MODELL_OPTIONEN = {"num_ctx": 4096, "temperature": 0.6}
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


class Echo:
    """WebRTC-Echo-Ausloeschung (AEC3 ueber `livekit`): Fernsignal = was der Mund abspielt, in 10-ms-Bloecken."""

    def __init__(self):
        from livekit import rtc
        self.rtc = rtc
        self.apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True, high_pass_filter=True,
                                             auto_gain_control=False)
        self.fern: queue.Queue = queue.Queue()

    def abgespielt(self, block: np.ndarray):
        self.fern.put(block.copy())

    def _rahmen(self, block: np.ndarray):
        f = self.rtc.AudioFrame.create(RATE, 1, BLOCK)
        np.frombuffer(f.data, dtype=np.int16)[:] = block
        return f

    def reinigen(self, mic: np.ndarray) -> np.ndarray:
        while True:
            try:
                self.apm.process_reverse_stream(self._rahmen(self.fern.get_nowait()))
            except queue.Empty:
                break
        f = self._rahmen(mic)
        self.apm.process_stream(f)
        return np.frombuffer(f.data, dtype=np.int16).copy()


def _woerter(text: str) -> list[str]:
    return re.findall(r"\w+", (text or "").lower())


def ist_eigenes_echo(text: str, gesagt: str) -> bool:
    """True, wenn die „Aeusserung“ fast nur aus Worten besteht, die LUNA gerade selbst gesagt hat."""
    w, g = _woerter(text), set(_woerter(gesagt))
    if not w or not g:
        return False
    return sum(x in g for x in w) / len(w) >= (1.0 if len(w) <= 3 else 0.7)


class Ohr(threading.Thread):
    """Liest das Mikrofon, schneidet Aeusserungen aus, meldet Unterbrechungen."""

    def __init__(self, geraet, modus: str, aeusserungen: queue.Queue, mund, echo: Echo | None = None):
        super().__init__(daemon=True)
        self.geraet, self.modus, self.q, self.mund, self.echo = geraet, modus, aeusserungen, mund, echo
        self.vad = webrtcvad.Vad(3 if modus == "lautsprecher" else 2)
        self.pegel = deque(maxlen=34)          # ~1 s Mikrofonpegel waehrend LUNA spricht (Echo-Schaetzung)
        self.grundrauschen = 200.0

    def run(self):
        puffer, stimme, stille, laeuft, start_t, unterbrechen, waehrend = [], 0, 0, False, 0.0, 0, False
        vorlauf = deque(maxlen=10)
        with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK, device=self.geraet) as st:
            while True:
                teile = []
                for _ in range(FRAME // BLOCK):
                    daten, _ = st.read(BLOCK)
                    b = daten[:, 0].copy()
                    teile.append(self.echo.reinigen(b) if self.echo else b)
                f = np.concatenate(teile)
                rms = float(np.sqrt(np.mean(f.astype(np.float32) ** 2)))
                sprache = self.vad.is_speech(f.tobytes(), RATE)
                if self.mund.spricht():
                    self.pegel.append(rms)
                    echo = (sum(self.pegel) / len(self.pegel)) if self.pegel else 0.0
                    laut_genug = self.modus != "lautsprecher" or rms > max(echo * 2.5, self.grundrauschen * 6)
                    eingeschwungen = len(self.pegel) >= EINSCHWINGEN_FRAMES
                    unterbrechen = unterbrechen + 1 if (sprache and laut_genug and eingeschwungen) else 0
                    if unterbrechen >= UNTERBRECHEN_FRAMES:
                        self.mund.unterbrechen(jetzt() - UNTERBRECHEN_FRAMES * 0.03)
                        unterbrechen, laeuft, puffer, stimme, stille = 0, True, list(vorlauf), START_FRAMES, 0
                        start_t, waehrend = jetzt(), True
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
                        waehrend = self.mund.spricht() or jetzt() - self.mund.zuletzt_ton < 1.0
                    continue
                puffer.append(f)
                stille = 0 if sprache else stille + 1
                if stille * 30 >= ENDE_STILLE_MS or len(puffer) > 30 * 1000 // 30:
                    audio = np.concatenate(puffer).astype(np.float32) / 32768.0
                    self.q.put({"audio": audio, "start": start_t, "ende": jetzt() - stille * 0.03, "waehrend": waehrend})
                    laeuft, puffer, stimme, stille = False, [], 0, 0
                    vorlauf.clear()


class Mund:
    """Spricht Saetze nacheinander (Pocket TTS oder Piper) ueber einen eigenen 16-kHz-Strom, jederzeit unterbrechbar."""

    def __init__(self, stimme: Path | str, geraet, protokoll: Protokoll, sprecher: int | None = None,
                 echo: Echo | None = None):
        self.pocket = None
        if str(stimme).startswith("pocket:"):            # Pocket TTS (Kyutai, Deutsch): eingebaute Stimme oder eigene WAV
            from pocket_tts import TTSModel
            sprache, _, name = str(stimme)[7:].partition("/")
            self.pocket = TTSModel.load_model(language=sprache or "german")
            self.pocket_stimme = self.pocket.get_state_for_audio_prompt(name or "anna")
            self.rate = self.pocket.sample_rate
        else:
            from piper import PiperVoice, SynthesisConfig
            self.voice = PiperVoice.load(str(stimme))
            self.syn = SynthesisConfig(speaker_id=sprecher) if sprecher is not None else None
            self.rate = self.voice.config.sample_rate
        self.geraet, self.prot, self.echo = geraet, protokoll, echo
        self.saetze: queue.Queue = queue.Queue()
        self._ton = np.zeros(0, dtype=np.int16)        # noch abzuspielen (16 kHz)
        self._lock = threading.Lock()
        self.zuletzt_ton = 0.0
        self.gesagt: deque = deque(maxlen=20)          # (Zeit, Satz) fuer die Echo-Sperre
        self.strom = sd.OutputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK, device=geraet,
                                     callback=self._ausgabe)
        self.strom.start()
        self._spricht = threading.Event()
        self.abbruch = threading.Event()
        self.unterbrochen = threading.Event()   # gilt fuer die ganze laufende Antwort (Kopf hoert auf zu streamen)
        self.erster_ton: float | None = None
        threading.Thread(target=self._lauf, daemon=True).start()

    def spricht(self) -> bool:
        return self._spricht.is_set()

    def _ausgabe(self, out, frames, _zeit, _status):
        """Ton-Ausgabe im 10-ms-Takt; jeder Block geht als Fernsignal an die Echo-Ausloeschung (auch Stille)."""
        with self._lock:
            n = min(frames, len(self._ton))
            block = np.zeros(frames, dtype=np.int16)
            block[:n] = self._ton[:n]
            self._ton = self._ton[n:]
        if n:
            self.zuletzt_ton = jetzt()
        out[:, 0] = block
        if self.echo:
            self.echo.abgespielt(block)

    def kuerzlich_gesagt(self) -> str:
        grenze = jetzt() - ECHO_FENSTER_S
        return " ".join(s for t, s in self.gesagt if t >= grenze)

    def sag(self, text: str):
        self.saetze.put(text)

    def unterbrechen(self, sprachbeginn: float):
        if not self._spricht.is_set():
            return
        self.unterbrochen.set()
        self.abbruch.set()
        while not self.saetze.empty():
            self.saetze.get_nowait()
        with self._lock:
            self._ton = np.zeros(0, dtype=np.int16)
        self.prot.schreibe(art="unterbrochen", s=round(jetzt() - sprachbeginn, 3))
        print("   ✋ unterbrochen")

    def _lauf(self):
        while True:
            text = self.saetze.get()
            if text is None:
                continue
            self.abbruch.clear()
            if self.pocket is not None:
                a = self.pocket.generate_audio(self.pocket_stimme, text).flatten().numpy()
            else:
                a = np.concatenate([c.audio_int16_array for c in self.voice.synthesize(text, syn_config=self.syn)]
                                   ).astype(np.float32) / 32768.0
            if self.rate != RATE:                      # alles auf 16 kHz (Takt der Echo-Ausloeschung)
                from math import gcd
                from scipy.signal import resample_poly
                g = gcd(RATE, self.rate)
                a = resample_poly(a, RATE // g, self.rate // g)
            ton = (np.clip(a, -1, 1) * 32767).astype(np.int16)
            if self.abbruch.is_set():
                continue
            self._spricht.set()
            self.gesagt.append((jetzt(), text))
            with self._lock:
                self._ton = np.concatenate([self._ton, ton])
            if self.erster_ton is None:
                self.erster_ton = jetzt()
            while not self.abbruch.is_set():
                with self._lock:
                    rest = len(self._ton)
                if not rest:
                    break
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
            "options": MODELL_OPTIONEN, "messages": verlauf}) as r:
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
    ap.add_argument("--modell", default="qwen3:30b-a3b-instruct-2507-q4_K_M")
    ap.add_argument("--stimme", default="pocket:german/anna",
                    help="pocket:<german|german_24l>/<stimme> oder Piper-Name, z. B. de_DE-thorsten-high")
    ap.add_argument("--modus", choices=("kopfhoerer", "lautsprecher"), default="lautsprecher")
    ap.add_argument("--mikro", default="RODE NT-USB")
    ap.add_argument("--ausgabe", default="")
    ap.add_argument("--sprecher", type=int, default=None, help="bei de_DE-mls-medium: Nummer aus der Hoerprobe")
    ap.add_argument("--ohr", default="small", help="Whisper-Modell in der Sitzung: small | medium | turbo")
    ap.add_argument("--ohne-echo", action="store_true", help="Echo-Ausloeschung aus (nur zum Vergleich)")
    a = ap.parse_args()
    aus_name = a.ausgabe or ("RODE NT-USB" if a.modus == "kopfhoerer" else "Creative Stage")
    mic, out = geraet(a.mikro, True), geraet(aus_name, False)
    prot = Protokoll(HIER / "sitzung_log.jsonl")
    echo = None if a.ohne_echo else Echo()
    print(f"LUNA-Probe L1 -- Modell {a.modell}, Stimme {a.stimme}, Modus {a.modus}, "
          f"Echo-Ausloeschung {'aus' if echo is None else 'an'}")
    print(f"Mikrofon: {sd.query_devices(mic)['name'] if mic is not None else 'Standard'} | "
          f"Ausgabe: {sd.query_devices(out)['name'] if out is not None else 'Standard'}")
    print("Lade Whisper-Modelle und Stimme ...")
    from faster_whisper import WhisperModel
    klein = WhisperModel("small", device="cpu", compute_type="int8")
    gross = klein if a.ohr == "small" else WhisperModel(
        "mobiuslabsgmbh/faster-whisper-large-v3-turbo" if a.ohr == "turbo" else a.ohr, device="cpu", compute_type="int8")
    stimmen = HIER.parent / "stimmen"
    mund = Mund(a.stimme if a.stimme.startswith("pocket:") else stimmen / f"{a.stimme}.onnx", out, prot, a.sprecher,
                echo)
    print("Lade das Sprachmodell (beim ersten Start bis zu 30 s) ...")
    requests.post("http://localhost:11434/api/chat", timeout=300, json={          # gleiche Optionen wie kopf(),
        "model": a.modell, "stream": False, "think": False, "keep_alive": "60m",  # sonst laedt Ollama neu (Test 1: 27 s)
        "options": {**MODELL_OPTIONEN, "num_predict": 1}, "messages": [{"role": "user", "content": "Hallo"}]})
    q: queue.Queue = queue.Queue()
    Ohr(mic, a.modus, q, mund, echo).start()
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
        if u.get("waehrend") and ist_eigenes_echo(text, mund.kuerzlich_gesagt()):
            prot.schreibe(art="echo_verworfen", text=text)
            print(f"   (eigenes Echo verworfen: {text})")
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
                      echo_an=echo is not None, warteschlange=q.qsize(),
                      dauer_rede_s=round(u["ende"] - u["start"], 2), stt_s=round(t_text - t0, 2),
                      erstes_token_s=round((erst or t_text) - t_text, 2),
                      satzende_bis_erster_ton_s=round((mund.erster_ton or jetzt()) - u["ende"], 2))
        print(f"🌙 LUNA: {antwort}")
        if mund.erster_ton:
            print(f"   ⏱ {mund.erster_ton - u['ende']:.1f} s vom Ende deines Satzes bis zu LUNAs erstem Wort")


if __name__ == "__main__":
    main()
