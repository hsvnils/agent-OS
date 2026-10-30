"""Trockenlauf ohne Ton: erkannter Text -> erster Ton (Kopf + Pocket-Stimme), Ausgabe wird nur im Echtzeit-Takt geleert."""
import sys, threading, time
from pathlib import Path
import numpy as np
import sounddevice as sd
sys.path.insert(0, str(Path(__file__).parent))
import probe_l1 as p


class _StummerStrom:                       # ersetzt sd.OutputStream: ruft den Callback im 10-ms-Takt, spielt nichts ab
    def __init__(self, *, callback, blocksize, **_):
        self.cb, self.n = callback, blocksize

    def start(self):
        def lauf():
            out = np.zeros((self.n, 1), dtype=np.int16)
            while True:
                self.cb(out, self.n, None, None)
                time.sleep(self.n / p.RATE)
        threading.Thread(target=lauf, daemon=True).start()


sd.OutputStream = _StummerStrom
mund = p.Mund("pocket:german/anna", None, p.Protokoll(Path(__file__).parent / "trocken_log.jsonl"))
for frage in ("Wer ist 3 Legged Thing?", "Was ist mit der Kiez Alm?", "Erklaer mir kurz, was ein Tausender-Kontakt-Preis ist."):
    mund.erster_ton = None; mund.unterbrochen.clear(); t = p.jetzt()
    v = [{"role": "system", "content": p.SYSTEM.format(datum="Freitag")}, {"role": "user", "content": frage}]
    ant, erst = p.kopf("qwen3:30b-a3b-instruct-2507-q4_K_M", v, mund, mund.unterbrochen)
    while mund.erster_ton is None: time.sleep(0.01)
    print(f"Text fertig -> erstes Token {erst - t:.2f} s, erster Ton {mund.erster_ton - t:.2f} s | {ant[:110]}")
    while mund.spricht() or not mund.saetze.empty(): time.sleep(0.05)
