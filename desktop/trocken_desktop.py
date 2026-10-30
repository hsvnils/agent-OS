"""Trockenlauf L2 ohne Ton und ohne NAS: echte Werkzeug-Beschreibungen, nachgebaute Ergebnisse -- prueft Werkzeugwahl,
Ja-Sperre und Zeiten. Aufruf: venv\\Scripts\\python.exe probe\\trocken_desktop.py"""
import json, sys, threading, time
from datetime import datetime
from pathlib import Path
import numpy as np
import sounddevice as sd
sys.path.insert(0, str(Path(__file__).parent))
import probe_l1 as p
import luna_desktop as ld


class _StummerStrom:
    def __init__(self, *, callback, blocksize, **_):
        self.cb, self.n = callback, blocksize

    def start(self):
        def lauf():
            out = np.zeros((self.n, 1), dtype=np.int16)
            while True:
                self.cb(out, self.n, None, None)
                time.sleep(self.n / p.RATE)
        threading.Thread(target=lauf, daemon=True).start()


ERGEBNIS = {
    "brain_suchen": {"treffer": [{"quelle": "Firma P-00003 3 Legged Thing Ltd (Partner)", "text": "Instagram-Collab Trainingscamp; "
                     "Ansprechpartnerin Alison, Marketing; Muster der Punks-Range laut Mail vom 29.10. Ende November erwartet."},
                     {"quelle": "To-do A-2e60f375, faellig 2026-11-30", "text": "3 Legged Thing: nachfragen, wie es mit den Mustern aussieht"}]},
    "kalender_agenda": {"ok": True, "termine": [{"start": "2026-10-30T14:00:00+01:00", "titel": "Marketingroadmap ausarbeiten"}]},
    "todo_anlegen": {"ok": True, "id": "A-test", "titel": "Alison schreiben", "faellig": "2026-11-02"},
    "termin_anlegen": None,
    "brain_suchen_kiez": {"treffer": [{"quelle": "Rechnung an Kiez Alm Gastro GmbH, 11.05.2026", "text": "bezahlt"},
                                      {"quelle": "Angebot an Kiez Alm, 05.10.2026, 1.600 Euro", "text": "offen, wartet auf Antwort"}]},
}


class FakeApi:
    aufrufe = []

    def werkzeug(self, name, args, zug):
        self.aufrufe.append((name, args))
        if name == "termin_anlegen":
            r = {"ok": True, "angelegt": True} if args.get("bestaetigt") else {"ok": True, "vorschau": args, "hinweis": "Nur Vorschau."}
        else:
            r = ERGEBNIS["brain_suchen_kiez"] if name == "brain_suchen" and "kiez" in json.dumps(args).lower() \
                else ERGEBNIS.get(name, {"ok": True, "hinweis": "keine Daten"})
        return json.dumps(r, ensure_ascii=False)


sd.OutputStream = _StummerStrom
d = json.load(open(Path(__file__).parent / "_specs_test.json", encoding="utf-8"))
specs, gruppen = d["werkzeuge"], d["gruppen"]
werkzeuge = [{"type": "function", "function": {"name": s["name"], "description": s["description"], "parameters": s["input_schema"]}}
             for s in specs]
system = ld.SYSTEM.format(kalender=ld.kalender_text(datetime(2026, 10, 30, 10, 0)))
api = FakeApi()
prot = p.Protokoll(Path(__file__).parent / "trocken_log.jsonl")
kopf = ld.Kopf(api, werkzeuge, prot, ld.Werkzeugpflicht(gruppen, "LUNA, Nils, Kiez Alm, 3 Legged Thing, Alison, Athleticum"))
mund = p.Mund("pocket:german/anna", None, prot)
M = "qwen3:30b-a3b-instruct-2507-q4_K_M"
verlauf = [{"role": "system", "content": system}]
for satz in ("Wer ist 3 Legged Thing?", "Was steht heute im Kalender?", "Erinner mich Montag daran, Alison zu schreiben.",
             "Trag mir morgen um 10 Uhr einen Termin Dreh im Athleticum ein.", "Ja, mach.", "Was ist mit der Kiez Alm offen?",
             "Wie geht es dir?", "Schick die Mail an Alison gleich raus."):
    api.aufrufe.clear(); mund.erster_ton = None; mund.unterbrochen.clear()
    verlauf.append({"role": "user", "content": f"(Jetzt: Freitag 30.10.2026 10:00) {satz}"})
    t = p.jetzt()
    antwort, erst = kopf(M, verlauf, mund, mund.unterbrochen)
    verlauf.append({"role": "assistant", "content": antwort})
    print(f"\nDU: {satz}\n   Werkzeuge: {[(n, {k: v for k, v in a.items() if k in ('frage','titel','faellig','start','bestaetigt','tage')}) for n, a in api.aufrufe]}"
          f"\n   erster Ton {((mund.erster_ton or p.jetzt()) - t):.1f} s, fertig {p.jetzt() - t:.1f} s\n   LUNA: {antwort}")
    while mund.spricht() or not mund.saetze.empty():
        time.sleep(0.05)
