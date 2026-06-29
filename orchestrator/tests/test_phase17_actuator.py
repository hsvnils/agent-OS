"""Phase 17 (LUNA am Mac) — M3: Aktuator-Tor (Allowlist, Modi, Not-Aus, CEO-Tor-Invariante).

Plattform-sicher: die reine Tor-Logik (plan) wird auf macOS geprueft; modus/allowlist/not-aus ueberall.
Pfade fuer Modus + Not-Aus werden auf temporaere Dateien umgebogen (keine Home-Seiteneffekte).
"""
import tempfile
import unittest
from pathlib import Path

from runner import actuator


class _Patch(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        self._orig_mode = actuator.MODE_PATH
        self._orig_kill = actuator.KILLSWITCH_PATH
        actuator.MODE_PATH = d / "mode"
        actuator.KILLSWITCH_PATH = d / "kill"

    def tearDown(self):
        actuator.MODE_PATH = self._orig_mode
        actuator.KILLSWITCH_PATH = self._orig_kill
        self._tmp.cleanup()


class TestModus(_Patch):
    def test_default_ist_bestaetigen(self):
        self.assertEqual(actuator.get_mode(), actuator.MODE_CONFIRM)

    def test_sofort_setzen_und_lesen(self):
        self.assertEqual(actuator.set_mode("sofort"), actuator.MODE_INSTANT)
        self.assertEqual(actuator.get_mode(), actuator.MODE_INSTANT)
        self.assertEqual(actuator.set_mode("bestaetigen"), actuator.MODE_CONFIRM)
        self.assertEqual(actuator.get_mode(), actuator.MODE_CONFIRM)


class TestAllowlist(_Patch):
    def test_textedit_erlaubt(self):
        self.assertIsNotNone(actuator.allowed("TextEdit", "text_schreiben"))

    def test_unbekanntes_verboten(self):
        self.assertIsNone(actuator.allowed("Mail", "senden"))
        self.assertIsNone(actuator.allowed("TextEdit", "loeschen"))


class TestNotAus(_Patch):
    def test_not_aus_sperrt_plan(self):
        if not actuator.is_macos():
            self.skipTest("plan() erfordert macOS")
        actuator.KILLSWITCH_PATH.write_text("stop\n", encoding="utf-8")
        res = actuator.plan("TextEdit", "text_schreiben", "x")
        self.assertFalse(res["ok"])
        self.assertIn("NOT-AUS", res["grund"])


class TestTorLogik(_Patch):
    def test_benigne_aktion_modi(self):
        if not actuator.is_macos():
            self.skipTest("plan() erfordert macOS")
        actuator.set_mode("bestaetigen")
        p = actuator.plan("TextEdit", "text_schreiben", "Hallo")
        self.assertTrue(p["ok"])
        self.assertTrue(p["bestaetigung_noetig"])  # Standardmodus -> Vorschau

        actuator.set_mode("sofort")
        p = actuator.plan("TextEdit", "text_schreiben", "Hallo")
        self.assertFalse(p["bestaetigung_noetig"])  # Sofort -> direkt

    def test_ceo_tor_immer_bestaetigen_auch_im_sofort(self):
        if not actuator.is_macos():
            self.skipTest("plan() erfordert macOS")
        # CEO-Tor-Verb temporaer in die Allowlist injizieren -> muss IMMER bestaetigt werden.
        actuator.ALLOWLIST.setdefault("TextEdit", {})["_test_ceo"] = {
            "kategorie": "ceo_tor", "beschreibung": "test"}
        try:
            actuator.set_mode("sofort")
            p = actuator.plan("TextEdit", "_test_ceo", "x")
            self.assertTrue(p["ok"])
            self.assertTrue(p["bestaetigung_noetig"])  # trotz Sofort-Modus
        finally:
            actuator.ALLOWLIST["TextEdit"].pop("_test_ceo", None)

    def test_nicht_in_allowlist_blockiert(self):
        if not actuator.is_macos():
            self.skipTest("plan() erfordert macOS")
        p = actuator.plan("Safari", "alles", "x")
        self.assertFalse(p["ok"])


if __name__ == "__main__":
    unittest.main()
