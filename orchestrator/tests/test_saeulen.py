"""MONETARISIERUNG M1: Erloes-Saeulen fuer Einnahmen, Ausgaben und Stunden. Gate: Summe aller Saeulen = bisheriger
Umsatz, unbekannte Gegenpartei bleibt unzugeordnet (Gegenprobe), EUeR unveraendert."""
import unittest

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eigenbelege import EigenbelegStore
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.saeulen import Saeulen, vorschlag, zuordnungen
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_rechnungen import FD, _entwurf
from orchestrator.tests.test_zeiterfassung import _setup

J = jetzt().year - 1                       # Probejahr in der Vergangenheit


def _d(mmtt: str) -> str:
    return f"{J}-{mmtt}"


class TestVorschlag(unittest.TestCase):
    def test_1_regeln(self):
        self.assertEqual(vorschlag("einnahme", "Meta Platforms Ireland Ltd.", "Auszahlung 282,37 USD")[0], "S2a")
        self.assertEqual(vorschlag("einnahme", "Google Ireland", "YouTube-Auszahlung Juni", quelle="eigenbeleg")[0], "S2c")
        self.assertEqual(vorschlag("einnahme", "KJ Adventure World", "Collab - Gewinnspiel Reel", quelle="rechnung")[0], "S1")
        self.assertEqual(vorschlag("einnahme", "Firma", "Imagefilm Recruiting", quelle="rechnung")[0], "S6")
        self.assertEqual(vorschlag("einnahme", "Firma", "Ware", "barter", "ware")[0], "S1")
        self.assertEqual(vorschlag("ausgabe", "Printful Latvia AS", "Shirts")[0], "S5")

    def test_2_gegenprobe_unbekannt_und_mehrdeutig(self):
        self.assertEqual(vorschlag("einnahme", "CR Container Trading GmbH", "Zahlung Rechnung RE-1 -- September 26",
                                   quelle="rechnung"), ("", ""))
        s, grund = vorschlag("einnahme", "Brand X", "Reel-Produktion inkl. Schnitt Story-Paket", quelle="rechnung")
        self.assertEqual(s, "")
        self.assertIn("mehrdeutig", grund)
        # eigene Rechnung mit „Facebook" im Text ist keine Facebook-Auszahlung
        self.assertEqual(vorschlag("einnahme", "Brand X", "Facebook-Reel", quelle="rechnung")[0], "")
        self.assertEqual(vorschlag("ausgabe", "Supabase Pte. Ltd.", "Pro Plan")[0], "")     # App oder LUNA -> offen


class TestAuswertung(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, self.k, self.ab, self.auftrag, self.z = _setup()
        self.rs, self.eig = RechnungStore(self.bh, self.ks), EigenbelegStore(self.bh)
        self.s, self.f = Saeulen(self.bh, self.ks), Finanzen(self.bh, self.ks)
        ap = "AP-00001"                                                           # aus _stores()
        self.re = self.rs.festschreiben(_entwurf(self.rs, self.k, ap, auftrag=self.auftrag), FD)["nummer"]
        self.rs.bezahlt(self.re, datum=_d("03-10"))                                   # 1.020,00
        self.eb = self.eig.anlegen({"art": "einnahme", "datum": _d("06-30"), "betrag": "250,50",
                                    "text": "YouTube-Auszahlung Juni", "gegenpartei": "Google Ireland"})["nummer"]
        self.aus = self.eig.anlegen({"art": "ausgabe", "datum": _d("07-01"), "betrag": "99", "kategorie": "werbung",
                                     "text": "Printful Musterdruck"})["nummer"]

    def test_1_summe_stimmt_und_unzugeordnet_bleibt_offen(self):
        a = self.s.auswertung(J)
        self.assertTrue(a["stimmig"])
        self.assertEqual(a["ohne"]["einnahmen_cent"], 102000 + 25050)                # nichts zugeordnet -> alles offen
        self.assertEqual(a["offen"], 2)
        vs = {b["bezug"]: b["vorschlag"] for b in a["belege"]}
        self.assertEqual((vs[self.eb], vs[self.aus]), ("S2c", "S5"))
        self.assertEqual(vs[self.re], "")                                            # Reel-Produktion + Story = mehrdeutig

    def test_2_zuordnen_euer_unveraendert(self):
        vorher = self.f.euer(J)
        self.assertEqual(self.s.zuordnen([{"bezug": self.re, "saeule": "S1"}, {"bezug": self.eb, "saeule": "S2c"},
                                          {"bezug": self.aus, "saeule": "S5"}], von="test")["geaendert"], 3)
        a = self.s.auswertung(J)
        g = {x["code"]: x for x in a["gruppen"]}
        self.assertEqual((g["S1"]["einnahmen_cent"], g["S2"]["einnahmen_cent"], a["ohne"]["einnahmen_cent"]), (102000, 25050, 0))
        self.assertEqual({t["code"]: t["einnahmen_cent"] for t in g["S2"]["teile"]}["S2c"], 25050)
        self.assertEqual((g["S5"]["ausgaben_cent"], g["S5"]["db_cent"]), (9900, -9900))
        self.assertEqual(g["S1"]["monate"][2], 102000)                                # Maerz
        self.assertTrue(a["stimmig"])
        self.assertEqual(a["summe"]["einnahmen_cent"], 127050)
        self.assertEqual(self.f.euer(J), vorher)                                      # EUeR bleibt exakt gleich
        # unveraendert erneut -> kein neues Ereignis; zuruecknehmen -> wieder offen
        self.assertEqual(self.s.zuordnen([{"bezug": self.re, "saeule": "S1"}])["geaendert"], 0)
        self.s.zuordnen([{"bezug": self.eb, "saeule": ""}])
        self.assertNotIn(self.eb, zuordnungen(self.bh.eintraege()))
        self.assertEqual(self.s.auswertung(J)["ohne"]["einnahmen_cent"], 25050)

    def test_3_pruefung_vor_dem_schreiben(self):
        n = len(self.bh.eintraege())
        for falsch in ([{"bezug": self.re, "saeule": "S9"}], [{"bezug": "RE-1999-0001", "saeule": "S1"}], []):
            with self.assertRaises(ValueError, msg=falsch):
                self.s.zuordnen([{"bezug": self.eb, "saeule": "S2c"}] + falsch if falsch else [])
        self.assertEqual(len(self.bh.eintraege()), n)                                 # nichts halb geschrieben

    def test_4_vererbung_auftrag_und_stunden(self):
        self.z.eintragen(auftrag=self.auftrag, datum=_d("03-05"), minuten=120, arbeit="dreh")
        self.s.zuordnen([{"bezug": self.auftrag, "saeule": "S6"}])                  # nur der Auftrag
        a = self.s.auswertung(J)
        b = {x["bezug"]: x for x in a["belege"]}[self.re]
        self.assertEqual((b["saeule"], b["saeule_quelle"]), ("S6", "auftrag"))      # Rechnung erbt
        s6 = {x["code"]: x for x in a["gruppen"]}["S6"]
        self.assertEqual((s6["einnahmen_cent"], s6["minuten_erfasst"]), (102000, 120))
        self.assertEqual(s6["euro_je_stunde_cent"], 51000)                           # 1.020 EUR / 2 h
        # Schaetzung ohne Auftrag: setzen, ueberschreiben, loeschen
        self.s.stunden(J, 6, "nils", "S2c", "10")
        self.s.stunden(J, 6, "nils", "S2c", "12,5")
        self.s.stunden(J, 6, "celine", "S2c", "2")
        s2c = {t["code"]: t for t in {x["code"]: x for x in self.s.auswertung(J)["gruppen"]}["S2"]["teile"]}["S2c"]
        self.assertEqual(s2c["minuten_geschaetzt"], 14.5 * 60)
        self.s.stunden(J, 6, "celine", "S2c", "0")
        self.assertEqual(len(self.s.auswertung(J)["schaetzungen"]), 1)
        for falsch in ((J, 13, "nils", "S1", 1), (J, 1, "fremd", "S1", 1), (J, 1, "nils", "S9", 1), (J, 1, "nils", "S1", 999)):
            with self.assertRaises(ValueError, msg=falsch):
                self.s.stunden(*falsch)


class TestApi(ApiBasis):
    def test_1_lesen_und_zuordnen(self):
        eig = EigenbelegStore(self.w.kunden_store.bh)
        nr = eig.anlegen({"art": "einnahme", "datum": _d("01-23"), "betrag": "124,48", "text": "Auszahlung",
                          "gegenpartei": "Meta Platforms Ireland Ltd."})["nummer"]
        d = self.c.get(f"/api/finanzen/saeulen?jahr={J}").json()
        self.assertEqual((d["offen"], d["stimmig"], d["belege"][0]["vorschlag"]), (1, True, "S2a"))
        self.assertFalse(self.c.post("/api/finanzen/saeulen/zuordnen", json={"zuordnungen": [{"bezug": nr, "saeule": "X"}]}).json()["ok"])
        self.assertTrue(self.c.post("/api/finanzen/saeulen/zuordnen", json={"zuordnungen": [{"bezug": nr, "saeule": "S2a"}]}).json()["ok"])
        self.assertTrue(self.c.post("/api/finanzen/saeulen/stunden", json={"jahr": J, "monat": 1, "person": "nils",
                                                                           "saeule": "S2a", "stunden": "4"}).json()["ok"])
        d = self.c.get(f"/api/finanzen/saeulen?jahr={J}").json()
        s2a = {t["code"]: t for t in {g["code"]: g for g in d["gruppen"]}["S2"]["teile"]}["S2a"]
        self.assertEqual((d["offen"], s2a["einnahmen_cent"], s2a["minuten"], s2a["euro_je_stunde_cent"]), (0, 12448, 240, 3112))

    def test_2_oberflaeche(self):
        from pathlib import Path
        static = Path(self.w.__file__).parent / "static"
        js = (static / "app-v2.js").read_text(encoding="utf-8")
        self.assertIn('["saeulen", "Säulen"]', js)
        self.assertIn("/api/finanzen/saeulen?jahr=", js)
        self.assertIn('data-act="sl-uebernehmen"', js)


if __name__ == "__main__":
    unittest.main()
