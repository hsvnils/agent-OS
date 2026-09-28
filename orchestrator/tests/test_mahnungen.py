"""KUNDEN_FINANZEN Etappe 10: Mahnwesen -- Verzugszinsen taggenau ab Faelligkeit (Basiszins je Halbjahr + 9/5 Punkte),
40 EUR Pauschale (Unternehmer) bzw. 2,50 EUR je Mahnung (Verbraucher), Stufen 1-3, Folgemahnung nur nach ✅,
Zahlung mit Zinsen/Kosten, EUeR Zeile 12/13."""
import json
import unittest
from datetime import date, timedelta
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.mahnungen import MahnStore, folgemahnung_senden, verzugszinsen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.governance.google_workspace import MockGoogleWorkspace
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD, _entwurf


class TestZinsen(unittest.TestCase):
    def test_1_von_hand(self):
        z = verzugszinsen(100000, [], "2026-06-20", "2026-07-10", 9.0)
        # 10 Tage x 10,27 % + 10 Tage x 10,52 % auf 1.000 EUR / 365 = 2,8137 + 2,8822 = 5,6959 -> 5,70 EUR
        self.assertEqual((z["zinsen_cent"], z["tage"]), (570, 20))
        self.assertEqual([(a["satz"], a["tage"]) for a in z["abschnitte"]], [(10.27, 10), (10.52, 10)])
        # Teilzahlung von 400 EUR am 01.07. mindert ab dann den Betrag
        z2 = verzugszinsen(100000, [("2026-07-01", 40000)], "2026-06-20", "2026-07-10", 9.0)
        self.assertEqual(z2["abschnitte"][-1]["offen_cent"], 60000)
        self.assertEqual(z2["zinsen_cent"], round(100000 * 10.27 / 36500 * 10 + 60000 * 10.52 / 36500 * 10))
        self.assertEqual(verzugszinsen(100000, [], "2026-06-20", "2026-06-20", 9.0)["zinsen_cent"], 0)

    def test_2_unbekannter_basiszins_rechnet_nicht(self):
        with self.assertRaises(ValueError):
            verzugszinsen(100000, [], "2026-12-20", "2027-01-05", 9.0)


class TestMahnwesen(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, _, self.k, self.ap = _stores()
        self.rs, self.ms = RechnungStore(self.bh, self.ks), MahnStore(self.bh, self.ks)
        vor = jetzt() - timedelta(days=40)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=vor):
            self.re = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]
        self.faellig = self.rs.get(self.re)["faellig_am"]

    def test_1_stufen_und_betraege(self):
        v = self.ms.berechnen(self.re)
        self.assertEqual((v["stufe"], v["gebuehr_cent"], v["offen_cent"], v["verbraucher"]), (1, 4000, 102000, False))
        self.assertEqual(v["summe_cent"], 102000 + v["zinsen_cent"] + 4000)
        self.assertGreater(v["zinsen_cent"], 0)
        m1 = self.ms.erstellen(self.re, FD, frist_tage=7)
        self.assertEqual(m1["nummer"], f"MA-{jetzt().year}-0001")
        voll = self.ms.get(m1["nummer"])
        self.assertTrue((self.bh.dir / voll["belege"][0]["pfad"]).read_bytes().startswith(b"%PDF"))
        with self.assertRaises(ValueError):
            self.ms.berechnen(self.re)                                                   # erst senden
        self.ms.versendet(m1["nummer"], {"an": "x@y.de"})
        self.assertEqual(self.ms.faellige_folgemahnungen(), [])                           # Frist laeuft noch
        spaeter = jetzt().date() + timedelta(days=8)
        f = self.ms.faellige_folgemahnungen(spaeter)
        self.assertEqual([(x["rechnung"], x["stufe"]) for x in f], [(self.re, 2)])
        self.assertEqual(self.ms.berechnen(self.re)["gebuehr_cent"], 4000)              # Pauschale nur einmal
        self.ms.aussetzen(self.re, 2, "CEO: nein")
        self.assertEqual(self.ms.faellige_folgemahnungen(spaeter), [])                   # fragt nicht mehr
        m2 = self.ms.erstellen(self.re, FD); self.ms.versendet(m2["nummer"], {"an": "x"})  # manuell weiter moeglich
        m3 = self.ms.erstellen(self.re, FD); self.ms.versendet(m3["nummer"], {"an": "x"})
        self.assertEqual(self.ms.get(m3["nummer"])["stufe"], 3)
        with self.assertRaises(ValueError):
            self.ms.berechnen(self.re)                                                   # nach der letzten: Inkasso
        self.assertEqual(self.ms.faellige_folgemahnungen(spaeter + timedelta(days=30)), [])   # Stufe 3 -> keine 4.

    def test_2_verbraucher(self):
        self.ks.firma_aendern(self.k, {"verbraucher": "ja"})
        v = self.ms.berechnen(self.re)
        self.assertEqual((v["verbraucher"], v["gebuehr_cent"]), (True, 250))
        self.assertTrue(all(a["satz"] < 7 for a in v["zins_abschnitte"]))                  # 5 statt 9 Punkte
        m = self.ms.erstellen(self.re, FD); self.ms.versendet(m["nummer"], {"an": "x"})
        self.assertEqual(self.ms.berechnen(self.re)["gebuehr_cent"], 500)                # 2 x 2,50

    def test_3_nicht_mahnbar(self):
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt()):
            neu = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]
        with self.assertRaises(ValueError):
            self.ms.berechnen(neu)                                                       # noch nicht faellig
        self.rs.bezahlt(self.re, datum="")
        with self.assertRaises(ValueError):
            self.ms.berechnen(self.re)                                                   # bezahlt

    def test_4_zahlung_mit_zinsen_und_euer(self):
        with self.assertRaises(ValueError):
            self.rs.bezahlt(self.re, datum="", nebenforderung="10")                       # ohne Mahnung nicht
        m = self.ms.erstellen(self.re, FD); self.ms.versendet(m["nummer"], {"an": "x"})
        r = self.rs.bezahlt(self.re, datum="", nebenforderung="45,80")
        self.assertEqual((r["rest_cent"], r["nebenforderung_cent"]), (0, 4580))
        self.assertEqual(self.rs.get(self.re)["status"], "bezahlt")
        self.assertEqual(self.ms.faellige_folgemahnungen(jetzt().date() + timedelta(days=30)), [])   # bezahlt -> Schluss
        f = Finanzen(self.bh, self.ks)
        eu = f.euer(jetzt().year)
        self.assertEqual(eu["einnahmen_cent"], 102000 + 4580)
        self.assertEqual({p["kategorie"]: p["betrag_cent"] for p in eu["einnahmen"]}, {"umsatz": 102000, "nebenforderung": 4580})
        from orchestrator.core.jahresabschluss import euer_zeilen
        z = {(x["zeile"], x["kz"]): x["betrag_cent"] for x in euer_zeilen(f, jetzt().year)["zeilen"] if x["art"] == "einnahme"}
        self.assertEqual(z, {("12", "111"): 106580, ("13", "119"): 4580})                # 12 = alles, 13 nachrichtlich
        self.assertEqual(self.rs.umsatz(jetzt().year), 102000)                          # Zinsen zaehlen nicht zu § 19

    def test_5_folgemahnung_per_telegram_und_todos(self):
        ids = lambda: {t["id"]: t for t in geschaefts_todos(self.bh, self.ks)}
        self.assertIn("1. Mahnung erstellen", ids()[f"re-ueber:{self.re}"]["detail"])
        m = self.ms.erstellen(self.re, FD)
        self.assertIn("senden", ids()[f"re-ueber:{self.re}"]["titel"])
        self.ms.versendet(m["nummer"], {"an": "x"})
        self.assertIn("läuft", ids()[f"re-ueber:{self.re}"]["titel"])
        g = MockGoogleWorkspace()
        with self.assertRaises(ValueError):                                               # Stufe passt nicht
            folgemahnung_senden(self.bh, self.ks, g, self.re, 3, FD, von="t")
        r = folgemahnung_senden(self.bh, self.ks, g, self.re, 2, FD, von="Telegram:CEO")
        self.assertEqual(r["an"], "rechnung@brandx.de")
        self.assertEqual(g.gesendet[-1]["anhaenge"][0][0], f"Mahnung_{r['nummer']}.pdf")
        self.assertTrue(self.ms.get(r["nummer"])["versendet_am"])


class TestMahnungApi(ApiBasis):
    def test_a1_ablauf(self):
        self.w.kunden_store.bh.dir.joinpath("firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")
        rs = RechnungStore(self.w.kunden_store.bh, self.w.kunden_store)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=30)):
            re = rs.festschreiben(_entwurf(rs, self.k, self.ap, zahlungsziel_tage=7), FD)["nummer"]
        d = self.c.get(f"/api/finanzen/rechnungen/{re}").json()
        self.assertEqual(d["naechste_mahnung"]["stufe"], 1)
        self.assertTrue(self.c.get(f"/api/finanzen/rechnungen/{re}/mahnung-vorschau?frist_tage=10").json()["ok"])
        self.assertFalse(self.c.post(f"/api/finanzen/rechnungen/{re}/mahnung", json={}).json()["ok"])     # ohne Bestaetigung
        m = self.c.post(f"/api/finanzen/rechnungen/{re}/mahnung", json={"frist_tage": 10, "bestaetigt": True}).json()
        self.assertTrue(m["ok"], m)
        self.assertEqual(self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}/pdf").status_code, 200)
        v = self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}/versandvorschau").json()
        self.assertIn("1. Mahnung", v["betreff"])
        s = self.c.post(f"/api/finanzen/mahnungen/{m['nummer']}/senden",
                        json={"an": v["an"], "betreff": v["betreff"], "text": v["text"], "bestaetigt": True}).json()
        self.assertTrue(s["ok"], s)
        self.assertFalse(self.c.post(f"/api/finanzen/mahnungen/{m['nummer']}/senden",
                                     json={"an": v["an"], "betreff": "b", "text": "t", "bestaetigt": True}).json()["ok"])  # doppelt
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{re}").json()["mahnungen"][0]["stufe"], 1)


if __name__ == "__main__":
    unittest.main()
