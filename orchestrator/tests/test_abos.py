"""KUNDEN_FINANZEN Etappe 15 (CEO 2026-09-29): wiederkehrende Zahlungen / Abos mit Turnus; Buchen auf Klick oder -- per
Haken -- automatisch; Mail-Beleg verhindert Doppelbuchung; Kuendigung meldet sich rechtzeitig."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.abos import AboStore, faelligkeiten, lauf, monatlich_cent, offene, plus_monate
from orchestrator.core.buchhaltung import Buchhaltung, jetzt
from orchestrator.core.eigenbelege import EigenbelegStore
from orchestrator.core.eingangsbelege import EingangStore
from orchestrator.core.kunden import KundenStore
from orchestrator.core.todos import finanzcheck
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import _pdf

HEUTE = date(2026, 9, 29)


def _stores():
    bh = Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")
    ks = KundenStore(bh)
    apple = ks.firma_anlegen({"name": "Apple Distribution International Ltd.", "typ": "lieferant"})["nummer"]
    return bh, ks, AboStore(bh), apple


def _abo(**x):
    return {"bezeichnung": "iCloud+ 2 TB", "firma": "L-00001", "betrag": "9,99", "kategorie": "software",
            "turnus": "monatlich", "start": "2026-07-22"} | x


class TestTurnus(unittest.TestCase):
    def test_1_faelligkeiten(self):
        self.assertEqual(faelligkeiten({"start": "2026-01-31", "turnus": "monatlich"}, date(2026, 4, 30)),
                         ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"])          # kein Wandern auf den 28.
        self.assertEqual(plus_monate(date(2028, 1, 31), 1, 31), date(2028, 2, 29))          # Schaltjahr
        self.assertEqual(faelligkeiten({"start": "2026-05-23", "turnus": "jaehrlich"}, date(2028, 1, 1)),
                         ["2026-05-23", "2027-05-23"])
        self.assertEqual(faelligkeiten({"start": "2026-09-01", "turnus": "woechentlich"}, date(2026, 9, 20)),
                         ["2026-09-01", "2026-09-08", "2026-09-15"])
        self.assertEqual(faelligkeiten({"start": "2026-01-15", "turnus": "vierteljaehrlich", "ende": "2026-08-01"},
                                       date(2027, 1, 1)), ["2026-01-15", "2026-04-15", "2026-07-15"])
        self.assertEqual(monatlich_cent({"betrag_cent": 9900, "turnus": "jaehrlich"}), 825)
        self.assertEqual(monatlich_cent({"betrag_cent": 1000, "turnus": "woechentlich"}), 4333)

    def test_2_pruefung(self):
        bh, ks, st, apple = _stores()
        for falsch, grund in ((_abo(firma=""), "Stammdaten"), (_abo(kategorie="anlage"), "Kategorie"),
                              (_abo(turnus="taeglich"), "Turnus"), (_abo(betrag="0"), "groesser"),
                              (_abo(ende="2026-01-01"), "vor der ersten")):
            with self.assertRaises(ValueError, msg=grund) as cm:
                st.anlegen(falsch, ks)
            self.assertIn(grund, str(cm.exception))
        self.assertEqual(st.anlegen(_abo(), ks)["nummer"], "ABO-00001")
        self.assertEqual(st.get("ABO-00001")["firma"], apple)


class TestFaelligkeiten(unittest.TestCase):
    def test_1_buchen_auf_klick(self):
        bh, ks, st, apple = _stores()
        nr = st.anlegen(_abo(vertragsnummer="MNMTH0S0KW"), ks)["nummer"]
        with mock.patch("orchestrator.core.eigenbelege.jetzt", return_value=jetzt().replace(year=2026, month=9, day=29)), \
                mock.patch("orchestrator.core.abos.jetzt", return_value=jetzt().replace(year=2026, month=9, day=29)):
            self.assertEqual([o["faellig"] for o in offene(bh.eintraege(), HEUTE)], ["2026-07-22", "2026-08-22", "2026-09-22"])
            r = st.buchen(nr, "2026-08-22", ks)
            eb = EigenbelegStore(bh).get(r["eigenbeleg"])
            self.assertEqual((eb["datum"], eb["betrag_cent"], eb["firma"], eb["kategorie"]), ("2026-08-22", 999, apple, "software"))
            self.assertIn("ABO-00001", eb["referenz"])
            with self.assertRaises(ValueError):
                st.buchen(nr, "2026-08-22", ks)                                           # nie doppelt
            with self.assertRaises(ValueError):
                st.buchen(nr, "2026-08-23", ks)                                           # keine Faelligkeit
            with self.assertRaises(ValueError):
                st.buchen(nr, "2026-10-22", ks)                                           # Zukunft
            st.ueberspringen(nr, "2026-07-22", "vor dem Abo schon anders gebucht")
            with self.assertRaises(ValueError):
                st.ueberspringen(nr, "2026-07-22", "nochmal")                             # jede Faelligkeit genau einmal
            self.assertEqual([o["faellig"] for o in offene(bh.eintraege(), HEUTE)], ["2026-09-22"])
            st.aendern(nr, {"betrag": "12,99"}, ks)                                       # gilt fuer kuenftige
            self.assertEqual(EigenbelegStore(bh).get(st.buchen(nr, "2026-09-22", ks)["eigenbeleg"])["betrag_cent"], 1299)
            st.beenden(nr, "2026-10-01", "gekuendigt")
            self.assertEqual(offene(bh.eintraege(), date(2027, 3, 1)), [])               # nach Ende nichts mehr
        self.assertEqual(bh.pruefe_kette(), [])

    def test_2_lauf_auto_und_mailbeleg(self):
        bh, ks, st, apple = _stores()
        auto = st.anlegen(_abo(bezeichnung="Kontoführung", start="2026-09-01", betrag="5", kategorie="buero",
                               auto_buchen=True), ks)["nummer"]
        klick = st.anlegen(_abo(bezeichnung="AppleCare", start="2026-09-18", betrag="4,49", kategorie="sonstiges"),
                           ks)["nummer"]                                           # vor iCloud: Betrag muss passen
        mail = st.anlegen(_abo(start="2026-09-22", beleg_per_mail=True, auto_buchen=True), ks)["nummer"]
        mail2 = st.anlegen(_abo(bezeichnung="Dropbox", start="2026-09-10", betrag="30", beleg_per_mail=True,
                                auto_buchen=True), ks)["nummer"]                   # Haken wirkt bei Mail-Beleg nicht
        eb = EingangStore(bh)
        b = eb.aufnehmen(_pdf("Apple iCloud " * 10), "i.pdf")["nummer"]
        eb.buchen(b, {"lieferant": "Apple", "lieferant_firma": apple, "rechnungsdatum": "2026-09-21", "betrag": "10,49",
                      "kategorie": "software"})
        meldungen = []
        with mock.patch("orchestrator.core.eigenbelege.jetzt", return_value=jetzt().replace(year=2026, month=9, day=29)), \
                mock.patch("orchestrator.core.abos.jetzt", return_value=jetzt().replace(year=2026, month=9, day=29)):
            erg = lauf(bh, ks, heute=HEUTE, notify=lambda t, **k: meldungen.append(t))
        self.assertEqual(len(erg["gebucht"]), 1)
        self.assertIn("Kontoführung", erg["gebucht"][0])
        self.assertEqual(st.get(auto)["erledigt"]["2026-09-01"]["wie"], "gebucht")
        e = st.get(mail)["erledigt"]["2026-09-22"]
        self.assertEqual((e["wie"], e["beleg"]), ("beleg", b))                             # Mail-Beleg = erfuellt
        self.assertNotIn("2026-09-18", st.get(klick)["erledigt"])                        # AppleCare: Betrag passt nicht
        self.assertEqual(st.get(mail2)["erledigt"], {})                                  # wartet auf den Beleg
        self.assertEqual(len(meldungen), 1)
        self.assertEqual(lauf(bh, ks, heute=HEUTE), {"erfuellt": [], "gebucht": [], "fehler": []})   # idempotent

    def test_3_todos(self):
        bh, ks, st, apple = _stores()
        st.anlegen(_abo(start="2026-09-18", bezeichnung="AppleCare"), ks)
        st.anlegen(_abo(start="2026-09-25", bezeichnung="Canva", beleg_per_mail=True), ks)
        st.anlegen(_abo(start="2026-06-01", bezeichnung="Vertrag", turnus="jaehrlich", ende="2027-06-01",
                        kuendigungsfrist_tage=240), ks)
        t = {x["id"].split(":")[0]: x for x in finanzcheck(bh.eintraege(), HEUTE)}
        self.assertIn("AppleCare fällig am 18.09.2026", t["abo"]["titel"])
        self.assertEqual(t["abo"]["erledigen"], {"pfad": "/api/finanzen/abos/ABO-00001/buchen", "schluessel": "2026-09-18",
                                                 "label": "✓ Buchen"})
        self.assertNotIn("abo-beleg", t)                                                   # Canva: Karenz 10 Tage
        self.assertIn("kündigen bis 04.10.2026", t["abo-kuendigung"]["titel"])
        t = {x["id"].split(":")[0]: x for x in finanzcheck(bh.eintraege(), date(2026, 10, 6))}
        self.assertIn("Canva: Beleg zum 25.09. fehlt", t["abo-beleg"]["titel"])


class TestAboApi(ApiBasis):
    def test_ablauf(self):
        ks = self.w.kunden_store
        l = ks.firma_anlegen({"name": "Canva Pty Ltd", "typ": "lieferant"})["nummer"]
        r = self.c.post("/api/finanzen/abos", json={"abo": _abo(firma=l, bezeichnung="Canva Pro", betrag="12",
                                                                   start=(jetzt().date() - timedelta(days=1)).isoformat())}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.get("/api/finanzen/abos").json()
        self.assertEqual((d["summe"]["ausgaben_monat_cent"], d["abos"][0]["firma_nr"], len(d["abos"][0]["offen"])), (1200, l, 1))
        faellig = d["abos"][0]["offen"][0]
        r = self.c.post(f"/api/finanzen/abos/{r['nummer']}/buchen", json={"schluessel": faellig}).json()   # wie das To-do
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["eigenbeleg"].startswith("EB-"))
        self.assertEqual(self.c.get("/api/finanzen/abos").json()["abos"][0]["offen"], [])
        self.assertFalse(self.c.post("/api/finanzen/abos", json={"abo": _abo(firma="L-09999")}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
