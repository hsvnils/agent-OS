"""Self-Checks Angebote (KUNDEN_FINANZEN_ROADMAP.md, Etappe 3): Nummer AN-, Positionen in Cent, Status, PDF,
Gmail-Entwurf mit Anhang, Kalender-Erinnerungen, CRM-Stufe -- offline (Google-Attrappe)."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from orchestrator.core.angebote import AngebotStore
from orchestrator.core.beleg_pdf import _latin1, beleg_pdf, cent, eur, menge, positions_summe
from orchestrator.core.buchhaltung import Buchhaltung, jetzt
from orchestrator.core.kunden import KundenStore

FIRMA = {"firma": "Krüger Onlinehandel und Media", "zusatz": "c/o Hanserautisch", "inhaber": "Nils Krüger",
         "strasse": "Arthur-Soltau-Weg 7c", "plz": "22889", "ort": "Tangstedt",
         "bank": {"kontoinhaber": "Nils Krüger", "iban": "DE00123456780000000000", "bic": "TESTDEFFXXX", "bank": "Testbank"}}


def _stores():
    bh = Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")
    ks = KundenStore(bh)
    k = ks.firma_anlegen({"name": "Brand X GmbH", "strasse": "Hafenstr. 1", "plz": "20095", "ort": "Hamburg",
                          "rechnungsmail": "rechnung@brandx.de"})["nummer"]
    ap = ks.ansprechpartner_anlegen(k, {"vorname": "Anna", "nachname": "Muster", "mail": "anna@brandx.de"})["nummer"]
    return bh, ks, AngebotStore(bh, ks), k, ap


POS = [{"beschreibung": "Reel-Produktion inkl. Schnitt", "menge": "2", "einheit": "Stück", "einzelpreis": "450,00"},
       {"beschreibung": "Story-Paket", "menge": "1,5", "einheit": "Std.", "einzelpreis": "80"}]


class TestGeld(unittest.TestCase):
    def test_1_parsen_und_format(self):
        self.assertEqual([cent(x) for x in ("1.234,50", "1234.50", "1234,5", 12, 12.345, "0,005")],
                         [123450, 123450, 123450, 1200, 1235, 1])
        # deutscher Tausenderpunkt ohne Komma (Befund Etappe 3b): „1.600“ ist 1.600 €, „1.5“/„1.50“ bleiben Dezimal
        self.assertEqual([cent(x) for x in ("1.600", "12.345.678", "1.5", "1.50", "1.6000")],
                         [160000, 1234567800, 150, 150, 160])
        self.assertEqual(eur(123450), "1.234,50 €")
        self.assertEqual(eur(-5), "-0,05 €")
        self.assertEqual(positions_summe("1.5", 8000), 12000)
        self.assertEqual(positions_summe("0.333", 100), 33)
        for falsch in ("abc", "", None, "NaN", True):
            with self.assertRaises(ValueError, msg=falsch):
                cent(falsch)
        with self.assertRaises(ValueError):
            menge("0")
        self.assertEqual(_latin1("1 € – „x“"), '1 EUR - "x"')


class TestAngebotStore(unittest.TestCase):
    def test_1_anlegen_nummer_summe(self):
        bh, ks, st, k, ap = _stores()
        nr = st.anlegen({"firma": k, "ansprechpartner": ap, "titel": "Kampagne Herbst", "positionen": POS},
                        von="LUNA-OS:ceo")["nummer"]
        self.assertEqual(nr, f"AN-{jetzt().year}-0001")
        a = st.angebot(nr)
        self.assertEqual([p["gesamt_cent"] for p in a["positionen"]], [90000, 12000])
        self.assertEqual(a["summe_cent"], 102000)
        self.assertEqual((a["status"], a["nachfassen_tage"]), ("entwurf", 7))
        self.assertEqual(a["gueltig_bis"], (date.fromisoformat(a["datum"]) + timedelta(days=14)).isoformat())
        self.assertEqual(st.liste()[0]["firma_name"], "Brand X GmbH")
        self.assertEqual(bh.pruefe_kette(), [])

    def test_2_validierung_ohne_nummernverbrauch(self):
        bh, ks, st, k, ap = _stores()
        vorher = len(bh.eintraege("nummer"))
        for falsch in ({"firma": k, "positionen": []}, {"firma": "K-09999", "positionen": POS},
                       {"firma": k, "positionen": [{"beschreibung": "", "einzelpreis": "1"}]},
                       {"firma": k, "positionen": [{"beschreibung": "x", "einzelpreis": "-1"}]},
                       {"firma": k, "positionen": POS, "datum": "2026-10-10", "gueltig_bis": "2026-10-01"},
                       {"firma": k, "positionen": POS, "datum": "gestern"}):
            with self.assertRaises((ValueError, KeyError), msg=falsch):
                st.anlegen(falsch)
        k2 = ks.firma_anlegen({"name": "Andere"})["nummer"]
        with self.assertRaises(ValueError):                                           # AP einer fremden Firma
            st.anlegen({"firma": k2, "ansprechpartner": ap, "positionen": POS})
        self.assertEqual(len(bh.eintraege("nummer")), vorher + 1)                     # nur K-00002

    def test_3_aendern_nur_im_entwurf(self):
        bh, ks, st, k, ap = _stores()
        nr = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        self.assertEqual(st.aendern(nr, {"titel": "Neu", "positionen": POS[:1]})["geaendert"], ["positionen", "titel"])
        self.assertEqual(st.angebot(nr)["summe_cent"], 90000)
        self.assertEqual(st.aendern(nr, {"titel": "Neu"}), {"geaendert": []})
        st.status_setzen(nr, "versendet")
        with self.assertRaises(ValueError):
            st.aendern(nr, {"titel": "zu spaet"})
        with self.assertRaises(ValueError):
            st.status_setzen(nr, "versendet")
        st.status_setzen(nr, "angenommen", grund="per Mail")
        with self.assertRaises(ValueError):
            st.status_setzen(nr, "abgelehnt")
        self.assertEqual(st.angebot(nr)["status"], "angenommen")

    def test_4_abgelaufen_abgeleitet(self):
        bh, ks, st, k, ap = _stores()
        nr = st.anlegen({"firma": k, "positionen": POS, "datum": "2026-01-01", "gueltig_bis": "2026-01-31"})["nummer"]
        self.assertEqual(nr, "AN-2026-0001")                                          # Jahr aus dem Angebotsdatum
        self.assertEqual(st.angebot(nr)["anzeige_status"], "entwurf")
        st.status_setzen(nr, "versendet")
        self.assertEqual(st.angebot(nr)["anzeige_status"], "abgelaufen")
        self.assertEqual(st.angebot(nr)["status"], "versendet")

    def test_5_pdf_und_ablage(self):
        bh, ks, st, k, ap = _stores()
        nr = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": POS * 12})["nummer"]  # 24 Pos. -> 2 Seiten
        pdf = st.pdf(nr, FIRMA)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"/Count 2", pdf)
        r = st.pdf_ablegen(nr, pdf, an="anna@brandx.de", entwurf_id="d1")
        self.assertEqual((bh.dir / r["pfad"]).read_bytes(), pdf)
        a = st.angebot(nr)
        self.assertEqual((a["pdfs"][0]["inhalt"], a["pdfs"][0]["an"]), (a["inhalt"], "anna@brandx.de"))
        self.assertEqual(bh.eintraege("beleg")[0]["daten"]["art"], "geschaeftsbrief")
        self.assertEqual(bh.pruefe_belege(), [])

    def test_6_pdf_ohne_unicode_schrift(self):
        pdf = beleg_pdf(art="Angebot", nummer="AN-2026-0001", firma=FIRMA, empfaenger=["Brand X – GmbH"],
                        infos=[("Datum", "01.10.2026")], einleitung="„Hallo“ …",
                        positionen=[{"beschreibung": "x", "menge": "1", "einheit": "", "einzelpreis_cent": 100,
                                     "gesamt_cent": 100}], summe_cent=100, hinweise=["§ 19"], schluss="",
                        schrift_dir=Path(tempfile.mkdtemp()))
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestAngebotApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.crm import CrmStore
        from orchestrator.governance.google_workspace import MockGoogleWorkspace
        self.w = webapp
        self.orig = (webapp.kunden_store, webapp.crm_store, webapp._GOOGLE)
        bh, ks, st, self.k, self.ap = _stores()
        (bh.dir / "firmendaten.json").write_text(json.dumps(FIRMA), encoding="utf-8")
        webapp.kunden_store = ks
        webapp.crm_store = CrmStore(bh.dir.parent / "crm.jsonl")
        webapp.crm_store.nachricht_erfassen("Brand_X", "Kooperation?", quelle="instagram")
        ks.collab_zuordnen(self.k, "Brand_X")
        self.g = webapp._GOOGLE = MockGoogleWorkspace()
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.kunden_store, self.w.crm_store, self.w._GOOGLE = self.orig

    def _neu(self, **extra):
        r = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap,
                                                               "titel": "Herbst", "positionen": POS} | extra}).json()
        self.assertTrue(r["ok"], r)
        return r["nummer"]

    def test_1_ablauf_bis_versendet(self):
        nr = self._neu()
        pdf = self.c.get(f"/api/crm/angebote/{nr}/pdf")
        self.assertEqual((pdf.status_code, pdf.headers["content-type"]), (200, "application/pdf"))
        r = self.c.post(f"/api/crm/angebote/{nr}/mailentwurf", json={}).json()
        self.assertEqual((r["ok"], r["an"]), (True, "anna@brandx.de"))                # AP-Mail vor Rechnungs-Mail
        e = self.g.entwuerfe[-1]
        self.assertEqual(e["anhaenge"][0][0], f"Angebot_{nr}.pdf")
        self.assertIn("1.020,00 €", e["text"])
        self.assertEqual(self.c.get(f"/api/crm/angebote/{nr}/pdf?archiv=1").status_code, 200)
        v = self.c.post(f"/api/crm/angebote/{nr}/versendet").json()
        self.assertTrue(v["ok"], v)
        self.assertEqual(len(v["termine"]), 2)                                        # Nachfassen + vor Ablauf
        self.assertTrue(self.g.termine[0]["titel"].startswith(f"Angebot {nr} nachfassen"))
        self.assertEqual(v["hinweise"], [])
        self.assertEqual(self.w.crm_store.firmen()[0]["status"], "angebot")
        d = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual((d["status"], d["versendet_pdf"]), ("versendet", d["pdfs"][0]["pfad"]))
        self.assertEqual(len(d["pdfs"]), 1)                                           # kein zweites PDF noetig
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}", json={"angebot": {"titel": "x"}}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "angenommen"}).json()["ok"])

    def test_2_geaendert_nach_entwurf_legt_neuen_stand_ab(self):
        nr = self._neu()
        self.c.post(f"/api/crm/angebote/{nr}/mailentwurf", json={})
        self.c.post(f"/api/crm/angebote/{nr}", json={"angebot": {"titel": "Geaendert"}})
        v = self.c.post(f"/api/crm/angebote/{nr}/versendet").json()
        self.assertIn("geaendert", v["hinweise"][0])
        self.assertEqual(len(self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]["pdfs"]), 2)

    def test_3_fehlerfaelle(self):
        nr = self._neu(gueltig_bis=(jetzt().date() + timedelta(days=7)).isoformat())
        self.w.kunden_store.ansprechpartner_aendern(self.ap, {"mail": ""})
        self.w.kunden_store.firma_aendern(self.k, {"rechnungsmail": ""})
        r = self.c.post(f"/api/crm/angebote/{nr}/mailentwurf", json={}).json()
        self.assertIn("Keine Mail-Adresse", r["hinweis"])
        self.assertEqual(self.c.post(f"/api/crm/angebote/{nr}/mailentwurf", json={"an": "x@y.de"}).json()["an"], "x@y.de")
        (self.w.kunden_store.bh.dir / "firmendaten.json").unlink()
        self.assertEqual(self.c.get(f"/api/crm/angebote/{nr}/pdf").status_code, 409)
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "angenommen"}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "quatsch"}).json()["ok"])
        self.assertEqual(self.c.get("/api/crm/angebote/AN-2026-0999").status_code, 404)

    def test_4_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/crm/angebote/AN-2026-0001/mailentwurf"), "crm")
        self.assertIn("angebote", erlaubte_apps({"role": "team", "allowed_modules": ["crm"]}))


if __name__ == "__main__":
    unittest.main()
