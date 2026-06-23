"""Self-Check: Backend-/API-Fehler wird sauber gemeldet statt als Traceback.

Deckt die GATE-B-Robustheit ab: faellt ein Modellaufruf aus (z. B. API-Guthaben
zu niedrig), darf die Sitzungsschleife nicht abstuerzen -- der HoA gibt eine
CEO-taugliche Fehlermeldung aus und protokolliert wahrheitsgemaess.
"""
import unittest

from orchestrator.core.backends import BackendError, MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


def _raise(_m, _c):
    raise BackendError("Modellaufruf fuer 'berater' fehlgeschlagen (...). "
                       "Anthropic-API-Guthaben zu niedrig -- aufladen.")


class TestBackendFehler(unittest.TestCase):
    def test_backend_fehler_wird_sauber_gemeldet(self):
        backend = MockBackend(scripted={"berater": _raise})
        hoa = HeadOfAgents(backend, load_default_subagents(), gate=CeoGate())

        # Darf NICHT werfen -- saubere Antwort statt Traceback.
        out = "".join(hoa.handle("Strategie-Einschaetzung bitte"))

        self.assertIn("FEHLER:", out)
        self.assertIn("Guthaben", out)

    def test_changelog_kennzeichnet_fehler(self):
        eintraege = []

        def changelog(actor, was, warum, betroffen):
            eintraege.append(was)

        backend = MockBackend(scripted={"berater": _raise})
        hoa = HeadOfAgents(
            backend, load_default_subagents(), gate=CeoGate(), changelog=changelog
        )
        "".join(hoa.handle("Strategie-Einschaetzung bitte"))

        self.assertTrue(eintraege)
        self.assertIn("mit Fehler(n)", eintraege[0])


if __name__ == "__main__":
    unittest.main()
