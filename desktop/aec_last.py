"""Last-Test Echo (L2-Nachbesserung 30.10.): LUNA spricht gestreamt ueber die Creative Stage, parallel rechnet Whisper --
zaehlt Selbst-Unterbrechungen und Echo-„Aeusserungen“ mit dem echten Ohr. Aufruf: venv\\Scripts\\python.exe aec_last.py [--ohne-zeit]"""
import importlib.util, queue, sys, threading, time
import numpy as np
s = importlib.util.spec_from_file_location("p", "probe/probe_l1.py"); p = importlib.util.module_from_spec(s); s.loader.exec_module(p)
from faster_whisper import WhisperModel
(p.HIER / "lasttest.jsonl").unlink(missing_ok=True)
prot = p.Protokoll(p.HIER / "lasttest.jsonl")
echo = p.Echo()
mund = p.Mund("pocket:german/anna", p.geraet("Creative Stage", False), prot, None, echo)
q = queue.Queue()
p.Ohr(p.geraet("RODE NT-USB", True), "lautsprecher", q, mund, echo).start()
w = WhisperModel("small", device="cpu", compute_type="int8")
stopp = threading.Event()
def last():                                    # Whisper dauernd beschaeftigt wie im Gespraech
    a = np.random.default_rng(0).standard_normal(16000 * 4).astype(np.float32) * 0.01
    while not stopp.is_set():
        list(w.transcribe(a, language="de", beam_size=1)[0])
threading.Thread(target=last, daemon=True).start()
import requests
def modell_last():                             # das grosse Sprachmodell rechnet gleichzeitig (wie im Gespraech)
    while not stopp.is_set():
        requests.post("http://localhost:11434/api/chat", timeout=120, json={
            "model": "qwen3:30b-a3b-instruct-2507-q4_K_M", "stream": False, "think": False, "keep_alive": "60m",
            "options": {"num_ctx": 4096, "num_predict": 200},
            "messages": [{"role": "user", "content": "Erzaehl eine lange Geschichte ueber Hamburg."}]})
threading.Thread(target=modell_last, daemon=True).start()
unterbrochen = []
alt = mund.unterbrechen
mund.unterbrechen = lambda t: (unterbrochen.append(time.time()), alt(t))[1]
time.sleep(2)
text = ("Hallo Nils, das ist der Last-Test für die Echo-Unterdrückung. Ich spreche jetzt mehrere Sätze hintereinander, "
        "während gleichzeitig die Spracherkennung rechnet. So sehen wir, ob ich mich selbst noch unterbreche. "
        "Drei Legged Thing schickt die Muster Ende November, und bei der Kiez Alm ist ein Angebot offen. "
        "Wenn alles klappt, höre ich jetzt nur noch dich und nicht mehr mich selbst.")
for satz in text.split(". "):
    mund.sag(satz.strip(". ") + ".")
time.sleep(1)
while mund.spricht() or not mund.saetze.empty():
    time.sleep(0.1)
time.sleep(1.5)
stopp.set()
import json
art = [json.loads(z)["art"] for z in open(p.HIER / "lasttest.jsonl", encoding="utf-8")]
print("Selbst-Unterbrechungen:", len(unterbrochen), "| geduckt:", art.count("geduckt"), "| Echo-Aeusserungen im Ohr:", q.qsize())
gesperrt = 0
while not q.empty():
    u = q.get()
    t = " ".join(x.text.strip() for x in w.transcribe(u["audio"], language="de", beam_size=1)[0]).strip()
    sperre = bool(u.get("waehrend")) and p.ist_eigenes_echo(t, mund.kuerzlich_gesagt(u["start"], u["ende"]))
    gesperrt += sperre
    print(f"   Aeusserung: {t!r} -> {'von der Echo-Sperre verworfen' if sperre else 'WUERDE ALS EINGABE ZAEHLEN'}")
