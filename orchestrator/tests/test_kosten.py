"""Self-Checks CFO Stufe 2 -- Token-/Kostenerfassung (offline)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.kosten import KostenStore, schaetze_eur
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


class TestKosten(unittest.TestCase):
    def test_1_schaetzung(self):
        eur = schaetze_eur("claude-haiku-4-5", 1_000_000, 1_000_000)  # 1+5 USD * 0.92
        self.assertAlmostEqual(eur, 6 * 0.92, places=2)

    def test_2_record_und_monat(self):
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        ks.record(quelle="chat", modell="claude-haiku-4-5", input_tokens=10000, output_tokens=2000)
        ks.record(quelle="chat", modell="gpt-4o", input_tokens=5000, output_tokens=1000)
        m = ks.monat()
        self.assertEqual(m["je_quelle"]["chat"]["aufrufe"], 2)
        self.assertIn("anthropic", m["je_provider"])
        self.assertIn("openai", m["je_provider"])
        self.assertGreater(m["gesamt_eur"], 0)

    def test_2b_je_agent_und_echte_usd(self):
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        ks.record(quelle="chat", agent="HoA", modell="claude-opus-4-8", input_tokens=1000, output_tokens=500)
        ks.record(quelle="agent", agent="CFO", modell="claude-haiku-4-5", input_tokens=800, output_tokens=200)
        # kosten_usd hat Vorrang vor der Schaetzung -> 2 USD * 0.92 = 1.84 EUR
        ev = ks.record(quelle="agent", agent="CFO", modell="claude-opus-4-8", input_tokens=1, output_tokens=1,
                       kosten_usd=2.0)
        self.assertAlmostEqual(ev["eur"], 1.84, places=2)
        m = ks.monat()
        self.assertIn("je_agent", m)
        self.assertEqual(m["je_agent"]["CFO"]["aufrufe"], 2)
        self.assertEqual(m["je_agent"]["HoA"]["aufrufe"], 1)

    def test_2c_alteintrag_ohne_agent_faellt_auf_quelle(self):
        from datetime import datetime
        p = Path(tempfile.mkdtemp()) / "k.jsonl"
        p.write_text('{"ts":"%s-01T00:00:00","quelle":"chat","modell":"claude-haiku-4-5",'
                     '"provider":"anthropic","in":10,"out":5,"eur":0.01}\n'
                     % datetime.now().strftime("%Y-%m"), encoding="utf-8")
        m = KostenStore(p).monat()
        self.assertIn("chat", m["je_agent"])            # Alt-Eintrag ohne 'agent' -> unter 'quelle' gebucket

    def test_3_provider_erkennung(self):
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        self.assertEqual(ks.record(quelle="x", modell="gpt-4o-mini", input_tokens=1,
                                   output_tokens=1)["provider"], "openai")
        self.assertEqual(ks.record(quelle="x", modell="claude-opus-4-8", input_tokens=1,
                                   output_tokens=1)["provider"], "anthropic")

    def test_4_tool(self):
        self.assertIn("kosten_statistik", {t["name"] for t in tool_specs()})
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        ks.record(quelle="chat", modell="claude-haiku-4-5", input_tokens=100, output_tokens=50)
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], kosten=ks)
        res = run_tool("kosten_statistik", {}, ctx)
        self.assertIn("gesamt_eur", res)


if __name__ == "__main__":
    unittest.main()
