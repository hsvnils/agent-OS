"""LUNA-Hologramm: 2D-Living-Portrait-Modul wird ausgeliefert; Feature-Flag steckt in /api/me.

Das Hologramm nutzt DAS Kunstbild direkt (kein 3D/WebGL, kein Three.js) -- `luna-avatar.js` ueber /static;
der Umschalter Orb<->Hologramm haengt an `/api/me.avatar_enabled` (env `LUNA_AVATAR`, Default an).
"""
import os
import unittest

from fastapi.testclient import TestClient

from orchestrator.channels.web.app import app


class TestAvatarAssets(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def test_avatar_modul_ausgeliefert(self):
        r = self.c.get("/static/luna-avatar.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("createAvatar", r.text)      # exportierte API (unveraendert)
        self.assertIn("luna-portrait", r.text)     # 2D-Portrait nutzt das Kunstbild
        self.assertNotIn("import * as THREE", r.text)  # kein 3D/Three.js mehr

    def test_me_hat_avatar_flag(self):
        r = self.c.get("/api/me")
        self.assertEqual(r.status_code, 200)
        self.assertIn("avatar_enabled", r.json())
        self.assertTrue(r.json()["avatar_enabled"])

    def test_flag_abschaltbar_per_env(self):
        os.environ["LUNA_AVATAR"] = "0"
        try:
            self.assertFalse(TestClient(app).get("/api/me").json()["avatar_enabled"])
        finally:
            os.environ.pop("LUNA_AVATAR", None)


if __name__ == "__main__":
    unittest.main()
