"""KONTAKTE K4: Mail an Ansprechpartner aus LUNA-OS -- Versand nur mit Bestaetigung (Fake-SMTP, kein echter Versand),
Absender nils@ bis K5 gesperrt, Kopie in die Akte mit Ansprechpartner, Kennung -> Antwort wird erkannt (K3), Anhang nur
aus der Akte derselben Firma, Entwurf schickt nur die Stichworte ans Modell, Schalter KONTAKT_MAIL=0."""
import email
import os
from email import policy
from unittest import mock

from orchestrator.core.firmenakte import Firmenakte
from orchestrator.core.kontakt_mail import entwurf
from orchestrator.core.mail_antworten import antworten_pruefen, kontakt_mails
from orchestrator.tests.test_allinkl_mail import ENV, FakeIMAP, FakeSMTP
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mail_antworten import CEO, Postfach, antwort


class TestKontaktMail(ApiBasis):
    def setUp(self):
        super().setUp()
        self.ks, self.bh = self.w.kunden_store, self.w.kunden_store.bh
        self.ap = self.ks.firma(self.k)["ansprechpartner_liste"][0]

    def _mit_allinkl(self, fn, env=ENV):
        p = []
        with mock.patch.object(self.w, "_google_secrets", return_value=env), \
             mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p)), \
             mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)):
            return fn(), p

    def _body(self, **kw):
        return {"firma": self.k, "ansprechpartner": self.ap["nummer"], "an": self.ap["mail"], "betreff": "Dreh am Freitag",
                "text": "Guten Tag Anna,\n\npasst Freitag?\n\nViele Gruesse", "bestaetigt": True} | kw

    def _senden(self, **kw):
        return self._mit_allinkl(lambda: self.c.post("/api/crm/kontakt/mail/senden", json=self._body(**kw)).json())

    def test_1_vorschau(self):
        with mock.patch.object(self.w, "_google_secrets", return_value=ENV):
            v = self.c.get(f"/api/crm/kontakt/mail/vorschau?firma={self.k}&ap={self.ap['nummer']}").json()
        self.assertEqual((v["an"], v["ansprechpartner"]["nummer"], v["bereit"], v["aktiv"]), (self.ap["mail"], self.ap["nummer"], True, True))
        self.assertTrue(v["text"].startswith(v["anrede"]))
        self.assertEqual([(a["id"], a["frei"]) for a in v["absender"]], [("luna", True), ("nils", False)])
        self.assertEqual(self.c.get(f"/api/crm/kontakt/mail/vorschau?firma={self.k}&ap=AP-XXX").status_code, 400)
        self.assertEqual(self.c.get("/api/crm/kontakt/mail/vorschau?firma=K-9999").status_code, 404)
        d = self.c.get(f"/api/crm/kunden/{self.k}").json()
        self.assertTrue(d["kontakt_mail"])

    def test_2_senden_akte_kennung(self):
        self.assertFalse(self.c.post("/api/crm/kontakt/mail/senden", json=self._body(bestaetigt=False)).json()["ok"])
        r, p = self._senden(absender="nils")
        self.assertFalse(r["ok"])
        self.assertIn("K5", r["hinweis"])
        self.assertFalse([x for x in p if x[0] == "send"])                                    # nils@ -> nichts gesendet
        r, p = self._senden()
        self.assertTrue(r["ok"], r)
        gesendet = [x[1] for x in p if x[0] == "send"]
        self.assertEqual(len(gesendet), 1)
        self.assertEqual((gesendet[0]["To"], gesendet[0]["Subject"]), (self.ap["mail"], "Dreh am Freitag"))
        self.assertIn("luna@hanserautisch.de", gesendet[0]["From"])
        km = kontakt_mails(self.bh.eintraege())
        self.assertEqual(list(km), [r["kennung"]])
        self.assertEqual((km[r["kennung"]]["firma"], km[r["kennung"]]["ansprechpartner"], km[r["kennung"]]["akte_id"]),
                         (self.k, self.ap["nummer"], r["akte_id"]))
        dok = Firmenakte(self.bh, self.ks).dokument(r["akte_id"])
        self.assertEqual((dok["firma"], dok["ansprechpartner"], dok["art"]), (self.k, self.ap["nummer"], "mail"))
        self.assertEqual(sorted(d["name"].rsplit(".", 1)[1] for d in dok["dateien"]), ["eml", "pdf"])   # .eml + PDF-Ansicht
        # Verlauf am Ansprechpartner + Zaehler in der Firmen-Ansicht
        v = self.c.get(f"/api/crm/kontakt/verlauf?firma={self.k}&ap={self.ap['nummer']}").json()["verlauf"]
        self.assertEqual([x["id"] for x in v], [r["akte_id"]])
        self.assertEqual(self.c.get(f"/api/crm/kunden/{self.k}").json()["ap_mails"], {self.ap["nummer"]: 1})
        # Antwort darauf -> K3 ordnet sie zu (Akte + Meldung)
        meldungen = []
        neu = antworten_pruefen(self.bh, self.ks, Postfach([antwort(self.ap["mail"], "Re: Dreh am Freitag", "Passt!",
                                                                    auf=gesendet[0]["Message-ID"])]),
                                eigene=CEO + ["luna@hanserautisch.de"], notify=lambda t, **kw: meldungen.append(t))
        self.assertEqual([(x["nummer"], x["art"], x["ansprechpartner"]) for x in neu], [(self.k, "kontakt", self.ap["nummer"])])
        self.assertIn("Antwort von", meldungen[0])
        self.assertEqual(self.c.get(f"/api/crm/kunden/{self.k}").json()["ap_mails"], {self.ap["nummer"]: 2})

    def test_3_anhang_nur_aus_eigener_akte(self):
        a = Firmenakte(self.bh, self.ks)
        did = a.hochladen(self.k, b"%PDF-1.4 test", "Angebot.pdf", titel="Angebot")["id"]
        fremd = self.c.post("/api/crm/kunden", json={"firma": {"name": "Andere GmbH", "typ": "kunde"}}).json()["nummer"]
        fdid = a.hochladen(fremd, b"%PDF-1.4 geheim", "Fremd.pdf")["id"]
        r, p = self._senden(anhaenge=[fdid])
        self.assertFalse(r["ok"])
        self.assertFalse([x for x in p if x[0] == "send"])
        r, p = self._senden(anhaenge=[did])
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["anhaenge"], ["Angebot.pdf"])
        msg = email.message_from_bytes([x[1] for x in p if x[0] == "send"][0].as_bytes(), policy=policy.default)
        self.assertEqual([t.get_filename() for t in msg.iter_attachments()], ["Angebot.pdf"])

    def test_4_nur_ceo_nur_allinkl_schalter(self):
        with mock.patch.object(self.w, "hat_modul", return_value=False):
            self.assertIn("nur der CEO", self._senden()[0]["hinweis"])
        r, p = self._mit_allinkl(lambda: self.c.post("/api/crm/kontakt/mail/senden", json=self._body()).json(),
                                 env={k: v for k, v in ENV.items() if k != "KUNDENVERSAND"})       # Gmail-Weg -> nein
        self.assertFalse(r["ok"])
        self.assertIn("luna@", r["hinweis"])
        with mock.patch.dict(os.environ, {"KONTAKT_MAIL": "0"}):
            r, p = self._senden()
            self.assertFalse(r["ok"])
            self.assertFalse(self.c.get(f"/api/crm/kunden/{self.k}").json()["kontakt_mail"])
        self.assertFalse([x for x in p if x[0] == "send"])
        self.assertEqual(kontakt_mails(self.bh.eintraege()), {})

    def test_5_entwurf_nur_stichworte(self):
        gesehen = []

        class Client:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kw):
                        gesehen.append(kw)
                        return mock.Mock(choices=[mock.Mock(message=mock.Mock(content="gerne bestaetige ich den Termin."))])
        with self.assertRaises(ValueError):
            entwurf("  ", client=Client, modell="m")
        self.assertEqual(entwurf("Termin Freitag bestaetigen", client=Client, modell="m"), "gerne bestaetige ich den Termin.")
        inhalt = gesehen[0]["messages"][0]["content"]
        self.assertIn("Termin Freitag bestaetigen", inhalt)
        for privat in (self.ap["mail"], self.ap["nachname"], self.ks.firma(self.k)["name"]):
            self.assertNotIn(privat, inhalt)
        with mock.patch.object(self.w, "_cloud", return_value=(Client, "anthropic")):
            r = self.c.post("/api/crm/kontakt/mail/entwurf", json={"stichworte": "Danke fuers Gespraech"}).json()
        self.assertEqual((r["ok"], r["text"]), (True, "gerne bestaetige ich den Termin."))
