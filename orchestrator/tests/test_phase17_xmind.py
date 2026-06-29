"""Phase 17 (LUNA am Mac) — M5/#2: XMind-Inhalt lesen + bearbeiten (.xmind-Datei).

Plattformunabhaengig: erzeugt eine temporaere .xmind (ZIP + content.json) und prueft lesen/hinzufuegen/
umbenennen. Keine macOS-Abhaengigkeit (reine Datei-/JSON-Operationen).
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from runner import xmind


def _make_xmind(path: Path):
    content = [{
        "id": "s1", "class": "sheet", "title": "Blatt 1",
        "rootTopic": {"id": "r", "class": "topic", "title": "Wurzel",
                      "children": {"attached": [
                          {"id": "a", "class": "topic", "title": "Ast A"},
                          {"id": "b", "class": "topic", "title": "Ast B"},
                      ]}},
    }]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.json", json.dumps(content, ensure_ascii=False))
        z.writestr("metadata.json", "{}")


class TestXmind(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "test.xmind")
        _make_xmind(Path(self.path))

    def tearDown(self):
        self._tmp.cleanup()

    def test_lesen(self):
        r = xmind.read_outline(self.path)
        self.assertTrue(r["ok"])
        self.assertIn("Wurzel", r["gliederung"])
        self.assertIn("Ast A", r["gliederung"])

    def test_knoten_hinzufuegen_unter_eltern(self):
        r = xmind.add_node(self.path, "Neuer Knoten", eltern="Ast A")
        self.assertTrue(r["ok"])
        self.assertEqual(r["eltern"], "Ast A")
        self.assertIn("Neuer Knoten", xmind.read_outline(self.path)["gliederung"])

    def test_knoten_hinzufuegen_wurzel(self):
        r = xmind.add_node(self.path, "Direkt an Wurzel")
        self.assertTrue(r["ok"])
        self.assertEqual(r["eltern"], "Wurzel")

    def test_eltern_nicht_gefunden(self):
        r = xmind.add_node(self.path, "X", eltern="GibtsNicht")
        self.assertFalse(r["ok"])

    def test_umbenennen(self):
        r = xmind.rename_node(self.path, "Ast B", "Ast B neu")
        self.assertTrue(r["ok"])
        g = xmind.read_outline(self.path)["gliederung"]
        self.assertIn("Ast B neu", g)
        self.assertNotIn("- Ast B\n", g + "\n")

    def test_umbenennen_nicht_gefunden(self):
        r = xmind.rename_node(self.path, "Unbekannt", "Neu")
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
