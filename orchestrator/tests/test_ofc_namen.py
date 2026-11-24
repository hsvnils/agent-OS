"""OFC_ROADMAP O2: Namen je Ticket aendern, Ticket-Datei umbenennen -- Vorschau schreibt nichts, Umbenennen mit Zusatz A/B,
Namenswechsel, Kollision (auch Gross/Klein), Sonderzeichen, Datei fehlt, Rueckgaengig, nie loeschen/ueberschreiben,
Import danach ohne Aenderung, Endpunkte nur CEO mit Bestaetigung. Fixtures ohne echte Namen."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core.ofc_store import (OfcStore, datei_fuer_name, import_anwenden, import_plan, name_sauber, namen_plan,
                                         namen_setzen, namen_vorschlaege, rueckgaengig)
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_store import _saison


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = _saison(self.d)
        self.h = self.s / "HSV vs FCB"
        (self.h / "262236181415-3B-Dora.pdf").write_text("Ticketnummer: 262236181415-3", encoding="utf-8")
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, self.s)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def dateien(self):
        return sorted(p.name for p in self.h.iterdir())


class TestNamen(_Basis):
    def test_1_sauber_und_dateiname(self):
        self.assertEqual(name_sauber("  Jörg /Maria:  Müller-Groß. "), "Jörg Maria Müller-Groß")
        self.assertEqual(name_sauber('a*b?c"d<e>f|g\\h'), "a b c d e f g h")
        self.assertEqual(name_sauber("../.."), "")
        self.assertEqual(datei_fuer_name("1-2", "262236181415-3B-Alt.pdf", "Neu"), "262236181415-3B-Neu.pdf")
        self.assertEqual(datei_fuer_name("262236181415-1", "", ""), "262236181415-1.pdf")
        self.assertEqual(datei_fuer_name("162236525621-7", "162236525621-7.pdf", "Emil"), "162236525621-7-Emil.pdf")

    def test_2_vorschau_schreibt_nichts_dann_umbenennen_und_rueckgaengig(self):
        vorher, n = self.dateien(), len(self.st.eintraege())
        v = namen_plan(self.st, "262236181415-1", "Anna Neu", self.s)
        self.assertEqual((v["ok"], v["umbenennen"], v["datei_alt"], v["datei_neu"]),
                         (True, True, "262236181415-1-Anna.pdf", "262236181415-1-Anna Neu.pdf"))
        self.assertEqual((self.dateien(), len(self.st.eintraege())), (vorher, n))              # Dry-Run
        r = namen_setzen(self.st, "262236181415-1", "Anna Neu", self.s, von="test")
        self.assertTrue(r["gespeichert"])
        self.assertIn("262236181415-1-Anna Neu.pdf", self.dateien())
        self.assertNotIn("262236181415-1-Anna.pdf", self.dateien())
        self.assertEqual(len(self.dateien()), len(vorher))                                    # nichts geloescht/kopiert
        t = self.st.stand()["tickets"]["262236181415-1"]
        self.assertEqual((t["name"], t["datei"], t["letzte_aenderung"]["name_alt"]), ("Anna Neu", "262236181415-1-Anna Neu.pdf", "Anna"))
        self.assertEqual(import_plan(self.st, self.s)["tickets_geaendert"], 0)               # Import sieht keine Aenderung
        r = rueckgaengig(self.st, "262236181415-1", self.s)
        self.assertTrue(r["gespeichert"])
        self.assertEqual(self.dateien(), vorher)
        self.assertEqual(self.st.stand()["tickets"]["262236181415-1"]["name"], "Anna")
        e = self.st.eintraege()[-1]
        self.assertEqual((e["typ"], e["daten"]["rueckgaengig"]), ("ofc_name", True))

    def test_3_zusatz_bleibt_und_name_leeren(self):
        namen_setzen(self.st, "262236181415-3", "Ernst", self.s)
        self.assertIn("262236181415-3B-Ernst.pdf", self.dateien())
        namen_setzen(self.st, "262236181415-3", "", self.s)
        self.assertIn("262236181415-3B.pdf", self.dateien())
        self.assertEqual(self.st.stand()["tickets"]["262236181415-3"]["name"], "")

    def test_4_kollision_auch_gross_klein_nichts_geaendert(self):
        (self.h / "262236181415-1-bob.pdf").write_text("fremd", encoding="utf-8")
        vorher, n = self.dateien(), len(self.st.eintraege())
        r = namen_setzen(self.st, "262236181415-1", "Bob", self.s)
        self.assertFalse(r["ok"]); self.assertIn("schon", r["hinweis"])
        self.assertEqual((self.dateien(), len(self.st.eintraege())), (vorher, n))
        self.assertEqual((self.h / "262236181415-1-bob.pdf").read_text(encoding="utf-8"), "fremd")   # nicht ueberschrieben
        r = namen_setzen(self.st, "262236181415-1", "anna", self.s)                         # nur Gross/Klein der eigenen Datei
        self.assertTrue(r["gespeichert"]); self.assertIn("262236181415-1-anna.pdf", self.dateien())

    def test_5_datei_fehlt_oder_verschoben(self):
        r = namen_setzen(self.st, "262236181415-2", "Carla", self.s)                        # in der Rechnung, keine Datei
        self.assertTrue(r["gespeichert"]); self.assertFalse(r["umbenennen"]); self.assertIn("Keine Ticket-Datei", r["hinweis"])
        (self.h / "262236181415-1-Anna.pdf").rename(self.d / "weg.pdf")                     # von Hand weggenommen
        n = len(self.st.eintraege())
        r = namen_setzen(self.st, "262236181415-1", "Neu", self.s)
        self.assertFalse(r["ok"]); self.assertIn("Ordner einlesen", r["hinweis"])
        self.assertEqual(len(self.st.eintraege()), n)
        self.assertFalse(namen_plan(self.st, "gibtsnicht", "x", self.s)["ok"])
        self.assertIn("Keine Änderung", namen_plan(self.st, "262236189999-1", "Ben", self.s)["hinweis"])
        self.assertFalse(rueckgaengig(self.st, "262236189999-1", self.s)["ok"])

    def test_6_rename_fehler_und_vorschlaege(self):
        with mock.patch("orchestrator.core.ofc_store.os.rename", side_effect=PermissionError("nein")):
            n = len(self.st.eintraege())
            r = namen_setzen(self.st, "262236181415-1", "Neu", self.s)
            self.assertFalse(r["ok"]); self.assertIn("PermissionError", r["hinweis"])
            self.assertEqual(len(self.st.eintraege()), n)
        v = namen_vorschlaege(self.st, [{"name": "Max Beispiel"}, {"name": "anna"}])
        self.assertEqual(v[:2], ["Max Beispiel", "anna"])
        self.assertNotIn("Anna", v)                                                          # Dublette (Gross/Klein)
        self.assertIn("Dora", v)
        src = Path(ofc.__file__).with_name("ofc_store.py").read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "remove(", "replace("):
            self.assertNotIn(verboten, src, verboten)                                       # nie loeschen/ueberschreiben


class TestApi(ApiBasis):
    def test_7_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            _saison(Path(d))
            self.c.post("/api/ofc/import", json={"bestaetigt": True})
            v = self.c.get("/api/ofc/ticket/262236181415-1/name/vorschau", params={"name": "Neu"}).json()
            self.assertEqual(v["datei_neu"], "262236181415-1-Neu.pdf")
            self.assertFalse(self.c.post("/api/ofc/ticket/262236181415-1/name", json={"name": "Neu"}).json()["ok"])
            self.assertTrue((Path(d) / "Tickets 26-27" / "HSV vs FCB" / "262236181415-1-Anna.pdf").exists())
            r = self.c.post("/api/ofc/ticket/262236181415-1/name", json={"name": "Neu", "bestaetigt": True}).json()
            self.assertTrue(r["gespeichert"])
            self.assertTrue((Path(d) / "Tickets 26-27" / "HSV vs FCB" / "262236181415-1-Neu.pdf").exists())
            v = self.c.get("/api/ofc/ticket/262236181415-1/name/vorschau", params={"rueckgaengig": 1}).json()
            self.assertEqual((v["name_neu"], v["datei_neu"]), ("Anna", "262236181415-1-Anna.pdf"))
            r = self.c.post("/api/ofc/ticket/262236181415-1/name", json={"bestaetigt": True, "rueckgaengig": True}).json()
            self.assertTrue(r["gespeichert"])
            with mock.patch.object(self.w, "_google", side_effect=RuntimeError("x")):
                n = self.c.get("/api/ofc/namen").json()
                self.assertEqual((n["mitglieder_ok"], "Anna" in n["namen"]), (False, True))
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/namen").status_code, 403)
                self.assertEqual(self.c.get("/api/ofc/ticket/262236181415-1/name/vorschau").status_code, 403)
                self.assertEqual(self.c.post("/api/ofc/ticket/262236181415-1/name",
                                             json={"name": "x", "bestaetigt": True}).status_code, 403)
