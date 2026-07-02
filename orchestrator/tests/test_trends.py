import tempfile
import unittest
from pathlib import Path

from orchestrator.core.trends import TrendStore
from orchestrator.governance.supabase import MockSupabaseClient, SupabaseAuth, SupabaseClient


class TestTrendStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cache = Path(self.dir.name) / "trends.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_list_aus_supabase_und_cache(self):
        mock = MockSupabaseClient()
        mock.rows["trend_signals"] = [{"id": "t1", "title": "Stadion-Sounds", "status": "new",
                                       "relevance": "high", "score": 80}]
        store = TrendStore(mock, self.cache)
        rows = store.list()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Stadion-Sounds")
        self.assertTrue(self.cache.exists())          # Cache wurde geschrieben

    def test_list_fallback_aus_cache_wenn_offline(self):
        # zuerst mit Mock cachen ...
        mock = MockSupabaseClient()
        mock.rows["trend_signals"] = [{"id": "t1", "title": "Retro-Trikots", "status": "new"}]
        TrendStore(mock, self.cache).list()
        # ... dann OFFLINE (nicht verfuegbarer Client) -> Cache-Fallback
        offline = TrendStore(SupabaseClient(SupabaseAuth()), self.cache)
        rows = offline.list()
        self.assertEqual(rows[0]["title"], "Retro-Trikots")

    def test_status_setzen_upsert(self):
        mock = MockSupabaseClient()
        mock.rows["trend_signals"] = [{"id": "t1", "title": "X", "status": "new"}]
        store = TrendStore(mock, self.cache)
        store.list()                                  # Cache befuellen
        r = store.status_setzen("t1", "approved")
        self.assertTrue(r["ok"])
        self.assertEqual(mock.upserts[-1][0], "trend_signals")
        self.assertEqual(mock.upserts[-1][1][0]["status"], "approved")

    def test_status_ungueltig(self):
        store = TrendStore(MockSupabaseClient(), self.cache)
        self.assertFalse(store.status_setzen("t1", "quatsch")["ok"])

    def test_status_offline_fall_b(self):
        store = TrendStore(SupabaseClient(SupabaseAuth()), self.cache)
        self.assertTrue(store.status_setzen("t1", "approved")["fall_b"])


if __name__ == "__main__":
    unittest.main()
