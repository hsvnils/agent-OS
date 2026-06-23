"""Self-Check: Blockade -> CTO; CEO-Tor-Aktion -> blockiert + Freigabe-Anfrage."""
import unittest

from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


class TestEskalation(unittest.TestCase):
    def test_blockade_geht_an_cto(self):
        scripted = {
            "berater": lambda m, c: "BLOCKED: ausserhalb Mandat",
            "cto": lambda m, c: "Workaround gebaut",
        }
        backend = MockBackend(scripted=scripted)
        hoa = HeadOfAgents(backend, load_default_subagents(), gate=CeoGate())
        out = "".join(hoa.handle("Analysiere etwas Kniffliges"))

        self.assertIn("Via CTO geloest", out)
        self.assertTrue(any(k == "cto" for k, _ in backend.calls))

    def test_ceo_tor_aktion_blockiert_und_freigabe_anfrage(self):
        hoa = HeadOfAgents(MockBackend(), load_default_subagents(), gate=CeoGate())
        out = "".join(hoa.handle("Bitte ein neues kostenpflichtiges Tool beschaffen"))

        self.assertIn("CEO-Tor beruehrt", out)
        self.assertIn("ANFRAGE an CEO", out)
        # Keine Delegation, da vor Ausfuehrung blockiert
        # (Backend wurde nicht aufgerufen)
        self.assertEqual(hoa.backend.calls, [])


if __name__ == "__main__":
    unittest.main()
