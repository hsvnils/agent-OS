"""L1-Messung der Einzelteile (Ohr, Kopf, Mund) auf dem MACO470 -- ohne Mikrofon, ohne Bedienen."""
import json, sys, time, wave, statistics
from pathlib import Path
import numpy as np, requests, soundfile as sf

H = Path(__file__).resolve().parent
erg = {}

# --- Ohr: Whisper (lokal, CPU) ---
from faster_whisper import WhisperModel
audio, sr = sf.read(H / "satz_luna.wav", dtype="float32")
for name in ("small", "mobiuslabsgmbh/faster-whisper-large-v3-turbo"):
    t = time.time(); m = WhisperModel(name, device="cpu", compute_type="int8"); lade = time.time() - t
    zeiten = []
    for _ in range(3):
        t = time.time(); seg, _i = m.transcribe(audio, language="de", beam_size=1, vad_filter=False)
        text = " ".join(s.text.strip() for s in seg); zeiten.append(time.time() - t)
    erg[f"ohr:{name.split('/')[-1]}"] = {"laden_s": round(lade, 1), "s_fuer_9s_audio": round(min(zeiten), 2), "text": text}

# --- Kopf: lokales Modell, Zeit bis zum ersten Wort (Streaming) ---
def erster_token(modell, prompt):
    t = time.time(); erst = None; n = 0
    with requests.post("http://localhost:11434/api/chat", stream=True, timeout=300, json={
            "model": modell, "stream": True, "think": False, "keep_alive": "30m",
            "messages": [{"role": "system", "content": "Du bist LUNA, antworte kurz auf Deutsch."},
                         {"role": "user", "content": prompt}]}) as r:
        for z in r.iter_lines():
            if not z: continue
            d = json.loads(z); c = d.get("message", {}).get("content", "")
            if c and erst is None: erst = time.time() - t
            n += len(c)
            if d.get("done"): ges = time.time() - t; ev = d.get("eval_count", 0); evd = d.get("eval_duration", 1) / 1e9
    return {"erstes_wort_s": round(erst or -1, 2), "gesamt_s": round(ges, 2), "token_pro_s": round(ev / evd, 1)}
for modell in ("qwen3:30b-a3b", "qwen3:14b"):
    erster_token(modell, "Hallo")                              # warm laden
    erg[f"kopf:{modell}"] = erster_token(modell, "Leg mir ein To-do an: Angebot Kiez Alm bis Freitag. Bestaetige in einem Satz.")

# --- Mund: Piper-Stimmen, Echtzeitfaktor ---
from piper import PiperVoice
satz = "Alles klar, ich lege das To-do an: Angebot für Kiez Alm, fällig am Freitag. Soll ich dich am Donnerstag daran erinnern?"
for onnx in sorted((H.parent / "stimmen").glob("*.onnx")):
    v = PiperVoice.load(str(onnx)); t = time.time()
    with wave.open(str(H / f"mund_{onnx.stem}.wav"), "wb") as w: v.synthesize_wav(satz, w)
    dauer = sf.info(str(H / f"mund_{onnx.stem}.wav")).duration
    erg[f"mund:{onnx.stem}"] = {"s_rechnen": round(time.time() - t, 2), "s_sprache": round(dauer, 2)}
print(json.dumps(erg, ensure_ascii=False, indent=1))
(H / "messung.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
