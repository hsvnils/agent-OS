import wave
from pathlib import Path
from piper import PiperVoice
H = Path(__file__).resolve().parent
satz = ("Hallo Nils, ich bin da. Ich habe das To-do angelegt: Angebot für Kiez Alm, fällig am Freitag. "
        "Soll ich dich am Donnerstag um neun Uhr daran erinnern?")
for onnx in sorted((H.parent / "stimmen").glob("*.onnx")):
    v = PiperVoice.load(str(onnx))
    with wave.open(str(H / f"hoerprobe_{onnx.stem}.wav"), "wb") as w:
        v.synthesize_wav(satz, w)
    print(onnx.stem)
