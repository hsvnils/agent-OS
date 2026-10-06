"""BELEG_BEARBEITBAR (CEO 2026-10-06): Belege bis zum Versand bearbeitbar, mit dem Versand festgeschrieben, danach nur
ueber „Bearbeiten“ mit Begruendung (neue Fassung). B1/B2: Auftrag."""
import json

from orchestrator.tests.test_angebote import FIRMA, ApiBasis

NEU_POS = [{"beschreibung": "Reel-Produktion inkl. Schnitt", "menge": "3", "einheit": "Stück", "einzelpreis": "450,00"}]


class TestAuftragBearbeitbar(ApiBasis):
    def setUp(self):
        super().setUp()
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps(FIRMA | {"steuernummer": "30/000/00000"}),
                                                                     encoding="utf-8")

    def _auftrag(self, **extra):
        r = self.c.post("/api/crm/auftraege", json={"auftrag": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst",
                                                                 "positionen": [{"beschreibung": "Story-Paket", "menge": "1",
                                                                                 "einheit": "", "einzelpreis": "100"}]} | extra,
                                                    "leistung_von": "2026-10-01", "leistung_bis": "2026-10-02"}).json()
        self.assertTrue(r["ok"], r)
        return r["nummer"]

    def _aendern(self, nr, **felder):
        return self.c.post(f"/api/crm/auftraege/{nr}", json={"auftrag": felder}).json()

    def _detail(self, nr):
        return self.c.get(f"/api/crm/auftraege/{nr}").json()["auftrag"]

    def _senden(self, nr):
        r = self.c.post(f"/api/crm/auftraege/{nr}/senden", json={"an": "p@example.com", "betreff": "B", "text": "T",
                                                                  "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)

    def test_b1_vor_dem_versand_alles_aenderbar(self):
        nr = self._auftrag()
        self.assertEqual(self._detail(nr)["sperre"], {})
        r = self._aendern(nr, positionen=NEU_POS, titel="Herbst neu", rabatt_prozent="10",
                          zahlung={"ziel_tage": "21", "vorkasse": {"art": "prozent", "wert": "50", "frist_tage": "7"}})
        self.assertTrue(r["ok"], r)
        a = self._detail(nr)
        self.assertEqual((a["titel"], a["summe_cent"], a["zahlung"]["ziel_tage"]), ("Herbst neu", 121500, 21))
        self.assertEqual(a["vorkasse_cent"], 60750)                                      # Vorkasse aus der neuen Fassung
        self.assertIn("positionen", a["verlauf"][-1]["felder"])
        pdf = self.c.get(f"/api/crm/auftraege/{nr}/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        r = self._aendern(nr, zahlung={"ziel_tage": "21"})                               # Vorkasse wieder weg
        self.assertEqual(self._detail(nr)["vorkasse_cent"], 0)
        self.assertFalse(self._aendern(nr, positionen=[])["ok"])                         # mindestens eine Position
        self.assertEqual(self.w.kunden_store.bh.pruefe_kette(), [])

    def test_b1_nach_dem_versand_gesperrt(self):
        nr = self._auftrag()
        self._senden(nr)
        sp = self._detail(nr)["sperre"]
        self.assertEqual(sp["art"], "versendet")
        r = self._aendern(nr, positionen=NEU_POS)
        self.assertFalse(r["ok"])
        self.assertIn("Versendet", r["hinweis"])
        self.assertTrue(self._aendern(nr, notiz="Dreh am Freitag")["ok"])               # Leistung/Notiz bleiben frei

    def test_b1_rechnung_oder_postings_sperren_fest(self):
        nr = self._auftrag()
        e = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()
        self.assertTrue(self._aendern(nr, titel="nur Entwurf da")["ok"])               # Rechnungs-Entwurf sperrt nicht
        r = self.c.post(f"/api/finanzen/rechnungen/{e['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        sp = self._detail(nr)["sperre"]
        self.assertEqual(sp["art"], "fest")
        self.assertIn(r["nummer"], sp["grund"])
        self.assertFalse(self._aendern(nr, titel="zu spaet")["ok"])
        self.assertFalse(self.c.post(f"/api/crm/auftraege/{nr}/entsperren", json={"grund": "x"}).json()["ok"])
        nr2 = self._auftrag()
        self.w.kunden_store.bh.erfassen("posting_veroeffentlicht", {"id": f"{nr2}-P1-1", "datum": "2026-10-01"})
        self.assertEqual(self._detail(nr2)["sperre"]["art"], "fest")

    def test_b2_bearbeiten_mit_begruendung(self):
        nr = self._auftrag()
        self.assertFalse(self.c.post(f"/api/crm/auftraege/{nr}/entsperren", json={"grund": "x"}).json()["ok"])   # nicht gesperrt
        self._senden(nr)
        self.assertFalse(self.c.post(f"/api/crm/auftraege/{nr}/entsperren", json={"grund": " "}).json()["ok"])   # Grund Pflicht
        r = self.c.post(f"/api/crm/auftraege/{nr}/entsperren", json={"grund": "Kunde will 3 statt 1 Reel"}).json()
        self.assertEqual((r["ok"], r["fassung"]), (True, 2))
        a = self._detail(nr)
        self.assertEqual((a["sperre"], a["fassung"]), ({}, 2))
        self.assertEqual(a["verlauf"][-1]["grund"], "Kunde will 3 statt 1 Reel")
        self.assertTrue(self._aendern(nr, positionen=NEU_POS)["ok"])
        v = self.c.get(f"/api/crm/auftraege/{nr}/versandvorschau").json()
        self.assertTrue(v["betreff"].endswith("(Version 2)"), v["betreff"])
        self._senden(nr)                                                                # erneut versendet -> wieder fest
        a = self._detail(nr)
        self.assertEqual((a["sperre"]["art"], len(a["pdfs"])), ("versendet", 2))      # beide Fassungen abgelegt
        self.assertFalse(self._aendern(nr, titel="ohne Grund")["ok"])
        self.assertEqual(self.w.kunden_store.bh.pruefe_kette(), [])


class TestAngebotBearbeitbar(ApiBasis):
    def test_b2_versendetes_angebot_neue_fassung(self):
        nr = self._neu()
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}/entsperren", json={"grund": "x"}).json()["ok"])   # Entwurf
        self.assertTrue(self.c.post(f"/api/crm/angebote/{nr}/versendet").json()["ok"])
        alt = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual(len(alt["versendet_termine"]), 2)
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}", json={"angebot": {"titel": "x"}}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/angebote/{nr}/entsperren", json={"grund": ""}).json()["ok"])
        with __import__("unittest").mock.patch("orchestrator.core.erinnerungen.jetzt") as j:   # Termine liegen in der Zukunft
            j.return_value = __import__("datetime").datetime(2026, 1, 1)
            r = self.c.post(f"/api/crm/angebote/{nr}/entsperren", json={"grund": "Preis nachverhandelt"}).json()
        self.assertEqual((r["ok"], r["fassung"]), (True, 2), r)
        self.assertEqual(sorted(self.g.geloeschte_termine), sorted(t["id"] for t in alt["versendet_termine"]))
        a = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual((a["status"], a["fassung"], a["entsperrt"]["grund"]), ("entwurf", 2, "Preis nachverhandelt"))
        self.assertTrue(self.c.post(f"/api/crm/angebote/{nr}", json={"angebot": {"titel": "Herbst V2"}}).json()["ok"])
        v = self.c.get(f"/api/crm/angebote/{nr}/versandvorschau").json()
        self.assertIn("(Version 2)", v["betreff"])
        self.assertTrue(self.c.post(f"/api/crm/angebote/{nr}/versendet").json()["ok"])
        a = self.c.get(f"/api/crm/angebote/{nr}").json()["angebot"]
        self.assertEqual((a["status"], a["entsperrt"], len(a["pdfs"])), ("versendet", None, 2))   # beide Fassungen abgelegt
        self.assertTrue(self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "angenommen"}).json()["ok"])
        r = self.c.post(f"/api/crm/angebote/{nr}/entsperren", json={"grund": "zu spaet"}).json()
        self.assertFalse(r["ok"])
        self.assertIn("Auftrag", r["hinweis"])
        self.assertEqual(self.w.kunden_store.bh.pruefe_kette(), [])



if __name__ == "__main__":
    import unittest
    unittest.main()
