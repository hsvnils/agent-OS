"""MAILVERSAND_ALLINKL M1: Kundenmails ueber luna@hanserautisch.de (SMTP + Ablage in „Gesendet“ per IMAP) -- nur mit
Attrappen, kein echter Versand. Schalter KUNDENVERSAND entscheidet allein, kein automatischer Rueckfall auf Gmail."""
import email
import smtplib
import unittest
from email import policy
from unittest import mock

from orchestrator.governance.allinkl_mail import AllInklMail, kundenversand, versandweg
from orchestrator.tests.test_angebote import ApiBasis

PW = "geheim-Passwort-123"
ENV = {"KUNDENVERSAND": "allinkl", "ALLINKL_SMTP_HOST": "w0000.kasserver.com", "ALLINKL_IMAP_HOST": "w0000.kasserver.com",
       "ALLINKL_MAIL_USER": "luna@hanserautisch.de", "ALLINKL_MAIL_PASSWORT": PW, "ALLINKL_ABSENDER": "luna@hanserautisch.de"}


class FakeSMTP:
    def __init__(self, protokoll, fehler=None):
        self.p, self.fehler = protokoll, fehler

    def login(self, user, pw):
        if self.fehler:
            raise self.fehler
        self.p.append(("login", user, pw))

    def send_message(self, msg):
        self.p.append(("send", msg))

    def quit(self):
        self.p.append(("quit",))


class FakeIMAP:
    def __init__(self, protokoll, liste=None, kaputt=False):
        self.p, self.kaputt = protokoll, kaputt
        self.liste = liste if liste is not None else [b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren \\Sent) "." "Gesendete Elemente"']

    def login(self, user, pw):
        if self.kaputt:
            raise OSError("imap weg")
        self.p.append(("imap-login", user))

    def list(self):
        return "OK", self.liste

    def append(self, ordner, flags, datum, roh):
        self.p.append(("append", ordner, flags, roh))
        return "OK", [b""]

    def logout(self):
        pass


def _mail(env=ENV, **kw):
    p = []
    m = AllInklMail(env, smtp_fabrik=lambda: FakeSMTP(p, kw.get("smtp_fehler")),
                    imap_fabrik=lambda: FakeIMAP(p, kw.get("liste"), kw.get("imap_kaputt", False)))
    return m, p


class TestAllInkl(unittest.TestCase):
    def test_1_schalter_und_einrichtung(self):
        self.assertEqual((kundenversand({}), kundenversand({"KUNDENVERSAND": " AllInkl "}), kundenversand({"KUNDENVERSAND": "x"})),
                         ("gmail", "allinkl", "gmail"))
        g = object()
        self.assertIs(versandweg({}, g), g)                                    # Standard bleibt Gmail
        self.assertIsInstance(versandweg(ENV, g), AllInklMail)
        halb = {k: v for k, v in ENV.items() if k != "ALLINKL_MAIL_PASSWORT"}
        with self.assertRaises(ValueError) as e:                                # kein stiller Rueckfall auf Gmail
            versandweg(halb, g)
        self.assertIn("ALLINKL_MAIL_PASSWORT", str(e.exception))
        m, p = _mail(halb)
        r = m.mail_senden("a@b.de", "B", "T", bestaetigt=True)
        self.assertFalse(r["ok"])
        self.assertEqual(p, [])

    def test_2_senden_und_gesendet(self):
        m, p = _mail()
        vor = m.mail_senden("kunde@kiezalm.de", "Angebot AN-1", "Hallo")
        self.assertTrue(vor["bestaetigung_noetig"])                             # ohne Bestaetigung nur Vorschau
        self.assertEqual(p, [])
        r = m.mail_senden("kunde@kiezalm.de", "Angebot AN-1", "Hallo", bestaetigt=True, absender_name="Hanserautisch – LUNA",
                          anhaenge=[("Angebot_AN-1.pdf", b"%PDF-1.4 x", "application/pdf")])
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["kanal"], r["thread_id"], r["gesendet_ordner"]), ("allinkl", "", "Gesendete Elemente"))
        self.assertRegex(r["id"], r"^luna-[0-9a-f]{24}$")
        self.assertEqual(p[0], ("login", "luna@hanserautisch.de", PW))
        msg = p[1][1]
        self.assertEqual(msg["From"], "Hanserautisch – LUNA <luna@hanserautisch.de>")
        self.assertEqual(msg["Message-ID"], f"<{r['id']}@hanserautisch.de>")
        ap = [x for x in p if x[0] == "append"][0]
        self.assertEqual((ap[1], ap[2]), ('"Gesendete Elemente"', r"(\Seen)"))
        roh = m.mail_roh(r["id"])["roh"]
        self.assertEqual(ap[3], roh)                                            # dieselben Bytes in Gesendet und im Archiv
        geparst = email.message_from_bytes(roh, policy=policy.default)
        self.assertEqual([a.get_filename() for a in geparst.iter_attachments()], ["Angebot_AN-1.pdf"])
        self.assertFalse(m.mail_roh("luna-unbekannt")["ok"])

    def test_3_fehler_ohne_zugangsdaten_im_text(self):
        m, _ = _mail(smtp_fehler=smtplib.SMTPAuthenticationError(535, PW.encode()))
        r = m.mail_senden("a@b.de", "B", "T", bestaetigt=True)
        self.assertFalse(r["ok"])
        self.assertIn("Anmeldung abgelehnt", r["hinweis"])
        self.assertNotIn(PW, str(r))
        m, _ = _mail(smtp_fehler=OSError(f"kaputt {PW}"))
        r = m.mail_senden("a@b.de", "B", "T", bestaetigt=True)
        self.assertEqual(r["hinweis"], "Senden ueber All-Inkl fehlgeschlagen (OSError).")

    def test_4_gesendet_ordner(self):
        m, p = _mail(imap_kaputt=True)                                          # IMAP weg: Mail ist trotzdem raus
        r = m.mail_senden("a@b.de", "B", "T", bestaetigt=True)
        self.assertEqual((r["ok"], r["gesendet_ordner"]), (True, ""))
        self.assertTrue(m.mail_roh(r["id"])["ok"])
        m, p = _mail(liste=[b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren) "." "INBOX.Sent"'])   # ohne \Sent-Flag
        self.assertEqual(m.mail_senden("a@b.de", "B", "T", bestaetigt=True)["gesendet_ordner"], "INBOX.Sent")
        m, p = _mail(ENV | {"ALLINKL_GESENDET_ORDNER": "Ausgang"})
        self.assertEqual(m.mail_senden("a@b.de", "B", "T", bestaetigt=True)["gesendet_ordner"], "Ausgang")

    def test_5_verbindung_pruefen(self):
        m, p = _mail()
        self.assertEqual(m.verbindung_pruefen(), {"ok": True, "smtp": True, "imap": True, "gesendet_ordner": "Gesendete Elemente"})
        self.assertFalse([x for x in p if x[0] in ("send", "append")])           # Pruefung verschickt nichts


class TestApi(ApiBasis):
    def _allinkl(self, env=ENV):
        p = []
        return p, (mock.patch.object(self.w, "_google_secrets", return_value=env),
                   mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p)),
                   mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)))

    def test_angebot_ueber_allinkl(self):
        nr = self._neu()
        p, (a, b, c) = self._allinkl()
        with a, b, c:
            v = self.c.get(f"/api/crm/angebote/{nr}/versandvorschau").json()
            self.assertEqual((v["absender"], v["versand_kanal"], v["google"]),
                             ("Hanserautisch – LUNA <luna@hanserautisch.de>", "allinkl", True))
            r = self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "anna@brandx.de", "betreff": v["betreff"],
                                                                   "text": v["text"], "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.g.gesendet, [])                                   # Gmail bleibt unberuehrt
        an = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual((an["status"], an["versendet_mail"]["kanal"]), ("versendet", "allinkl"))
        mid = an["versendet_mail"]["message_id"]
        self.assertIn(mid, an.get("mail_archiv") or {})                        # .eml sofort archiviert
        self.assertEqual(len([x for x in p if x[0] == "append"]), 1)

    def test_nicht_eingerichtet_kein_rueckfall(self):
        nr = self._neu()
        p, (a, b, c) = self._allinkl({"KUNDENVERSAND": "allinkl"})
        with a, b, c:
            v = self.c.get(f"/api/crm/angebote/{nr}/versandvorschau").json()
            r = self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "anna@brandx.de", "betreff": "B", "text": "T",
                                                                   "bestaetigt": True}).json()
        self.assertEqual((v["versand_kanal"], v["google"]), ("allinkl", False))
        self.assertFalse(r["ok"])
        self.assertIn("nicht eingerichtet", r["hinweis"])
        self.assertEqual((self.g.gesendet, p), ([], []))
        self.assertEqual(self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]["status"], "entwurf")

    def test_status_und_testmail(self):
        p, (a, b, c) = self._allinkl()
        with a, b, c:
            st = self.c.get("/api/finanzen/kundenversand").json()
            self.assertFalse(self.c.post("/api/finanzen/kundenversand/testmail", json={"an": "nils@hanserautisch.de"}).json()["ok"])
            t = self.c.post("/api/finanzen/kundenversand/testmail", json={"an": "nils@hanserautisch.de", "bestaetigt": True}).json()
        self.assertEqual((st["kanal"], st["fehlend"], st["pruefung"]["ok"]), ("allinkl", [], True))
        self.assertNotIn(PW, str(st))
        self.assertTrue(t["ok"], t)
        self.assertEqual([x[1]["To"] for x in p if x[0] == "send"], ["nils@hanserautisch.de"])
        with mock.patch.object(self.w, "_google_secrets", return_value={}):
            st = self.c.get("/api/finanzen/kundenversand").json()
        self.assertEqual((st["kanal"], "pruefung" in st, len(st["fehlend"])), ("gmail", False, 5))

    def test_mail_programm_bleibt(self):
        nr = self._neu()
        p, (a, b, c) = self._allinkl()
        with a, b, c:
            r = self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "anna@brandx.de", "betreff": "B", "text": "T",
                                                                   "bestaetigt": True, "kanal": "mail-programm"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(p, [])                                                 # eigenes Mail-Programm: LUNA sendet nichts


if __name__ == "__main__":
    unittest.main()
