"""Raum-Test L1b: ein Satz ueber die Creative Stage, Mikrofon mit/ohne Echo-Ausloeschung -- misst den Echo-Rest."""
import importlib.util, threading, time, numpy as np, sounddevice as sd
s = importlib.util.spec_from_file_location("p", "probe/probe_l1.py"); p = importlib.util.module_from_spec(s); s.loader.exec_module(p)
echo = p.Echo()
mund = p.Mund("pocket:german/anna", p.geraet("Creative Stage", False), p.Protokoll(p.HIER / "raumtest.jsonl"), None, echo)
roh, sauber = [], []
def ohr():
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=160, device=p.geraet("RODE NT-USB", True)) as st:
        t = time.time()
        while time.time() - t < 9:
            b = st.read(160)[0][:, 0].copy(); roh.append(b); sauber.append(echo.reinigen(b))
th = threading.Thread(target=ohr); th.start(); time.sleep(1.0)
mund.sag("Hallo Nils, das ist ein kurzer Echo-Test. Ich spreche jetzt ein paar Sätze über die Creative Stage, damit ich messen kann, wie viel von meiner Stimme im Mikrofon ankommt.")
th.join()
rms = lambda x: float(np.sqrt(np.mean(np.concatenate(x).astype(np.float32) ** 2)))
r, c = roh[100:], sauber[100:]        # ohne die erste Sekunde (Stille)
lang = [i for i in range(len(r)) if np.sqrt(np.mean(r[i].astype(np.float32)**2)) > 300]
print("Bloecke mit Echo:", len(lang), "| Echo roh", round(rms([r[i] for i in lang]) if lang else 0),
      "| nach Ausloeschung", round(rms([c[i] for i in lang]) if lang else 0),
      "| zweite Haelfte nach Ausloeschung", round(rms([c[i] for i in lang[len(lang)//2:]]) if lang else 0))
v = p.webrtcvad.Vad(3); f = np.concatenate(c); fr = [f[i:i+480] for i in range(0, len(f)-480, 480)]
print("VAD 'Sprache' in Rahmen nach Ausloeschung:", sum(v.is_speech(x.tobytes(), 16000) for x in fr), "von", len(fr))
f = np.concatenate(r); fr = [f[i:i+480] for i in range(0, len(f)-480, 480)]
print("VAD 'Sprache' in Rahmen roh:", sum(v.is_speech(x.tobytes(), 16000) for x in fr), "von", len(fr))
