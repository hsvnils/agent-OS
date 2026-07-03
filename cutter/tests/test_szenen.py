import types
import unittest

from cutter import ffmpeg_ops as fo
from cutter import pipeline


class TestParseSzenen(unittest.TestCase):
    def test_parst_pts_times(self):
        text = (
            "[Parsed_showinfo_1 @ 0x0] n:0 pts:123 pts_time:1.5 pos:1 fmt:yuv420p\n"
            "[Parsed_showinfo_1 @ 0x0] n:1 pts:456 pts_time:4.25 pos:2 fmt:yuv420p\n"
        )
        self.assertEqual(fo._parse_szenen_pts(text), [1.5, 4.25])

    def test_leere_ausgabe(self):
        self.assertEqual(fo._parse_szenen_pts("keine szenen hier"), [])

    def test_sortiert(self):
        text = "pts_time:9.0 x\npts_time:2.0 y\n"
        self.assertEqual(fo._parse_szenen_pts(text), [2.0, 9.0])


class TestBrollStart(unittest.TestCase):
    def setUp(self):
        self._orig = fo.szenen_zeiten

    def tearDown(self):
        pipeline.fo.szenen_zeiten = self._orig

    def _info(self, dauer):
        return types.SimpleNamespace(dauer=dauer, pfad="clip.mp4")

    def _patch_szenen(self, cuts):
        pipeline.fo.szenen_zeiten = lambda pfad, **kw: cuts

    def test_waehlt_laengste_szene(self):
        # Szenen: [0-1], [1-2], [2-9], [9-10] -> laengste ist 2..9 -> Start ~2.3
        self._patch_szenen([1.0, 2.0, 9.0])
        start = pipeline._broll_start(self._info(10.0), 3.2, {})
        self.assertAlmostEqual(start, 2.3, places=1)

    def test_abgeschaltet_nutzt_default(self):
        self._patch_szenen([1.0, 2.0, 9.0])
        start = pipeline._broll_start(self._info(10.0), 3.2, {"CUTTER_SZENEN": "0"})
        self.assertAlmostEqual(start, 2.0, places=1)          # 20 % von 10 s

    def test_keine_szenen_nutzt_default(self):
        self._patch_szenen([])
        start = pipeline._broll_start(self._info(10.0), 3.2, {})
        self.assertAlmostEqual(start, 2.0, places=1)

    def test_zu_kurzer_clip_nutzt_default(self):
        # Bei kurzer Dauer wird gar nicht erst gesucht (Szenen-Callback darf nicht aufgerufen werden).
        def _boom(*a, **k):
            raise AssertionError("szenen_zeiten sollte bei kurzem Clip nicht aufgerufen werden")
        pipeline.fo.szenen_zeiten = _boom
        start = pipeline._broll_start(self._info(1.2), 3.2, {})
        self.assertGreaterEqual(start, 0.0)

    def test_start_bleibt_im_clip(self):
        self._patch_szenen([1.0])
        start = pipeline._broll_start(self._info(5.0), 3.2, {})
        self.assertLessEqual(start, 5.0 - 0.5)


if __name__ == "__main__":
    unittest.main()
