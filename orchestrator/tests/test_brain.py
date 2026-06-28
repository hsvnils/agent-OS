import tempfile
import unittest
from pathlib import Path

from orchestrator.core.brain import Brain


class TestBrain(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.brain = Brain(Path(self.dir.name) / "brain.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_merken_und_suchen(self):
        self.brain.merken("Partner Hotel Oetztal: 4-Sterne, Kooperation fuer Reels geplant.",
                          titel="Hotel Oetztal", tags=["partner", "marketing"])
        self.brain.merken("Steuerberater Termin im Juli vorbereiten.", titel="Steuer")
        treffer = self.brain.suchen("hotel oetztal kooperation")
        self.assertTrue(treffer)
        self.assertEqual(treffer[0]["titel"], "Hotel Oetztal")

    def test_suche_ohne_treffer(self):
        self.brain.merken("Irgendein Text ueber Aepfel.")
        self.assertEqual(self.brain.suchen("voellig anderes thema xyz"), [])

    def test_dedup_per_ref(self):
        a = self.brain.merken("Befund A", ref="R-1", quelle="research")
        b = self.brain.merken("Befund A (anderer Text)", ref="R-1", quelle="research")
        self.assertEqual(a, b)  # gleiche ref -> kein Duplikat
        self.assertEqual(len(self.brain._items()), 1)

    def test_dedup_per_text(self):
        self.brain.merken("Exakt gleicher Text")
        self.brain.merken("Exakt gleicher Text")
        self.assertEqual(len(self.brain._items()), 1)

    def test_vergessen(self):
        bid = self.brain.merken("Bald vergessen", titel="Temp")
        self.assertTrue(self.brain.vergessen(bid))
        self.assertEqual(self.brain.suchen("vergessen"), [])
        self.assertFalse(self.brain.vergessen("B-existiert-nicht"))

    def test_titel_wird_hoeher_gewichtet(self):
        self.brain.merken("Budget steht im Titel.", titel="Budget Planung")
        self.brain.merken("Hier kommt das Wort budget nur im Fliesstext vor, sonst nichts wichtiges.")
        treffer = self.brain.suchen("budget")
        self.assertEqual(treffer[0]["titel"], "Budget Planung")

    def test_leerer_text_wird_nicht_gespeichert(self):
        self.assertEqual(self.brain.merken("   "), "")
        self.assertEqual(self.brain._items(), [])


if __name__ == "__main__":
    unittest.main()
