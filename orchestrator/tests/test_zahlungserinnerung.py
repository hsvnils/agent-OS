"""ZAHLUNGSERINNERUNG Z1 (CEO 2026-10-26): freundliche Erinnerung als Stufe 0 vor der 1. Mahnung -- Nummer ZE-, ohne Zinsen,
Pauschale oder Mahnkosten, Rechnung als zweiter Anhang, nur einmal und nur vor der 1. Mahnung; die 1. Mahnung nimmt Bezug
darauf, die Mahnstufen zaehlen weiter ab 1."""
import json
import unittest
from datetime import date, timedelta
from unittest import mock

from orchestrator.core.belegverfolgung import kette
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.mahnungen import MahnStore, mahnung_mail_text, senden
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.governance.google_workspace import MockGoogleWorkspace
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD, _entwurf


class TestZahlungserinnerung(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, _, self.k, self.ap = _stores()
        self.rs, self.ms = RechnungStore(self.bh, self.ks), MahnStore(self.bh, self.ks)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=40)):
            self.re = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]

    def test_1_ohne_kosten_eigene_nummer(self):
        v = self.ms.berechnen(self.re, erinnerung=True)
        self.assertEqual((v["stufe"], v["zinsen_cent"], v["gebuehr_cent"], v["summe_cent"]), (0, 0, 0, 102000))
        ze = self.ms.erstellen(self.re, FD, erinnerung=True)
        self.assertEqual(ze["nummer"], f"ZE-{jetzt().year}-0001")
        voll = self.ms.get(ze["nummer"])
        pdf = (self.bh.dir / voll["belege"][0]["pfad"]).read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(voll["belege"][0]["pfad"].endswith(f"Zahlungserinnerung_{ze['nummer']}.pdf"))
        t = self.ms.teile(voll)
        alles = t["einleitung"] + " ".join(t["hinweise"]) + " ".join(p["beschreibung"] for p in t["positionen"])
        self.assertIn("im täglichen Stress gehen manchmal Dinge unter", t["einleitung"])
        for verboten in ("Verzugszins", "Pauschale", "Mahnkosten", "§ 288"):
            self.assertNotIn(verboten, alles)
        self.assertEqual(len(t["positionen"]), 1)

    def test_2_nur_einmal_und_nur_vor_der_mahnung(self):
        ze = self.ms.erstellen(self.re, FD, erinnerung=True)
        with self.assertRaises(ValueError):
            self.ms.berechnen(self.re)                                          # erst senden
        self.ms.versendet(ze["nummer"], {"an": "x@y.de"})
        with self.assertRaises(ValueError):
            self.ms.berechnen(self.re, erinnerung=True)                         # nur einmal
        m1 = self.ms.berechnen(self.re)
        self.assertEqual((m1["stufe"], m1["gebuehr_cent"]), (1, 4000))          # Mahnung zaehlt ab 1, Pauschale normal
        self.assertEqual(m1["vorige"], [])
        self.assertEqual(m1["erinnerung"]["nummer"], ze["nummer"])
        m = self.ms.erstellen(self.re, FD)
        self.assertTrue(m["nummer"].startswith("MA-"))
        self.assertIn("Zahlungserinnerung vom", self.ms.teile(self.ms.get(m["nummer"]))["einleitung"])
        self.ms.versendet(m["nummer"], {"an": "x"})
        self.assertEqual(self.ms.berechnen(self.re)["stufe"], 2)
        self.assertEqual(self.ms.berechnen(self.re)["vorige"][0]["nummer"], m["nummer"])   # Erinnerung nicht als Mahnung
        # nach einer Mahnung keine Erinnerung mehr
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=40)):
            re2 = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]
        m2 = self.ms.erstellen(re2, FD); self.ms.versendet(m2["nummer"], {"an": "x"})
        with self.assertRaises(ValueError):
            self.ms.berechnen(re2, erinnerung=True)

    def test_3_folgevorschlag_todos_verfolgung(self):
        ids = lambda: {t["id"]: t for t in geschaefts_todos(self.bh, self.ks)}
        self.assertIn("Zahlungserinnerung", ids()[f"re-ueber:{self.re}"]["detail"])
        ze = self.ms.erstellen(self.re, FD, erinnerung=True)
        self.assertIn("Zahlungserinnerung", ids()[f"re-ueber:{self.re}"]["titel"])
        self.ms.versendet(ze["nummer"], {"an": "x"})
        f = self.ms.faellige_folgemahnungen(jetzt().date() + timedelta(days=8))
        self.assertEqual([(x["rechnung"], x["stufe"]) for x in f], [(self.re, 1)])   # danach fragt LUNA nach der 1. Mahnung
        v = kette(self.bh.eintraege(), self.re)
        knoten = {k["id"]: k for k in v["knoten"]}
        self.assertEqual(knoten[ze["nummer"]]["titel"], "Zahlungserinnerung")

    def test_4_mail_und_anhaenge(self):
        ze = self.ms.erstellen(self.re, FD, erinnerung=True)
        voll = self.ms.get(ze["nummer"])
        betreff, text = mahnung_mail_text(voll, None, FD, kunde="Brand X")
        self.assertIn(self.re, betreff)
        self.assertIn("im täglichen Stress", text)
        self.assertNotIn("Mahnung", betreff)
        g = MockGoogleWorkspace()
        senden(self.ms, g, ze["nummer"], an="kunde@example.de", betreff=betreff, text=text, von="t")
        namen = [a[0] for a in g.gesendet[-1]["anhaenge"]]
        self.assertEqual(namen[0], f"Zahlungserinnerung_{ze['nummer']}.pdf")
        self.assertEqual(len(namen), 2)                                          # Rechnung geht mit
        self.assertTrue(all(a[1] > 0 for a in g.gesendet[-1]["anhaenge"]))                   # Mock merkt sich die Groesse


class TestVorschlagZ2(unittest.TestCase):
    """Z2: Vorschlag per Telegram ab 3 Tagen Ueberfaelligkeit, nur ohne bisherige Erinnerung/Mahnung, ❌ setzt aus."""
    def setUp(self):
        self.bh, self.ks, _, self.k, self.ap = _stores()
        self.rs, self.ms = RechnungStore(self.bh, self.ks), MahnStore(self.bh, self.ks)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=20)):
            self.re = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]
        self.faellig = date.fromisoformat(self.rs.get(self.re)["faellig_am"])

    def test_1_zeitpunkt_und_bedingungen(self):
        vor = lambda tage, **kw: [(x["rechnung"], x["stufe"]) for x in
                                  self.ms.faellige_folgemahnungen(self.faellig + timedelta(days=tage), **kw)]
        self.assertEqual(vor(2, erinnerung=True), [])                              # erst ab 3 Tagen nach Faelligkeit
        self.assertEqual(vor(3, erinnerung=True), [(self.re, 0)])
        self.assertEqual(vor(10), [])                                                # Schalter aus -> kein Vorschlag
        self.ms.aussetzen(self.re, 0, "nein")
        self.assertEqual(vor(10, erinnerung=True), [])                               # ❌ -> fragt nicht mehr

    def test_2_nach_erinnerung_oder_zahlung_kein_vorschlag(self):
        tag = self.faellig + timedelta(days=10)
        ze = self.ms.erstellen(self.re, FD, erinnerung=True)
        self.assertEqual(self.ms.faellige_folgemahnungen(tag, erinnerung=True), [])
        self.ms.versendet(ze["nummer"], {"an": "x"})
        self.assertEqual(self.ms.faellige_folgemahnungen(jetzt().date() + timedelta(days=8), erinnerung=True)[0]["stufe"], 1)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=20)):
            re2 = self.rs.festschreiben(_entwurf(self.rs, self.k, self.ap, zahlungsziel_tage=14), FD)["nummer"]
        self.rs.bezahlt(re2, datum="")
        self.assertNotIn(re2, [x["rechnung"] for x in self.ms.faellige_folgemahnungen(tag, erinnerung=True)])

    def test_3_telegram_text_und_senden(self):
        from orchestrator.core.mahnungen import folgemahnung_frage, folgemahnung_senden
        v = self.ms.berechnen(self.re, erinnerung=True)
        txt = folgemahnung_frage(v, "Brand X")
        self.assertIn("Zahlungserinnerung", txt)
        self.assertNotIn("Verzugszinsen", txt)
        g = MockGoogleWorkspace()
        r = folgemahnung_senden(self.bh, self.ks, g, self.re, 0, FD, von="Telegram:CEO")
        self.assertTrue(r["nummer"].startswith("ZE-"))
        self.assertEqual(len(g.gesendet[-1]["anhaenge"]), 2)
        self.assertIn("Erinnerung", g.gesendet[-1]["betreff"])
        with self.assertRaises(ValueError):
            folgemahnung_senden(self.bh, self.ks, g, self.re, 0, FD, von="t")       # nur einmal


class TestZahlungserinnerungApi(ApiBasis):
    def test_a1_ablauf(self):
        self.w.kunden_store.bh.dir.joinpath("firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")
        rs = RechnungStore(self.w.kunden_store.bh, self.w.kunden_store)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() - timedelta(days=30)):
            re = rs.festschreiben(_entwurf(rs, self.k, self.ap, zahlungsziel_tage=7), FD)["nummer"]
        d = self.c.get(f"/api/finanzen/rechnungen/{re}").json()
        self.assertEqual((d["naechste_erinnerung"]["stufe"], d["naechste_mahnung"]["stufe"]), (0, 1))
        v = self.c.get(f"/api/finanzen/rechnungen/{re}/mahnung-vorschau?frist_tage=10&erinnerung=true").json()
        self.assertEqual((v["stufe"], v["gebuehr_cent"]), (0, 0))
        m = self.c.post(f"/api/finanzen/rechnungen/{re}/mahnung", json={"frist_tage": 10, "bestaetigt": True,
                                                                          "erinnerung": True}).json()
        self.assertTrue(m["nummer"].startswith("ZE-"), m)
        r = self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}/pdf")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Zahlungserinnerung_", r.headers["content-disposition"])
        vs = self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}/versandvorschau").json()
        self.assertEqual((vs["art"], vs["zusatz_pdf"]), ("zahlungserinnerung", f"Rechnung {re}"))
        s = self.c.post(f"/api/finanzen/mahnungen/{m['nummer']}/senden",
                        json={"an": vs["an"], "betreff": vs["betreff"], "text": vs["text"], "bestaetigt": True}).json()
        self.assertTrue(s["ok"], s)
        d = self.c.get(f"/api/finanzen/rechnungen/{re}").json()
        self.assertIsNone(d["naechste_erinnerung"])
        self.assertEqual(d["naechste_mahnung"]["stufe"], 1)
        self.assertEqual(self.c.get(f"/api/finanzen/mahnungen/{m['nummer']}").json()["blatt"]["art"], "Zahlungserinnerung")


if __name__ == "__main__":
    unittest.main()
