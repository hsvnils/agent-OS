"""Self-Check: gleicher HoA-Kern, unterschiedliche Adapter -> gleiches Ergebnis.

Beweist, dass spaetere Voice-/Telegram-Adapter ohne Kernaenderung andocken.
"""
import io
import unittest

from orchestrator.channels.mock import MockAdapter
from orchestrator.channels.terminal import TerminalAdapter
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


def build_core():
    return HeadOfAgents(MockBackend(), load_default_subagents(), gate=CeoGate())


class TestKanalAbstraktion(unittest.TestCase):
    def test_terminal_und_mock_gleiches_ergebnis(self):
        msg = "Analysiere die Effizienz unserer Prozesse"

        # Terminal-Adapter mit injizierten Streams
        tin = io.StringIO(msg + "\nexit\n")
        tout = io.StringIO()
        TerminalAdapter(in_stream=tin, out_stream=tout).run(build_core())
        term_out = tout.getvalue()

        # Mock-Adapter
        ma = MockAdapter([msg])
        ma.run(build_core())
        mock_out = ma.text()

        # Die konsolidierte Antwort des Mock-Laufs steckt unveraendert im Terminal-Lauf
        self.assertIn(mock_out.strip(), term_out)
        self.assertIn("Konsolidierte Antwort an den CEO:", mock_out)


if __name__ == "__main__":
    unittest.main()
