import tempfile
import unittest
from pathlib import Path

from orchestrator.core.content_store import (ContentStore, IDEA_STATUSES, TREND_FELDER, TREND_STATUSES)
from orchestrator.governance.supabase import MockSupabaseClient, SupabaseAuth, SupabaseClient


class TestContentStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cache = Path(self.dir.name) / "c.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def _store(self, client, tabelle="trend_signals", statuses=TREND_STATUSES):
        return ContentStore(client, tabelle, TREND_FELDER, self.cache, statuses=statuses)

    def test_list_supabase_und_cache(self):
        mock = MockSupabaseClient()
        mock.rows["trend_signals"] = [{"id": "t1", "title": "Stadion", "status": "new"}]
        rows = self._store(mock).list()
        self.assertEqual(rows[0]["title"], "Stadion")
        self.assertTrue(self.cache.exists())

    def test_list_fallback_offline(self):
        mock = MockSupabaseClient()
        mock.rows["trend_signals"] = [{"id": "t1", "title": "Retro", "status": "new"}]
        self._store(mock).list()                                     # Cache befuellen
        rows = self._store(SupabaseClient(SupabaseAuth())).list()    # offline -> Cache
        self.assertEqual(rows[0]["title"], "Retro")

    def test_status_setzen_patch(self):
        mock = MockSupabaseClient()
        r = self._store(mock).status_setzen("t1", "approved")
        self.assertTrue(r["ok"])
        tabelle, patch, params = mock.patches[-1]
        self.assertEqual(tabelle, "trend_signals")
        self.assertEqual(patch["status"], "approved")
        self.assertIn("id=eq.t1", params)

    def test_status_ungueltig(self):
        self.assertFalse(self._store(MockSupabaseClient()).status_setzen("t1", "quatsch")["ok"])

    def test_parametrierbar_ideen(self):
        # gleicher Store, andere Tabelle/Statusliste
        mock = MockSupabaseClient()
        store = self._store(mock, tabelle="ideas", statuses=IDEA_STATUSES)
        self.assertTrue(store.status_setzen("i1", "planned")["ok"])
        self.assertEqual(mock.patches[-1][0], "ideas")
        self.assertFalse(store.status_setzen("i1", "approved")["ok"])   # 'approved' gehoert zu Trends, nicht Ideen

    def test_patch_beliebiges_feld(self):
        mock = MockSupabaseClient()
        r = self._store(mock, tabelle="sources", statuses=()).patch("s1", {"is_active": False})
        self.assertTrue(r["ok"])
        self.assertEqual(mock.patches[-1][0], "sources")
        self.assertEqual(mock.patches[-1][1]["is_active"], False)

    def test_status_feld_recommendation(self):
        mock = MockSupabaseClient()
        store = ContentStore(mock, "ai_intel_items", TREND_FELDER, self.cache,
                             statuses=("use", "investigate", "later", "ignore"), status_feld="recommendation")
        self.assertTrue(store.status_setzen("a1", "use")["ok"])
        self.assertEqual(mock.patches[-1][1]["recommendation"], "use")     # PATCH auf recommendation, nicht status

    def test_offline_status_fall_b(self):
        self.assertTrue(self._store(SupabaseClient(SupabaseAuth())).status_setzen("t1", "approved")["fall_b"])

    def test_add_insert_und_cache(self):
        mock = MockSupabaseClient()
        store = self._store(mock)
        r = store.add({"title": "Neuer Trend", "status": "new", "source_url": "https://x.test/1"})
        self.assertTrue(r["ok"])
        tabelle, rows, _ = mock.upserts[-1]
        self.assertEqual(tabelle, "trend_signals")
        self.assertEqual(rows[0]["title"], "Neuer Trend")
        self.assertIn("created_at", rows[0])   # Zeitstempel automatisch gesetzt
        self.assertIn("updated_at", rows[0])
        self.assertNotIn("id", rows[0])        # id bleibt offen -> Supabase-Default
        # Cache wurde vorne befuellt (Offline-Fallback fuer die Anzeige)
        self.assertEqual(self._store(SupabaseClient(SupabaseAuth())).list()[0]["title"], "Neuer Trend")

    def test_add_none_werte_fallen_raus(self):
        mock = MockSupabaseClient()
        self._store(mock).add({"title": "T", "relevance": None, "score": None})
        rows = mock.upserts[-1][1]
        self.assertNotIn("relevance", rows[0])   # None-Felder gehen nicht an Supabase (Defaults greifen)

    def test_add_offline_fall_b(self):
        r = self._store(SupabaseClient(SupabaseAuth())).add({"title": "T"})
        self.assertTrue(r["fall_b"])


if __name__ == "__main__":
    unittest.main()
