"""Paket D L2: feste Sicherungen des LUNA-Desktop (laufen unter Windows; hier ohne Ton/Modell mit Attrappen geprueft)."""
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))
if "probe_l1" not in sys.modules:                       # Windows-Teile (Mikrofon, Stimme) gibt es hier nicht
    _p = types.ModuleType("probe_l1")
    _p.jetzt = lambda: 0.0
    _p.AKTUELL = {}
    sys.modules["probe_l1"] = _p
import luna_desktop as ld  # noqa: E402

from orchestrator.core.desktop_werkzeuge import ERLAUBT, gruppen  # noqa: E402


class TestSicherungen(unittest.TestCase):
    def test_1_bestaetigt_nur_nach_ja(self):
        for satz in ("Ja.", "ja bitte", "Genau, mach das", "Okay", "Passt"):
            self.assertEqual(ld.sicher_bestaetigt({"bestaetigt": True}, satz), ({"bestaetigt": True}, False), satz)
        for satz in ("Trag den Termin ein", "Nein", "Moment mal", "", "Wer ist das?"):
            self.assertEqual(ld.sicher_bestaetigt({"bestaetigt": True, "titel": "x"}, satz),
                             ({"bestaetigt": False, "titel": "x"}, True), satz)
        self.assertEqual(ld.sicher_bestaetigt({"titel": "x"}, "Nein"), ({"titel": "x"}, False))

    def test_2_werkzeugpflicht(self):
        w = ld.Werkzeugpflicht(gruppen(), "LUNA, Nils, Kiez Alm, 3 Legged Thing")
        self.assertIn("kalender_agenda", w.kandidaten("Was steht heute im Kalender?"))
        self.assertIn("todo_anlegen", w.kandidaten("Erinner mich Montag daran"))
        self.assertEqual(w.kandidaten("Wer ist 3 Legged Thing?")[0], "brain_suchen")
        self.assertEqual(w.kandidaten("Was ist mit der Kiez Alm offen?")[0], "brain_suchen")
        self.assertEqual(w.kandidaten("Wie geht es dir?"), [])
        self.assertEqual(w.kandidaten("Erzähl mir einen Witz"), [])
        self.assertTrue(set(sum((g["werkzeuge"] for g in gruppen()), [])) <= set(ERLAUBT))

    def test_3_geklappt(self):
        mb = {"termin_anlegen", "firma_anlegen"}
        self.assertTrue(ld.geklappt("todo_anlegen", json.dumps({"ok": True, "id": "A-1"}), False, mb))
        self.assertFalse(ld.geklappt("todo_anlegen", json.dumps({"ok": False}), False, mb))
        self.assertFalse(ld.geklappt("mail_entwurf", json.dumps({"fehler": "x"}), False, mb))
        self.assertFalse(ld.geklappt("termin_anlegen", json.dumps({"ok": True, "vorschau": {}}), False, mb))  # Vorschau
        self.assertTrue(ld.geklappt("termin_anlegen", json.dumps({"ok": True}), True, mb))
        self.assertFalse(ld.geklappt("termin_anlegen", "kein json", True, mb))
        self.assertTrue(ld.AKTIONEN <= set(ERLAUBT))

    def test_4_behauptung_und_kalender(self):
        self.assertTrue(ld._BEHAUPTUNG.search("Der Termin ist eingetragen."))
        self.assertFalse(ld._BEHAUPTUNG.search("Soll ich den Termin eintragen?"))
        k = ld.kalender_text(datetime(2026, 10, 30, 10, 0))
        self.assertIn("- Freitag 2026-10-30 (heute)", k)
        self.assertIn("- Montag 2026-11-02", k)
        self.assertEqual(ld._ohne_zeit("(Jetzt: Freitag 30.10.2026 10:00) Ja."), "Ja.")


class FakeApi:
    def __init__(self):
        self.aufrufe = []

    def werkzeug(self, name, args, zug):
        self.aufrufe.append((name, dict(args)))
        return json.dumps({"ok": True, "angelegt": bool(args.get("bestaetigt"))})


class TestJaFuehrtVorschauAus(unittest.TestCase):
    def test_ja_bestaetigt_die_vorschau_selbst(self):
        api, prot = FakeApi(), types.SimpleNamespace(schreibe=lambda **k: None)
        spec = [{"type": "function", "function": {"name": "termin_anlegen", "parameters": {
            "properties": {"titel": {}, "start": {}, "bestaetigt": {}}, "required": ["titel", "start"]}}}]
        k = ld.Kopf(api, spec, prot)
        nachrichten, erledigt, erfolge = [], set(), set()
        k._ausfuehren("termin_anlegen", {"titel": "Dreh", "start": "2026-10-31T10:00:00", "bestaetigt": True},
                      "z1", "Trag ein", 0.0, nachrichten, erledigt, erfolge)
        self.assertEqual(api.aufrufe[-1][1]["bestaetigt"], False)                 # ohne Ja nur Vorschau
        self.assertEqual(k.vorschau, ("termin_anlegen", {"titel": "Dreh", "start": "2026-10-31T10:00:00"}))
        self.assertEqual(erfolge, set())
        k._ausfuehren("termin_anlegen", {"titel": "Dreh"}, "z1", "Ja", 0.0, nachrichten, erledigt, erfolge)
        self.assertEqual(len(api.aufrufe), 1)                                      # Pflichtfeld fehlt -> nicht an die NAS
        k._ausfuehren("termin_anlegen", {"titel": "Dreh", "start": "s", "bestaetigt": True}, "z2", "Ja", 0.0,
                      nachrichten, erledigt, erfolge)
        k._ausfuehren("termin_anlegen", {"titel": "Dreh2", "start": "s", "bestaetigt": True}, "z2", "Ja", 0.0,
                      nachrichten, erledigt, erfolge)
        self.assertEqual([a[1].get("bestaetigt") for a in api.aufrufe], [False, True])   # je Zug nur einmal bestaetigt
        self.assertEqual(erfolge, {"termin_anlegen"})


if __name__ == "__main__":
    unittest.main()
