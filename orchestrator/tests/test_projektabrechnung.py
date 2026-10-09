"""PROJEKTZEITEN Z2: Projektzeiten optional in der Rechnung -- Auswahl, beide Darstellungen, Summe = Stunden x Satz,
keine Doppelabrechnung, Storno gibt frei, Stundenzettel als PDF-Anlage, kalkulatorische Kosten bleiben getrennt."""
import io
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.katalog import Katalog
from orchestrator.core.projektabrechnung import KM_ID, ZEIT_ID, katalog_saetze, saetze, setzen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.zeiterfassung import kalkulatorisch
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_rechnungen import FD
from orchestrator.tests.test_zeiterfassung import _setup

GESTERN = (jetzt().date() - timedelta(days=1)).isoformat()
VORGESTERN = (jetzt().date() - timedelta(days=2)).isoformat()


def _basis():
    bh, ks, k, ab, nr, z = _setup()
    a = z.eintragen(auftrag=nr, datum=VORGESTERN, von_uhr="09:00", bis_uhr="12:30", pause_min="30", taetigkeit="Dreh")
    b = z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="14:00", bis_uhr="15:20", taetigkeit="Schnitt")
    z.fahrt_erfassen(a["id"], km=40)
    rs = RechnungStore(bh, ks, Katalog(bh))
    eid = rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"]
    rs.entwurf_aendern(eid, {"leistung_von": GESTERN})
    return bh, rs, z, ab, nr, eid, a["id"], b["id"]


class TestProjektabrechnung(unittest.TestCase):
    def test_1_zusammengefasst_mit_anlage(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        vorher = rs.get(eid)["summe_cent"]                                       # 1.020 EUR aus dem Auftrag
        r = setzen(rs, z, eid, zeiten=[a, b], km=[a], satz="65", km_satz="0,50")
        self.assertEqual(r["positionen"], 4)                                     # 2 Auftrag + Projektzeit + Fahrt
        x = rs.get(eid)
        pz = [p for p in x["positionen"] if p.get("katalog_id") == ZEIT_ID][0]
        self.assertEqual((pz["beschreibung"], pz["menge"], pz["einzelpreis_cent"]), ("Projektzeit 4,33 h", "4.33", 6500))
        self.assertEqual(x["summe_cent"], vorher + 28145 + 2000)                 # 4,33 h x 65 EUR + 40 km x 0,50 EUR
        pdf = rs.vorschau_pdf(eid, FD)
        from pypdf import PdfReader
        seiten = PdfReader(io.BytesIO(pdf)).pages
        self.assertIn("Stundenzettel", seiten[-1].extract_text())
        self.assertGreaterEqual(len(seiten), 2)
        self.assertEqual(ab.auftrag(nr)["verkauf_satz_cent"], 6500)              # je Auftrag gemerkt
        self.assertEqual(saetze(ab.auftrag(nr), rs.katalog)["satz_cent"], 6500)

    def test_2_einzeln(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        setzen(rs, z, eid, zeiten=[b, a], km=[], darstellung="einzeln", satz="60")
        zeilen = [p for p in rs.get(eid)["positionen"] if p.get("katalog_id") == ZEIT_ID]
        self.assertEqual([p["menge"] for p in zeilen], ["3", "1.33"])            # nach Datum sortiert
        self.assertTrue(zeilen[0]["beschreibung"].startswith("Arbeitszeit ") and "09:00–12:30 Uhr – Dreh" in zeilen[0]["beschreibung"])
        from pypdf import PdfReader
        self.assertNotIn("Stundenzettel", PdfReader(io.BytesIO(rs.vorschau_pdf(eid, FD))).pages[-1].extract_text())
        setzen(rs, z, eid, zeiten=[], km=[])                                      # abwaehlen entfernt die Positionen
        self.assertFalse([p for p in rs.get(eid)["positionen"] if p.get("katalog_id") in (ZEIT_ID, KM_ID)])
        self.assertEqual(rs.get(eid)["projektzeiten"], {})

    def test_3_keine_doppelabrechnung_storno_gibt_frei(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        setzen(rs, z, eid, zeiten=[a], km=[a], satz="65", km_satz="0,5")
        kalk_vorher = kalkulatorisch(bh.eintraege(), jetzt().year)
        nummer = rs.festschreiben(eid, FD)["nummer"]
        sz = {x["id"]: x for x in z.stundenzettel(nr)["eintraege"]}
        self.assertEqual((sz[a]["abgerechnet"], sz[a]["km_abgerechnet"], sz[b]["abgerechnet"]), (nummer, nummer, ""))
        self.assertEqual(kalkulatorisch(bh.eintraege(), jetzt().year)["summe_cent"], kalk_vorher["summe_cent"])  # getrennt
        with self.assertRaisesRegex(ValueError, "abgerechnet"):
            z.korrigieren(a, datum=VORGESTERN, von_uhr="09:00", bis_uhr="10:00", grund="x")
        with self.assertRaisesRegex(ValueError, "abgerechnet"):
            z.stornieren(a, "x")
        with self.assertRaisesRegex(ValueError, "abgerechnet"):
            z.fahrt_erfassen(a, km=10)
        r = rs.stornieren(nummer, FD, grund="Test", korrektur=True)
        sz = {x["id"]: x for x in z.stundenzettel(nr)["eintraege"]}
        self.assertEqual((sz[a]["abgerechnet"], sz[a]["km_abgerechnet"]), ("", ""))
        kid = r["korrektur_entwurf"]
        self.assertEqual(rs.get(kid)["projektzeiten"]["zeiten"], [a])
        rs.entwurf_aendern(kid, {"leistung_von": GESTERN})
        n2 = rs.festschreiben(kid, FD)["nummer"]
        self.assertEqual({x["id"]: x for x in z.stundenzettel(nr)["eintraege"]}[a]["abgerechnet"], n2)

    def test_4_doppelt_ueber_zwei_entwuerfe_und_aenderung(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        setzen(rs, z, eid, zeiten=[a, b], km=[], satz="65")
        z.korrigieren(b, datum=GESTERN, von_uhr="14:00", bis_uhr="16:00", grund="laenger")
        with self.assertRaisesRegex(ValueError, "geaendert"):
            rs.festschreiben(eid, FD)
        setzen(rs, z, eid, zeiten=[a, b], km=[], satz="65")
        nummer = rs.festschreiben(eid, FD)["nummer"]
        with self.assertRaisesRegex(ValueError, "Schon abgerechnet"):          # zweite Rechnung: Auswahl abgelehnt
            setzen(rs, z, rs.entwurf_anlegen({"firma": ab.auftrag(nr)["firma"], "auftrag": nr, "positionen": [
                {"beschreibung": "X", "menge": "1", "einzelpreis": "1"}]})["entwurf_id"], zeiten=[a], km=[], satz="65")
        self.assertTrue(nummer)

    def test_5_pflichtangaben_und_position_entfernt(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        with self.assertRaisesRegex(ValueError, "Stundensatz"):
            setzen(rs, z, eid, zeiten=[a], km=[])
        with self.assertRaisesRegex(ValueError, "km-Satz"):
            setzen(rs, z, eid, zeiten=[], km=[a])
        with self.assertRaisesRegex(ValueError, "ohne Kilometer"):
            setzen(rs, z, eid, zeiten=[], km=[b], km_satz="1")
        setzen(rs, z, eid, zeiten=[a], km=[], satz="65")
        pos = [p for p in rs.get(eid)["positionen"] if p.get("katalog_id") != ZEIT_ID]
        rs.entwurf_aendern(eid, {"positionen": [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in pos]})
        with self.assertRaisesRegex(ValueError, "Position fehlt"):
            rs.festschreiben(eid, FD)

    def test_6_katalog_satz(self):
        bh, rs, z, ab, nr, eid, a, b = _basis()
        k = rs.katalog.laden()
        k["gruppen"][0]["items"].append({"id": "projektstunde", "name": "Projektstunde", "basis": "", "preis_cent": 7000,
                                         "hinweis": "", "einheit": "Std."})
        rs.katalog.speichern(k)
        self.assertEqual(katalog_saetze(rs.katalog)["satz_cent"], 7000)
        self.assertEqual(saetze(ab.auftrag(nr), rs.katalog), {"satz_cent": 7000, "km_satz_cent": 0, "quelle": "katalog"})


class TestApi(ApiBasis):
    def test_a1_endpunkte(self):
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"})
        zid = self.c.post("/api/finanzen/zeit/eintrag", json={"auftrag": nr, "datum": GESTERN, "von": "09:00", "bis": "11:00", "arbeit": "dreh"}).json()["id"]
        eid = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()["entwurf_id"]
        d = self.c.get(f"/api/finanzen/rechnungen/{eid}/projektzeiten").json()
        self.assertEqual([x["id"] for x in d["stundenzettel"]["eintraege"]], [zid])
        self.assertEqual(d["saetze"]["satz_cent"], 0)
        r = self.c.post(f"/api/finanzen/rechnungen/{eid}/projektzeiten", json={"zeiten": [zid], "satz": "80"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{eid}/projektzeiten").json()["saetze"],
                         {"satz_cent": 8000, "km_satz_cent": 0, "quelle": "auftrag"})


if __name__ == "__main__":
    unittest.main()
