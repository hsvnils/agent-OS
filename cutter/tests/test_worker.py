"""Tests fuer den Cutter-Worker (MACO470): Job-Erkennung, Themen-Aufloesung, Reel-Job-Ablauf."""
import json
import unittest

from cutter import reel_select, worker


class TestManuelleThemen(unittest.TestCase):
    def test_torjubel_vorhanden(self):
        self.assertEqual(reel_select.THEMA_TAGS["Torjubel"], {"tor", "jubel"})
        self.assertIn("Torjubel", reel_select.MANUELLE_THEMEN)

    def test_thema_by_name(self):
        t = reel_select.thema_by_name("torjubel")               # case-insensitive
        self.assertIsNotNone(t)
        self.assertEqual(t[0], "Torjubel")
        for leer in ("gibtsnicht", "", None):
            self.assertIsNone(reel_select.thema_by_name(leer))

    def test_manuelle_themen_sind_echte_themen(self):
        """Jedes anwaehlbare Thema muss aufloesbar sein UND ein Tag-Mapping haben."""
        for name in reel_select.MANUELLE_THEMEN:
            self.assertIsNotNone(reel_select.thema_by_name(name), name)
            self.assertTrue(reel_select.THEMA_TAGS.get(name), name)


class TestJobErkennung(unittest.TestCase):
    def test_reel_job(self):
        note = json.dumps({"typ": "reel", "thema": "Torjubel", "spiel": None, "alle_spiele": True,
                           "min_dauer": 15, "max_dauer": 45})
        p = worker.reel_params({"note": note})
        self.assertIsNotNone(p)
        self.assertEqual(p["thema"], "Torjubel")
        self.assertTrue(p["alle_spiele"])

    def test_kein_reel_job(self):
        """Ordner-Jobs und Muell duerfen NICHT als Reel-Job durchgehen."""
        for note in (None, "", "normale Notiz", json.dumps({"typ": "cut"}), json.dumps([1, 2]), "{kaputt"):
            self.assertIsNone(worker.reel_params({"note": note}), note)
        self.assertIsNone(worker.reel_params({}))


class FakeBridge:
    """Minimal-Bridge: protokolliert Meldungen und das Einreichen."""
    def __init__(self, einreichen_ok=True):
        self.meldungen, self.eingereicht, self._ok = [], [], einreichen_ok

    def aktiv(self):
        return True

    def melden(self, **kw):
        self.meldungen.append(kw)

    def reel_einreichen(self, pfad, meta):
        self.eingereicht.append((pfad, meta))
        return {"ok": True, "id": "R1"} if self._ok else None


class TestReelJobAblauf(unittest.TestCase):
    def setUp(self):
        self.job = {"id": "J1", "projekt": "🎬 Reel · Torjubel · alle Spiele",
                    "note": json.dumps({"typ": "reel", "thema": "Torjubel", "alle_spiele": True,
                                        "min_dauer": 15, "max_dauer": 40})}
        self._orig = worker.reel_daily.lauf

    def tearDown(self):
        worker.reel_daily.lauf = self._orig

    def _run(self, ergebnis, bridge=None):
        aufrufe = {}

        def fake_lauf(**kw):
            aufrufe.update(kw)
            return ergebnis
        worker.reel_daily.lauf = fake_lauf
        b = bridge or FakeBridge()
        worker.verarbeite_reel_job(self.job, source="/src", outbox="/out", state="/st", bridge=b)
        return aufrufe, b

    def test_erfolg_reicht_ein_und_meldet_done(self):
        kw, b = self._run({"ok": True, "reel": "/out/r.mp4", "dauer_sek": 32.0, "verwendet": 8,
                           "datum": "2026-08-10", "thema": "Torjubel", "caption": "c", "spiele": ["A"]})
        # Parameter aus dem note-JSON korrekt durchgereicht
        self.assertEqual(kw["thema_name"], "Torjubel")
        self.assertTrue(kw["alle_spiele"])
        self.assertEqual(kw["min_dauer"], 15.0)
        self.assertEqual(kw["ziel_dauer"], 40.0)
        self.assertTrue(kw["schnell_index"])
        # erst running (Claim), dann done; genau ein Einreichen
        self.assertEqual([m["status"] for m in b.meldungen], ["running", "done"])
        self.assertEqual(len(b.eingereicht), 1)
        self.assertEqual(b.eingereicht[0][0], "/out/r.mp4")

    def test_zu_kurz_wird_nicht_eingereicht(self):
        _, b = self._run({"ok": False, "zu_kurz": True, "dauer_sek": 9.0,
                          "fehler": "Reel nur 9s (Mindestlaenge 15s)"})
        self.assertEqual([m["status"] for m in b.meldungen], ["running", "failed"])
        self.assertEqual(b.eingereicht, [])
        self.assertIn("15s", b.meldungen[-1]["fehler"])

    def test_absturz_wird_gefangen(self):
        def boom(**kw):
            raise RuntimeError("ffmpeg weg")
        worker.reel_daily.lauf = boom
        b = FakeBridge()
        worker.verarbeite_reel_job(self.job, source="/src", outbox="/out", state="/st", bridge=b)
        self.assertEqual(b.meldungen[-1]["status"], "failed")     # Worker laeuft weiter
        self.assertIn("ffmpeg weg", b.meldungen[-1]["fehler"])

    def test_einreichen_fehlgeschlagen_bleibt_done_mit_hinweis(self):
        """Offline (Camp): Reel ist gebaut, Einreichen scheitert -> kein Datenverlust, klarer Hinweis."""
        _, b = self._run({"ok": True, "reel": "/out/r.mp4", "dauer_sek": 30.0, "verwendet": 6,
                          "datum": "d", "thema": "Torjubel", "caption": "c", "spiele": []},
                         bridge=FakeBridge(einreichen_ok=False))
        self.assertEqual(b.meldungen[-1]["status"], "done")
        self.assertIn("fehlgeschlagen", b.meldungen[-1]["note"])


if __name__ == "__main__":
    unittest.main()
