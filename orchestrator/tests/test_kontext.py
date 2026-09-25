"""Self-Checks Kontext-Management (Etappe 3b, core/kontext.py) -- offline, ohne LLM."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_conversation import HoaConversation
from orchestrator.core.hoa_tools import ToolContext
from orchestrator.core.kontext import pausen_notiz, verdichte, wechsel_starts
from orchestrator.core.lokal_llm import geschaetzte_tokens
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


def _wechsel(nr: int, ergebnis_zeichen: int = 5000) -> list[dict]:
    """Ein Wechsel: CEO-Frage -> Werkzeug-Aufruf -> (grosses) Ergebnis -> Antwort."""
    return [
        {"role": "user", "content": f"Frage {nr}"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": f"t{nr}", "name": "antraege_zeigen", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{nr}", "content": "x" * ergebnis_zeichen}]},
        {"role": "assistant", "content": [{"type": "text", "text": f"Antwort {nr}"}]},
    ]


def _paare_intakt(messages: list[dict]) -> bool:
    ids_use = [b["id"] for m in messages if isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_use"]
    ids_res = [b["tool_use_id"] for m in messages if isinstance(m["content"], list) for b in m["content"]
               if b.get("type") == "tool_result"]
    return ids_use == ids_res


class TestKontext(unittest.TestCase):
    def test_1_passt_bleibt_unveraendert(self):
        m = _wechsel(1, 100)
        self.assertIs(verdichte(m, 10_000), m)

    def test_2_alte_ergebnisse_werden_gekuerzt_laufender_wechsel_nicht(self):
        m = _wechsel(1) + _wechsel(2) + _wechsel(3)
        vorher = geschaetzte_tokens(m)
        out = verdichte(m, vorher - 500)
        self.assertEqual(len(out), len(m))                                  # nichts entfernt, nur gekuerzt
        self.assertIn("[gekuerzt, 5000 Zeichen", out[2]["content"][0]["content"])
        self.assertEqual(out[-2]["content"][0]["content"], "x" * 5000)       # laufender Wechsel vollstaendig
        self.assertTrue(_paare_intakt(out))

    def test_3_aelteste_wechsel_fallen_gleitend_heraus(self):
        m = []
        for i in range(1, 11):
            m += _wechsel(i, 200)
        out = verdichte(m, geschaetzte_tokens(m) // 3)
        self.assertLess(geschaetzte_tokens(out), geschaetzte_tokens(m) // 3 + 1)
        self.assertEqual(out[0], {"role": "user", "content": out[0]["content"]})
        self.assertIsInstance(out[0]["content"], str)                        # beginnt mit echter CEO-Frage
        self.assertEqual(out[-4]["content"], "Frage 10")                     # neuester Wechsel bleibt
        self.assertTrue(_paare_intakt(out))

    def test_4_laufender_wechsel_wird_nie_zerrissen(self):
        m = _wechsel(1, 50_000)
        out = verdichte(m, 10)
        self.assertEqual(out, m)
        self.assertEqual(wechsel_starts(out), [0])

    def test_5_pausen_notiz(self):
        m = _wechsel(1) + _wechsel(2)
        n = pausen_notiz(m, 2)
        self.assertIn("Frage 2", n)
        self.assertIn("Antwort 2", n)
        self.assertEqual(pausen_notiz([], 2), "")

    def test_6_conversation_pause_und_budget(self):
        core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())
        ctx = ToolContext(core=core, antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[],
                          secret_dict={"LOCAL_LLM_KONTEXT": "32768", "CHAT_PAUSE_STUNDEN": "2"})
        gesehen = []

        class _Client:
            def __init__(self):
                self.messages = self

            def create(self, **kw):
                gesehen.append([dict(m) for m in kw["messages"]])
                return type("R", (), {"content": [{"type": "text", "text": "ok"}], "usage": None})()

        conv = HoaConversation(ctx, client=_Client())
        self.assertGreater(conv.verlauf_budget, 5000)                       # 32k-Fenster -> Platz fuer Verlauf
        conv.respond("Erste Frage")
        conv.respond("Zweite Frage")
        self.assertEqual(len(gesehen[-1]), 3)                               # Verlauf bleibt innerhalb der Pause
        conv.letzte_nachricht -= 3 * 3600                                   # 3 Stunden Stille
        conv.respond("Wie gesagt, und jetzt?")
        self.assertEqual(len(gesehen[-1]), 1)                               # neue Sitzung ...
        self.assertIn("Zweite Frage", gesehen[-1][0]["content"])            # ... mit Notiz zur letzten
        self.assertIn("Wie gesagt, und jetzt?", gesehen[-1][0]["content"])


if __name__ == "__main__":
    unittest.main()
