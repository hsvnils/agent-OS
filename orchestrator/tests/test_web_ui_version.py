"""Seit 2026-09-29 gibt es nur noch ein Design (V2): `/` liefert immer LUNA-OS V2 -- auch alte Lesezeichen mit
`?ui=v1` oder eine gespeicherte Einstellung `ui_version` fuehren nicht mehr ins entfernte V1."""
import unittest

from fastapi.testclient import TestClient

from orchestrator.channels.web.app import STATIC, app


class TestNurNochV2(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def test_start_ist_v2(self):
        for url in ("/", "/?ui=v1", "/?ui=v2", "/?ui=quatsch"):
            r = self.c.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertIn("app-v2.js", r.text, url)
            self.assertIn("Kontrollraum", r.text, url)

    def test_v1_dateien_sind_weg(self):
        for name in ("index.html", "app.js", "style.css", "vendor/winbox.bundle.min.js"):
            self.assertFalse((STATIC / name).exists(), name)
            self.assertEqual(self.c.get(f"/static/{name}").status_code, 404, name)
        self.assertNotIn("data-ui-mode", (STATIC / "app-v2.js").read_text(encoding="utf-8"))   # kein Umschalter mehr

    def test_prefs_mit_altem_ui_version_stoeren_nicht(self):
        r = self.c.post("/api/prefs", json={"prefs": {"ui_version": "v1"}})
        self.assertTrue(r.json().get("ok"))
        self.assertIn("app-v2.js", self.c.get("/").text)


if __name__ == "__main__":
    unittest.main()
