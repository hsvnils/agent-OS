"""Self-Checks lokales LLM (M6, core/lokal_llm.py) -- offline, OpenAI-Client gefakt, kein Netz."""
import sys
import types
import unittest
from unittest import mock

from orchestrator.core import lokal_llm
from orchestrator.core.backends import FallbackBackend
from orchestrator.core.kosten import _provider, schaetze_eur
from orchestrator.core.model_router import ModelRouter, btext

LOKAL = {"LOCAL_LLM_BASE_URL": "http://192.168.178.184:11434/v1", "LOCAL_LLM_MODEL": "qwen3:30b-a3b"}


def _fake_openai(antworten, aufrufe):
    """openai-Modul-Ersatz: liefert je Aufruf den naechsten Eintrag aus `antworten` (Text/Exception)."""
    class _Msg:
        def __init__(self, content):
            self.content, self.tool_calls = content, None

    class _Choice:
        def __init__(self, content):
            self.message, self.finish_reason = _Msg(content), ("length" if not content else "stop")

    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]
            self.usage = types.SimpleNamespace(prompt_tokens=10, completion_tokens=5)

    class _Client:
        def __init__(self, *a, **kw):
            self.kw = kw
            self.chat = self
            self.completions = self

        def create(self, **kw):
            aufrufe.append({"model": kw["model"], "max_tokens": kw["max_tokens"], "client": self.kw})
            a = antworten.pop(0)
            if isinstance(a, Exception):
                raise a
            return _Resp(a)

    mod = types.ModuleType("openai")
    mod.OpenAI = _Client
    return mock.patch.dict(sys.modules, {"openai": mod})


class _Anthro:
    def __init__(self, exc=None):
        self.exc, self.aufrufe, self.messages = exc, 0, self

    def create(self, **kw):
        self.aufrufe += 1
        if self.exc:
            raise self.exc
        return types.SimpleNamespace(content=[{"type": "text", "text": "cloud"}], usage=None)


class _Primary:
    def __init__(self, exc=None):
        self.exc, self.aufrufe = exc, 0

    def respond(self, *a):
        self.aufrufe += 1
        if self.exc:
            raise self.exc
        return "cli"


class TestLokalLLM(unittest.TestCase):
    def test_1_ohne_konfiguration_kein_eintrag(self):
        self.assertIsNone(lokal_llm.eintrag({}, "chat"))
        self.assertIsNone(lokal_llm.eintrag(LOKAL, "chat"))                      # Modus fehlt = aus
        self.assertIsNone(lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "aus"}, "chat"))
        self.assertIsNone(lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "vielleicht"}, "chat"))
        self.assertFalse(lokal_llm.aktiv(LOKAL))

    def test_2_eintrag_mit_standardwerten(self):
        e = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_FACHAGENTEN": "zuerst"}, "fachagenten")
        self.assertEqual((e["name"], e["model"], e["zuerst"]), ("lokal", "qwen3:30b-a3b", True))
        self.assertEqual((e["timeout"], e["max_tokens"], e["max_retries"]), (300.0, 4096, 0))
        self.assertFalse(lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "zuletzt"}, "chat")["zuerst"])
        self.assertIsNone(lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_FACHAGENTEN": "zuerst"}, "chat"))

    def test_3_schalter_aus_fallback_kette_unveraendert(self):
        from orchestrator.channels.telegram.bot import _fallbacks
        secrets = {"GEMINI_API_KEY": "g", "OPENAI_API_KEY": "o", **LOKAL}
        for bereich in ("chat", "fachagenten"):
            namen = [f["name"] for f in _fallbacks(secrets, {}, bereich=bereich)]
            self.assertEqual(namen, ["gemini", "openai"])
        namen = [f["name"] for f in _fallbacks({**secrets, "LOCAL_LLM_CHAT": "zuerst"}, {}, bereich="chat")]
        self.assertEqual(namen, ["gemini", "openai", "lokal"])

    def test_4_denktext_wird_entfernt(self):
        self.assertEqual(lokal_llm.ohne_denktext("<think>hmm\nnaja</think>\n\nHallo CEO"), "Hallo CEO")
        self.assertEqual(lokal_llm.ohne_denktext(None), "")

    def test_5_router_lokal_zuerst_spart_anthropic(self):
        anthro, aufrufe = _Anthro(), []
        fb = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "zuerst"}, "chat")
        with _fake_openai(["<think>x</think>lokal"], aufrufe):
            out = ModelRouter(anthro, anthropic_model="m", fallbacks=[fb]).create(system="s", tools=[], messages=[])
        self.assertEqual((out.provider, btext(out.content[0]), anthro.aufrufe), ("lokal", "lokal", 0))
        self.assertEqual(aufrufe[0]["max_tokens"], 4096)
        self.assertEqual((aufrufe[0]["client"]["timeout"], aufrufe[0]["client"]["max_retries"]), (300.0, 0))

    def test_6_router_lokal_scheitert_dann_anthropic(self):
        anthro, aufrufe = _Anthro(), []
        fb = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "zuerst"}, "chat")
        with _fake_openai([ConnectionError("Connection refused")], aufrufe):
            out = ModelRouter(anthro, anthropic_model="m", fallbacks=[fb]).create(system="s", tools=[], messages=[])
        self.assertEqual((out.provider, anthro.aufrufe), ("anthropic", 1))

    def test_7_router_leere_antwort_ist_fehler(self):
        # Denkschritte fressen max_tokens -> leerer Inhalt darf nicht als Antwort durchgehen.
        anthro, aufrufe = _Anthro(), []
        fb = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "zuerst"}, "chat")
        with _fake_openai([""], aufrufe):
            out = ModelRouter(anthro, anthropic_model="m", fallbacks=[fb]).create(system="s", tools=[], messages=[])
        self.assertEqual(out.provider, "anthropic")

    def test_8_router_verbindungsfehler_bei_anthropic_loest_fallback_aus(self):
        anthro, aufrufe = _Anthro(RuntimeError("Connection error.")), []
        fb = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_CHAT": "zuletzt"}, "chat")
        with _fake_openai(["lokal"], aufrufe):
            out = ModelRouter(anthro, anthropic_model="m", fallbacks=[fb]).create(system="s", tools=[], messages=[])
        self.assertEqual(out.provider, "lokal")

    def test_9_backend_lokal_zuerst_und_rueckfall(self):
        fb = lokal_llm.eintrag({**LOKAL, "LOCAL_LLM_FACHAGENTEN": "zuerst"}, "fachagenten")
        prim, aufrufe = _Primary(), []
        with _fake_openai(["Bewertung lokal"], aufrufe):
            self.assertEqual(FallbackBackend(prim, fallbacks=[fb]).respond("cfo", "s", "m", {}), "Bewertung lokal")
        self.assertEqual(prim.aufrufe, 0)
        prim, aufrufe = _Primary(), []
        with _fake_openai([TimeoutError("timed out")], aufrufe):
            self.assertEqual(FallbackBackend(prim, fallbacks=[fb]).respond("cfo", "s", "m", {}), "cli")
        self.assertEqual(prim.aufrufe, 1)

    def test_10_kosten_lokal_null(self):
        self.assertEqual(_provider("qwen3:30b-a3b"), "lokal")
        self.assertEqual(schaetze_eur("qwen3:30b-a3b", 1_000_000, 1_000_000), 0.0)
        self.assertGreater(schaetze_eur("unbekannt", 1_000_000, 1_000_000), 0.0)   # unveraendert fuer Cloud

    def test_11_health_check(self):
        ok, hinweis = lokal_llm.erreichbar("http://127.0.0.1:9/v1", timeout=1)
        self.assertFalse(ok)
        self.assertIn("nicht erreichbar", hinweis)
        from orchestrator.core.self_maintenance import SelfMaintenance
        komp = [c["komponente"] for c in SelfMaintenance(secrets=LOKAL).pruefe()]
        self.assertNotIn("Lokales LLM (Ollama, MACO470)", komp)                  # nicht aktiv -> kein Check
        sm = SelfMaintenance(secrets={**LOKAL, "LOCAL_LLM_BASE_URL": "http://127.0.0.1:9/v1",
                                      "LOCAL_LLM_CHAT": "zuletzt"})
        eintrag = [c for c in sm.pruefe() if c["komponente"] == "Lokales LLM (Ollama, MACO470)"]
        self.assertEqual(len(eintrag), 1)
        self.assertFalse(eintrag[0]["ok"])


if __name__ == "__main__":
    unittest.main()
