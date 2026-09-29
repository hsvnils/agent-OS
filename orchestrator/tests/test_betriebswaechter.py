"""BETRIEB_ROADMAP Etappe 3 (CEO-Go 2026-09-29): Waechter auf dem MACO470 meldet stille Ausfaelle von LUNA-OS, Bot,
Telegram-Zustellung und Backup -- erst nach zwei Laeufen, einmal, mit Erinnerung je 24 h und „wieder in Ordnung“."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.betriebswaechter import (backup_info, befunde, entscheiden, herzschlag_schreiben, status)

JETZT = datetime(2026, 9, 30, 12, 0)


class TestStatus(unittest.TestCase):
    def test_1_herzschlag_und_outbox(self):
        d = Path(tempfile.mkdtemp())
        t = JETZT.timestamp()
        herzschlag_schreiben(d / "hs.json", t - 10 * 60)
        log = d / "n.jsonl"
        log.write_text("\n".join(json.dumps(e) for e in (
            {"ts": (JETZT - timedelta(minutes=50)).isoformat(), "id": "N1", "typ": "queued"},
            {"ts": (JETZT - timedelta(minutes=49)).isoformat(), "id": "N1", "typ": "sent"},
            {"ts": (JETZT - timedelta(minutes=40)).isoformat(), "id": "N2", "typ": "queued"},
            {"ts": (JETZT - timedelta(minutes=5)).isoformat(), "id": "N3", "typ": "queued"})) + "\nkaputt\n")
        self.assertEqual(status(d / "hs.json", log, jetzt=t),
                         {"bot_alter_min": 10.0, "unzugestellt": 2, "aelteste_unzugestellt_min": 40.0})
        self.assertEqual(status(d / "fehlt.json", d / "fehlt.jsonl", jetzt=t),
                         {"bot_alter_min": None, "unzugestellt": 0, "aelteste_unzugestellt_min": None})

    def test_2_befunde(self):
        gut = {"bot_alter_min": 12, "aelteste_unzugestellt_min": None}
        self.assertEqual(befunde(gut, {"ok": True, "alter_h": 9}), [])
        self.assertEqual(befunde(None, None), ["luna_os"])
        self.assertEqual(befunde({"bot_alter_min": 50, "aelteste_unzugestellt_min": 31}, {"ok": True, "alter_h": 27}),
                         ["bot_stumm", "zustellung", "backup"])
        self.assertEqual(befunde({"bot_alter_min": None}, {"ok": False, "alter_h": 2}), ["bot_stumm", "backup"])

    def test_3_backup_aus_systemctl(self):
        self.assertEqual(backup_info("Result=success\nExecMainExitTimestamp=Wed 2026-09-30 03:20:42 CEST\n", JETZT),
                         {"ok": True, "alter_h": 8.7})
        self.assertEqual(backup_info("Result=exit-code\nExecMainExitTimestamp=Wed 2026-09-30 03:20:42 CEST", JETZT)["ok"],
                         False)
        self.assertEqual(backup_info("Result=success\nExecMainExitTimestamp=n/a", JETZT), {"ok": False, "alter_h": None})
        self.assertIsNone(backup_info("", JETZT))


class TestMelden(unittest.TestCase):
    def test_zwei_laeufe_einmal_erinnern_entwarnen(self):
        m, z = entscheiden(["bot_stumm"], {}, JETZT)                                  # Lauf 1: nur vormerken
        self.assertEqual(m, [])
        m, z = entscheiden(["bot_stumm"], z, JETZT + timedelta(minutes=15))           # Lauf 2: Alarm
        self.assertEqual(len(m), 1)
        self.assertIn("Telegram-Bot", m[0])
        self.assertIn("seit 30.09. 12:00", m[0])
        m, z = entscheiden(["bot_stumm"], z, JETZT + timedelta(hours=5))              # bleibt: kein Spam
        self.assertEqual(m, [])
        m, z = entscheiden(["bot_stumm"], z, JETZT + timedelta(hours=24, minutes=20))  # Erinnerung
        self.assertTrue(m[0].startswith("⏰ Weiterhin"))
        m, z = entscheiden([], z, JETZT + timedelta(hours=25))                        # Entwarnung
        self.assertEqual(m, ["✅ Wieder in Ordnung: Der Telegram-Bot auf der NAS meldet sich nicht mehr (kein Herzschlag)."])
        self.assertEqual(z, {})

    def test_neustart_blip_bleibt_still(self):
        m, z = entscheiden(["luna_os"], {}, JETZT)
        m2, z2 = entscheiden([], z, JETZT + timedelta(minutes=15))
        self.assertEqual((m, m2, z2), ([], [], {}))


class TestApi(unittest.TestCase):
    def test_status_endpunkt(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web.app import app
        r = TestClient(app).get("/api/betrieb/status")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {"bot_alter_min", "unzugestellt", "aelteste_unzugestellt_min"})


if __name__ == "__main__":
    unittest.main()
