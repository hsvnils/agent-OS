"""Self-Checks fuer den Live-Voice-Kanal (Phase 2), ohne Audio/STT/TTS und ohne Kosten.

Deckt ab: Bruecke offline, Kanal-Gleichheit (Terminal == Voice-Bruecke), show_panel
(inkl. kostenuebersicht aus finance/), Leck-Schutz in Panels, CEO-Tor im Voice-Pfad.
"""
import io
import unittest

from orchestrator.channels.terminal import TerminalAdapter
from orchestrator.channels.voice.bridge import HoaBridge
from orchestrator.channels.voice.panels import build_panel, detect_panel_intent
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate


def _core():
    return HeadOfAgents(MockBackend(), load_default_subagents(), gate=CeoGate())


class TestVoiceBridge(unittest.TestCase):
    def test_1_bruecke_offline(self):
        bridge = HoaBridge(_core())
        res = bridge.respond("Strategie-Einschaetzung zu Thema Alpha")
        self.assertTrue(res.spoken)
        self.assertIsNone(res.panel)

    def test_2_kanal_gleichheit_terminal_vs_voice(self):
        instruction = "Strategie-Einschaetzung zu Thema Alpha"
        # Voice-Bruecke
        voice_spoken = HoaBridge(_core()).respond(instruction).spoken
        # Terminal-Adapter ueber denselben (frischen) Kern
        out = io.StringIO()
        TerminalAdapter(in_stream=io.StringIO(instruction + "\nexit\n"), out_stream=out).run(_core())
        terminal_text = out.getvalue()
        # Gleicher HoA-Antwortinhalt in beiden Kanaelen; Voice ist nur sprechbar bereinigt
        # (ohne Bundle-Rahmen "Konsolidierte Antwort an den CEO:" / "- berater:").
        self.assertIn("Konsolidierte Antwort an den CEO", terminal_text)
        self.assertNotIn("Konsolidierte Antwort an den CEO", voice_spoken)
        self.assertIn("Thema Alpha", voice_spoken)
        self.assertIn("Thema Alpha", terminal_text)
        self.assertIn("Ergebnis zu", voice_spoken)  # eigentliche Antwort wird gesprochen

    def test_3_show_panel_kostenuebersicht_aus_finance(self):
        bridge = HoaBridge(_core())
        res = bridge.respond("Zeig mir bitte die Kostenuebersicht")
        self.assertIsNotNone(res.panel)
        self.assertEqual(res.panel["type"], "kostenuebersicht")
        self.assertIn("monatsbudget", res.panel)
        self.assertIn("finance/budget.md", res.panel["quellen"])
        # Reine Anzeige -> KEIN Tor ausgeloest.
        self.assertNotIn("ANFRAGE an CEO", res.spoken)
        self.assertIn("Kostenübersicht", res.spoken)  # gesprochener Text mit Umlaut
        self.assertEqual(res.panel["title"], "Kostenübersicht")

    def test_4_leck_schutz_in_panels(self):
        secret = "sk-ant-PANELSECRET-123"
        panel = build_panel("text", {"title": "X", "markdown": f"Key: {secret}"},
                            secrets=[secret])
        self.assertNotIn(secret, str(panel))
        self.assertIn("[REDACTED]", panel["markdown"])

    def test_5_ceo_tor_im_voice_pfad(self):
        bridge = HoaBridge(_core())
        res = bridge.respond("Bitte ein neues kostenpflichtiges Tool beschaffen")
        self.assertIsNone(res.panel)  # kein Anzeige-Intent
        self.assertIn("CEO-Tor beruehrt", res.spoken)
        self.assertIn("ANFRAGE an CEO", res.spoken)

    def test_6_intent_erkennt_nur_anzeige(self):
        self.assertIsNotNone(detect_panel_intent("zeig mir die kostenuebersicht"))
        self.assertIsNone(detect_panel_intent("beschaffe ein neues kostenpflichtiges tool"))


if __name__ == "__main__":
    unittest.main()
