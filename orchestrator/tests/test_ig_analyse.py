"""Collab-Radar Phase 2: KI-Analyse -- Parsing, Store-Lauf, Provider-Wahl (LLM gemockt)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.ig_analyse import IgAnalyzer, analyse_llm_aus_env
from orchestrator.core.ig_inbox import IgInboxStore


def fake_llm(antwort):
    def call(system, user):
        return antwort
    return call


class TestIgAnalyzer(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = IgInboxStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_json_parsing_und_normalisierung(self):
        roh = ('Klar! {"collab": true, "zusammenfassung": "Reels-Kooperation", "stand": "Angebot offen", '
               '"offene_todos": "Angebot senden", "warten_auf": "UNS"} -- fertig')   # Text drumherum + String-Todo
        az = IgAnalyzer(llm=fake_llm(roh), modell="test")
        r = az.analysiere([{"richtung": "ein", "text": "Wollen wir kooperieren?", "medien": False}])
        self.assertTrue(r["collab"])
        self.assertEqual(r["zusammenfassung"], "Reels-Kooperation")
        self.assertEqual(r["offene_todos"], ["Angebot senden"])   # String -> Liste
        self.assertEqual(r["warten_auf"], "uns")                  # normalisiert kleingeschrieben
        self.assertEqual(r["modell"], "test")

    def test_leerer_verlauf_ohne_llm_aufruf(self):
        def boom(s, u):
            raise AssertionError("LLM darf bei leerem Verlauf nicht gerufen werden")
        az = IgAnalyzer(llm=boom, modell="test")
        r = az.analysiere([{"richtung": "aus", "text": "", "medien": True}])   # nur Medien -> kein Transkript
        self.assertFalse(r["collab"])
        self.assertEqual(r["warten_auf"], "niemand")

    def test_analysiere_store_nur_neue(self):
        self.store.nachricht_hinzu("U1", "co", richtung="ein", text="Collab-Anfrage", medien=False,
                                   extern_id="m1", ts_msg="2026-06-01T10:00:00+0000")
        az = IgAnalyzer(llm=fake_llm('{"collab": true, "zusammenfassung":"x", "warten_auf":"uns"}'), modell="test")
        r1 = az.analysiere_store(self.store)
        self.assertEqual((r1["analysiert"], r1["collab"]), (1, 1))
        self.assertTrue(self.store.zustand("U1")["analyse"]["collab"])
        # zweiter Lauf: nichts Neues -> uebersprungen
        r2 = az.analysiere_store(self.store)
        self.assertEqual((r2["analysiert"], r2["uebersprungen"]), (0, 1))
        # neue Nachricht -> wieder analysiert
        self.store.nachricht_hinzu("U1", "co", richtung="ein", text="Noch da?", medien=False,
                                   extern_id="m2", ts_msg="2026-06-05T10:00:00+0000")
        self.assertEqual(az.analysiere_store(self.store)["analysiert"], 1)

    def test_nicht_verfuegbar_ohne_llm(self):
        r = IgAnalyzer(llm=None, modell="test").analysiere_store(self.store)
        self.assertFalse(r["ok"])

    def test_provider_wahl_aus_env(self):
        # Ohne passenden Key -> None
        self.assertIsNone(analyse_llm_aus_env({"IG_ANALYSE_MODELL": "gemini-flash-latest"}))
        self.assertIsNone(analyse_llm_aus_env({"IG_ANALYSE_MODELL": "claude-haiku-4-5"}))
        # Mit Key -> Callable (baut nur den Client, ruft nichts)
        self.assertTrue(callable(analyse_llm_aus_env({"IG_ANALYSE_MODELL": "gemini-flash-latest",
                                                      "GEMINI_API_KEY": "x"})))
        self.assertTrue(callable(analyse_llm_aus_env({"IG_ANALYSE_MODELL": "gpt-5",
                                                      "OPENAI_API_KEY": "x"})))
        self.assertTrue(callable(analyse_llm_aus_env({"IG_ANALYSE_MODELL": "claude-haiku-4-5",
                                                      "ANTHROPIC_API_KEY": "x"})))


if __name__ == "__main__":
    unittest.main()
