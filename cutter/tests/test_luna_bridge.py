"""Self-Checks K5-Bruecke (Mac-Cutter <-> LUNA-OS). Kein Netz -- _req wird ueberschrieben.

Lauf:  python -m unittest discover -s cutter/tests
"""
import unittest

from cutter.luna_bridge import LunaBridge


class TestLunaBridge(unittest.TestCase):
    def test_inaktiv_ohne_config(self):
        b = LunaBridge("", "", "")
        self.assertFalse(b.aktiv())
        self.assertEqual(b.offene_jobs(), [])       # kein Netz-Zugriff, sauber leer
        b.melden(projekt="p", status="done")        # darf nicht crashen

    def test_aktiv_mit_url_und_pw(self):
        self.assertTrue(LunaBridge("https://x", "ceo", "pw").aktiv())
        self.assertFalse(LunaBridge("https://x", "ceo", "").aktiv())   # ohne Passwort inaktiv

    def test_melden_payload(self):
        b = LunaBridge("https://x", "ceo", "pw")
        calls = []
        b._req = lambda pfad, method="GET", data=None: calls.append((pfad, method, data)) or {}
        b.melden(job_id="j1", projekt="p", status="done", clips_verwendet=3, dauer_sek=None, groesse_mb=12.5)
        pfad, method, data = calls[-1]
        self.assertEqual((pfad, method), ("/api/cutter/report", "POST"))
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["job_id"], "j1")
        self.assertEqual(data["clips_verwendet"], 3)
        self.assertEqual(data["groesse_mb"], 12.5)
        self.assertNotIn("dauer_sek", data)          # None-Felder fallen raus

    def test_melden_ohne_job_id(self):
        b = LunaBridge("https://x", "ceo", "pw")
        calls = []
        b._req = lambda pfad, method="GET", data=None: calls.append(data) or {}
        b.melden(projekt="auto", status="running")
        self.assertNotIn("job_id", calls[-1])        # neue Zeile (auto-verarbeitet)
        self.assertEqual(calls[-1]["projekt"], "auto")

    def test_offene_jobs_parst(self):
        b = LunaBridge("https://x", "ceo", "pw")
        b._req = lambda *a, **k: {"jobs": [{"id": "1", "projekt": "hsv"}]}
        self.assertEqual(b.offene_jobs()[0]["projekt"], "hsv")
        b._req = lambda *a, **k: None                 # Fehler/Netz weg
        self.assertEqual(b.offene_jobs(), [])


if __name__ == "__main__":
    unittest.main()
