"""OFC_ROADMAP O3: Neue Bestellungen aus HSV-Mails -- Vorschau schreibt nichts, neuer Spielordner nach E3 (Heim/Auswaerts),
bekanntes Spiel wird ergaenzt (Rechnungsnr oder Paarung), Dublette nicht doppelt, Tickets ohne Rechnung bleiben „wartet“,
nie ueberschreiben, umbenannte Tickets (O2) nicht erneut, nur HSV-Absender, Verwerfen, Postfach nur hsv.de, Endpunkte nur CEO.
Fixtures ohne echte Daten."""
import os
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc, ofc_post
from orchestrator.core.ofc_store import OfcStore, import_anwenden, namen_setzen, spiel_verwerfen, uebersicht
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import AUSWAERTS, HEIM, _pdf_als_text
from orchestrator.tests.test_ofc_store import _saison


def _mail(von: str, anh: list[tuple[str, str]], mid: str = "<m1@hsv.de>") -> dict:
    m = EmailMessage()
    m["From"], m["Subject"], m["Message-ID"] = von, "Ihre Bestellung", mid
    m.set_content("Hallo")
    for name, text in anh:
        m.add_attachment(text.encode("utf-8"), maintype="application", subtype="pdf", filename=name)
    return {"uid": "1", "roh": m.as_bytes()}


def _bytes_text(b: bytes) -> str:
    return b.decode("utf-8")


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = self.d / "Tickets 26-27"
        self.s.mkdir()
        self.st = OfcStore(self.d / "fanclub")
        self.p1 = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p2 = mock.patch.object(ofc, "pdf_bytes_text", _bytes_text)
        self.p1.start(); self.p2.start()

    def tearDown(self):
        self.p1.stop(); self.p2.stop()
        self.tmp.cleanup()

    def heim_mails(self):
        return [_mail("HSV Service <service@service.hsv.de>", [("Rechnung.pdf", HEIM), ("AGB.pdf", "Allgemeine Bedingungen")]),
                _mail("noreply@hsv.de", [("262236181415-1.pdf", "Ticketnummer: 262236181415-1"),
                                         ("262236181415-2.pdf", "Ticketnummer: 262236181415-2")], "<m2@hsv.de>")]


class TestPost(_Basis):
    def test_1_neues_heimspiel_vorschau_dann_anlegen_wiederholbar(self):
        v = ofc_post.post_plan(self.st, self.heim_mails(), self.s)
        self.assertEqual((v["mails"], v["neu"], v["dateien"]), (2, 1, 3))
        b = v["bestellungen"][0]
        self.assertEqual((b["status"], b["ordner"], b["neu_ordner"], b["dateien_neu"]),
                         ("neu", "HSV vs FC Bayern Muenchen", True, ["Rechnung.pdf", "262236181415-1.pdf", "262236181415-2.pdf"]))
        self.assertEqual(list(self.s.iterdir()), [])                                         # Dry-Run
        self.assertNotIn("_dateien", ofc_post.oeffentlich(v))
        r = ofc_post.post_anwenden(self.st, self.heim_mails(), self.s, von="test")
        self.assertEqual((r["geschrieben"], r["import"]["tickets_neu"]), (3, 2))
        o = self.s / "HSV vs FC Bayern Muenchen"
        self.assertEqual(sorted(p.name for p in o.iterdir()), ["262236181415-1.pdf", "262236181415-2.pdf", "Rechnung.pdf"])
        sp = uebersicht(self.st)["spiele"][0]
        self.assertEqual((sp["id"], sp["karten"], sp["heimspiel"]), ("HSV vs FC Bayern Muenchen", 2, True))
        r = ofc_post.post_anwenden(self.st, self.heim_mails(), self.s)                       # zweiter Lauf: nichts
        self.assertEqual((r["geschrieben"], r["bestellungen"][0]["status"]), (0, "vorhanden"))
        self.assertEqual(self.st.eintraege()[-1]["typ"], "ofc_post")                        # kein neuer Eintrag beim Leerlauf
        self.assertEqual(sum(1 for e in self.st.eintraege() if e["typ"] == "ofc_post"), 1)

    def test_2_auswaerts_ordnername_und_nur_hsv(self):
        mails = [_mail("service@hsv.de", [("Rechnung.pdf", AUSWAERTS)]),
                 _mail("service@paypal.de", [("Rechnung.pdf", HEIM)], "<p@paypal.de>")]       # kein HSV-Absender
        v = ofc_post.post_plan(self.st, mails, self.s)
        self.assertEqual(v["mails"], 1)
        b = v["bestellungen"][0]
        self.assertTrue(b["ordner"].endswith(" vs HSV"), b["ordner"])
        self.assertIn("Ticket-PDFs noch nicht", b["hinweis"])

    def test_3_bekanntes_spiel_ergaenzen_und_umbenannte_nicht_doppelt(self):
        _saison(self.d)                                                                     # HSV vs FCB mit Ticket 1 (Anna)
        import_anwenden(self.st, self.s)
        namen_setzen(self.st, "262236181415-1", "Anna Neu", self.s)                         # O2 umbenannt
        v = ofc_post.post_plan(self.st, self.heim_mails(), self.s)
        b = v["bestellungen"][0]
        self.assertEqual((b["status"], b["ordner"], b["spiel_id"], b["dateien_neu"]),
                         ("ergaenzen", "HSV vs FCB", "HSV vs FCB", ["262236181415-2.pdf"]))  # Rechnung + Ticket 1 schon da
        ofc_post.post_anwenden(self.st, self.heim_mails(), self.s)
        t = self.st.stand()["tickets"]["262236181415-2"]
        self.assertEqual(t["datei"], "262236181415-2.pdf")
        self.assertIn("262236181415-1-Anna Neu.pdf", [p.name for p in (self.s / "HSV vs FCB").iterdir()])

    def test_4_tickets_ohne_rechnung_warten_nie_ueberschreiben(self):
        mails = [_mail("noreply@hsv.de", [("999999999999-1.pdf", "Ticketnummer: 999999999999-1")])]
        v = ofc_post.post_plan(self.st, mails, self.s)
        self.assertEqual((v["wartet"], v["dateien"], v["bestellungen"][0]["status"]), (1, 0, "wartet"))
        o = self.s / "HSV vs FC Bayern Muenchen"
        o.mkdir()
        (o / "Rechnung.pdf").write_text("fremde Datei", encoding="utf-8")                   # Ordner existiert, nicht im Speicher
        v = ofc_post.post_plan(self.st, self.heim_mails(), self.s)
        b = v["bestellungen"][0]
        self.assertEqual(b["ordner"], "HSV vs FC Bayern Muenchen (28.11.)")                 # eigener Ordner statt fremdem
        with mock.patch.object(ofc_post, "post_plan", return_value=v | {"_dateien": [(o, "Rechnung.pdf", b"neu")]}):
            r = ofc_post.post_anwenden(self.st, [], self.s)
        self.assertEqual(r["geschrieben"], 0)
        self.assertEqual((o / "Rechnung.pdf").read_text(encoding="utf-8"), "fremde Datei")   # nicht ueberschrieben

    def test_5_verwerfen_bleibt_verworfen(self):
        ofc_post.post_anwenden(self.st, self.heim_mails(), self.s)
        sid = "HSV vs FC Bayern Muenchen"
        self.assertTrue(spiel_verwerfen(self.st, sid)["ok"])
        u = uebersicht(self.st)
        self.assertEqual((u["spiele"], u["verworfen"]), ([], [sid]))
        self.assertTrue((self.s / sid / "Rechnung.pdf").exists())                           # Ordner bleibt
        mails = self.heim_mails() + [_mail("noreply@hsv.de", [("262236181415-3.pdf", "Ticketnummer: 262236181415-3")], "<m3@hsv.de>")]
        v = ofc_post.post_plan(self.st, mails, self.s)
        self.assertEqual((v["bestellungen"][0]["status"], v["dateien"]), ("verworfen", 0))
        import_anwenden(self.st, self.s)
        self.assertEqual(uebersicht(self.st)["spiele"], [])
        spiel_verwerfen(self.st, sid, verworfen=False)
        self.assertEqual(len(uebersicht(self.st)["spiele"]), 1)
        self.assertFalse(spiel_verwerfen(self.st, "gibtsnicht")["ok"])

    def test_6_lauf_postfach_nur_hsv_und_fehler_ohne_text(self):
        pf = mock.Mock(verfuegbar=mock.Mock(return_value=True), posteingang=mock.Mock(return_value=self.heim_mails()))
        with mock.patch.object(ofc, "nas_ordner", return_value=self.s):
            r = ofc_post.lauf(self.st, pf)
        self.assertEqual((r["geschrieben"], ofc_post.letzter_lauf()["geschrieben"]), (3, 3))
        pf.posteingang.assert_called_with(tage=ofc_post.TAGE, nur=("hsv.de",))
        pf.posteingang.side_effect = OSError("pw=geheim")
        r = ofc_post.lauf(self.st, pf)
        self.assertFalse(r["ok"]); self.assertNotIn("geheim", r["hinweis"])
        with mock.patch.dict(os.environ, {"OFC_AUTO_POST": "0"}):
            self.assertIsNone(ofc_post.starten(lambda: self.st, lambda: pf))
        with mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": str(self.d / "fehlt")}):
            self.assertIsNone(ofc_post.starten(lambda: self.st, lambda: pf))                # ohne Mount kein Hintergrund
        src = Path(ofc_post.__file__).read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "rename", '"wb"', "write_bytes", "mail_senden"):
            self.assertNotIn(verboten, src, verboten)                                        # nie loeschen/ueberschreiben/senden


class TestPostfachFilter(unittest.TestCase):
    def test_7_posteingang_nur_teilmenge(self):
        from orchestrator.governance.allinkl_mail import HsvInsideMail
        from orchestrator.tests.test_ofc import ENV, FakeIMAP
        p = []
        h = HsvInsideMail(ENV, imap_fabrik=lambda: FakeIMAP(p, {}))
        h.posteingang(tage=5, nur=("hsv.de",))
        suche = [x for x in p if x[:2] == ("uid", "SEARCH")][0]
        self.assertEqual(suche[-2:], ("FROM", "hsv.de"))
        self.assertNotIn("paypal.de", suche)
        p.clear()
        self.assertEqual(h.posteingang(tage=5, nur=("evil.com",)), [])                     # nie mehr als erlaubt
        self.assertEqual(p, [])


class TestApi(ApiBasis):
    def test_8_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.object(ofc, "pdf_bytes_text", _bytes_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            (Path(d) / "Tickets 26-27").mkdir()
            pf = mock.Mock(verfuegbar=mock.Mock(return_value=True),
                           posteingang=mock.Mock(return_value=_Basis.heim_mails(None)))
            with mock.patch.object(self.w, "_ofc_postfach", return_value=pf):
                v = self.c.get("/api/ofc/post/vorschau").json()
                self.assertEqual((v["ok"], v["dateien"]), (True, 3)); self.assertNotIn("_dateien", v)
                self.assertFalse(self.c.post("/api/ofc/post", json={}).json()["ok"])
                self.assertFalse((Path(d) / "Tickets 26-27" / "HSV vs FC Bayern Muenchen").exists())
                r = self.c.post("/api/ofc/post", json={"bestaetigt": True}).json()
                self.assertEqual(r["geschrieben"], 3)
                self.assertEqual(self.c.get("/api/ofc/post/status").json()["geschrieben"], 3)
                self.assertFalse(self.c.post("/api/ofc/spiel/HSV vs FC Bayern Muenchen/verwerfen", json={}).json()["ok"])
                self.assertTrue(self.c.post("/api/ofc/spiel/HSV vs FC Bayern Muenchen/verwerfen",
                                            json={"bestaetigt": True}).json()["verworfen"])
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    for url in ("/api/ofc/post/vorschau", "/api/ofc/post/status"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
                    self.assertEqual(self.c.post("/api/ofc/post", json={"bestaetigt": True}).status_code, 403)
