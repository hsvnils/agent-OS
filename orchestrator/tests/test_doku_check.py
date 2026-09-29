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
        self.assertEqual(self.dc.pruefe_roadmaps() + self.dc.pruefe_datenfluesse()
                         + self.dc.pruefe_speicherschutz() + self.dc.pruefe_changelog(), [])

    def test_1b_changelog_format_zeit_reihenfolge(self):
        """BETRIEB_ROADMAP Etappe 2: Pflichtformat, keine Zukunft (BF-09), neueste zuerst ab dem Stichtag."""
        from datetime import datetime
        jetzt = datetime(2026, 9, 30, 12, 0)
        def e(kopf, was="x", warum="y", betroffen="z"):
            return f"{kopf}\n- **Was:** {was}\n- **Warum:** {warum}\n- **Betroffen:** {betroffen}\n\n"
        gut = ("# Changelog\n\n## Eintraege\n\n" + e("## [2026-09-30 11:00] — Claude Code")
               + e("## [2026-09-29 18:00] — Codex") + e("## [2026-09-20 08:00] — HoA") + e("## [2026-09-21 09:00] — HoA"))
        self.assertEqual(self.dc.pruefe_changelog(gut, jetzt), [])            # alte Unordnung (vor Stichtag) bleibt
        faelle = {
            "Kopf nicht im Format": e("## 2026-09-30 11:00 — Claude Code"),
            "Feld(er) fehlen oder leer: Warum": e("## [2026-09-30 11:00] — Claude Code", warum=""),
            "liegt in der Zukunft": e("## [2026-09-30 12:30] — Claude Code"),
            "ungueltiges Datum": e("## [2026-09-31 11:00] — Claude Code"),
        }
        for erwartet, eintrag in faelle.items():
            with self.subTest(erwartet=erwartet):
                befunde = self.dc.pruefe_changelog("## Eintraege\n" + eintrag, jetzt)
                self.assertTrue(any(erwartet in b for b in befunde), befunde)
        falsch_sortiert = "## Eintraege\n" + e("## [2026-09-29 18:00] — A") + e("## [2026-09-30 09:00] — B")
        self.assertTrue(any("steht unter dem aelteren Eintrag" in b
                            for b in self.dc.pruefe_changelog(falsch_sortiert, jetzt)))
        self.assertEqual(self.dc.pruefe_changelog("## [2026-09-30 11:00] — x", jetzt),
                         ["Changelog: Abschnitt „## Eintraege“ fehlt"])

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

    def test_3b_gegenprobe_speicher_ohne_backup_wird_gemeldet(self):
        text = (ROOT / "docs" / "datenfluesse.md").read_text(encoding="utf-8")
        zeile = "content_ops/trends_cache.jsonl\n"
        self.assertIn("```doku-check:ohne-backup\n", text)
        tmp = Path(tempfile.mkdtemp()) / "datenfluesse.md"
        teil = text.split("```doku-check:ohne-backup\n", 1)
        tmp.write_text(teil[0] + "```doku-check:ohne-backup\n" + teil[1].replace(zeile, "", 1), encoding="utf-8")
        with mock.patch.object(self.dc, "DOKU", tmp):
            fehler = self.dc.pruefe_speicherschutz()
        self.assertTrue(any("kein Backup: content_ops/trends_cache.jsonl" in f for f in fehler), fehler)

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
