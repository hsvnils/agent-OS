"""VORSCHLAGSPAUSE_ANBIETER P3 (CEO 2026-10-07): Kosten je Anbieter -- Abo und Einzelkosten (Credits) strikt getrennt."""
import json
import unittest
from datetime import date
from unittest import mock

from orchestrator.core.abos import AboStore, offene
from orchestrator.core.anbieter_kosten import kosten
from orchestrator.governance.dienste_register import anbieter
from orchestrator.tests.test_abos import _stores

HEUTE = date(2026, 10, 7)


def _beleg(bh, nr, firma, datum, cent, lieferant="Anthropic, PBC"):
    bh.erfassen("eingang_angelegt", {"nummer": nr, "dateiname": f"{nr}.pdf"})
    bh.erfassen("eingang_gebucht", {"nummer": nr, "felder": {"lieferant": lieferant, "lieferant_firma": firma, "art": "ausgabe",
                                                             "betrag_cent": cent, "rechnungsdatum": datum, "kategorie": "software"}})


class TestAnbieterKosten(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, self.st, _ = _stores()
        self.ant = self.ks.firma_anlegen({"name": "Anthropic, PBC", "typ": "lieferant"})["nummer"]
        self.ai = self.ks.firma_anlegen({"name": "ALL-INKL.COM - Neue Medien Münnich", "typ": "lieferant"})["nummer"]

    def _k(self):
        return kosten(self.bh.eintraege(), {f["nummer"]: f["name"] for f in self.ks.firmen()}, anbieter({}), heute=HEUTE)

    def test_1_abo_und_credits_getrennt(self):
        self.st.anlegen({"bezeichnung": "Claude Pro", "firma": self.ant, "betrag": "21,42", "kategorie": "software",
                         "turnus": "monatlich", "start": "2026-05-05", "ende": "2026-06-24", "beleg_per_mail": True}, self.ks)
        self.st.anlegen({"bezeichnung": "Claude Max", "firma": self.ant, "betrag": "107,10", "kategorie": "software",
                         "turnus": "monatlich", "start": "2026-06-25", "beleg_per_mail": True}, self.ks)
        _beleg(self.bh, "ER-1", self.ant, "2026-06-03", 2049)            # Guthaben-Aufladung, 2 Tage vor der Pro-Faelligkeit
        _beleg(self.bh, "ER-2", self.ant, "2026-06-05", 2142)            # Claude Pro
        _beleg(self.bh, "ER-3", self.ant, "2026-05-05", 2142)
        _beleg(self.bh, "ER-4", self.ant, "2026-09-25", 10710)           # Claude Max
        _beleg(self.bh, "ER-5", self.ant, "2026-05-06", 595)             # extra usage
        zu = {o["faellig"]: o["beleg"] for o in offene(self.bh.eintraege(), HEUTE)}
        self.assertEqual(zu["2026-06-05"], "ER-2")                       # naechster Betrag gewinnt, nicht die Aufladung
        a = self._k()["anbieter"]["anthropic"]
        self.assertEqual((a["abo_monat_cent"], a["abo_jahr_cent"]), (10710, 2142 + 2142 + 10710))
        self.assertEqual((a["einzel_jahr_cent"], a["einzel_anzahl"]), (2049 + 595, 2))
        self.assertEqual([x["laeuft"] for x in a["abos"]], [False, True])

    def test_2_quartal_beendet_und_keine_gemeinsame_summe(self):
        self.st.anlegen({"bezeichnung": "all-inkl PrivatPlus", "firma": self.ai, "betrag": "23,13", "kategorie": "software",
                         "turnus": "vierteljaehrlich", "start": "2026-01-20", "beleg_per_mail": True}, self.ks)
        for nr, d in (("ER-7", "2026-01-21"), ("ER-8", "2026-04-20"), ("ER-9", "2026-07-20")):
            _beleg(self.bh, nr, self.ai, d, 2313, lieferant="ALL-INKL.COM")
        nr = self.st.anlegen({"bezeichnung": "Gekuendigt", "firma": self.ant, "betrag": "23,00", "kategorie": "software",
                              "turnus": "monatlich", "start": "2026-01-10", "ende": "2026-10-09"}, self.ks)["nummer"]
        k = self._k()
        self.assertEqual((k["anbieter"]["allinkl"]["abo_monat_cent"], k["anbieter"]["allinkl"]["abo_jahr_cent"]), (771, 6939))
        self.assertEqual(k["anbieter"]["allinkl"]["einzel_jahr_cent"], 0)
        self.assertEqual(k["anbieter"]["anthropic"]["abo_monat_cent"], 0)          # gekuendigt -> laeuft nicht mehr
        self.assertEqual(k["abos_monat_cent"], 771)
        self.assertFalse({"gesamt_cent", "summe_cent"} & set(json.dumps(k).split('"')))   # nie eine gemeinsame Summe
        self.assertTrue(nr)

    def test_3_endpunkt_nur_mit_finanzen(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        alt = webapp.kunden_store
        webapp.kunden_store = self.ks
        try:
            c = TestClient(webapp.app)
            with mock.patch.object(webapp, "_google_secrets", return_value={}):
                self.assertIn("kosten", c.get("/api/anbieter").json())
                with mock.patch.object(webapp, "hat_modul", side_effect=lambda u, m: m in ("administration",)):
                    self.assertNotIn("kosten", c.get("/api/anbieter").json())       # ohne Modul Finanzen keine Kosten
        finally:
            webapp.kunden_store = alt


if __name__ == "__main__":
    unittest.main()
