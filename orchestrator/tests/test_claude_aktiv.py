"""CLAUDE_AKTIV C1 (CEO 2026-10-23): Chat/Fachagenten auf Sonnet 5.5, Routing auf Haiku 5.5; Sonnet 5.5 denkt immer mit
(Aufwand low, genug max_tokens, veraenderte Verlaeufe -> Denk-Bloecke verwerfen statt 400); Reihenfolge Claude -> lokal ->
Gemini; Preise fuer die neuen Modelle; Anthropic-Websuche bleibt aus."""
import tomllib
import unittest
from pathlib import Path

from orchestrator.core import kosten
from orchestrator.core.model_router import BINDUNG_BETA, ModelRouter, claude_einstellungen

ROOT = Path(__file__).resolve().parents[1]


class _Antwort:
    content = [{"type": "text", "text": "Hallo CEO"}]
    usage = None


class _Anthro:
    def __init__(self):
        self.aufrufe = []
        self.messages = self

    def create(self, **kw):
        self.aufrufe.append(kw)
        return _Antwort()


class TestClaudeAktiv(unittest.TestCase):
    def test_1_konfiguration(self):
        cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual({k: cfg["models"][k] for k in ("hoa", "cto", "berater", "routing")},
                         {"hoa": "claude-sonnet-5-5", "cto": "claude-sonnet-5-5", "berater": "claude-sonnet-5-5",
                          "routing": "claude-haiku-5-5"})
        self.assertEqual((cfg["voice"]["llm_model"], cfg["voice"]["chat_effort"]), ("claude-sonnet-5-5", "low"))

    def test_2_router_sonnet_55(self):
        a = _Anthro()
        out = ModelRouter(a, anthropic_model="claude-sonnet-5-5", effort="low").create(system="s", tools=[], messages=[])
        self.assertEqual(out.provider, "anthropic")
        kw = a.aufrufe[0]
        self.assertEqual(kw["thinking"], {"type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "drop_block"}})
        self.assertEqual(kw["output_config"], {"effort": "low"})
        self.assertEqual(kw["extra_headers"], {"anthropic-beta": BINDUNG_BETA})
        self.assertGreaterEqual(kw["max_tokens"], 8000)                       # Denken zaehlt zu max_tokens
        self.assertNotIn("temperature", kw)
        alt = claude_einstellungen("claude-sonnet-4-6", 1024, "low")          # aeltere Modelle unveraendert
        self.assertEqual(alt, {"max_tokens": 1024})
        self.assertIn("thinking", claude_einstellungen("claude-haiku-5-5", 1024, "low"))

    def test_3_reihenfolge_und_preise(self):
        from orchestrator.channels.telegram.bot import _fallbacks
        s = {"GEMINI_API_KEY": "g", "OPENAI_API_KEY": "o", "LOCAL_LLM_BASE_URL": "http://x:11434/v1",
             "LOCAL_LLM_MODEL": "qwen3:14b", "LOCAL_LLM_CHAT": "zuletzt"}
        self.assertEqual([f["name"] for f in _fallbacks(s, {}, bereich="chat")], ["lokal", "gemini", "openai"])
        self.assertEqual(kosten._rate("claude-haiku-5-5"), (0.10, 0.50))
        self.assertEqual(kosten._rate("claude-sonnet-5-5"), (2.0, 10.0))
        self.assertAlmostEqual(kosten.schaetze_eur("claude-sonnet-5-5", 1_000_000, 0), round(2.0 * kosten.USD_TO_EUR, 4))

    def test_4_keine_anthropic_websuche(self):
        from orchestrator.governance.web_research import WebResearch
        w = WebResearch.from_env({"ANTHROPIC_API_KEY": "sk-ant-gueltig-aussehend", "WEB_RESEARCH_ANTHROPIC": "1",
                                  "BRAVE_API_KEY": "b"})
        self.assertFalse(w.komplex.verfuegbar())


if __name__ == "__main__":
    unittest.main()
