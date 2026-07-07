"""Self-Checks fuer den Facebook-Reels-Uploader (Stufe D) -- Guards, ohne Netzwerk/Kosten."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.governance.facebook_reels import poste_reel


class TestFacebookReels(unittest.TestCase):
    def test_ohne_token_klarer_fehler(self):
        r = poste_reel("", "", "/x.mp4")
        self.assertFalse(r["ok"])
        self.assertIn("pages_manage_posts", r["fehler"])

    def test_fehlendes_video(self):
        r = poste_reel("123", "tok", "/gibt/es/nicht.mp4")
        self.assertFalse(r["ok"])
        self.assertIn("nicht gefunden", r["fehler"])

    def test_page_info_ohne_setup_leer(self):
        from orchestrator.governance.instagram_token import InstagramTokenManager
        mgr = InstagramTokenManager(user_token_seed="", app_secret="")   # nicht verfuegbar
        self.assertEqual(mgr.page_info(), ("", ""))

    def test_video_vorhanden_aber_kein_token(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reel.mp4"
            p.write_bytes(b"x")
            r = poste_reel("", "tok", str(p))               # page_id leer -> Guard vor Netzwerk
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
