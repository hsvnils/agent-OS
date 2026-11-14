"""TEILRECHNUNG (CEO 2026-11-14): Rechnung mit einer Position „spaeter abrechnen am“ -> Teilrechnung ueber den Rest,
die spaetere Position steht ohne Betrag mit Hinweis auf dem PDF; spaeter die Folgerechnung nur ueber die offenen
Positionen. Gegenproben: keine Doppelabrechnung, Storno-Reihenfolge, Datum in der Vergangenheit, Vorkasse."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.aufgaben import AufgabenStore
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.belegverfolgung import kette
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_provision import TEXT
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()
SPAETER = (HEUTE + timedelta(days=40)).isoformat()
CONTENT = {"beschreibung": "Content-Angebot siehe Mail", "menge": "1", "einzelpreis": "800"}
AFF = {"beschreibung": "Affiliate-Partnerschaft", "provision": {"art": "stueck", "wert": "5"}}


def _ohne_gesamt(pos):
    return [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in pos]


class Basis:
    def setUp(self):
        self.bh, self.ks, st, k, ap = _stores()
        an = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": [CONTENT, AFF]})["nummer"]
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        self.ab = AuftragBuch(self.bh, self.ks, st)
        self.auftrag = self.ab.aus_angebot(an, leistung_von=HEUTE.isoformat())["nummer"]
        self.rs = RechnungStore(self.bh, self.ks)

    def _teil(self, am=SPAETER):
        eid = self.rs.entwurf_aus_auftrag(self.ab.auftrag(self.auftrag))["entwurf_id"]
        pos = _ohne_gesamt(self.rs.get(eid)["positionen"])
        pos[1]["spaeter_am"] = am
        self.rs.entwurf_aendern(eid, {"positionen": pos})
        return eid


class TestTeilrechnung(Basis, unittest.TestCase):
    def test_1_teilrechnung_summe_und_pdf(self):
        eid = self._teil()
        e = self.rs.get(eid)
        self.assertEqual((e["summe_cent"], e["summen"]["spaeter"][0]["am"]), (80000, SPAETER))
        nr = self.rs.festschreiben(eid, FD)["nummer"]
        r = self.rs.get(nr)
        self.assertEqual((r["summe_cent"], r["teil"]["abrechnung_am"], r["rest_offen"], r["folge"]), (80000, SPAETER, True, ""))
        t = TEXT(self.rs._pdf(r, FD))
        d = f"{SPAETER[8:10]}.{SPAETER[5:7]}.{SPAETER[:4]}"
        self.assertIn(f"Wird am {d} gesondert abgerechnet (5,00 € je verkauftem Artikel).", t)   # CEO-Wortlaut
        self.assertIn("Teilrechnung", t)
        self.assertEqual(self.rs.umsatz(HEUTE.year), 80000)

    def test_1b_festpreis_spaeter_zaehlt_nicht(self):
        from orchestrator.core.angebote import _positionen, summen
        pos = _positionen([CONTENT, {"beschreibung": "Zweites Reel", "menge": "1", "einzelpreis": "300", "spaeter_am": SPAETER}])
        self.assertEqual(summen(pos, [], 0)["gesamt_cent"], 80000)                          # 300 EUR folgen spaeter
        self.assertEqual(summen(pos[:1], [], 0)["gesamt_cent"], 80000)

    def test_2_gegenproben_festschreiben(self):
        eid = self.rs.entwurf_aus_auftrag(self.ab.auftrag(self.auftrag))["entwurf_id"]
        with self.assertRaisesRegex(ValueError, "Provision noch nicht abgerechnet"):        # ohne „spaeter“ wie bisher
            self.rs.festschreiben(eid, FD)
        self.rs.entwurf_verwerfen(eid)
        eid = self._teil(am=(HEUTE - timedelta(days=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "Vergangenheit"):
            self.rs.festschreiben(eid, FD)

    def test_3_folgerechnung_genau_einmal(self):
        nr = self.rs.festschreiben(self._teil(), FD)["nummer"]
        with self.assertRaisesRegex(ValueError, "Teilrechnung"):                            # keine zweite normale Rechnung
            self.rs.entwurf_aus_auftrag(self.ab.auftrag(self.auftrag))
        f = self.rs.folgerechnung(nr)["entwurf_id"]
        self.assertTrue(self.rs.folgerechnung(nr)["vorhanden"])                             # ein Entwurf, nicht zwei
        e = self.rs.get(f)
        self.assertEqual([p["beschreibung"] for p in e["positionen"]], ["Affiliate-Partnerschaft"])
        self.assertEqual((e["folge_zu"], e["leistung_bis"]), (nr, SPAETER))
        self.assertIn(nr, e["einleitung"])
        with self.assertRaisesRegex(ValueError, "Provision noch nicht abgerechnet"):        # erst Zahlen eintragen
            self.rs.festschreiben(f, FD)
        pos = _ohne_gesamt(e["positionen"])
        pos[0]["provision"] = pos[0]["provision"] | {"abrechnung": "12"}
        self.rs.entwurf_aendern(f, {"positionen": pos})
        f_nr = self.rs.festschreiben(f, FD)["nummer"]
        fr, t = self.rs.get(f_nr), self.rs.get(nr)
        self.assertEqual((fr["summe_cent"], t["folge"], t["rest_offen"]), (6000, f_nr, False))
        self.assertRegex(TEXT(self.rs._pdf(fr, FD)), f"Zu Teilrechnung:? {nr}")
        self.assertEqual(self.rs.umsatz(HEUTE.year), 86000)
        with self.assertRaisesRegex(ValueError, "schon mit"):                               # keine Doppelabrechnung
            self.rs.folgerechnung(nr)
        with self.assertRaisesRegex(ValueError, "erst diese stornieren"):                   # Storno-Reihenfolge
            self.rs.stornieren(nr, FD, grund="Test")
        kanten = {(k["von"], k["nach"], k["text"]) for k in kette(self.bh.eintraege(), nr)["kanten"]}
        self.assertIn((nr, f_nr, "Rest abgerechnet in"), kanten)
        # Storno der Folgerechnung gibt den Rest wieder frei
        self.rs.stornieren(f_nr, FD, grund="falsche Stueckzahl")
        self.assertTrue(self.rs.get(nr)["rest_offen"])
        self.assertTrue(self.rs.folgerechnung(nr)["entwurf_id"])

    def test_4_storno_der_teilrechnung(self):
        nr = self.rs.festschreiben(self._teil(), FD)["nummer"]
        s = self.rs.get(self.rs.stornieren(nr, FD, grund="Test", korrektur=True)["storno"])
        self.assertEqual((s["summe_cent"], len(s["positionen"])), (-80000, 1))              # Hinweis nicht im Storno
        o = self.rs.get(nr)
        self.assertFalse(o["rest_offen"])
        with self.assertRaisesRegex(ValueError, "storniert"):
            self.rs.folgerechnung(nr)
        k = [e for e in self.rs.uebersicht()["entwuerfe"] if e["auftrag"] == self.auftrag]
        self.assertEqual(len(k), 1)                                                         # Korrektur-Entwurf
        self.assertEqual(self.rs.get(k[0]["entwurf_id"])["positionen"][1]["spaeter_am"], SPAETER)


class TestApi(ApiBasis):
    def test_1_todo_und_folge(self):
        import json
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")
        store = AufgabenStore(Path(tempfile.mkdtemp()) / "todos.jsonl")
        with mock.patch.object(self.w, "_aufgaben", return_value=store):
            e = self.c.post("/api/finanzen/rechnungen", json={"rechnung": {
                "firma": self.k, "ansprechpartner": self.ap, "leistung_von": HEUTE.isoformat(),
                "positionen": [CONTENT, AFF | {"spaeter_am": SPAETER}]}}).json()
            r = self.c.post(f"/api/finanzen/rechnungen/{e['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
            self.assertTrue(r["ok"], r)
            todo = [a for g in store.liste().values() if isinstance(g, list) for a in g]
            self.assertEqual(len(todo), 1)
            self.assertEqual((todo[0]["faellig"], todo[0]["titel"][:14]), (SPAETER, "Rest abrechnen"))
            u = self.c.get("/api/finanzen/uebersicht").json()["pipeline"]["reste"]
            self.assertEqual([x["nummer"] for x in u], [r["nummer"]])
            f = self.c.post(f"/api/finanzen/rechnungen/{r['nummer']}/folgerechnung", json={}).json()
            self.assertTrue(f["ok"], f)
            pos = _ohne_gesamt(self.c.get(f"/api/finanzen/rechnungen/{f['entwurf_id']}").json()["rechnung"]["positionen"])
            pos[0]["provision"] = pos[0]["provision"] | {"abrechnung": "3"}
            self.assertTrue(self.c.post(f"/api/finanzen/rechnungen/{f['entwurf_id']}", json={"rechnung": {"positionen": pos}}).json()["ok"])
            r2 = self.c.post(f"/api/finanzen/rechnungen/{f['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
            self.assertTrue(r2["ok"], r2)
            self.assertEqual(store.get(todo[0]["id"])["status"], "erledigt")                 # To-do abgehakt
            self.assertEqual(self.c.get("/api/finanzen/uebersicht").json()["pipeline"]["reste"], [])

    def test_2_oberflaeche(self):
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        for teil in ("an-p-spaeter", 'data-act="re-folge"', "/folgerechnung", "Rest später abrechnen"):
            self.assertIn(teil, js)


if __name__ == "__main__":
    unittest.main()
