"""Self-Check: ein Subagent loest im eigenen Mandat ohne Eskalation."""
import unittest

from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


class TestAutonomie(unittest.TestCase):
    def test_loesung_im_mandat_ohne_eskalation(self):
        backend = MockBackend()  # Default: liefert normales Ergebnis (kein BLOCKED)
        hoa = HeadOfAgents(backend, load_default_subagents(), gate=CeoGate())
        out = "".join(hoa.handle("Erstelle eine Markt-Analyse"))

        self.assertIn("berater", out)
        self.assertNotIn("BLOCKED", out)
        self.assertNotIn("Eskalation", out)
        # keine CTO-Eskalation ausgeloest
        self.assertFalse(any(k == "cto" for k, _ in backend.calls))


if __name__ == "__main__":
    unittest.main()
