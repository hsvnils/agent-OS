"""Alle MLS-Sprecher einen Satz sprechen lassen, Grundtonhoehe schaetzen -> weibliche Stimmen finden."""
import json, wave
from pathlib import Path
import numpy as np
from piper import PiperVoice, SynthesisConfig
H = Path(__file__).resolve().parent
v = PiperVoice.load(str(H.parent / "stimmen" / "de_DE-mls-medium.onnx"))
sr = v.config.sample_rate
def f0(x):
    x = x.astype(np.float32) / 32768.0
    werte = []
    for i in range(0, len(x) - 1024, 512):
        f = x[i:i + 1024] * np.hanning(1024)
        if np.sqrt(np.mean(f ** 2)) < 0.02: continue
        ac = np.correlate(f, f, "full")[1023:]
        lo, hi = int(sr / 400), int(sr / 70)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]: werte.append(sr / k)
    return float(np.median(werte)) if werte else 0.0
erg = []
for name, sid in v.config.speaker_id_map.items() if hasattr(v.config, "speaker_id_map") else []:
    pass
ids = json.loads((H.parent / "stimmen" / "de_DE-mls-medium.onnx.json").read_text(encoding="utf-8"))["speaker_id_map"]
for name, sid in ids.items():
    a = np.concatenate([c.audio_int16_array for c in v.synthesize("Hallo Nils, ich habe das To-do für Freitag angelegt.", syn_config=SynthesisConfig(speaker_id=sid))])
    erg.append({"sprecher": sid, "name": name, "f0": round(f0(a), 1)})
erg.sort(key=lambda e: -e["f0"])
(H / "mls_tonhoehe.json").write_text(json.dumps(erg, indent=0), encoding="utf-8")
frauen = [e for e in erg if 165 <= e["f0"] <= 260]
print("weiblich (geschaetzt):", len(frauen), "von", len(erg))
satz = ("Hallo Nils, ich bin da. Ich habe das To-do angelegt: Angebot für Kiez Alm, fällig am Freitag. "
        "Soll ich dich am Donnerstag um neun Uhr daran erinnern?")
# Auswahl: gleichmaessig ueber den weiblichen Tonhoehenbereich verteilt (tief -> hoch), 12 Stimmen
auswahl = [frauen[int(i * (len(frauen) - 1) / 11)] for i in range(12)] if len(frauen) >= 12 else frauen
for n, e in enumerate(sorted(auswahl, key=lambda e: e["f0"]), 1):
    with wave.open(str(H / f"mls_frau_{n:02d}_sprecher{e['sprecher']}.wav"), "wb") as w:
        v.synthesize_wav(satz, w, syn_config=SynthesisConfig(speaker_id=e["sprecher"]))
    print(n, e)
