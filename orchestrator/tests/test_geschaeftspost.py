"""KUNDEN_FINANZEN Etappe 28: BF-49 (Anwalts-/Forderungs-Post zu eigenen Rechnungen gehoert in die Firmenakte, nicht in
die Belege) und BF-50 (Selgros-Rechnung: Positionen brutto, Kartenzahlungsbeleg als Zahlungsnachweis).
Nachgebaute Texte, keine echten Kundendaten."""
import unittest

from orchestrator.core.eingangsbelege import EingangStore, cent, mail_eingang_pruefen, selgros_lesen, vorschlag_regeln
from orchestrator.core.firmenakte import eigene_forderung, mails_pruefen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_altrechnungen import PDF, T
from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_firmenakte import LUNA, _setup
from orchestrator.tests.test_mail_belege import ABS, MOIN, _G, _mail

ANWALT_BRIEF = """Anwaltskanzlei Muster
Kiez Alm Gastro GmbH
Grosse Freiheit 1
hiermit zeige ich die rechtliche Vertretung von Max Muster an.
Hierueber wurde die Rechnung Nr. 11052026 vom 11. Mai 2026 mit einem Gesamtbetrag von EUR 4.000,00 erstellt.
Kosten meiner Beauftragung EUR 480,17"""

SELGROS = """RechnungBelegnummer:
1234567890123456
Belegdatum:
19.09.2026 19:14
Selgros Musterstadt
Gutenbergring 1 12345 Musterstadt
Pos. GTIN Bezeichnung Menge Inhalt VP Einzelpreis* Warenwert* MwSt
1 4000000000001 RINDERSTEAK CA.2KG AE FR 2,28 1 kg 18,990 43,30 7,0 %
2 4000000000002 HONIGTOMATE CHERRY KL.I
NIEDERLANDE
0,445 1 kg 26,990 12,01 7,0 %
3 4000000000003 VENUSMUSCH.50/70 TK
1KG
1 1 BT A 4,290 4,29 7,0 %
4 4000000000004 TRAGETASCHE 0,79 1 ST 0,790 0,79 19,0 %
MwSt-Satz Ware Leergut Wa-Wert MwSt Gesamt
19,0 % 0,79 0,00 0,79 0,15 0,94
7,0 % 59,60 0,00 59,60 4,17 63,77
EUR 64,71
Sie haben bei diesem Einkauf gespart: Netto-Rabatt
A = Aktion / Werbepreise -3,10 EUR"""

KARTE = """KartenzahlungBelegnummer:
1234567890123456
Kundenbeleg
Bezahlung Contactless
Genehmigungs-Nr. 123456
Betrag EUR 64,71
Zahlung erfolgt"""


def _mit_rechnung():
    bh, ks, k, kiez, akte = _setup()
    RechnungStore(bh, ks).alt_erfassen({"firma": kiez, "nummer": "RG-11052026", "rechnungsdatum": T(140),
                                        "betrag": "4000"}, PDF)
    return bh, ks, kiez, akte


class TestForderungsPost(unittest.TestCase):
    def test_1_erkennung(self):
        bh, ks, kiez, akte = _mit_rechnung()
        e = bh.eintraege()
        self.assertEqual(eigene_forderung(ANWALT_BRIEF, e), "RG-11052026")                    # „Rechnung Nr. 11052026“
        self.assertEqual(eigene_forderung("Betreff: RG-11052026 offen", e), "RG-11052026")
        self.assertEqual(eigene_forderung("Moin Sarah, die Kiezalm hat sich nicht gemeldet? Mahnverfahren?", e),
                         "RG-11052026")                                                            # Name + Vokabular
        self.assertEqual(eigene_forderung("Kostennote Rechtsanwaeltin zur Sache RG-11052026: 480,17 EUR", e), "")
        self.assertEqual(eigene_forderung("Rechnung Nr. 12345678 Canva Pro 12,00 EUR", e), "")
        self.assertEqual(eigene_forderung("Kiez Alm Speisekarte Herbst", e), "")                  # Name ohne Forderung

    def test_2_mail_in_akte_statt_beleg(self):
        bh, ks, kiez, akte = _mit_rechnung()
        roh = _mail(MOIN, "WG: Offene Forderung", text=(
            "Anfang der weitergeleiteten Nachricht:\n\nVon: info@kanzlei-muster.de\nBetreff: Offene Forderung\n"
            "Datum: 8. September 2026\n\nanliegend erhalten Sie mein heutiges Schreiben vorab per Mail."),
            anhaenge=[("Schreiben.pdf", _pdf(ANWALT_BRIEF))])
        g = _G({"m1": roh})
        st = EingangStore(bh)
        self.assertEqual(mail_eingang_pruefen(st, g, absender=ABS), [])                          # kein Beleg
        self.assertEqual(st.liste(), [])
        neu = mails_pruefen(akte, g, ceo=ABS, luna=LUNA)
        self.assertEqual(len(neu), 1)
        dok = akte.zu_bezug("RG-11052026")
        self.assertEqual(len(dok), 1)
        self.assertEqual(dok[0]["firma"], kiez)


class TestSelgros(unittest.TestCase):
    def test_1_positionen_brutto(self):
        r = selgros_lesen(SELGROS)
        self.assertEqual(r["lieferant"], "Transgourmet Deutschland GmbH & Co. OHG (Selgros Musterstadt)")
        self.assertEqual([p["text"] for p in r["positionen"]],
                         ["RINDERSTEAK CA.2KG AE FR", "HONIGTOMATE CHERRY KL.I NIEDERLANDE", "VENUSMUSCH.50/70 TK 1KG",
                          "TRAGETASCHE"])
        self.assertEqual(sum(cent(p["betrag"]) for p in r["positionen"]), 6471)               # = EUR 64,71
        self.assertEqual(r["betrag"], "64,71")
        v = vorschlag_regeln(SELGROS)
        self.assertEqual((v["lieferant"][:12], len(v["positionen"])), ("Transgourmet", 4))
        self.assertIsNone(selgros_lesen("Rechnung Canva 12,00 EUR"))

    def test_2_kartenbeleg_ist_nachweis(self):
        bh, ks, k, kiez, akte = _setup()
        st = EingangStore(bh)
        roh = _mail(MOIN, "WG: Ihre Kassenrechnung", text="Anfang der weitergeleiteten Nachricht:\n\nVon: rechnung@selgros.de\n",
                    anhaenge=[("1234.1.PDF", _pdf(SELGROS)), ("1234.2.PDF", _pdf(KARTE))])
        neu = mail_eingang_pruefen(st, _G({"s1": roh}), absender=ABS)
        self.assertEqual(len(neu), 1)
        b = st.get(neu[0])
        self.assertEqual([x.get("rolle") for x in b["belege"]], [None, "zahlungsnachweis"])
        self.assertEqual(len(b["vorschlag"]["positionen"]), 4)


if __name__ == "__main__":
    unittest.main()
