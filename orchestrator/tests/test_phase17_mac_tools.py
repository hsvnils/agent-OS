"""Phase 17 (LUNA am Mac) — M2: On-Screen-Awareness + App-Wissen.

Plattform-sicher: laeuft auch auf Nicht-macOS (dort degradieren die Awareness-Funktionen kontrolliert).
"""
import pathlib
import unittest

from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from runner import awareness, capabilities


def _ctx():
    root = pathlib.Path(".")
    return ToolContext(core=None, antraege=None, engine=None, finance_dir=root,
                       repo_root=root, leak_secrets=[])


class TestPhase17ToolsRegistered(unittest.TestCase):
    def test_neue_tools_im_schema(self):
        names = {s["name"] for s in tool_specs()}
        self.assertIn("bildschirm_sehen", names)
        self.assertIn("apps_kennen", names)


class TestAwareness(unittest.TestCase):
    def test_snapshot_struktur(self):
        snap = run_tool("bildschirm_sehen", {}, _ctx())
        self.assertIn("verfuegbar", snap)
        self.assertIn("laufende_apps", snap)
        self.assertIsInstance(snap["laufende_apps"], list)

    def test_nicht_macos_degradiert(self):
        # frontmost_app darf nie werfen; ohne macOS -> verfuegbar False mit Hinweis.
        res = awareness.frontmost_app()
        self.assertIn("verfuegbar", res)
        if not awareness.is_macos():
            self.assertFalse(res["verfuegbar"])
            self.assertIn("hinweis", res)


class TestCapabilities(unittest.TestCase):
    def test_apps_kennen_struktur(self):
        res = run_tool("apps_kennen", {"aufgabe": "Notiz schreiben"}, _ctx())
        self.assertIn("installiert", res)
        self.assertIn("bekannte_apps", res)
        self.assertIn("empfehlung", res)

    def test_empfehlung_text_findet_textedit(self):
        # Hinweis ist kuratiert (auch ohne Installation vorhanden) -> Empfehlung greift plattformunabhaengig.
        treffer = capabilities.recommend_for("ich will einen Text schreiben")
        apps = {t["app"].lower() for t in treffer}
        self.assertTrue(any("textedit" in a for a in apps))

    def test_build_register_struktur(self):
        reg = capabilities.build_register()
        self.assertIn("installiert", reg)
        self.assertIn("bekannt", reg)
        self.assertIn("unbekannt", reg)


if __name__ == "__main__":
    unittest.main()
