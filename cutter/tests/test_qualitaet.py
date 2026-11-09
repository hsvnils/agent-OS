"""Kontrolle am fertigen Video (CUTTER_AUSBAU C1): erzeugte Fehlvideos muessen auffallen, gesunde nicht."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cutter import ffmpeg_ops as fo
from cutter import qualitaet as q
from cutter import reel_daily as rd
from cutter import worker as wk


def _gesund(**neu) -> dict:
    return {"hat_video": True, "breite": 1080, "hoehe": 1920, "fps": 30.0, "dauer": 20.0, "hat_ton": True,
            "ton_hz": 44100, "lufs": -16.0, "true_peak": -1.5, "schwarz": [], "standbild": [], "stille": []} | neu


def _arten(w: dict) -> set:
    return {x["art"] for x in q.bewerte(w)}


class TestRegeln(unittest.TestCase):
    def test_gesund_ohne_befund(self):
        self.assertEqual(q.bewerte(_gesund()), [])

    def test_jede_abweichung_faellt_auf(self):
        faelle = {"format": {"breite": 1920, "hoehe": 1080}, "fps": {"fps": 25.0}, "dauer": {"dauer": 0.4},
                  "ton": {"hat_ton": False}, "stumm": {"lufs": None}, "lautheit": {"lufs": -24.0},
                  "true_peak": {"true_peak": -0.2}, "stille": {"stille": [{"start": 3.0, "dauer": 2.5}]},
                  "schwarz": {"schwarz": [{"start": 0.0, "dauer": 0.8}]},
                  "standbild": {"standbild": [{"start": 4.0, "dauer": 3.0}]}, "video": {"hat_video": False}}
        for art, aenderung in faelle.items():
            with self.subTest(art):
                self.assertIn(art, _arten(_gesund(**aenderung)))

    def test_grenzwerte_noch_in_ordnung(self):
        self.assertEqual(q.bewerte(_gesund(lufs=-13.0, true_peak=-1.0, fps=29.97)), [])

    def test_fast_ganz_schwarz_ist_fehler(self):
        b = q.bewerte(_gesund(schwarz=[{"start": 0.0, "dauer": 19.0}]))
        self.assertEqual(b[0]["stufe"], "fehler")

    def test_kurzes_schwarz_nur_warnung(self):
        b = q.bewerte(_gesund(schwarz=[{"start": 5.0, "dauer": 1.0}]))
        self.assertEqual(b[0]["stufe"], "warnung")

    def test_absichtlich_leise_wird_beim_ton_nicht_bewertet(self):
        w = _gesund(lufs=-33.0, stille=[{"start": 3.0, "dauer": 4.0}])
        self.assertEqual(q.bewerte(w, ziel_lufs=None), [])
        self.assertIn("lautheit", _arten(w))                    # Gegenprobe: mit Ziel faellt es auf
        self.assertIn("ton", {x["art"] for x in q.bewerte(_gesund(hat_ton=False), ziel_lufs=None)})

    def test_anderes_lautheitsziel(self):
        self.assertEqual(q.bewerte(_gesund(lufs=-14.0), ziel_lufs=-14.0), [])
        self.assertIn("lautheit", {x["art"] for x in q.bewerte(_gesund(lufs=-20.0), ziel_lufs=-14.0)})


class TestParser(unittest.TestCase):
    def test_liest_alle_werte(self):
        t = ("[blackdetect @ 0x1] black_start:1.5 black_end:2.5 black_duration:1\n"
             "lavfi.freezedetect.freeze_start: 4.2\nlavfi.freezedetect.freeze_duration: 2.8\n"
             "[silencedetect @ 0x2] silence_start: 7\n[silencedetect @ 0x2] silence_end: 9.5 | silence_duration: 2.5\n"
             "[Parsed_ebur128_0 @ 0x3] Summary:\n\n  Integrated loudness:\n    I:         -15.9 LUFS\n"
             "    Threshold: -26.0 LUFS\n\n  True peak:\n    Peak:       -1.4 dBFS\n")
        m = q.lies_messung(t)
        self.assertEqual((m["lufs"], m["true_peak"]), (-15.9, -1.4))
        self.assertEqual(m["schwarz"], [{"start": 1.5, "dauer": 1.0}])
        self.assertEqual(m["standbild"], [{"start": 4.2, "dauer": 2.8}])
        self.assertEqual(m["stille"], [{"start": 7.0, "dauer": 2.5}])

    def test_standbild_bis_zum_ende(self):
        m = q.lies_messung("lavfi.freezedetect.freeze_start: 3\n", 10.0)
        self.assertEqual(m["standbild"], [{"start": 3.0, "dauer": 7.0}])

    def test_minus_unendlich_ist_kein_wert(self):
        m = q.lies_messung("Summary:\n  I:  -inf LUFS\n  Peak:  -inf dBFS\n")
        self.assertIsNone(m["lufs"])
        self.assertIsNone(m["true_peak"])


class TestMeldung(unittest.TestCase):
    def test_ohne_befund_keine_meldung(self):
        self.assertEqual(q.als_text({"gemessen": True, "ok": True, "befunde": []}), "")
        self.assertEqual(q.als_text(None), "")

    def test_befund_und_messfehler_werden_gemeldet(self):
        t = q.als_text({"gemessen": True, "ok": False, "befunde": [{"art": "fps", "stufe": "fehler", "text": "Bildrate 25"}]})
        self.assertIn("Bildrate 25", t)
        self.assertIn("nicht möglich", q.als_text({"gemessen": False, "ok": None, "fehler": "kaputt", "befunde": []}))

    def test_worker_haengt_befund_an_und_reicht_trotzdem_ein(self):
        res = {"ok": True, "reel": "/x.mp4", "dauer_sek": 20, "verwendet": 3, "datum": "d", "thema": "t", "caption": "c",
               "spiele": [], "qualitaet": {"gemessen": True, "ok": False,
                                            "befunde": [{"art": "fps", "stufe": "fehler", "text": "Bildrate 25"}]}}
        br = mock.Mock()
        br.reel_einreichen.return_value = {"ok": True}
        with mock.patch.object(wk.reel_daily, "lauf", return_value=res), mock.patch.object(wk.melden, "sende_text") as st:
            wk.verarbeite_reel_job({"id": "1", "projekt": "P"}, source=Path("."), outbox=Path("."), state=Path("."),
                                   bridge=br, token="t", chat="c")
        br.reel_einreichen.assert_called_once()                 # C1 misst nur, sperrt nicht
        self.assertIn("Bildrate 25", st.call_args[0][2])

    def test_nachtlauf_meldet_nur_bei_befund(self):
        with mock.patch.object(rd.melden, "sende_text") as st, \
                mock.patch("cutter.pipeline._lade_env", return_value={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_ALLOWED_CHAT_ID": "c"}):
            self.assertFalse(rd._melde_qualitaet({"qualitaet": {"gemessen": True, "ok": True, "befunde": []}}))
            st.assert_not_called()
            rd._melde_qualitaet({"spiel": "S", "qualitaet": {"gemessen": True, "ok": True,
                                 "befunde": [{"art": "stille", "stufe": "warnung", "text": "Stille bei 3 s"}]}})
            self.assertIn("Stille bei 3 s", st.call_args[0][2])


@unittest.skipUnless(fo.ffmpeg_vorhanden() and fo.hat_filter("ebur128") and fo.hat_filter("freezedetect"), "ffmpeg-Filter fehlen")
class TestEchteVideos(unittest.TestCase):
    """Gegenprobe mit echten Dateien: dasselbe Messwerkzeug muss gesund und kaputt unterscheiden."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _baue(self, video: str, audio: str | None, dauer: int = 4) -> Path:
        ziel = Path(self._tmp.name) / "probe.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(dauer), "-i", video]
        if audio:
            cmd += ["-f", "lavfi", "-t", str(dauer), "-i", audio, "-c:a", "aac", "-shortest"]
        subprocess.run(cmd + ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(ziel)], check=True)
        return ziel

    BILD, TON = "testsrc2=s=1080x1920:r=30", "sine=f=440:r=44100,volume=0.25"

    def _arten(self, video, audio) -> set:
        e = q.pruefe_video(self._baue(video, audio), ziel_lufs=-34.0)
        self.assertTrue(e["gemessen"], e)
        return {x["art"] for x in e["befunde"]}

    def test_gesund(self):
        e = q.pruefe_video(self._baue(self.BILD, self.TON), ziel_lufs=-34.0)
        self.assertEqual(e["befunde"], [], e.get("werte"))
        self.assertTrue(e["ok"])
        self.assertIsNotNone(e["werte"]["lufs"])

    def test_falsches_format(self):
        self.assertIn("format", self._arten("testsrc2=s=1920x1080:r=30", self.TON))

    def test_falsche_bildrate(self):
        self.assertIn("fps", self._arten("testsrc2=s=1080x1920:r=25", self.TON))

    def test_schwarz(self):
        self.assertIn("schwarz", self._arten("color=c=black:s=1080x1920:r=30", self.TON))

    def test_standbild(self):
        self.assertIn("standbild", self._arten("color=c=red:s=1080x1920:r=30", self.TON))

    def test_stumm(self):
        self.assertIn("stumm", self._arten(self.BILD, "anullsrc=r=44100:cl=stereo"))

    def test_ohne_tonspur(self):
        self.assertIn("ton", self._arten(self.BILD, None))

    def test_unlesbar_wirft_nicht(self):
        p = Path(self._tmp.name) / "kaputt.mp4"
        p.write_bytes(b"kein video")
        e = q.pruefe_video(p)
        self.assertEqual((e["gemessen"], e["ok"]), (False, None))


class TestEinbindung(unittest.TestCase):
    @unittest.skipUnless(fo.ffmpeg_vorhanden(), "ffmpeg nicht installiert")
    def test_pipeline_traegt_ergebnis_ein_und_uebersteht_absturz(self):
        from cutter import pipeline as pl
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for n in ("a", "b"):
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "4", "-i", "testsrc2=s=1280x720:r=30",
                                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / f"{n}.mp4")], check=True)
            b = pl.schneide_ordner(d, transkribieren=False, gemini=False)
            self.assertTrue(b["ok"])
            self.assertIn("qualitaet", b)
            self.assertTrue(b["qualitaet"]["gemessen"], b["qualitaet"])
            with mock.patch.object(pl.qualitaet, "pruefe_video", side_effect=RuntimeError("Boom")):
                b2 = pl.schneide_ordner(d, ausgabe=d / "zwei.mp4", transkribieren=False, gemini=False)
            self.assertTrue(b2["ok"])
            self.assertFalse(b2["qualitaet"]["gemessen"])
