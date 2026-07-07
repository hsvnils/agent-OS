"""Self-Checks fuer den Reel-Freigabe-Store (Reel-Pipeline Stufe C), offline und ohne Kosten."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.reel_store import ReelStore


class TestReelStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = ReelStore(self.tmp / "log.jsonl")

    def test_einreichen_und_holen(self):
        rid = self.store.einreichen(datum="2026-07-07", thema="Fan-Stimmung", caption="cap",
                                    video="/x/reel.mp4", spiele=["A vs B"], dauer_sek=41.4)
        r = self.store.holen(rid)
        self.assertEqual(r["status"], "wartet")
        self.assertEqual(r["thema"], "Fan-Stimmung")
        self.assertEqual(r["spiele"], ["A vs B"])

    def test_freigeben_und_status_folgen(self):
        rid = self.store.einreichen(datum="2026-07-07", thema="T", caption="c", video="/x.mp4")
        self.assertTrue(self.store.status_setzen(rid, "freigegeben"))
        self.assertEqual(self.store.holen(rid)["status"], "freigegeben")
        self.assertTrue(self.store.status_setzen(rid, "gepostet", fb_video_id="123"))
        self.assertEqual(self.store.holen(rid)["fb_video_id"], "123")

    def test_unbekannter_status_oder_id(self):
        rid = self.store.einreichen(datum="d", thema="t", caption="c", video="/x.mp4")
        self.assertFalse(self.store.status_setzen(rid, "quatsch"))
        self.assertFalse(self.store.status_setzen("gibtsnicht", "freigegeben"))

    def test_liste_filtert_nach_status(self):
        a = self.store.einreichen(datum="d1", thema="t", caption="c", video="/a.mp4")
        self.store.einreichen(datum="d2", thema="t", caption="c", video="/b.mp4")
        self.store.status_setzen(a, "freigegeben")
        self.assertEqual(len(self.store.liste()), 2)
        self.assertEqual([r["id"] for r in self.store.liste(status="freigegeben")], [a])
        self.assertEqual(len(self.store.liste(status="wartet")), 1)


if __name__ == "__main__":
    unittest.main()
