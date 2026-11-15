"""MONETARISIERUNG M8: Kneipen als Kunden. Gate: Testkneipe von Angebot ueber Auftrag bis Rechnung, Listung erscheint mit
richtigem Zeitraum, Erinnerungen (App-Eintrag, Verlaengerung) werden per Telegram gesendet. Gegenproben: Storno nimmt die
Listung heraus, To-dos nur einmal, andere Rechnungen sind keine Listung, spaetere Positionen zaehlen nicht."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.aufgaben import AufgabenStore, erinnerungen_senden
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.kneipen import _plus_monate, art, aufgaben, listung, uebersicht
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.saeulen import vorschlag
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()
MONAT = {"beschreibung": "Spieltags-Partner in der Fan-App", "menge": "3", "einzelpreis": "10", "katalog_id": "kneipe_monat"}


class TestRegeln(unittest.TestCase):
    def test_1_positionen_und_zeitraum(self):
        self.assertEqual([art(p) for p in (MONAT, {"beschreibung": "Saisonpaket Spieltags-Partner"},
                                           {"beschreibung": "Reel", "katalog_id": "reel_solo"},
                                           MONAT | {"spaeter_am": "2027-01-01"})], ["monat", "saison", "", ""])
        self.assertEqual(_plus_monate(date(2026, 11, 30), 3), date(2027, 2, 28))
        r = {"nummer": "RE-1", "firma": "K-1", "rechnungsdatum": "2026-11-15", "leistung_von": "2026-11-15",
             "positionen": [MONAT], "status": "offen", "summe_cent": 3000}
        self.assertEqual((listung(r)["von"], listung(r)["bis"]), ("2026-11-15", "2027-02-14"))
        s = r | {"positionen": [{"beschreibung": "Saisonpaket Spieltags-Partner", "katalog_id": "kneipe_saison"}]}
        self.assertEqual(listung(s)["bis"], "2027-06-30")
        self.assertEqual(listung(s | {"leistung_von": "2027-07-01"})["bis"], "2028-06-30")
        self.assertEqual(listung(r | {"leistung_bis": "2026-12-31"})["bis"], "2026-12-31")              # Rechnung gilt
        self.assertIsNone(listung(r | {"status": "storniert"}))
        self.assertIsNone(listung(r | {"positionen": [{"beschreibung": "Reel", "menge": "1"}]}))
        self.assertEqual(vorschlag("einnahme", "Kiezkneipe", "Spieltags-Partner in der Fan-App", quelle="rechnung")[0], "S3b")

    def test_2_uebersicht_status(self):
        h = date(2026, 11, 15)
        def r(nr, firma, von, bis):
            return {"nummer": nr, "firma": firma, "rechnungsdatum": von, "leistung_von": von, "leistung_bis": bis,
                    "positionen": [MONAT], "status": "bezahlt"}
        u = uebersicht({x["nummer"]: x for x in (r("RE-1", "K-1", "2026-09-01", "2026-11-30"),
                                                 r("RE-2", "K-2", "2026-10-01", "2027-03-31"),
                                                 r("RE-3", "K-3", "2026-06-01", "2026-08-31"),
                                                 r("RE-4", "K-1", "2026-12-01", "2027-02-28"),     # Verlaengerung
                                                 r("RE-5", "K-4", "2026-12-01", "2027-01-31"))},
                       {"K-1": "Kiez Eck"}, h)
        st = {k["firma"]: (k["status"], k["bis"]) for k in u["kneipen"]}
        self.assertEqual(st, {"K-1": ("aktiv", "2027-02-28"), "K-2": ("aktiv", "2027-03-31"), "K-3": ("abgelaufen", "2026-08-31"),
                              "K-4": ("kommend", "2027-01-31")})
        self.assertEqual((u["aktiv"], u["laeuft_aus"]), (2, 0))
        u2 = uebersicht({"RE-1": r("RE-1", "K-1", "2026-09-01", "2026-11-30")}, {}, h)
        self.assertEqual((u2["kneipen"][0]["status"], u2["kneipen"][0]["tage_rest"], u2["laeuft_aus"]), ("laeuft_aus", 15, 1))


class TestTestkneipe(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, st, k, ap = _stores()
        self.k = k
        an = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": [MONAT]})["nummer"]
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        ab = AuftragBuch(self.bh, self.ks, st)
        auftrag = ab.aus_angebot(an, leistung_von=HEUTE.isoformat())["nummer"]
        self.rs = RechnungStore(self.bh, self.ks)
        eid = self.rs.entwurf_aus_auftrag(ab.auftrag(auftrag))["entwurf_id"]
        self.nr = self.rs.festschreiben(eid, FD)["nummer"]
        self.todos = AufgabenStore(Path(tempfile.mkdtemp()) / "todos.jsonl")

    def test_1_angebot_bis_rechnung_und_erinnerung(self):
        r = self.rs.get(self.nr)
        x = listung(r)
        bis = _plus_monate(HEUTE, 3) - timedelta(days=1)
        self.assertEqual((x["von"], x["bis"], x["summe_cent"], x["pakete"]), (HEUTE.isoformat(), bis.isoformat(), 3000, ["monat"]))
        neu = aufgaben(self.todos, r, "Testkneipe", HEUTE)
        self.assertEqual([a["faellig"] for a in neu], [HEUTE.isoformat(), (bis - timedelta(days=14)).isoformat()])
        self.assertIn(f"{bis:%d.%m.%Y}", neu[0]["titel"])
        self.assertEqual(aufgaben(self.todos, r, "Testkneipe", HEUTE), [])                 # Gegenprobe: nur einmal
        gesendet = []
        mit = lambda t, k: gesendet.append(t) or True
        tag = bis - timedelta(days=14)
        erinnerungen_senden(self.todos, mit, jetzt=datetime(tag.year, tag.month, tag.day, 10, 0))
        self.assertTrue(any("Verlängerung anbieten: Testkneipe" in t for t in gesendet), gesendet)

    def test_2_storno_nimmt_listung_heraus(self):
        self.rs.stornieren(self.nr, FD, grund="Test")
        _, rechnungen = self.rs._stand()
        self.assertEqual(uebersicht(rechnungen, {}, HEUTE)["kneipen"], [])


class TestApi(ApiBasis):
    def test_1_festschreiben_legt_todos_an(self):
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")
        store = AufgabenStore(Path(tempfile.mkdtemp()) / "todos.jsonl")
        with mock.patch.object(self.w, "_aufgaben", return_value=store):
            e = self.c.post("/api/finanzen/rechnungen", json={"rechnung": {
                "firma": self.k, "ansprechpartner": self.ap, "leistung_von": HEUTE.isoformat(), "positionen": [MONAT]}}).json()
            r = self.c.post(f"/api/finanzen/rechnungen/{e['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
            self.assertTrue(r["ok"], r)
            self.assertTrue(any("Kneipen-Listung" in h for h in r["hinweise"]), r["hinweise"])
            titel = sorted(a["titel"][:12] for g in store.liste().values() for a in g)
            self.assertEqual(titel, ["Kneipe in de", "Verlängerung"])
            k = self.c.get("/api/finanzen/kneipen").json()
            self.assertEqual((k["aktiv"], k["kneipen"][0]["listungen"][0]["rechnung"]), (1, r["nummer"]))
            # Gegenprobe: normale Rechnung legt keine Kneipen-To-dos an
            e2 = self.c.post("/api/finanzen/rechnungen", json={"rechnung": {
                "firma": self.k, "ansprechpartner": self.ap, "leistung_von": HEUTE.isoformat(),
                "positionen": [{"beschreibung": "Reel", "menge": "1", "einzelpreis": "100"}]}}).json()
            r2 = self.c.post(f"/api/finanzen/rechnungen/{e2['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
            self.assertTrue(r2["ok"], r2)
            self.assertEqual(sum(len(g) for g in store.liste().values()), 2)

    def test_2_oberflaeche(self):
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        for teil in ("finKneipen", "/api/finanzen/kneipen", '["kneipen", "Kneipen"]', "KNEIPE_RE"):
            self.assertIn(teil, js)


if __name__ == "__main__":
    unittest.main()
