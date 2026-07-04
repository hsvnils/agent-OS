"""UI-V1/V2-Umschaltung: der `/`-Handler liefert die richtige Einstiegs-Datei; Prefs nehmen `ui_version` an.

Ohne Passwort laeuft LUNA-OS im offenen Dev-Modus (Owner) -> die Requests kommen ohne Login durch.
Ohne Supabase bleibt der Prefs-Store leer -> Default V1; die `?ui=`-Query ist der harte Override/Escape-Hatch.
"""
import unittest

from fastapi.testclient import TestClient

from orchestrator.channels.web.app import app


class TestUiVersionRouting(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def test_default_ist_v1(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("LUNA Command Center", r.text)     # V1-Titel
        self.assertIn("/static/app.js", r.text)          # V1-Bundle

    def test_query_v2_liefert_v2_shell(self):
        r = self.c.get("/?ui=v2")
        self.assertEqual(r.status_code, 200)
        self.assertIn("app-v2.js", r.text)               # V2-Bundle
        self.assertIn("Kontrollraum", r.text)            # V2-Titel

    def test_query_v1_override_liefert_v1(self):
        r = self.c.get("/?ui=v1")
        self.assertIn("/static/app.js", r.text)
        self.assertNotIn("app-v2.js", r.text)

    def test_unbekannter_ui_param_faellt_auf_v1(self):
        r = self.c.get("/?ui=quatsch")
        self.assertIn("LUNA Command Center", r.text)

    def test_prefs_akzeptiert_ui_version(self):
        r = self.c.post("/api/prefs", json={"prefs": {"ui_version": "v2"}})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))


if __name__ == "__main__":
    unittest.main()
