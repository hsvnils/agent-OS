"""LUNA 3D-Hologramm: Assets werden ausgeliefert und das Feature-Flag steckt in /api/me.

Vendored Three.js (kein CDN) + das geteilte Avatar-Modul muessen ueber /static erreichbar sein; der Umschalter
Orb<->Hologramm haengt an `/api/me.avatar_enabled` (env `LUNA_AVATAR`, Default an).
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
        self.assertIn("createAvatar", r.text)          # exportierte API
        self.assertIn("three.module.min.js", r.text)   # vendored, kein CDN

    def test_threejs_vendored(self):
        r = self.c.get("/static/vendor/three/three.module.min.js")
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.content), 100000)      # echter Three.js-Build

    def test_me_hat_avatar_flag(self):
        r = self.c.get("/api/me")
        self.assertEqual(r.status_code, 200)
        self.assertIn("avatar_enabled", r.json())
        self.assertTrue(r.json()["avatar_enabled"])     # Default an

    def test_flag_abschaltbar_per_env(self):
        os.environ["LUNA_AVATAR"] = "0"
        try:
            self.assertFalse(TestClient(app).get("/api/me").json()["avatar_enabled"])
        finally:
            os.environ.pop("LUNA_AVATAR", None)


if __name__ == "__main__":
    unittest.main()
