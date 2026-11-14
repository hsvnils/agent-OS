"""MONETARISIERUNG M2: Plan, Gates mit Kontinuitaet, Ampel, Kooperationen Soll/Ist. Gate laut Roadmap: Tests rechnen die
Kontinuitaet nach (5 gute Monate + 1 schlechter = nicht erreicht). Alle Zahlen sind ausgedacht (oeffentliches Repo)."""
import unittest
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eigenbelege import EigenbelegStore
from orchestrator.core.plan import Plan, ampel, formel, pruefe_plan, regel_pruefen
from orchestrator.core.saeulen import Saeulen
from orchestrator.tests.test_angebote import ApiBasis, _stores

J = jetzt().year - 1
HEUTE = jetzt().replace(year=J, month=7, day=15)       # abgeschlossen: Jan-Jun J
VAR = {"E_nils": 550000, "L_nils": 95000, "FIX": 40000}


def _reihe(gewinne):
    return [{"monat": f"{J}-{i + 1:02d}", "gewinn_cent": g, "einnahmen_cent": g, "koop_anzahl": 1, "koop_cent": g,
             "db": {"S1": g}} for i, g in enumerate(gewinne)]


def _plan(**g2):
    return {"personen": {"nils": {"netto_cent": "3.000", "E_cent": "5.500", "L_cent": "950"}},
            "annahmen": {"koop_schnitt_cent": "1.200", "fixkosten_cent": "400", "stunden_je_koop": "8"},
            "gates": [{"code": "G1", "name": "Validierung", "kriterien": [{"text": "Steuerberater gefunden"}],
                       "regeln": [{"was": "koop_anzahl", "art": "in_folge", "monate": 3, "schwelle": "1"}]},
                      {"code": "G2", "name": "Nebenerwerb", "fruehestens": f"{J + 1}-06", "koop_anzahl": 2,
                       "ziele": {"S1": "2.400", "S2a": "150"},
                       "regeln": [{"was": "gewinn", "art": "in_folge", "monate": 6, "schwelle": "2*L_nils"}]} | g2]}


class TestRegeln(unittest.TestCase):
    def test_1_formel(self):
        self.assertEqual(formel("2*L_nils+1000", VAR), 2 * 95000 + 100000)
        self.assertEqual(formel("E_nils", VAR), 550000)
        self.assertEqual(formel("1", VAR, geld=False), 1)
        for falsch in ("", "L_x", "2**L_nils", "import os", "E_nils-1"):
            with self.assertRaises(ValueError, msg=falsch):
                formel(falsch, VAR)

    def test_2_in_folge_gegenprobe(self):
        r = {"was": "gewinn", "art": "in_folge", "monate": 6, "x": 0, "schwelle": "1000"}
        self.assertTrue(regel_pruefen(r, _reihe([100000] * 6), VAR)["erfuellt"])
        fuenf_plus_eins = regel_pruefen(r, _reihe([100000] * 5 + [99999]), VAR)
        self.assertEqual((fuenf_plus_eins["erfuellt"], fuenf_plus_eins["ist"]), (False, 0))
        eins_dann_fuenf = regel_pruefen(r, _reihe([99999] + [100000] * 5), VAR)
        self.assertEqual((eins_dann_fuenf["erfuellt"], eins_dann_fuenf["ist"]), (False, 5))
        self.assertFalse(regel_pruefen(r, _reihe([100000] * 5), VAR)["erfuellt"])      # zu wenige Monate

    def test_3_schnitt_und_x_von_y(self):
        s = {"was": "gewinn", "art": "schnitt", "monate": 6, "x": 0, "schwelle": "1000"}
        self.assertTrue(regel_pruefen(s, _reihe([50000, 150000] * 3), VAR)["erfuellt"])
        self.assertFalse(regel_pruefen(s, _reihe([50000, 149999] * 3), VAR)["erfuellt"])
        x = {"was": "S1", "art": "x_von_y", "monate": 6, "x": 4, "schwelle": "750"}
        self.assertTrue(regel_pruefen(x, _reihe([75000] * 4 + [0, 0]), VAR)["erfuellt"])
        self.assertFalse(regel_pruefen(x, _reihe([75000] * 3 + [0, 0, 0]), VAR)["erfuellt"])

    def test_4_ampel(self):
        self.assertEqual(ampel(1000, [950]), "gruen")
        self.assertEqual(ampel(1000, [500, 850]), "gelb")
        self.assertEqual(ampel(1000, [850, 900]), "rot")                               # zwei Monate gelb
        self.assertEqual(ampel(1000, [1000, 790]), "rot")
        self.assertEqual(ampel(1000, []), "rot")

    def test_5_plan_pruefen(self):
        p = pruefe_plan(_plan())
        self.assertEqual((p["personen"]["nils"]["L_cent"], p["annahmen"]["koop_schnitt_cent"]), (95000, 120000))
        self.assertEqual(p["gates"][1]["ziele"], {"S1": 240000, "S2a": 15000})
        self.assertEqual(pruefe_plan(p), p)                                             # gespeicherte Fassung stabil
        for kaputt in ({"gates": [{"code": "G1", "name": ""}]},
                       {"gates": [{"code": "G1", "name": "a"}, {"code": "G1", "name": "b"}]},
                       {"gates": [{"code": "G1", "name": "a", "regeln": [{"was": "gewinn", "art": "in_folge", "monate": 13, "schwelle": "1"}]}]},
                       {"gates": [{"code": "G1", "name": "a", "regeln": [{"was": "gewinn", "art": "in_folge", "monate": 3, "schwelle": "3*Q"}]}]},
                       {"gates": [{"code": "G1", "name": "a", "ziele": {"S9": "5"}}]},
                       {"annahmen": {"fixkosten_cent": "viel"}}):
            with self.assertRaises(ValueError, msg=kaputt):
                pruefe_plan(kaputt)


class TestAuswertung(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, *_ = _stores()
        eig, s = EigenbelegStore(self.bh), Saeulen(self.bh, self.ks)
        for m in range(1, 7):                                                 # Jan-Jun je eine Kooperation 1.200 EUR
            nr = eig.anlegen({"art": "einnahme", "datum": f"{J}-{m:02d}-10", "betrag": "1.200", "text": "Kooperation",
                              "gegenpartei": "Marke"})["nummer"]
            s.zuordnen([{"bezug": nr, "saeule": "S1"}])
        eig.anlegen({"art": "einnahme", "datum": f"{J}-07-02", "betrag": "999", "text": "laufender Monat",
                     "gegenpartei": "Marke"})                                   # Juli zaehlt noch nicht
        self.p = Plan(self.bh, self.ks)

    def _aus(self):
        with mock.patch("orchestrator.core.plan.jetzt", return_value=HEUTE):
            return self.p.auswertung()

    def test_1_ohne_plan(self):
        a = self._aus()
        self.assertEqual((a["hat_plan"], a["gates"], a["ziel_gate"], a["bis_monat"]), (False, [], "", f"{J}-06"))

    def test_2_gates_ampel_koop(self):
        self.assertTrue(self.p.speichern(_plan(), von="test")["geaendert"])
        self.assertFalse(self.p.speichern(_plan())["geaendert"])                     # unveraendert -> kein Eintrag
        a = self._aus()
        g1, g2 = a["gates"]
        self.assertTrue(g1["regeln_stand"][0]["erfuellt"])
        self.assertFalse(g1["erreicht"])                                             # Kriterium noch offen
        self.assertEqual(a["ziel_gate"], "G1")
        self.p.kriterium("G1", 0, True, von="test")
        a = self._aus()
        g1, g2 = a["gates"]
        self.assertTrue(g1["erreicht"])
        self.assertEqual(a["ziel_gate"], "G2")
        self.assertEqual(g2["regeln_stand"][0]["schwelle"], 190000)                    # 2 x L
        self.assertFalse(g2["regeln_stand"][0]["erfuellt"])                            # 1.200 < 1.900
        self.assertEqual((g2["koop_noetig"], g2["stunden_koop"], g2["ziel_gewinn_cent"]), (2, 16.0, 255000 - 40000))
        amp = {x["code"]: x for x in a["ampeln"]}
        self.assertEqual((amp["S1"]["letzter_cent"], amp["S1"]["quote"], amp["S1"]["ampel"]), (120000, 50, "rot"))
        self.assertEqual(amp["S2a"]["letzter_cent"], 0)
        self.assertEqual(a["koop"]["soll_anzahl"], 2)
        self.assertEqual([m["anzahl"] for m in a["koop"]["monate"]][-6:], [1] * 6)
        self.assertEqual(a["monate"][-1]["gewinn_cent"], 120000)
        self.assertEqual(len(a["verlauf"]), 2)
        # Schwelle haengt am Plan: L kleiner -> Gate G2 erreicht
        neu = self.p.aktuell()
        neu["personen"]["nils"]["L_cent"] = 60000
        self.p.speichern(neu, notiz="L gesenkt")
        self.assertEqual(self._aus()["gates"][1]["erreicht"], True)

    def test_3_falscher_plan_schreibt_nichts(self):
        n = len(self.bh.eintraege())
        with self.assertRaises(ValueError):
            self.p.speichern({"gates": [{"code": "G1", "name": "x", "regeln": [{"was": "gewinn", "art": "schnitt",
                                                                               "monate": 3, "schwelle": "kaputt+"}]}]})
        with self.assertRaises(ValueError):
            self.p.kriterium("G9", 0, True)
        self.assertEqual(len(self.bh.eintraege()), n)


class TestApi(ApiBasis):
    def test_1_plan_api(self):
        d = self.c.get("/api/finanzen/plan").json()
        self.assertFalse(d["hat_plan"])
        self.assertIn("S2a", d["auswahl"]["ziel_codes"])
        self.assertFalse(self.c.post("/api/finanzen/plan", json={"plan": {"gates": [{"code": "G1"}]}}).json()["ok"])
        r = self.c.post("/api/finanzen/plan", json={"plan": _plan(), "notiz": "erste Fassung"}).json()
        self.assertTrue(r["ok"] and r["geaendert"])
        self.assertTrue(self.c.post("/api/finanzen/plan/kriterium", json={"gate": "G1", "index": 0, "erledigt": True}).json()["ok"])
        d = self.c.get("/api/finanzen/plan").json()
        self.assertTrue(d["plan"]["gates"][0]["kriterien"][0]["erledigt"])
        self.assertEqual(d["verlauf"][-1]["notiz"], "erste Fassung")

    def test_2_oberflaeche(self):
        from pathlib import Path
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        self.assertIn('["plan", "Plan"]', js)
        self.assertIn("/api/finanzen/plan", js)


if __name__ == "__main__":
    unittest.main()
