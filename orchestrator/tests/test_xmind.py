"""Phase 17 (M5) -- XMind lesen/bearbeiten (add/rename/delete/move) offline."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from runner import xmind


def _make(path, data):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.json", json.dumps(data, ensure_ascii=False))
        z.writestr("metadata.json", "{}")   # weiterer Eintrag -> muss erhalten bleiben


def _content(path):
    with zipfile.ZipFile(path, "r") as z:
        return json.loads(z.read("content.json").decode("utf-8")), z.namelist()


class TestXmind(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.p = str(Path(self.dir.name) / "m.xmind")
        _make(self.p, [{"title": "Blatt", "rootTopic": {"title": "Wurzel", "children": {"attached": [
            {"title": "A", "children": {"attached": [{"title": "A1"}]}},
            {"title": "B"},
        ]}}}])

    def tearDown(self):
        self.dir.cleanup()

    def test_read_outline(self):
        r = xmind.read_outline(self.p)
        self.assertTrue(r["ok"])
        for t in ("Wurzel", "A", "A1", "B"):
            self.assertIn(t, r["gliederung"])

    def test_add_node(self):
        self.assertTrue(xmind.add_node(self.p, "C", eltern="B")["ok"])
        self.assertIn("C", xmind.read_outline(self.p)["gliederung"])
        # metadata.json erhalten
        _, namen = _content(self.p)
        self.assertIn("metadata.json", namen)

    def test_rename_node(self):
        self.assertTrue(xmind.rename_node(self.p, "A1", "A1neu")["ok"])
        gl = xmind.read_outline(self.p)["gliederung"]
        self.assertIn("A1neu", gl)
        self.assertNotIn("A1\n", gl + "\n")

    def test_delete_node(self):
        r = xmind.delete_node(self.p, "A")
        self.assertTrue(r["ok"])
        gl = xmind.read_outline(self.p)["gliederung"]
        self.assertNotIn("A1", gl)             # Unterknoten mit weg
        self.assertNotIn("- A", gl)
        self.assertIn("B", gl)

    def test_delete_wurzel_verboten(self):
        self.assertFalse(xmind.delete_node(self.p, "Wurzel")["ok"])

    def test_delete_nicht_gefunden(self):
        self.assertFalse(xmind.delete_node(self.p, "GibtsNicht")["ok"])

    def test_move_node(self):
        r = xmind.move_node(self.p, "B", "A")
        self.assertTrue(r["ok"])
        data, _ = _content(self.p)
        a = next(k for k in data[0]["rootTopic"]["children"]["attached"] if k["title"] == "A")
        self.assertTrue(any(k["title"] == "B" for k in a["children"]["attached"]))
        # B nicht mehr direkt unter Wurzel
        self.assertFalse(any(k["title"] == "B" for k in data[0]["rootTopic"]["children"]["attached"]))

    def test_move_zyklus_verboten(self):
        # A unter A1 (A1 ist Nachfahre von A) -> Zyklus
        self.assertFalse(xmind.move_node(self.p, "A", "A1")["ok"])

    def test_move_wurzel_verboten(self):
        self.assertFalse(xmind.move_node(self.p, "Wurzel", "A")["ok"])

    def test_move_ziel_unbekannt(self):
        self.assertFalse(xmind.move_node(self.p, "B", "GibtsNicht")["ok"])


if __name__ == "__main__":
    unittest.main()
