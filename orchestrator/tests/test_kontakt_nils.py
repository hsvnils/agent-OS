"""KONTAKTE K5: Absender nils@hanserautisch.de -- eigener Zugang (NILS_MAIL_*), Senden nur nach Klick, Kopie in „Gesendet“
von nils@; im Postfach nils@ werden NUR Antworten auf LUNA-Mails gelesen (Server-Suche nach Kennung + Kopf-Nachpruefung,
alle anderen Mails nie heruntergeladen, readonly); ohne Zugangsdaten bleibt nils@ gesperrt."""
from unittest import mock

from orchestrator.core.mail_antworten import antworten_pruefen, kontakt_mail_vermerken, kontakt_mails
from orchestrator.governance.allinkl_mail import NilsMail
from orchestrator.tests.test_allinkl_mail import ENV, FakeIMAP, FakeSMTP
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mail_antworten import CEO, Postfach, antwort

NILS = {"NILS_MAIL_USER": "nils@hanserautisch.de", "NILS_MAIL_PASSWORT": "nils-pruefwert-123", "NILS_MAIL_NAME": "Nils Test"}
KEN = "luna-" + "d" * 24


class FakeNilsIMAP:
    """Posteingang mit drei Mails: 1 = Antwort mit Kennung, 2 = Server-Treffer ohne echte Kennung, 3 = privat (kein Treffer)."""

    def __init__(self, p, mails):
        self.p, self.mails = p, mails

    def login(self, user, pw):
        self.p.append(("imap-login", user))

    def select(self, ordner, readonly=False):
        self.p.append(("select", ordner, readonly))
        return "OK", [b"3"]

    def uid(self, befehl, *args):
        self.p.append(("uid", befehl) + tuple(a.decode() if isinstance(a, bytes) else a for a in args))
        if befehl == "SEARCH":
            return "OK", [b"1 2"]                                              # Server filtert: Mail 3 kommt gar nicht vor
        uid, teil = args[0], args[1]
        kopf, roh = self.mails[uid.decode() if isinstance(uid, bytes) else uid]
        return "OK", [(b"x", kopf if "HEADER.FIELDS" in teil else roh)]

    def logout(self):
        pass


class TestNilsPostfach(ApiBasis):
    def test_1_nur_antworten_auf_luna_mails(self):
        p = []
        echte = antwort("kunde@firma.de", "Re: Hallo", "Gern!", auf=f"<{KEN}@hanserautisch.de>")
        mails = {"1": (f"In-Reply-To: <{KEN}@hanserautisch.de>\r\n".encode(), echte),
                 "2": (b"References: <luna-kurz@x.de>\r\n", b"GEHEIM privat")}
        n = NilsMail(ENV | NILS, imap_fabrik=lambda: FakeNilsIMAP(p, mails))
        out = n.posteingang(tage=30)
        self.assertEqual([x["uid"] for x in out], ["1"])
        self.assertIn(("select", "INBOX", True), p)                                                  # nur lesend
        suche = [x for x in p if x[:2] == ("uid", "SEARCH")][0]
        self.assertIn("In-Reply-To", suche)
        self.assertIn("References", suche)
        voll = [x for x in p if x[:2] == ("uid", "FETCH") and x[3] == "(BODY.PEEK[])"]
        self.assertEqual([x[2] for x in voll], ["1"])                                                # Mail 2 nie geladen
        self.assertFalse(any(x[:2] == ("uid", "STORE") or x[1] in ("COPY", "MOVE") for x in p if x[0] == "uid"))
        self.assertEqual(("imap-login", "nils@hanserautisch.de"), p[0])

    def test_2_nur_kontakt_im_postfach_nils(self):
        ks, bh = self.w.kunden_store, self.w.kunden_store.bh
        ap = ks.firma(self.k)["ansprechpartner_liste"][0]
        kontakt_mail_vermerken(bh, firma=self.k, ansprechpartner=ap["nummer"], message_id=KEN, betreff="Hallo", kanal="allinkl-nils")
        ken2 = "luna-" + "e" * 24                                       # z. B. Vorstellungs-Mail ueber luna@ -> nicht im nils-Postfach
        bh.erfassen("vorstellung_gesendet", {"nummer": self.k, "message_id": ken2, "kanal": "allinkl", "an": "x@y.de",
                                             "betreff": "Vorstellung"}, von="test")
        pf = Postfach([antwort(ap["mail"], "Re: Hallo", "Passt", auf=f"<{KEN}@hanserautisch.de>"),
                       antwort(ap["mail"], "Re: Vorstellung", "Interesse", auf=f"<{ken2}@hanserautisch.de>", mid="<v@x>")])
        neu = antworten_pruefen(bh, ks, pf, eigene=CEO, trocken=True, nur_kontakt=True)
        self.assertEqual([(x["nummer"], x["art"]) for x in neu], [(self.k, "kontakt")])
        alle = antworten_pruefen(bh, ks, pf, eigene=CEO, trocken=True)                               # Gegenprobe ohne Filter
        self.assertEqual(len(alle), 2)


class TestNilsSenden(ApiBasis):
    def setUp(self):
        super().setUp()
        self.ks, self.bh = self.w.kunden_store, self.w.kunden_store.bh
        self.ap = self.ks.firma(self.k)["ansprechpartner_liste"][0]

    def _mit(self, env, fn):
        p = []
        with mock.patch.object(self.w, "_google_secrets", return_value=env), \
             mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p)), \
             mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)):
            return fn(), p

    def _body(self, **kw):
        return {"firma": self.k, "ansprechpartner": self.ap["nummer"], "an": self.ap["mail"], "betreff": "Von Nils",
                "text": "Moin", "bestaetigt": True, "absender": "nils"} | kw

    def test_3_ohne_zugang_gesperrt(self):
        v, _ = self._mit(ENV, lambda: self.c.get(f"/api/crm/kontakt/mail/vorschau?firma={self.k}").json())
        self.assertEqual([(a["id"], a["frei"]) for a in v["absender"]], [("luna", True), ("nils", False)])
        self.assertIn("NILS_MAIL_USER", [a for a in v["absender"] if a["id"] == "nils"][0]["hinweis"])
        r, p = self._mit(ENV, lambda: self.c.post("/api/crm/kontakt/mail/senden", json=self._body()).json())
        self.assertFalse(r["ok"])
        self.assertFalse([x for x in p if x[0] == "send"])
        self.assertEqual(kontakt_mails(self.bh.eintraege()), {})

    def test_4_senden_als_nils(self):
        v, _ = self._mit(ENV | NILS, lambda: self.c.get(f"/api/crm/kontakt/mail/vorschau?firma={self.k}").json())
        self.assertEqual([(a["id"], a["frei"]) for a in v["absender"]], [("luna", True), ("nils", True)])
        self.assertEqual(v["nils_name"], "Nils Test")
        r, p = self._mit(ENV | NILS, lambda: self.c.post("/api/crm/kontakt/mail/senden", json=self._body()).json())
        self.assertTrue(r["ok"], r)
        msg = [x[1] for x in p if x[0] == "send"][0]
        self.assertEqual(msg["From"], "Nils Test <nils@hanserautisch.de>")
        self.assertRegex(msg["Message-ID"], r"^<luna-[0-9a-f]{24}@hanserautisch.de>$")              # Kennung fuer die Antwort
        self.assertEqual([x[1] for x in p if x[0] == "imap-login"], ["nils@hanserautisch.de"])     # Gesendet von nils@
        self.assertTrue([x for x in p if x[0] == "append"])
        km = kontakt_mails(self.bh.eintraege())
        self.assertEqual([(d["kanal"], d["firma"], d["ansprechpartner"]) for d in km.values()],
                         [("allinkl-nils", self.k, self.ap["nummer"])])
        # luna@ geht weiterhin ueber luna@
        r, p = self._mit(ENV | NILS, lambda: self.c.post("/api/crm/kontakt/mail/senden", json=self._body(absender="luna")).json())
        self.assertIn("luna@hanserautisch.de", [x[1] for x in p if x[0] == "send"][0]["From"])

    def test_5_verbindung_pruefen_ohne_versand(self):
        r, p = self._mit(ENV | NILS, lambda: self.c.get("/api/crm/kontakt/nils/pruefen").json())
        self.assertEqual((r["smtp"], r["imap"]), (True, True))
        self.assertFalse([x for x in p if x[0] in ("send", "append")])
        self.assertNotIn("nils-pruefwert-123", str(r))
        r, _ = self._mit(ENV, lambda: self.c.get("/api/crm/kontakt/nils/pruefen").json())
        self.assertEqual((r["ok"], r["fehlend"]), (False, ["NILS_MAIL_USER", "NILS_MAIL_PASSWORT"]))
