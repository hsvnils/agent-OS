"""KUNDEN_CHECKLISTE C1/C2: Gespraechsleitfaden am Kunden -- auch ohne Vorgang anlegen, laufend speichern (Kopf, Antworten,
abhaken), Pflichtbloecke und Fortschritt, Abschluss = PDF in der Firmenakte (Fassungen), Uebernahme ins Briefing nur mit
Vorschau/Bestaetigung und nur fuer Vorgaenge desselben Kunden; leere Checkliste als PDF/Word aus derselben Fragenliste."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from orchestrator.core.firmenakte import Firmenakte
from orchestrator.core.konzept import KonzeptStore
from orchestrator.core.leitfaden import BLOECKE, FRAGEN, LeitfadenStore, dokument_docx, dokument_pdf
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_postings import REEL


def _text(b: bytes) -> str:
    from pypdf import PdfReader
    return " ".join(s.extract_text() for s in PdfReader(io.BytesIO(b)).pages)


class TestLeitfaden(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, self.st, self.k, self.ap = _stores()
        self.lf = LeitfadenStore(self.bh, self.ks)

    def test_1_anlegen_ohne_vorgang_und_laufend_speichern(self):
        lid = self.lf.anlegen(self.k, titel="Erstgespräch")["id"]
        self.lf.kopf(lid, {"gespraechspartner": "Anna Muster", "unbekannt": "x"})
        self.lf.antwort(lid, "B1", text="Mehr Reservierungen")
        self.lf.antwort(lid, "B1", text="Mehr Reservierungen am Wochenende")      # letzter Stand gilt
        self.lf.antwort(lid, "F1", erledigt=True)
        g = self.lf.get(lid)
        self.assertEqual(g["antworten"]["B1"]["text"], "Mehr Reservierungen am Wochenende")
        self.assertTrue(g["antworten"]["F1"]["erledigt"])
        self.assertEqual(g["gespraechspartner"], "Anna Muster")
        self.assertEqual(g["fortschritt"], {"bloecke": len(BLOECKE), "fertig": 2})
        self.assertEqual([p[0] for p in g["offen_pflicht"]], ["C", "D", "I", "J"])   # B beantwortet
        self.assertEqual([x["id"] for x in self.lf.liste(self.k)], [lid])
        for falsch in (lambda: self.lf.antwort(lid, "Z9", text="x"), lambda: self.lf.antwort(lid, "B1"),
                       lambda: self.lf.kopf(lid, {"datum": "morgen"})):
            with self.assertRaises(ValueError):
                falsch()
        with self.assertRaises(KeyError):
            self.lf.anlegen("K-99999")
        with self.assertRaises(KeyError):
            self.lf.antwort("LF-00000000", "B1", text="x")

    def test_2_abschliessen_pdf_in_der_akte_mit_fassungen(self):
        lid = self.lf.anlegen(self.k, titel="Herbst")["id"]
        with self.assertRaises(ValueError):
            self.lf.abschliessen(lid)                                              # leer
        self.lf.antwort(lid, "D2", text="Du, locker, mit Humor")
        self.lf.kopf(lid, {"notizen": "Rückruf Freitag"})
        r = self.lf.abschliessen(lid)
        self.assertEqual(r["fassung"], 1)
        doc = Firmenakte(self.bh, self.ks).dokument(r["akte_id"])
        self.assertEqual((doc["firma"], doc["art"]), (self.k, "leitfaden"))
        pdf = (self.bh.dir / doc["dateien"][0]["pfad"]).read_bytes()
        t = _text(pdf)
        for erwartet in ("Gesprächsleitfaden", "Du, locker, mit Humor", "Rückruf Freitag", "Brand X GmbH", "Noch offene Pflichtblöcke"):
            self.assertIn(erwartet, t)
        self.assertIn("Pflichtblöcke offen", doc["notiz"])
        self.lf.antwort(lid, "B1", text="Bekanntheit")
        self.assertEqual(self.lf.abschliessen(lid)["fassung"], 2)                  # neue Fassung, alte bleibt
        self.assertEqual(len([d for d in Firmenakte(self.bh, self.ks).akte(self.k) if d["art"] == "leitfaden"]), 2)

    def test_3_uebernahme_ins_briefing(self):
        an = self.st.anlegen({"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst", "positionen": [REEL]})["nummer"]
        kz = KonzeptStore(self.bh, Path(tempfile.mkdtemp()))
        kz.briefing(an, {"ziel": "alt"})
        lid = self.lf.anlegen(self.k)["id"]
        self.lf.antwort(lid, "B1", text="Mehr Reservierungen")
        self.lf.antwort(lid, "B2", text="Reservierungen pro Woche")
        self.lf.antwort(lid, "C1", text="25-40, Hamburg")
        self.lf.antwort(lid, "A1", text="Restaurant")                              # ohne Briefing-Feld
        self.assertEqual([x["nummer"] for x in self.lf.vorgaenge(self.k)], [an])
        v = self.lf.uebernahme_vorschau(lid, an, kz)
        felder = {f["feld"]: f for f in v["felder"]}
        self.assertEqual(set(felder), {"ziel", "zielgruppe"})
        self.assertEqual((felder["ziel"]["alt"], felder["ziel"]["neu"]), ("alt", "Mehr Reservierungen\nReservierungen pro Woche"))
        self.assertEqual(kz.mappe(an)["briefing"]["ziel"], "alt")                 # Vorschau schreibt nichts
        r = self.lf.uebernehmen(lid, an, kz, felder=["zielgruppe"])
        self.assertEqual(r["felder"], ["zielgruppe"])
        b = kz.mappe(an)["briefing"]
        self.assertEqual((b["ziel"], b["zielgruppe"]), ("alt", "25-40, Hamburg"))
        self.assertEqual(self.lf.get(lid)["uebernahmen"][0]["vorgang"], an)
        # anderer Kunde -> abgelehnt
        k2 = self.ks.firma_anlegen({"name": "Andere GmbH", "strasse": "A 1", "plz": "20095", "ort": "Hamburg"})["nummer"]
        lid2 = self.lf.anlegen(k2)["id"]
        self.lf.antwort(lid2, "B1", text="x")
        with self.assertRaises(ValueError):
            self.lf.uebernahme_vorschau(lid2, an, kz)

    def test_4_leere_dokumente_aus_derselben_fragenliste(self):
        t = _text(dokument_pdf())
        self.assertIn("Kunden-Checkliste", t)
        for _, titel, _, _ in BLOECKE:
            self.assertIn(titel, t)
        self.assertEqual(len(FRAGEN), sum(len(fs) for *_, fs in BLOECKE))
        z = zipfile.ZipFile(io.BytesIO(dokument_docx()))
        doc = z.read("word/document.xml").decode()
        self.assertIn("Was macht ihr", doc)
        self.assertNotIn("word/media/logo.jpg", z.namelist())                       # ohne Logo kein Bild-Verweis
        self.assertNotIn("rIdLogo", doc)


class TestLeitfadenApi(ApiBasis):
    def test_a1_ablauf(self):
        self.assertEqual(len(self.c.get("/api/crm/leitfaden/fragen").json()["bloecke"]), len(BLOECKE))
        self.assertEqual(self.c.get("/api/crm/leitfaden/vorlage.pdf").content[:4], b"%PDF")
        self.assertEqual(self.c.get("/api/crm/leitfaden/vorlage.docx").content[:2], b"PK")
        self.assertEqual(self.c.get("/api/crm/leitfaden/vorlage.exe").status_code, 404)
        r = self.c.post(f"/api/crm/kunden/{self.k}/leitfaeden", json={"titel": "Erstgespräch"}).json()
        self.assertTrue(r["ok"], r)
        lid = r["id"]
        self.assertTrue(self.c.post(f"/api/crm/leitfaden/{lid}", json={"frage": "B1", "text": "Bekanntheit"}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/crm/leitfaden/{lid}", json={"frage": "B2", "erledigt": True}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/crm/leitfaden/{lid}", json={"kopf": {"gespraechspartner": "Anna"}}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/leitfaden/{lid}", json={"frage": "B1"}).json()["ok"])
        d = self.c.get(f"/api/crm/leitfaden/{lid}").json()
        self.assertEqual(d["leitfaden"]["antworten"]["B1"]["text"], "Bekanntheit")
        self.assertEqual(d["firma"]["nummer"], self.k)
        a = self.c.post(f"/api/crm/leitfaden/{lid}/abschliessen", json={}).json()
        self.assertTrue(a["ok"], a)
        self.assertEqual(self.c.get(f"/api/crm/akte/{a['akte_id']}/datei").content[:4], b"%PDF")
        self.assertEqual(self.c.get(f"/api/crm/kunden/{self.k}/leitfaeden").json()["leitfaeden"][0]["fassungen"][0]["fassung"], 1)
        self.assertEqual(self.c.get("/api/crm/leitfaden/LF-00000000").status_code, 404)
        an = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "T",
                                                               "positionen": [REEL]}}).json()
        nr = an.get("nummer") or (an.get("angebot") or {}).get("nummer")
        v = self.c.get(f"/api/crm/leitfaden/{lid}/uebernahme?vorgang={nr}").json()
        self.assertTrue(v["ok"], v)
        self.assertFalse(self.c.post(f"/api/crm/leitfaden/{lid}/uebernahme", json={"vorgang": nr}).json()["ok"])  # ohne Bestaetigung
        u = self.c.post(f"/api/crm/leitfaden/{lid}/uebernahme", json={"vorgang": nr, "bestaetigt": True}).json()
        self.assertTrue(u["ok"], u)
        self.assertEqual(u["felder"], ["ziel"])


if __name__ == "__main__":
    unittest.main()
