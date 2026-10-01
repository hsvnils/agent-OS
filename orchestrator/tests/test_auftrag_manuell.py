"""KUNDEN_FINANZEN Etappe 31: Auftrag ohne Angebot (CEO 2026-10-02: „Nicht jeder Auftrag braucht ein Angebot“)."""
import io
import unittest

from orchestrator.core.beauftragung import AuftragBuch, auftrag_mail_text
from orchestrator.core.buchhaltung import jetzt
from orchestrator.tests.test_angebote import POS, ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date().isoformat()


class TestAnlegen(unittest.TestCase):
    def test_1_ohne_angebot(self):
        bh, ks, st, k, ap = _stores()
        ab = AuftragBuch(bh, ks, st)
        for daten, fehler in (({"firma": k, "titel": "", "positionen": POS}, "Titel"),
                              ({"firma": k, "titel": "X", "positionen": []}, "Position"),
                              ({"firma": k, "titel": "X", "positionen": POS, "rabatt_prozent": "95"}, "Rabatt")):
            with self.assertRaisesRegex(ValueError, fehler):
                ab.anlegen(daten)
        with self.assertRaises(KeyError):
            ab.anlegen({"firma": "K-09999", "titel": "X", "positionen": POS})
        with self.assertRaisesRegex(ValueError, "Ende liegt vor"):
            ab.anlegen({"firma": k, "titel": "X", "positionen": POS}, leistung_von="2026-10-10", leistung_bis="2026-10-01")
        r = ab.anlegen({"firma": k, "ansprechpartner": ap, "titel": "Kampagne Herbst", "positionen": POS,
                        "zahlung": {"ziel_tage": "14", "vorkasse": {"art": "prozent", "wert": "50"}}},
                       leistung_von="2026-10-05", notiz="per Telefon beauftragt")
        a = ab.auftrag(r["nummer"])
        self.assertTrue(r["nummer"].startswith("AB-"))
        self.assertEqual((a["angebot"], a["status"], a["titel"], a["summe_cent"], a["vorkasse_cent"]),
                         ("", "beauftragt", "Kampagne Herbst", 102000, 51000))
        self.assertEqual((a["leistung_von"], a["notiz"]), ("2026-10-05", "per Telefon beauftragt"))

    def test_2_bestaetigung_ohne_angebotsbezug(self):
        bh, ks, st, k, ap = _stores()
        ab = AuftragBuch(bh, ks, st)
        nr = ab.anlegen({"firma": k, "titel": "Shooting", "positionen": POS, "layout": "standard"})["nummer"]
        a = ab.auftrag(nr)
        betreff, text = auftrag_mail_text(a, None, FD)
        self.assertNotIn("Angebot", text)
        self.assertIn("über 1.020,00 €", text)
        from pypdf import PdfReader
        pdf = ab.pdf(nr, FD)
        inhalt = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
        self.assertIn(nr, inhalt)
        self.assertNotIn("Angebot", inhalt)
        for layout in ("hanserautisch", "standard"):                                      # beide Vorlagen
            n2 = ab.anlegen({"firma": k, "titel": "Shooting", "positionen": POS, "layout": layout})["nummer"]
            t = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(ab.pdf(n2, FD))).pages)
            self.assertNotIn("Angebot:", t)
            self.assertNotIn("Angebots ", t)


class TestApi(ApiBasis):
    def test_a1_anlegen_rechnung_zeit(self):
        r = self.c.post("/api/crm/auftraege", json={"auftrag": {"firma": self.k, "titel": "Direktauftrag", "positionen": POS},
                                                    "leistung_von": HEUTE}).json()
        self.assertTrue(r["ok"], r)
        nr = r["nummer"]
        d = self.c.get(f"/api/crm/auftraege/{nr}").json()["auftrag"]
        self.assertEqual((d["angebot"], d["summe_cent"]), ("", 102000))
        self.assertIn(nr, [x["nummer"] for x in self.c.get("/api/crm/auftraege").json()["auftraege"]])
        re_ = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()
        self.assertTrue(re_["ok"], re_)                                                      # Rechnung wie gewohnt
        self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"})
        self.assertTrue(self.c.post("/api/finanzen/zeit/start", json={"auftrag": nr}).json()["ok"])
        self.assertFalse(self.c.post("/api/crm/auftraege", json={"auftrag": {"firma": self.k, "titel": ""}}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
