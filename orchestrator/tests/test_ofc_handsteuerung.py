"""OFC_TICKETVERSAND TV6/TV7: Handsteuerung -- bezahlt / nicht bezahlt von Hand nur mit Grund ("nicht bezahlt" ueberstimmt
auch eine zugeordnete PayPal-Zahlung, Kasse und Zuordnung bleiben), Ticketmail je Person auch vor der Zahlung (nur von Hand,
nur mit Kommentar, ohne Dank, mit Zahlungshinweis; die Automatik sendet dann nie). Kein echter Versand."""
import unittest

from orchestrator.core import ofc_versand
from orchestrator.core.ofc_eingang import bezahlt_stand
from orchestrator.core.ofc_kasse import kassenbuch
from orchestrator.core.ofc_store import bezahlt_markieren, spiel_detail, tickets_je_mitglied
from orchestrator.core.ofc_wallet import wallet_von_hand
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc_tv4 import AN, _Basis
from orchestrator.tests.test_ofc_versand import MITGLIEDER, FakePf

T1, T2 = "262236181415-1", "262236181415-2"
SP = "HSV vs FCB"


class _Hand(_Basis):
    def wallets(self):
        for nr in (T1, T2):
            wallet_von_hand(self.st, nr, f"https://www.eventimsports.de/wallet/{nr}/x")

    def bz(self, nr):
        return bezahlt_stand(self.st.stand())["tickets"][nr]


class TestGrundPflicht(_Hand):
    def test_jede_hand_aenderung_braucht_grund(self):
        for kw in ({}, {"notiz": ""}, {"notiz": "  ab "}):
            self.assertFalse(bezahlt_markieren(self.st, [T1], True, art="bar", **kw)["ok"], kw)
            self.assertFalse(bezahlt_markieren(self.st, [T1], False, nicht=True, **kw)["ok"], kw)
        self.assertNotIn("hand_bezahlt", self.st.stand()["tickets"][T1])                      # nichts gespeichert
        self.assertTrue(bezahlt_markieren(self.st, [T1], True, art="bar", notiz="bar am Stadion")["ok"])
        self.assertFalse(bezahlt_markieren(self.st, [T1], False, notiz="")["ok"])               # Zuruecknehmen auch nur mit Grund
        self.assertTrue(self.bz(T1)["bezahlt"])
        self.assertFalse(bezahlt_markieren(self.st, [T1], True, nicht=True, notiz="beides")["ok"])


class TestNichtBezahlt(_Hand):
    def test_ueberstimmt_paypal_kasse_und_zuordnung_bleiben(self):
        self.wallets()
        self.eingang("11-1004", 2 * self.preis)                                                  # per Zweck zugeordnet
        self.assertTrue(self.bz(T1)["bezahlt"])
        kasse = kassenbuch(self.st.stand())["buchungen"]
        eingaenge = self.st.stand()["eingaenge"]
        r = bezahlt_markieren(self.st, [T1], False, nicht=True, notiz="PayPal zurueckgebucht")
        self.assertEqual(r["geaendert"], 1)
        b = self.bz(T1)
        self.assertFalse(b["bezahlt"])
        self.assertEqual(b["bezahlt_cent"], 0)
        self.assertTrue(b["paypal_zugeordnet"])
        self.assertTrue(self.bz(T2)["bezahlt"])                                                   # nur die eine Karte
        self.assertEqual(kassenbuch(self.st.stand())["buchungen"], kasse)                         # Kasse unberuehrt
        self.assertEqual(self.st.stand()["eingaenge"], eingaenge)                                 # Zuordnung unberuehrt
        g = ofc_versand.plan(self.st.stand(), SP, MITGLIEDER)["gruppen"][0]                       # Zahlungsbitte wieder moeglich
        self.assertEqual(([x["ticketnr"] for x in g["tickets"]], g["betrag_cent"], g["status"]), ([T1], self.preis, "bereit"))
        self.assertEqual(tickets_je_mitglied(self.st, "1004")["offen_cent"], self.preis)
        self.assertEqual(bezahlt_markieren(self.st, [T1], False, nicht=True, notiz="nochmal")["geaendert"], 0)   # nicht doppelt
        bezahlt_markieren(self.st, [T1], False, notiz="doch bezahlt")                             # zuruecknehmen
        self.assertTrue(self.bz(T1)["bezahlt"])                                                   # PayPal zaehlt wieder
        self.assertEqual(bezahlt_markieren(self.st, [T1], False, notiz="nichts da")["geaendert"], 0)

    def test_automatik_sendet_nicht(self):
        self.wallets()
        bezahlt_markieren(self.st, [T1, T2], False, nicht=True, notiz="Rueckbuchung erwartet")
        self.eingang("11-1004", 2 * self.preis)
        pf = FakePf()
        r = ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)
        self.assertEqual((r["gesendet"], r["fehler"]), (0, []))                                  # gar nicht erst versucht
        self.assertEqual(pf.gesendet, [])
        bezahlt_markieren(self.st, [T1, T2], False, notiz="Zahlung ok")                         # Gegenprobe: zurueck -> Automatik
        self.assertEqual(ofc_versand.auto_lauf(self.st, pf, MITGLIEDER, env=AN)["gesendet"], 1)

    def test_verlauf_im_spiel(self):
        bezahlt_markieren(self.st, [T1], True, art="bar", notiz="bar am Stadion")
        bezahlt_markieren(self.st, [T1], False, nicht=True, notiz="Schein war falsch")
        v = spiel_detail(self.st, SP)["hand_verlauf"]
        self.assertEqual([(x["ticketnr"], x["nicht_bezahlt"], x["notiz"]) for x in v],
                         [(T1, True, "Schein war falsch"), (T1, False, "bar am Stadion")])


class TestVorZahlung(_Hand):
    def test_plan_zeigt_unbezahlte(self):
        self.wallets()
        g = ofc_versand.tickets_plan(self.st.stand(), SP, MITGLIEDER)["gruppen"][0]
        self.assertEqual((g["status"], g["vor_zahlung"], g["unbezahlt"], g["offen_cent"], g["verwendungszweck"]),
                         ("bereit", True, 2, 2 * self.preis, "11-1004"))
        bezahlt_markieren(self.st, [T1, T2], True, art="bar", notiz="bar")
        g = ofc_versand.tickets_plan(self.st.stand(), SP, MITGLIEDER)["gruppen"][0]
        self.assertEqual((g["vor_zahlung"], g["unbezahlt"]), (False, 0))

    def test_nur_mit_kommentar_ohne_dank_mit_zahlungshinweis(self):
        self.wallets()
        pf = FakePf()
        for k in ("", "  x "):
            r = ofc_versand.tickets_senden(self.st, pf, SP, "1004", MITGLIEDER, kommentar=k)
            self.assertFalse(r["ok"])
            self.assertIn("Kommentar", r["hinweis"])
        self.assertEqual(pf.gesendet, [])
        self.assertTrue(ofc_versand.tickets_senden(self.st, pf, SP, "1004", MITGLIEDER, test=True)["ok"])   # Testmail ohne Kommentar
        r = ofc_versand.tickets_senden(self.st, pf, SP, "1004", MITGLIEDER, kommentar="zahlt bar am Stadion")
        self.assertTrue(r["ok"], r)
        an, betreff, text, kw = pf.gesendet[-1]
        self.assertEqual(an, "anna@example.org")
        self.assertNotIn("danke für deine Zahlung", text)
        self.assertIn("moin@hsvinside.de", text)
        self.assertIn("11-1004", text)
        self.assertEqual(len(kw["anhaenge"]), 2)
        m = [x for x in self.st.stand()["mails"].values() if x["art"] == "tickets" and not x["test"]][0]
        self.assertEqual((m["vor_zahlung"], m["kommentar"]), (True, "zahlt bar am Stadion"))

    def test_nach_zahlung_mit_dank_ohne_kommentar(self):
        self.wallets()
        bezahlt_markieren(self.st, [T1, T2], True, art="bar", notiz="bar")
        pf = FakePf()
        self.assertTrue(ofc_versand.tickets_senden(self.st, pf, SP, "1004", MITGLIEDER)["ok"])
        self.assertIn("danke für deine Zahlung", pf.gesendet[-1][2])

    def test_automatik_nie_vor_zahlung(self):
        self.wallets()
        pf = FakePf()
        r = ofc_versand.tickets_senden(self.st, pf, SP, "1004", MITGLIEDER, auto=True, kommentar="egal")
        self.assertFalse(r["ok"])
        self.assertEqual(pf.gesendet, [])


class TestApi(ApiBasis):
    def test_grund_und_kommentar_ueber_api(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from orchestrator.core import ofc
        from orchestrator.core.ofc_store import OfcStore, import_anwenden, mitglied_setzen
        from orchestrator.tests.test_ofc import _pdf_als_text
        from orchestrator.tests.test_ofc_store import _saison
        with tempfile.TemporaryDirectory() as tmp:
            saison = _saison(Path(tmp))
            st = OfcStore(Path(tmp) / "fanclub")
            with mock.patch.object(ofc, "pdf_text", _pdf_als_text), mock.patch.object(ofc, "nas_ordner", return_value=saison):
                import_anwenden(st, saison)
                mitglied_setzen(st, T1, "1004")
                pf = FakePf()
                pf.verfuegbar = lambda: True
                with mock.patch.object(self.w, "_ofc_store", return_value=st), \
                        mock.patch.object(self.w, "_ofc_postfach", return_value=pf), \
                        mock.patch.object(self.w, "_ofc_mitglieder_daten", return_value={"mitglieder": MITGLIEDER}):
                    url = "/api/ofc/tickets/bezahlt"
                    self.assertFalse(self.c.post(url, json={"bestaetigt": True, "tickets": [T1], "nicht": True}).json()["ok"])
                    self.assertTrue(self.c.post(url, json={"bestaetigt": True, "tickets": [T1], "nicht": True, "notiz": "Rueckbuchung"}).json()["ok"])
                    self.assertTrue(st.stand()["tickets"][T1]["hand_bezahlt"]["nicht_bezahlt"])
                    url = f"/api/ofc/spiel/{SP}/tickets_senden"
                    self.assertFalse(self.c.post(url, json={"bestaetigt": True, "nummer": "1004"}).json()["ok"])
                    self.assertEqual(pf.gesendet, [])
                    r = self.c.post(url, json={"bestaetigt": True, "nummer": "1004", "kommentar": "zahlt bar"}).json()
                    self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
