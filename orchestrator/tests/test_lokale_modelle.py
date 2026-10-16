"""MODELL_RADAR R4 (CEO 2026-10-16): bessere lokale Modelle -- Kandidaten aus der Ollama-Bibliothek (Werkzeuge, passt auf
den MACO470), Qualitaet aus Artificial Analysis, Probelauf altes gegen neues Modell ueber das Backoffice; plus BF-71
(ungueltiger GitHub-Schluessel -> oeffentlich weiter)."""
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime
from pathlib import Path
from unittest import mock

from orchestrator.core import modell_radar as mr
from orchestrator.core.auftraege import AuftragStore
from orchestrator.tests.test_skill_werkstatt import FakeBO

BIB = """<li><a href="/library/qwen3" class="g"><h2>qwen3</h2><p>Qwen3 is the latest generation of large language models in Qwen series.</p>
<span>tools</span><span>thinking</span><span>0.6b</span><span>14b</span><span>30b</span><span>235b</span><span>40.3M</span><span>&nbsp;Pulls</span>
<span>Updated&nbsp;</span><span>1 year ago</span></a></li>
<li><a href="/library/qwen3.5" class="g"><h2>qwen3.5</h2><p>Qwen3.5 brings better tool use and reasoning to every size of the family.</p>
<span>tools</span><span>9b</span><span>27b</span><span>122b</span><span>1.2M</span><span>&nbsp;Pulls</span><span>Updated&nbsp;</span><span>2 days ago</span></a></li>
<li><a href="/library/bild-only" class="g"><h2>bild-only</h2><p>A vision model without tool calling for describing images only.</p>
<span>vision</span><span>7b</span><span>Updated&nbsp;</span><span>3 days ago</span></a></li>
<li><a href="/library/riesig" class="g"><h2>riesig</h2><p>A very large model with tool use that never fits a small home server.</p>
<span>tools</span><span>70b</span><span>Updated&nbsp;</span><span>3 days ago</span></a></li>
<li><a href="/library/nur-cloud" class="g"><h2>nur-cloud</h2><p>Cloud only model offered through the hosted service, not for local use.</p>
<span>tools</span><span>cloud</span><span>Updated&nbsp;</span><span>1 day ago</span></a></li>"""
AA = [{"name": "Qwen3 30B A3B", "slug": "qwen3-30b-a3b", "hersteller": "Alibaba", "iq": 40.0, "preis": 0.3, "preis_in": 0.1, "preis_out": 0.9, "tempo": 80},
      {"name": "Qwen3.5 27B", "slug": "qwen3-5-27b", "hersteller": "Alibaba", "iq": 47.0, "preis": 0.3, "preis_in": 0.1, "preis_out": 0.9, "tempo": 60}]


class TestKandidaten(unittest.TestCase):
    def test_1_liste_und_auswahl(self):
        self.assertEqual((mr.groesse_b("qwen3:30b-a3b"), mr.groesse_b("gemma3:4b"), mr.groesse_b("qwen3:0.6b"), mr.groesse_b("llama")),
                         (30.0, 4.0, 0.6, None))
        l = mr.lies_ollama(BIB)
        self.assertEqual([(x["name"], x["groessen"]) for x in l][:2], [("qwen3", [0.6, 14.0, 30.0, 235.0]), ("qwen3.5", [9.0, 27.0, 122.0])])
        self.assertEqual((l[0]["aktualisiert"], l[0]["pulls"], l[0]["faehigkeiten"]), ("1 year ago", "40.3M", ["tools", "thinking"]))
        k = mr.lokale_kandidaten("qwen3:30b-a3b", l, [])
        self.assertEqual([c["modell"] for c in k["kandidaten"]], ["qwen3.5:27b"])     # eigene Familie, ohne Tools, zu gross, Cloud raus
        self.assertEqual(k["vorschlaege"], [])                                          # ohne Qualitaetsdaten kein Vorschlag
        k = mr.lokale_kandidaten("qwen3:30b-a3b", l, AA)
        self.assertEqual([(v["modell"], v["iq"], v["unser_iq"]) for v in k["vorschlaege"]], [("qwen3.5:27b", 47.0, 40.0)])
        self.assertEqual(mr.lokale_kandidaten("qwen3:30b-a3b", l, AA, max_b=14)["kandidaten"][0]["modell"], "qwen3.5:9b")
        titel, text = mr.lokal_vorschlag_text("qwen3:30b-a3b", k["vorschlaege"][0])
        self.assertIn("qwen3.5:27b", titel)
        self.assertIn("Umgestellt wird erst nach deiner Entscheidung", text)


class TestProbelauf(unittest.TestCase):
    def test_2_alt_gegen_neu(self):
        r, bo = mr.Radar(Path(tempfile.mkdtemp()) / "radar"), FakeBO()
        lt = mr.LokalTests(r)
        with self.assertRaises(ValueError):
            lt.starten(bo, alt="qwen3:30b-a3b", neu="x; rm -rf /", faelle=mr.STANDARD_PRUEFFAELLE, jetzt="t")
        t = lt.starten(bo, alt="qwen3:30b-a3b", neu="qwen3.5:27b", faelle=mr.STANDARD_PRUEFFAELLE[:2], jetzt="2026-10-16T20:00:00")
        self.assertEqual(sorted(k for k, v in t["jobs"].items() if bo.get(v)["lokal_modell"] == "qwen3.5:27b"), ["neu0", "neu1"])
        with self.assertRaises(ValueError):
            lt.starten(bo, alt="qwen3:30b-a3b", neu="qwen3.5:27b", faelle=mr.STANDARD_PRUEFFAELLE[:2], jetzt="t2")   # laeuft schon
        for j in bo.jobs.values():
            j |= {"status": "fertig", "ergebnis": "Antwort", "dauer_s": 12.0 if ":neu" in j["zweck"] else 20.0}
        self.assertEqual(lt.tick(bo), [])
        t = lt.alle()[t["id"]]
        self.assertEqual((t["status"], t["dauer_neu"], t["dauer_alt"]), ("urteil", 12.0, 20.0))
        from orchestrator.core.skill_werkstatt import _reihenfolge
        for k, j in bo.jobs.items():
            if ":urteil" in j["zweck"]:
                i = int(j["zweck"].rsplit("urteil", 1)[1])
                neu_vorne = _reihenfolge(t["id"], i)
                j |= {"status": "fertig", "ergebnis": json.dumps({"A": 4 if neu_vorne else 1, "B": 1 if neu_vorne else 4, "besser": "A" if neu_vorne else "B"})}
        m = lt.tick(bo)
        t = lt.alle()[t["id"]]
        self.assertEqual((t["status"], t["punkte_neu"], t["punkte_alt"], t["besser"]), ("fertig", 8, 2, True))
        self.assertIn("Umstellen entscheidest du", m[0])

    def test_3_worker_und_auftrag(self):
        bo = AuftragStore(Path(tempfile.mkdtemp()) / "bo.jsonl")
        aid = bo.anlegen("Test", art="roh", lokal_modell="qwen3.5:27b")
        self.assertEqual(bo.get(aid)["lokal_modell"], "qwen3.5:27b")
        from backoffice import worker
        neu, alt = mock.Mock(modell="qwen3.5:27b"), mock.Mock(modell="qwen3:30b-a3b")
        neu.antwort.return_value = alt.antwort.return_value = "Eine brauchbare Antwort."
        alt.mit_modell.return_value = neu
        d = worker.verarbeite({"id": "BO-1", "art": "roh", "aufgabe": "x", "lokal_modell": "qwen3.5:27b"}, alt, lambda a, t: "")
        self.assertEqual((d["ok"], d["modell"]), (True, "qwen3.5:27b"))
        alt.mit_modell.side_effect = ValueError("ungueltiger Modellname")
        self.assertIn("Modell nicht verfuegbar", worker.verarbeite({"id": "BO-2", "art": "roh", "aufgabe": "x", "lokal_modell": "x;y"}, alt, None)["grund"])
        o = worker.Ollama("http://localhost:11434", "qwen3:30b-a3b")
        with self.assertRaises(ValueError):
            o.mit_modell("x; rm -rf /")


class TestGitHubSchluessel(unittest.TestCase):
    def test_4_ungueltiger_schluessel(self):
        from orchestrator.governance.github_watch import GitHubWatch
        aufrufe = []

        def oeffnen(req, timeout=15):
            aufrufe.append(req.headers.get("Authorization"))
            if req.headers.get("Authorization"):
                raise urllib.error.HTTPError(req.full_url, 401, "Bad credentials", {}, io.BytesIO(b""))
            return io.BytesIO(json.dumps({"items": [{"full_name": "a/b", "html_url": "u", "stargazers_count": 50}]}).encode())
        gh = GitHubWatch({"GITHUB_TOKEN": "kaputt"})
        with mock.patch("urllib.request.urlopen", side_effect=oeffnen):
            r = gh.trending("agent-skills", min_stars=20)
        self.assertEqual(([x.name for x in r], gh.schluessel_ungueltig, aufrufe), (["a/b"], True, ["Bearer kaputt", None]))


class TestBotUndApi(unittest.TestCase):
    def test_5_radar_lauf_und_api(self):
        from orchestrator.channels.telegram import bot
        r = mr.Radar(Path(tempfile.mkdtemp()) / "radar")
        r.aa_speichern(AA, "2026-10-16T07:00:00")
        gesendet, antraege = [], mock.Mock()
        abruf = lambda url, kopf=None: BIB if url == mr.OLLAMA_BIBLIOTHEK else (_ for _ in ()).throw(OSError("aus"))
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append(p["text"])), \
                mock.patch.object(bot, "_modell_radar", return_value=r), mock.patch.object(mr, "QUELLEN", []):
            sec = {"LOCAL_LLM_MODEL": "qwen3:30b-a3b"}
            bot.radar_lauf("T", "1", sec, antraege=antraege, jetzt=datetime(2026, 10, 16, 7), abruf=abruf, suche=lambda q: [], cfg={})
            bot.radar_lauf("T", "1", sec, antraege=antraege, jetzt=datetime(2026, 10, 17, 7), abruf=abruf, suche=lambda q: [], cfg={})
        self.assertEqual(antraege.stellen.call_count, 1)                                 # Vorschlag nur einmal
        self.assertIn("Lokales Modell testen", antraege.stellen.call_args.args[0])
        self.assertTrue(any("qwen3.5:27b" in g for g in gesendet))
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        root = Path(tempfile.mkdtemp())
        (root / "radar").mkdir()
        for n in ("aa.json", "ollama.json"):
            (root / "radar" / n).write_text((r.dir / n).read_text(encoding="utf-8"), encoding="utf-8")
        bo = AuftragStore(root / "bo.jsonl")
        c = TestClient(webapp.app)
        with mock.patch.object(webapp, "_google_secrets", return_value={"LOCAL_LLM_MODEL": "qwen3:30b-a3b"}), \
                mock.patch.object(webapp, "ROOT", root), mock.patch.object(webapp, "_backoffice_store", return_value=bo):
            d = c.get("/api/modell-radar").json()
            self.assertEqual(([k["modell"] for k in d["lokal"]["kandidaten"]], d["lokal"]["unser"]["iq"]), (["qwen3.5:27b"], 40.0))
            t = c.post("/api/modell-radar/lokal-test", json={"modell": "qwen3.5:27b"}).json()
            self.assertTrue(t["ok"], t)
            self.assertEqual(len([a for a in bo.list("neu") if a.get("lokal_modell") == "qwen3.5:27b"]), len(mr.STANDARD_PRUEFFAELLE))
            self.assertEqual(c.get("/api/modell-radar").json()["lokal"]["tests"][0]["status"], "laeuft")
            self.assertFalse(c.post("/api/modell-radar/lokal-test", json={"modell": "x y"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
