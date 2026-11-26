"""OFC_TICKETVERSAND TV3: Zahlungsbitte aus moin@ -- Senden nur aus dem OFC-Versand, nur ein Empfaenger, abschaltbar; Plan je
Mitglied (Verwendungszweck <Spieltag>-<Nummer>, Adresse aus der Liste, gesperrt ohne Spieltag/Adresse); nie doppelt ohne
„erneut“, Testmail an moin@, Limit je Stunde, Protokoll ohne Text; Endpunkte nur CEO. Kein echter Versand."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc, ofc_versand
from orchestrator.core.ofc_store import OfcStore, import_anwenden, mitglied_setzen, person_speichern, spieltag_setzen
from orchestrator.governance.allinkl_mail import HsvInsideMail
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import ENV, _pdf_als_text
from orchestrator.tests.test_ofc_store import _saison

MITGLIEDER = [{"nummer": "1004", "name": "Anna Muster", "vorname": "Anna", "email": "anna@example.org"},
              {"nummer": "1005", "name": "Bert Ohne", "vorname": "Bert", "email": ""}]


class FakeSMTP:
    def __init__(self, log):
        self.log = log

    def login(self, u, p):
        self.log.append(("login", u))

    def send_message(self, msg, to_addrs=None):
        self.log.append(("send", list(to_addrs), msg["From"], msg["Subject"], msg.get_content()))

    def quit(self):
        pass


class FakePf:
    def __init__(self):
        self.gesendet = []

    def verfuegbar(self):
        return True

    def mail_senden(self, an, betreff, text, **kw):
        self.gesendet.append((an, betreff, text, kw))
        return {"ok": True, "message_id": "<x@hsvinside.de>", "gesendet_ordner": "Gesendet"}


class TestPostfachSenden(unittest.TestCase):
    def _pf(self, env=ENV):
        log = []
        pf = HsvInsideMail(env, imap_fabrik=lambda: (_ for _ in ()).throw(OSError("kein IMAP im Test")))
        pf._smtp = lambda: FakeSMTP(log)
        return pf, log

    def test_nur_aus_ofc_versand_ein_empfaenger_abschaltbar(self):
        pf, log = self._pf()
        self.assertEqual(pf.smtp_host, ENV["HSVINSIDE_IMAP_HOST"])                       # gleicher All-Inkl-Server
        self.assertFalse(pf.mail_senden("a@example.org", "B", "T", bestaetigt=True)["ok"])  # ohne ofc_freigabe
        self.assertFalse(pf.mail_senden("a@example.org, b@example.org", "B", "T", bestaetigt=True, ofc_freigabe=True)["ok"])
        self.assertFalse(pf.mail_senden("a@example.org", "B", "T", ofc_freigabe=True)["ok"])  # ohne Bestaetigung
        self.assertEqual(log, [])
        r = pf.mail_senden("a@example.org", "B", "T", bestaetigt=True, ofc_freigabe=True)
        self.assertTrue(r["ok"], r)
        self.assertEqual(log[-1][1], ["a@example.org"])
        self.assertIn("HSVInside <moin@hsvinside.de>", log[-1][2])
        aus, log2 = self._pf(ENV | {"OFC_MAILVERSAND": "0"})
        self.assertFalse(aus.mail_senden("a@example.org", "B", "T", bestaetigt=True, ofc_freigabe=True)["ok"])
        self.assertEqual(log2, [])


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        d = Path(self.tmp.name)
        import_anwenden(st := OfcStore(d / "fanclub"), _saison(d))
        self.st = st
        mitglied_setzen(st, "262236181415-1", "1004")
        mitglied_setzen(st, "262236181415-2", "1004")

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()


class TestPlanUndSenden(_Basis):
    def test_plan(self):
        mitglied_setzen(self.st, "262236189999-1", "1005")
        p = ofc_versand.plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)
        g = {x["nummer"]: x for x in p["gruppen"]}
        self.assertEqual(g["1004"]["verwendungszweck"], "11-1004")                      # Spieltag 11 aus dem Spielplan
        self.assertEqual((g["1004"]["status"], len(g["1004"]["tickets"])), ("bereit", 2))
        self.assertEqual(g["1004"]["adresse_maskiert"], "a…@example.org")
        self.assertEqual(g["1005"]["status"], "gesperrt")                               # keine Adresse
        self.assertEqual(ofc_versand.plan(self.st.stand(), "HSV vs FCB", None)["gruppen"][0]["status"], "gesperrt")
        spieltag_setzen(self.st, "SVW vs HSV", "")
        mitglied_setzen(self.st, "162236525621-7", "1004")
        self.assertIn("Spieltag fehlt", ofc_versand.plan(self.st.stand(), "SVW vs HSV", MITGLIEDER)["gruppen"][0]["hinweis"])

    def test_text_ohne_ki_mit_betrag_und_zweck(self):
        v = ofc_versand.vorschau(self.st.stand(), "HSV vs FCB", "1004", MITGLIEDER)
        self.assertTrue(v["text"].startswith("Moin Anna,"))
        self.assertIn("Verwendungszweck: 11-1004", v["text"])
        self.assertIn("per PayPal an moin@hsvinside.de", v["text"])
        self.assertIn("Block", v["text"])

    def test_senden_nie_doppelt_test_an_moin_limit(self):
        pf = FakePf()
        r = ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, test=True)
        self.assertTrue(r["ok"])
        self.assertEqual(pf.gesendet[-1][0], "moin@hsvinside.de")
        self.assertTrue(pf.gesendet[-1][1].startswith("[TEST] "))
        self.assertTrue(pf.gesendet[-1][3]["ofc_freigabe"])
        self.assertTrue(ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER)["ok"])   # Test zaehlt nicht als gebeten
        self.assertEqual(pf.gesendet[-1][0], "anna@example.org")
        self.assertFalse(ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER)["ok"])  # Gegenprobe: nicht doppelt
        self.assertTrue(ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, erneut=True)["ok"])
        self.assertEqual(ofc_versand.plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["status"], "gebeten")
        log = json.dumps(self.st.stand()["mails"], ensure_ascii=False)
        self.assertNotIn("anna@example.org", log)                                       # Adresse nur maskiert
        self.assertNotIn("Moin Anna", log)                                              # kein Mailtext im Protokoll
        spaeter = datetime.now(timezone.utc)
        with mock.patch.object(ofc_versand, "LIMIT_STUNDE", 3):
            self.assertIn("Höchstens", ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, erneut=True, jetzt=spaeter)["hinweis"])
            self.assertTrue(ofc_versand.senden(self.st, pf, "HSV vs FCB", "1004", MITGLIEDER, erneut=True,
                                               jetzt=spaeter + timedelta(hours=2))["ok"])

    def test_bezahlt_faellt_raus(self):
        with mock.patch("orchestrator.core.ofc_eingang.bezahlt_stand",
                        return_value={"tickets": {"262236181415-1": {"bezahlt": True}, "262236181415-2": {"bezahlt": True}}}):
            self.assertEqual(ofc_versand.plan(self.st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"], [])


class TestExtern(_Basis):
    def test_person_speichern(self):
        r = person_speichern(self.st, "Kim", "Gast", "kim@example.org")
        self.assertEqual(r, {"ok": True, "id": "G1"})
        self.assertEqual(person_speichern(self.st, "Kim", "Gast", "KIM@example.org")["id"], "G1")   # gleiche Mail = gleiche Person
        self.assertEqual(person_speichern(self.st, "Lu", "", "lu@example.org")["id"], "G2")
        self.assertFalse(person_speichern(self.st, "X", "Y", "keine-mail")["ok"])
        self.assertFalse(person_speichern(self.st, "", "", "a@example.org")["ok"])
        self.assertFalse(person_speichern(self.st, "X", "Y", "", "G9")["ok"])
        person_speichern(self.st, "Kim", "Gastmann", "kim@example.org", "G1")
        self.assertEqual(self.st.stand()["personen"]["G1"]["nachname"], "Gastmann")
        n = len(self.st.eintraege())
        person_speichern(self.st, "Kim", "Gastmann", "kim@example.org", "G1")
        self.assertEqual(len(self.st.eintraege()), n)                                   # unveraendert -> kein Ereignis

    def test_zahlungsbitte_an_externe(self):
        pid = person_speichern(self.st, "Kim", "Gast", "kim@example.org")["id"]
        mitglied_setzen(self.st, "262236181415-2", pid)                                # Karte mit Preis
        p = ofc_versand.plan(self.st.stand(), "HSV vs FCB", None)                       # auch ohne lesbare Mitgliederliste
        g = {x["nummer"]: x for x in p["gruppen"]}[pid]
        self.assertEqual((g["status"], g["verwendungszweck"], g["extern"]), ("bereit", "11-G1", True))
        pf = FakePf()
        self.assertTrue(ofc_versand.senden(self.st, pf, "HSV vs FCB", pid, None)["ok"])
        self.assertEqual(pf.gesendet[-1][0], "kim@example.org")
        self.assertIn("Moin Kim,", pf.gesendet[-1][2])
        self.assertIn("über deinen Fanclub HSVInside", pf.gesendet[-1][2])


class TestApi(ApiBasis):
    def test_nur_ceo_und_bestaetigung(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text):
            st = OfcStore(Path(d) / "fanclub")
            import_anwenden(st, saison := _saison(Path(d)))
            mitglied_setzen(st, "262236181415-1", "1004")
            pf = FakePf()
            self.enterContext(mock.patch.object(ofc, "nas_ordner", return_value=saison))
            with mock.patch.object(self.w, "_ofc_store", return_value=st), mock.patch.object(self.w, "_ofc_postfach", return_value=pf), \
                    mock.patch.object(self.w, "_ofc_mitglieder_daten", return_value={"mitglieder": MITGLIEDER}):
                self.assertEqual(self.c.get("/api/ofc/spiel/HSV vs FCB/zahlungsbitten").json()["bereit"], 1)
                self.assertFalse(self.c.post("/api/ofc/spiel/HSV vs FCB/zahlungsbitte", json={"nummer": "1004"}).json()["ok"])
                self.assertEqual(pf.gesendet, [])
                r = self.c.post("/api/ofc/spiel/HSV vs FCB/zahlungsbitte", json={"bestaetigt": True, "alle": True}).json()
                self.assertEqual(r["gesendet"], 1)
                r = self.c.post("/api/ofc/ticket/262236189999-1/name", json={"bestaetigt": True, "name": "Kim Gast",
                                                                            "extern": {"vorname": "Kim", "nachname": "Gast", "email": "kim@example.org"}}).json()
                self.assertTrue(r["ok"], r)
                self.assertEqual(st.stand()["tickets"]["262236189999-1"]["mitglied"], "G1")
                self.assertFalse(self.c.post("/api/ofc/ticket/262236189999-1/name", json={"bestaetigt": True, "name": "X",
                                                                                         "extern": {"vorname": "X", "email": "kaputt"}}).json()["ok"])
                self.assertEqual(self.c.get("/api/ofc/namen").json()["extern"][0]["id"], "G1")
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    self.assertEqual(self.c.get("/api/ofc/spiel/HSV vs FCB/zahlungsbitten").status_code, 403)
                    self.assertEqual(self.c.post("/api/ofc/spiel/HSV vs FCB/zahlungsbitte", json={"bestaetigt": True}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
