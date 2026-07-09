"""Tests fuer die einstellbaren Werte (Settings-Store, /api/settings-Coercion, Notifier-Filter)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.store import InvestmentStore, SETTINGS_DEFAULTS


class TestSettingsStore(unittest.TestCase):
    def test_defaults_und_override(self):
        with tempfile.TemporaryDirectory() as d:
            st = InvestmentStore(Path(d) / "log.jsonl")
            self.assertEqual(st.settings()["depot_stop_pct"], SETTINGS_DEFAULTS["depot_stop_pct"])
            st.set_setting("depot_stop_pct", 12.5)
            st.set_setting("depot_alerts", False)
            cfg = st.settings()
            self.assertEqual(cfg["depot_stop_pct"], 12.5)
            self.assertFalse(cfg["depot_alerts"])
            # letzte Aenderung gewinnt
            st.set_setting("depot_stop_pct", 5.0)
            self.assertEqual(st.settings()["depot_stop_pct"], 5.0)

    def test_unbekannter_key_abgelehnt(self):
        with tempfile.TemporaryDirectory() as d:
            st = InvestmentStore(Path(d) / "log.jsonl")
            with self.assertRaises(ValueError):
                st.set_setting("gibt_es_nicht", 1)
            st.set_settings({"paper_stop_pct": 9.0, "quatsch": 1})   # unbekannte werden ignoriert
            self.assertEqual(st.settings()["paper_stop_pct"], 9.0)
            self.assertNotIn("quatsch", st.settings())


class TestSettingsEndpoint(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web.app import app
        self.c = TestClient(app)

    def test_get_und_coercion(self):
        r = self.c.get("/api/settings")
        self.assertEqual(r.status_code, 200)
        self.assertIn("depot_stop_pct", r.json())
        # Strings/Ranges werden korrekt gecoerct
        r = self.c.post("/api/settings", json={"settings": {
            "depot_stop_pct": "10", "depot_alerts": "aus", "briefing_morgen_stunde": "30",
            "ruhezeit_von": "", "ruhezeit_bis": "7"}})
        self.assertEqual(r.status_code, 200)
        cfg = r.json()["settings"]
        self.assertEqual(cfg["depot_stop_pct"], 10.0)          # str -> float
        self.assertFalse(cfg["depot_alerts"])                  # "aus" -> False
        self.assertEqual(cfg["briefing_morgen_stunde"], 23)    # 30 -> auf 0..23 geklemmt
        self.assertIsNone(cfg["ruhezeit_von"])                 # "" -> None (aus)
        self.assertEqual(cfg["ruhezeit_bis"], 7)
        # aufraeumen: Defaults zuruecksetzen
        self.c.post("/api/settings", json={"settings": {
            "depot_stop_pct": 8, "depot_alerts": True, "briefing_morgen_stunde": 8, "ruhezeit_bis": ""}})


class TestNotifierFilter(unittest.TestCase):
    def test_alert_erlaubt_und_ruhezeit(self):
        from orchestrator.channels.telegram.bot import _alert_erlaubt, _in_ruhezeit
        cfg = {"alert_investment": False, "alert_crm": True, "ruhezeit_von": 22, "ruhezeit_bis": 7}
        self.assertFalse(_alert_erlaubt(cfg, "investment"))
        self.assertTrue(_alert_erlaubt(cfg, "crm"))
        self.assertTrue(_alert_erlaubt(cfg, "briefing"))       # unbekannte Kategorie -> erlaubt
        # Fenster ueber Mitternacht 22->7
        self.assertTrue(_in_ruhezeit(cfg, 23))
        self.assertTrue(_in_ruhezeit(cfg, 3))
        self.assertFalse(_in_ruhezeit(cfg, 12))
        self.assertFalse(_in_ruhezeit({"ruhezeit_von": None, "ruhezeit_bis": None}, 3))  # aus


if __name__ == "__main__":
    unittest.main()
