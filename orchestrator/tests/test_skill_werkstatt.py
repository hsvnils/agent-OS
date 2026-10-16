"""SKILL_WERKSTATT S1-S4 (CEO 2026-10-16): nur eigene Skills -- Radar liefert Ideen (nichts uebernehmen), Luecken aus der
eigenen Arbeit, Werkstatt mit Pruffaellen und Probelauf mit/ohne Skill, Freigabe Pflicht, Lernen aus Rueckmeldungen."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from orchestrator.core import skill_werkstatt as sw
from orchestrator.core.dept_skills import lade_dept_skills
from orchestrator.governance.github_watch import Repo

KARTE = """---
name: {name}
version: {version}
beschreibung: Testskill
lizenz: {lizenz}
autor: Test
governance: intern
modell: Richtwert
---
# Skill: {name}

## Vorgehen
1. Gruss mit Namen.
2. Preis nennen.
"""


def _entwurf(name="angebot-gastro", version="1.0.0", lizenz="intern"):
    return ("===SKILL===\n" + KARTE.format(name=name, version=version, lizenz=lizenz) + "===PRUEFFAELLE===\n"
            + json.dumps([{"eingabe": "Angebot fuer Kiez Burger", "kriterien": ["nennt Preis", "duzt nicht"]},
                          {"eingabe": "Angebot fuer Hafenbar", "kriterien": ["nennt Preis", "max 5 Saetze", "Gruss"]}]))


class FakeBO:
    """Backoffice wie `AuftragStore` (anlegen/get); `erledigen(fn)` beantwortet alle offenen Auftraege."""
    def __init__(self):
        self.jobs = {}

    def anlegen(self, aufgabe, *, art="sonstiges", von="", system="", zweck="", stumm=False, lokal_modell=""):
        jid = f"BO-{len(self.jobs) + 1}"
        self.jobs[jid] = {"id": jid, "status": "neu", "aufgabe": aufgabe, "system": system, "zweck": zweck, "art": art, "stumm": stumm,
                          "lokal_modell": lokal_modell}
        return jid

    def get(self, jid):
        return self.jobs.get(jid)

    def erledigen(self, fn):
        for j in self.jobs.values():
            if j["status"] == "neu":
                j |= {"status": "fertig", "ergebnis": fn(j)}


def _antwort(kandidat_besser=True):
    def fn(j):
        if j["zweck"].endswith(":entwurf"):
            return _entwurf()
        if ":urteil" in j["zweck"]:
            wid, i = j["zweck"].split(":")[1], int(j["zweck"].rsplit("urteil", 1)[1])
            kand_vorne = sw._reihenfolge(wid, i)
            gut, schlecht = 2, 0
            a, b = ((gut, schlecht) if kand_vorne else (schlecht, gut)) if kandidat_besser else ((schlecht, gut) if kand_vorne else (gut, schlecht))
            return json.dumps({"A": a, "B": b, "besser": "A" if a > b else "B"})
        return "Antwort " + ("mit Skill" if "## Skill" in j["system"] else "ohne Skill")
    return fn


def _werkstatt(mit_repo_skill=True):
    root = Path(tempfile.mkdtemp())
    if mit_repo_skill:
        d = root / "skills" / "cfo" / "rechnung-pruefen"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(KARTE.format(name="rechnung-pruefen", version="1.0.0", lizenz="intern"), encoding="utf-8")
    return sw.Werkstatt(root / "skills_werkstatt", root / "skills_eigen", root), root


class TestRadarUndLuecken(unittest.TestCase):
    def test_1_radar_nur_ideen(self):
        w, _ = _werkstatt()
        repos = [Repo("a/invoice-skills", "https://github.com/a/invoice-skills", 900, "Invoice and accounting skills " + "x" * 300, topics=["agent-skills"]),
                 Repo("b/sales-outreach", "https://github.com/b/sales-outreach", 450, "Sales outreach and lead skills"),
                 Repo("c/random", "https://github.com/c/random", 30, "misc")]
        neu = w.radar_merken(repos, "2026-10-16T08:00:00")
        st = {x["name"]: (x["status"], x["abteilungen"], x["eigener"]) for x in neu}
        self.assertEqual(st["a/invoice-skills"][0], "vorhanden")                                  # cfo hat rechnung-pruefen
        self.assertEqual(st["b/sales-outreach"][:2], ("luecke", ["cro"]))
        self.assertEqual(st["c/random"][0], "ohne_bezug")
        self.assertLessEqual(max(len(x["kurz"]) for x in neu), 140)                              # nie mehr als ein Anriss
        self.assertEqual(w.radar_merken(repos, "2026-11-16T08:00:00"), [])                       # nicht doppelt
        self.assertIn("nichts", sw.radar_bericht(neu).lower())

    def test_2_luecken_aus_eigener_arbeit(self):
        w, _ = _werkstatt()
        w.radar_merken([Repo("b/sales-outreach", "u", 450, "Sales outreach skills")], "t")
        ideen = sw.luecken(w, nutzung={"cro": {"anzahl": 6, "fehler": 0}, "cfo": {"anzahl": 10, "fehler": 4}, "cto": {"anzahl": 2, "fehler": 2}},
                           trajektorien=[{"tags": ["Rechnung"], "erfolg": True}] * 3 + [{"tags": ["research"], "erfolg": True}] * 3,
                           jetzt="2026-10-16T08:00:00")
        titel = sorted((i["abteilung"], i["quelle"]) for i in ideen)
        self.assertEqual(titel, [("cfo", "Nutzung"), ("cro", "Nutzung"), ("cro", "Skill-Radar"), ("res", "Erfahrungen")])
        self.assertEqual(sw.luecken(w, nutzung={"cro": {"anzahl": 6, "fehler": 0}}, trajektorien=[], jetzt="t2"), [])   # dedupliziert


class TestWerkstatt(unittest.TestCase):
    def test_3_ablauf_bis_aktiv_und_rueckweg(self):
        w, root = _werkstatt()
        bo = FakeBO()
        e = w.idee(abteilung="cro", titel="Angebotstext Gastro", warum="Test", quelle="CEO", jetzt="t")
        sw.entwurf_starten(w, bo, e["id"])
        self.assertEqual(sw.tick(w, bo), [])                                                      # Entwurf noch offen
        bo.erledigen(_antwort())
        sw.tick(w, bo)
        x = w.eintraege()[e["id"]]
        self.assertEqual((x["status"], len(x["pruffaelle"]), x["ordner"]), ("probelauf", 2, "angebot-gastro"))
        probe = [j for j in bo.jobs.values() if ":kand" in j["zweck"] or ":verg" in j["zweck"]]
        self.assertEqual(len(probe), 4)                                                           # je Fall mit + ohne
        self.assertEqual(sorted("## Skill" in j["system"] for j in probe), [False, False, True, True])
        with self.assertRaises(ValueError):
            w.aktivieren(e["id"])                                                                 # erst nach Pruefung
        bo.erledigen(_antwort())
        sw.tick(w, bo)
        bo.erledigen(_antwort())
        meldung = sw.tick(w, bo)
        x = w.eintraege()[e["id"]]
        self.assertEqual((x["status"], x["ergebnis"]["kandidat"], x["ergebnis"]["vergleich"]), ("zur_freigabe", 4, 0))
        self.assertIn("besser", meldung[0])
        self.assertNotIn("angebot-gastro", lade_dept_skills("cro", root)[0])                      # vor Freigabe nicht aktiv
        w.aktivieren(e["id"])
        self.assertIn("### Skill: angebot-gastro", lade_dept_skills("cro", root)[0])
        self.assertTrue((root / "skills_eigen" / "cro" / "angebot-gastro" / "pruffaelle.json").exists())

    def test_4_nicht_besser_und_ungueltig(self):
        w, _ = _werkstatt()
        bo = FakeBO()
        e = w.idee(abteilung="cro", titel="X", warum="", quelle="CEO", jetzt="t")
        sw.entwurf_starten(w, bo, e["id"])
        for _ in range(3):
            bo.erledigen(_antwort(kandidat_besser=False))
            sw.tick(w, bo)
        self.assertEqual(w.eintraege()[e["id"]]["status"], "nicht_besser")
        e2 = w.idee(abteilung="cro", titel="Y", warum="", quelle="CEO", jetzt="t")
        sw.entwurf_starten(w, bo, e2["id"])
        bo.erledigen(lambda j: _entwurf(lizenz="MIT"))                                           # fremde Lizenz = kein eigener Skill
        sw.tick(w, bo)
        x = w.eintraege()[e2["id"]]
        self.assertEqual(x["status"], "fehler")
        self.assertIn("intern", x["verlauf"][-1]["text"])
        with self.assertRaises(ValueError):
            sw.entwurf_lesen("kaputt")

    def test_5_lernen_aus_rueckmeldungen(self):
        w, root = _werkstatt()
        with self.assertRaises(KeyError):
            w.rueckmeldung("cfo/gibt-es-nicht", gut=False)
        w.rueckmeldung("cfo/rechnung-pruefen", gut=True)
        w.rueckmeldung("cfo/rechnung-pruefen", gut=False, text="zu lang")
        self.assertEqual(sw.verbesserungen_anstossen(w), [])                                      # erst ab 3
        w.rueckmeldung("cfo/rechnung-pruefen", gut=False, text="Skonto vergessen")
        v = sw.verbesserungen_anstossen(w)
        self.assertEqual((len(v), v[0]["art"], v[0]["ordner"]), (1, "verbesserung", "rechnung-pruefen"))
        self.assertIn("Version 1.1.0", v[0]["titel"])
        self.assertIn("Skonto vergessen", v[0]["aufgabe"])
        self.assertEqual(sw.verbesserungen_anstossen(w), [])                                      # laeuft schon
        bo = FakeBO()
        sw.entwurf_starten(w, bo, v[0]["id"])
        bo.erledigen(lambda j: _entwurf(name="rechnung-pruefen", version="1.1.0"))
        sw.tick(w, bo)
        verg = [j for j in bo.jobs.values() if ":verg" in j["zweck"]]
        self.assertTrue(all("Gruss mit Namen" in j["system"] for j in verg))                      # alt gegen neu, nicht ohne
        for _ in range(2):
            bo.erledigen(_antwort())
            sw.tick(w, bo)
        w.aktivieren(v[0]["id"])
        self.assertIn("version: 1.1.0", w.skill_text("cfo", "rechnung-pruefen"))
        self.assertEqual(lade_dept_skills("cfo", root)[0].count("### Skill: rechnung-pruefen"), 1)   # ueberschreibt, kein Doppel
        self.assertTrue(all(r["verarbeitet"] for r in w.rueckmeldungen()["cfo/rechnung-pruefen"]))
        self.assertEqual(w.zurueck("cfo", "rechnung-pruefen")["wiederhergestellt"] != "", True)
        self.assertIn("version: 1.0.0", w.skill_text("cfo", "rechnung-pruefen"))


class TestBotUndApi(unittest.TestCase):
    def test_6_bot_lauf(self):
        from orchestrator.channels.telegram import bot
        w, _ = _werkstatt()
        gesendet = []
        gh = mock.Mock(trending=lambda thema, **k: [Repo(f"x/{thema}-sales", "u", 300, "sales lead skills")])
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append(p["text"])), \
                mock.patch.object(bot, "_skill_werkstatt", return_value=w):
            out = bot.skill_lauf("T", "1", {}, backoffice=FakeBO(), jetzt=datetime(2026, 11, 1, 8), monatlich=True, taeglich=True,
                                 github=gh, nutzung={}, trajektorien=[])
        self.assertEqual((out["radar"], out["ideen"]), (4, 1))
        self.assertTrue(any("Skill-Radar" in g for g in gesendet))
        self.assertTrue(any("Skill-Idee" in g for g in gesendet))

    def test_7_api(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.auftraege import AuftragStore
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/skills/rueckmeldung"), "administration")
        w, root = _werkstatt()
        bo = AuftragStore(root / "bo.jsonl")
        c = TestClient(webapp.app)
        with mock.patch.object(webapp, "_werkstatt", return_value=w), mock.patch.object(webapp, "_backoffice_store", return_value=bo), \
                mock.patch.object(webapp, "ROOT", root):
            r = c.post("/api/skills/werkstatt", json={"abteilung": "cro", "titel": "Angebotstext Gastro", "gleich_bauen": True}).json()
            self.assertEqual((r["ok"], r["eintrag"]["status"]), (True, "entwurf_angefragt"))
            self.assertEqual(bo.list("neu")[0]["art"], "roh")                                     # an das Backoffice
            self.assertFalse(c.post("/api/skills/werkstatt", json={"abteilung": "cro", "titel": "Angebotstext Gastro"}).json()["ok"])
            self.assertTrue(c.post("/api/skills/rueckmeldung", json={"skill": "cfo/rechnung-pruefen", "gut": True}).json()["ok"])
            d = c.get("/api/skills").json()
            self.assertEqual(([s["name"] for s in d["skills"]], d["skills"][0]["rueckmeldungen"]), (["rechnung-pruefen"], 1))
            self.assertFalse(c.post(f"/api/skills/werkstatt/{r['eintrag']['id']}/aktivieren", json={}).json()["ok"])   # noch nicht geprueft


if __name__ == "__main__":
    unittest.main()
