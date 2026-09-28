"""KUNDEN_FINANZEN Etappe 11: Positionen erkennen (E-Rechnung, Text, KI) und Beleg aufteilen -- private Artikel zaehlen
nicht, Zahlungen anteilig, AfA/GWG je Position."""
import unittest
from datetime import timedelta
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eingangsbelege import (EingangStore, anteile, e_rechnung_lesen, positionen_regeln,
                                              vorschlag_llm, vorschlag_regeln)
from orchestrator.core.finanzen import Finanzen
from orchestrator.tests.test_angebote import _stores
from orchestrator.tests.test_eingangsbelege import UBL, _pdf

AMAZON = """Amazon EU S.a.r.l.
Rechnung
Rechnungsdatum 12.09.2026
Beschreibung Menge Stückpreis (ohne USt.) USt. % Stückpreis (inkl. USt.) Zwischensumme (inkl. USt.)
Anker USB-C Kabel 2m 2 10,92 € 19 % 12,99 € 25,98 €
Kinderbuch Die Maus 1 14,95 € 7 % 16,00 € 16,00 €
Versandkosten 3,99 €
Zwischensumme (ohne USt.) 38,63 €
Gesamtpreis 45,97 €"""


class TestPositionen(unittest.TestCase):
    def test_1_text(self):
        p = positionen_regeln(AMAZON)
        self.assertEqual([(x["text"], x["betrag"]) for x in p],
                         [("Anker USB-C Kabel 2m", "25,98"), ("Kinderbuch Die Maus", "16,00"), ("Versandkosten", "3,99")])
        self.assertEqual(vorschlag_regeln(AMAZON)["positionen"], p)
        self.assertEqual(positionen_regeln("1 SmallRig Cage Kit 4336 für Sony Alpha 6700 1 Stk. 19,0 % 51,92 € 51,92 €")[0]["text"],
                         "SmallRig Cage Kit 4336 für Sony Alpha 6700")
        self.assertEqual(positionen_regeln("19% MwSt. 8,29 €\nGesamtbetrag (brutto) 51,92 €\nIBAN DE12 3456 00,00"), [])

    def test_2_e_rechnung_brutto(self):
        ubl = UBL.replace(b"<cac:InvoiceLine><cac:Item><cbc:Name>Funkmikrofon</cbc:Name></cac:Item></cac:InvoiceLine>",
                          b"<cac:InvoiceLine><cbc:LineExtensionAmount currencyID=\"EUR\">294.03</cbc:LineExtensionAmount>"
                          b"<cac:Item><cbc:Name>Funkmikrofon</cbc:Name><cac:ClassifiedTaxCategory><cbc:Percent>19</cbc:Percent>"
                          b"</cac:ClassifiedTaxCategory></cac:Item></cac:InvoiceLine>")
        e = e_rechnung_lesen(ubl)
        self.assertEqual(e["positionen"], [{"text": "Funkmikrofon", "betrag": "349,90"}])       # 294,03 netto + 19 %

    def test_3_ki(self):
        v = vorschlag_llm('{"positionen": [{"text": "Kabel", "betrag": "25,98", "kategorie": "buero"}, {"text": "", "betrag": "1"}, '
                          '{"text": "Buch", "betrag": "abc"}, {"text": "Maus", "betrag": "9", "kategorie": "erfunden"}], "kategorie": "buero"}')
        self.assertEqual(v["positionen"], [{"text": "Kabel", "betrag": "25,98", "kategorie": "buero"}, {"text": "Maus", "betrag": "9,00"}])

    def test_4_anteile_exakt(self):
        t = [{"betrag_cent": 2598}, {"betrag_cent": 1600}, {"betrag_cent": 399}]
        self.assertEqual(sum(anteile(4597, t)), 4597)
        self.assertEqual(anteile(4597, t), [2598, 1600, 399])
        self.assertEqual(sum(anteile(1000, t)), 1000)                                      # Teilzahlung, kein Cent verloren


class TestAufteilung(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, *_ = _stores()
        self.eb, self.f = EingangStore(self.bh), Finanzen(self.bh, self.ks)
        latin = AMAZON.replace("€", "EUR").replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")   # Test-PDF: Helvetica
        self.nr = self.eb.aufnehmen(_pdf(latin), "amazon.pdf")["nummer"]
        self.heute = jetzt().date().isoformat()
        self.basis = {"lieferant": "Amazon", "rechnungsdatum": self.heute, "betrag": "45,97", "kategorie": "buero"}

    def auf(self, *zeilen):
        return [{"text": t, "betrag": b, "kategorie": k} | extra for t, b, k, *rest in zeilen for extra in [rest[0] if rest else {}]]

    def test_1_pruefungen(self):
        with self.assertRaises(ValueError):                                                # Summe passt nicht
            self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Kabel", "25,98", "buero"), ("Buch", "16,00", "privat"))})
        with self.assertRaises(ValueError):                                                # alles privat
            self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Kabel", "25,98", "privat"), ("Rest", "19,99", "privat"))})
        with self.assertRaises(ValueError):                                                # Kategorie fehlt
            self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Kabel", "25,98", ""), ("Rest", "19,99", "buero"))})
        with self.assertRaises(ValueError):                                                # Gutschrift nie aufteilen
            self.eb.buchen(self.nr, self.basis | {"art": "einnahme", "aufteilung": self.auf(("a", "45,97", "buero"))})
        r = self.eb.buchen(self.nr, self.basis | {"kategorie": "", "aufteilung": self.auf(("Kabel", "25,98", "buero"))
                                                  + self.auf(("Buch", "16,00", "privat"), ("Versand", "3,99", "buero"))})
        self.assertEqual((r["felder"]["kategorie"], len(r["felder"]["aufteilung"])), ("buero", 3))
        l = next(x for x in self.eb.liste() if x["nummer"] == self.nr)
        self.assertEqual((l["aufgeteilt"], l["teils_privat"]), (3, True))

    def test_2_privat_zaehlt_nicht(self):
        self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Kabel", "25,98", "buero"), ("Buch", "16,00", "privat"),
                                                                      ("Versand", "3,99", "buero"))})
        self.eb.bezahlt(self.nr, self.heute)
        j = [z for z in self.f.journal(jetzt().year) if z["bezug"] == self.nr]
        self.assertEqual([(z["kategorie"], z["betrag_cent"], z["abziehbar_cent"]) for z in j],
                         [("buero", 2598, 2598), ("privat", 1600, 0), ("buero", 399, 399)])
        eu = self.f.euer(jetzt().year)
        self.assertEqual(eu["ausgaben_cent"], 2598 + 399)                                  # 29,97 statt 45,97
        self.assertNotIn("privat", {p["kategorie"] for p in eu["ausgaben"]})

    def test_3_teilzahlung_anteilig(self):
        self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Kabel", "25,98", "buero"), ("Buch", "16,00", "privat"),
                                                                      ("Versand", "3,99", "buero"))})
        self.eb.bezahlt(self.nr, self.heute, betrag="20")
        j = [z for z in self.f.journal(jetzt().year) if z["bezug"] == self.nr]
        self.assertEqual(sum(z["betrag_cent"] for z in j), 2000)
        self.assertEqual(sum(z["abziehbar_cent"] for z in j), 2000 - next(z["betrag_cent"] for z in j if z["kategorie"] == "privat"))

    def test_4_anlage_und_gwg_je_position(self):
        nr = self.eb.aufnehmen(_pdf("Foto Laden Rechnung Kamera und Tasche " + "x" * 30), "foto.pdf")["nummer"]
        b = {"lieferant": "Foto Laden", "rechnungsdatum": self.heute, "betrag": "1.349,00", "kategorie": ""}
        with self.assertRaises(ValueError):                                                # Kamera > 800 als GWG
            self.eb.buchen(nr, b | {"aufteilung": self.auf(("Kamera", "1.299,00", "gwg"), ("Tasche", "50,00", "gwg"))})
        with self.assertRaises(ValueError):                                                # Anlage ohne Nutzungsdauer
            self.eb.buchen(nr, b | {"aufteilung": self.auf(("Kamera", "1.299,00", "anlage"), ("Tasche", "50,00", "gwg"))})
        self.eb.buchen(nr, b | {"aufteilung": self.auf(("Kamera", "1.299,00", "anlage", {"nutzungsdauer_jahre": 7}),
                                                       ("Tasche", "50,00", "gwg"))})
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(month=12, day=31)):
            a = self.f.anlagen(jetzt().year)
            eu = self.f.euer(jetzt().year)
        self.assertEqual([(x["bezeichnung"], x["ak_cent"], x["nutzungsdauer_jahre"]) for x in a], [("Kamera", 129900, 7)])
        self.eb.bezahlt(nr, self.heute)
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(month=12, day=31)):
            eu = self.f.euer(jetzt().year)
        pos = {p["kategorie"]: p["betrag_cent"] for p in eu["ausgaben"]}
        self.assertEqual(pos["gwg"], 5000)                                                 # Tasche sofort
        self.assertNotIn(129900, pos.values())                                            # Kamera nur ueber AfA

    def test_5_eine_position_ist_normale_buchung(self):
        r = self.eb.buchen(self.nr, self.basis | {"aufteilung": self.auf(("Alles", "45,97", "buero"))})
        self.assertNotIn("aufteilung", r["felder"])


if __name__ == "__main__":
    unittest.main()
