"""KUNDEN_FINANZEN Etappe 27: Plattform-Auszahlungen mit Erzielt-Zeitraum (Facebook). Reine Information -- die EUeR
bleibt beim Zufluss. Beispieltext nachgebaut (keine echten IDs/Adressen im oeffentlichen Repo)."""
import unittest

from orchestrator.core.finanzen import Finanzen
from orchestrator.core.kunden import KundenStore
from orchestrator.core.plattform import _monatsanteile, auswertung, posten_aus_text, remittance_lesen
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import _store

META = """Meta Platforms Ireland Ltd.
Merrion Road
Dublin 4
REMITTANCE
Payee: Beispiel Creator
The following payment has been remitted to your Bank account:
Payment Number: 11112222333344445
Payment Date: 25-Sep-2026
Payment Currency: USD
Payment Amount: 282.37
Remittance Details
Payout Reference # Payout Period Product - Object Name - Object ID Remittance
90000000000000001 01-Jun-2026 -> 30-Jun-2026 Content - (Beispielseite - 100000000000001) 23.29
90000000000000002 01-Aug-2026 -> 31-Aug-2026 Content - (Beispielseite - 100000000000001) 188.15
90000000000000003 01-Jul-2026 -> 31-Jul-2026 Content - (Beispielseite - 100000000000001) 69.96
90000000000000004 01-Jul-2026 -> 31-Jul-2026 Content - (Beispielseite - 100000000000001) 0.97
Total: $282.37
"""


def _auszahlung(st, text=META, eur="246,38", datum="2026-09-29", nr="11112222333344445"):
    n = st.aufnehmen(text.encode(), f"Payment_{nr}.pdf", text=text)["nummer"]
    st.buchen(n, {"lieferant": "Meta Platforms Ireland Ltd.", "rechnungsnummer": nr, "rechnungsdatum": datum,
                  "betrag": eur, "art": "einnahme", "kategorie": "umsatz", "leistung": "Auszahlung"})
    st.bezahlt(n, datum)
    return n


class TestLesen(unittest.TestCase):
    def test_1_remittance(self):
        r = remittance_lesen(META)
        self.assertEqual((r["zahlungs_id"], r["datum"], r["waehrung"], r["betrag_cent"], r["stimmig"]),
                         ("11112222333344445", "2026-09-25", "USD", 28237, True))
        self.assertEqual([(p["von"], p["bis"], p["betrag_cent"]) for p in r["posten"]],
                         [("2026-06-01", "2026-06-30", 2329), ("2026-07-01", "2026-07-31", 6996),
                          ("2026-07-01", "2026-07-31", 97), ("2026-08-01", "2026-08-31", 18815)])
        self.assertIsNone(remittance_lesen("Rechnung Canva 12,00 EUR"))
        self.assertFalse(remittance_lesen(META.replace("Payment Amount: 282.37", "Payment Amount: 282.64"))["stimmig"])

    def test_2_von_hand(self):
        p = posten_aus_text("01.12.2025-31.12.2025 47,29\n\n01.11.2025 - 30.11.2025 98,87 $ Content")
        self.assertEqual([(x["von"], x["betrag_cent"]) for x in p], [("2025-11-01", 9887), ("2025-12-01", 4729)])
        for falsch in ("", "November 98,87", "31.12.2025-01.12.2025 5,00", "01.12.2025-31.12.2025 0"):
            with self.assertRaises(ValueError, msg=falsch):
                posten_aus_text(falsch)

    def test_3_monatsanteile(self):
        a = _monatsanteile("2026-01-01", "2026-02-28", 59.0)          # 31 + 28 Tage
        self.assertAlmostEqual(a["2026-01"], 31.0)
        self.assertAlmostEqual(a["2026-02"], 28.0)
        self.assertEqual(list(_monatsanteile("2026-03-01", "2026-03-31", 1.0)), ["2026-03"])


class TestStore(unittest.TestCase):
    def test_1_pdf_auswertung_und_eur_unveraendert(self):
        st = _store()
        n = _auszahlung(st)
        self.assertIn("erzielt 01.06.2026–31.08.2026", st.get(n)["vorschlag"]["leistung"])
        d = auswertung(list(st._falte(st.bh.eintraege()).values()), 2026)
        a = d["auszahlungen"][0]
        self.assertEqual((a["fremd_cent"], a["eur_cent"], a["von"], a["bis"], a["quelle"]),
                         (28237, 24638, "2026-06-01", "2026-08-31", "pdf"))
        self.assertEqual({m["monat"]: m["fremd_cent"] for m in d["erzielt"]}, {"2026-06": 2329, "2026-07": 7093, "2026-08": 18815})
        self.assertAlmostEqual(sum(m["eur_cent"] for m in d["erzielt"]), 24638, delta=2)    # Euro-Anteile = Bankeingang
        self.assertEqual(auswertung(list(st._falte(st.bh.eintraege()).values()), 2025)["auszahlungen"], [])

    def test_2_von_hand_januar_zufluss_2026(self):
        st = _store()
        f = Finanzen(st.bh, KundenStore(st.bh))
        n = st.aufnehmen(b"screenshot", "Auszahlung_Januar.png", text="Auszahlungsdetails 146,16 $")["nummer"]
        st.buchen(n, {"lieferant": "Meta Platforms Ireland Ltd.", "rechnungsnummer": "55556666777788889",
                      "rechnungsdatum": "2026-01-23", "betrag": "124,48", "art": "einnahme", "kategorie": "umsatz"})
        st.bezahlt(n, "2026-01-23")
        vorher = f.euer(2026)
        st.posten_setzen(n, "01.11.2025-30.11.2025 98,87\n01.12.2025-31.12.2025 47,29", zahlungs_id="55556666777788889")
        self.assertEqual(f.euer(2026), vorher)                        # Zeitraeume aendern keine Buchung
        d = auswertung(list(st._falte(st.bh.eintraege()).values()), 2026)
        self.assertEqual(d["auszahlungen"][0]["quelle"], "hand")
        self.assertEqual([m["monat"] for m in d["erzielt"]], ["2025-11", "2025-12"])   # erzielt 2025, zugeflossen 2026
        self.assertEqual(d["ausgezahlt_eur_cent"], 12448)

    def test_3_nur_einnahmen(self):
        st = _store()
        n = st.aufnehmen(b"x", "rechnung.pdf", text="Rechnung Canva 12,00 EUR")["nummer"]
        st.buchen(n, {"lieferant": "Canva", "rechnungsdatum": "2026-09-01", "betrag": "12,00", "art": "ausgabe",
                      "kategorie": "software"})
        with self.assertRaisesRegex(ValueError, "nur bei Einnahmen"):
            st.posten_setzen(n, "01.09.2026-30.09.2026 12,00")


class TestApi(ApiBasis):
    def test_a1_endpunkte(self):
        st = self.w._eingang()
        n = _auszahlung(st)
        d = self.c.get("/api/finanzen/plattform?jahr=2026").json()
        self.assertEqual(d["ausgezahlt_fremd_cent"], 28237)
        b = self.c.get(f"/api/finanzen/belege/{n}").json()["beleg"]
        self.assertEqual(len(b["plattform"]["posten"]), 4)
        r = self.c.post(f"/api/finanzen/belege/{n}/posten", json={"zeilen": "01.06.2026-31.08.2026 282,37"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{n}").json()["beleg"]["plattform"]["quelle"], "hand")
        self.assertFalse(self.c.post(f"/api/finanzen/belege/{n}/posten", json={"zeilen": "Unsinn"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
