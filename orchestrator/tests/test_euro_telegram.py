"""CEO 2026-09-28: Euro-Betrag einer Fremdwaehrungs-Zahlung per Telegram schicken -> Zuordnung, Vorschau, nach ✅
buchen + Geldeingang + Kalender-Erinnerung weg. Regelbasiert, gebucht wird nur nach dem Klick."""
import unittest
from datetime import date

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eingangsbelege import (EingangStore, euro_buchen, euro_vorschau, euro_zuordnen,
                                              fremdwaehrung_erinnern, offene_fremdwaehrung)
from orchestrator.core.erinnerungen import erledigte_entfernen
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.todos import geschaefts_todos
from orchestrator.governance.google_workspace import MockGoogleWorkspace
from orchestrator.tests.test_angebote import _stores
from orchestrator.tests.test_eingangsbelege import _pdf

H = jetzt().date()
META = (f"Meta Platforms Ireland Ltd.\nREMITTANCE\nPayment Number: 29163590826663755\nPayment Date: "
        f"{H.day:02d}-{H.strftime('%b')}-{H.year}\nPayment Currency: USD\nTotal: $282.37")


class TestEuroTelegram(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, *_ = _stores()
        self.st = EingangStore(self.bh)
        self.nr = self.st.aufnehmen(_pdf(META), "meta.pdf")["nummer"]

    def test_1_zuordnung(self):
        o = offene_fremdwaehrung(self.st)
        self.assertEqual([x["nummer"] for x in o], [self.nr])
        for text in ("Facebook 241,80", "Meta 241,80 €", "Facebook 241 €", f"{self.nr} 241,80", "241,80 € sind auf dem Konto", "fb: 241.80 euro"):
            z = euro_zuordnen(text, o)
            self.assertIsNotNone(z, text)
            self.assertEqual((z["nummer"], z["betrag_cent"]), (self.nr, 24100 if "241 €" in text else 24180), text)
        z = euro_zuordnen("Facebook 241,80 am 26.09.", o, heute=date(2026, 10, 2))
        self.assertEqual((z["datum"], z["datum_angegeben"]), ("2026-09-26", True))
        z = euro_zuordnen("Facebook 241,80 am 28.12.", o, heute=date(2027, 1, 3))            # Vorjahr
        self.assertEqual(z["datum"], "2026-12-28")
        for text in ("Wie viel hat Facebook 2026 gezahlt?", "Hallo LUNA", "Meta 241,80 und 12,00",
                     "Ruf mich um 14 Uhr an", "Facebook hat 2026 gut funktioniert", "Meta 241,80?"):
            self.assertIsNone(euro_zuordnen(text, o), text)
        self.assertIsNone(euro_zuordnen("Facebook 241,80", []))                           # nichts offen -> Chat
        self.assertIn("282,37 USD → 241,80 €", euro_vorschau(euro_zuordnen("Facebook 241,80", o)))

    def test_2_zwei_offene_brauchen_nummer(self):
        n2 = self.st.aufnehmen(_pdf(META.replace("29163590826663755", "1111")), "meta2.pdf")["nummer"]
        o = offene_fremdwaehrung(self.st)
        self.assertIsNone(euro_zuordnen("Facebook 241,80", o))                            # mehrdeutig
        self.assertEqual(euro_zuordnen(f"{n2} 99,10 €", o)["nummer"], n2)

    def test_3_buchen_loescht_erinnerung_und_todo(self):
        g = MockGoogleWorkspace()
        fremdwaehrung_erinnern(self.st, g)
        tid = f"bl-euro:{self.nr}"
        self.assertIn(tid, {t["id"] for t in geschaefts_todos(self.bh, self.ks)})
        r = euro_buchen(self.st, self.nr, 24180, H.isoformat())
        self.assertEqual(r["art"], "einnahme")
        x = self.st.get(self.nr)
        self.assertEqual((x["status"], x["felder"]["betrag_cent"], x["felder"]["kategorie"], x["bezahlt_am"]),
                         ("gebucht", 24180, "umsatz", H.isoformat()))
        self.assertIn("282,37 USD", x["felder"]["notiz"])
        weg = erledigte_entfernen(self.bh, g)
        self.assertEqual([w["bezug"] for w in weg], [self.nr])
        self.assertEqual(g.geloeschte_termine, [weg[0]["id"]])
        self.assertNotIn(tid, {t["id"] for t in geschaefts_todos(self.bh, self.ks)})
        self.assertEqual(Finanzen(self.bh, self.ks).euer(H.year)["einnahmen_cent"], 24180)
        with self.assertRaises(ValueError):
            euro_buchen(self.st, self.nr, 24180, H.isoformat())                             # doppelt -> nein


if __name__ == "__main__":
    unittest.main()
