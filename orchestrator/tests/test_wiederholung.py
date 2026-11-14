"""MONETARISIERUNG M6: wiederkehrende To-dos, Vorlagen fuer Datenlieferungen, Teilzeit-Antrag aus dem Plan.
Gate: Erledigen erzeugt genau einen naechsten Termin (Gegenprobe: kein zweiter), Erinnerung mit gleichem Abstand."""
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from orchestrator.core.aufgaben import AufgabenStore, erinnerungen_senden, naechster_termin
from orchestrator.core.daten_rhythmus import erster_termin, teilzeit_erinnern, teilzeit_vorlauf, vorlagen, vorlagen_anlegen
from orchestrator.tests.test_angebote import ApiBasis

JETZT = datetime(2026, 11, 14, 10, 0)


def _store():
    return AufgabenStore(Path(tempfile.mkdtemp()) / "todos.jsonl")


class TestTermine(unittest.TestCase):
    def test_1_naechster_termin(self):
        self.assertEqual(naechster_termin("2026-11-16", "woechentlich", "2026-11-14"), "2026-11-23")
        self.assertEqual(naechster_termin("2026-01-31", "monatlich", "2026-01-31", 31), "2026-02-28")   # Monatsende
        self.assertEqual(naechster_termin("2026-02-28", "monatlich", "2026-02-28", 31), "2026-03-31")   # Tag bleibt 31
        self.assertEqual(naechster_termin("2026-10-05", "quartalsweise", "2026-10-05"), "2027-01-05")
        self.assertEqual(naechster_termin("2026-11-14", "jaehrlich", "2026-11-14"), "2027-11-14")
        self.assertEqual(naechster_termin("2026-09-05", "monatlich", "2026-11-14"), "2026-12-05")      # verpasste ueberspringen
        with self.assertRaises(ValueError):
            naechster_termin("2026-11-14", "taeglich", "2026-11-14")

    def test_2_vorlagen_ersttermin(self):
        heute = date(2026, 11, 14)                                                    # Samstag
        self.assertEqual(erster_termin("reichweite", heute), date(2026, 11, 16))       # Montag
        self.assertEqual(erster_termin("reichweite", date(2026, 11, 16)), date(2026, 11, 16))
        self.assertEqual(erster_termin("abrechnungen", heute), date(2026, 12, 5))
        self.assertEqual(erster_termin("stunden", date(2026, 11, 2)), date(2026, 11, 3))
        self.assertEqual(erster_termin("quartal", heute), date(2027, 1, 5))


class TestWiederholung(unittest.TestCase):
    def setUp(self):
        self.st = _store()
        self.p = mock.patch("orchestrator.core.aufgaben.jetzt_lokal", return_value=JETZT)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_1_erledigen_legt_genau_einen_nachfolger_an(self):
        a = self.st.anlegen("Abrechnungen erfassen", faellig="2026-11-05", erinnerung="2026-11-04T18:30", notiz="PDFs",
                            wiederholung="monatlich")
        x = self.st.erledigen(a["id"])
        n = self.st.get(x["naechste"])
        self.assertEqual((n["faellig"], n["erinnerung"], n["notiz"], n["serie"], n["status"]),
                         ("2026-12-05", "2026-12-04T18:30", "PDFs", a["id"], "offen"))             # gleicher Abstand
        self.st.erledigen(a["id"], False)                                              # wieder oeffnen ...
        self.st.erledigen(a["id"])                                                     # ... und erneut erledigen
        offen = [t for g in self.st.liste().values() for t in g if t["titel"] == "Abrechnungen erfassen" and t["status"] == "offen"]
        self.assertEqual(len(offen), 1)                                                # Gegenprobe: kein zweiter Nachfolger
        n2 = self.st.get(self.st.erledigen(n["id"])["naechste"])                        # Serie laeuft weiter
        self.assertEqual((n2["faellig"], n2["serie"]), ("2027-01-05", a["id"]))

    def test_2_ohne_wiederholung_kein_nachfolger(self):
        a = self.st.anlegen("Einmalig", faellig="2026-11-20")
        self.assertEqual(self.st.erledigen(a["id"])["naechste"], "")
        self.assertEqual(sum(len(g) for g in self.st.liste().values()), 1)

    def test_3_pruefungen(self):
        with self.assertRaisesRegex(ValueError, "Fälligkeitsdatum"):
            self.st.anlegen("x", wiederholung="woechentlich")
        with self.assertRaisesRegex(ValueError, "Wiederholung"):
            self.st.anlegen("x", faellig="2026-11-20", wiederholung="stuendlich")
        a = self.st.anlegen("y", faellig="2026-11-20")
        b = self.st.aendern(a["id"], {"wiederholung": "woechentlich"})
        self.assertEqual((b["wiederholung"], b["serie"], b["tag"]), ("woechentlich", a["id"], 20))
        with self.assertRaisesRegex(ValueError, "Fälligkeitsdatum"):
            self.st.aendern(a["id"], {"faellig": ""})

    def test_4_telegram_erinnerung_des_nachfolgers(self):
        a = self.st.anlegen("Reichweiten", faellig="2026-11-09", wiederholung="woechentlich")
        n = self.st.get(self.st.erledigen(a["id"])["naechste"])
        self.assertEqual(n["faellig"], "2026-11-16")
        gesendet = []
        ids = erinnerungen_senden(self.st, lambda t, k: gesendet.append(t) or True, jetzt=datetime(2026, 11, 16, 9, 0))
        self.assertEqual(ids, [n["id"]])
        self.assertIn("🔁 wöchentlich", gesendet[0])


class TestVorlagenUndTeilzeit(unittest.TestCase):
    def test_1_vorlagen_einmal(self):
        st = _store()
        with mock.patch("orchestrator.core.aufgaben.jetzt_lokal", return_value=JETZT):
            neu = vorlagen_anlegen(st, ["reichweite", "stunden"], date(2026, 11, 14))
            self.assertEqual([(a["faellig"], a["wiederholung"]) for a in neu], [("2026-11-16", "woechentlich"),
                                                                              ("2026-12-03", "monatlich")])
            self.assertEqual(vorlagen_anlegen(st, ["reichweite"], date(2026, 11, 14)), [])     # laeuft schon
            self.assertEqual({v["id"]: v["aktiv"] for v in vorlagen(st)},
                             {"reichweite": True, "abrechnungen": False, "stunden": True, "quartal": False})
            with self.assertRaises(ValueError):
                vorlagen_anlegen(st, ["gibtsnicht"], date(2026, 11, 14))

    def test_2_teilzeit_ab_haelfte_und_nur_einmal(self):
        def ausw(ist, name="Brückenjob Nils"):
            return {"gates": [{"code": "G3", "name": name, "erreicht": False,
                               "regeln_stand": [{"regel": {"art": "in_folge", "monate": 6}, "erfuellt": False, "ist": ist}]}]}
        self.assertEqual(teilzeit_vorlauf(ausw(2)), [])                                 # Gegenprobe: zu frueh
        self.assertEqual(teilzeit_vorlauf(ausw(3, "Vollzeit Nils")), [])                # kein Brueckenjob-Gate
        self.assertEqual(teilzeit_vorlauf(ausw(3))[0]["stand"], 3)
        st = _store()
        with mock.patch("orchestrator.core.aufgaben.jetzt_lokal", return_value=JETZT):
            a = teilzeit_erinnern(st, ausw(3), date(2026, 11, 14))
            self.assertEqual((len(a), a[0]["faellig"], a[0]["quelle"]), (1, "2026-11-21", "Plan:G3:teilzeit"))
            self.assertEqual(teilzeit_erinnern(st, ausw(4), date(2026, 11, 15)), [])     # nur einmal je Gate
            st.erledigen(a[0]["id"])
            self.assertEqual(teilzeit_erinnern(st, ausw(5), date(2026, 11, 16)), [])     # auch nicht nach Erledigen


class TestApi(ApiBasis):
    def test_1_anlegen_erledigen_vorlagen(self):
        st = _store()
        with mock.patch.object(self.w, "_aufgaben", return_value=st):
            r = self.c.post("/api/aufgaben", json={"titel": "Stunden eintragen", "faellig": "2030-01-03",
                                                   "wiederholung": "monatlich"}).json()
            self.assertTrue(r["ok"], r)
            self.assertFalse(self.c.post("/api/aufgaben", json={"titel": "x", "wiederholung": "monatlich"}).json()["ok"])
            x = self.c.post(f"/api/aufgaben/{r['aufgabe']['id']}/erledigen", json={}).json()["aufgabe"]
            self.assertEqual(st.get(x["naechste"])["faellig"], "2030-02-03")
            v = self.c.get("/api/aufgaben/vorlagen").json()["vorlagen"]
            self.assertEqual(len(v), 4)
            r = self.c.post("/api/aufgaben/vorlagen", json={"ids": ["quartal"]}).json()
            self.assertTrue(r["ok"], r)
            self.assertEqual(len(r["angelegt"]), 1)

    def test_2_oberflaeche(self):
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        for teil in ('id="${id}"', "auf-wdh", 'data-act="auf-vorlagen"', "/api/aufgaben/vorlagen", "d.teilzeit"):
            self.assertIn(teil, js)


if __name__ == "__main__":
    unittest.main()
