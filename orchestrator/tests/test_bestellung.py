"""Bestellbestaetigung -> Eigenbeleg: Vorschlag aus der weitergeleiteten Mail (Betrag, Datum, Haendler, Bestellnummer,
Zweck), Buchung nur per Klick mit Mail als Nachweis, kein Doppel, Erinnerung bis gebucht oder „keine Firmenausgabe“."""
import unittest
from email.message import EmailMessage

from orchestrator.core.bestellung import betrag_lesen, ist_bestellung, offene, todos, vorschlag
from orchestrator.core.firmenakte import Firmenakte
from orchestrator.tests.test_angebote import ApiBasis


def weitergeleitet(betreff="Bestellt: „PUMA Unisex Anzarun Lite...“", summe="Summe 34.99€"):
    m = EmailMessage()
    m["From"], m["To"] = "Nils <hsvnils@icloud.com>", "luna.hanserautisch@gmail.com"
    m["Subject"], m["Date"] = f"Fwd: {betreff}", "Wed, 30 Sep 2026 13:40:35 +0200"
    m.set_content("Für das drehen von Content im Athleticum gekauft\n\nVon meinem iPhone gesendet\n\n"
                  "Anfang der weitergeleiteten Nachricht:\n\n"
                  'Von: "Amazon.de" <bestellbestaetigung@amazon.de>\n'
                  f"Betreff: {betreff}\nDatum: 30. September 2026 um 13:39:12 MESZ\nAn: hsvnils@icloud.com\n\n"
                  "Ankunft morgen\nNils – Tangstedt\nBestellnr. 305-4067967-3366747\nBestellung ansehen oder ändern\n"
                  f"PUMA Unisex Anzarun Lite Niedrig\nMenge: 1\n{summe}\n")
    return m.as_bytes()


class TestLesen(unittest.TestCase):
    def test_betrag(self):
        self.assertEqual(betrag_lesen("Summe 34.99€"), "34,99")
        self.assertEqual(betrag_lesen("Gesamtsumme: 1.234,56 €"), "1234,56")
        self.assertEqual(betrag_lesen("Gesamtbetrag EUR 12,00"), "12,00")
        self.assertEqual(betrag_lesen("Danke für Ihren Einkauf"), "")
        self.assertTrue(ist_bestellung("Bestellt: „PUMA …“"))
        self.assertTrue(ist_bestellung("Ihre Bestellung bei Thomann"))
        self.assertFalse(ist_bestellung("Rechnung 4711"))

    def test_vorschlag(self):
        v = vorschlag(weitergeleitet())
        self.assertEqual((v["betrag"], v["datum"], v["gegenpartei"], v["referenz"]),
                         ("34,99", "2026-09-30", "Amazon.de", "Bestellnr. 305-4067967-3366747"))
        self.assertIn("Athleticum", v["zweck"])
        self.assertTrue(v["text"].startswith("Bestellung Amazon.de: PUMA Unisex Anzarun Lite"))
        self.assertIn("Athleticum", v["text"])


class TestApi(ApiBasis):
    def _mail(self, **kw):
        ks = self.w.kunden_store
        return Firmenakte(ks.bh, ks).mail_aufnehmen(weitergeleitet(**kw), "gm-" + str(len(ks.bh.eintraege())),
                                                   eigene=["hsvnils@icloud.com"], weitergeleitet=True)["id"]

    def test_buchen_mit_nachweis(self):
        bh = self.w.kunden_store.bh
        mid = self._mail()
        self.assertEqual([t["act_id"] for t in todos(bh.eintraege())], [mid])               # Erinnerung
        v = self.c.get(f"/api/finanzen/bestellung/{mid}/vorschlag").json()
        self.assertEqual((v["betrag"], v["nachweis"]), ("34,99", mid))
        buchung = {"art": "ausgabe", "datum": v["datum"], "betrag": v["betrag"], "kategorie": "sonstiges", "text": v["text"],
                   "gegenpartei": v["gegenpartei"], "referenz": v["referenz"], "nachweis": mid}
        r = self.c.post("/api/finanzen/eigenbelege", json={"buchung": buchung}).json()
        self.assertTrue(r["ok"], r)
        eb = next(x for x in self.c.get("/api/finanzen/eigenbelege").json()["eigenbelege"] if x["nummer"] == r["nummer"])
        self.assertEqual((eb["betrag_cent"], eb["nachweis"]["akte_id"]), (3499, mid))
        self.assertEqual(offene(bh.eintraege()), [])                                         # gebucht -> keine Erinnerung
        r2 = self.c.post("/api/finanzen/eigenbelege", json={"buchung": buchung}).json()
        self.assertFalse(r2["ok"])
        self.assertIn("schon gebucht", r2["hinweis"])                                       # kein Doppel
        bad = self.c.post("/api/finanzen/eigenbelege", json={"buchung": buchung | {"nachweis": "D-00000000"}}).json()
        self.assertFalse(bad["ok"])
        self.assertEqual(self.c.get("/api/finanzen/bestellung/D-00000000/vorschlag").status_code, 404)

    def test_keine_firmenausgabe(self):
        bh = self.w.kunden_store.bh
        mid = self._mail(betreff="Bestellt: „Kaffeemaschine“", summe="Summe 99.00€")
        self.assertTrue(self.c.post(f"/api/finanzen/bestellung/{mid}/keine-ausgabe", json={}).json()["ok"])
        self.assertEqual(todos(bh.eintraege()), [])
        self.assertFalse(self.c.post("/api/finanzen/bestellung/D-00000000/keine-ausgabe", json={}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
