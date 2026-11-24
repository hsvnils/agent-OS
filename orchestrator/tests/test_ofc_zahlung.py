"""OFC_ROADMAP O4: Eigene PayPal-Zahlungen -- Erkennen (gesendet, Später bezahlen, Abbuchung, Erstattung), andere Haendler
und Mitgliederzahlungen ignoriert, Zuordnung (Nummer, Betrag + Datum, Gegner), gleiche Summe zweimal -> nicht automatisch,
Dubletten, Dry-Run, manuell zuordnen/loesen/ignorieren, Hinweise im Reiter, kein Mailtext gespeichert, Endpunkte nur CEO.
Fixtures ohne echte Daten."""
import json
import os
import tempfile
import unittest
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core import ofc_zahlung as oz
from orchestrator.core.ofc_store import OfcStore, import_anwenden, spiel_detail, uebersicht
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_store import _saison


def _pp(betreff: str, text: str, von: str = "service@paypal.de", datum: str = "Tue, 06 Oct 2026 10:00:00 +0200",
        mid: str = "<a@paypal.de>") -> dict:
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"], m["Message-ID"] = von, betreff, datum, mid
    m.set_content(text)
    return {"uid": "1", "roh": m.as_bytes()}


def _gesendet(betrag="70,00", haendler="Hamburger Sport-Verein e.V.", tc="1AB23456CD7890123", extra="", datum="06.10.2026",
              mid="<g@paypal.de>"):
    return _pp(f"Beleg für Ihre Zahlung an {haendler}...",
               f"Hallo Max Kaeufer!\nSie haben {betrag}\xa0€\xa0EUR an {haendler}... gezahlt\nHändler\n{haendler}...\n"
               f"{datum}\n{extra}Gesamtbetrag\n{betrag}\xa0€\xa0EUR\nTransaktionscode: {tc}\n", mid=mid)


SPAETER = _pp("Ihr Kauf bei CTS EVENTIM AG & Co... – Sie bezahlen in 30 Tagen",
              "Hallo, Max\nIhre Zahlung für Ihren Einkauf an Max nach 30 Tagen für Ihre Bestellung über 123,40\xa0€\xa0EUR bei "
              "CTS EVENTIM AG & Co. KGaA.\n123,40\xa0€\xa0EUR\nHändler\nCTS EVENTIM AG & Co\nDatum des Kaufs\n9. Oktober 2026\n",
              mid="<s@paypal.de>")
ABGEBUCHT = _pp("Ihre Zahlung mit PayPal war erfolgreich", "Wir haben 123,40\xa0€\xa0EUR eingezogen.\n08.11.2026\n",
                datum="Sun, 08 Nov 2026 10:00:00 +0100", mid="<ok@paypal.de>")
FEHLER = _pp("Ihre Zahlung konnte nicht eingezogen werden", "Betrag 123,40\xa0€\xa0EUR\n08.11.2026\n", mid="<f@paypal.de>")
MITGLIED = _pp("Sie haben eine Zahlung erhalten", "Erika Muster hat Ihnen 35,00\xa0€\xa0EUR gesendet\nTransaktionscode: 9ZZ99999ZZ9999999",
               mid="<m@paypal.de>")
ANDERER = _gesendet("19,99", "Simple Webshop GmbH", "5CC55555CC5555555", mid="<x@paypal.de>")


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = _saison(self.d)                                                   # HSV vs FCB (Rechnung 70,00 vom 05.10.2026)
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, self.s)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()


class TestLesen(unittest.TestCase):
    def test_1_arten_und_felder(self):
        z = oz.paypal_lesen(_gesendet(extra="Bestellnummer\n12345678\n")["roh"])
        self.assertEqual((z["art"], z["betrag_cent"], z["datum"], z["transaktionscode"], z["bestellnr"], z["id"]),
                         ("gesendet", 7000, "2026-10-06", "1AB23456CD7890123", "12345678", "1AB23456CD7890123"))
        self.assertTrue(z["haendler"].startswith("Hamburger Sport-Verein"))
        s = oz.paypal_lesen(SPAETER["roh"])
        self.assertEqual((s["art"], s["betrag_cent"], s["datum"]), ("spaeter", 12340, "2026-10-09"))
        self.assertIn("EVENTIM", s["haendler"])
        self.assertEqual(oz.paypal_lesen(ABGEBUCHT["roh"])["art"], "abbuchung_ok")
        self.assertEqual(oz.paypal_lesen(FEHLER["roh"])["art"], "abbuchung_fehler")
        e = oz.paypal_lesen(_pp("Rückzahlung von Hamburger Sport-Verein e.V.", "Sie haben 35,00\xa0€\xa0EUR an Hamburger "
                                "Sport-Verein e.V. gezahlt\nRückzahlung erhalten 35,00\xa0€\xa0EUR")["roh"])
        self.assertEqual((e["art"], e["betrag_cent"]), ("erstattung", 3500))
        self.assertIsNone(oz.paypal_lesen(MITGLIED["roh"]))                       # Mitgliederzahlung -> O5
        self.assertIsNone(oz.paypal_lesen(ANDERER["roh"]))                        # anderer Haendler
        self.assertIsNone(oz.paypal_lesen(_gesendet(mid="<y@x>")["roh"].replace(b"paypal.de", b"paypa1.de")))

    def test_2_dubletten(self):
        a = _gesendet()
        self.assertEqual(len(oz.zahlungen_aus_mails([a, a, _gesendet(mid="<andere@paypal.de>")])), 1)   # gleicher Code


class TestZuordnung(_Basis):
    def test_3_auto_ueber_betrag_und_datum_dry_run(self):
        n = len(self.st.eintraege())
        v = oz.zahl_plan(self.st, [_gesendet(), MITGLIED, ANDERER])
        self.assertEqual(len(self.st.eintraege()), n)                             # Dry-Run
        self.assertEqual((len(v["neu"]), v["auto"]), (1, 1))
        z = v["neu"][0]
        self.assertEqual((z["spiel"], z["zuordnung"]), ("HSV vs FCB", "auto"))
        self.assertIn("Betrag = Rechnung", z["vorschlaege"][0]["gruende"])
        oz.zahl_anwenden(self.st, [_gesendet()])
        e = self.st.eintraege()[-1]
        self.assertEqual(e["typ"], "ofc_zahlung")
        self.assertNotIn("_text", e["daten"]); self.assertNotIn("Max", json.dumps(e))   # kein Mailtext gespeichert
        self.assertEqual(oz.zahl_plan(self.st, [_gesendet()])["neu"], [])         # wiederholbar
        d = spiel_detail(self.st, "HSV vs FCB")
        self.assertEqual((d["bezahlt_cent"], len(d["zahlungen"])), (7000, 1))
        self.assertNotIn("Eigene Zahlung nicht zugeordnet", d["hinweise"])

    def test_4_nummer_sicher_gleiche_summe_zweimal_nicht_auto(self):
        z = oz.zahl_plan(self.st, [_gesendet("12,00", extra="Rechnung 262236181415\n")])["neu"][0]
        self.assertEqual((z["spiel"], z["zuordnung"]), ("HSV vs FCB", "auto"))   # Nummer passt, Betrag egal
        zweit = self.s / "HSV vs SGE"
        zweit.mkdir()
        from orchestrator.tests.test_ofc import HEIM
        (zweit / "Rechnung.pdf").write_text(HEIM.replace("262236181415", "262236187777").replace("FC Bayern Muenchen", "Eintracht Frankfurt"),
                                             encoding="utf-8")
        import_anwenden(self.st, self.s)
        z = oz.zahl_plan(self.st, [_gesendet()])["neu"][0]                       # 70,00 passt zu zwei Spielen
        self.assertEqual((z["spiel"], z["zuordnung"]), ("", "offen"))
        self.assertEqual({v["spiel"] for v in z["vorschlaege"][:2]}, {"HSV vs FCB", "HSV vs SGE"})

    def test_5_manuell_loesen_ignorieren_und_hinweise(self):
        oz.zahl_anwenden(self.st, [SPAETER, FEHLER])
        u = uebersicht(self.st, heute=date(2026, 11, 10))
        self.assertEqual(u["zahlungen_offen"], 1)
        fcb = [x for x in u["spiele"] if x["id"] == "HSV vs FCB"][0]
        self.assertIn("Eigene Zahlung nicht zugeordnet", fcb["hinweise"])
        zid = next(iter(self.st.stand()["zahlungen"].values()))["id"]
        zid = [z for z in self.st.stand()["zahlungen"].values() if z["art"] == "spaeter"][0]["id"]
        self.assertTrue(oz.zuordnen(self.st, zid, "HSV vs FCB")["ok"])
        st = oz.zahlungs_status(self.st.stand(), heute=date(2026, 11, 10))
        sp = [z for z in st if z["id"] == zid][0]
        self.assertEqual((sp["zuordnung"], sp["faellig"], sp["abbuchung"]), ("manuell", "2026-11-08", "fehlgeschlagen"))
        fcb = [x for x in uebersicht(self.st, heute=date(2026, 11, 10))["spiele"] if x["id"] == "HSV vs FCB"][0]
        self.assertIn("Später bezahlen: Abbuchung fehlgeschlagen", fcb["hinweise"])
        self.assertEqual(oz.zuordnen(self.st, zid, "")["zuordnung"], "offen")     # loesen
        self.assertEqual(oz.zuordnen(self.st, zid, "", ignorieren=True)["zuordnung"], "ignoriert")
        self.assertEqual(uebersicht(self.st)["zahlungen_offen"], 0)
        self.assertFalse(oz.zuordnen(self.st, "gibtsnicht", "")["ok"])
        self.assertFalse(oz.zuordnen(self.st, zid, "Fantasie")["ok"])

    def test_6_spaeter_abgebucht(self):
        oz.zahl_anwenden(self.st, [SPAETER, ABGEBUCHT])
        sp = [z for z in oz.zahlungs_status(self.st.stand(), heute=date(2026, 11, 1)) if z["art"] == "spaeter"][0]
        self.assertEqual(sp["abbuchung"], "abgebucht")
        self.assertEqual(len(oz.zahlungs_status(self.st.stand())), 1)              # Abbuchungs-Mails nur Info

    def test_7_lauf_nur_paypal_und_fehler_ohne_text(self):
        pf = mock.Mock(verfuegbar=mock.Mock(return_value=True), posteingang=mock.Mock(return_value=[_gesendet()]))
        r = oz.lauf(self.st, pf)
        self.assertEqual(r["auto"], 1)
        pf.posteingang.assert_called_with(tage=oz.TAGE, nur=("paypal.de", "paypal.com"))
        pf.posteingang.side_effect = OSError("pw=geheim")
        r = oz.lauf(self.st, pf)
        self.assertFalse(r["ok"]); self.assertNotIn("geheim", r["hinweis"])


class TestApi(ApiBasis):
    def test_8_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            _saison(Path(d))
            self.c.post("/api/ofc/import", json={"bestaetigt": True})
            pf = mock.Mock(verfuegbar=mock.Mock(return_value=True), posteingang=mock.Mock(return_value=[_gesendet(), SPAETER]))
            with mock.patch.object(self.w, "_ofc_postfach", return_value=pf):
                v = self.c.get("/api/ofc/zahlungen/vorschau").json()
                self.assertEqual((v["ok"], len(v["neu"]), v["auto"], v["offen"]), (True, 2, 1, 1))
                self.assertFalse(self.c.post("/api/ofc/zahlungen/abholen", json={}).json()["ok"])
                self.assertEqual(self.c.get("/api/ofc/zahlungen").json()["zahlungen"], [])
                self.assertEqual(self.c.post("/api/ofc/zahlungen/abholen", json={"bestaetigt": True}).json()["auto"], 1)
                z = self.c.get("/api/ofc/zahlungen").json()
                self.assertEqual((len(z["zahlungen"]), len(z["spiele"])), (2, 2))
                offen = [x for x in z["zahlungen"] if x["zuordnung"] == "offen"][0]
                r = self.c.post(f"/api/ofc/zahlung/{offen['id']}/zuordnen", json={"spiel": "SVW vs HSV"}).json()
                self.assertEqual(r["zuordnung"], "manuell")
                self.assertEqual(self.c.get("/api/ofc/spiel/SVW vs HSV").json()["bezahlt_cent"], 12340)
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    for url in ("/api/ofc/zahlungen", "/api/ofc/zahlungen/vorschau"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
                    self.assertEqual(self.c.post(f"/api/ofc/zahlung/{offen['id']}/zuordnen", json={"spiel": ""}).status_code, 403)
