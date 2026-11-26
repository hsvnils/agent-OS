"""OFC_TICKETVERSAND TV0: Analyse der Wallet-Links in HSV-Mails -- zaehlt richtig, erkennt pkpass-Anhaenge, gibt NIE Links,
Namen oder Mailtext aus, Adress-Abdeckung nur als Zahlen, Endpunkt nur CEO. Fixtures ohne echte Daten."""
import json
import unittest
from email.message import EmailMessage
from unittest import mock

from orchestrator.core import ofc, ofc_wallet
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc_post import _bytes_text

GEHEIM = "abcDEF123geheimToken987"


def _ticket(nr):
    return f"Ticketnummer: {nr}\n12. Spieltag" if nr.endswith("-1") else f"Ticketnummer: {nr}"


def _hsv_mail(links_html: str, tickets=("262236181415-1", "262236181415-2"), pkpass=0, von="tickets@hsv.de", text=""):
    m = EmailMessage()
    m["From"], m["Subject"], m["Message-ID"] = von, "Deine Tickets", "<w1@hsv.de>"
    m.set_content(text or "Hallo Anna Muster, hier deine Tickets.")
    m.add_alternative(f"<html><body><p>Hallo Anna Muster</p>{links_html}</body></html>", subtype="html")
    for nr in tickets:
        m.add_attachment(_ticket(nr).encode(), maintype="application", subtype="pdf", filename=f"{nr}.pdf")
    for i in range(pkpass):
        m.add_attachment(b"PK", maintype="application", subtype="vnd.apple.pkpass", filename=f"t{i}.pkpass")
    return {"uid": "1", "roh": m.as_bytes()}


class _Pf:
    def __init__(self, mails):
        self.mails = mails
        self.aufrufe = []

    def posteingang(self, **kw):
        self.aufrufe.append(kw)
        return self.mails


class TestAnalyse(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(ofc, "pdf_bytes_text", _bytes_text)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_je_ticket_ein_link_mit_ticketnummer(self):
        links = ("<a href='https://wallet.hsv.example/pass/262236181415-1?t=" + GEHEIM + "'>Zu Apple Wallet hinzufügen</a>"
                 "<a href='https://wallet.hsv.example/pass/262236181415-2?t=" + GEHEIM + "'>Zu Apple Wallet hinzufügen</a>"
                 "<a href='https://www.hsv.de/datenschutz'>Datenschutz Anna Muster</a>")
        pf = _Pf([_hsv_mail(links)])
        r = ofc_wallet.analyse(pf, tage=30)
        self.assertEqual(pf.aufrufe[0]["nur"], ("hsv.de",))          # nur HSV-Mails
        self.assertEqual((r["mails_mit_tickets"], r["tickets"], r["wallet_links"]), (1, 2, 2))
        self.assertEqual(r["verhaeltnis_wallet_zu_tickets"], {"gleich": 1})
        self.assertEqual(r["je_mail"][0]["ticketnr_im_link"], 2)
        self.assertEqual((r["spieltag_im_ticket"], r["spieltag_in_rechnung"]), (1, 0))
        self.assertEqual(r["wallet_hosts"], {"wallet.hsv.example": 2})
        self.assertIn("wallet.hsv.example/pass/*?t", r["link_muster"])
        # Gegenprobe: kein Link-Wert, kein Name, keine Ticketnummer im Bericht
        s = json.dumps(r, ensure_ascii=False)
        for verboten in (GEHEIM, "Anna", "Muster", "262236181415", "https://"):
            self.assertNotIn(verboten, s, verboten)

    def test_ein_link_fuer_die_bestellung_und_pkpass(self):
        pf = _Pf([_hsv_mail("<a href='https://pay.google.com/gp/v/save/xyz'><img alt='Google Wallet'></a>", pkpass=2)])
        r = ofc_wallet.analyse(pf)
        self.assertEqual(r["verhaeltnis_wallet_zu_tickets"], {"weniger": 1})
        self.assertEqual(r["pkpass_anhaenge"], 2)
        self.assertEqual(r["je_mail"][0]["ticketnr_im_link"], 0)
        self.assertIn("google wallet", r["linktexte_maskiert"])

    def test_link_im_text_teil_und_mails_ohne_tickets(self):
        pf = _Pf([_hsv_mail("", text="Wallet: https://wallet.hsv.example/w/123"),
                  {"uid": "2", "roh": _hsv_mail("", tickets=())["roh"]}])
        r = ofc_wallet.analyse(pf)
        self.assertEqual(r["mails_mit_tickets"], 1)
        self.assertEqual(r["wallet_links"], 1)

    def test_maskiert(self):
        self.assertEqual(ofc_wallet.maskiert("Ticket für Anna Muster 12"), "ticket für … ##")
        self.assertEqual(ofc_wallet.maskiert("Zu Apple Wallet hinzufügen"), "zu apple wallet hinzufügen")

    def test_adressen_abdeckung_nur_zahlen(self):
        t = {"1": {"name": "Anna Muster"}, "2": {"name": "Bob"}, "3": {"name": "Cora Doppelt"}, "4": {"name": "Dirk Ohne"}, "5": {}}
        m = [{"name": "Anna Muster", "email": "anna@example.org"}, {"name": "Cora Doppelt", "email": "c1@example.org"},
             {"name": "Cora Doppelt", "email": "c2@example.org"}, {"name": "Dirk Ohne", "email": ""}]
        r = ofc_wallet.adressen_abdeckung(t, m)
        self.assertEqual((r["namen"], r["eindeutig_mit_mail"], r["mehrdeutig"], r["treffer_ohne_mail"], r["ohne_treffer"]),
                         (4, 1, 1, 1, 1))
        self.assertNotIn("anna@", json.dumps(r))
        self.assertFalse(ofc_wallet.adressen_abdeckung(t, None)["ok"])


class TestApi(ApiBasis):
    def test_nur_ceo(self):
        pf = _Pf([])
        pf.verfuegbar = lambda: True
        with mock.patch.object(self.w, "_ofc_postfach", return_value=pf), \
                mock.patch.object(self.w, "_ofc_mitglieder_daten", return_value=None):
            self.assertTrue(self.c.get("/api/ofc/analyse/wallet").json()["ok"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/analyse/wallet").status_code, 403)


if __name__ == "__main__":
    unittest.main()
