"""KUNDEN_FINANZEN Etappe 23: Provisionsmodell (Affiliate) -- im Angebot „5 EUR je verkauftem Artikel“ bzw. „10 % vom
Umsatz“ ohne Phantasiesumme, nach der Collab abrechnen -> Rechnung mit echtem Euro-Betrag; Rabatt/Zuschlag wirken nicht
auf die Provision; Festschreiben erst nach Abrechnung."""
import io
import re
import unittest

from pypdf import PdfReader

from orchestrator.core.angebote import _positionen, provision_text, summen
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.katalog import pruefe
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import _stores
from orchestrator.tests.test_rechnungen import FD

TEXT = lambda pdf: re.sub(r"\s+", " ", " ".join(s.extract_text() for s in PdfReader(io.BytesIO(pdf)).pages))  # noqa: E731
REEL = {"beschreibung": "Reel", "menge": "1", "einzelpreis": "1000"}
AFF_ST = {"beschreibung": "Affiliate-Partnerschaft", "provision": {"art": "stueck", "wert": "5"}}
AFF_PR = {"beschreibung": "Affiliate-Partnerschaft", "provision": {"art": "prozent", "wert": "10"}}


class TestRechnen(unittest.TestCase):
    def test_1_modell_ohne_und_mit_abrechnung(self):
        p = _positionen([AFF_ST])[0]
        self.assertEqual((p["einzelpreis_cent"], p["provision"]), (0, {"art": "stueck", "satz_cent": 500}))
        self.assertEqual(provision_text(p["provision"]), "5,00 € je verkauftem Artikel")
        a = _positionen([AFF_ST | {"provision": {"art": "stueck", "wert": "5", "abrechnung": "120"}}])[0]
        self.assertEqual((a["menge"], a["einzelpreis_cent"], a["provision"]["stueck"]), ("120", 500, 120))
        b = _positionen([AFF_PR | {"provision": {"art": "prozent", "wert": "10", "abrechnung": "3.400,05"}}])[0]
        self.assertEqual((b["einzelpreis_cent"], b["provision"]["basis_cent"]), (34001, 340005))   # kaufmaennisch
        self.assertEqual(_positionen([p])[0], p)                                                   # gespeichert -> gleich
        for falsch in ({"art": "stueck", "wert": "0"}, {"art": "prozent", "wert": "150"}, {"art": "pauschal", "wert": 1},
                       {"art": "stueck", "wert": "5", "abrechnung": "-1"}):
            with self.assertRaises(ValueError, msg=falsch):
                _positionen([{"beschreibung": "x", "provision": falsch}])

    def test_2_summen_rabatt_nicht_auf_provision(self):
        pos = _positionen([REEL, AFF_ST | {"provision": {"art": "stueck", "wert": "5", "abrechnung": "100"}}])
        s = summen(pos, [{"name": "Exklusiv", "prozent": 20}], 10)
        self.assertEqual((s["formate_cent"], s["provision_cent"], s["gesamt_cent"]), (100000, 50000, 108000 + 50000))
        offen = summen(_positionen([REEL, AFF_ST]), [], 0)
        self.assertEqual((offen["gesamt_cent"], offen["provision_offen"]), (100000, True))

    def test_3_katalog_standardmodell(self):
        k = {"gruppen": [{"name": "Partnerschaften", "items": [{"id": "affiliate", "name": "Affiliate", "preis_cent": 0,
                                                                "provision_art": "prozent", "provision_wert": "10"}]}]}
        self.assertEqual(pruefe(k)["gruppen"][0]["items"][0]["provision_wert"], 10.0)
        with self.assertRaises(ValueError):
            pruefe({"gruppen": [{"name": "P", "items": [{"id": "a", "name": "A", "preis_cent": 0, "provision_art": "stueck",
                                                          "provision_wert": 0}]}]})


class TestHanserautisch(unittest.TestCase):
    def test_1_zeile_und_summe(self):
        from orchestrator.core.angebote import AngebotStore
        from orchestrator.core.katalog import Katalog
        bh, ks, _, k, ap = _stores()
        st = AngebotStore(bh, ks, Katalog(bh))
        an = st.anlegen({"firma": k, "positionen": [REEL, AFF_PR]})["nummer"]
        t = TEXT(st.pdf(an, FD))
        self.assertIn("10 % vom vermittelten Umsatz nach Abrechnung", t)                 # Zeile: Modell + Betragstext
        self.assertIn("Provision nach Abrechnung", t)                                     # Summenblock

    def test_2_preisliste(self):
        from orchestrator.core.angebote import preisliste_pdf
        from orchestrator.core.katalog import Katalog
        bh = _stores()[0]
        kat = Katalog(bh).laden()
        kat["gruppen"][0]["items"].append({"id": "affiliate", "name": "Affiliate-Partnerschaft", "basis": "", "hinweis": "",
                                           "preis_cent": 0, "einheit": "", "aktiv": True, "provision_art": "stueck",
                                           "provision_wert": 500})
        t = TEXT(preisliste_pdf(kat, FD, logo=None))
        self.assertIn("Affiliate-Partnerschaft 5,00 € / Stk.", t)                          # nie „0,00 €“


class TestAblauf(unittest.TestCase):
    def test_1_angebot_auftrag_abrechnung(self):
        bh, ks, st, k, ap = _stores()
        an = st.anlegen({"firma": k, "positionen": [REEL, AFF_ST], "rabatt_prozent": 10})["nummer"]
        a = st.angebot(an)
        self.assertEqual(a["summe_cent"], 90000)                                     # Provision nicht in der Summe
        t = TEXT(st.pdf(an, FD))
        self.assertIn("5,00 € je verkauftem Artikel", t)
        self.assertIn("nach Abrechnung", t)
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        ab = AuftragBuch(bh, ks, st)
        nr = ab.aus_angebot(an, leistung_von=jetzt().date().isoformat())["nummer"]
        self.assertIn("je verkauftem Artikel", TEXT(ab.pdf(nr, FD)))
        rs = RechnungStore(bh, ks)
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"]
        with self.assertRaisesRegex(ValueError, "Provision noch nicht abgerechnet"):
            rs.festschreiben(eid, FD)
        pos = rs.get(eid)["positionen"]
        pos[1] = {k: v for k, v in pos[1].items() if k != "gesamt_cent"} | {"provision": pos[1]["provision"] | {"abrechnung": "37"}}
        rs.entwurf_aendern(eid, {"positionen": [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in pos]})
        r = rs.get(rs.festschreiben(eid, FD)["nummer"])
        self.assertEqual(r["summe_cent"], 90000 + 18500)                             # 37 x 5 EUR, ohne Rabatt
        self.assertIn("37 verkaufte Artikel × 5,00 €", TEXT(rs._pdf(r, FD)))
        self.assertEqual(rs.umsatz(jetzt().year), 108500)


if __name__ == "__main__":
    unittest.main()
