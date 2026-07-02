import tempfile
import unittest
from pathlib import Path

from orchestrator.core.crm import CrmStore
from orchestrator.core.crm_projection import SupabaseCrmProjection
from orchestrator.core.crm_sync import CrmSync
from orchestrator.governance.supabase import MockSupabaseClient, SupabaseAuth, SupabaseClient


class TestCrmSync(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.s = CrmStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def _sync(self, mock, name="cursor.txt"):
        return CrmSync(self.s, mock, cursor_path=Path(self.dir.name) / name)

    def test_pull_uebernimmt_hcc_statuswechsel(self):
        self.s.nachricht_erfassen("Acme", "hi", extern_id="m1")   # lokal Status 'neu'
        mock = MockSupabaseClient()
        mock.rows["crm_companies"] = [{"firma": "Acme", "status": "vereinbart",
                                       "updated_at": "2026-07-02T10:00:00"}]
        r = self._sync(mock).pull()
        self.assertTrue(r["ok"])
        self.assertEqual(r["uebernommen"], 1)
        self.assertEqual(self.s.firmen()[0]["status"], "vereinbart")   # HCC-Aenderung lokal uebernommen

    def test_pull_todo_erledigt(self):
        tid = self.s.todo_hinzufuegen("Acme", "nachfassen")
        mock = MockSupabaseClient()
        mock.rows["crm_todos"] = [{"id": tid, "updated_at": "2026-07-02T10:00:00"}]
        self._sync(mock, "c2.txt").pull()
        self.assertEqual(len(self.s.todos(nur_offen=True)), 0)   # per HCC erledigt

    def test_idempotent_kein_doppel(self):
        self.s.nachricht_erfassen("Acme", "hi", extern_id="m1")
        mock = MockSupabaseClient()
        mock.rows["crm_companies"] = [{"firma": "Acme", "status": "angebot",
                                       "updated_at": "2026-07-02T10:00:00"}]
        sync = self._sync(mock, "c3.txt")
        sync.pull()
        events_1 = len(list(open(Path(self.dir.name) / "log.jsonl")))
        sync.pull()   # gleiche Zeile nochmal -> kein neues Event (Status schon gesetzt)
        events_2 = len(list(open(Path(self.dir.name) / "log.jsonl")))
        self.assertEqual(events_1, events_2)

    def test_uebernehmen_projiziert_nicht_zurueck(self):
        mock = MockSupabaseClient()
        s = CrmStore(Path(self.dir.name) / "np.jsonl", projektor=SupabaseCrmProjection(mock))
        s.nachricht_erfassen("Acme", "hi", extern_id="m1")   # das projiziert (Write-Through)
        n_before = len(mock.upserts)
        s.uebernehmen_status_extern("Acme", "angebot")       # darf NICHT zurueckprojizieren (Loop-Schutz)
        self.assertEqual(len(mock.upserts), n_before)

    def test_fall_b_ohne_client(self):
        sync = self._sync(SupabaseClient(SupabaseAuth()), "c4.txt")
        self.assertTrue(sync.pull()["fall_b"])


if __name__ == "__main__":
    unittest.main()
