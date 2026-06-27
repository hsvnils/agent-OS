"""Self-Checks Cutter Agent. Logik-Tests laufen ueberall; ffmpeg-Tests nur mit installiertem ffmpeg.

Lauf:  python -m unittest discover -s cutter/tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from cutter import ffmpeg_ops as fo
from cutter import pipeline as pl


class TestLogik(unittest.TestCase):
    def test_1_auf_budget_kuerzt(self):
        mk = lambda d: pl.Auswahl(fo.ClipInfo(Path("x"), d, True, 0, 0), "broll", 0.0, d)
        aus = [mk(20), mk(20), mk(20)]
        gewaehlt = pl._auf_budget(aus, 45.0)
        self.assertEqual(len(gewaehlt), 2)                 # 20+20 passt, 60 nicht

    def test_2_clip_ohne_sprache_ist_broll(self):
        info = fo.ClipInfo(Path("clip.mp4"), 10.0, hat_audio=False, breite=1920, hoehe=1080)
        a = pl._clip_auswaehlen(info, weg="", max_sprache=14.0, broll_dauer=3.2, sprache="de", env={})
        self.assertEqual(a.typ, "broll")
        self.assertGreater(a.start, 0.0)                   # ab ~20 % (wackeliger Anfang weg)
        self.assertLessEqual(a.dauer, 3.2)

    def test_3_srt_zeit_format(self):
        self.assertEqual(pl._srt_zeit(0.5), "00:00:00,500")
        self.assertEqual(pl._srt_zeit(3661.25), "01:01:01,250")

    def test_4_srt_schreiben(self):
        p = Path(tempfile.mkdtemp()) / "u.srt"
        pl._schreibe_srt([(0.5, 3.0, "Hallo"), (3.0, 5.0, "Welt")], p)
        txt = p.read_text(encoding="utf-8")
        self.assertIn("00:00:00,500 --> 00:00:03,000", txt)
        self.assertIn("Hallo", txt)
        self.assertIn("2\n", txt)

    def test_5_clips_im_ordner_sortiert_filtert(self):
        d = Path(tempfile.mkdtemp())
        for n in ["b.mp4", "a.mov", "notiz.txt", ".versteckt.mp4"]:
            (d / n).write_bytes(b"x")
        namen = [p.name for p in fo.clips_im_ordner(d)]
        self.assertEqual(namen, ["a.mov", "b.mp4"])        # sortiert, nur Video, kein Hidden/txt


@unittest.skipUnless(fo.ffmpeg_vorhanden(), "ffmpeg nicht installiert")
class TestFFmpeg(unittest.TestCase):
    def test_6_ordner_zu_reel(self):
        d = Path(tempfile.mkdtemp())
        for i, sz in enumerate(["1280x720", "720x720"]):
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                            f"testsrc=size={sz}:rate=30:duration=2",
                            "-c:v", "libx264", str(d / f"{i}_c.mp4")], capture_output=True)
        bericht = pl.schneide_ordner(d, transkribieren=False, gemini=False)
        self.assertTrue(bericht["ok"], bericht)
        info = fo.probe(Path(bericht["ausgabe"]))
        self.assertEqual((info.breite, info.hoehe), (fo.BREITE, fo.HOEHE))   # 1080x1920


if __name__ == "__main__":
    unittest.main()
