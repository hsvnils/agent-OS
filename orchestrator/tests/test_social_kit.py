import tempfile
import unittest
from pathlib import Path

from orchestrator.core.social_kit import MetaInsights, SocialStore, Snapshot, media_kit


def _fake_http(url, params):
    if url.endswith("/insights"):
        return {"data": [{"name": "reach", "values": [{"value": 30000}]},
                         {"name": "profile_views", "values": [{"value": 1200}]}]}
    if url.endswith("/media"):
        return {"data": [{"like_count": 100, "comments_count": 10, "timestamp": "2026-07-01"},
                         {"like_count": 200, "comments_count": 20, "timestamp": "2026-07-02"}]}
    # Profil-Endpoint
    return {"username": "hanserautisch", "followers_count": 5000, "media_count": 120}


class TestMetaInsights(unittest.TestCase):
    def test_hole_parst_alles(self):
        mi = MetaInsights("tok", "123", http=_fake_http)
        snap = mi.hole("2026-07")
        self.assertEqual(snap.username, "hanserautisch")
        self.assertEqual(snap.followers, 5000)
        self.assertEqual(snap.reach, 30000)
        self.assertEqual(snap.profile_views, 1200)
        self.assertEqual(snap.avg_likes, 150.0)
        self.assertEqual(snap.avg_comments, 15.0)
        self.assertAlmostEqual(snap.engagement_rate, 3.3, places=1)   # 165/5000*100
        self.assertEqual(len(snap.top_posts), 2)

    def test_ohne_token_nicht_verfuegbar(self):
        self.assertFalse(MetaInsights("", "123").verfuegbar)
        self.assertIsNone(MetaInsights("", "123", http=_fake_http).hole())

    def test_profil_fehler_gibt_none(self):
        def boom(url, params):
            if not url.endswith("/insights") and not url.endswith("/media"):
                return {"error": {"message": "invalid token"}}
            return {}
        self.assertIsNone(MetaInsights("tok", "123", http=boom).hole())


class TestSocialStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = SocialStore(Path(self.dir.name) / "social.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_speichern_und_monat(self):
        self.store.speichere(Snapshot(monat="2026-06", followers=4500))
        self.store.speichere(Snapshot(monat="2026-07", followers=5000))
        self.assertEqual(self.store.monat("2026-06")["followers"], 4500)
        self.assertEqual(self.store.monat()["monat"], "2026-07")       # Default: neuester

    def test_dedup_juengster_gewinnt(self):
        self.store.speichere(Snapshot(monat="2026-07", followers=5000))
        self.store.speichere(Snapshot(monat="2026-07", followers=5100))   # Korrektur
        self.assertEqual(self.store.monat("2026-07")["followers"], 5100)
        self.assertEqual(len(self.store.verlauf()), 1)

    def test_leer(self):
        self.assertIsNone(self.store.monat())
        self.assertEqual(self.store.verlauf(), [])


class TestMediaKit(unittest.TestCase):
    def test_media_kit_mit_trend(self):
        jetzt = {"monat": "2026-07", "username": "hanserautisch", "followers": 5000, "reach": 30000,
                 "profile_views": 1200, "engagement_rate": 3.3, "media_count": 120, "avg_likes": 150.0,
                 "avg_comments": 15.0, "top_posts": []}
        vor = {"followers": 4500, "reach": 25000, "profile_views": 1000, "engagement_rate": 3.0}
        kit = media_kit(jetzt, vor)
        self.assertIn("Follower: 5000", kit["media_kit_text"])
        self.assertIn("+500", kit["media_kit_text"])                    # Delta ggue. Vormonat
        self.assertEqual(kit["kennzahlen"]["reach"], 30000)
        self.assertIn("CEO-Tor", kit["hinweis"])

    def test_media_kit_ohne_vormonat(self):
        kit = media_kit({"monat": "2026-07", "username": "x", "followers": 100})
        self.assertIn("Follower: 100", kit["media_kit_text"])
        self.assertNotIn("Vormonat", kit["media_kit_text"])


if __name__ == "__main__":
    unittest.main()
