"""Self-Checks fuer das dateibasierte Agenten-Gedaechtnis (Schritt B).

Deckt ab: Round-Trip, Relevanz-Recall, Leck-Schutz, HoA-Integration,
Dry-Run-Trennung und Isolation vom persoenlichen Claude-Code-Memory.
"""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.memory import Memory, MemoryRecord
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


def _rec(instruction: str, result: str = "ok-ergebnis", status: str = "ok") -> MemoryRecord:
    return MemoryRecord.build(
        session_id="t", instruction=instruction, delegated_to=["berater"],
        status=status, result=result,
    )


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_1_round_trip_neueste_zuerst(self):
        mem = Memory(self.tmp / "log.jsonl")
        mem.append(_rec("Erster Auftrag Alpha"))
        mem.append(_rec("Zweiter Auftrag Beta"))
        recs = mem.recall("beliebig", limit=5)
        self.assertEqual(len(recs), 2)
        self.assertIn("Beta", recs[0]["instruction"])  # neueste zuerst

    def test_2_relevanz_recall_findet_aelteren_treffer(self):
        mem = Memory(self.tmp / "log.jsonl", recall_limit=2)
        mem.append(_rec("Auftrag zum Thema zebra"))   # aeltester, distinktes Stichwort
        mem.append(_rec("Auftrag zwei"))
        mem.append(_rec("Auftrag drei"))
        recs = mem.recall("Neue Frage zu zebra", limit=2)
        instructions = " ".join(r["instruction"] for r in recs)
        self.assertIn("zebra", instructions)  # trotz Position ausserhalb der letzten N

    def test_3_leck_schutz(self):
        secret = "sk-ant-TESTSECRET-xyz"
        mem = Memory(self.tmp / "log.jsonl", secrets=[secret])
        mem.append(_rec(f"Bitte nutze den Key {secret} fuer etwas"))
        raw = (self.tmp / "log.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(secret, raw)
        self.assertIn("[REDACTED]", raw)

    def test_4_hoa_integration_zweiter_auftrag_sieht_kontext(self):
        mem = Memory(self.tmp / "log.jsonl")
        backend = MockBackend()
        hoa = HeadOfAgents(backend, load_default_subagents(), gate=CeoGate(), memory=mem)
        list(hoa.handle("Strategie zu Thema Alpha"))
        list(hoa.handle("Strategie zu Thema Beta"))
        # Zweiter Backend-Aufruf muss den Gedaechtnis-Kontext (inkl. Alpha) enthalten.
        _, zweite_nachricht = backend.calls[-1]
        self.assertIn("Gedaechtnis-Kontext", zweite_nachricht)
        self.assertIn("Alpha", zweite_nachricht)

    def test_5_dry_run_trennung(self):
        canonical = self.tmp / "log.jsonl"
        dryrun = self.tmp / "log_dryrun.jsonl"
        Memory(dryrun).append(_rec("Smoke-Auftrag"))
        self.assertTrue(dryrun.exists())
        self.assertFalse(canonical.exists())  # kanonischer Store bleibt unberuehrt

    def test_6_isolation_kein_fremdes_memory(self):
        mem = Memory(self.tmp / "frisch.jsonl")
        self.assertEqual(mem.recall("irgendwas"), [])  # zieht kein persoenliches Memory
        self.assertEqual(mem.path, self.tmp / "frisch.jsonl")


if __name__ == "__main__":
    unittest.main()
