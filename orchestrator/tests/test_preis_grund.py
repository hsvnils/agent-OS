"""Rechnung: Preis einer Position von Hand ueberschreiben (CEO 2026-10-05) -- nur mit Grund; vorheriger Preis und Grund
bleiben an der Position (Kette), TKP-Positionen werden dann nicht nachgerechnet, der Grund steht nicht auf dem PDF."""
import unittest

from orchestrator.core.angebote import _positionen
from orchestrator.tests.test_rechnungen import FD, _rs

TKP = {"beschreibung": "Reel", "menge": "1", "einzelpreis": "1600", "kontakte": 37000, "tkp_cent": 3000,
       "produktion_cent": 49000, "katalog_id": "reel_solo"}


class TestPreisGrund(unittest.TestCase):
    def test_1_grund_pflicht_und_gespeichert(self):
        with self.assertRaises(ValueError) as e:
            _positionen([{"beschreibung": "Reel", "einzelpreis": "1200", "preis_vorher_cent": 160000}])
        self.assertIn("Grund", str(e.exception))
        p = _positionen([{"beschreibung": "Reel", "einzelpreis": "1200", "preis_vorher_cent": 160000, "preis_grund": "Stammkunde"}])[0]
        self.assertEqual((p["einzelpreis_cent"], p["preis_vorher_cent"], p["preis_grund"]), (120000, 160000, "Stammkunde"))
        p = _positionen([{"beschreibung": "Reel", "einzelpreis": "1600", "preis_vorher_cent": 160000}])[0]
        self.assertNotIn("preis_grund", p)                                     # unveraendert: kein Grund noetig

    def test_2_tkp_wird_ueberschrieben_nicht_nachgerechnet(self):
        normal = _positionen([TKP | {"einzelpreis": "999"}])[0]
        self.assertEqual(normal["einzelpreis_cent"], 160000)                     # ohne Grund folgt der Preis dem TKP
        p = _positionen([TKP | {"einzelpreis": "1200", "preis_vorher_cent": 160000, "preis_grund": "Paketpreis vereinbart"}])[0]
        self.assertEqual((p["einzelpreis_cent"], p.get("kontakte")), (120000, None))

    def test_3_festschreiben_behaelt_grund_pdf_ohne_grund(self):
        bh, ks, rs, k, ap = _rs()
        from orchestrator.core.buchhaltung import jetzt
        eid = rs.entwurf_anlegen({"firma": k, "ansprechpartner": ap, "leistung_von": jetzt().date().isoformat(), "positionen": [
            {"beschreibung": "Reel", "menge": "1", "einzelpreis": "1200", "preis_vorher_cent": 160000, "preis_grund": "Stammkundenrabatt"}]})["entwurf_id"]
        nr = rs.festschreiben(eid, FD)["nummer"]
        r = rs.get(nr)
        self.assertEqual((r["positionen"][0]["preis_grund"], r["summe_cent"]), ("Stammkundenrabatt", 120000))
        from io import BytesIO
        from pypdf import PdfReader
        pdf = "".join(s.extract_text() for s in PdfReader(BytesIO((bh.dir / r["belege"][0]["pfad"]).read_bytes())).pages)
        self.assertIn("Reel", pdf)                                                # Text ist lesbar
        self.assertNotIn("Stammkundenrabatt", pdf)
        ev = [e for e in bh.eintraege() if "Stammkundenrabatt" in str(e["daten"])]
        self.assertTrue(ev)                                                       # nachvollziehbar in der Kette


if __name__ == "__main__":
    unittest.main()
