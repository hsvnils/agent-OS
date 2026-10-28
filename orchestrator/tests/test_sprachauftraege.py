"""JARVIS_ALLTAG J2b: Sprachauftraege fuer die lokale LUNA-Stimme -- Lebenszyklus, MP3-Pruefung, Briefing-Schritt
(einmal je Tag, Abbruch um 10 Uhr, Hinweis), Endpunkte fuer den Sprach-Arbeiter."""
import base64
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.sprachauftraege import SprachStore, briefing_schritt

MP3 = b"ID3" + b"\x00" * 100
D = "2026-10-29"


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = SprachStore(Path(self.tmp.name) / "sprache" / "log.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_1_lebenszyklus(self):
        sid = self.st.anlegen("Guten Morgen.", zweck="briefing:" + D)
        self.assertFalse(self.st.fertig(sid, MP3))                       # erst nach naechster()
        self.assertEqual(self.st.naechster()["id"], sid)
        self.assertIsNone(self.st.naechster())
        with self.assertRaisesRegex(ValueError, "MP3"):
            self.st.fertig(sid, b"<html>kein Ton</html>")
        self.assertTrue(self.st.fertig(sid, MP3, sprache_s=12.3))
        self.assertEqual(self.st.mp3_pfad(sid).read_bytes(), MP3)
        self.assertEqual(self.st.get(sid)["sprache_s"], 12.3)
        self.assertTrue(self.st.gesendet(sid))
        self.assertEqual(self.st.get(sid)["status"], "gesendet")
        with self.assertRaises(ValueError):
            self.st.anlegen("  ", zweck="x")

    def test_2_haengend_und_alte_dateien(self):
        sid = self.st.anlegen("Text.", zweck="x")
        self.st.naechster()
        self.assertEqual(self.st.aufraeumen(stunden=1), 0)
        self.assertEqual(self.st.aufraeumen(stunden=1, jetzt=datetime.now() + timedelta(hours=2)), 1)
        self.assertEqual(self.st.get(sid)["status"], "neu")
        self.st.naechster()
        self.st.fertig(sid, MP3)
        self.st.aufraeumen(jetzt=datetime.now() + timedelta(days=29))
        self.assertTrue(self.st.mp3_pfad(sid).exists())
        self.st.aufraeumen(jetzt=datetime.now() + timedelta(days=31))
        self.assertFalse(self.st.mp3_pfad(sid).exists())
        self.assertEqual(self.st.mp3_pfad("../../etc/passwd").parent, self.st.dir)


class TestBriefingSchritt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = SprachStore(Path(self.tmp.name) / "log.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def schritt(self, h, text="Guten Morgen."):
        return briefing_schritt(self.st, D, datetime(2026, 10, 29, h, 5), text)

    def test_1_einmal_anlegen_dann_senden(self):
        self.assertEqual(self.schritt(7, text=None), ("", None))        # Briefing noch nicht raus
        self.assertEqual(self.st.list(), [])
        self.assertEqual(self.schritt(8), ("", None))
        self.assertEqual(self.schritt(8), ("", None))
        self.assertEqual(len(self.st.list()), 1)                         # nur ein Auftrag je Tag
        a = self.st.naechster()
        self.st.fertig(a["id"], MP3)
        aktion, x = self.schritt(8)
        self.assertEqual((aktion, x["id"]), ("senden", a["id"]))
        self.st.gesendet(a["id"])
        self.assertEqual(self.schritt(9), ("", None))
        self.assertEqual(len(self.st.list()), 1)

    def test_2_zu_spaet_gibt_hinweis(self):
        self.schritt(8)
        self.assertEqual(self.schritt(9)[0], "")
        aktion, a = self.schritt(10)
        self.assertEqual(aktion, "hinweis")
        self.assertIn("nicht fertig", a["grund"])
        self.assertEqual(self.schritt(11)[0], "hinweis")                 # Dedup macht der Bot (Agenda)
        self.assertEqual(briefing_schritt(self.st, "2026-10-30", datetime(2026, 10, 30, 10, 5), "Text."), ("", None))
        self.assertEqual(self.st.zum_zweck("briefing:2026-10-30"), None)  # nach 10 Uhr kein neuer Auftrag


class TestEndpunkte(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = webapp.sprache
        webapp.sprache = SprachStore(Path(self.tmp.name) / "log.jsonl")
        self.st = webapp.sprache
        self.c = TestClient(webapp.app)

    def tearDown(self):
        from orchestrator.channels.web import app as webapp
        webapp.sprache = self.alt
        self.tmp.cleanup()

    def test_1_holen_und_hochladen(self):
        sid = self.st.anlegen("Hallo Nils.", zweck="briefing:" + D)
        r = self.c.get("/api/sprache/naechster").json()
        self.assertEqual(r["auftrag"], {"id": sid, "text": "Hallo Nils."})
        self.assertIsNone(self.c.get("/api/sprache/naechster").json()["auftrag"])
        r = self.c.post("/api/sprache/ergebnis", json={"id": sid, "ok": True, "mp3_b64": base64.b64encode(MP3).decode(),
                                                      "sprache_s": 3}).json()
        self.assertTrue(r["ok"])
        self.assertEqual(self.st.get(sid)["status"], "fertig")

    def test_2_fehler_und_unsinn(self):
        sid = self.st.anlegen("Hallo.", zweck="x")
        self.c.get("/api/sprache/naechster")
        r = self.c.post("/api/sprache/ergebnis", json={"id": sid, "ok": True, "mp3_b64": "kein base64!"}).json()
        self.assertFalse(r["ok"])
        self.assertEqual(self.st.get(sid)["status"], "fehlgeschlagen")
        self.assertFalse(self.c.post("/api/sprache/ergebnis", json={"id": "SP-gibts-nicht", "ok": False}).json()["ok"])

    def test_3_nur_administration(self):
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/sprache/naechster"), "administration")


if __name__ == "__main__":
    unittest.main()
