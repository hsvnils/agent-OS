"""Phase 17 (M5) -- Vision-Endpoint-Guards (ohne Netz/Modell)."""
import os
import unittest

from runner.vision import bild_lesen


class TestVisionGuards(unittest.TestCase):
    def setUp(self):
        self._alt = {k: os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY")}
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        for k, v in self._alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_ohne_key(self):
        r = bild_lesen(b"\x89PNG...", "was ist das?")
        self.assertFalse(r["ok"])
        self.assertIn("Vision-Modell", r["grund"])

    def test_leeres_bild(self):
        os.environ["GEMINI_API_KEY"] = "dummy"
        r = bild_lesen(b"", "")
        self.assertFalse(r["ok"])
        self.assertIn("Leeres Bild", r["grund"])


if __name__ == "__main__":
    unittest.main()
