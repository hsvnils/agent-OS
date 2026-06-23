"""Self-Check: nach einer Aktion ein umlautfreier Changelog-Eintrag."""
import os
import tempfile
import unittest

from orchestrator.governance.changelog_tool import append_changelog

UMLAUTE = "äöüÄÖÜß"


class TestChangelog(unittest.TestCase):
    def test_eintrag_ist_umlautfrei_und_wird_eingefuegt(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "cl.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# Changelog\n\n## Eintraege\n")

        # Quelle enthaelt Umlaute -> muss transliteriert werden
        entry = append_changelog(
            p, "Head of Agents",
            "Etwas geändert mit Umlaut-Quelle: Aenderung",
            "Grund mit ueberfluessigen Zeichen",
            "Dateien/Agenten",
        )

        with open(p, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("## Eintraege", content)
        self.assertIn(entry.strip(), content)
        # Eintrag enthaelt keine Umlaute/scharfes S
        for ch in entry:
            self.assertNotIn(ch, UMLAUTE)


if __name__ == "__main__":
    unittest.main()
