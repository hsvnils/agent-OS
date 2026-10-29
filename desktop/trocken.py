"""Trockenlauf: Ohr (Datei statt Mikro), Kopf, Mund ohne Abspielen -- misst die Kette."""
import sys, time, json
from pathlib import Path
import soundfile as sf, sounddevice as sd
sys.path.insert(0, str(Path(__file__).parent))
import probe_l1 as p
sd.play = lambda *a, **k: None                      # nichts abspielen
class _S:  active = False
sd.get_stream = lambda: _S()
from faster_whisper import WhisperModel
ohr = sys.argv[2] if len(sys.argv) > 2 else "small"
gross = WhisperModel({"turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo"}.get(ohr, ohr), device="cpu", compute_type="int8")
audio, _ = sf.read(Path(__file__).parent / "satz_luna.wav", dtype="float32")
audio = audio[: 16000 * 4]                          # 4 s Satz
prot = p.Protokoll(Path(__file__).parent / "trocken_log.jsonl")
modell = sys.argv[1] if len(sys.argv) > 1 else "qwen3:14b"
for stimme in ("de_DE-thorsten-high", "de_DE-kerstin-low"):
    mund = p.Mund(Path(__file__).parent.parent / "stimmen" / f"{stimme}.onnx", None, prot)
    for frage in ("Was kannst du schon alles?", "Erklaer mir kurz, was ein Tausender-Kontakt-Preis ist."):
        t_ende = p.jetzt()
        segs, _ = gross.transcribe(audio, language="de", beam_size=1, vad_filter=False); " ".join(s.text for s in segs)
        t_text = p.jetzt()
        mund.erster_ton = None; mund.unterbrochen.clear()
        verlauf = [{"role": "system", "content": p.SYSTEM.format(datum="Donnerstag, 29.10.2026")}, {"role": "user", "content": frage}]
        antwort, erst = p.kopf(modell, verlauf, mund, mund.unterbrochen)
        while mund.erster_ton is None: time.sleep(0.01)
        print(json.dumps({"modell": modell, "ohr": ohr, "erste_phrase": "", "stimme": stimme, "stt_s": round(t_text - t_ende, 2),
                          "erstes_token_s": round(erst - t_text, 2), "satzende_bis_erster_ton_s": round(mund.erster_ton - t_ende, 2),
                          "antwort": antwort[:160]}, ensure_ascii=False))
