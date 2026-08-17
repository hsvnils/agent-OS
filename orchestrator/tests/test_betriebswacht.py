"""Tests der Betriebs-Wacht -- sie muss genau die stillen Ausfaelle vom August 2026 erkennen."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.betriebswacht import pruefe
from orchestrator.core.reel_store import ReelStore

JETZT = datetime(2026, 8, 17, 12, 0, 0)


def _vor(minuten: float) -> str:
    return (JETZT - timedelta(minutes=minuten)).isoformat(timespec="seconds")


def _schluessel(befunde) -> set:
    return {b["schluessel"] for b in befunde}


class TestStillerBetrieb(unittest.TestCase):
    def test_alles_ruhig_keine_meldung(self):
        jobs = [{"status": "done", "projekt": "X", "created_at": _vor(500)},
                {"status": "queued", "projekt": "Frisch", "created_at": _vor(5)}]
        self.assertEqual(pruefe(jobs=jobs, herzschlag=_vor(0.5), letztes_reel=_vor(600), jetzt=JETZT), [])

    def test_queue_stau(self):
        jobs = [{"status": "queued", "projekt": "Reel · Torjubel", "created_at": _vor(120)}]
        b = pruefe(jobs=jobs, herzschlag=_vor(0.5), jetzt=JETZT)
        self.assertEqual(_schluessel(b), {"queue_stau"})
        self.assertIn("Torjubel", b[0]["detail"])

    def test_haengender_job(self):
        jobs = [{"status": "running", "projekt": "Reel · lang", "created_at": _vor(400),
                 "updated_at": _vor(300)}]
        self.assertEqual(_schluessel(pruefe(jobs=jobs, herzschlag=_vor(0.5), jetzt=JETZT)), {"job_haengt"})

    def test_laufender_job_im_zeitrahmen_ist_ok(self):
        jobs = [{"status": "running", "projekt": "Reel", "created_at": _vor(10), "updated_at": _vor(10)}]
        self.assertEqual(pruefe(jobs=jobs, herzschlag=_vor(0.5), jetzt=JETZT), [])

    def test_stummer_worker(self):
        """Der eigentliche Ausfall im August: der Worker war tot, ohne dass ein Job wartete."""
        b = pruefe(jobs=[], herzschlag=_vor(240), jetzt=JETZT)
        self.assertEqual(_schluessel(b), {"worker_stumm"})
        self.assertIn("4.0 Stunden", b[0]["detail"])

    def test_ohne_herzschlag_kein_fehlalarm(self):
        """Solange die Web-App den Herzschlag noch nicht schreibt (vor dem Neustart), still bleiben."""
        self.assertEqual(pruefe(jobs=[], herzschlag=None, letztes_reel=None, jetzt=JETZT), [])

    def test_kein_reel_ueber_nacht(self):
        b = pruefe(jobs=[], herzschlag=_vor(0.5), letztes_reel=_vor(60 * 40), jetzt=JETZT)
        self.assertEqual(_schluessel(b), {"kein_reel"})

    def test_reel_von_heute_nacht_ist_ok(self):
        self.assertEqual(pruefe(jobs=[], herzschlag=_vor(0.5), letztes_reel=_vor(60 * 9), jetzt=JETZT), [])

    def test_mehrere_befunde_gleichzeitig(self):
        jobs = [{"status": "queued", "projekt": "A", "created_at": _vor(120)}]
        b = pruefe(jobs=jobs, herzschlag=_vor(240), letztes_reel=_vor(60 * 40), jetzt=JETZT)
        self.assertEqual(_schluessel(b), {"queue_stau", "worker_stumm", "kein_reel"})

    def test_meldetext_ist_konstant(self):
        """Der Text darf keine Minutenangabe enthalten -- sonst greift die Dedup der Notifications nicht
        und der CEO bekaeme alle 15 Minuten dieselbe Warnung."""
        a = pruefe(jobs=[{"status": "queued", "projekt": "A", "created_at": _vor(60)}], jetzt=JETZT)
        c = pruefe(jobs=[{"status": "queued", "projekt": "A", "created_at": _vor(900)}], jetzt=JETZT)
        self.assertEqual(a[0]["text"], c[0]["text"])
        self.assertNotEqual(a[0]["detail"], c[0]["detail"])

    def test_kaputte_zeitstempel_loesen_nichts_aus(self):
        jobs = [{"status": "queued", "projekt": "A", "created_at": "keine-zeit"},
                {"status": "queued", "projekt": "B"}]
        self.assertEqual(pruefe(jobs=jobs, jetzt=JETZT), [])

    def test_zeitzonen_offset_wird_verstanden(self):
        mit_tz = (JETZT - timedelta(minutes=120)).isoformat(timespec="seconds") + "+02:00"
        jobs = [{"status": "queued", "projekt": "A", "created_at": mit_tz}]
        self.assertEqual(_schluessel(pruefe(jobs=jobs, jetzt=JETZT)), {"queue_stau"})


class TestZuletztEingereicht(unittest.TestCase):
    def test_spaetere_freigabe_verfaelscht_den_stempel_nicht(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.jsonl"
            store = ReelStore(p)
            store.einreichen(datum="2026-08-14", thema="Torjubel", caption="c", video="/v.mp4", rid="r1")
            alt = store.zuletzt_eingereicht()
            zeilen = p.read_text("utf-8").splitlines()
            zeilen.append(json.dumps({"typ": "status", "id": "r1", "status": "freigegeben",
                                      "ts": "2026-08-17T11:59:00"}))
            p.write_text("\n".join(zeilen) + "\n", "utf-8")
            # Die Freigabe von heute darf den Einreich-Zeitpunkt nicht auf "heute" ziehen.
            self.assertEqual(ReelStore(p).zuletzt_eingereicht(), alt)
            self.assertEqual(ReelStore(p).liste()[0]["ts"], "2026-08-17T11:59:00")

    def test_ohne_reels_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(ReelStore(Path(d) / "log.jsonl").zuletzt_eingereicht())


if __name__ == "__main__":
    unittest.main()
