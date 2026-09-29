"""CEO 2026-09-29: Beleg-Mails, die LUNA erledigt hat, wandern aus dem Posteingang in `LUNA/<Art>/<Jahr>` und
sind gelesen; alles andere bleibt im Posteingang. Nur nach sicherer Aufnahme, protokolliert, nachholend."""
import unittest
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eingangsbelege import MAIL_ABGELEGT, mail_eingang_pruefen, mail_ordner, mails_ablegen
from orchestrator.tests.test_eingangsbelege import TEXT, _Google, _pdf, _store

ABS = ["hsvnils@icloud.com"]
NILS = "Nils <hsvnils@icloud.com>"
META = ("Meta Platforms Ireland Ltd.\nREMITTANCE\nPayment Number: 2916\nPayment Date: 15-Sep-2026\n"
        "Payment Currency: USD\nTotal: $282.37")


class _Ablage(_Google):
    """Google-Ersatz mit Ordner-Ablage; `kaputt` = Ablage scheitert (z. B. Recht fehlt noch)."""
    def __init__(self, mails, kaputt=False):
        super().__init__(mails)
        self.kaputt, self.abgelegt = kaputt, []
    def mail_ablegen(self, mid, ordner):
        if self.kaputt:
            return {"ok": False, "hinweis": "Mail ablegen fehlgeschlagen: 403 insufficient scopes"}
        self.abgelegt.append((mid, ordner))
        return {"ok": True}


def _protokoll(st):
    return [e["daten"] for e in st.bh.eintraege() if e["typ"] == MAIL_ABGELEGT]


class TestMailAblage(unittest.TestCase):
    def test_1_rechnung_gutschrift_doppelt(self):
        st = _store()
        g = _Ablage({"m1": (NILS, [("Rechnung.pdf", _pdf(TEXT))]),
                     "m2": (NILS, [("meta.pdf", _pdf(META))]),
                     "m3": (NILS, [("Rechnung-nochmal.pdf", _pdf(TEXT))]),               # gleiche PDF wie m1
                     "m4": (NILS, [("logo.gif", b"GIF89a")]),                             # nichts erkannt -> bleibt
                     "m5": ("Fremd <evil@example.com>", [("Rechnung.pdf", _pdf("Fremd " * 20))])})
        neu = mail_eingang_pruefen(st, g, absender=ABS)
        self.assertEqual(len(neu), 2)
        self.assertEqual(sorted(g.abgelegt), [("m1", "LUNA/Rechnungen/2026"), ("m2", "LUNA/Gutschriften/2026"),
                                              ("m3", f"LUNA/Doppelt/{jetzt().year}")])
        self.assertEqual({p["mail_id"]: p["belege"] for p in _protokoll(st)},
                         {"m1": [neu[0]], "m2": [neu[1]], "m3": [neu[0]]})              # Mail <-> Beleg nachvollziehbar
        abrufe = g.abrufe
        self.assertEqual(mail_eingang_pruefen(st, g, absender=ABS), [])
        self.assertEqual(len(g.abgelegt), 3)                                            # jede Mail genau einmal
        self.assertEqual(g.abrufe, abrufe + 1)                                          # nur m4 (neuer Prozess-Set) -- m1-m3 nie wieder

    def test_2_ablage_scheitert_dann_nachholen(self):
        """Solange das Google-Recht fehlt: nichts protokolliert, Mail bleibt; danach holt LUNA alles nach."""
        st = _store()
        mails = {"m1": (NILS, [("Rechnung.pdf", _pdf(TEXT))]), "m3": (NILS, [("r2.pdf", _pdf(TEXT))])}
        g = _Ablage(mails, kaputt=True)
        gesehen = set()
        neu = mail_eingang_pruefen(st, g, absender=ABS, gesehen=gesehen)
        self.assertEqual(len(neu), 1)
        self.assertEqual(_protokoll(st), [])
        self.assertNotIn("m3", gesehen)                                                 # Doppelt-Mail -> erneut versuchen
        g.kaputt = False
        self.assertEqual(mail_eingang_pruefen(st, g, absender=ABS, gesehen=gesehen), [])
        self.assertEqual(sorted(g.abgelegt), [("m1", "LUNA/Rechnungen/2026"), ("m3", f"LUNA/Doppelt/{jetzt().year}")])

    def test_3_verworfen_bleibt_und_jahr(self):
        st = _store()
        a = st.aufnehmen(_pdf(TEXT), "a.pdf", quelle="mail", mail_id="x1")["nummer"]
        b = st.aufnehmen(_pdf("Irgendwas ohne Datum " * 5), "b.pdf", quelle="mail", mail_id="x2")["nummer"]
        c = st.aufnehmen(_pdf("Hochgeladen " * 5), "c.pdf")["nummer"]                  # Upload: keine Mail
        st.verwerfen(b, "kein Beleg")
        g = _Ablage({})
        self.assertEqual(mails_ablegen(st, g), [{"mail_id": "x1", "ordner": "LUNA/Rechnungen/2026"}])
        self.assertEqual(mails_ablegen(st, g), [])
        self.assertTrue(a and c)
        self.assertEqual(mail_ordner({"eingegangen": "2027-01-03T10:00:00", "vorschlag": {"rechnungsdatum": ""}}),
                         "LUNA/Rechnungen/2027")                                        # ohne Datum: Eingangsjahr
        self.assertEqual(mail_ordner({"vorschlag": {"rechnungsdatum": "2026-12-30", "art": "ausgabe"},
                                      "felder": {"rechnungsdatum": "2025-12-30", "art": "einnahme"}}),
                         "LUNA/Gutschriften/2025")                                      # gebuchte Werte gehen vor

    def test_4_ohne_google_nichts(self):
        self.assertEqual(mails_ablegen(_store(), None), [])


class _Req:
    def __init__(self, f): self.f = f
    def execute(self): return self.f()


class _Svc:
    """Gmail-API-Attrappe: labels().list/create, messages().modify."""
    def __init__(self, labels=None):
        self.labels_ = dict(labels or {"INBOX": "INBOX"})
        self.angelegt, self.modify = [], []
    def users(self): return self
    def labels(self):
        svc = self
        class L:
            def list(self, userId): return _Req(lambda: {"labels": [{"name": n, "id": i} for n, i in svc.labels_.items()]})
            def create(self, userId, body):
                def f():
                    svc.angelegt.append(body["name"]); svc.labels_[body["name"]] = f"L{len(svc.labels_)}"
                    return {"id": svc.labels_[body["name"]]}
                return _Req(f)
        return L()
    def messages(self):
        svc = self
        class M:
            def modify(self, userId, id, body): return _Req(lambda: svc.modify.append((id, body)) or {})
        return M()


class TestGmailSchicht(unittest.TestCase):
    def _gw(self, svc):
        from orchestrator.governance.google_workspace import GoogleAuth, GoogleWorkspace
        auth = GoogleAuth(client_id="c", client_secret="s", refresh_token="r")
        auth.service = lambda api, version: svc
        return GoogleWorkspace(auth)

    def test_1_ordner_anlegen_verschieben_gelesen(self):
        svc = _Svc({"INBOX": "INBOX", "LUNA": "L9"})
        gw = self._gw(svc)
        self.assertTrue(gw.mail_ablegen("m1", "LUNA/Rechnungen/2026")["ok"])
        self.assertTrue(gw.mail_ablegen("m2", "LUNA/Rechnungen/2026")["ok"])
        self.assertEqual(svc.angelegt, ["LUNA/Rechnungen", "LUNA/Rechnungen/2026"])     # nur fehlende Ebenen, einmal
        lid = svc.labels_["LUNA/Rechnungen/2026"]
        self.assertEqual(svc.modify[0], ("m1", {"addLabelIds": [lid], "removeLabelIds": ["INBOX", "UNREAD", "SPAM"]}))

    def test_2_fehler_wird_gemeldet(self):
        svc = _Svc()
        def kaputt(**k): raise RuntimeError("403 Request had insufficient authentication scopes")
        svc.messages = lambda: type("M", (), {"modify": lambda self, **k: kaputt()})()
        r = self._gw(svc).mail_ablegen("m1", "LUNA/Doppelt/2026")
        self.assertFalse(r["ok"])
        self.assertIn("insufficient", r["hinweis"])

    def test_3_neues_recht_bricht_alten_token_nicht(self):
        """Der Token wird ohne Scope-Liste erneuert -> bis zur Neu-Anmeldung laufen Lesen/Kalender weiter."""
        from orchestrator.governance.google_workspace import SCOPES, GoogleAuth
        self.assertIn("https://www.googleapis.com/auth/gmail.modify", SCOPES)
        auth = GoogleAuth(client_id="c", client_secret="s", refresh_token="r")
        with mock.patch("google.oauth2.credentials.Credentials") as cred, \
                mock.patch("googleapiclient.discovery.build"):
            auth.service("gmail", "v1")
        self.assertNotIn("scopes", cred.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
