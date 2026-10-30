"""Paket D L2-Nachbesserung 30.10.: Echo-Sperre nach Aufnahmezeit, „Danke LUNA“-Varianten, Ducken statt Abbrechen.
Die Windows-Teile (numpy, Mikrofon, Stimme) gibt es hier nicht -- sie werden fuer den Import durch Attrappen ersetzt."""
import importlib.util
import sys
import types
import unittest
from collections import deque
from pathlib import Path

PFAD = Path(__file__).resolve().parents[2] / "desktop" / "probe_l1.py"


def _probe():
    alt = {}
    for name in ("numpy", "requests", "sounddevice", "webrtcvad"):
        alt[name] = sys.modules.get(name)
        if name not in sys.modules or name in ("numpy", "sounddevice", "webrtcvad"):
            sys.modules[name] = types.ModuleType(name)
    try:
        spec = importlib.util.spec_from_file_location("probe_l1_test", PFAD)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        for name, mod in alt.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod


p = _probe()


class TestEcho(unittest.TestCase):
    def test_1_eigenes_echo(self):
        gesagt = "Das ist ein alter Internet-Scherz – Leggit-Ting ist kein echter Mensch."
        self.assertTrue(p.ist_eigenes_echo("Das ist ein alter Internet-Charts.", gesagt))      # Fall vom Live-Test
        self.assertTrue(p.ist_eigenes_echo("kein echter Mensch", gesagt))
        self.assertFalse(p.ist_eigenes_echo("Wer ist 3 Legged Thing?", gesagt))
        self.assertFalse(p.ist_eigenes_echo("Stopp", gesagt))

    def test_2_fenster_ab_aufnahme_nicht_ab_auswertung(self):
        m = types.SimpleNamespace(gesagt=deque([(100.0, "Das ist ein alter Internet-Scherz.")]))
        # Aufnahme bei 104-106 s, ausgewertet erst bei 120 s (Warteschlange): Satz zaehlt trotzdem
        self.assertIn("Internet-Scherz", p.Mund.kuerzlich_gesagt(m, 104.0, 106.0))
        self.assertEqual(p.Mund.kuerzlich_gesagt(m, 120.0, 121.0), "")                       # lange danach: nicht
        self.assertEqual(p.Mund.kuerzlich_gesagt(m, 90.0, 95.0), "")                         # vor dem Satz: nicht

    def test_3_danke_luna_varianten(self):
        for s in ("Danke LUNA.", "Danke, Juna.", "Danke, Lena.", "Okay, danke Luna.", "Tschüss Luna"):
            self.assertTrue(p.ENDE.search(s), s)
        for s in ("Danke.", "Danke für die Info", "Wer ist Lena Meyer?"):
            self.assertFalse(p.ENDE.search(s), s)

    def test_4_ducken_und_zurueck(self):
        prot = types.SimpleNamespace(eintraege=[])
        prot.schreibe = lambda **k: prot.eintraege.append(k["art"])
        spricht = types.SimpleNamespace(is_set=lambda: True)
        m = types.SimpleNamespace(_spricht=spricht, lautstaerke=1.0, prot=prot)
        p.Mund.leiser(m)
        self.assertEqual((m.lautstaerke, prot.eintraege), (p.GEDUCKT, ["geduckt"]))
        p.Mund.leiser(m)                                                    # nur einmal protokolliert
        self.assertEqual(prot.eintraege, ["geduckt"])
        p.Mund.normal(m)
        self.assertEqual(m.lautstaerke, 1.0)


if __name__ == "__main__":
    unittest.main()
