"""LUNA 3D-Hologramm: Assets werden ausgeliefert und das Feature-Flag steckt in /api/me.

Vendored Three.js + GLTFLoader + GLB-Modell (kein CDN, per Import-Map) muessen ueber /static erreichbar sein;
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
        self.assertIn("createAvatar", r.text)     # exportierte API
        self.assertIn("GLTFLoader", r.text)        # laedt echtes GLB-Modell

    def test_vendored_assets(self):
        for pfad, minlen in [
            ("/static/vendor/three/three.module.min.js", 100000),
            ("/static/vendor/three/loaders/GLTFLoader.js", 20000),
            ("/static/vendor/three/utils/BufferGeometryUtils.js", 5000),
            ("/static/vendor/models/luna-avatar.glb", 500000),
        ]:
            r = self.c.get(pfad)
            self.assertEqual(r.status_code, 200, pfad)
            self.assertGreater(len(r.content), minlen, pfad)

    def test_importmap_in_beiden_shells(self):
        for pfad in ("/?ui=v1", "/?ui=v2"):
            html = self.c.get(pfad).text
            self.assertIn('type="importmap"', html, pfad)
            self.assertIn("/static/vendor/three/three.module.min.js", html, pfad)

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
