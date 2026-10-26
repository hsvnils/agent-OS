"""NETZ_AGENT Q2: Ergebnis-Formular (Claude Haiku 5.5 ohne Werkzeuge, festes Schema, Quellen nur aus den Suchtreffern) und
zweiter Suchversuch bei Namensaufloesungs-Fehlern (BF-73)."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from netz_agent import agent as ag
from netz_agent import formular

TREFFER = [{"titel": "Agentur A", "url": "https://a.example/preise", "auszug": "Reel ab 500 EUR"},
           {"titel": "Agentur B", "url": "https://b.example/", "auszug": "Paket 1.200 EUR"}]


class _Client:
    def __init__(self, daten=None, fehler=None):
        self.aufrufe, self.daten, self.fehler = [], daten, fehler
        self.messages = self

    def create(self, **kw):
        self.aufrufe.append(kw)
        if self.fehler:
            raise self.fehler
        return SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=900, output_tokens=120),
                               content=[SimpleNamespace(type="text", text=json.dumps(self.daten))])


class TestFormular(unittest.TestCase):
    def test_1_pruefung(self):
        f = formular.pruefe({"antwort": "x" * 5000, "unsicher": False, "grund": "",
                             "fakten": [{"text": "Reel ab 500 EUR", "quelle": 1}, {"text": "erfunden", "quelle": 7},
                                        {"text": "y" * 900, "quelle": 2}] + [{"text": "z", "quelle": 1}] * 20}, TREFFER)
        self.assertEqual(len(f["antwort"]), formular.MAX_ANTWORT)
        self.assertEqual(len(f["fakten"]), formular.MAX_FAKTEN)
        self.assertNotIn("erfunden", [x["text"] for x in f["fakten"]])          # Quelle 7 gibt es nicht
        self.assertTrue(all(len(x["text"]) <= formular.MAX_FAKT for x in f["fakten"]))
        self.assertEqual([q["url"] for q in f["quellen"]], ["https://a.example/preise", "https://b.example/"])
        leer = formular.pruefe({"antwort": "?", "fakten": [], "unsicher": False, "grund": ""}, TREFFER)
        self.assertTrue(leer["unsicher"])

    def test_2_modellaufruf_ohne_werkzeuge(self):
        c = _Client({"antwort": "Reels kosten ab 500 EUR.", "fakten": [{"text": "Reel ab 500 EUR", "quelle": 1}],
                     "unsicher": False, "grund": ""})
        f = formular.erstellen("Preise Stadion-Reels?", TREFFER, [{"url": TREFFER[0]["url"], "text": "Seitentext"}], client=c)
        kw = c.aufrufe[0]
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertNotIn("tools", kw)
        self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")
        self.assertIn("NIE", kw["system"])
        self.assertIn("[1] Agentur A\nSeitentext", kw["messages"][0]["content"])
        self.assertEqual((f["antwort"], f["token"]), ("Reels kosten ab 500 EUR.", [900, 120]))

    def test_3_agent_mit_formular_und_fehler(self):
        q = Path(tempfile.mkdtemp())
        for client, erwartet in ((_Client({"antwort": "A", "fakten": [{"text": "F", "quelle": 1}], "unsicher": False, "grund": ""}), "A"),
                                 (_Client(fehler=RuntimeError("Limit")), None)):
            a = ag.Agent(q, "s", suche=lambda f, s: TREFFER, hole=lambda u: {"url": u, "titel": "", "text": "t", "status": 200},
                         modell_client=client)
            e = a.bearbeite({"id": "auftrag-0001", "art": "suche", "frage": "x", "max_seiten": 1})
            self.assertTrue(e["ok"])
            if erwartet:
                self.assertEqual(e["formular"]["antwort"], erwartet)
            else:
                self.assertIn("Limit", e["formular"]["fehler"])            # Rohdaten gehen trotzdem zurueck

    def test_4_zweiter_suchversuch(self):
        antwort = json.dumps({"web": {"results": [{"title": "T", "url": "https://x.example/", "description": "d"}]}}).encode()
        aufrufe = []

        def oeffnen(req, timeout=0):
            aufrufe.append(1)
            if len(aufrufe) == 1:
                raise urllib.error.URLError("Temporary failure in name resolution")
            return io.BytesIO(antwort)
        with mock.patch("urllib.request.urlopen", side_effect=oeffnen):
            t = ag.brave_suche("frage", "s", pause=0)
        self.assertEqual((len(aufrufe), t[0]["url"]), (2, "https://x.example/"))


if __name__ == "__main__":
    unittest.main()
