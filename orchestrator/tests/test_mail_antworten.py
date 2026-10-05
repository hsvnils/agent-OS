"""MAILVERSAND_ALLINKL M2: Kundenantworten im Postfach luna@ erkennen -- Zuordnung ueber die Kennung der gesendeten Mail
(In-Reply-To/References) bzw. Belegnummer im Betreff, genau einmal erfassen, ablegen, melden; Postfach nur lesen."""
import unittest
from email.message import EmailMessage
from unittest import mock

from orchestrator.core.mail_antworten import antworten_pruefen, art, gesendete, schluessel, zuordnen
from orchestrator.governance.allinkl_mail import AllInklMail
from orchestrator.tests.test_allinkl_mail import ENV, FakeIMAP, FakeSMTP
from orchestrator.tests.test_angebote import ApiBasis

CEO = ["nils@hanserautisch.de", "hsvnils@icloud.com"]


def antwort(von, betreff, text, *, auf="", mid="<a1@brandx.de>"):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = von, "luna@hanserautisch.de", betreff, mid
    m["Date"] = "Mon, 05 Oct 2026 18:00:00 +0200"
    if auf:
        m["In-Reply-To"] = auf
        m["References"] = auf
    m.set_content(text)
    return m.as_bytes()


class Postfach:
    def __init__(self, mails):
        self.mails = mails

    def posteingang(self, *, tage=30):
        return [{"uid": str(i), "roh": r} for i, r in enumerate(self.mails)]


class TestZuordnung(unittest.TestCase):
    def test_kennung_betreff_mahnung(self):
        zu = {"luna-" + "a" * 24: "AN-2026-0001", "luna-" + "b" * 24: "RE-2026-0003-M1"}
        mahn = {"RE-2026-0003-M1": "RE-2026-0003"}
        self.assertEqual(zuordnen(antwort("x@y.de", "Re: Hallo", "ok", auf=f"<luna-{'a' * 24}@hanserautisch.de>"), zu), "AN-2026-0001")
        self.assertEqual(zuordnen(antwort("x@y.de", "AW: Angebot AN-2026-0001", "ok"), zu), "AN-2026-0001")
        self.assertEqual(zuordnen(antwort("x@y.de", "AW: Mahnung zu RE-2026-0003", "ok"), zu, mahn), "RE-2026-0003")
        self.assertEqual(zuordnen(antwort("x@y.de", "Frage zu AN-2026-0099", "ok"), zu), "")   # nicht ueber All-Inkl gesendet
        self.assertEqual(zuordnen(antwort("x@y.de", "Newsletter", "ok", auf="<luna-unbekannt@x.de>"), zu), "")
        self.assertEqual((art("AN-2026-0001"), art("RE-2026-0003-M1"), art("RG-11052026"), art("AB-2026-0002")),
                         ("Angebot", "Mahnung", "Rechnung", "Auftrag"))
        self.assertEqual(schluessel("<x@y>", b""), schluessel("<x@y>", b"anders"))
        self.assertRegex(schluessel("", b"inhalt"), r"^imap-[0-9a-f]{20}$")


class TestAblauf(ApiBasis):
    def _senden(self, pfad, body):
        p = []
        with mock.patch.object(self.w, "_google_secrets", return_value=ENV), \
             mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p)), mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)):
            r = self.c.post(pfad, json=body | {"bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        return [x[1] for x in p if x[0] == "send"][0]["Message-ID"]

    def test_angebot_und_auftrag(self):
        bh = self.w.kunden_store.bh
        an = self._neu()
        mid = self._senden(f"/api/crm/angebote/{an}/senden", {"an": "anna@brandx.de", "betreff": f"Angebot {an}", "text": "T"})
        self.assertIn(mid.strip("<>").split("@")[0], gesendete(bh.eintraege())[0])
        self.c.post(f"/api/crm/angebote/{an}/status", json={"status": "angenommen"})
        ab = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={}).json()["nummer"]
        mid_ab = self._senden(f"/api/crm/auftraege/{ab}/senden", {"an": "anna@brandx.de", "betreff": f"Auftrag {ab}", "text": "T"})
        meldungen = []
        notify = lambda text, **kw: meldungen.append(text)
        pf = Postfach([antwort("Anna <anna@brandx.de>", f"Re: Angebot {an}", "Passt, legen wir los!\n\nAm Montag schrieb LUNA:\n> alt",
                               auf=mid),
                       antwort("anna@brandx.de", "Re: Auftragsbestaetigung", "Danke!", auf=mid_ab, mid="<a2@brandx.de>"),
                       antwort("Nils <nils@hanserautisch.de>", f"Re: Angebot {an}", "selbst", auf=mid, mid="<c1@x>"),
                       antwort("spam@irgendwo.de", "Gewinnspiel", "!!!", mid="<s1@x>")])
        neu = antworten_pruefen(bh, self.w.kunden_store, pf, eigene=CEO + ["luna@hanserautisch.de"], notify=notify)
        self.assertEqual([(x["nummer"], x["ablage"]) for x in neu], [(an, "angebot"), (ab, "akte")])
        a = self.c.get(f"/api/crm/angebote/{an}").json()["angebot"]
        self.assertEqual(len(a["antworten"]), 1)
        self.assertEqual(a["antworten"][0]["vorschau"], "Passt, legen wir los!")          # Zitat abgeschnitten
        self.assertIn(neu[0]["id"], a["mail_archiv"])                                     # .eml am Angebot
        mail = self.c.get(f"/api/crm/angebote/{an}/mail/{neu[0]['id']}").json()
        self.assertIn("legen wir los", str(mail))
        from orchestrator.core.firmenakte import Firmenakte
        doks = Firmenakte(bh, self.w.kunden_store).zu_bezug(ab)
        self.assertEqual([(d["art"], d["firma"]) for d in doks], [("mail", self.k)])
        self.assertEqual(len(meldungen), 2)
        self.assertTrue(meldungen[0].startswith(f"✉️ Antwort auf Angebot {an} von Anna"))
        self.assertIn(f"Antwort auf Auftrag {ab}", meldungen[1])
        # zweiter Lauf: nichts doppelt
        self.assertEqual(antworten_pruefen(bh, self.w.kunden_store, pf, eigene=CEO, notify=notify), [])
        self.assertEqual(len(meldungen), 2)
        self.assertEqual(len(self.c.get(f"/api/crm/angebote/{an}").json()["angebot"]["antworten"]), 1)

    def test_testmail_antwort_auch_vom_ceo(self):
        mid = self._senden("/api/finanzen/kundenversand/testmail", {"an": "hsvnils@icloud.com"})
        meldungen = []
        pf = Postfach([antwort("Nils <hsvnils@icloud.com>", "Re: LUNA-Testmail ueber All-Inkl", "Kommt an!", auf=mid)])
        bh = self.w.kunden_store.bh
        neu = antworten_pruefen(bh, self.w.kunden_store, pf, eigene=CEO, notify=lambda t, **kw: meldungen.append(t))
        self.assertEqual([(x["nummer"], x["ablage"]) for x in neu], [("TESTMAIL", "keine")])
        self.assertIn("Testmail", meldungen[0])
        self.assertIn("Kommt an!", meldungen[0])
        from orchestrator.core.firmenakte import Firmenakte
        self.assertEqual(Firmenakte(bh, self.w.kunden_store).offene(), [])                 # nichts abgelegt
        self.assertEqual(antworten_pruefen(bh, self.w.kunden_store, pf, eigene=CEO), [])     # nur einmal
        # CEO antwortet auf einen echten Beleg -> weiter ignoriert
        an = self._neu()
        mid2 = self._senden(f"/api/crm/angebote/{an}/senden", {"an": "anna@brandx.de", "betreff": f"Angebot {an}", "text": "T"})
        pf2 = Postfach([antwort("hsvnils@icloud.com", f"Re: Angebot {an}", "intern", auf=mid2, mid="<c9@x>")])
        self.assertEqual(antworten_pruefen(bh, self.w.kunden_store, pf2, eigene=CEO), [])

    def test_ohne_allinkl_versand_nichts(self):
        an = self._neu()
        pf = Postfach([antwort("anna@brandx.de", f"Re: Angebot {an}", "Hallo")])
        self.assertEqual(antworten_pruefen(self.w.kunden_store.bh, self.w.kunden_store, pf, eigene=CEO), [])


class TestImapLesen(unittest.TestCase):
    def test_nur_lesen(self):
        p = []

        class Imap(FakeIMAP):
            def select(self, ordner, readonly=False):
                p.append(("select", ordner, readonly))
                return "OK", [b"2"]

            def uid(self, befehl, *args):
                p.append(("uid", befehl) + args)
                if befehl == "SEARCH":
                    return "OK", [b"7 8"]
                return "OK", [(b"7 (BODY[] {3}", b"roh" + args[0]), b")"]

        m = AllInklMail(ENV, imap_fabrik=lambda: Imap(p))
        r = m.posteingang(tage=30)
        self.assertEqual([(x["uid"], x["roh"]) for x in r], [("7", b"roh7"), ("8", b"roh8")])
        self.assertIn(("select", "INBOX", True), p)                                        # nur lesend geoeffnet
        self.assertTrue([x for x in p if x[:2] == ("uid", "FETCH")] and all(x[3] == "(BODY.PEEK[])" for x in p if x[:2] == ("uid", "FETCH")))   # Gelesen-Status bleibt
        self.assertRegex([x for x in p if x[:2] == ("uid", "SEARCH")][0][4], r"^\d\d-[A-Z][a-z]{2}-\d{4}$")
        self.assertEqual(AllInklMail({}).posteingang(), [])


if __name__ == "__main__":
    unittest.main()
