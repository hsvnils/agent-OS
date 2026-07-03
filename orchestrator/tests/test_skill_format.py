import tempfile
import unittest
from pathlib import Path

from orchestrator.core import skill_format as sf


class TestSkillFormat(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def _md(self, text):
        (self.root / "SKILL.md").write_text(text, encoding="utf-8")

    def test_parse_skill_card(self):
        card = sf.parse_skill_card('---\nname: foo\nversion: "1.0"\nbeschreibung: Ein Test\n---\nInhalt\n')
        self.assertEqual(card["name"], "foo")
        self.assertEqual(card["version"], "1.0")           # Quotes entfernt
        self.assertEqual(card["beschreibung"], "Ein Test")

    def test_parse_ohne_frontmatter(self):
        self.assertEqual(sf.parse_skill_card("# Kein Frontmatter\n"), {})

    def test_konform(self):
        self._md("---\nname: mein-skill\nversion: 1.0.0\nbeschreibung: X\nlizenz: intern\n---\nAnleitung\n")
        self.assertEqual(sf.validiere(self.root), [])
        self.assertTrue(sf.ist_konform(self.root))

    def test_fehlende_skill_md(self):
        f = sf.validiere(self.root)
        self.assertTrue(any(x.schwere == "mittel" and "SKILL.md" in x.titel for x in f))

    def test_fehlendes_frontmatter(self):
        self._md("# Skill\nNur Text.\n")
        f = sf.validiere(self.root)
        self.assertTrue(any("Frontmatter" in x.titel for x in f))
        self.assertFalse(sf.ist_konform(self.root))

    def test_fehlende_pflichtfelder(self):
        self._md("---\nname: mein-skill\nversion: 1.0\n---\nText\n")   # beschreibung + lizenz fehlen
        f = sf.validiere(self.root)
        problem = [x for x in f if "Pflichtfelder" in x.titel][0]
        self.assertIn("beschreibung", problem.detail)
        self.assertIn("lizenz", problem.detail)

    def test_name_nicht_kebab(self):
        self._md("---\nname: Mein_Skill\nversion: 1.0\nbeschreibung: X\nlizenz: intern\n---\n")
        f = sf.validiere(self.root)
        self.assertTrue(any("kebab" in x.titel for x in f))

    def test_version_nicht_semver(self):
        self._md("---\nname: mein-skill\nversion: v1\nbeschreibung: X\nlizenz: intern\n---\n")
        f = sf.validiere(self.root)
        self.assertTrue(any("semver" in x.titel for x in f))


if __name__ == "__main__":
    unittest.main()
