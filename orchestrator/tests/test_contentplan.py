"""CONTENT_PLAN C1-C3: eigene Eintraege (Kette, Pruefung), Kunden-Postings mit geplantem Datum und Drehtermine automatisch,
Feiertage Hamburg lokal berechnet, eigene Anlaesse, Wochenplan-Vorschlag nur als Entwurf."""
import json
import unittest
from datetime import date
from unittest import mock

from orchestrator.core.contentplan import ContentPlan, feiertage_hamburg, ostersonntag, vorschlag
from orchestrator.core.konzept import KonzeptStore
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_postings import REEL, _auftrag


class _Modell:
    def __init__(self, text):
        self.text, self.anfragen = text, []
        self.chat = type("Ch", (), {"completions": self})()

    def create(self, **kw):
        self.anfragen.append(kw)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": self.text})()})()]})()


class TestFeiertage(unittest.TestCase):
    def test_hamburg(self):
        self.assertEqual(ostersonntag(2026), date(2026, 4, 5))
        self.assertEqual(ostersonntag(2027), date(2027, 3, 28))
        f = feiertage_hamburg(2026)
        self.assertEqual((f["2026-04-03"], f["2026-04-06"], f["2026-05-14"], f["2026-05-25"], f["2026-10-31"]),
                         ("Karfreitag", "Ostermontag", "Christi Himmelfahrt", "Pfingstmontag", "Reformationstag"))
        self.assertEqual(len(f), 10)


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.bh, self.ab, self.nr, self.ps = _auftrag([REEL])
        self.cp = ContentPlan(self.bh)

    def test_1_eintraege(self):
        with self.assertRaises(ValueError):
            self.cp.anlegen({"datum": "2026-10-10"})                                # Titel fehlt
        with self.assertRaises(ValueError):
            self.cp.anlegen({"datum": "2026-10-10", "titel": "X", "kanal": "myspace"})
        with self.assertRaises(ValueError):
            self.cp.anlegen({"datum": "2026-10-10", "titel": "X", "zeit": "25:00"})
        pid = self.cp.anlegen({"datum": "2026-10-10", "zeit": "18:30", "titel": "Derby-Reel", "format": "reel"})["id"]
        self.cp.aendern(pid, {"status": "skript", "datum": "2026-10-11"})
        z = self.cp.zeitraum("2026-10-01", "2026-10-31", heute="2026-10-05")
        e = [x for x in z["eintraege"] if x["quelle"] == "plan"]
        self.assertEqual([(x["titel"], x["datum"], x["status"], x["zeit"]) for x in e], [("Derby-Reel", "2026-10-11", "skript", "18:30")])
        self.cp.entfernen(pid)
        self.assertFalse([x for x in self.cp.zeitraum("2026-10-01", "2026-10-31")["eintraege"] if x["quelle"] == "plan"])
        self.assertTrue(any(e["typ"] == "plan_eintrag" for e in self.bh.eintraege()))     # nachvollziehbar in der Kette

    def test_2_postings_dreh_anlaesse(self):
        p1, p2 = f"{self.nr}-P1-1", f"{self.nr}-P1-2"
        self.ps.planen(p1, "2026-10-03")
        self.ps.planen(p2, "2026-10-20")
        KonzeptStore(self.bh).dreh(self.nr, {"datum": "2026-10-08", "zeit": "17:00", "ort": "Kiez"})
        self.cp.anlass({"von": "2026-10-15", "bis": "2026-10-25", "titel": "Herbstkampagne"})
        z = self.cp.zeitraum("2026-10-01", "2026-10-31", heute="2026-10-05")
        po = {x["id"]: x for x in z["eintraege"] if x["quelle"] == "posting"}
        self.assertEqual((po[p1]["status"], po[p1]["ueberfaellig"], po[p2]["ueberfaellig"]), ("geplant", True, False))
        dreh = [x for x in z["eintraege"] if x["quelle"] == "dreh"]
        self.assertEqual(len(dreh), 1)
        self.assertRegex(dreh[0]["titel"], r"^Dreh \S.* · Kiez$")
        self.assertNotIn(self.nr, dreh[0]["titel"])                                    # Kundenname statt Nummer
        self.assertEqual(z["feiertage"], {"2026-10-03": "Tag der Deutschen Einheit", "2026-10-31": "Reformationstag"})
        self.assertEqual([a["titel"] for a in z["anlaesse"]], ["Herbstkampagne"])
        self.assertEqual([x["datum"] for x in z["eintraege"]], sorted(x["datum"] for x in z["eintraege"]))
        self.ps.planen(p2, "")                                                       # Planung entfernen
        self.assertNotIn(p2, {x["id"] for x in self.cp.zeitraum("2026-10-01", "2026-10-31")["eintraege"]})
        with self.assertRaises(ValueError):
            self.cp.zeitraum("2026-01-01", "2028-01-01")                               # zu langer Zeitraum

    def test_3_vorschlag_nur_passende(self):
        self.ps.planen(f"{self.nr}-P1-1", "2026-10-07")
        self.cp.anlegen({"datum": "2026-10-09", "titel": "Derby-Recap"})
        plan = self.cp.zeitraum("2026-10-05", "2026-10-11")
        antwort = {"vorschlaege": [{"datum": "2026-10-06", "kanal": "tiktok", "format": "reel", "titel": "Fanmarsch", "notiz": "POV"},
                                   {"datum": "2026-12-24", "titel": "ausserhalb"}, {"datum": "2026-10-07", "titel": ""},
                                   {"datum": "2026-10-08", "kanal": "myspace", "format": "?", "titel": "Kiez-Talk"}]}
        modell = _Modell(json.dumps(antwort))
        v = vorschlag(plan, system="CCO", client=modell)
        prompt = modell.anfragen[0]["messages"][-1]["content"]
        self.assertIn("2026-10-07 Kunden-Posting", prompt)
        self.assertIn("Derby-Recap", prompt)
        posting = next(x for x in plan["eintraege"] if x["quelle"] == "posting")
        self.assertNotIn(posting["titel"], prompt)                                    # kein Kunden-/Auftragsname an Gemini
        self.assertEqual([(x["datum"], x["kanal"], x["format"], x["titel"]) for x in v],
                         [("2026-10-06", "tiktok", "reel", "Fanmarsch"), ("2026-10-08", "instagram", "reel", "Kiez-Talk")])
        with self.assertRaises(ValueError):
            vorschlag(plan, system="CCO", client=_Modell("weiss nicht"))


class TestApi(ApiBasis):
    def test_endpunkte(self):
        r = self.c.post("/api/contentplan", json={"datum": "2026-10-10", "titel": "Spieltag-Story", "format": "story", "kunde": self.k}).json()
        self.assertTrue(r["ok"], r)
        self.assertTrue(self.c.post(f"/api/contentplan/{r['id']}", json={"status": "geplant"}).json()["ok"])
        a = self.c.post("/api/contentplan/anlass", json={"von": "2026-10-09", "titel": "Derby-Woche", "bis": "2026-10-12"}).json()
        z = self.c.get("/api/contentplan?von=2026-10-01&bis=2026-10-31").json()
        self.assertEqual([(x["status"], bool(x["kunde_name"])) for x in z["eintraege"] if x["quelle"] == "plan"], [("geplant", True)])
        self.assertEqual(len(z["anlaesse"]), 1)
        self.assertTrue(self.c.post(f"/api/contentplan/anlass/{a['id']}/entfernen").json()["ok"])
        self.assertTrue(self.c.post(f"/api/contentplan/{r['id']}/entfernen").json()["ok"])
        self.assertFalse(self.c.post("/api/contentplan/CP-gibtsnicht/entfernen").json()["ok"])
        self.assertEqual(self.c.get("/api/contentplan?von=2026-10-31&bis=2026-10-01").status_code, 400)

    def test_posting_planen(self):
        an = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst",
                                                                "positionen": [REEL]}}).json()["nummer"]
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        pid = self.c.get(f"/api/crm/auftraege/{nr}/postings").json()["postings"][0]["id"]
        self.assertTrue(self.c.post(f"/api/crm/postings/{pid}/geplant", json={"datum": "2026-10-14"}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/postings/{pid}/geplant", json={"datum": "morgen"}).json()["ok"])
        self.assertEqual(self.c.get(f"/api/crm/auftraege/{nr}/postings").json()["postings"][0]["geplant"], "2026-10-14")
        z = self.c.get("/api/contentplan?von=2026-10-01&bis=2026-10-31").json()["eintraege"]
        self.assertEqual([(x["id"], x["quelle"], x["status"], x["titel"].endswith("(Herbst)")) for x in z], [(pid, "posting", "geplant", True)])

    def test_vorschlag_speichert_nichts_und_zaehlt(self):
        gezaehlt, antwort = [], json.dumps({"vorschlaege": [{"datum": "2026-10-06", "titel": "Fanmarsch"}]})
        with mock.patch("openai.OpenAI", return_value=_Modell(antwort)), \
             mock.patch.object(self.w, "_google_secrets", return_value={"GEMINI_API_KEY": "x" * 20}), \
             mock.patch("orchestrator.core.agenten_profil.AgentenNutzung.erfassen",
                        lambda self_, agent, **kw: gezaehlt.append((agent, kw["quelle"], kw["ok"]))):
            r = self.c.post("/api/contentplan/vorschlag", json={"von": "2026-10-05", "bis": "2026-10-11"}).json()
        self.assertEqual([v["titel"] for v in r["vorschlaege"]], ["Fanmarsch"])
        self.assertEqual(gezaehlt, [("cco", "konzept", True)])
        self.assertFalse(self.c.get("/api/contentplan?von=2026-10-01&bis=2026-10-31").json()["eintraege"])   # nur Entwurf
        with mock.patch.object(self.w, "_google_secrets", return_value={}):
            r = self.c.post("/api/contentplan/vorschlag", json={"von": "2026-10-05", "bis": "2026-10-11"}).json()
        self.assertEqual((r["ok"], r["hinweis"]), (False, "Kein Gemini-Zugang konfiguriert."))


if __name__ == "__main__":
    unittest.main()
