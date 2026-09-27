"""Self-Checks Backoffice-Auftraege: Store + LUNA-OS-API (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 2) -- offline."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.auftraege import AuftragStore, briefing_zeilen


def _store():
    return AuftragStore(Path(tempfile.mkdtemp()) / "log.jsonl")


class TestAuftragStore(unittest.TestCase):
    def test_1_lebenszyklus(self):
        s = _store()
        aid = s.anlegen("Fasse die Recherche zusammen", art="zusammenfassung")
        self.assertEqual(s.get(aid)["status"], "neu")
        a = s.naechster()
        self.assertEqual((a["id"], a["status"]), (aid, "in_arbeit"))
        self.assertIsNone(s.naechster())                                   # nichts mehr offen
        s.fertig(aid, ergebnis="- Punkt 1", modell="qwen3:14b", dauer_s=12.34)
        a = s.get(aid)
        self.assertEqual((a["status"], a["ergebnis"], a["dauer_s"]), ("fertig", "- Punkt 1", 12.3))
        self.assertEqual([v["event"] for v in a["verlauf"]], ["neu", "in_arbeit", "fertig"])

    def test_2_reihenfolge_aelteste_zuerst_und_kurz_id(self):
        s = _store()
        a1 = s.anlegen("erst")
        a2 = s.anlegen("dann")
        self.assertEqual(s.naechster()["id"], a1)
        self.assertEqual(s.get("#" + a2.split("-")[-1])["id"], a2)        # per Suffix auffindbar

    def test_3_leer_und_unbekannte_art(self):
        s = _store()
        with self.assertRaises(ValueError):
            s.anlegen("   ")
        self.assertEqual(s.get(s.anlegen("x", art="quatsch"))["art"], "sonstiges")
        self.assertFalse(s.fertig("A-gibt-es-nicht", ergebnis="x"))

    def test_4_haengende_zurueck_auf_neu(self):
        s = _store()
        aid = s.anlegen("haengt")
        s.naechster()
        with mock.patch("orchestrator.core.auftraege.datetime") as dt:
            dt.now.return_value = datetime.now() + timedelta(hours=3)
            dt.fromisoformat = datetime.fromisoformat
            self.assertEqual(s.aufraeumen(stunden=2), 1)
        self.assertEqual(s.get(aid)["status"], "neu")

    def test_5_briefing_nur_nachts_gemeldete(self):
        s = _store()
        a = s.anlegen("Nachtarbeit"); s.naechster(); s.fertig(a, ergebnis="ok", meldung="briefing")
        b = s.anlegen("Tagarbeit"); s.naechster(); s.fertig(b, ergebnis="ok", meldung="einzeln")
        c = s.anlegen("Kaputt"); s.naechster(); s.fehlschlag(c, grund="Antwort unbrauchbar", meldung="briefing")
        zeilen = briefing_zeilen(s, datetime.now() - timedelta(hours=1))
        self.assertEqual(len(zeilen), 2)
        self.assertTrue(any("Nachtarbeit" in z and "erledigt" in z for z in zeilen))
        self.assertTrue(any("Kaputt" in z and "fehlgeschlagen" in z for z in zeilen))


class TestBackofficeApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.notifications import Notifications
        self.w = webapp
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = (webapp.backoffice, webapp.notifications)
        webapp.backoffice = AuftragStore(self.tmp / "b.jsonl")
        webapp.notifications = Notifications(self.tmp / "n.jsonl")
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.backoffice, self.w.notifications = self.orig

    def _auftrag_holen(self):
        r = self.c.post("/api/backoffice/auftrag", json={"aufgabe": "Bewerte Antrag X", "art": "bewertung"}).json()
        self.assertTrue(r["ok"])
        a = self.c.get("/api/backoffice/naechster").json()["auftrag"]
        self.assertEqual((a["id"], a["status"]), (r["id"], "in_arbeit"))
        return a

    def test_1_tagsueber_einzelmeldung_mit_vollem_ergebnis(self):
        a = self._auftrag_holen()
        with mock.patch.object(self.w, "_backoffice_nacht", return_value=False):
            r = self.c.post("/api/backoffice/ergebnis", json={"id": a["id"], "ok": True, "ergebnis": "Empfehlung: freigeben",
                                                              "zweitmeinung": "Teile die Empfehlung.", "modell": "qwen3:14b"}).json()
        self.assertEqual(r, {"ok": True, "meldung": "einzeln"})
        n = self.w.notifications.pending()
        self.assertEqual(len(n), 1)
        self.assertIn(f"#{a['kurz']} erledigt", n[0]["text"])
        self.assertIn("Empfehlung: freigeben", n[0]["detail"])
        self.assertIn("Zweitmeinung (Gemini)", n[0]["detail"])
        self.assertEqual(self.w.backoffice.get(a["id"])["status"], "fertig")

    def test_2_nachts_nur_briefing(self):
        a = self._auftrag_holen()
        with mock.patch.object(self.w, "_backoffice_nacht", return_value=True):
            r = self.c.post("/api/backoffice/ergebnis", json={"id": a["id"], "ok": False, "grund": "Antwort unbrauchbar"}).json()
        self.assertEqual(r["meldung"], "briefing")
        self.assertEqual(self.w.notifications.pending(), [])
        self.assertEqual(self.w.backoffice.get(a["id"])["status"], "fehlgeschlagen")

    def test_3_unbekannt_und_leere_warteschlange(self):
        self.assertFalse(self.c.post("/api/backoffice/ergebnis", json={"id": "A-x", "ok": True}).json()["ok"])
        self.assertIsNone(self.c.get("/api/backoffice/naechster").json()["auftrag"])

    def test_4_nachtfenster(self):
        self.assertTrue(self.w._backoffice_nacht(datetime(2026, 9, 27, 3, 0)))
        self.assertFalse(self.w._backoffice_nacht(datetime(2026, 9, 27, 6, 0)))
        self.assertFalse(self.w._backoffice_nacht(datetime(2026, 9, 27, 0, 59)))

    def test_5_werkzeug_auftrag_details(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        a = self._auftrag_holen()
        self.w.backoffice.fertig(a["id"], ergebnis="Langes Ergebnis")
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=None, repo_root=None,
                          leak_secrets=[], backoffice=self.w.backoffice)
        out = run_tool("auftrag_details", {"auftrag_id": "#" + a["kurz"]}, ctx)
        self.assertEqual((out["status"], out["ergebnis"]), ("fertig", "Langes Ergebnis"))


if __name__ == "__main__":
    unittest.main()
