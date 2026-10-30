import time, json
from pathlib import Path
import numpy as np, scipy.io.wavfile as wf, torch
from pocket_tts import TTSModel
H = Path(__file__).resolve().parent
satz = ("Hallo Nils, ich bin da. Ich habe das To-do angelegt: Angebot für Kiez Alm, fällig am Freitag. "
        "Soll ich dich am Donnerstag um neun Uhr daran erinnern?")
erg = {}
for sprache in ("german", "german_24l"):
    t = time.time(); m = TTSModel.load_model(language=sprache); lade = time.time() - t
    for ref in [type("R", (), {"stem": n})() for n in ("anna", "vera", "eve", "alba", "jane", "mary", "estelle", "lola", "cosette", "fantine")]:
        st = m.get_state_for_audio_prompt(ref.stem)
        t = time.time(); erst = None; teile = []
        for chunk in m.generate_audio_stream(st, satz):
            if erst is None: erst = time.time() - t
            teile.append(chunk)
        dauer_r = time.time() - t
        audio = torch.cat([c if c.dim() == 1 else c.flatten() for c in teile]).numpy()
        sek = len(audio) / m.sample_rate
        wf.write(str(H / f"pocket_{sprache}_{ref.stem}.wav"), m.sample_rate, (np.clip(audio, -1, 1) * 32767).astype(np.int16))
        erg[f"{sprache}:{ref.stem}"] = {"erster_ton_s": round(erst, 2), "rechnen_s": round(dauer_r, 2), "sprache_s": round(sek, 2),
                                        "echtzeit_x": round(sek / dauer_r, 2)}
        print(sprache, ref.stem, erg[f"{sprache}:{ref.stem}"], flush=True)
    erg[f"{sprache}:laden_s"] = round(lade, 1)
(H / "pocket_messung.json").write_text(json.dumps(erg, indent=1), encoding="utf-8")
