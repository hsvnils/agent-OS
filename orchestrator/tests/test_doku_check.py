"""Self-Check: Doku und Code laufen nicht auseinander (scripts/doku_check.py, AGENTS.md 6)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "doku_check.py"


def _lade():
    spec = importlib.util.spec_from_file_location("doku_check", SKRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(SKRIPT.exists() and (ROOT / "docs" / "datenfluesse.md").exists(),
                     "Doku-Check nur im vollstaendigen Repo")
class TestDokuCheck(unittest.TestCase):
    def setUp(self):
        self.dc = _lade()

    def test_1_repo_ist_konsistent(self):
        self.assertEqual(self.dc.pruefe_roadmaps() + self.dc.pruefe_datenfluesse(), [])

    def test_2_gegenprobe_fehlender_host_wird_gemeldet(self):
        text = (ROOT / "docs" / "datenfluesse.md").read_text(encoding="utf-8")
        self.assertIn("\napi.telegram.org\n", text)
        tmp = Path(tempfile.mkdtemp()) / "datenfluesse.md"
        tmp.write_text(text.replace("\napi.telegram.org\n", "\n", 1), encoding="utf-8")
        with mock.patch.object(self.dc, "DOKU", tmp):
            fehler = self.dc.pruefe_datenfluesse()
        self.assertTrue(any("api.telegram.org" in f and "nicht in" in f for f in fehler), fehler)

    def test_3_gegenprobe_veralteter_eintrag_wird_gemeldet(self):
        text = (ROOT / "docs" / "datenfluesse.md").read_text(encoding="utf-8")
        tmp = Path(tempfile.mkdtemp()) / "datenfluesse.md"
        tmp.write_text(text.replace("```doku-check:tabellen\n", "```doku-check:tabellen\ngibt_es_nicht\n", 1),
                       encoding="utf-8")
        with mock.patch.object(self.dc, "DOKU", tmp):
            fehler = self.dc.pruefe_datenfluesse()
        self.assertTrue(any("gibt_es_nicht" in f and "nicht mehr vor" in f for f in fehler), fehler)

    def test_4_gegenprobe_roadmap_ohne_header_und_verzeichnis(self):
        d = Path(tempfile.mkdtemp())
        (d / "ROADMAP.md").write_text("# Master\n", encoding="utf-8")
        (d / "TEST_ROADMAP.md").write_text("# Roadmap: Test\n\n- Status: vielleicht\n", encoding="utf-8")
        with mock.patch.object(self.dc, "ROOT", d):
            fehler = self.dc.pruefe_roadmaps()
        self.assertTrue(any("Roadmap-Verzeichnis" in f for f in fehler), fehler)
        self.assertTrue(any("Basiscommit" in f for f in fehler), fehler)
        self.assertTrue(any("ungueltig" in f for f in fehler), fehler)

    def test_5_gueltige_roadmap_ist_ok(self):
        d = Path(tempfile.mkdtemp())
        (d / "ROADMAP.md").write_text("| `TEST_ROADMAP.md` | Test |\n", encoding="utf-8")
        (d / "TEST_ROADMAP.md").write_text(
            "# Roadmap: Test\n\n- Status: geplant\n- Stand: 2026-09-25\n- Arbeitsbranch: `ai/test`\n"
            "- Basiscommit: `abc1234`\n- Naechster Schritt: vorlegen\n- Hinweis: Plan, kein Auftrag.\n",
            encoding="utf-8")
        with mock.patch.object(self.dc, "ROOT", d):
            self.assertEqual(self.dc.pruefe_roadmaps(), [])


if __name__ == "__main__":
    unittest.main()
