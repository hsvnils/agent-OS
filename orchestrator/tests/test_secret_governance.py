"""Self-Check: grant_capability Fall A/B + Leck-Schutz (kein Key im Klartext)."""
import unittest

from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.capability import grant_capability
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.leak_guard import is_redactable_secret, redact


class TestSecretGovernance(unittest.TestCase):
    def test_fall_a_gewaehrt_und_informiert(self):
        inform, clog = [], []
        r = grant_capability(
            "cto", "supabase",
            exists_and_paid=True, in_budget=True,
            ceo_inform=lambda a, c: inform.append((a, c)),
            changelog=lambda *x: clog.append(x),
        )
        self.assertTrue(r.granted)
        self.assertEqual(r.fall, "A")
        self.assertTrue(inform)
        self.assertTrue(clog)

    def test_fall_b_blockiert_und_eskaliert(self):
        clog = []
        r = grant_capability(
            "cto", "neuer_bezahl_dienst",
            exists_and_paid=False, in_budget=False,
            changelog=lambda *x: clog.append(x),
        )
        self.assertFalse(r.granted)
        self.assertEqual(r.fall, "B")
        self.assertIn("ANFRAGE an CEO", r.freigabe_anfrage)
        self.assertTrue(clog)

    def test_leak_guard_redigiert_secret(self):
        secret = "sk-test-SECRET-123456"
        text = "Die HoA-Ausgabe enthaelt den Key " + secret + " versehentlich."
        red = redact(text, [secret])
        self.assertNotIn(secret, red)
        self.assertIn("[REDACTED]", red)

    def test_is_redactable_secret_filtert_nicht_secrets(self):
        # Echte Keys -> ja; Flags/Zahlen/E-Mails/kurze Werte -> nein (sonst werden IDs/Logs verstuemmelt).
        self.assertTrue(is_redactable_secret("sk-ant-abcdef1234567890"))
        self.assertTrue(is_redactable_secret("BSAGzbv3zkWK7It-c2NQ"))
        self.assertFalse(is_redactable_secret("1"))                 # WEB_RESEARCH_ANTHROPIC=1
        self.assertFalse(is_redactable_secret("8594240885"))        # Chat-ID (rein numerisch)
        self.assertFalse(is_redactable_secret("hsvnils@icloud.com"))  # E-Mail (PII, kein Secret)
        self.assertFalse(is_redactable_secret("Europe/Bln"))        # kurz

    def test_secret_taucht_nicht_in_hoa_ausgabe_auf(self):
        secret = "sk-test-SECRET-123456"
        backend = MockBackend(scripted={"berater": lambda m, c: "Ergebnis mit " + secret})
        hoa = HeadOfAgents(
            backend, load_default_subagents(), gate=CeoGate(), leak_secrets=[secret]
        )
        out = "".join(hoa.handle("Erstelle eine Analyse"))
        self.assertNotIn(secret, out)
        self.assertIn("[REDACTED]", out)


if __name__ == "__main__":
    unittest.main()
