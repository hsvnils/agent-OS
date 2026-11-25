"""OFC_KASSE_ROADMAP KA3-KA5: Kassenbuch (Buchungen aus Eingaengen, eigenen Zahlungen, Handbuchungen), Kassenstand ab
Anfangsbestand, Storno statt Loeschen, Kategorie per Klick, Beleg nur neu, „Spaeter bezahlen“ vorgemerkt, nur CEO.
Fixtures ohne echte Daten."""
import base64
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core import ofc_eingang as oe
from orchestrator.core import ofc_kasse as ok
from orchestrator.core.ofc_store import OfcStore, import_anwenden
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_eingang import _erhalten, _ordner, _pp


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = Path(self.tmp.name) / "Tickets 26-27"
        _ordner(s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, s)
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00"),
                                      _erhalten("Fremde Person", "12,00", tc="2FF22222FF2222222", mid="<f@p>")])
        bank = _pp("Sie haben eine Rückzahlung gesendet", "Sie haben eine Rückzahlung an Hamburger Sparkasse AG ••1234 gesendet\n"
                   "Betrag 20,00\xa0€\xa0EUR\nTransaktionscode\n8BB88888BB8888888\n", "<b@p>")
        oe.eingang_anwenden(self.st, [bank])
        for z in ({"id": "z-1", "art": "gesendet", "betrag_cent": 7000, "datum": "2026-10-05", "zuordnung": "auto", "spiel": "HSV vs FCB",
                   "haendler": "CTS EVENTIM"},
                  {"id": "z-2", "art": "spaeter", "betrag_cent": 3000, "datum": "2026-10-01", "zuordnung": "auto", "spiel": "HSV vs FCB"},
                  {"id": "z-3", "art": "erstattung", "betrag_cent": 1000, "datum": "2026-10-09", "zuordnung": "auto"}):
            self.st.erfassen("ofc_zahlung", z)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()


class TestKasse(_Basis):
    def test_1_buchungen_aus_quellen(self):
        b = {x["id"]: x for x in ok.buchungen(self.st.stand(), heute=date(2026, 10, 20))}
        self.assertEqual((b["eingang:e-1EE11111EE1111111"]["betrag_cent"], b["eingang:e-1EE11111EE1111111"]["kategorie"]), (3500, "tickets"))
        self.assertEqual(b["eingang:e-2FF22222FF2222222"]["kategorie"], "offen")
        self.assertEqual((b["eingang:e-8BB88888BB8888888"]["betrag_cent"], b["eingang:e-8BB88888BB8888888"]["kategorie"]), (-2000, "auszahlung"))
        self.assertEqual((b["zahlung:z-1"]["betrag_cent"], b["zahlung:z-1"]["kategorie"]), (-7000, "tickets"))
        self.assertEqual((b["zahlung:z-2"]["status"], b["zahlung:z-2"]["datum"]), ("vorgemerkt", "2026-10-31"))   # faellig +30
        self.assertEqual(b["zahlung:z-3"]["betrag_cent"], 1000)
        self.assertEqual(ok.buchungen(self.st.stand(), heute=date(2026, 11, 20))[0]["status"] in ("gebucht", "vorgemerkt"), True)
        x = {y["id"]: y for y in ok.buchungen(self.st.stand(), heute=date(2026, 11, 20))}
        self.assertEqual(x["zahlung:z-2"]["status"], "gebucht")                                  # >5 Tage nach Faelligkeit

    def test_2_kassenstand_anfangsbestand_storno(self):
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertIsNone(k["kassenstand_cent"])
        self.assertEqual((k["einnahmen_cent"], k["ausgaben_cent"], k["vorgemerkt_cent"]), (5700, -9000, -3000))
        ok.anfangsbestand_setzen(self.st, "2026-10-06", 10000)
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertEqual(k["kassenstand_cent"], 10000 + 3500 + 1200 - 2000 + 1000)          # ab 06.10.: Eingaenge 07.10., Erstattung 09.10.
        r = ok.buchung_anlegen(self.st, datum="2026-10-10", betrag_cent=-349, kategorie="gebuehren", text="PayPal-Gebühr")
        self.assertTrue(r["ok"])
        self.assertEqual(ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))["kassenstand_cent"], 13700 - 349)
        ok.storno(self.st, r["id"])
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertEqual(k["kassenstand_cent"], 13700)
        self.assertEqual([b["status"] for b in k["buchungen"] if b["id"] == "kasse:" + r["id"]], ["storniert"])  # bleibt sichtbar
        ok.storno(self.st, r["id"], zurueck=True)
        self.assertEqual(ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))["kassenstand_cent"], 13700 - 349)
        self.assertFalse(ok.storno(self.st, "eingang:x")["ok"])
        ok.anfangsbestand_setzen(self.st, "2026-10-01", 0)                                       # Historie, der letzte gilt
        self.assertEqual(len(self.st.stand()["kasse_start"]), 2)

    def test_3_eingaben_pruefen_kategorie_beleg(self):
        for kw in ({"datum": "x", "betrag_cent": 1, "kategorie": "gebuehren", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 0, "kategorie": "gebuehren", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 1, "kategorie": "offen", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 1, "kategorie": "gebuehren", "text": " "}):
            self.assertFalse(ok.buchung_anlegen(self.st, **kw)["ok"], kw)
        self.assertFalse(ok.buchung_anlegen(self.st, datum="2026-10-01", betrag_cent=-100, kategorie="auslagen", text="x",
                                            beleg=b"MZ", beleg_name="a.exe")["ok"])
        r = ok.buchung_anlegen(self.st, datum="2026-10-01", betrag_cent=-100, kategorie="auslagen", text="Kleber", beleg=b"%PDF-1.4", beleg_name="q.pdf")
        p = ok.beleg_pfad(self.st, r["id"])
        self.assertTrue(p and p.read_bytes().startswith(b"%PDF"))
        self.assertIsNone(ok.beleg_pfad(self.st, "k-gibtsnicht"))
        self.assertTrue(ok.kategorie_setzen(self.st, "eingang:e-2FF22222FF2222222", "spenden")["ok"])
        b = {x["id"]: x for x in ok.buchungen(self.st.stand())}
        self.assertEqual(b["eingang:e-2FF22222FF2222222"]["kategorie"], "spenden")
        self.assertFalse(ok.kategorie_setzen(self.st, "eingang:gibtsnicht", "spenden")["ok"])
        self.assertFalse(ok.kategorie_setzen(self.st, "eingang:e-2FF22222FF2222222", "xyz")["ok"])
        src = Path(ok.__file__).read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "os.remove", "os.replace", "shutil", '"wb"'):
            self.assertNotIn(verboten, src, verboten)


class TestKasseApi(ApiBasis):
    def test_4_endpunkte_nur_ceo(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.w, "ROOT", Path(d)):
            self.assertTrue(self.c.get("/api/ofc/kasse").json()["ok"])
            self.assertFalse(self.c.post("/api/ofc/kasse/buchung", json={"datum": "2026-10-01", "betrag_cent": -100}).json()["ok"])
            r = self.c.post("/api/ofc/kasse/buchung", json={"datum": "2026-10-01", "betrag_cent": -100, "kategorie": "gebuehren",
                                                            "text": "Gebühr", "bestaetigt": True,
                                                            "beleg": {"name": "b.png", "daten": base64.b64encode(b"\x89PNG").decode()}}).json()
            self.assertTrue(r["ok"])
            self.assertEqual(self.c.get(f"/api/ofc/kasse/beleg/{r['id']}").headers["content-type"], "image/png")
            self.assertTrue(self.c.post("/api/ofc/kasse/anfangsbestand", json={"datum": "2026-09-30", "betrag_cent": 5000, "bestaetigt": True}).json()["ok"])
            self.assertEqual(self.c.get("/api/ofc/kasse").json()["kassenstand_cent"], 4900)
            self.assertTrue(self.c.post("/api/ofc/kasse/storno", json={"id": r["id"], "bestaetigt": True}).json()["storniert"])
            self.assertTrue(self.c.post("/api/ofc/kasse/kategorie", json={"quelle": "kasse:" + r["id"], "kategorie": "auslagen"}).json()["ok"])
            self.assertFalse(self.c.post("/api/ofc/kasse/anfangsbestand", json={"datum": "2026-09-30", "betrag_cent": "x", "bestaetigt": True}).json()["ok"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/kasse").status_code, 403)
                self.assertEqual(self.c.get(f"/api/ofc/kasse/beleg/{r['id']}").status_code, 403)
                for url in ("/api/ofc/kasse/buchung", "/api/ofc/kasse/storno", "/api/ofc/kasse/kategorie", "/api/ofc/kasse/anfangsbestand"):
                    self.assertEqual(self.c.post(url, json={"bestaetigt": True}).status_code, 403, url)
