"""CUTTER_AUSBAU C2: Stil v2 (S-Kurve, Lautheit, Schnitt-Grenzen, Schalter). Ohne echtes Archiv."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cutter import ffmpeg_ops as fo
from cutter import pipeline as pl
from cutter import qualitaet


def _werte_aus(frames: int, ziel: float) -> list[float]:
    """Rechnet den echten ffmpeg-Ausdruck nach, statt nur die Python-Kurve zu pruefen."""
    ausdruck = fo.zoom_ausdruck(frames, ziel).replace("min(", "_min(")
    return [eval(ausdruck, {"_min": min, "on": i}) for i in range(frames)]   # noqa: S307 (eigener Ausdruck)


class Kurve(unittest.TestCase):
    def test_anfang_und_ende_exakt(self):
        w = _werte_aus(138, 1.12)
        self.assertAlmostEqual(w[0], 1.0, places=6)
        self.assertAlmostEqual(w[-1], 1.12, places=3)

    def test_keine_spruenge_und_nie_rueckwaerts(self):
        w = _werte_aus(138, 1.12)
        schritte = [b - a for a, b in zip(w, w[1:])]
        self.assertTrue(all(s >= -1e-9 for s in schritte))
        self.assertLess(max(schritte), 0.002)

    def test_ist_nicht_linear(self):
        """Gegenprobe zum alten Zoom: Am Rand kleine Schritte, in der Mitte die groessten."""
        w = _werte_aus(138, 1.12)
        schritte = [b - a for a, b in zip(w, w[1:])]
        self.assertLess(schritte[0], schritte[len(schritte) // 2] / 10)
        self.assertLess(schritte[-1], schritte[len(schritte) // 2] / 10)

    def test_ein_bild_stuerzt_nicht_ab(self):
        self.assertIn("min(on/1,1)", fo.zoom_ausdruck(1))


class Lautheit(unittest.TestCase):
    MESSUNG = {"input_i": "-30.0", "input_tp": "-12.0", "input_lra": "5.0", "input_thresh": "-40.0", "target_offset": "0.2"}

    def test_zweiter_durchgang_nutzt_messwerte(self):
        f = fo.loudnorm_filter(self.MESSUNG, ziel_lufs=-14.0)
        for teil in ("I=-14.0", "measured_I=-30.0", "measured_TP=-12.0", "measured_thresh=-40.0", "offset=0.2", "linear=true", "aresample=48000"):
            self.assertIn(teil, f)

    def test_stille_wird_nie_hochgezogen(self):
        for m in (dict(self.MESSUNG, input_i="-inf"), dict(self.MESSUNG, input_i="-99.0"), None, {}):
            self.assertEqual(fo.loudnorm_filter(m, ziel_lufs=-14.0), "aresample=48000")


class LautesteStelle(unittest.TestCase):
    def test_findet_die_spitze(self):
        text = ("[x] t: 0.4 TARGET:-23 LUFS    M: -120.7 S:-120.7\n[x] t: 2.2 TARGET:-23 LUFS    M: -11.5 S:-20.0\n"
                "[x] t: 3.0 TARGET:-23 LUFS    M: -25.0 S:-18.0\n")
        self.assertEqual(fo.lies_lautesten(text), (2.0, -11.5))

    def test_stille_gibt_nichts(self):
        self.assertIsNone(fo.lies_lautesten("[x] t: 0.4 TARGET:-23 LUFS    M: -120.7 S:-120.7\n"))
        self.assertIsNone(fo.lies_lautesten(""))


class Auswahl(unittest.TestCase):
    @staticmethod
    def _a(name, typ="broll", pegel=None):
        info = fo.ClipInfo(Path(name), 10.0, True, 1080, 1920)
        return pl.Auswahl(info, typ, 0.0, 3.0, [], pegel=pegel)

    def test_staerkster_kommt_nach_vorn_rest_bleibt(self):
        a, b, c = self._a("a", pegel=-30.0), self._a("b", pegel=-12.0), self._a("c", pegel=-20.0)
        neu, geaendert = pl._staerkster_nach_vorn([a, b, c])
        self.assertTrue(geaendert)
        self.assertEqual(neu, [b, a, c])

    def test_sprech_clips_bleiben_unberuehrt(self):
        liste = [self._a("a", typ="sprache"), self._a("b", pegel=-12.0)]
        self.assertEqual(pl._staerkster_nach_vorn(liste), (liste, False))

    def test_ohne_pegel_keine_aenderung(self):
        liste = [self._a("a"), self._a("b")]
        self.assertEqual(pl._staerkster_nach_vorn(liste), (liste, False))

    def test_schnitt_endet_am_satzende(self):
        info = fo.ClipInfo(Path("x"), 40.0, True, 1080, 1920)
        t = [{"start": 0.5, "ende": 6.0, "text": "a"}, {"start": 6.5, "ende": 12.3, "text": "b"}, {"start": 13.0, "ende": 20.0, "text": "c"}]
        self.assertAlmostEqual(pl._dauer_bis_grenze(info, t, 0.3, 14.0), 12.2)

    def test_kurzer_clip_bleibt_ganz(self):
        info = fo.ClipInfo(Path("x"), 40.0, True, 1080, 1920)
        self.assertAlmostEqual(pl._dauer_bis_grenze(info, [{"start": 0.5, "ende": 6.0, "text": "a"}], 0.3, 14.0), 5.9)

    def test_sprechpause_wenn_kein_satzende_passt(self):
        info = fo.ClipInfo(Path("x"), 40.0, True, 1080, 1920)
        t = [{"start": 0.5, "ende": 30.0, "text": "lang"}]
        with mock.patch.object(fo, "stille_spannen", return_value=[(9.0, 9.4), (20.0, 21.0)]):
            self.assertAlmostEqual(pl._dauer_bis_grenze(info, t, 0.3, 14.0), 8.9)

    def test_ohne_jede_grenze_das_limit(self):
        info = fo.ClipInfo(Path("x"), 40.0, True, 1080, 1920)
        with mock.patch.object(fo, "stille_spannen", return_value=[]):
            self.assertEqual(pl._dauer_bis_grenze(info, [{"start": 0.5, "ende": 30.0, "text": "lang"}], 0.3, 14.0), 14.0)


class Schalter(unittest.TestCase):
    def test_standard_und_unsinn(self):
        self.assertEqual(pl._wahl(None, ("v1", "v2"), "v1"), "v1")
        self.assertEqual(pl._wahl("quatsch", ("v1", "v2"), "v1"), "v1")
        self.assertEqual(pl._wahl(" V2 ", ("v1", "v2"), "v1"), "v2")

    def test_ueberblenden_bleibt_ohne_ceo_aenderung_standard(self):
        self.assertEqual(pl._wahl(None, ("weich", "hart"), "weich"), "weich")


class UeberblendKette(unittest.TestCase):
    def test_offsets_laufen_mit_der_kuerzung(self):
        with mock.patch.object(fo, "dauer_von", return_value=4.0):
            filter_, vlabel, alabel = fo._xfade_graph([Path("a"), Path("b"), Path("c")], 0.35)
        self.assertIn("offset=3.650", filter_[0])
        self.assertIn("offset=7.300", filter_[1])
        self.assertEqual((vlabel, alabel), ("[v2]", "[a2]"))


class FehlerGrund(unittest.TestCase):
    def test_grund_bleibt_erhalten(self):
        """BF-92: Der Grund eines gescheiterten Aufrufs darf nicht mehr verschwinden."""
        self.assertFalse(fo._run(["ffmpeg", "-hide_banner", "-i", "/gibt/es/nicht.mp4", "-f", "null", "-"]))
        self.assertIn("nicht.mp4", fo.letzter_fehler)

    def test_erfolg_loescht_alten_grund(self):
        fo.letzter_fehler = "alt"
        self.assertTrue(fo._run(["ffmpeg", "-version"]))
        self.assertEqual(fo.letzter_fehler, "")


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg fehlt")
class EchtesVideo(unittest.TestCase):
    """Rendert kurze Testclips mit 60 fps und prueft das Ergebnis mit der Kontrolle aus C1."""

    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="c2test_"))
        self.addCleanup(shutil.rmtree, self.ordner, ignore_errors=True)

    def _clip(self, name: str, hz: int, dauer: float = 2.0) -> Path:
        p = self.ordner / name
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s=1080x1920:r=60:d={dauer}", "-f", "lavfi",
                        "-i", f"sine=f={hz}:r=44100:d={dauer},volume=0.2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(p)],
                       check=True)
        return p

    def _segment(self, name: str, hz: int, **kw) -> Path:
        ziel = self.ordner / f"seg_{name}"
        self.assertTrue(fo.segment_normalisieren(self._clip(name, hz), ziel, start=0.0, dauer=2.0, hat_audio=True, zoom=True, randschnitt=False, stil="v2", **kw),
                        fo.letzter_fehler)
        return ziel

    def _pruefe(self, weich: bool, ziel_lauf: float, soll_dauer: float):
        segmente = [self._segment("a.mp4", 440, ton_blende=not weich), self._segment("b.mp4", 660, ton_blende=not weich)]
        ziel = self.ordner / "reel.mp4"
        self.assertTrue(fo.zusammenfuegen_v2(segmente, ziel, weich=weich, ziel_lufs=ziel_lauf), fo.letzter_fehler)
        q = qualitaet.pruefe_video(ziel, ziel_lufs=ziel_lauf)
        self.assertTrue(q["gemessen"], q)
        self.assertEqual(q["werte"]["ton_hz"], 48000)
        self.assertEqual((q["werte"]["breite"], q["werte"]["hoehe"]), (1080, 1920))
        self.assertAlmostEqual(q["werte"]["dauer"], soll_dauer, delta=0.15)
        self.assertLessEqual(q["werte"]["true_peak"], -1.0)
        self.assertAlmostEqual(q["werte"]["lufs"], ziel_lauf, delta=1.5)
        self.assertFalse(list(self.ordner.glob("*.roh.mkv")), "Zwischendatei muss weg sein")

    def test_harter_schnitt_kuerzt_nicht(self):
        self._pruefe(False, fo.ZIEL_LUFS_V2, 4.0)

    def test_ueberblenden_kuerzt_um_die_blende(self):
        self._pruefe(True, fo.ZIEL_LUFS_V2, 3.65)

    def test_60_fps_laeuft_in_echtzeit(self):
        """Quelle wird ab 1,5 s weiss. Ohne `fps` vor zoompan zeigt das Segment nur die erste Sekunde und bleibt blau."""
        quelle = self.ordner / "wechsel.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:r=60:d=2,drawbox=c=white:t=fill:enable='gte(t,1.5)'",
                        "-f", "lavfi", "-i", "sine=f=440:r=44100:d=2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(quelle)], check=True)
        ziel = self.ordner / "seg_wechsel.mp4"
        self.assertTrue(fo.segment_normalisieren(quelle, ziel, start=0.0, dauer=2.0, hat_audio=True, zoom=True, randschnitt=False, stil="v2"), fo.letzter_fehler)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-sseof", "-0.2", "-i", str(ziel), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                           capture_output=True, text=True, check=True)
        helligkeit = [float(x.split("=")[1]) for x in r.stderr.splitlines() if "YAVG=" in x]
        self.assertTrue(helligkeit)
        self.assertGreater(helligkeit[-1], 180)


if __name__ == "__main__":
    unittest.main()
