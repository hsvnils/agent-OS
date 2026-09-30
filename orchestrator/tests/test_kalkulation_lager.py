"""KUNDEN_FINANZEN Etappe 21: interne Kosten je Katalog-Artikel -> Deckungsbeitrag und Marge (Warnung unter Mindestmarge),
nie im Kunden-PDF; Lagerbestand fuer physische Ware (Zugaenge minus Verkaeufe laut Rechnungen, Storno zurueck)."""
import json
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.katalog import Katalog, kalkulation, pruefe
from orchestrator.core.lager import Lager, bestaende
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()


def _katalog(**extra):
    return {"gruppen": [{"name": "Produkte", "items": [{"id": "schal", "name": "Fan-Schal", "preis_cent": 2500,
                                                        "kosten": {"einkauf": 900, "material": 100}} | extra]}]}


class TestKalkulation(unittest.TestCase):
    def test_1_marge(self):
        k = pruefe(_katalog() | {"mindestmarge_prozent": "70"})
        it = k["gruppen"][0]["items"][0]
        self.assertEqual(it["kosten"], {"einkauf": 900, "material": 100})
        self.assertEqual(kalkulation(it, k["mindestmarge_prozent"]),
                         {"kosten_cent": 1000, "db_cent": 1500, "marge_prozent": 60.0, "unter_mindestmarge": True})
        self.assertIsNone(kalkulation(pruefe({"gruppen": [{"name": "P", "items": [{"id": "a", "name": "A",
                                                                                   "preis_cent": 100}]}]})["gruppen"][0]["items"][0]))
        with self.assertRaises(ValueError):
            pruefe(_katalog(kosten={"einkauf": -5}))

    def test_2_nie_im_pdf(self):
        from orchestrator.core.angebote import AngebotStore
        bh, ks, _, k, ap = _stores()
        kat = Katalog(bh)
        kat.speichern(pruefe(_katalog()))
        st = AngebotStore(bh, ks, kat)
        an = st.anlegen({"firma": k, "layout": "standard", "positionen": [{"beschreibung": "Fan-Schal", "menge": "2",
                                                                          "einzelpreis": "25", "katalog_id": "schal"}]})["nummer"]
        import io
        from pypdf import PdfReader
        text = " ".join(s.extract_text() for s in PdfReader(io.BytesIO(st.pdf(an, FD))).pages)
        self.assertNotIn("9,00", text)
        self.assertNotIn("Marge", text)


class TestLager(unittest.TestCase):
    def _setup(self):
        bh, ks, st, k, ap = _stores()
        kat = Katalog(bh)
        kat.speichern(pruefe(_katalog(physisch=True, mindestbestand=5, lager_start=(HEUTE - timedelta(days=10)).isoformat())))
        return bh, ks, k, kat, Lager(bh, kat), RechnungStore(bh, ks)

    def test_1_zugang_verkauf_storno(self):
        bh, ks, k, kat, lg, rs = self._setup()
        lg.bewegung("schal", 20, grund="Wareneingang", datum=(HEUTE - timedelta(days=5)).isoformat(), beleg="er-2026-0001")
        nr = rs.festschreiben(rs.entwurf_anlegen({"firma": k, "leistung_von": HEUTE.isoformat(), "positionen": [
            {"beschreibung": "Fan-Schal", "menge": "12", "einzelpreis": "25", "katalog_id": "schal"}]})["entwurf_id"], FD)["nummer"]
        x = lg.uebersicht()[0]
        self.assertEqual((x["zugang"], x["verkauft"], x["bestand"], x["niedrig"]), (20, 12, 8, False))
        nr2 = rs.festschreiben(rs.entwurf_anlegen({"firma": k, "leistung_von": HEUTE.isoformat(), "positionen": [
            {"beschreibung": "Fan-Schal", "menge": "4", "einzelpreis": "25", "katalog_id": "schal"}]})["entwurf_id"], FD)["nummer"]
        self.assertEqual((lg.uebersicht()[0]["bestand"], lg.uebersicht()[0]["niedrig"]), (4, True))
        self.assertIn("lager:schal", {t["id"] for t in geschaefts_todos(bh, ks)})
        rs.stornieren(nr2, FD, grund="Retoure")
        self.assertEqual(lg.uebersicht()[0]["bestand"], 8)                               # Storno bucht zurueck
        self.assertNotIn("lager:schal", {t["id"] for t in geschaefts_todos(bh, ks)})
        self.assertTrue(nr.startswith("RE-"))

    def test_2_vor_lager_start_und_pruefungen(self):
        bh, ks, k, kat, lg, rs = self._setup()
        roh = json.loads(kat.pfad.read_text())
        roh["gruppen"][0]["items"][0]["lager_start"] = (HEUTE + timedelta(days=1)).isoformat()   # Start morgen
        kat.speichern(pruefe(roh))
        rs.festschreiben(rs.entwurf_anlegen({"firma": k, "leistung_von": HEUTE.isoformat(), "positionen": [
            {"beschreibung": "Fan-Schal", "menge": "3", "einzelpreis": "25", "katalog_id": "schal"}]})["entwurf_id"], FD)
        self.assertEqual(bestaende(bh.eintraege(), kat.laden())["schal"]["verkauft"], 0)   # vor dem Lager-Start
        for m, g, d in ((0, "x", ""), ("abc", "x", ""), (5, "", ""), (5, "x", (HEUTE + timedelta(days=1)).isoformat())):
            with self.assertRaises(ValueError):
                lg.bewegung("schal", m, grund=g, datum=d)
        with self.assertRaises(ValueError):
            lg.bewegung("gibtsnicht", 5, grund="x")


class TestApi(ApiBasis):
    def test_a1_lager_endpunkte(self):
        Katalog(self.w.kunden_store.bh).speichern(pruefe(_katalog(physisch=True, mindestbestand=2)))
        r = self.c.post("/api/finanzen/lager/schal/bewegung", json={"menge": "10", "grund": "Wareneingang"}).json()
        self.assertTrue(r["ok"], r)
        a = self.c.get("/api/finanzen/lager").json()["artikel"][0]
        self.assertEqual((a["id"], a["bestand"]), ("schal", 10))
        self.assertFalse(self.c.post("/api/finanzen/lager/schal/bewegung", json={"menge": "0", "grund": "x"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
