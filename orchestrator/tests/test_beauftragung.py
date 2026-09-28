"""KUNDEN_FINANZEN Etappe 4: Auftrag AB- aus angenommenem Angebot, Verknuepfung, Status, PDF, Versand."""
import json
import unittest
from unittest import mock

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.tests.test_angebote import FIRMA, POS, ApiBasis, _stores


def _buch():
    bh, ks, st, k, ap = _stores()
    nr = st.anlegen({"firma": k, "ansprechpartner": ap, "titel": "Herbst", "positionen": POS,
                     "zuschlaege": [{"name": "Rechte", "prozent": 25}], "rabatt_prozent": 10})["nummer"]
    return bh, ks, st, AuftragBuch(bh, ks, st), nr


class TestAuftragBuch(unittest.TestCase):
    def test_1_nur_aus_angenommenem_angebot_genau_einmal(self):
        bh, ks, st, ab, an = _buch()
        with self.assertRaises(ValueError):
            ab.aus_angebot(an)                                                         # noch Entwurf
        st.status_setzen(an, "versendet")
        with self.assertRaises(ValueError):
            ab.aus_angebot(an)                                                         # noch nicht angenommen
        st.status_setzen(an, "angenommen")
        nr = ab.aus_angebot(an, leistung_von="2026-10-01", leistung_bis="2026-10-31", notiz="Start nach Abstimmung",
                            von="LUNA-OS:ceo")["nummer"]
        self.assertEqual(nr, f"AB-{jetzt().year}-0001")
        with self.assertRaises(ValueError):
            ab.aus_angebot(an)                                                         # kein zweiter Auftrag
        a = ab.auftrag(nr)
        self.assertEqual((a["angebot"], a["status"], a["leistung_von"]), (an, "beauftragt", "2026-10-01"))
        self.assertEqual(a["summe_cent"], st.angebot(an)["summe_cent"])                 # Summen wie im Angebot
        self.assertEqual(st.angebot(an)["auftrag"], nr)                                 # Verknuepfung zurueck
        self.assertEqual(len(bh.eintraege("nummer")), 4)                                # K, AP, AN, AB -- Fehlversuche ohne Nummer
        self.assertEqual(bh.pruefe_kette(), [])

    def test_2_aendern_und_status(self):
        bh, ks, st, ab, an = _buch()
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        nr = ab.aus_angebot(an)["nummer"]
        with self.assertRaises(ValueError):
            ab.aendern(nr, {"leistung_von": "2026-10-10", "leistung_bis": "2026-10-01"})
        self.assertEqual(ab.aendern(nr, {"notiz": "neu"})["geaendert"], ["notiz"])
        self.assertEqual(ab.aendern(nr, {"notiz": "neu"})["geaendert"], [])
        ab.status_setzen(nr, "erledigt", grund="geliefert")
        with self.assertRaises(ValueError):
            ab.aendern(nr, {"notiz": "zu spaet"})
        with self.assertRaises(ValueError):
            ab.status_setzen(nr, "storniert")
        self.assertEqual(ab.auftrag(nr)["status"], "erledigt")

    def test_3_pdf_beide_layouts(self):
        bh, ks, st, ab, an = _buch()
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        nr = ab.aus_angebot(an, leistung_von="2026-10-01")["nummer"]
        self.assertTrue(ab.pdf(nr, FIRMA).startswith(b"%PDF"))                          # Standard (Angebot ohne Katalog)
        r = ab.pdf_ablegen(nr, ab.pdf(nr, FIRMA), an="x@y.de")
        self.assertEqual(ab.auftrag(nr)["pdfs"][0]["pfad"], r["pfad"])
        self.assertEqual(bh.pruefe_belege(), [])


class TestAuftragApi(ApiBasis):
    """Nutzt das Setup der Angebots-API-Tests (Mock-Google, Firmendaten, Collab)."""

    def _angenommen(self):
        nr = self._neu()
        self.c.post(f"/api/crm/angebote/{nr}/senden", json={"an": "p@example.com", "betreff": "B", "text": "T", "bestaetigt": True})
        return nr

    def test_a1_annehmen_und_auftrag_in_einem_schritt(self):
        an = self._angenommen()
        r = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True, "leistung_von": "2026-10-01"}).json()
        self.assertTrue(r["ok"], r)
        a = self.c.get(f"/api/crm/angebote/{an}").json()["angebot"]
        self.assertEqual((a["status"], a["auftrag"]), ("angenommen", r["nummer"]))
        self.assertEqual(self.w.crm_store.firmen()[0]["status"], "vereinbart")          # CRM-Stufe
        d = self.c.get(f"/api/crm/auftraege/{r['nummer']}").json()
        self.assertEqual((d["auftrag"]["angebot"], d["mail_an"]), (an, "anna@brandx.de"))
        self.assertEqual(self.c.get("/api/crm/auftraege").json()["auftraege"][0]["nummer"], r["nummer"])
        self.assertFalse(self.c.post(f"/api/crm/angebote/{an}/auftrag", json={}).json()["ok"])   # nur einmal

    def test_a2_senden_nur_ceo_mit_bestaetigung(self):
        an = self._angenommen()
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.assertEqual(self.c.get(f"/api/crm/auftraege/{nr}/pdf").status_code, 200)
        v = self.c.get(f"/api/crm/auftraege/{nr}/versandvorschau").json()
        self.assertIn(an, v["text"])
        roh = {"an": "p@example.com", "betreff": v["betreff"], "text": v["text"]}
        self.assertFalse(self.c.post(f"/api/crm/auftraege/{nr}/senden", json=roh).json()["ok"])
        with mock.patch.object(self.w, "hat_modul", return_value=False):
            self.assertIn("nur der CEO", self.c.post(f"/api/crm/auftraege/{nr}/senden", json=roh | {"bestaetigt": True}).json()["hinweis"])
        vorher = len(self.g.gesendet)
        self.assertTrue(self.c.post(f"/api/crm/auftraege/{nr}/senden", json=roh | {"bestaetigt": True}).json()["ok"])
        self.assertEqual(len(self.g.gesendet), vorher + 1)
        self.assertEqual(self.g.gesendet[-1]["anhaenge"][0][0], f"Auftragsbestaetigung_{nr}.pdf")
        a = self.c.get(f"/api/crm/auftraege/{nr}").json()["auftrag"]
        self.assertEqual((a["status"], a["gesendet_mail"]["an"]), ("beauftragt", "p@example.com"))   # Senden aendert Status nicht
        self.assertTrue(self.c.post(f"/api/crm/auftraege/{nr}/status", json={"status": "erledigt"}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/auftraege/{nr}/status", json={"status": "quatsch"}).json()["ok"])

    def test_a3_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/crm/auftraege/AB-2026-0001/senden"), "crm")
        # Auftraege sind ein Tab im Bereich Angebote (App-ID „auftraege“ gehoert dem Backoffice / Modul administration)
        self.assertIn("angebote", erlaubte_apps({"role": "team", "allowed_modules": ["crm"]}))


if __name__ == "__main__":
    unittest.main()
