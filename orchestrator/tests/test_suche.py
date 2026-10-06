"""GLOBALE_SUCHE G1: eine Suche ueber alle Geschaeftsdaten -- Kategorien, Betraege, Daten, Umlaute, Rechte."""
import unittest
from unittest import mock

from orchestrator.core.suche import _woerter, norm, suchen
from orchestrator.tests.test_angebote import ApiBasis


class TestNorm(unittest.TestCase):
    def test_umlaute_und_woerter(self):
        self.assertEqual(norm("München Straße"), "muenchen strasse")
        self.assertEqual(norm("Muenchen"), "muenchen")
        self.assertEqual(_woerter("  Kiez   ALM 1.600 € "), ["kiez", "alm", "1.600"])


class TestSuche(ApiBasis):
    def setUp(self):
        super().setUp()
        bh = self.w.kunden_store.bh
        self.an = self._neu(titel="Herbstkampagne Kiez")
        bh.erfassen("eingang_angelegt", {"nummer": "ER-2026-0901", "dateiname": "amazon-puma.pdf"})
        bh.erfassen("eingang_gebucht", {"nummer": "ER-2026-0901", "felder": {"lieferant": "Amazon EU", "betrag_cent": 8995,
                                                                              "rechnungsdatum": "2026-10-03", "kategorie": "sonstiges",
                                                                              "rechnungsnummer": "DE-ABC-1"}})
        self.c.post("/api/contentplan", json={"datum": "2026-10-10", "titel": "Derby-Recap München", "format": "video"})

    def _gruppen(self, q, **kw):
        r = self.c.get("/api/suche", params={"q": q}, **kw).json()
        return {g["id"]: g for g in r["gruppen"]}, r

    def test_1_kategorien(self):
        g, r = self._gruppen("brand")
        self.assertIn("kunden", g)                                                # Firma „Brand X GmbH“
        self.assertIn("angebote", g)                                              # Angebot der Firma
        self.assertEqual(g["angebote"]["treffer"][0]["act"], "an-detail")
        g, _ = self._gruppen(self.an)                                             # Nummer exakt -> oben
        self.assertEqual((g["angebote"]["treffer"][0]["act_id"]), self.an)
        g, _ = self._gruppen("herbstkampagne")
        self.assertEqual(list(g), ["angebote"])

    def test_2_betrag_datum_umlaut(self):
        g, _ = self._gruppen("89,95")
        self.assertEqual([t["act_id"] for t in g["ausgaben"]["treffer"]], ["ER-2026-0901"])
        g, _ = self._gruppen("03.10.2026 amazon")
        self.assertIn("ausgaben", g)
        g, _ = self._gruppen("oktober 2026 amazon")
        self.assertIn("ausgaben", g)
        g, _ = self._gruppen("muenchen")                                          # Umlaut egal
        self.assertEqual(g["contentplan"]["treffer"][0]["act"], "cp-suche")
        g, _ = self._gruppen("münchen derby")
        self.assertIn("contentplan", g)
        g, r = self._gruppen("gibtsnichtxyz")
        self.assertEqual((g, r["gesamt"]), ({}, 0))
        self.assertEqual(self._gruppen("a")[1]["gruppen"], [])                    # zu kurz

    def test_3_rechte(self):
        with mock.patch.object(self.w, "erlaubte_apps", return_value=["home", "kunden", "angebote"]):
            g, _ = self._gruppen("amazon")
        self.assertNotIn("ausgaben", g)                                           # ohne Finanzen keine Belege
        with mock.patch.object(self.w, "erlaubte_apps", return_value=["home", "kunden", "angebote"]):
            g, _ = self._gruppen("brand")
        self.assertIn("angebote", g)

    def test_4_nichts_veraendert(self):
        vorher = len(self.w.kunden_store.bh.eintraege())
        suchen(self.w.kunden_store.bh, self.w.kunden_store, "brand")
        self.assertEqual(len(self.w.kunden_store.bh.eintraege()), vorher)


if __name__ == "__main__":
    unittest.main()
