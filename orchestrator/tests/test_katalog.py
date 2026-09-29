"""Self-Checks Etappe 3b: Leistungskatalog (aus dem Preislisten-Generator), Zuschlaege + Rabatt, Hanserautisch-PDF,
Preisliste, Rechte -- offline."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.angebote import AngebotStore, anrede_moin, preisliste_pdf, summen
from orchestrator.core.katalog import STANDARD, Katalog, pruefe
from orchestrator.tests.test_angebote import FIRMA, _stores


def _logo(pfad: Path) -> Path:
    from PIL import Image
    Image.new("RGB", (560, 221), (0, 64, 135)).save(pfad, "JPEG")
    return pfad


def _pos(kat, iid, menge=1):
    it, g = kat.format(iid)
    return {"beschreibung": it["name"], "detail": it["basis"], "menge": menge, "einheit": it["einheit"],
            "einzelpreis_cent": it["preis_cent"], "katalog_id": iid, "gruppe": g}


class TestKatalog(unittest.TestCase):
    def test_1_standard_wie_generator(self):
        k = pruefe(copy.deepcopy(STANDARD))
        items = {it["id"]: it for g in k["gruppen"] for it in g["items"]}
        self.assertEqual(len(items), 18)                                               # 15 Formate + 3 Pakete
        self.assertEqual((items["reel_solo"]["preis_cent"], items["pk_saison"]["einheit"]), (160000, "Monat"))
        self.assertEqual([z["prozent"] for z in k["zuschlaege"]], [25, 60, 50, 20, 25, 20])
        # Pakete wie im Generator nachgerechnet: Matchday = (1600+600+150+150) - 10 %, Saison = (1200+2*1050+2*600) - 20 %
        self.assertEqual(items["pk_match"]["preis_cent"], round((160000 + 60000 + 15000 + 15000) * 0.9))
        self.assertEqual(items["pk_saison"]["preis_cent"], round((120000 + 2 * 105000 + 2 * 60000) * 0.8))

    def test_2_speichern_protokolliert_preise(self):
        bh, *_ = _stores()
        kat = Katalog(bh)
        self.assertFalse(kat.pfad.exists())
        neu = kat.laden()
        neu["gruppen"][0]["items"][0]["produktion_cent"] = 59000     # Etappe 16: Preis = Kontakte x TKP + Produktion
        r = kat.speichern(neu, von="LUNA-OS:ceo")
        self.assertEqual(r["preise"], {"reel_solo": [160000, 170000]})
        self.assertEqual(kat.laden()["gruppen"][0]["items"][0]["preis_cent"], 170000)
        self.assertEqual(bh.eintraege("katalog_geaendert")[0]["daten"]["preise"], {"reel_solo": [160000, 170000]})
        self.assertEqual(kat.speichern(kat.laden()), {"geaendert": False})             # nichts geaendert -> kein Eintrag
        self.assertEqual(len(bh.eintraege("katalog_geaendert")), 1)
        self.assertEqual(bh.pruefe_kette(), [])

    def test_3_validierung(self):
        for kaputt in ({"gruppen": []}, {"gruppen": [{"name": "X", "items": [{"id": "a b", "name": "x", "preis_cent": 1}]}]},
                       {"gruppen": [{"name": "X", "items": [{"id": "a", "name": "x", "preis_cent": -1}]}]},
                       {"gruppen": [{"name": "X", "items": [{"id": "a", "name": "x", "preis_cent": 1},
                                                            {"id": "a", "name": "y", "preis_cent": 1}]}]},
                       {"gruppen": [{"name": "X", "items": [{"id": "a", "name": "x", "preis_cent": 1}]}],
                        "zuschlaege": [{"id": "z", "prozent": 0}]}, "quatsch"):
            with self.assertRaises(ValueError, msg=kaputt):
                pruefe(kaputt)

    def test_4_kaputte_datei_faellt_auf_standard_zurueck(self):
        bh, *_ = _stores()
        (bh.dir / "katalog.json").write_text("{kaputt", encoding="utf-8")
        self.assertEqual(len(Katalog(bh).laden()["zuschlaege"]), 6)


class TestAngebot3b(unittest.TestCase):
    def test_1_summen_wie_generator(self):
        pos = [{"menge": "2", "einzelpreis_cent": 160000}, {"menge": "3", "einzelpreis_cent": 60000}]
        sm = summen(pos, [{"name": "Rechte", "prozent": 25}, {"name": "Express", "prozent": 25}], 10)
        self.assertEqual(sm["formate_cent"], 500000)
        self.assertEqual([c for *_, c in sm["zuschlaege"]], [125000, 125000])       # je auf die Summe der Formate
        self.assertEqual(sm["rabatt"], (10, 75000))                                 # Rabatt auf Zwischensumme
        self.assertEqual(sm["gesamt_cent"], 675000)
        self.assertEqual(summen(pos, [], 0)["rabatt"], None)
        self.assertEqual(summen([{"menge": "1", "einzelpreis_cent": 333}], [{"name": "x", "prozent": 33.33}], 0)
                         ["zuschlaege"][0][2], 111)                                  # kaufmaennisch gerundet

    def test_2_angebot_aus_katalog_eingefroren(self):
        bh, ks, _, k, ap = _stores()
        kat = Katalog(bh)
        st = AngebotStore(bh, ks, kat)
        nr = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": [_pos(kat, "reel_solo", 2), _pos(kat, "saison")],
                         "zuschlaege": [{"id": "rechte", "name": "Nutzungsrechte", "prozent": 25}],
                         "rabatt_prozent": "10"})["nummer"]
        a = st.angebot(nr)
        self.assertEqual((a["layout"], a["summen"]["gesamt_cent"]), ("hanserautisch", round((320000 + 120000) * 1.25 * 0.9)))
        self.assertEqual(a["positionen"][1]["katalog_id"], "saison")
        self.assertTrue(a["bloecke"]["kalkulation"] and a["bloecke"]["zeige_kennzahlen"])
        from datetime import date, timedelta
        self.assertEqual(a["gueltig_bis"], (date.fromisoformat(a["datum"]) + timedelta(days=14)).isoformat())
        k2 = kat.laden()
        k2["gruppen"][0]["items"][0]["preis_cent"] = 999900
        k2["texte"]["kennzahlen"] = [["1", "neu"]]
        kat.speichern(k2)
        a = st.angebot(nr)                                                             # Katalogaenderung wirkt nicht
        self.assertEqual((a["positionen"][0]["einzelpreis_cent"], a["bloecke"]["kennzahlen"][0][0]), (160000, "120.000+"))
        st.aendern(nr, {"zeige_kalkulation": False})
        self.assertFalse(st.angebot(nr)["bloecke"]["zeige_kalkulation"])
        with self.assertRaises(ValueError):
            st.aendern(nr, {"rabatt_prozent": 95})
        with self.assertRaises(ValueError):
            st.aendern(nr, {"zuschlaege": [{"name": "x", "prozent": 500}]})

    def test_3_pdfs(self):
        bh, ks, _, k, ap = _stores()
        _logo(bh.dir / "logo.jpg")
        kat = Katalog(bh)
        st = AngebotStore(bh, ks, kat)
        nr = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": [_pos(kat, i) for i in ("reel_solo", "story", "pk_match")],
                         "zuschlaege": [{"name": "Express", "prozent": 25}], "rabatt_prozent": 5})["nummer"]
        self.assertTrue(st.pdf(nr, FIRMA).startswith(b"%PDF"))
        st.aendern(nr, {"layout": "standard"})
        self.assertTrue(st.pdf(nr, FIRMA).startswith(b"%PDF"))
        liste = preisliste_pdf(kat.laden(), FIRMA, logo=bh.dir / "logo.jpg")
        self.assertIn(b"/Count 3", liste)
        self.assertTrue(preisliste_pdf(kat.laden(), FIRMA, logo=None, ids=["reel_solo"]).startswith(b"%PDF"))
        with self.assertRaises(ValueError):
            preisliste_pdf(kat.laden(), FIRMA, logo=None, ids=["gibtsnicht"])

    def test_4_anrede(self):
        self.assertEqual(anrede_moin({"vorname": "Anna Lena", "nachname": "Muster"}, "X"), "Moin Anna,")
        self.assertEqual(anrede_moin({"vorname": "Herr", "nachname": "Muster"}, "X"), "Moin Herr Muster,")
        self.assertEqual(anrede_moin({"nachname": "Muster"}, "X"), "Moin Muster,")
        self.assertEqual(anrede_moin(None, "Brand X"), "Moin liebes Team von Brand X,")


class TestKatalogApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        self.w = webapp
        self.orig = webapp.kunden_store
        bh, ks, _, self.k, self.ap = _stores()
        (bh.dir / "firmendaten.json").write_text(json.dumps(FIRMA), encoding="utf-8")
        webapp.kunden_store = ks
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.kunden_store = self.orig

    def test_1_lesen_speichern_preisliste(self):
        d = self.c.get("/api/crm/katalog").json()
        self.assertEqual((d["gespeichert"], d["darf_aendern"]), (False, True))
        kat = d["katalog"]
        kat["zuschlaege"][0]["prozent"] = 30
        self.assertTrue(self.c.post("/api/crm/katalog", json={"katalog": kat}).json()["ok"])
        self.assertEqual(self.c.get("/api/crm/katalog").json()["katalog"]["zuschlaege"][0]["prozent"], 30)
        self.assertFalse(self.c.post("/api/crm/katalog", json={"katalog": {"gruppen": []}}).json()["ok"])
        r = self.c.get(f"/api/crm/katalog/preisliste.pdf?ids=reel_solo,story&firma={self.k}&ap={self.ap}")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "application/pdf"))
        self.assertEqual(self.c.get("/api/crm/katalog/preisliste.pdf?ids=gibtsnicht").status_code, 400)

    def test_2_preise_nur_mit_finanzen(self):
        from unittest import mock
        with mock.patch.object(self.w, "hat_modul", return_value=False):
            r = self.c.post("/api/crm/katalog", json={"katalog": self.c.get("/api/crm/katalog").json()["katalog"]}).json()
        self.assertFalse(r["ok"])
        self.assertIn("Finanzen", r["hinweis"])

    def test_3_angebot_ueber_api_mit_zuschlag(self):
        r = self.c.post("/api/crm/angebote", json={"angebot": {
            "firma": self.k, "positionen": [{"beschreibung": "Reel", "menge": "1", "einzelpreis": "1.600",
                                             "katalog_id": "reel_solo", "gruppe": "Instagram", "detail": "Ø 37.000"}],
            "zuschlaege": [{"id": "rechte", "name": "Nutzungsrechte", "prozent": 25}], "rabatt_prozent": 0,
            "zeige_kennzahlen": False}}).json()
        self.assertTrue(r["ok"], r)
        a = self.c.get(f"/api/crm/angebote/{r['nummer']}").json()["angebot"]
        self.assertEqual((a["summe_cent"], a["bloecke"]["zeige_kennzahlen"]), (200000, False))
        self.assertEqual(self.c.get(f"/api/crm/angebote/{r['nummer']}/pdf").status_code, 200)


if __name__ == "__main__":
    unittest.main()
