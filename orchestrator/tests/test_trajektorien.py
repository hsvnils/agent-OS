import tempfile
import unittest
from pathlib import Path

from orchestrator.core.trajektorien import TrajektorienStore


class TestTrajektorien(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = TrajektorienStore(Path(self.dir.name) / "traj.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_merken_und_aehnliche(self):
        self.store.merken("Reel aus Rohclips schneiden",
                          "Clips in cutter-Ordner legen, launchd erzeugt 9:16-Reel", tags=["cutter", "video"])
        self.store.merken("Sicherheits-Audit durchfuehren",
                          "Tool sicherheits_audit aufrufen, Befunde melden", tags=["security"])
        treffer = self.store.aehnliche("Wie schneide ich ein Reel aus Clips?")
        self.assertTrue(treffer)
        self.assertIn("Reel", treffer[0]["aufgabe"])

    def test_leere_felder_werden_nicht_gespeichert(self):
        self.assertEqual(self.store.merken("", "irgendwas"), "")
        self.assertEqual(self.store.merken("aufgabe", "   "), "")
        self.assertEqual(self.store._items(), [])

    def test_dedup_per_ref(self):
        a = self.store.merken("A", "Weg 1", ref="R-1")
        b = self.store.merken("A geaendert", "Weg 1 anders", ref="R-1")
        self.assertEqual(a, b)
        self.assertEqual(len(self.store._items()), 1)

    def test_dedup_per_inhalt(self):
        self.store.merken("gleich", "gleicher weg")
        self.store.merken("gleich", "gleicher weg")
        self.assertEqual(len(self.store._items()), 1)

    def test_nur_erfolg_filtert_misserfolg(self):
        self.store.merken("Deploy testen", "Weg der geklappt hat", erfolg=True, tags=["deploy"])
        self.store.merken("Deploy testen", "Weg der fehlschlug", erfolg=False, tags=["deploy"])
        nur_ok = self.store.aehnliche("Deploy testen", nur_erfolg=True)
        self.assertTrue(all(e.get("erfolg") for e in nur_ok))
        alle = self.store.aehnliche("Deploy testen", nur_erfolg=False)
        self.assertGreater(len(alle), len(nur_ok))

    def test_vergessen(self):
        tid = self.store.merken("Temp", "Weg")
        self.assertTrue(self.store.vergessen(tid))
        self.assertEqual(self.store.aehnliche("Temp"), [])
        self.assertFalse(self.store.vergessen("T-gibtsnicht"))

    def test_kein_treffer_leer(self):
        self.store.merken("Aepfel ernten", "in den Korb legen")
        self.assertEqual(self.store.aehnliche("Quantenphysik Vorlesung xyz"), [])


if __name__ == "__main__":
    unittest.main()
