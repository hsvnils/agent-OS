"""OFC_ROADMAP O0: Fanclub HSVInside -- HSV-Rechnung/Tickets lesen (Heim, Auswaerts, Pokal, ohne Saison), Ordner-Analyse
ohne Namen, Postfach moin@ nur lesend und nur PayPal/Eventim/HSV (Absender nachgeprueft), maskierte Postfach-Analyse,
Endpunkte nur fuer den CEO. Beispieldaten sind erfunden."""
import os
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.governance.allinkl_mail import HsvInsideMail
from orchestrator.tests.test_angebote import ApiBasis

HEIM = """HSV Fussball AG & Co. KGaA
Max Kaeufer Swift: GENODEF1S11
Rechnung
Auftrags-Nr.: 180131000
262236181415Rechnungsnr:
Kunden-Nr.: 2267029
Datum 05.10.2026
Gemaess unseren Geschaeftsbedingungen erhalten Sie anbei 2
Eintrittskarte(n).
26-27 Hamburger SV - FC Bayern Muenchen / 28.11.2026 / 15:30 (Volksparkstadion)
Hamburger SV-FC Bayern Muenchen
Pos  Ticketnummer Block Preisgruppe Reihe Sitz Preis
1   262236181415-1 28C PK5 17 74 35,00 EUR
2   262236181415-2 28C PK5 17 75 35,00 EUR
max@example.org / Mobile-Ticket
Gesamtsumme für 2 Ticket(s): 70,00 EUR
Zahlart: PayPal
"""
AUSWAERTS = """Rechnungsnr: 262230000001
Kunden-Nr.: 2267029
Datum 01.10.2026
Eintrittskarte(n).
Auswärts 26-27 Dortmund / 29.08.2026 / 18:30 (SIGNAL IDUNA PARK)
Borussia Dortmund-Hamburger SV
1   262230000001-1 61 Gast Steh 1 12 57,20 EUR
2   262230000001-2 61 Gast Steh 1 13 57,20 EUR
Gesamtsumme für 2 Ticket(s): 1.114,40 EUR
Zahlart: PayPal
"""
FREUNDSCHAFT = """Rechnungsnr: 262239999999
Hamburger SV - Hajduk Split / 15.11.2026 / 15:00 (Volksparkstadion)
Hamburger SV-Hajduk Split
1   262239999999-1 22B PK3 4 9 25,44 EUR
Gesamtsumme für 1 Ticket(s): 25,44 EUR
"""


class TestRechnung(unittest.TestCase):
    def test_1_heimspiel(self):
        r = ofc.rechnung_aus_text(HEIM)
        self.assertTrue(r["erkannt"])
        self.assertEqual((r["rechnungsnr"], r["auftragsnr"], r["kundennr"], r["datum"]),
                         ("262236181415", "180131000", "2267029", "2026-10-05"))
        self.assertEqual((r["spiel"], r["spieltag"], r["uhrzeit"], r["ort"], r["saison"], r["wettbewerb"]),
                         ("Hamburger SV - FC Bayern Muenchen", "2026-11-28", "15:30", "Volksparkstadion", "26-27", ""))
        self.assertEqual((r["heimspiel"], r["gegner"], r["anzahl"], r["summe_cent"], r["zahlart"]),
                         (True, "FC Bayern Muenchen", 2, 7000, "PayPal"))
        self.assertEqual(r["tickets"][1], {"pos": 2, "ticketnr": "262236181415-2", "block": "28C", "preisgruppe": "PK5",
                                           "reihe": "17", "sitz": "75", "preis_cent": 3500})

    def test_2_auswaerts_und_freundschaft(self):
        r = ofc.rechnung_aus_text(AUSWAERTS)
        self.assertEqual((r["wettbewerb"], r["saison"], r["spiel"], r["heimspiel"], r["gegner"]),
                         ("Auswärts", "26-27", "Borussia Dortmund - Hamburger SV", False, "Borussia Dortmund"))
        self.assertEqual((r["tickets"][0]["preisgruppe"], r["summe_cent"]), ("Gast Steh", 111440))   # zwei Woerter, Tausenderpunkt
        f = ofc.rechnung_aus_text(FREUNDSCHAFT)
        self.assertEqual((f["erkannt"], f["saison"], f["gegner"], f["spieltag"]), (True, "", "Hajduk Split", "2026-11-15"))
        self.assertFalse(ofc.rechnung_aus_text("irgendein Text ohne Rechnung")["erkannt"])

    def test_3_ticket_und_dateiname(self):
        for t in ("Ticketnummer: 262236181415-3", "Ticket Nummer: 262236181415-3", "Bestellnummer: 262236181415-3"):
            self.assertEqual(ofc.ticket_aus_text(f"x\n{t}\ny")["ticketnr"], "262236181415-3", t)
        self.assertEqual(ofc.ticket_aus_text("nichts"), {})
        self.assertEqual(ofc.datei_name("262236181415-3-Anna.pdf")["name"], "Anna")
        self.assertEqual(ofc.datei_name("262236181415-3.pdf")["name"], "")
        self.assertEqual(ofc.datei_name("262236181415-2A - Ben Muster.pdf"), {"rechnungsnr": "262236181415", "pos": 2,
                                                                            "zusatz": "A", "name": "Ben Muster"})
        self.assertEqual(ofc.datei_name("Rechnung.pdf"), {})


def _pdf_als_text(p):
    return Path(p).read_text(encoding="utf-8")


class TestOrdner(unittest.TestCase):
    def test_4_ordner_analyse_ohne_namen(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / "Tickets 26-27"
            heim = s / "HSV vs FCB"
            heim.mkdir(parents=True)
            (heim / "Rechnung.pdf").write_text(HEIM, encoding="utf-8")
            (heim / "262236181415-1-Geheimname.pdf").write_text("Ticketnummer: 262236181415-1", encoding="utf-8")
            (heim / "262236181415-2.pdf").write_text("Ticketnummer: 262236181415-2", encoding="utf-8")
            (heim / "262236189999-1-Zweitname.pdf").write_text("Ticketnummer: 262236189999-1", encoding="utf-8")   # 2. Bestellung
            (heim / "ATGB_Ticketing.pdf").write_text("AGB", encoding="utf-8")
            (heim / "@eaDir").mkdir()
            alt = s / "Abgeschlossen" / "BVB vs HSV"
            alt.mkdir(parents=True)
            (alt / "Rechnung.pdf").write_text(AUSWAERTS, encoding="utf-8")
            (s / "@eaDir").mkdir()
            with mock.patch.object(ofc, "pdf_text", _pdf_als_text):
                r = ofc.ordner_analyse(s)
        self.assertEqual(r["summe"], {"spiele": 2, "erkannt": 2, "karten": 4, "dateien": 3})
        sp = {x["ordner"]: x for x in r["spiele"]}
        h = sp["HSV vs FCB"]
        self.assertEqual((h["abgeschlossen"], h["karten_rechnung"], h["ticket_dateien"], h["dateien_zugeordnet"],
                          h["mit_name"], h["ohne_name"], h["bestellungen_ohne_rechnung"]), (False, 2, 3, 2, 2, 1, 1))
        self.assertEqual((sp["BVB vs HSV"]["abgeschlossen"], sp["BVB vs HSV"]["fehlende_tickets"]), (True, 2))
        self.assertNotIn("Geheimname", str(r))
        self.assertNotIn("Zweitname", str(r))
        self.assertFalse(ofc.ordner_analyse(Path(d) / "gibtsnicht")["ok"])


class FakeIMAP:
    def __init__(self, p, mails):
        self.p, self.mails = p, mails

    def login(self, user, pw):
        self.p.append(("login", user))

    def select(self, ordner, readonly=False):
        self.p.append(("select", ordner, readonly))
        return "OK", [b"2"]

    def uid(self, befehl, *args):
        self.p.append(("uid", befehl) + tuple(a.decode() if isinstance(a, bytes) else a for a in args))
        if befehl == "SEARCH":
            return "OK", [" ".join(self.mails).encode()]
        uid, teil = (args[0].decode() if isinstance(args[0], bytes) else args[0]), args[1]
        von, roh = self.mails[uid]
        return "OK", [(b"x", f"From: {von}\r\n".encode() if "HEADER.FIELDS" in teil else roh)]

    def logout(self):
        pass


def _mail(von, betreff, text):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = von, "moin@hsvinside.de", betreff, "Mon, 23 Nov 2026 10:00:00 +0100"
    m.set_content(text)
    return m.as_bytes()


ENV = {"HSVINSIDE_IMAP_HOST": "w0000.kasserver.com", "HSVINSIDE_MAIL_USER": "moin@hsvinside.de",
       "HSVINSIDE_MAIL_PASSWORT": "ofc-pruefwert-789"}


class TestPostfach(unittest.TestCase):
    def _pf(self, mails, env=ENV):
        p = []
        return HsvInsideMail(env, imap_fabrik=lambda: FakeIMAP(p, mails)), p

    def test_5_nur_erlaubte_absender_nur_lesend(self):
        echt = _mail("PayPal <service@paypal.de>", "Sie haben eine Zahlung erhalten", "Betrag 35,00 €")
        mails = {"1": ("PayPal <service@paypal.de>", echt), "2": ("Spam <x@paypal.de.betrug.com>", b"GEHEIM"),
                 "3": ("Freund <a@privat.de>", b"PRIVAT")}
        pf, p = self._pf(mails)
        out = pf.posteingang(tage=30)
        self.assertEqual([x["uid"] for x in out], ["1"])
        self.assertIn(("select", "INBOX", True), p)
        voll = [x[2] for x in p if x[:2] == ("uid", "FETCH") and x[3] == "(BODY.PEEK[])"]
        self.assertEqual(voll, ["1"])                                                     # 2 und 3 nie geladen
        suche = [x for x in p if x[:2] == ("uid", "SEARCH")][0]
        for d in ("paypal.de", "eventim.de", "hsv.de"):
            self.assertIn(d, suche)
        self.assertFalse(pf.mail_senden("a@b.de", "B", "T", bestaetigt=True)["ok"])
        self.assertFalse(any(x[1] in ("STORE", "COPY", "MOVE") for x in p if x[0] == "uid"))

    def test_6_pruefen_ohne_lesen_und_fehlend(self):
        pf, p = self._pf({})
        self.assertEqual(pf.verbindung_pruefen(), {"ok": True, "imap": True})
        self.assertFalse([x for x in p if x[0] == "uid"])
        r = HsvInsideMail({}).verbindung_pruefen()
        self.assertEqual(r["fehlend"], ["HSVINSIDE_IMAP_HOST", "HSVINSIDE_MAIL_USER", "HSVINSIDE_MAIL_PASSWORT"])
        self.assertIn("hsvinside-extra.de", HsvInsideMail(ENV | {"HSVINSIDE_ABSENDER": "@hsvinside-extra.de"}).domains)

    def test_7_analyse_maskiert(self):
        mails = {"1": ("PayPal <service@paypal.de>", _mail("PayPal <service@paypal.de>", "Max Mustermann hat Ihnen Geld gesendet",
                                                           "Hallo,\nSie haben eine Zahlung erhalten.\nVon: Max Mustermann\n"
                                                           "Betrag: 35,00 € EUR\nMitteilung: Bayern 1x\nTransaktionscode: 8AB12345CD")),
                 "2": ("PayPal <service@paypal.de>", _mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an CTS Eventim",
                                                           "Sie haben eine Zahlung an CTS EVENTIM gesendet.\nBetrag 140,00 € EUR\n"
                                                           "Transaktionscode: 9XY")),
                 "3": ("HSV <ticketing@hsv.de>", _mail("HSV <ticketing@hsv.de>", "Ihre Rechnung 262236181415", "Rechnungsnr 1"))}
        pf, _ = self._pf(mails)
        r = ofc.mail_analyse(pf, tage=30)
        self.assertEqual({k: v["anzahl"] for k, v in r["typen"].items()}, {"paypal_erhalten": 1, "paypal_gesendet": 1, "hsv": 1})
        self.assertEqual(r["typen"]["paypal_erhalten"]["felder"]["transaktionscode"], 1)
        text = str(r)
        for privat in ("Mustermann", "Max", "35,00", "8AB12345CD", "262236181415"):
            self.assertNotIn(privat, text)


class TestApi(ApiBasis):
    def test_8_nur_ceo_und_ordner(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Tickets 26-27" / "Spiel").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}):
                r = self.c.get("/api/ofc/analyse/ordner").json()
                self.assertEqual((r["ok"], r["summe"]["spiele"]), (True, 1))
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    for url in ("/api/ofc/analyse/ordner", "/api/ofc/analyse/postfach", "/api/ofc/postfach/pruefen"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
        with mock.patch.object(self.w, "_google_secrets", return_value={}):
            r = self.c.get("/api/ofc/analyse/postfach").json()
        self.assertFalse(r["ok"])
        self.assertIn("HSVINSIDE_MAIL_USER", r["hinweis"])
