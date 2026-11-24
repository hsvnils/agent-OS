"""OFC_ROADMAP O6: Abschluss nur wenn bezahlt + Datum vorbei (sonst nur „trotzdem“), Verschieben mit Kollision, wieder oeffnen,
3-Tage-Hinweis, offene Posten mit Text zum Kopieren, Saisonsummen, Statistik je Mitglied, CSV/PDF (A4 hochkant), nur CEO.
Fixtures ohne echte Daten."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core import ofc_eingang as oe
from orchestrator.core import ofc_saison as osa
from orchestrator.core.ofc_store import OfcStore, import_anwenden, uebersicht
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_eingang import _erhalten, _ordner

NACH = date(2026, 12, 1)                     # nach dem Spieltag 28.11.2026


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = self.d / "Tickets 26-27"
        _ordner(self.s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
        _ordner(self.s, "HSV vs SGE", "262236187777", "Eintracht Frankfurt", ["Erika Muster", "Carla"])
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, self.s)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def bezahlen_fcb(self):
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00")])
        oe.eingang_anwenden(self.st, [_erhalten("Erika Muster", "35,00", "Bayern", tc="2EE22222EE2222222", mid="<2@p>")])


class TestAbschluss(_Basis):
    def test_1_nur_wenn_bezahlt_und_vorbei(self):
        sp = {x["id"]: x for x in uebersicht(self.st, heute=NACH)["spiele"]}
        self.assertEqual(sp["HSV vs FCB"]["status"], "vorbei")
        r = osa.abschliessen(self.st, "HSV vs FCB", self.s, heute=NACH)
        self.assertFalse(r["ok"]); self.assertIn("Noch nicht", r["hinweis"])
        self.assertTrue((self.s / "HSV vs FCB").is_dir())
        self.bezahlen_fcb()
        self.assertEqual({x["id"]: x["status"] for x in uebersicht(self.st, heute=NACH)["spiele"]}["HSV vs FCB"], "abschliessbar")
        self.assertEqual({x["id"]: x["status"] for x in uebersicht(self.st, heute=date(2026, 11, 20))["spiele"]}["HSV vs FCB"], "offen")
        v = osa.abschluss_plan(self.st, "HSV vs FCB", self.s, heute=NACH)
        self.assertEqual((v["von"], v["nach"], v["abschliessbar"]), ("HSV vs FCB", "Abgeschlossen/HSV vs FCB", True))
        self.assertTrue((self.s / "HSV vs FCB").is_dir())                                 # Vorschau verschiebt nichts
        r = osa.abschliessen(self.st, "HSV vs FCB", self.s, heute=NACH)
        self.assertTrue(r["verschoben"])
        self.assertTrue((self.s / "Abgeschlossen" / "HSV vs FCB" / "Rechnung.pdf").exists())
        self.assertFalse((self.s / "HSV vs FCB").exists())
        sp = {x["id"]: x for x in uebersicht(self.st, heute=NACH)["spiele"]}
        self.assertEqual((sp["HSV vs FCB"]["status"], sp["HSV vs FCB"]["pfad"]), ("abgeschlossen", "Abgeschlossen/HSV vs FCB"))
        self.assertEqual(import_anwenden(self.st, self.s)["spiele_geaendert"], [])         # Import sieht keine Aenderung
        r = osa.abschliessen(self.st, "HSV vs FCB", self.s, zurueck=True)
        self.assertTrue(r["verschoben"]); self.assertTrue((self.s / "HSV vs FCB").is_dir())

    def test_2_trotzdem_und_kollision(self):
        r = osa.abschliessen(self.st, "HSV vs SGE", self.s, trotzdem=True, heute=date(2026, 11, 1))
        self.assertTrue(r["verschoben"])
        (self.s / "HSV vs FCB" / "x").mkdir()
        ab = self.s / "Abgeschlossen" / "hsv vs fcb"
        ab.mkdir()                                                                       # gleicher Name (Gross/Klein) da
        r = osa.abschliessen(self.st, "HSV vs FCB", self.s, trotzdem=True, heute=NACH)
        self.assertFalse(r["ok"]); self.assertIn("gibt es schon", r["hinweis"])
        self.assertTrue((self.s / "HSV vs FCB" / "x").is_dir())
        self.assertFalse(osa.abschliessen(self.st, "gibtsnicht", self.s)["ok"])
        self.assertFalse(osa.abschluss_plan(self.st, "HSV vs SGE", self.s)["ok"])          # schon abgeschlossen
        src = Path(osa.__file__).read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "rmdir", "os.remove", "os.replace", "shutil"):
            self.assertNotIn(verboten, src, verboten)

    def test_3_hinweis_drei_tage_vorher(self):
        h = {x["id"]: x["hinweise"] for x in uebersicht(self.st, heute=date(2026, 11, 26))["spiele"]}
        self.assertEqual(h["HSV vs FCB"][0], "Spiel in 2 Tag(en): 2 unbezahlt")
        h = {x["id"]: x["hinweise"] for x in uebersicht(self.st, heute=date(2026, 11, 20))["spiele"]}
        self.assertFalse(any(x.startswith("Spiel in") for x in h["HSV vs FCB"]))


class TestAuswertung(_Basis):
    def test_4_offene_posten_text_summen_statistik(self):
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00")])
        st = self.st.stand()
        po = {x["name"]: x for x in osa.offene_posten(st)}
        self.assertNotIn("Ben Beispiel", po)
        e = po["Erika Muster"]
        self.assertEqual((e["summe_cent"], len(e["posten"])), (7000, 2))
        self.assertIn("Hallo Erika", e["text"]); self.assertIn("70,00 €", e["text"]); self.assertIn("28.11.2026", e["text"])
        su = osa.saison_summen(st)
        self.assertEqual((su["eingekauft_cent"], su["eingenommen_cent"], su["offen_cent"], su["differenz_cent"], su["karten_bezahlt"]),
                         (14000, 3500, 10500, -10500, 1))
        stat = osa.statistik(st)
        top = stat["personen"][0]
        self.assertEqual((top["name"], top["karten"], top["spiele"]), ("Erika Muster", 2, 2))
        self.assertEqual(stat["wettbewerbe"], ["Liga"])

    def test_5_abgeschlossene_nur_auf_wunsch(self):
        osa.abschliessen(self.st, "HSV vs SGE", self.s, trotzdem=True, heute=NACH)
        st = self.st.stand()
        self.assertEqual(len(osa.offene_posten(st)), 2)                                    # Erika, Ben (nur FCB)
        self.assertEqual(sum(len(x["posten"]) for x in osa.offene_posten(st, alle=True)), 4)

    def test_6_export_csv_pdf(self):
        st = self.st.stand()
        c = osa.export_csv(st).decode("utf-8-sig").splitlines()
        self.assertTrue(c[0].startswith("Saison;Spiel;Datum")); self.assertEqual(len(c), 5)
        self.assertIn("Erika Muster", c[1])
        pdf = osa.export_pdf(st, saison_name="26-27")
        self.assertTrue(pdf.startswith(b"%PDF"))
        from pypdf import PdfReader
        import io
        s = PdfReader(io.BytesIO(pdf)).pages[0].mediabox
        self.assertLess(float(s.width), float(s.height))                                  # hochkant


class TestApi(ApiBasis):
    def test_7_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            _ordner(Path(d) / "Tickets 26-27", "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
            self.c.post("/api/ofc/import", json={"bestaetigt": True})
            s = self.c.get("/api/ofc/saison").json()
            self.assertEqual((s["summen"]["karten"], len(s["posten"])), (2, 2))
            self.assertTrue(self.c.get("/api/ofc/export.pdf").content.startswith(b"%PDF"))
            self.assertIn("Ticketnummer", self.c.get("/api/ofc/export.csv").content.decode("utf-8-sig"))
            v = self.c.get("/api/ofc/spiel/HSV vs FCB/abschluss/vorschau").json()
            self.assertEqual(v["nach"], "Abgeschlossen/HSV vs FCB")
            self.assertFalse(self.c.post("/api/ofc/spiel/HSV vs FCB/abschluss", json={}).json()["ok"])
            r = self.c.post("/api/ofc/spiel/HSV vs FCB/abschluss", json={"bestaetigt": True, "trotzdem": True}).json()
            self.assertTrue(r["verschoben"])
            r = self.c.post("/api/ofc/spiel/HSV vs FCB/abschluss", json={"bestaetigt": True, "zurueck": True}).json()
            self.assertTrue(r["verschoben"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                for url in ("/api/ofc/saison", "/api/ofc/export.csv", "/api/ofc/export.pdf", "/api/ofc/spiel/HSV vs FCB/abschluss/vorschau"):
                    self.assertEqual(self.c.get(url).status_code, 403, url)
                self.assertEqual(self.c.post("/api/ofc/spiel/HSV vs FCB/abschluss", json={"bestaetigt": True}).status_code, 403)
