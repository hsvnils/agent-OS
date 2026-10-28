"""Self-Checks Sprach-Arbeiter (JARVIS_ALLTAG J2b) -- offline, Bridge/Stimme gefakt (kein qwen-tts noetig)."""
import unittest

from sprachdienst import worker as w


class FakeStimme:
    modell = "fake"

    def __init__(self, sekunden=2.0, fehler=None):
        self.sekunden, self.fehler, self.texte = sekunden, fehler, []

    def sprechen(self, text):
        if self.fehler:
            raise self.fehler
        self.texte.append(text)
        return [0.0] * int(24000 * self.sekunden), 24000


class FakeBridge:
    def __init__(self, auftraege):
        self.auftraege, self.ergebnisse = list(auftraege), []

    def _req(self, pfad, method="GET", data=None, timeout=None):
        if pfad == "/api/sprache/naechster":
            return {"auftrag": self.auftraege.pop(0) if self.auftraege else None}
        self.ergebnisse.append(data)
        return {"ok": True}


class TestAbschnitte(unittest.TestCase):
    def test_1_ganze_saetze_und_obergrenze(self):
        text = " ".join(f"Satz Nummer {i} ist hier zu Ende." for i in range(40))
        teile = w.abschnitte(text, max_zeichen=120)
        self.assertTrue(all(len(t) <= 120 for t in teile))
        self.assertTrue(all(t.endswith(".") for t in teile))
        self.assertEqual(" ".join(teile), " ".join(text.split()))

    def test_2_ueberlanger_satz_am_komma(self):
        s = "Heute " + ", ".join(f"Punkt {i}" for i in range(60)) + "."
        teile = w.abschnitte(s, max_zeichen=100)
        self.assertTrue(all(len(t) <= 100 for t in teile))
        self.assertTrue(teile[0].endswith(","))
        self.assertEqual(w.abschnitte("   "), [])


class TestDurchlauf(unittest.TestCase):
    def test_1_fertig_mit_mp3(self):
        b = FakeBridge([{"id": "SP-1", "text": "Guten Morgen."}])
        self.assertEqual(w.durchlauf(b, FakeStimme(), mp3=lambda s, sr: b"ID3xx"), 1)
        e = b.ergebnisse[0]
        self.assertTrue(e["ok"])
        self.assertEqual(e["sprache_s"], 2.0)
        self.assertEqual(e["mp3_b64"], "SUQzeHg=")

    def test_2_fehler_und_stille_werden_gemeldet(self):
        b = FakeBridge([{"id": "SP-1", "text": "x"}, {"id": "SP-2", "text": "y"}])
        w.durchlauf(b, FakeStimme(fehler=RuntimeError("kaputt")), mp3=lambda s, sr: b"ID3")
        self.assertFalse(b.ergebnisse[0]["ok"])
        self.assertIn("kaputt", b.ergebnisse[0]["grund"])
        b = FakeBridge([{"id": "SP-3", "text": "z"}])
        w.durchlauf(b, FakeStimme(sekunden=0.1), mp3=lambda s, sr: b"ID3")
        self.assertEqual(b.ergebnisse[0]["grund"], "keine Sprache erzeugt")


if __name__ == "__main__":
    unittest.main()
