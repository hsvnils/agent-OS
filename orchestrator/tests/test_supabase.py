import json
import unittest

from orchestrator.governance.supabase import (MockSupabaseClient, SupabaseAuth, SupabaseClient)


class FakeFetch:
    """Zeichnet Requests auf und liefert eine vorgegebene Antwort (kein Netz)."""
    def __init__(self, antwort=None):
        self.antwort = antwort
        self.calls = []

    def __call__(self, url, *, method="GET", headers=None, data=None, timeout=15):
        self.calls.append({"url": url, "method": method, "headers": headers,
                           "data": json.loads(data.decode()) if data else None})
        return self.antwort


class TestSupabase(unittest.TestCase):
    def _client(self, fetch):
        return SupabaseClient(SupabaseAuth(url="https://x.supabase.co", service_key="svc"), fetch=fetch)

    def test_from_env(self):
        a = SupabaseAuth.from_env({"SUPABASE_URL": "https://x.supabase.co/", "SUPABASE_SERVICE_ROLE_KEY": "k"})
        self.assertEqual(a.url, "https://x.supabase.co")   # trailing slash entfernt
        self.assertTrue(a.verfuegbar())

    def test_fall_b_ohne_keys(self):
        c = SupabaseClient(SupabaseAuth())
        self.assertTrue(c.upsert("crm_companies", {"name": "X"})["fall_b"])
        self.assertTrue(c.select("crm_companies")["fall_b"])

    def test_upsert_baut_request(self):
        f = FakeFetch()
        r = self._client(f).upsert("crm_companies", {"ref": "acme", "status": "neu"}, on_conflict="ref")
        self.assertTrue(r["ok"])
        self.assertEqual(r["anzahl"], 1)
        call = f.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertIn("/rest/v1/crm_companies", call["url"])
        self.assertIn("on_conflict=ref", call["url"])
        self.assertIn("merge-duplicates", call["headers"]["Prefer"])
        self.assertEqual(call["headers"]["apikey"], "svc")
        self.assertEqual(call["data"], [{"ref": "acme", "status": "neu"}])

    def test_select_baut_request(self):
        f = FakeFetch(antwort=[{"ref": "acme"}])
        r = self._client(f).select("crm_companies", params="select=ref&limit=1")
        self.assertTrue(r["ok"])
        self.assertEqual(r["rows"], [{"ref": "acme"}])
        self.assertEqual(f.calls[0]["method"], "GET")
        self.assertIn("select=ref&limit=1", f.calls[0]["url"])

    def test_fehler_wird_gefangen(self):
        def boom(*a, **k):
            raise RuntimeError("netzwerk weg")
        r = self._client(boom).upsert("crm_companies", {"ref": "x"})
        self.assertFalse(r["ok"])
        self.assertIn("netzwerk weg", r["fehler"])

    def test_mock_client_sammelt(self):
        m = MockSupabaseClient()
        m.upsert("crm_companies", {"ref": "acme"}, on_conflict="ref")
        self.assertEqual(m.upserts[0][0], "crm_companies")
        self.assertEqual(m.upserts[0][2], "ref")


if __name__ == "__main__":
    unittest.main()
