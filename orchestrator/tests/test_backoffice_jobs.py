"""Self-Checks Etappe 4 (FRONTDESK_BACKOFFICE_ROADMAP.md): Nacht-Jobs der Agenten ueber das Backoffice."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core.auftraege import AuftragStore
from orchestrator.core.backends import FallbackBackend
from orchestrator.core.hintergrund import aktiv, hintergrund_modus
from orchestrator.core.notifications import Notifications


class _Primary:
    def __init__(self):
        self.aufrufe = 0

    def respond(self, *a):
        self.aufrufe += 1
        return "aus der Cloud"


def _backend(store, *, worker=None, timeout=60):
    """FallbackBackend mit Backoffice; `worker(store)` spielt je Warte-Takt den MACO-Worker."""
    b = FallbackBackend(_Primary(), backoffice=store, backoffice_timeout=timeout, backoffice_takt=10)
    uhr = [0.0]

    def schlaf(s):
        uhr[0] += s
        if worker:
            worker(store)
    b._schlaf = schlaf
    return b, uhr


class TestBackofficeJobs(unittest.TestCase):
    def setUp(self):
        self.store = AuftragStore(Path(tempfile.mkdtemp()) / "b.jsonl")

    def _worker_erledigt(self, store):
        a = store.naechster()
        if a:
            store.fertig(a["id"], ergebnis="lokales Ergebnis", modell="qwen3:14b", meldung="keine")

    def test_1_ohne_hintergrund_direkt_cloud(self):
        b, _ = _backend(self.store)
        self.assertEqual(b.respond("cfo", "s", "m", {}), "aus der Cloud")
        self.assertEqual(self.store.list(), [])                              # interaktiv: kein Auftrag

    def test_2_im_hintergrund_ueber_backoffice(self):
        b, _ = _backend(self.store, worker=self._worker_erledigt)
        usage = []
        b.on_usage = lambda *a: usage.append(a)
        with hintergrund_modus():
            self.assertTrue(aktiv())
            out = b.respond("cfo", "Du bist der CFO.", "Wo sparen?", {})
        self.assertFalse(aktiv())
        self.assertEqual((out, b.primary.aufrufe), ("lokales Ergebnis", 0))
        a = self.store.list()[0]
        self.assertEqual((a["art"], a["stumm"], a["zweck"]), ("roh", True, "job:cfo"))
        self.assertIn("Du bist der CFO.", a["system"])
        self.assertEqual(usage[0][:2], ("cfo", "qwen3:14b"))                 # Kostenlog: lokal, 0 EUR

    def test_3_fehlgeschlagen_dann_cloud(self):
        def worker(store):
            a = store.naechster()
            if a:
                store.fehlschlag(a["id"], grund="Antwort unbrauchbar", meldung="keine")
        b, _ = _backend(self.store, worker=worker)
        with hintergrund_modus():
            self.assertEqual(b.respond("cto", "s", "m", {}), "aus der Cloud")

    def test_4_zeitlimit_dann_cloud_und_auftrag_abgehakt(self):
        b, uhr = _backend(self.store, timeout=60)                            # kein Worker (MACO aus, BF-02)
        with mock.patch("orchestrator.core.backends.time.monotonic", side_effect=lambda: uhr[0]):
            with hintergrund_modus():
                self.assertEqual(b.respond("cco", "s", "m", {}), "aus der Cloud")
        a = self.store.list()[0]
        self.assertEqual(a["status"], "fehlgeschlagen")
        self.assertIn("Zeitlimit", a["grund"])

    def test_5_meldungen_im_hintergrund_warten_aufs_briefing(self):
        n = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        sofort = n.enqueue("Tagsueber", dedup_stunden=0)
        with hintergrund_modus():
            nacht = n.enqueue("Nachts: neue Content-Ideen", dedup_stunden=0)
        self.assertEqual([e["id"] for e in n.zustellbar()], [sofort])
        self.assertEqual([e["id"] for e in n.fuer_briefing()], [nacht])
        with mock.patch("orchestrator.core.notifications.datetime") as dt:
            from datetime import datetime, timedelta
            dt.now.return_value = datetime.now() + timedelta(hours=6)
            dt.fromisoformat = datetime.fromisoformat
            n.verwerfe_alte(stunden=3)                                       # Lawinenschutz beim Bot-Start
        self.assertEqual([e["id"] for e in n.fuer_briefing()], [nacht])      # ... verwirft Briefing-Meldungen NICHT

    def test_6_stumme_auftraege_ohne_meldung(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        orig = (webapp.backoffice, webapp.notifications)
        d = Path(tempfile.mkdtemp())
        webapp.backoffice, webapp.notifications = AuftragStore(d / "b.jsonl"), Notifications(d / "n.jsonl")
        try:
            aid = webapp.backoffice.anlegen("x", art="roh", stumm=True)
            webapp.backoffice.naechster()
            with mock.patch.object(webapp, "_backoffice_nacht", return_value=False):
                r = TestClient(webapp.app).post("/api/backoffice/ergebnis", json={"id": aid, "ok": True, "ergebnis": "y"}).json()
            self.assertEqual(r["meldung"], "keine")
            self.assertEqual(webapp.notifications.pending(), [])
        finally:
            webapp.backoffice, webapp.notifications = orig


if __name__ == "__main__":
    unittest.main()
