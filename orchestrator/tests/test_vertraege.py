"""VERTRAGSWERK V1/V2: Vorlagen mit Versionen und Pruefstatus, nur gepruefte Version „in Kraft“, Vergleich,
erste Entwuerfe (Claude Code) nur als Entwurf, Rechte (nur CEO aendert)."""
import unittest

from orchestrator.core.vertraege import ARTEN, VertragStore, platzhalter
from orchestrator.core.vertrag_entwuerfe import ENTWUERFE
from orchestrator.tests.test_angebote import ApiBasis, _stores


class TestVertraege(unittest.TestCase):
    def setUp(self):
        self.bh = _stores()[0]
        self.vs = VertragStore(self.bh)

    def test_1_entwuerfe_nur_als_entwurf(self):
        self.assertEqual(set(ENTWUERFE), set(ARTEN))
        self.assertEqual(sorted(self.vs.entwuerfe_laden()), sorted(ARTEN))
        self.assertEqual(self.vs.entwuerfe_laden(), [])                              # kein zweites Mal
        for x in self.vs.liste():
            self.assertEqual((x["aktuell"], x["status"], x["in_kraft"]), (1, "entwurf", None))
        self.assertIsNone(self.vs.in_kraft("agb"))                                  # ungeprueft darf nicht raus
        k = self.vs.vorlage("kooperation")["versionen"][0]
        self.assertTrue({"Kunde", "Leistungen", "Verguetung", "Nutzungsrechte", "Freigabe"} <= set(k["platzhalter"]))
        self.assertEqual(k["quelle"], "Entwurf Claude Code (ungeprüft)")

    def test_2_pruefen_versionen_vergleich(self):
        self.vs.entwuerfe_laden()
        with self.assertRaisesRegex(ValueError, "geprueft"):
            self.vs.status_setzen("agb", 1, "geprueft", datum="2026-10-20")
        self.vs.status_setzen("agb", 1, "geprueft", pruefer="RAin Muster", datum="2026-10-20")
        self.assertEqual(self.vs.in_kraft("agb")["version"], 1)
        par = self.vs.vorlage("agb")["versionen"][0]["paragraphen"]
        neu = [dict(p) for p in par]
        neu[0]["text"] += " Ergänzung."
        neu.append({"titel": "§ 15 Neu", "text": "Text {Kunde}"})
        self.vs.version_anlegen("agb", titel="AGB", paragraphen=neu)
        self.assertEqual(self.vs.in_kraft("agb")["version"], 1)                     # v2 ist Entwurf -> v1 gilt weiter
        v = {x["titel"]: x["art"] for x in self.vs.vergleich("agb", 1, 2)}
        self.assertEqual((v["§ 1 Geltungsbereich"], v["§ 15 Neu"], v["§ 2 Angebot und Vertragsschluss"]), ("geaendert", "neu", "gleich"))
        self.vs.status_setzen("agb", 2, "geprueft", pruefer="RAin Muster", datum="2026-11-01")
        self.assertEqual(self.vs.in_kraft("agb")["version"], 2)
        self.vs.status_setzen("agb", 2, "ausser_kraft", notiz="zurueckgezogen")
        self.assertEqual(self.vs.in_kraft("agb")["version"], 1)
        with self.assertRaisesRegex(ValueError, "Titel und Text"):
            self.vs.version_anlegen("agb", titel="x", paragraphen=[{"titel": "", "text": "x"}])

    def test_3_platzhalter(self):
        self.assertEqual(platzhalter([{"titel": "§ 1 {Kunde}", "text": "{Kunde} zahlt {Verguetung}."}]), ["Kunde", "Verguetung"])


class TestApi(ApiBasis):
    def test_a1_endpunkte(self):
        self.assertTrue(self.c.post("/api/crm/vertraege/alle/entwuerfe", json={}).json()["ok"])
        l = self.c.get("/api/crm/vertraege").json()["vorlagen"]
        self.assertEqual(len(l), 4)
        d = self.c.get("/api/crm/vertraege/agb").json()["vorlage"]
        self.assertEqual(d["versionen"][0]["status"], "entwurf")
        r = self.c.post("/api/crm/vertraege/agb/status", json={"version": 1, "status": "geprueft", "pruefer": "RAin X",
                                                                "datum": "2026-10-20"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.c.get("/api/crm/vertraege").json()["vorlagen"][0]["in_kraft"], 1)


if __name__ == "__main__":
    unittest.main()
