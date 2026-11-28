"""OFC_TICKETVERSAND TV4: Zahlung ueber den Verwendungszweck zuordnen (Code + genauer Betrag), Tickets senden (PDF-Anhang +
Wallet-Links), automatisch nur wenn alles eindeutig ist und der Schalter an ist; nie doppelt. Kein echter Versand."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc, ofc_versand
from orchestrator.core.ofc_eingang import _offen, vorschlag, zweck_treffer
from orchestrator.core.ofc_store import OfcStore, bezahlt_markieren, import_anwenden, mitglied_setzen, person_speichern
from orchestrator.core.ofc_wallet import wallet_von_hand
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_store import _saison
from orchestrator.tests.test_ofc_versand import MITGLIEDER, FakePf

AN = {"OFC_AUTO_TICKETVERSAND": "1"}


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.saison = _saison(d)
        (self.saison / "HSV vs FCB" / "262236181415-2.pdf").write_text("Ticketnummer: 262236181415-2", encoding="utf-8")
        self.p = [mock.patch.object(ofc, "pdf_text", _pdf_als_text), mock.patch.object(ofc, "nas_ordner", return_value=self.saison)]
        for x in self.p:
            x.start()
        self.st = OfcStore(d / "fanclub")
        import_anwenden(self.st, self.saison)
        mitglied_setzen(self.st, "262236181415-1", "1004")
        mitglied_setzen(self.st, "262236181415-2", "1004")
        self.preis = self.st.stand()["tickets"]["262236181415-1"]["preis_cent"]

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.tmp.cleanup()

    def eingang(self, mitteilung, betrag, datum=None, eid="e-1"):
        z = {"id": eid, "name": "Irgendwer Anders", "betrag_cent": betrag, "mitteilung": mitteilung,
             "datum": datum or date.today().isoformat(), "transaktionscode": eid}
        e = z | vorschlag(z, self.st.stand(), _offen(self.st.stand()))
        self.st.erfassen("ofc_eingang", {k: v for k, v in e.items() if k != "vorschlaege"})
        return e


class TestZweck(_Basis):
    def test_code_und_genauer_betrag(self):
        st = self.st.stand()
        z = {"name": "X", "betrag_cent": 2 * self.preis, "mitteilung": "Karten 11-1004 danke"}
        self.assertEqual(zweck_treffer(z, st, _offen(st))["tickets"], ["262236181415-1", "262236181415-2"])
        for text in ("11 1004", "11/1004", "11-1004!"):
            self.assertTrue(zweck_treffer(z | {"mitteilung": text}, st, _offen(st)), text)
        self.assertIsNone(zweck_treffer(z | {"betrag_cent": self.preis}, st, _offen(st)))        # Betrag passt nicht
        self.assertIsNone(zweck_treffer(z | {"mitteilung": "12-1004"}, st, _offen(st)))          # anderer Spieltag
        self.assertIsNone(zweck_treffer(z | {"mitteilung": "11-1005"}, st, _offen(st)))          # andere Nummer
        self.assertIsNone(zweck_treffer(z | {"mitteilung": "2:1 gewonnen, 1-0 Halbzeit"}, st, _offen(st)))
        v = vorschlag(z | {"id": "x", "datum": "2026-11-27"}, st, _offen(st))
        self.assertEqual((v["zuordnung"], v["zweck"]), ("auto", "11-1004"))

    def test_fuehrende_nullen_und_externe(self):
        mitglied_setzen(self.st, "262236181415-1", "0001")
        pid = person_speichern(self.st, "Kim", "Gast", "kim@example.org")["id"]
        mitglied_setzen(self.st, "262236181415-2", pid)
        st = self.st.stand()
        self.assertTrue(zweck_treffer({"betrag_cent": self.preis, "mitteilung": "11-1"}, st, _offen(st)))
        self.assertTrue(zweck_treffer({"betrag_cent": self.preis, "mitteilung": "11-g1"}, st, _offen(st)))
        self.assertIsNone(zweck_treffer({"betrag_cent": self.preis, "mitteilung": "11-1"}, st | {"tickets": {}}, {}))


class TestTicketsSenden(_Basis):
    def bereit(self):
        bezahlt_markieren(self.st, ["262236181415-1", "262236181415-2"], True, art="bar", notiz="bar bezahlt")
        for nr in ("262236181415-1", "262236181415-2"):
            wallet_von_hand(self.st, nr, f"https://www.eventimsports.de/wallet/{nr}/x")

    def test_plan_und_senden_mit_anhang(self):
        self.assertTrue(ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["vor_zahlung"])  # nichts bezahlt
        self.bereit()
        g = ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]
        self.assertEqual((g["status"], g["hinweis"]), ("bereit", ""))
        pf = FakePf()
        r = ofc_versand.tickets_senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER)
        self.assertTrue(r["ok"], r)
        an, betreff, text, kw = pf.gesendet[-1]
        self.assertEqual(an, "anna@example.org")
        self.assertEqual([a[0] for a in kw["anhaenge"]], ["262236181415-1-Anna.pdf", "262236181415-2.pdf"])
        self.assertTrue(all(a[2] == "application/pdf" and a[1] for a in kw["anhaenge"]))
        self.assertIn("eventimsports.de/wallet/262236181415-2/x", text)
        self.assertTrue(kw["ofc_freigabe"])
        self.assertFalse(ofc_versand.tickets_senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER)["ok"])   # nicht doppelt
        self.assertTrue(ofc_versand.tickets_senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, erneut=True)["ok"])
        self.assertEqual(ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["status"], "gesendet")

    def test_test_an_moin_zaehlt_nicht(self):
        self.bereit()
        pf = FakePf()
        self.assertTrue(ofc_versand.tickets_senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, test=True)["ok"])
        self.assertEqual(pf.gesendet[-1][0], "moin@hsvinside.de")
        self.assertEqual(ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["status"], "bereit")

    def test_pdf_fehlt_gesperrt(self):
        self.bereit()
        (self.saison / "HSV vs FCB" / "262236181415-2.pdf").rename(self.saison / "HSV vs FCB" / "weg.txt")
        import_anwenden(self.st, self.saison)
        g = ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]
        self.assertEqual(g["status"], "gesperrt")

    def test_ohne_adresse_gesperrt(self):
        self.bereit()
        mitglied_setzen(self.st, "262236181415-1", "1005")
        g = {x["nummer"]: x for x in ofc_versand.tickets_plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"]}
        self.assertEqual(g["1005"]["status"], "gesperrt")


class TestAuto(_Basis):
    def test_auto_nur_eindeutig_mit_schalter(self):
        for nr in ("262236181415-1", "262236181415-2"):
            wallet_von_hand(self.st, nr, f"https://www.eventimsports.de/wallet/{nr}/x")
        pf = FakePf()
        self.eingang("11-1004", 2 * self.preis)
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env={})["gesendet"], 0)          # Schalter aus
        self.assertEqual(pf.gesendet, [])
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)["gesendet"], 1)
        self.assertEqual(pf.gesendet[-1][0], "anna@example.org")
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)["gesendet"], 0)          # nie doppelt
        self.assertTrue(self.st.stand()["mails"] and all(m["auto"] for m in self.st.stand()["mails"].values()))

    def test_kein_auto_bei_zuordnung_ueber_namen(self):
        for nr in ("262236181415-1", "262236181415-2"):
            wallet_von_hand(self.st, nr, f"https://www.eventimsports.de/wallet/{nr}/x")
        self.st.erfassen("ofc_eingang", {"id": "e-name", "name": "Anna Muster", "betrag_cent": 2 * self.preis, "mitteilung": "Bayern",
                                         "datum": date.today().isoformat(), "zuordnung": "auto",
                                         "tickets": ["262236181415-1", "262236181415-2"], "art": "ticket"})
        pf = FakePf()
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)["gesendet"], 0)   # nur per Verwendungszweck
        self.assertEqual(pf.gesendet, [])

    def test_kein_auto_ohne_wallet_ohne_zweck_oder_alt(self):
        pf = FakePf()
        self.eingang("11-1004", 2 * self.preis)
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)["gesendet"], 0)          # Wallet fehlt
        bezahlt_markieren(self.st, ["262236181415-1", "262236181415-2"], False, notiz="zurueck")
        for nr in ("262236181415-1", "262236181415-2"):
            wallet_von_hand(self.st, nr, f"https://www.eventimsports.de/wallet/{nr}/x")
        bezahlt_markieren(self.st, ["262236181415-1", "262236181415-2"], True, notiz="bar")                # von Hand bezahlt
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN, heute=date(2099, 1, 1))["gesendet"], 0)  # Zahlung alt
        self.assertEqual(pf.gesendet, [])


class TestApi(ApiBasis):
    def test_nur_ceo(self):
        with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
            self.assertEqual(self.c.get("/api/ofc/spiel/X/ticketversand").status_code, 403)
            self.assertEqual(self.c.post("/api/ofc/spiel/X/tickets_senden", json={"bestaetigt": True}).status_code, 403)
        self.assertFalse(self.c.post("/api/ofc/spiel/X/tickets_senden", json={"nummer": "1"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
