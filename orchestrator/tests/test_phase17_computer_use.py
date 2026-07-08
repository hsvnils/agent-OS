"""Tests fuer den generischen Sprach-Steuer-Loop (Phase 17, M6) -- reine Logik, kein Mac/Gemini noetig."""
import json
import unittest

from runner import actuator
from runner import computer_use as cu


def _decider(*antworten):
    """Baut ein entscheide()-Callable, das der Reihe nach die vorgegebenen Rohantworten liefert."""
    folge = list(antworten)

    def entscheide(ziel, bild, verlauf):
        return folge.pop(0) if folge else json.dumps({"aktion": "fertig", "ergebnis": "fertig", "konfidenz": 1})
    return entscheide


def _shot_ok(breite=1440, hoehe=900):
    return lambda: {"ok": True, "bild": b"PNG", "breite": breite, "hoehe": hoehe}


class TestParse(unittest.TestCase):
    def test_plain_json(self):
        d = cu.parse_aktion('{"aktion":"taste","kuerzel":"cmd+s"}')
        self.assertEqual(d["aktion"], "taste")

    def test_fenced_json(self):
        d = cu.parse_aktion('Klar!\n```json\n{"aktion":"fertig","ergebnis":"ok"}\n```\n')
        self.assertEqual(d["aktion"], "fertig")

    def test_embedded_json(self):
        d = cu.parse_aktion('Ich denke {"aktion":"klick","x":0.5,"y":0.5} passt.')
        self.assertEqual(d["aktion"], "klick")

    def test_garbage(self):
        self.assertIsNone(cu.parse_aktion("kein json hier"))
        self.assertIsNone(cu.parse_aktion(""))


class TestValidieren(unittest.TestCase):
    def test_klick_ok_und_konfidenz_clamp(self):
        r = cu.validiere_aktion({"aktion": "klick", "x": 0.5, "y": 0.2, "konfidenz": 5})
        self.assertTrue(r["ok"])
        self.assertEqual(r["konfidenz"], 1.0)                 # auf 0..1 geklemmt

    def test_klick_ausserhalb_bereich(self):
        self.assertFalse(cu.validiere_aktion({"aktion": "klick", "x": 1.4, "y": 0.2})["ok"])

    def test_klick_ohne_koordinaten(self):
        self.assertFalse(cu.validiere_aktion({"aktion": "klick"})["ok"])

    def test_unbekannte_aktion(self):
        self.assertFalse(cu.validiere_aktion({"aktion": "sprengen"})["ok"])

    def test_tippe_ohne_text(self):
        self.assertFalse(cu.validiere_aktion({"aktion": "tippe", "text": ""})["ok"])

    def test_taste_und_app(self):
        self.assertTrue(cu.validiere_aktion({"aktion": "taste", "kuerzel": "return"})["ok"])
        self.assertTrue(cu.validiere_aktion({"aktion": "oeffne_app", "app": "Safari"})["ok"])

    def test_englische_aliase(self):
        r = cu.validiere_aktion({"action": "click", "x": 0.5, "y": 0.5})
        self.assertTrue(r["ok"]); self.assertEqual(r["aktion"], "klick")
        r = cu.validiere_aktion({"action": "open", "app_name": "Safari"})
        self.assertTrue(r["ok"]); self.assertEqual(r["aktion"], "oeffne_app"); self.assertEqual(r["app"], "Safari")
        r = cu.validiere_aktion({"action": "type", "value": "hallo"})
        self.assertTrue(r["ok"]); self.assertEqual(r["aktion"], "tippe"); self.assertEqual(r["text"], "hallo")
        r = cu.validiere_aktion({"aktion": "taste", "key": "cmd+s"})
        self.assertTrue(r["ok"]); self.assertEqual(r["kuerzel"], "cmd+s")


class TestAppAufloesung(unittest.TestCase):
    def test_synonym_und_exakt(self):
        apps = ["Calculator", "Safari", "Mail"]
        self.assertEqual(actuator.aufloesen_app("Taschenrechner", apps=apps), "Calculator")
        self.assertEqual(actuator.aufloesen_app("rechner", apps=apps), "Calculator")
        self.assertEqual(actuator.aufloesen_app("calculator", apps=apps), "Calculator")   # exakt (ci)
        self.assertEqual(actuator.aufloesen_app("Safari", apps=apps), "Safari")

    def test_teilstring_und_none(self):
        self.assertEqual(actuator.aufloesen_app("safari", apps=["Safari Technology Preview"]),
                         "Safari Technology Preview")
        self.assertIsNone(actuator.aufloesen_app("gibtsnicht xyz", apps=["Calculator"]))
        self.assertIsNone(actuator.aufloesen_app("", apps=["Calculator"]))


class TestGefahr(unittest.TestCase):
    def test_gefahrwort_in_begruendung(self):
        self.assertTrue(cu.ist_gefaehrlich({"aktion": "klick", "begruendung": "Mail jetzt senden"}))
        self.assertTrue(cu.ist_gefaehrlich({"aktion": "klick", "begruendung": "Datei loeschen"}))
        self.assertTrue(cu.ist_gefaehrlich({"aktion": "klick", "begruendung": "Artikel kaufen"}))

    def test_gefahr_taste(self):
        self.assertTrue(cu.ist_gefaehrlich({"aktion": "taste", "kuerzel": "cmd+delete"}))

    def test_benigne_aktion_ungefaehrlich(self):
        self.assertFalse(cu.ist_gefaehrlich({"aktion": "klick", "begruendung": "Adressleiste anklicken"}))
        self.assertFalse(cu.ist_gefaehrlich({"aktion": "taste", "kuerzel": "cmd+l"}))


class TestKoordinaten(unittest.TestCase):
    def test_mapping_und_clamp(self):
        self.assertEqual(cu.map_klick(0.5, 0.5, 1440, 900), (720, 450))
        self.assertEqual(cu.map_klick(0.0, 0.0, 1440, 900), (0, 0))
        self.assertEqual(cu.map_klick(1.5, -0.2, 1440, 900), (1440, 0))   # geklemmt


class TestLoop(unittest.TestCase):
    def _handle_ok(self):
        aufgerufen = []

        def handle(aktion, shot):
            aufgerufen.append(aktion["aktion"])
            return {"ausgefuehrt": True}
        return handle, aufgerufen

    def test_happy_path_bis_fertig(self):
        handle, aufgerufen = self._handle_ok()
        dec = _decider(
            json.dumps({"aktion": "oeffne_app", "app": "Safari", "konfidenz": 0.9, "begruendung": "Safari oeffnen"}),
            json.dumps({"aktion": "taste", "kuerzel": "cmd+l", "konfidenz": 0.9, "begruendung": "Adressleiste"}),
            json.dumps({"aktion": "fertig", "ergebnis": "Safari offen, Adressleiste aktiv", "konfidenz": 1}),
        )
        r = cu.fuehre_ziel_aus("oeffne Safari", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "fertig")
        self.assertEqual(aufgerufen, ["oeffne_app", "taste"])     # zwei benigne Schritte ausgefuehrt

    def test_gefahr_haelt_an_und_fuehrt_nicht_aus(self):
        handle, aufgerufen = self._handle_ok()
        dec = _decider(json.dumps({"aktion": "klick", "x": 0.5, "y": 0.5, "konfidenz": 0.95,
                                   "begruendung": "Senden-Knopf druecken"}))
        r = cu.fuehre_ziel_aus("mail schreiben", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "bestaetigung")
        self.assertEqual(r["grund"], "ceo_tor")
        self.assertEqual(aufgerufen, [])                          # NICHT ausgefuehrt

    def test_niedrige_konfidenz_haelt_an(self):
        handle, aufgerufen = self._handle_ok()
        dec = _decider(json.dumps({"aktion": "klick", "x": 0.5, "y": 0.5, "konfidenz": 0.2,
                                   "begruendung": "vielleicht hier"}))
        r = cu.fuehre_ziel_aus("irgendwas", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "bestaetigung")
        self.assertEqual(r["grund"], "unsicher")
        self.assertEqual(aufgerufen, [])

    def test_not_aus_stoppt_sofort(self):
        handle, aufgerufen = self._handle_ok()
        r = cu.fuehre_ziel_aus("egal", screenshot=_shot_ok(), entscheide=_decider(),
                               handle=handle, gestoppt=lambda: True)
        self.assertEqual(r["status"], "gestoppt")
        self.assertEqual(aufgerufen, [])

    def test_screenshot_fehler(self):
        handle, _ = self._handle_ok()
        r = cu.fuehre_ziel_aus("egal", screenshot=lambda: {"ok": False, "grund": "kein Recht"},
                               entscheide=_decider(), handle=handle)
        self.assertEqual(r["status"], "fehler")

    def test_kaputte_modellantwort(self):
        handle, _ = self._handle_ok()
        # Alle Retry-Versuche liefern kein JSON -> Loop gibt sauber 'fehler' zurueck (kein Absturz).
        r = cu.fuehre_ziel_aus("egal", screenshot=_shot_ok(),
                               entscheide=_decider("kein json", "kein json", "kein json"), handle=handle)
        self.assertEqual(r["status"], "fehler")

    def test_frage_beendet_loop(self):
        handle, aufgerufen = self._handle_ok()
        dec = _decider(json.dumps({"aktion": "frage", "text": "Welche Datei?", "konfidenz": 0.9}))
        r = cu.fuehre_ziel_aus("lade datei hoch", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "frage")
        self.assertEqual(aufgerufen, [])

    def test_max_schritte_deckel(self):
        handle, aufgerufen = self._handle_ok()
        # Modell sagt immer dieselbe benigne Aktion -> nie 'fertig' -> Deckel greift.
        dec = _decider(*([json.dumps({"aktion": "taste", "kuerzel": "down", "konfidenz": 0.9,
                                      "begruendung": "scrollen"})] * 10))
        r = cu.fuehre_ziel_aus("scrolle", screenshot=_shot_ok(), entscheide=dec, handle=handle, max_schritte=3)
        self.assertEqual(r["status"], "max_erreicht")
        self.assertEqual(len(aufgerufen), 3)

    def test_ausfuehrungsfehler_stoppt(self):
        def handle(aktion, shot):
            return {"ausgefuehrt": False, "grund": "Bedienungshilfen fehlen"}
        dec = _decider(json.dumps({"aktion": "taste", "kuerzel": "cmd+l", "konfidenz": 0.9,
                                   "begruendung": "Adressleiste"}))
        r = cu.fuehre_ziel_aus("egal", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "fehler")

    def test_leeres_ziel(self):
        handle, _ = self._handle_ok()
        r = cu.fuehre_ziel_aus("  ", screenshot=_shot_ok(), entscheide=_decider(), handle=handle)
        self.assertEqual(r["status"], "fehler")

    def test_retry_prosa_dann_erfolg(self):
        # Modell liefert zweimal Prosa (kein JSON), beim 3. Versuch gueltiges JSON -> Loop macht weiter.
        handle, aufgerufen = self._handle_ok()
        dec = _decider("Ich schaue mal...", "Einen Moment...",
                       json.dumps({"aktion": "oeffne_app", "app": "Safari", "konfidenz": 0.9,
                                   "begruendung": "Safari"}),
                       json.dumps({"aktion": "fertig", "ergebnis": "offen", "konfidenz": 1}))
        r = cu.fuehre_ziel_aus("oeffne safari", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "fertig")
        self.assertEqual(aufgerufen, ["oeffne_app"])

    def test_retry_erschoepft_dann_fehler(self):
        handle, aufgerufen = self._handle_ok()
        dec = _decider("kein json", "immer noch nicht", "auch das nicht")   # 3x unbrauchbar
        r = cu.fuehre_ziel_aus("egal", screenshot=_shot_ok(), entscheide=dec, handle=handle)
        self.assertEqual(r["status"], "fehler")
        self.assertEqual(aufgerufen, [])


if __name__ == "__main__":
    unittest.main()
