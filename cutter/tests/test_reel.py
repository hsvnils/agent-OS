"""Tests fuer die Reel-Pipeline-Auswahl (Stufe B) -- reine Logik, kein ffmpeg noetig."""
import json
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from cutter import reel_select as rs
from cutter import reel_source as rq


def _clip(pfad, spiel, energie):
    return {"pfad": pfad, "spiel": spiel, "energie": energie, "dauer": 4.0, "hat_audio": True}


class TestThemaRotation(unittest.TestCase):
    def test_deterministisch_und_kein_wiederholen(self):
        self.assertEqual(rs.thema_fuer_tag(date(2026, 7, 7)), rs.thema_fuer_tag(date(2026, 7, 7)))
        start = date(2026, 1, 1).toordinal()
        for d in range(0, 40):
            a = rs.thema_fuer_tag(date.fromordinal(start + d))
            b = rs.thema_fuer_tag(date.fromordinal(start + d + 1))
            self.assertNotEqual(a[0], b[0])                # nie zwei Tage am Stueck dasselbe Thema


class TestAuswahl(unittest.TestCase):
    def test_energie_und_spielstreuung(self):
        index = ([_clip(f"g1/{i}.mp4", "Spiel1", 0.9) for i in range(5)]
                 + [_clip(f"g2/{i}.mp4", "Spiel2", 0.9) for i in range(5)]
                 + [_clip(f"g3/{i}.mp4", "Spiel3", 0.1) for i in range(5)])
        aus = rs.waehle_clips(index, ("Tore & Highlights", "hoch", "x"), seed="fix", max_clips=6)
        self.assertTrue(aus)
        self.assertTrue(all(c["energie"] >= 0.55 for c in aus))     # nur hohe Energie
        self.assertGreaterEqual(len({c["spiel"] for c in aus}), 2)  # ueber mehrere Spiele gestreut

    def test_meidet_kuerzlich_genutzte(self):
        index = [_clip(f"g/{i}.mp4", "S", 0.5) for i in range(6)]
        genutzt = {"g/0.mp4", "g/1.mp4", "g/2.mp4"}
        aus = rs.waehle_clips(index, ("Beste Momente", "mix", "x"), genutzt=genutzt, seed="fix", max_clips=3)
        self.assertEqual(len(aus), 3)
        self.assertTrue(all(c["pfad"] not in genutzt for c in aus))


class TestSpielordnerErkennung(unittest.TestCase):
    def test_erkennt_spiele_und_meidet_nicht_spiele(self):
        spiele = ["B04 vs HSV - 16.05.2026", "BMG vs. HSV - 24.08.2025", "HSV 2vs1 Stuttgart - 30.11.2025",
                  "HSV 5 vs Braunschweig 3", "29. Spieltag - VfB Stuttgart - Hamburger SV", "HSV vs BVB"]
        keine = ["A Message for Ludo", "AOOSTAR X Hanserautisch", "DanceForGood-Website",
                 "Community-Einsendungen Aufstiegsfeier", "Biggie & Henning - 30.05.2026"]
        for s in spiele:
            self.assertTrue(rq.ist_spielordner(s), s)
        for n in keine:
            self.assertFalse(rq.ist_spielordner(n), n)


class TestPersistenz(unittest.TestCase):
    def test_lade_genutzte_nur_im_zeitfenster(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "used.jsonl"
            p.write_text(json.dumps({"ts": time.time() - 30 * 86400, "clips": ["alt.mp4"]}) + "\n"
                         + json.dumps({"ts": time.time() - 1 * 86400, "clips": ["neu.mp4"]}) + "\n", "utf-8")
            g = rs.lade_genutzte(p, tage=14)
            self.assertIn("neu.mp4", g)
            self.assertNotIn("alt.mp4", g)

    def test_lade_index_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "clip_index.json"
            p.write_text('{"clips":[{"pfad":"x.mp4","spiel":"S","energie":0.4}]}', "utf-8")
            idx = rq.lade_index(p)
            self.assertTrue(idx and idx[0]["pfad"] == "x.mp4")
            self.assertEqual(rq.lade_index(Path(d) / "fehlt.json"), [])


if __name__ == "__main__":
    unittest.main()
