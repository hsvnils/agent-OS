"""Self-Checks Backoffice-Worker (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 2) -- offline, Bridge/Ollama gefakt."""
import unittest
from datetime import datetime

from backoffice import worker as w

GUT = ("Sehr geehrter Herr Berger, leider muss ich unseren Termin am Donnerstag verschieben, weil ich auf "
       "Dienstreise bin. Passt Ihnen Dienstag oder Mittwoch vormittags? Viele Grüße, Nils Krüger")
# Echte Fehlbilder aus BF-23 (qwen3:14b, 2026-09-26):
SCHLEIFE = "Hallo Nils! Wie kann ich ich ich ich ich ich ich ich ich ich ich ich ich ich ich ich"
SALAT = "Es gibt insgesamt 15 Anträge. Die Mostly Anträge kommen von CTO.甦\n\\Framework\\$\\$\\$\\$\\$\\$\\$\\$"


class FakeOllama:
    modell = "qwen3:14b"

    def __init__(self, antworten, geladen=False):
        self.antworten, self._geladen, self.entladen_n, self.gesehen = list(antworten), geladen, 0, []

    def geladen(self):
        return self._geladen

    def antwort(self, messages):
        self.gesehen.append(messages)
        return self.antworten.pop(0)

    def entladen(self):
        self.entladen_n += 1


class FakeBridge:
    def __init__(self, auftraege):
        self.auftraege, self.meldungen, self.abgerufen = list(auftraege), [], 0

    def _req(self, pfad, method="GET", data=None, timeout=None):
        if pfad == "/api/backoffice/naechster":
            self.abgerufen += 1
            return {"auftrag": self.auftraege.pop(0) if self.auftraege else None}
        self.meldungen.append(data)
        return {"ok": True}


class TestWorker(unittest.TestCase):
    def test_1_darf_laden(self):
        self.assertTrue(w.darf_laden(None, geladen=True, nacht=False, schwelle_tag=13, schwelle_nacht=11)[0])
        self.assertTrue(w.darf_laden(13.5, geladen=False, nacht=False, schwelle_tag=13, schwelle_nacht=11)[0])
        self.assertFalse(w.darf_laden(12.0, geladen=False, nacht=False, schwelle_tag=13, schwelle_nacht=11)[0])
        self.assertTrue(w.darf_laden(12.0, geladen=False, nacht=True, schwelle_tag=13, schwelle_nacht=11)[0])
        self.assertFalse(w.darf_laden(None, geladen=False, nacht=True, schwelle_tag=13, schwelle_nacht=11)[0])

    def test_2_nacht(self):
        self.assertTrue(w.ist_nacht(datetime(2026, 9, 27, 1, 0)))
        self.assertFalse(w.ist_nacht(datetime(2026, 9, 27, 6, 0)))

    def test_3_plausibilitaet_faengt_bf23_ab(self):
        self.assertEqual(w.plausibel(GUT), [])
        self.assertIn("Wort-Wiederholungsschleife", w.plausibel(SCHLEIFE))
        self.assertTrue({"fremde Schriftzeichen", "Zeichensalat"} & set(w.plausibel(SALAT)))

    def test_4_anweisung_je_art(self):
        m = w.nachrichten({"art": "entwurf", "aufgabe": "Mail an Thomas"})
        self.assertIn("Ich-Form", m[0]["content"])
        self.assertIn("Pflichtpunkten", w.nachrichten({"art": "bewertung", "aufgabe": "x"})[0]["content"])
        self.assertIn("vollständig", w.nachrichten({"art": "unbekannt", "aufgabe": "x"})[0]["content"])

    def test_5_unbrauchbar_einmal_wiederholen(self):
        o = FakeOllama([SCHLEIFE, GUT])
        r = w.verarbeite({"id": "A-1", "art": "entwurf", "aufgabe": "x"}, o, lambda a, e: "")
        self.assertEqual((r["ok"], r["ergebnis"], len(o.gesehen)), (True, GUT, 2))
        o = FakeOllama([SCHLEIFE, SALAT])
        r = w.verarbeite({"id": "A-2", "art": "entwurf", "aufgabe": "x"}, o, lambda a, e: "")
        self.assertFalse(r["ok"])
        self.assertIn("unbrauchbar", r["grund"])

    def test_6_gegenlesen_nur_bei_bewertung_und_analyse(self):
        gelesen = []
        leser = lambda a, e: gelesen.append(a["art"]) or "Teile die Empfehlung."
        r = w.verarbeite({"id": "A-3", "art": "bewertung", "aufgabe": "x"}, FakeOllama([GUT]), leser)
        self.assertEqual(r["zweitmeinung"], "Teile die Empfehlung.")
        w.verarbeite({"id": "A-4", "art": "entwurf", "aufgabe": "x"}, FakeOllama([GUT]), leser)
        self.assertEqual(gelesen, ["bewertung"])

    def test_7_ram_zu_knapp_nichts_holen(self):
        b = FakeBridge([{"id": "A-5", "kurz": "5", "art": "entwurf", "aufgabe": "x"}])
        n = w.durchlauf(b, FakeOllama([GUT]), lambda a, e: "", messen=lambda: 5.0, jetzt=datetime(2026, 9, 27, 14))
        self.assertEqual((n, b.abgerufen), (0, 0))                          # Auftrag bleibt in der Warteschlange

    def test_8_stapel_abarbeiten_dann_entladen(self):
        b = FakeBridge([{"id": "A-6", "kurz": "6", "art": "entwurf", "aufgabe": "x"},
                        {"id": "A-7", "kurz": "7", "art": "zusammenfassung", "aufgabe": "y"}])
        o = FakeOllama([GUT, GUT])
        n = w.durchlauf(b, o, lambda a, e: "", messen=lambda: 16.0, jetzt=datetime(2026, 9, 27, 14))
        self.assertEqual(n, 2)
        self.assertEqual([m["id"] for m in b.meldungen], ["A-6", "A-7"])
        self.assertTrue(all(m["ok"] for m in b.meldungen))
        self.assertEqual(o.entladen_n, 1)


if __name__ == "__main__":
    unittest.main()
