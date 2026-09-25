"""Self-Checks BF-18: ungueltiger API-Schluessel loest den Fallback aus, Chat-Fehler werden protokolliert."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core.aktivitaet import Aktivitaet
from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_conversation import HoaConversation
from orchestrator.core.hoa_tools import ToolContext
from orchestrator.core.model_router import ModelRouter, _ist_fallback_fehler, btext
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]
# So meldet das Anthropic-SDK einen ungueltigen Schluessel (nachgestellt am 2026-09-25).
FEHLER_401 = ("Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', "
              "'message': 'API key is invalid.'}, 'request_id': None}")


class AuthenticationError(Exception):
    pass


class _Anthro:
    def __init__(self, exc):
        self.exc, self.messages = exc, self

    def create(self, **kw):
        raise self.exc


def _fake_openai(text):
    class _Client:
        def __init__(self, *a, **kw):
            self.chat = self.completions = self

        def create(self, **kw):
            msg = types.SimpleNamespace(content=text, tool_calls=None)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg, finish_reason="stop")],
                                         usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1))
    mod = types.ModuleType("openai")
    mod.OpenAI = _Client
    return mock.patch.dict(sys.modules, {"openai": mod})


class TestChatFallback(unittest.TestCase):
    def test_1_401_ist_fallback_grund(self):
        self.assertTrue(_ist_fallback_fehler(AuthenticationError(FEHLER_401)))
        self.assertFalse(_ist_fallback_fehler(ValueError("tool_use ids ohne tool_result")))

    def test_2_router_401_dann_gemini(self):
        gemini = {"name": "gemini", "key": "g", "base_url": None, "model": "gemini-2.5-flash"}
        with _fake_openai("Hallo CEO"):
            out = ModelRouter(_Anthro(AuthenticationError(FEHLER_401)), anthropic_model="m",
                              fallbacks=[gemini]).create(system="s", tools=[], messages=[])
        self.assertEqual((out.provider, btext(out.content[0])), ("gemini", "Hallo CEO"))

    def test_3_chat_fehler_wird_protokolliert(self):
        akt = Aktivitaet(Path(tempfile.mkdtemp()) / "log.jsonl")
        core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())
        ctx = ToolContext(core=core, antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], aktivitaet=akt)
        conv = HoaConversation(ctx, client=_Anthro(RuntimeError("kaputt 500")))   # kein Fallback konfiguriert
        antwort = conv.respond("Hallo")
        self.assertIn("technischen Fehler", antwort)
        e = akt.letzte(1)[0]
        self.assertEqual((e["akteur"], e["kategorie"]), ("LUNA-Chat", "fehler"))
        self.assertIn("RuntimeError: kaputt 500", e["detail"])


if __name__ == "__main__":
    unittest.main()
