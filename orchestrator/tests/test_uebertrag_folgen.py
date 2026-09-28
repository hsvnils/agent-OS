"""Folgen aus dem Uebertrag 2026 (CEO 28.09.2026): Verlustvortrag im Finanzbereich (nicht EUeR), Amazon-Positionen
(mehrzeiliger Text, geschuetzte Leerzeichen, Sammel-PDF), CFO-Hinweis „wiederkehrend fehlt“ nur bei Abo-artigen Betraegen."""
import unittest
from datetime import date
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eigenbelege import EigenbelegStore
from orchestrator.core.eingangsbelege import positionen_regeln, vorschlag_regeln
from orchestrator.core.finanzen import VERLUSTVORTRAG, Finanzen, verlustvortrag
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import ApiBasis, _stores

AMAZON_ECHT = ("Rechnungsdetails\nBestelldatum 21.09.2026\nRechnungsnummer DE693NP65AEUD\nZahlbetrag 25,89 €\n"
               "Bestellinformationen\nBeschreibung Menge Stückpreis\n(ohne\xa0USt.)\nUSt.\xa0% Stückpreis\n(inkl.\xa0USt.)\n"
               "Zwischensumme\n(inkl.\xa0USt.)\nSMALLRIG Kamera Monitor Mount mit Kaltschuhadapter &\n"
               "Anti-Twist-Design | B08JZ7MQN6 \nASIN: B08JZ7MQN6\n1 22,90 € 19% 27,25 € 27,25 €\n"
               "Versandkosten 0,00 € 0,00 € 0,00 €\nAktionsrabatt -1,14 € -1,36 € -1,36 €\n"
               "Rechnungsdetails\nRechnungsnummer DE6005YXL1FVTI\nZahlbetrag 23,92 €\n(inkl.\xa0USt.)\n"
               "SIRUI AM-SHS Seitenhandgriff, ARRI\nASIN: B0XYZ\n1 26,81 € 19% 31,90 € 31,90 €\nAktionsrabatt -6,71 € -7,98 € -7,98 €\n")


class TestAmazon(unittest.TestCase):
    def test_1_mehrzeilig_und_sammel_pdf(self):
        p = positionen_regeln(AMAZON_ECHT)
        self.assertEqual([(x["text"][:34], x["betrag"]) for x in p],
                         [("SMALLRIG Kamera Monitor Mount mit ", "27,25"), ("Aktionsrabatt", "-1,36"),
                          ("SIRUI AM-SHS Seitenhandgriff, ARRI", "31,90"), ("Aktionsrabatt", "-7,98")])
        self.assertNotIn("B08JZ7MQN6", p[0]["text"])
        self.assertEqual(vorschlag_regeln(AMAZON_ECHT)["betrag"], "49,81")           # 25,89 + 23,92 (zwei Rechnungen)


class TestVerlustvortrag(unittest.TestCase):
    def test_1_verrechnung_nicht_in_euer(self):
        bh, ks, *_ = _stores()
        f = Finanzen(bh, ks)
        j = jetzt().year
        self.assertIsNone(f.uebersicht(j)["verlustvortrag"])
        bh.erfassen(VERLUSTVORTRAG, {"jahr": j - 1, "betrag_cent": 262259})
        EigenbelegStore(bh).anlegen({"art": "einnahme", "datum": jetzt().date().isoformat(), "betrag": "1000", "text": "Auszahlung"})
        v = f.uebersicht(j)["verlustvortrag"]
        self.assertEqual((v["betrag_cent"], v["verrechnet_cent"], v["verbleibend_cent"]), (262259, 100000, 162259))
        self.assertEqual(f.euer(j)["ausgaben_cent"], 0)                                 # keine Ausgabe in der EUeR
        bh.erfassen(VERLUSTVORTRAG, {"jahr": j - 1, "betrag_cent": 250000})             # Korrektur: letzte gilt
        self.assertEqual(verlustvortrag(bh.eintraege(), j - 1), 250000)


class TestWiederkehrend(unittest.TestCase):
    def test_1_amazon_unregelmaessig_kein_hinweis(self):
        bh, ks, *_ = _stores()
        eig = EigenbelegStore(bh)
        h = date(jetzt().year, jetzt().month, 15)
        from orchestrator.core.todos import _monat
        m1, m2 = _monat(h, 1), _monat(h, 2)
        for mon, amazon, abo in ((m2, "16,37", "9,99"), (m1, "310,40", "9,99")):
            eig.anlegen({"art": "ausgabe", "datum": f"{mon}-05", "betrag": amazon, "kategorie": "buero", "text": "Einkauf",
                         "gegenpartei": "Amazon.de"})
            eig.anlegen({"art": "ausgabe", "datum": f"{mon}-06", "betrag": abo, "kategorie": "software", "text": "Abo",
                         "gegenpartei": "Canva"})
        with mock.patch("orchestrator.core.eigenbelege.jetzt", return_value=jetzt()):
            titel = [t["titel"] for t in geschaefts_todos(bh, ks, heute=h) if t["id"].startswith("fehlt:")]
        self.assertEqual(len(titel), 1)
        self.assertTrue(titel[0].startswith("Canva"))                                    # Abo ja, Amazon nein


class TestVerlustvortragApi(ApiBasis):
    def test_a1(self):
        j = jetzt().year
        self.assertFalse(self.c.post("/api/finanzen/verlustvortrag", json={"jahr": j, "betrag": "10"}).json()["ok"])  # laufendes Jahr
        self.assertFalse(self.c.post("/api/finanzen/verlustvortrag", json={"jahr": j - 1, "betrag": "-5"}).json()["ok"])
        self.assertTrue(self.c.post("/api/finanzen/verlustvortrag", json={"jahr": j - 1, "betrag": "2.622,59"}).json()["ok"])
        self.assertEqual(self.c.get("/api/finanzen/uebersicht").json()["verlustvortrag"]["betrag_cent"], 262259)
        self.assertEqual(self.c.get("/api/finanzen/abschluss").json()["verlustvortrag"]["betrag_cent"], 262259)


if __name__ == "__main__":
    unittest.main()
