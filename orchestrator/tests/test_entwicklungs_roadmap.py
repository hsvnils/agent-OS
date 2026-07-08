"""Tests fuer die Entwicklungs-Roadmap (aus freigegebenen Antraegen) -- reine Logik, kein Netz/NAS."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.entwicklungs_roadmap import EntwicklungsRoadmap


def _antrag(antrag_id="A-1", titel="Titel", von="CTO (Selbst-Entwicklung)"):
    return {"antrag_id": antrag_id, "titel": titel, "beschreibung": "Beschreibung", "kategorie": "Innovation",
            "von": von, "verlauf": [{"ts": "2026-07-08T10:00:00", "event": "eingereicht"},
                                    {"ts": "2026-07-08T11:00:00", "event": "freigegeben"}]}


class TestAufnehmen(unittest.TestCase):
    def test_aufnehmen_und_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            rid = rm.aufnehmen(_antrag("A-1"))
            self.assertTrue(rid and rid.startswith("E-"))
            self.assertIsNone(rm.aufnehmen(_antrag("A-1")))       # gleiche antrag_id -> None
            self.assertEqual(len(rm.list()), 1)
            it = rm.get(rid)
            self.assertEqual(it["status"], "offen")
            self.assertEqual(it["quelle"], "self-dev")            # "Selbst-Entwicklung" -> self-dev
            self.assertEqual(it["freigegeben_ts"], "2026-07-08T11:00:00")

    def test_quelle_antrag_ohne_selbstentwicklung(self):
        with tempfile.TemporaryDirectory() as d:
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            rid = rm.aufnehmen(_antrag("A-2", von="Head of Agents"))
            self.assertEqual(rm.get(rid)["quelle"], "antrag")

    def test_transitions(self):
        with tempfile.TemporaryDirectory() as d:
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            rid = rm.aufnehmen(_antrag("A-3"))
            self.assertTrue(rm.in_arbeit(rid)); self.assertEqual(rm.get(rid)["status"], "in_arbeit")
            self.assertTrue(rm.umsetzen(rid, notiz="commit abc123"))
            self.assertEqual(rm.get(rid)["status"], "umgesetzt")
            self.assertEqual(rm.get(rid)["notiz"], "commit abc123")
            self.assertFalse(rm.umsetzen("E-gibtsnicht"))


class TestMarkdown(unittest.TestCase):
    def test_render_umlautfrei_und_inhalt(self):
        with tempfile.TemporaryDirectory() as d:
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            rm.aufnehmen(_antrag("A-1", titel="Praezise Pruefung fuer Aenderung".replace(
                "Praezise", "Präzise").replace("Pruefung", "Prüfung").replace("fuer", "für").replace(
                "Aenderung", "Änderung")))
            md = rm.als_markdown()
            self.assertTrue(md.strip())
            self.assertNotRegex(md, r"[äöüÄÖÜß]")   # keine ae/oe/ue/ss-Umlaute
            self.assertIn("Praezise Pruefung fuer Aenderung", md)                     # transliteriert
            self.assertTrue((Path(d) / "roadmap.md").exists())                        # render_md hat geschrieben


class TestBackfill(unittest.TestCase):
    def test_backfill_nur_freigegebene_und_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            antraege = Antraege(Path(d) / "antraege.jsonl")           # ohne on_freigabe -> kein Auto-Add
            a1 = antraege.stellen("Erster", "b", von="CTO (Selbst-Entwicklung)")
            a2 = antraege.stellen("Zweiter", "b")
            antraege.stellen("Dritter (nur eingereicht)", "b")        # bleibt eingereicht
            antraege.freigeben(a1)
            antraege.freigeben(a2)
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            self.assertEqual(rm.backfill(antraege), 2)                # nur die 2 freigegebenen
            self.assertEqual(rm.backfill(antraege), 0)               # idempotent
            self.assertEqual(len(rm.list()), 2)

    def test_backfill_faengt_auch_spaeter_umgesetzte(self):
        with tempfile.TemporaryDirectory() as d:
            antraege = Antraege(Path(d) / "antraege.jsonl")
            a1 = antraege.stellen("Umgesetzter", "b")
            antraege.freigeben(a1)
            antraege.status_setzen(a1, "in_umsetzung")               # aktueller Status != freigegeben
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            self.assertEqual(rm.backfill(antraege), 1)               # verlauf hatte 'freigegeben'


class TestHook(unittest.TestCase):
    def test_freigeben_ruft_hook(self):
        with tempfile.TemporaryDirectory() as d:
            rm = EntwicklungsRoadmap(Path(d) / "roadmap.jsonl")
            antraege = Antraege(Path(d) / "antraege.jsonl", on_freigabe=rm.aufnehmen)
            aid = antraege.stellen("Neuer Punkt", "Details", von="CRO (Selbst-Entwicklung)")
            self.assertEqual(len(rm.list()), 0)                      # vor Freigabe: leer
            self.assertTrue(antraege.freigeben(aid))
            items = rm.list()
            self.assertEqual(len(items), 1)                          # nach Freigabe: auf der Roadmap
            self.assertEqual(items[0]["antrag_id"], aid)
            self.assertEqual(items[0]["titel"], "Neuer Punkt")

    def test_hook_fehler_blockiert_freigabe_nicht(self):
        def kaputt(_a):
            raise RuntimeError("boom")
        with tempfile.TemporaryDirectory() as d:
            antraege = Antraege(Path(d) / "antraege.jsonl", on_freigabe=kaputt)
            aid = antraege.stellen("X", "y")
            self.assertTrue(antraege.freigeben(aid))                 # Freigabe trotz Hook-Fehler ok
            self.assertEqual(antraege.get(aid)["status"], "freigegeben")


if __name__ == "__main__":
    unittest.main()
