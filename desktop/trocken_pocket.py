import sys, time
from pathlib import Path
import sounddevice as sd
sys.path.insert(0, str(Path(__file__).parent))
import probe_l1 as p
sd.play = lambda *a, **k: None
class _S: active = False
sd.get_stream = lambda: _S()
mund = p.Mund("pocket:german/anna", None, p.Protokoll(Path(__file__).parent / "trocken_log.jsonl"))
for frage in ("Hallo LUNA, wie geht es dir?", "Erklaer mir kurz, was ein Tausender-Kontakt-Preis ist."):
    mund.erster_ton = None; mund.unterbrochen.clear(); t = p.jetzt()
    v = [{"role": "system", "content": p.SYSTEM.format(datum="Donnerstag")}, {"role": "user", "content": frage}]
    ant, erst = p.kopf("qwen3:30b-a3b-instruct-2507-q4_K_M", v, mund, mund.unterbrochen)
    while mund.erster_ton is None: time.sleep(0.01)
    print(f"Text fertig -> erster Ton {mund.erster_ton - t:.2f} s | {ant[:80]}")
