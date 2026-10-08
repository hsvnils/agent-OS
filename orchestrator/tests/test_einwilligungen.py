"""EINWILLIGUNG_AUFNAHMEN (CEO 2026-10-08): Einwilligung je Person mit Unterschrift (Apple Pencil) -> PDF A4 hochkant am
Auftrag, nur NAS (eigener Ordner, nicht Kette/Drive); Minderjaehrige, Kopie per Mail, Widerruf."""
import base64
import json
import os
import struct
import tempfile
import unittest
import zlib
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core.einwilligungen import EinwilligungStore, alter
from orchestrator.core.vertrag_entwuerfe import ENTWUERFE
from orchestrator.tests.test_angebote import FIRMA, ApiBasis


def _png(w=240, h=70) -> str:
    """Echtes RGBA-PNG (zufaellige Pixel = „Striche“) als Data-URL wie aus dem Canvas."""
    raw = b"".join(b"\x00" + os.urandom(w * 4) for _ in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw))
           + ch(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


VORLAGE = {"titel": ENTWUERFE["einwilligung"]["titel"], "paragraphen": ENTWUERFE["einwilligung"]["paragraphen"], "version": 1}
AUFTRAG = {"nummer": "AB-2026-0001", "titel": "Herbst", "firma": "K-00001"}
PERSON = {"vorname": "Anna", "nachname": "Muster", "strasse": "Weg 1", "plz": "20095", "ort": "Hamburg"}


class TestKern(unittest.TestCase):
    def setUp(self):
        self.st = EinwilligungStore(Path(tempfile.mkdtemp()) / "einwilligungen")

    def _erteilen(self, **x):
        e = {"person": PERSON, "zwecke": ["eigene_kanaele"], "unterschrift_person": _png()} | x
        return self.st.erteilen(AUFTRAG, e, vorlage=VORLAGE, firmendaten=FIRMA, kunde="Brand X GmbH", heute=date(2026, 10, 8))

    def test_1_erwachsen_pdf_hochkant(self):
        from pypdf import PdfReader
        import io
        r = self._erteilen(person=PERSON | {"geburtsdatum": "1990-05-01", "mail": "anna@example.com"}, zwecke=["eigene_kanaele", "name"])
        x = self.st.get(r["id"])
        self.assertEqual((x["auftrag"], x["minderjaehrig"], x["alter"], x["vorlage_version"]), ("AB-2026-0001", False, 36, 1))
        pdf = PdfReader(io.BytesIO(self.st.pdf(r["id"])))
        breite, hoehe = float(pdf.pages[0].mediabox.width), float(pdf.pages[0].mediabox.height)
        self.assertLess(breite, hoehe)                                           # A4 hochkant
        text = "".join(p.extract_text() for p in pdf.pages)
        self.assertIn("Anna Muster", text)
        self.assertIn("Brand X GmbH", text)
        self.assertIn("Herbst", text)
        self.assertNotIn("data:image", self.st.log.read_text(encoding="utf-8"))  # Unterschrift nie im Log
        self.assertEqual(json.loads(self.st.log.read_text(encoding="utf-8"))["sha256"], __import__("hashlib").sha256(self.st.pdf(r["id"])).hexdigest())

    def test_2_pruefungen(self):
        for x, grund in ((dict(person=PERSON | {"vorname": ""}), "Vor- und Nachnamen"),
                         (dict(person=PERSON | {"plz": ""}), "Anschrift"),
                         (dict(zwecke=["name"]), "Zweck"),
                         (dict(unterschrift_person=""), "unterschreiben"),
                         (dict(unterschrift_person="data:image/png;base64,AAAA"), "unterschreiben"),
                         (dict(person=PERSON | {"geburtsdatum": "2100-01-01"}), "Geburtsdatum")):
            with self.assertRaises(ValueError, msg=grund) as cm:
                self._erteilen(**x)
            self.assertIn(grund, str(cm.exception))
        self.assertEqual(self.st.liste(), [])                                    # nichts halb angelegt

    def test_3_minderjaehrige(self):
        self.assertEqual(alter("2011-10-09", date(2026, 10, 8)), 14)
        with self.assertRaises(ValueError):                                      # unter 16: Erziehungsberechtigte Pflicht
            self._erteilen(person=PERSON | {"geburtsdatum": "2011-05-01"})
        r = self._erteilen(person=PERSON | {"geburtsdatum": "2011-05-01"}, eltern_name="Petra Muster", unterschrift_eltern=_png())
        self.assertEqual((self.st.get(r["id"])["minderjaehrig"], self.st.get(r["id"])["eltern_name"]), (True, "Petra Muster"))
        r2 = self._erteilen(person=PERSON | {"geburtsdatum": "2016-01-01"}, unterschrift_person="", eltern_name="P. M.",
                            unterschrift_eltern=_png())                          # unter 14: nur die Eltern
        self.assertTrue(r2["id"])
        self.assertEqual(len(self.st.liste("ab-2026-0001")), 2)                  # mehrere Personen je Auftrag

    def test_4_widerruf_und_versand(self):
        r = self._erteilen()
        self.st.versendet(r["id"], "anna@example.com")
        with self.assertRaises(ValueError):
            self.st.widerrufen(r["id"], weg="")
        self.st.widerrufen(r["id"], datum="2026-11-01", weg="Mail", notiz="Reel 2 betroffen")
        x = self.st.get(r["id"])
        self.assertEqual((x["versendet"][0]["an"], x["widerruf"]["datum"], x["widerruf"]["weg"]), ("anna@example.com", "2026-11-01", "Mail"))
        with self.assertRaises(ValueError):
            self.st.widerrufen(r["id"], weg="Mail")                              # nur einmal


class TestApi(ApiBasis):
    def setUp(self):
        super().setUp()
        self.ew = EinwilligungStore(Path(tempfile.mkdtemp()) / "einwilligungen")   # nie der echte Ordner
        self._p = mock.patch.object(self.w, "_einwilligungen", return_value=self.ew)
        self._p.start()
        r = self.c.post("/api/crm/auftraege", json={"auftrag": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Dreh Herbst",
                                                                 "positionen": [{"beschreibung": "Reel", "menge": "1", "einheit": "",
                                                                                 "einzelpreis": "100"}]}}).json()
        self.nr = r["nummer"]

    def tearDown(self):
        self._p.stop()
        super().tearDown()

    def test_5_ablauf_am_auftrag(self):
        d = self.c.get(f"/api/crm/auftraege/{self.nr}/einwilligungen").json()
        self.assertEqual((d["einwilligungen"], d["projekt"], d["vorlage"]["version"]), ([], "Dreh Herbst", 0))   # Entwurf aus dem Code
        self.assertIn("Brand X", d["zwecke"]["kunde_kanaele"])
        body = {"person": PERSON | {"nachname": "Teststein", "mail": "anna@example.com"}, "zwecke": ["eigene_kanaele", "kunde_kanaele"], "unterschrift_person": _png()}
        r = self.c.post(f"/api/crm/auftraege/{self.nr}/einwilligungen", json=body).json()
        self.assertTrue(r["ok"], r)
        self.c.post(f"/api/crm/auftraege/{self.nr}/einwilligungen", json=body | {"person": PERSON | {"vorname": "Ben", "nachname": "Teststein"}})
        liste = self.c.get(f"/api/crm/auftraege/{self.nr}/einwilligungen").json()["einwilligungen"]
        self.assertEqual([x["person"]["vorname"] for x in liste], ["Anna", "Ben"])
        pdf = self.c.get(f"/api/crm/einwilligungen/{r['id']}/pdf")
        self.assertEqual((pdf.status_code, pdf.content[:4]), (200, b"%PDF"))
        v = self.c.get(f"/api/crm/einwilligungen/{r['id']}/versandvorschau").json()
        self.assertEqual(v["an"], "anna@example.com")
        self.assertIn("Dreh Herbst", v["betreff"])
        self.assertFalse(self.c.post(f"/api/crm/einwilligungen/{r['id']}/senden", json={"an": "anna@example.com", "betreff": "B", "text": "T"}).json()["ok"])
        s = self.c.post(f"/api/crm/einwilligungen/{r['id']}/senden", json={"an": "anna@example.com", "betreff": v["betreff"],
                                                                           "text": v["text"], "bestaetigt": True}).json()
        self.assertTrue(s["ok"], s)
        self.assertEqual(self.g.gesendet[-1]["anhaenge"][0][2], "application/pdf")
        w = self.c.post(f"/api/crm/einwilligungen/{r['id']}/widerruf", json={"weg": "Mail", "datum": "2026-10-08"}).json()
        self.assertTrue(w["ok"], w)
        self.assertEqual(self.c.get(f"/api/crm/auftraege/{self.nr}/einwilligungen").json()["einwilligungen"][0]["widerruf"]["weg"], "Mail")
        kette = json.dumps(self.w.kunden_store.bh.eintraege(), ensure_ascii=False)
        self.assertNotIn("Teststein", kette)                                     # Personendaten nicht in der Buchhaltungs-Kette

    def test_6_rechte(self):
        with mock.patch.object(self.w, "hat_modul", return_value=False):
            self.assertEqual(self.c.get(f"/api/crm/auftraege/{self.nr}/einwilligungen").status_code, 403)
            self.assertFalse(self.c.post(f"/api/crm/auftraege/{self.nr}/einwilligungen", json={}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
