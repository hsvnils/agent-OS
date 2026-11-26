"""OFC (CEO 2026-11-26): Fanclub-Postfach in ALLEN Ordnern lesen -- nur lesend, nur erlaubte Absender, ohne Papierkorb/Spam/
Gesendet/Entwuerfe, gleiche Mail in zwei Ordnern nur einmal, ohne IMAP-LIST nur INBOX. Fixtures ohne echte Daten."""
import unittest

from orchestrator.governance.allinkl_mail import HsvInsideMail
from orchestrator.tests.test_ofc import ENV, _mail


def _m(von, mid, text="x"):
    b = _mail(von, "Tickets", text)
    return b.replace(b"Subject:", f"Message-ID: {mid}\r\nSubject:".encode(), 1)


class FakeOrdnerIMAP:
    LISTE = [b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren) "." "INBOX.Tickets 26-27"',
             b'(\\HasNoChildren \\Trash) "." "INBOX.Trash"', b'(\\HasNoChildren) "." "INBOX.Spam"',
             b'(\\HasNoChildren \\Sent) "." "INBOX.Sent"', b'(\\Noselect \\HasChildren) "." "Archiv"',
             b'(\\HasNoChildren) "." "INBOX.Entw\xc3\xbcrfe"', b'(\\HasNoChildren) "." Bestellungen']

    def __init__(self, p, ordner, liste=True):
        self.p, self.ordner, self.akt, self.liste = p, ordner, None, liste

    def login(self, *a):
        pass

    def list(self):
        if not self.liste:
            raise AttributeError("kein LIST")
        return "OK", list(self.LISTE)

    def select(self, name, readonly=False):
        self.p.append(("select", name, readonly))
        self.akt = name.strip('"')
        return ("OK", [b"1"]) if self.akt in self.ordner else ("NO", [b""])

    def uid(self, befehl, *args):
        self.p.append(("uid", befehl, self.akt) + tuple(a.decode() if isinstance(a, bytes) else a for a in args))
        mails = self.ordner.get(self.akt, {})
        if befehl == "SEARCH":
            return "OK", [" ".join(mails).encode()]
        uid, teil = (args[0].decode() if isinstance(args[0], bytes) else args[0]), args[1]
        von, roh = mails[uid]
        if "HEADER.FIELDS" in teil:
            mid = next((z for z in roh.decode().splitlines() if z.startswith("Message-ID:")), "")
            return "OK", [(b"x", f"From: {von}\r\n{mid}\r\n".encode())]
        return "OK", [(b"x", roh)]

    def logout(self):
        pass


class TestAlleOrdner(unittest.TestCase):
    def _pf(self, ordner, liste=True):
        p = []
        return HsvInsideMail(ENV, imap_fabrik=lambda: FakeOrdnerIMAP(p, ordner, liste)), p

    def test_alle_ordner_ohne_papierkorb_spam_gesendet(self):
        hsv = "HSV <tickets@hsv.de>"
        ordner = {"INBOX": {"1": (hsv, _m(hsv, "<a@hsv.de>"))},
                  "INBOX.Tickets 26-27": {"7": (hsv, _m(hsv, "<b@hsv.de>")), "8": (hsv, _m(hsv, "<a@hsv.de>")),
                                          "9": ("Freund <x@privat.de>", b"PRIVAT")},
                  "Bestellungen": {"3": (hsv, _m(hsv, "<c@hsv.de>"))},
                  "INBOX.Trash": {"4": (hsv, _m(hsv, "<d@hsv.de>"))}, "INBOX.Spam": {"5": (hsv, _m(hsv, "<e@hsv.de>"))},
                  "INBOX.Sent": {"6": (hsv, _m(hsv, "<f@hsv.de>"))}}
        pf, p = self._pf(ordner)
        out = pf.posteingang(tage=30, nur=("hsv.de",))
        self.assertEqual([x["uid"] for x in out], ["1", "Bestellungen:3", "INBOX.Tickets 26-27:7"])   # <a> nur einmal
        gewaehlt = [x[1].strip('"') for x in p if x[0] == "select"]
        self.assertEqual(gewaehlt, ["INBOX", "Bestellungen", "INBOX.Tickets 26-27"])
        self.assertTrue(all(x[2] is True for x in p if x[0] == "select"))                     # nur lesend
        self.assertIn(("select", '"INBOX.Tickets 26-27"', True), p)                           # Leerzeichen gequotet
        voll = [(x[2], x[4]) for x in p if x[:2] == ("uid", "FETCH") and x[-1] == "(BODY.PEEK[])"]
        self.assertNotIn(("INBOX.Tickets 26-27", "9"), voll)                                   # fremder Absender nie geladen
        self.assertFalse(any(x[1] in ("STORE", "COPY", "MOVE", "EXPUNGE") for x in p if x[0] == "uid"))

    def test_ohne_list_nur_inbox(self):
        hsv = "HSV <tickets@hsv.de>"
        pf, p = self._pf({"INBOX": {"1": (hsv, _m(hsv, "<a@hsv.de>"))}, "Bestellungen": {"3": (hsv, _m(hsv, "<c@hsv.de>"))}}, liste=False)
        self.assertEqual([x["uid"] for x in pf.posteingang(tage=30)], ["1"])


if __name__ == "__main__":
    unittest.main()
