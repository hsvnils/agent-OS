"""KUNDEN_FINANZEN Etappe 19: Rechnungen von vor LUNA mit Originalnummer + Original-PDF uebernehmen (keine neue
RE-Nummer), Zahlung wie gewohnt, schon verschickte Mahnungen als erreichte Stufe erfassen."""
import base64
import json
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.mahnungen import MahnStore
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()
T = lambda n: (HEUTE - timedelta(days=n)).isoformat()   # noqa: E731
PDF = _pdf("Rechnung RG-11052026\nKiez Alm Gastro GmbH\nGesamt 4.000,00 EUR")


def _rs():
    bh, ks, st, k, ap = _stores()
    return bh, ks, RechnungStore(bh, ks), k


class TestAltrechnung(unittest.TestCase):
    def test_1_uebernehmen_ohne_neue_nummer(self):
        bh, ks, rs, k = _rs()
        r = rs.alt_erfassen({"firma": k, "nummer": "rg-11052026", "rechnungsdatum": T(140), "betrag": "4.000,00",
                             "leistung": "Social-Media-Werbung Saison 2025/26"}, PDF, "RG-11052026.pdf")
        x = rs.get("RG-11052026")
        self.assertEqual((r["nummer"], x["status"], x["summe_cent"], x["faellig_am"], x["alt"]),
                         ("RG-11052026", "offen", 400000, T(140), True))              # faellig = sofort
        self.assertEqual((bh.dir / x["belege"][0]["pfad"]).read_bytes(), PDF)        # Original unveraendert
        self.assertEqual([e for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "RE"], [])   # RE-Kreis unberuehrt
        self.assertEqual(rs.umsatz(int(T(140)[:4])), 400000)
        nr = rs.festschreiben(rs.entwurf_anlegen({"firma": k, "positionen": [{"beschreibung": "x", "menge": "1",
                                                  "einzelpreis": "10"}], "leistung_von": T(1)})["entwurf_id"], FD)["nummer"]
        self.assertTrue(nr.endswith("-0001"))                                          # erste LUNA-Nummer, lueckenlos
        self.assertEqual((bh.pruefe_kette(), bh.pruefe_belege()), ([], []))

    def test_2_pruefungen(self):
        bh, ks, rs, k = _rs()
        ok = {"firma": k, "nummer": "RG-18032026", "rechnungsdatum": T(10), "betrag": "385,12"}
        for falsch, pdf in (({**ok, "nummer": "RE-2026-0001"}, PDF), ({**ok, "nummer": "x"}, PDF), (ok, b"kein pdf"),
                            ({**ok, "firma": "K-99999"}, PDF), ({**ok, "rechnungsdatum": T(-1)}, PDF),
                            ({**ok, "betrag": "0"}, PDF), ({**ok, "faellig_am": T(20)}, PDF)):
            with self.assertRaises(ValueError, msg=falsch):
                rs.alt_erfassen(falsch, pdf)
        rs.alt_erfassen(ok, PDF)
        with self.assertRaisesRegex(ValueError, "gibt es schon"):
            rs.alt_erfassen(ok, PDF)

    def test_3_bezahlt_und_mahnstufen(self):
        bh, ks, rs, k = _rs()
        rs.alt_erfassen({"firma": k, "nummer": "RG-18032026", "rechnungsdatum": T(30), "betrag": "385,12"}, PDF)
        rs.bezahlt("RG-18032026", datum=T(30))
        self.assertEqual(rs.get("RG-18032026")["status"], "bezahlt")
        rs.alt_erfassen({"firma": k, "nummer": "RG-11052026", "rechnungsdatum": T(140), "betrag": "4000"}, PDF)
        ms = MahnStore(bh, ks)
        with self.assertRaises(ValueError):
            ms.alt_erfassen("RG-18032026", datum=T(5))                                   # bezahlt: nicht mahnbar
        m1 = ms.alt_erfassen("RG-11052026", datum=T(100), pdf=_pdf("1. Mahnung"))
        with self.assertRaises(ValueError):
            ms.alt_erfassen("RG-11052026", datum=T(120))                                 # vor der vorigen Mahnung
        ms.alt_erfassen("RG-11052026", datum=T(70))
        m3 = ms.alt_erfassen("RG-11052026", datum=T(30), summe="4.015,00")
        self.assertEqual((m1["nummer"], m1["stufe"], m3["nummer"], m3["stufe"]), ("RG-11052026-M1", 1, "RG-11052026-M3", 3))
        self.assertEqual(ms.get("RG-11052026-M3")["summe_cent"], 401500)
        with self.assertRaisesRegex(ValueError, "drei Mahnungen"):
            ms.alt_erfassen("RG-11052026", datum=T(1))
        with self.assertRaisesRegex(ValueError, "Mahnbescheid"):
            ms.berechnen("RG-11052026")                                                  # naechster Schritt: Anwalt
        self.assertEqual([e for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "MA"], [])
        from orchestrator.core.todos import geschaefts_todos
        t = [x for x in geschaefts_todos(bh, ks) if x["id"] == "re-ueber:RG-11052026"]
        self.assertIn("Mahnbescheid", t[0]["detail"])


class TestApi(ApiBasis):
    def setUp(self):
        super().setUp()
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")

    def test_a1_altrechnung_und_altmahnung(self):
        d = {"name": "RG.pdf", "daten": base64.b64encode(PDF).decode()}
        r = self.c.post("/api/finanzen/rechnungen/alt", json={"datei": d, "rechnung": {
            "firma": self.k, "nummer": "RG-11052026", "rechnungsdatum": T(140), "betrag": "4000"}}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.c.get("/api/finanzen/rechnungen/RG-11052026/pdf").content, PDF)
        m = self.c.post("/api/finanzen/rechnungen/RG-11052026/altmahnung", json={"datum": T(100), "datei": d}).json()
        self.assertTrue(m["ok"], m)
        self.assertEqual(self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}/pdf").status_code, 200)
        ohne = self.c.post("/api/finanzen/rechnungen/RG-11052026/altmahnung", json={"datum": T(70)}).json()
        self.assertEqual(self.c.get(f"/api/finanzen/mahnungen/{ohne['nummer']}/pdf").status_code, 404)
        u = self.c.get("/api/finanzen/rechnungen").json()
        self.assertEqual(u["rechnungen"][0]["nummer"], "RG-11052026")


if __name__ == "__main__":
    unittest.main()
