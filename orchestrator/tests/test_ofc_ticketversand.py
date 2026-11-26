"""OFC_TICKETVERSAND TV1/TV2: Wallet-Link je Ticket nur ueber die Ticketnummer (auch aus Mails ohne PDF, nie Praefix-Treffer,
nur https, nur HSV, Handeintrag bleibt), Lauf alle 15 Minuten, Mitglied je Ticket, Tickets je Mitglied mit Offen-Betrag,
Spieltag aus dem Spielplan oder von Hand, Endpunkte nur CEO. Fixtures ohne echte Daten."""
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc, ofc_post, ofc_spielplan, ofc_wallet
from orchestrator.core.ofc_store import (OfcStore, import_anwenden, mitglied_setzen, spiel_detail, spieltag_setzen,
                                         tickets_je_mitglied, uebersicht)
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_post import _bytes_text
from orchestrator.tests.test_ofc_store import _saison

W = "https://www.eventimsports.de/wallet/"


def _wallet_mail(links, von="tickets@hsv.de", pdf=False):
    m = EmailMessage()
    m["From"], m["Subject"], m["Message-ID"] = von, "Deine Wallet-Tickets", "<w@hsv.de>"
    m.set_content("Hallo")
    m.add_alternative("<html><body>" + "".join(f"<a href='{u}'>26-27 Hamburger SV - FCB</a>" for u in links) + "</body></html>", subtype="html")
    if pdf:
        m.add_attachment(b"Ticketnummer: 262236181415-1", maintype="application", subtype="pdf", filename="t.pdf")
    return {"uid": "1", "roh": m.as_bytes()}


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.p = [mock.patch.object(ofc, "pdf_text", _pdf_als_text), mock.patch.object(ofc, "pdf_bytes_text", _bytes_text)]
        for x in self.p:
            x.start()
        self.s = _saison(self.d)
        self.st = OfcStore(self.d / "fanclub")
        import_anwenden(self.st, self.s)

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.tmp.cleanup()


class TestWallet(_Basis):
    def test_zuordnung_ueber_ticketnummer_auch_ohne_pdf(self):
        mails = [_wallet_mail([W + "262236181415-2/abc", W + "2622361814151/xyz", W + "unbekannt/1"])]
        r = ofc_wallet.wallet_anwenden(self.st, mails)
        t = self.st.stand()["tickets"]
        self.assertEqual(r["neu"], 2)
        self.assertEqual(t["262236181415-2"]["wallet"], W + "262236181415-2/abc")
        self.assertEqual(t["262236181415-1"]["wallet"], W + "2622361814151/xyz")       # Nummer ohne Strich im Link
        self.assertFalse(t["262236189999-1"].get("wallet"))
        self.assertEqual(ofc_wallet.wallet_anwenden(self.st, mails)["neu"], 0)        # nicht doppelt

    def test_kein_praefix_treffer(self):
        nrn = {"262236181415-1", "262236181415-12"}
        self.assertEqual(ofc_wallet.wallet_links(_wallet_mail([W + "262236181415-12/a"])["roh"], nrn), {"262236181415-12": W + "262236181415-12/a"})

    def test_nur_https_nur_hsv_nur_wallet(self):
        self.assertEqual(ofc_wallet.wallet_anwenden(self.st, [_wallet_mail(["http://www.eventimsports.de/wallet/262236181415-1/a"])])["neu"], 0)
        self.assertEqual(ofc_wallet.wallet_anwenden(self.st, [_wallet_mail([W + "262236181415-1/a"], von="x@fremd.de")])["neu"], 0)
        self.assertEqual(ofc_wallet.wallet_anwenden(self.st, [_wallet_mail(["https://www.hsv.de/news/262236181415-1"])])["neu"], 0)

    def test_handeintrag_bleibt(self):
        self.assertFalse(ofc_wallet.wallet_von_hand(self.st, "262236181415-1", "javascript:alert(1)")["ok"])
        self.assertFalse(ofc_wallet.wallet_von_hand(self.st, "262236181415-1", "https://a b")["ok"])
        self.assertTrue(ofc_wallet.wallet_von_hand(self.st, "262236181415-1", "https://wallet.example/h")["ok"])
        ofc_wallet.wallet_anwenden(self.st, [_wallet_mail([W + "262236181415-1/neu"])])
        self.assertEqual(self.st.stand()["tickets"]["262236181415-1"]["wallet"], "https://wallet.example/h")
        d = spiel_detail(self.st, "HSV vs FCB")
        self.assertEqual(next(t for t in d["tickets"] if t["ticketnr"] == "262236181415-1")["wallet"], "https://wallet.example/h")
        self.assertEqual(next(s for s in uebersicht(self.st)["spiele"] if s["id"] == "HSV vs FCB")["wallet"], 1)

    def test_lauf_holt_wallet_mit(self):
        pf = mock.Mock()
        pf.verfuegbar.return_value = True
        pf.posteingang.return_value = [_wallet_mail([W + "262236181415-1/l"])]
        with mock.patch.object(ofc, "nas_ordner", return_value=self.s):
            r = ofc_post.lauf(self.st, pf)
        self.assertEqual(r.get("wallet_neu"), 1, r)
        self.assertEqual(pf.posteingang.call_count, 1)                                # dieselben Mails, kein zweiter Abruf


class TestMitglied(_Basis):
    def test_mitglied_und_tickets_je_mitglied(self):
        self.assertTrue(mitglied_setzen(self.st, "262236181415-1", "1004")["geaendert"])
        self.assertFalse(mitglied_setzen(self.st, "262236181415-1", "1004")["geaendert"])
        mitglied_setzen(self.st, "162236525621-7", "1004")
        r = tickets_je_mitglied(self.st, "1004")
        self.assertEqual((r["anzahl"], r["spiele"]), (2, 2))
        self.assertGreater(r["offen_cent"], 0)
        self.assertEqual(tickets_je_mitglied(self.st, "")["anzahl"], 0)                # leere Nummer = niemand
        self.assertEqual(tickets_je_mitglied(self.st, "100")["anzahl"], 0)             # kein Praefix-Treffer
        mitglied_setzen(self.st, "262236181415-1", "")                                 # Gast
        self.assertEqual(tickets_je_mitglied(self.st, "1004")["anzahl"], 1)


class TestSpielplan(_Basis):
    def test_kennung_aus_spielplan_und_von_hand(self):
        self.assertEqual(ofc_spielplan.kennung({"spieltag": "2026-11-28"})["kennung"], "11")
        self.assertEqual(ofc_spielplan.kennung({"spieltag": "2026-11-29"})["kennung"], "11")     # +-1 Tag (Verlegung)
        self.assertEqual(ofc_spielplan.kennung({"spieltag": "2026-10-27"})["kennung"], "P2")
        self.assertEqual(ofc_spielplan.kennung({"spieltag": "2026-07-15"})["kennung"], "")       # Testspiel: nichts raten
        self.assertEqual(spiel_detail(self.st, "HSV vs FCB")["spiel"]["kennung"]["kennung"], "11")
        self.assertFalse(spieltag_setzen(self.st, "HSV vs FCB", "35")["ok"])
        self.assertTrue(spieltag_setzen(self.st, "HSV vs FCB", "s1")["ok"])
        self.assertEqual(spiel_detail(self.st, "HSV vs FCB")["spiel"]["kennung"], {"kennung": "S1", "quelle": "hand", "spiel": ""})
        spieltag_setzen(self.st, "HSV vs FCB", "")
        self.assertEqual(spiel_detail(self.st, "HSV vs FCB")["spiel"]["kennung"]["quelle"], "spielplan")

    def test_zwei_spiele_dicht_beieinander_nicht_raten(self):
        dicht = (("1", "2026-08-01", "Hamburger SV", "A"), ("2", "2026-08-02", "B", "Hamburger SV"))
        with mock.patch.object(ofc_spielplan, "SPIELE", dicht):
            self.assertEqual(ofc_spielplan.kennung({"spieltag": "2026-08-01"})["kennung"], "")   # zwei Treffer -> kein Raten

    def test_spielplan_vollstaendig(self):
        bl = [s for s in ofc_spielplan.SPIELE if not s[0].startswith("P")]
        self.assertEqual(sorted(int(s[0]) for s in bl), list(range(1, 35)))
        self.assertEqual(len({s[1] for s in ofc_spielplan.SPIELE}), len(ofc_spielplan.SPIELE))   # ein Spiel je Tag
        self.assertTrue(all("Hamburger SV" in (s[2], s[3]) for s in ofc_spielplan.SPIELE))


class TestApi(ApiBasis):
    def test_endpunkte_nur_ceo_und_name_mit_mitglied(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.object(ofc, "nas_ordner", return_value=_saison(Path(d))):
            st = OfcStore(Path(d) / "fanclub")
            import_anwenden(st, Path(d) / "Tickets 26-27")
            with mock.patch.object(self.w, "_ofc_store", return_value=st):
                r = self.c.post("/api/ofc/ticket/262236181415-1/name", json={"bestaetigt": True, "name": "Anna", "mitglied": "1004"}).json()
                self.assertTrue(r["ok"], r)
                self.assertEqual(st.stand()["tickets"]["262236181415-1"]["mitglied"], "1004")
                self.assertEqual(self.c.get("/api/ofc/mitglied/1004/tickets").json()["anzahl"], 1)
                self.assertTrue(self.c.post("/api/ofc/spiel/HSV vs FCB/spieltag", json={"kennung": "P1"}).json()["ok"])
                self.assertFalse(self.c.post("/api/ofc/ticket/262236181415-1/wallet", json={"url": "https://x.example/w"}).json()["ok"])
                self.assertTrue(self.c.post("/api/ofc/ticket/262236181415-1/wallet", json={"bestaetigt": True, "url": "https://x.example/w"}).json()["ok"])
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    self.assertEqual(self.c.get("/api/ofc/mitglied/1004/tickets").status_code, 403)
                    for url in ("/api/ofc/spiel/HSV vs FCB/spieltag", "/api/ofc/ticket/262236181415-1/wallet", "/api/ofc/wallet/abholen"):
                        self.assertEqual(self.c.post(url, json={"bestaetigt": True}).status_code, 403, url)


if __name__ == "__main__":
    unittest.main()
