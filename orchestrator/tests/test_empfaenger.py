"""EMPFAENGER_MEHRERE M1/M2 (CEO 2026-10-13): mehrere Empfaenger, CC und BCC beim Versand -- geprueft je Adresse,
BCC nie im Mailkopf, alte Einzel-Adressen unveraendert, Vorschlaege aus den Adressen der Firma."""
import base64
import email
import unittest
from email import policy
from unittest import mock

from orchestrator.core import empfaenger as em
from orchestrator.tests.test_allinkl_mail import ENV, FakeIMAP, FakeSMTP
from orchestrator.tests.test_angebote import ApiBasis


class TestKern(unittest.TestCase):
    def test_1_pruefen_und_anzeige(self):
        e = em.pruefen("a@x.de, Bea <b@y.de>; a@x.de", "c@z.de\nB@y.de", ["d@w.de"])
        self.assertEqual(e, {"an": ["a@x.de", "b@y.de"], "cc": ["c@z.de"], "bcc": ["d@w.de"]})      # Doppelte raus
        t = em.anzeige(e)
        self.assertEqual(t, "a@x.de, b@y.de · CC: c@z.de · BCC: d@w.de")
        self.assertEqual(em.zerlegen(t), e)                                                        # Hin und zurueck
        self.assertEqual(em.zerlegen("anna@brandx.de"), {"an": ["anna@brandx.de"], "cc": [], "bcc": []})
        for falsch, grund in (("a@x.de, kaputt@", "kaputt@"), ("", "mindestens eine"), (",".join(f"p{i}@x.de" for i in range(11)), "Hoechstens")):
            with self.assertRaises(ValueError) as cm:
                em.pruefen(falsch)
            self.assertIn(grund, str(cm.exception))
        with self.assertRaises(ValueError):
            em.pruefen("", cc="c@z.de")                                                            # nur CC reicht nicht
        self.assertEqual(em.aus_body({"an": "a@x.de", "bcc": "d@w.de"}), "a@x.de · BCC: d@w.de")
        self.assertEqual(em.aus_body({"an": t}), t)                                                # schon zusammengesetzt
        self.assertEqual(em.erste(t), "a@x.de")
        self.assertEqual(em.kopf("einzel@x.de"), ("einzel@x.de", "", [], ["einzel@x.de"]))         # alt: unveraendert
        self.assertEqual(em.kopf(t), ("a@x.de, b@y.de", "c@z.de", ["d@w.de"], ["a@x.de", "b@y.de", "c@z.de", "d@w.de"]))

    def test_2_gmail_kopf(self):
        from orchestrator.governance.google_workspace import _mime
        m = email.message_from_bytes(base64.urlsafe_b64decode(_mime("a@x.de · CC: c@z.de · BCC: d@w.de", "B", "T")),
                                     policy=policy.default)
        self.assertEqual((m["To"], m["Cc"], m["Bcc"]), ("a@x.de", "c@z.de", "d@w.de"))           # Gmail entfernt Bcc beim Zustellen


class TestApi(ApiBasis):
    def _allinkl(self):
        p = []
        return p, (mock.patch.object(self.w, "_google_secrets", return_value=ENV),
                   mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p)),
                   mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)))

    def test_3_vorschlaege_und_versand(self):
        self.w.kunden_store.firma_aendern(self.k, {"rechnungsmail": "buchhaltung@brandx.de"})
        self.w.kunden_store.ansprechpartner_anlegen(self.k, {"vorname": "Ben", "nachname": "Bote", "mail": "ben@brandx.de"})
        nr = self._neu()
        v = self.c.get(f"/api/crm/angebote/{nr}/versandvorschau").json()
        self.assertEqual([(a["mail"], a["rolle"]) for a in v["adressen"]],
                         [("anna@brandx.de", "Ansprechpartner"), ("ben@brandx.de", "Ansprechpartner"), ("buchhaltung@brandx.de", "Rechnungs-Mail")])
        p, (a, b, c) = self._allinkl()
        with a, b, c:
            f = self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "anna@brandx.de, kaputt@", "betreff": "B", "text": "T",
                                                                   "bestaetigt": True}).json()
            self.assertEqual((f["ok"], "kaputt@" in f["hinweis"]), (False, True))
            self.assertFalse([x for x in p if x[0] == "send"])                                    # nichts verschickt
            r = self.c.post(f"/api/crm/angebote/{nr}/senden", json={
                "an": "anna@brandx.de, ben@brandx.de", "cc": "buchhaltung@brandx.de", "bcc": "nils@hanserautisch.de",
                "betreff": v["betreff"], "text": v["text"], "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        msg = [x[1] for x in p if x[0] == "send"][0]
        self.assertEqual((msg["To"], msg["Cc"], msg["Bcc"]), ("anna@brandx.de, ben@brandx.de", "buchhaltung@brandx.de", None))
        self.assertEqual([x[1] for x in p if x[0] == "an"][0],
                         ["anna@brandx.de", "ben@brandx.de", "buchhaltung@brandx.de", "nils@hanserautisch.de"])  # BCC nur im Umschlag
        roh = [x[3] for x in p if x[0] == "append"][0]                                           # Kopie in „Gesendet“
        self.assertIn(b"buchhaltung@brandx.de", roh)
        self.assertNotIn(b"nils@hanserautisch.de", roh)                                           # BCC nirgends im Kopf
        an = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual(an["versendet_mail"]["an"],
                         "anna@brandx.de, ben@brandx.de · CC: buchhaltung@brandx.de · BCC: nils@hanserautisch.de")   # Verlauf

    def test_4_alter_einzelwert_und_mail_programm(self):
        nr = self._neu()
        r = self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "anna@brandx.de", "betreff": "B", "text": "T", "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.g.gesendet[-1]["an"], "anna@brandx.de")                             # Gmail-Weg wie bisher
        e = self.c.post(f"/api/crm/mailentwurf/angebot/{nr}/eml", json={"an": "a@x.de", "cc": "c@z.de", "bcc": "d@w.de",
                                                                       "betreff": "B", "text": "T"})
        m = email.message_from_bytes(e.content, policy=policy.default)
        self.assertEqual((m["To"], m["Cc"], m["Bcc"]), ("a@x.de", "c@z.de", "d@w.de"))


if __name__ == "__main__":
    unittest.main()
