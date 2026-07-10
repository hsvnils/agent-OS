"""Tests fuer Clip-Brain Stufe 1: ffmpeg-Ausgabe-Parser, Qualitaets-Score, Signatur-Cache/Limit."""
import json
import tempfile
import unittest
from pathlib import Path

from cutter import clip_brain as cb

EBUR128 = """
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -18.4 LUFS
    Threshold: -28.6 LUFS
"""
SILENCE = """
[silencedetect @ 0x1] silence_start: 1.02
[silencedetect @ 0x1] silence_end: 2.52 | silence_duration: 1.5
[silencedetect @ 0x1] silence_end: 5.0 | silence_duration: 0.75
"""
BLACK = "[blackdetect @ 0x1] black_start:0 black_end:0.8 black_duration:0.8\n" \
        "[blackdetect @ 0x1] black_start:9 black_end:9.4 black_duration:0.4\n"
YAVG = "lavfi.signalstats.YAVG=4.0\nlavfi.signalstats.YAVG=6.0\nlavfi.signalstats.YAVG=8.0\n"


class TestParser(unittest.TestCase):
    def test_lufs(self):
        self.assertEqual(cb._parse_lufs(EBUR128), -18.4)
        self.assertIsNone(cb._parse_lufs("nix"))

    def test_stille_summe(self):
        self.assertAlmostEqual(cb._parse_stille(SILENCE), 2.25)
        self.assertEqual(cb._parse_stille(""), 0.0)

    def test_schwarz_summe(self):
        self.assertAlmostEqual(cb._parse_schwarz(BLACK), 1.2)

    def test_yavg_mittel(self):
        self.assertEqual(cb._parse_yavg(YAVG), 6.0)
        self.assertIsNone(cb._parse_yavg("keine metadaten"))


class TestFormatUndScore(unittest.TestCase):
    def test_format_label(self):
        self.assertEqual(cb.format_label(1080, 1920), "hoch")
        self.assertEqual(cb.format_label(1920, 1080), "quer")
        self.assertEqual(cb.format_label(1000, 1000), "quadrat")
        self.assertEqual(cb.format_label(0, 0), "")

    def test_score_guter_clip(self):
        q = cb.qualitaets_score({"breite": 1080, "hoehe": 1920, "dauer": 10, "hat_audio": True,
                                 "lufs": -16.0, "stille_sek": 0.0, "schwarz_sek": 0.0,
                                 "schaerfe_yavg": 9.0})
        self.assertGreaterEqual(q["gesamt"], 90)
        self.assertEqual(q["teil"]["aufloesung"], 1.0)

    def test_score_schlechter_clip(self):
        q = cb.qualitaets_score({"breite": 320, "hoehe": 240, "dauer": 10, "hat_audio": False,
                                 "lufs": None, "stille_sek": 8.0, "schwarz_sek": 5.0,
                                 "schaerfe_yavg": 1.0})
        self.assertLessEqual(q["gesamt"], 35)

    def test_score_grenzen_und_neutral(self):
        q = cb.qualitaets_score({"dauer": 5})            # alles unbekannt -> weder 0 noch 100
        self.assertTrue(0 < q["gesamt"] < 100)


class TestArchivIndex(unittest.TestCase):
    def _archiv(self, d: Path, clips=3) -> Path:
        spiel = d / "HSV vs FCB - 2026-05-01"           # muss ist_spielordner() erfuellen ("vs")
        spiel.mkdir(parents=True)
        for i in range(clips):
            (spiel / f"clip{i}.mp4").write_bytes(b"x")
        return d

    def test_cache_und_limit(self):
        with tempfile.TemporaryDirectory() as t:
            src = self._archiv(Path(t) / "src")
            idx = Path(t) / "index.json"
            karte = {"breite": 1080, "hoehe": 1920, "dauer": 5.0, "fps": 30.0, "codec": "h264",
                     "bitrate": 1, "hat_audio": True, "format": "hoch", "qualitaet": 80,
                     "qualitaet_teil": {}}
            orig_analyse = cb.analysiere_clip
            orig_ffmpeg = cb.fo.ffmpeg_vorhanden
            cb.analysiere_clip = lambda p, **kw: dict(karte)
            cb.fo.ffmpeg_vorhanden = lambda: True
            try:
                r1 = cb.baue_archiv_index(src, idx, limit=2)
                self.assertTrue(r1["ok"])
                self.assertEqual(r1["analysiert"], 2)     # Limit greift
                self.assertEqual(r1["offen"], 1)

                r2 = cb.baue_archiv_index(src, idx)       # Rest, Cache greift fuer die ersten beiden
                self.assertEqual(r2["analysiert"], 1)
                self.assertEqual(r2["uebersprungen"], 2)
                self.assertEqual(r2["gesamt"], 3)

                r3 = cb.baue_archiv_index(src, idx)       # nichts mehr zu tun
                self.assertEqual(r3["analysiert"], 0)
                self.assertEqual(r3["uebersprungen"], 3)
            finally:
                cb.analysiere_clip, cb.fo.ffmpeg_vorhanden = orig_analyse, orig_ffmpeg

            gespeichert = json.loads(idx.read_text("utf-8"))
            self.assertEqual(len(gespeichert["clips"]), 3)
            eine = next(iter(gespeichert["clips"].values()))
            self.assertEqual(eine["spiel"], "HSV vs FCB - 2026-05-01")
            self.assertEqual(eine["stufe"], 1)
            self.assertIn("sig", eine)

    def test_quelle_fehlt(self):
        with tempfile.TemporaryDirectory() as t:
            r = cb.baue_archiv_index(Path(t) / "gibtsnicht", Path(t) / "i.json")
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
