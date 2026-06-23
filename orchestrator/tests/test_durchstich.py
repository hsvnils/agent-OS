"""Self-Check: Durchstich CEO -> HoA -> CTO/Berater -> EINE konsolidierte Antwort."""
import unittest

from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


class TestDurchstich(unittest.TestCase):
    def test_durchstich_eine_antwort(self):
        backend = MockBackend()
        changelog_calls = []
        hoa = HeadOfAgents(
            backend,
            load_default_subagents(),
            gate=CeoGate(),
            changelog=lambda *a: changelog_calls.append(a),
        )
        msg = "Analysiere unsere Markt-Strategie und pruefe die technische Machbarkeit"
        out = "".join(hoa.handle(msg))

        # Beide Subagenten beteiligt
        self.assertIn("berater", out)
        self.assertIn("cto", out)
        # Genau EINE konsolidierte Antwort
        self.assertEqual(out.count("Konsolidierte Antwort an den CEO:"), 1)
        # Changelog wurde geschrieben
        self.assertTrue(changelog_calls)
        # Delegation an beide erfolgte
        keys = {k for k, _ in backend.calls}
        self.assertEqual(keys, {"berater", "cto"})


if __name__ == "__main__":
    unittest.main()
