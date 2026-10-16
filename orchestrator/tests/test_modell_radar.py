"""MODELL_RADAR R1-R3 (CEO 2026-10-13): Hersteller-News (Feeds, Seiten, Aenderungsprotokolle) regelbasiert eingestuft,
Artificial-Analysis-Vergleich mit Vorschlaegen als Antrag (nie automatisch), Wochenbericht, Uebersicht nur fuer Admins."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from orchestrator.core import modell_radar as mr

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>X</title>
<item><title>Introducing Mistral Large 4</title><link>https://mistral.ai/news/mistral-large-4/</link><pubDate>Tue, 06 Oct 2026 12:00:27 GMT</pubDate><description>&lt;p&gt;Neues Modell&lt;/p&gt;</description></item>
<item><title>Hallo, Deutschland!</title><link>https://mistral.ai/news/hallo-deutschland/</link></item></channel></rss>"""
ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Releases</title>
<entry><title>v0.40.4</title><link rel="alternate" href="https://github.com/ollama/ollama/releases/tag/v0.40.4"/><updated>2026-10-10T10:00:00Z</updated></entry>
<entry><title>v0.40.5-rc0</title><link rel="alternate" href="https://github.com/ollama/ollama/releases/tag/v0.40.5-rc0"/></entry></feed>"""
SEITE = """<a href="/news/claude-sonnet-6" class="x"><span>Introducing Claude Sonnet 6</span></a><a href="/news/claude-sonnet-6">Read</a>
<a href="/news/policy-update">FEATURED</a>"""
CHANGELOG = """<h2>October 8, 2026</h2><p>Gemini 3.7 Flash deprecation: gemini-3.7-flash will be shut down.</p>
<h2>October 6, 2026</h2><p>gemini-2.5-flash will be shut down on December 1, 2026. Migrate to a newer model.</p>
<div>Oct 3</div><div>Update</div><div>gpt-4o-mini-tts has a new voice.</div>"""
UNSERE = [{"einsatz": "Chat-Rückfall Gemini", "modell": "gemini-2.5-flash"}, {"einsatz": "Chat-Rückfall OpenAI", "modell": "gpt-4o-mini"},
          {"einsatz": "Lokal (MACO470)", "modell": "qwen3:14b"}]
AA = {"status": 200, "data": [
    {"name": "Gemini 2.5 Flash", "slug": "gemini-2-5-flash", "model_creator": {"name": "Google"},
     "evaluations": {"artificial_analysis_intelligence_index": 50}, "pricing": {"price_1m_blended_3_to_1": 1.0, "price_1m_input_tokens": 0.5, "price_1m_output_tokens": 2.5},
     "median_output_tokens_per_second": 200},
    {"name": "Billig Flash", "slug": "billig-flash", "model_creator": {"name": "Mistral"},
     "evaluations": {"artificial_analysis_intelligence_index": 51}, "pricing": {"price_1m_blended_3_to_1": 0.4, "price_1m_input_tokens": 0.2, "price_1m_output_tokens": 1.0},
     "median_output_tokens_per_second": 150},
    {"name": "Klug Pro", "slug": "klug-pro", "model_creator": {"name": "OpenAI"},
     "evaluations": {"artificial_analysis_intelligence_index": 60}, "pricing": {"price_1m_blended_3_to_1": 1.05, "price_1m_input_tokens": 0.5, "price_1m_output_tokens": 2.7},
     "median_output_tokens_per_second": 90},
    {"name": "Fremd", "slug": "fremd", "model_creator": {"name": "Unbekannt AG"},
     "evaluations": {"artificial_analysis_intelligence_index": 90}, "pricing": {"price_1m_blended_3_to_1": 0.01}}]}
QUELLEN = [{"id": "mistral", "hersteller": "Mistral", "art": "feed", "url": "https://mistral.ai/news/rss"},
           {"id": "ollama", "hersteller": "Ollama", "art": "feed", "url": "https://github.com/x.atom", "release": True},
           {"id": "anthropic", "hersteller": "Anthropic", "art": "links", "url": "https://www.anthropic.com/news", "muster": r"/news/[a-z0-9-]+", "basis": "https://www.anthropic.com"},
           {"id": "gemini-api", "hersteller": "Google", "art": "changelog", "url": "https://ai.google.dev/changelog"},
           {"id": "kaputt", "hersteller": "X", "art": "feed", "url": "https://kaputt.example/rss"}]


class TestParser(unittest.TestCase):
    def test_1_feeds_seiten_changelog(self):
        f = mr.lies_feed(RSS)
        self.assertEqual([(x["titel"], x["link"]) for x in f], [("Introducing Mistral Large 4", "https://mistral.ai/news/mistral-large-4/"),
                                                              ("Hallo, Deutschland!", "https://mistral.ai/news/hallo-deutschland/")])
        self.assertEqual(f[0]["anriss"], "Neues Modell")
        self.assertEqual([x["link"] for x in mr.lies_feed(ATOM)], ["https://github.com/ollama/ollama/releases/tag/v0.40.4",
                                                                  "https://github.com/ollama/ollama/releases/tag/v0.40.5-rc0"])
        s = mr.lies_links(SEITE, r"/news/[a-z0-9-]+", "https://www.anthropic.com")
        self.assertEqual([(x["titel"], x["link"]) for x in s], [("Introducing Claude Sonnet 6", "https://www.anthropic.com/news/claude-sonnet-6"),
                                                              ("Policy update", "https://www.anthropic.com/news/policy-update")])
        c = mr.lies_changelog(CHANGELOG, "https://ai.google.dev/changelog")
        self.assertEqual([x["datum"] for x in c], ["October 8, 2026", "October 6, 2026", "Oct 3"])
        self.assertIn("gemini-2.5-flash will be shut down", c[1]["anriss"])

    def test_2_einstufung(self):
        q = {"art": "feed", "hersteller": "Google"}
        c = mr.lies_changelog(CHANGELOG, "u")
        stufen = [mr.einstufen(x, {"art": "changelog"}, UNSERE) for x in c]
        self.assertEqual(stufen, [("gelb", []), ("rot", ["gemini-2.5-flash"]), ("gelb", [])])   # 3.7 / 2.5 / -tts nicht verwechselt
        self.assertEqual(mr.einstufen({"titel": "Gemini 2.5 Flash will be retired", "anriss": ""}, q, UNSERE)[0], "rot")
        self.assertEqual(mr.einstufen({"titel": "Gemini 2.5 Flash-Lite retired", "anriss": ""}, q, UNSERE), ("gelb", []))   # nicht unser Modell -> nicht rot
        self.assertEqual(mr.einstufen({"titel": "Introducing Mistral Large 4", "anriss": ""}, q, UNSERE)[0], "gelb")
        self.assertEqual(mr.einstufen({"titel": "Customer story: Asana", "anriss": ""}, q, UNSERE)[0], "grau")
        rel = {"art": "feed", "release": True}
        self.assertEqual((mr.einstufen({"titel": "v0.40.4"}, rel, UNSERE)[0], mr.einstufen({"titel": "v0.40.5-rc0"}, rel, UNSERE)[0]), ("gelb", "grau"))
        g = mr.genutzte_modelle({"voice": {"llm_model": "claude-sonnet-5"}, "models": {"hoa": "claude-sonnet-5", "routing": "claude-haiku-4-5"}},
                                {"GEMINI_API_KEY": "x", "LOCAL_LLM_MODEL": "qwen3:14b"})
        self.assertEqual([x["modell"] for x in g], ["claude-sonnet-5", "gemini-2.5-flash", "claude-sonnet-5", "claude-haiku-4-5", "qwen3:14b", "gemini-2.5-flash"])
        self.assertNotIn("x", json.dumps(g).replace("max", ""))                                   # keine Schluesselwerte


class TestLauf(unittest.TestCase):
    def _abruf(self, url, kopf=None):
        if "kaputt" in url:
            raise OSError("weg")
        if url == mr.AA_URL:
            self.assertEqual(kopf["x-api-key"], "AAKEY")
            return json.dumps(AA)
        return {"https://mistral.ai/news/rss": RSS, "https://github.com/x.atom": ATOM, "https://www.anthropic.com/news": SEITE,
                "https://ai.google.dev/changelog": self.changelog}[url]

    def test_3_bestand_neu_fehler(self):
        r = mr.Radar(Path(tempfile.mkdtemp()) / "radar")
        self.changelog = CHANGELOG.split("<h2>October 6")[0]                                     # erster Lauf: nur 8. Oktober
        self.assertEqual(mr.lauf_news(r, UNSERE, jetzt=datetime(2026, 10, 13, 7), abruf=self._abruf, quellen=QUELLEN), [])   # Bestand
        self.assertIn("OSError", r.stand()["quellen"]["kaputt"]["fehler"])                         # Fehler stoppt die anderen nicht
        self.assertEqual(len([x for x in r.news().values() if x["bestand"]]), len(r.news()))
        self.changelog = CHANGELOG
        rot = mr.lauf_news(r, UNSERE, jetzt=datetime(2026, 10, 14, 7), abruf=self._abruf, quellen=QUELLEN)
        self.assertEqual([x["betroffen"] for x in rot], [["gemini-2.5-flash"]])
        self.assertEqual(mr.lauf_news(r, UNSERE, jetzt=datetime(2026, 10, 15, 7), abruf=self._abruf, quellen=QUELLEN), [])   # nicht doppelt
        self.assertIn("gemini-2.5-flash", mr.meldung_rot(rot))

    def test_4_artificial_analysis(self):
        aa = mr.aa_modelle(AA)
        self.assertEqual(mr.aa_finden("gemini-2.5-flash", aa)["name"], "Gemini 2.5 Flash")
        self.assertIsNone(mr.aa_finden("qwen3:14b", aa))
        v = mr.vorschlaege(UNSERE, aa)
        self.assertEqual([(x["regel"], x["neu"]["name"]) for x in v], [("guenstiger", "Billig Flash"), ("besser", "Klug Pro")])   # „Fremd“ nie
        lokal = [{"einsatz": "Lokal (MACO470)", "modell": "gemini-2.5-flash"}]                  # lokal nie gegen Cloud-Preise
        self.assertEqual(mr.vorschlaege(lokal, aa), [])
        k = mr.kostenvoranschlag(v[0], {"in": 2_000_000, "out": 1_000_000})
        self.assertIn("ca. 3.50 $ → 1.40 $ im Monat", k)
        titel, text = mr.vorschlag_text(v[0], None)
        self.assertIn("Modellwechsel prüfen", titel)
        self.assertIn("nicht erfasst", text)
        self.assertIn(mr.AA_QUELLE, text)
        r = mr.Radar(Path(tempfile.mkdtemp()) / "radar")
        self.assertEqual(len(mr.lauf_aa(r, UNSERE, schluessel="AAKEY", jetzt=datetime(2026, 10, 13, 7), abruf=self._abruf)), 2)
        self.assertEqual(mr.lauf_aa(r, UNSERE, schluessel="AAKEY", jetzt=datetime(2026, 10, 14, 7), abruf=self._abruf), [])   # je einmal


class TestBot(unittest.TestCase):
    def test_5_lauf_antraege_wochenbericht(self):
        from orchestrator.channels.telegram import bot
        r = mr.Radar(Path(tempfile.mkdtemp()) / "radar")
        gesendet, antraege = [], mock.Mock()
        antraege.list.return_value = [{"kategorie": "modell"}]
        t = TestLauf()
        t.changelog = CHANGELOG
        with mock.patch.object(bot, "_api", side_effect=lambda tk, m, p: gesendet.append(p["text"])), \
                mock.patch.object(bot, "_modell_radar", return_value=r), mock.patch.object(mr, "QUELLEN", QUELLEN[:4]), \
                mock.patch.object(bot, "_nutzung_30_tage", return_value={}):
            cfg = {"voice": {}, "models": {}}
            sec = {"GEMINI_API_KEY": "g", "OPENAI_API_KEY": "o", "ARTIFICIALANALYSIS_API_KEY": "AAKEY"}
            out = bot.radar_lauf("T", "1", sec, antraege=antraege, jetzt=datetime(2026, 10, 13, 7), abruf=t._abruf, suche=lambda q: [], cfg=cfg)
            self.assertEqual((out["rot"], out["vorschlaege"], out["bericht"]), (0, 2, False))     # Bestand still, 2 Antraege
            self.assertEqual(antraege.stellen.call_count, 2)
            self.assertEqual(antraege.stellen.call_args.kwargs["kategorie"], "modell")
            self.assertTrue(any("nie" in g.lower() or "Nichts wird automatisch" in g for g in gesendet))
            out = bot.radar_lauf("T", "1", sec, antraege=antraege, jetzt=datetime(2026, 10, 19, 9, 5), abruf=t._abruf, suche=lambda q: [],
                                 cfg=cfg, taeglich=False)                                         # Montag 09:05
            self.assertTrue(out["bericht"])
            self.assertIn("Modell-Radar – Woche", gesendet[-1])
            self.assertIn("1 Vorschlag", gesendet[-1])
            n = len(gesendet)
            self.assertFalse(bot.radar_lauf("T", "1", sec, antraege=antraege, jetzt=datetime(2026, 10, 19, 9, 15), abruf=t._abruf,
                                            suche=lambda q: [], cfg=cfg, taeglich=False)["bericht"])    # nur einmal je Woche
            self.assertEqual(len(gesendet), n)
        self.assertEqual(antraege.stellen.call_count, 2)


class TestApi(unittest.TestCase):
    def test_6_uebersicht_nur_admin(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/modell-radar"), "administration")
        c = TestClient(webapp.app)
        with mock.patch.object(webapp, "_google_secrets", return_value={"GEMINI_API_KEY": "GEHEIM123456", "ARTIFICIALANALYSIS_API_KEY": "AAGEHEIM"}), \
                mock.patch.object(webapp, "ROOT", Path(tempfile.mkdtemp())):
            d = c.get("/api/modell-radar").json()
        self.assertTrue(d["aa_aktiv"])
        self.assertIn("gemini-2.5-flash", [m["modell"] for m in d["modelle"]])
        self.assertNotIn("GEHEIM", json.dumps(d))
        self.assertIn("NVIDIA", d["hersteller"])
        self.assertIn("Microsoft", d["hersteller"])


if __name__ == "__main__":
    unittest.main()
