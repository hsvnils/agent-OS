"""REELS_ROADMAP Etappe 1: Verfall nach 30 Tagen, Videos abgelehnter/verfallener Reels nach 14 Tagen loeschen
(gepostete nie), Nachschub-Bremse ab 10 wartenden, Betriebs-Wacht wertet eine gebremste Nacht nicht als Ausfall."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.reel_store import ReelStore

HEUTE = date.today()


def _store():
    d = Path(tempfile.mkdtemp()) / "reel_freigabe"
    return ReelStore(d / "log.jsonl"), d


def _reel(st, d, name):
    video = d / f"{name}.mp4"
    video.write_bytes(b"\x00" * 10)
    return st.einreichen(datum=HEUTE.isoformat(), thema=name, caption="c", video=f"/app/reel_freigabe/{name}.mp4"), video


class TestVerfallUndLoeschen(unittest.TestCase):
    def test_1_verfall_ab_tag_31(self):
        st, d = _store()
        rid, video = _reel(st, d, "a")
        frei, _ = _reel(st, d, "b")
        st.status_setzen(frei, "freigegeben")
        self.assertEqual(st.aufraeumen(HEUTE + timedelta(days=30))["verfallen"], [])           # Tag 30: wartet noch
        r = st.aufraeumen(HEUTE + timedelta(days=31))
        self.assertEqual((r["verfallen"], r["geloescht"]), ([rid], []))                         # Video bleibt vorerst
        self.assertEqual(st.holen(rid)["status"], "verfallen")
        self.assertEqual(st.holen(frei)["status"], "freigegeben")
        self.assertTrue(video.exists())
        self.assertEqual(st.wartend(), 0)

    def test_2_loeschen_nach_14_tagen_nur_abgelehnt_und_verfallen(self):
        st, d = _store()
        ab, v_ab = _reel(st, d, "abgelehnt")
        post, v_post = _reel(st, d, "gepostet")
        st.status_setzen(ab, "abgelehnt")
        st.status_setzen(post, "gepostet")
        self.assertEqual(st.aufraeumen(HEUTE + timedelta(days=13))["geloescht"], [])
        self.assertEqual(st.aufraeumen(HEUTE + timedelta(days=14))["geloescht"], [ab])
        self.assertFalse(v_ab.exists())
        self.assertTrue(v_post.exists())                                                        # gepostet: nie
        self.assertTrue(st.holen(ab)["video_geloescht"])
        self.assertEqual(st.aufraeumen(HEUTE + timedelta(days=200)), {"verfallen": [], "geloescht": []})   # idempotent
        self.assertTrue(v_post.exists())

    def test_3_fehlende_datei_und_fremde_endung(self):
        st, d = _store()
        rid = st.einreichen(datum="x", thema="t", caption="c", video="/app/reel_freigabe/weg.mp4")
        fremd = st.einreichen(datum="x", thema="t", caption="c", video="/etc/passwd")
        st.status_setzen(rid, "abgelehnt")
        st.status_setzen(fremd, "abgelehnt")
        r = st.aufraeumen(HEUTE + timedelta(days=20))
        self.assertEqual(r["geloescht"], [rid])                                                 # keine MP4 -> nie anfassen


class TestBremse(unittest.TestCase):
    def test_1_ab_zehn(self):
        st, d = _store()
        for i in range(9):
            _reel(st, d, f"r{i}")
        self.assertEqual(st.bremse(), {"wartet": 9, "bremse": False, "ab": 10})
        _reel(st, d, "r9")
        self.assertTrue(st.bremse()["bremse"])

    def test_2_uebersprungen_zaehlt_fuer_die_wacht(self):
        st, d = _store()
        _reel(st, d, "r")
        vorher = st.zuletzt_aktiv()
        with mock.patch("orchestrator.core.reel_store.datetime") as dt:
            dt.now.return_value.isoformat.return_value = "2099-01-01T03:30:00"
            st.uebersprungen(grund="10 Reels warten", wartet=10)
        self.assertEqual(st.zuletzt_aktiv(), "2099-01-01T03:30:00")
        self.assertNotEqual(st.zuletzt_eingereicht(), "2099-01-01T03:30:00")                    # Einreichen unveraendert
        self.assertLess(vorher, st.zuletzt_aktiv())

    def test_3_nachtlauf(self):
        from cutter import reel_daily

        class Br:
            def __init__(self, b): self.b, self.gemeldet = b, []
            def aktiv(self): return True
            def reel_bremse(self): return self.b
            def reel_uebersprungen(self, **kw): self.gemeldet.append(kw)
        an = Br({"wartet": 12, "bremse": True})
        self.assertEqual(reel_daily.gebremst(an)["wartet"], 12)
        self.assertEqual(an.gemeldet[0]["wartet"], 12)
        aus = Br({"wartet": 3, "bremse": False})
        self.assertIsNone(reel_daily.gebremst(aus))
        self.assertEqual(aus.gemeldet, [])
        self.assertIsNone(reel_daily.gebremst(Br(None)))                                        # LUNA-OS weg: schneiden
        with mock.patch.object(reel_daily, "gebremst", return_value={"wartet": 11}), \
                mock.patch.object(reel_daily, "lauf", side_effect=AssertionError("darf nicht schneiden")):
            self.assertEqual(reel_daily.main(["--einreichen"]), 0)
        with mock.patch.object(reel_daily, "gebremst", side_effect=AssertionError("Handlauf nicht bremsen")), \
                mock.patch.object(reel_daily, "lauf", return_value={"ok": False}), \
                mock.patch.object(reel_daily, "_melde_fehlschlag", return_value=True):
            self.assertEqual(reel_daily.main(["--einreichen", "--spiel", "HSV vs X"]), 1)


class TestApi(unittest.TestCase):
    def test_a1_bremse_und_uebersprungen(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        st, d = _store()
        alt = webapp.reel_store
        webapp.reel_store = st
        try:
            c = TestClient(webapp.app)
            self.assertEqual(c.get("/api/reel/bremse").json()["bremse"], False)
            self.assertTrue(c.post("/api/reel/uebersprungen", json={"grund": "Test", "wartet": 10}).json()["ok"])
            self.assertIsNotNone(st.zuletzt_aktiv())
        finally:
            webapp.reel_store = alt


if __name__ == "__main__":
    unittest.main()
