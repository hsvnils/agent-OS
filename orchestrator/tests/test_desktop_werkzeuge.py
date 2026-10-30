"""Paket D L2: LUNA-Desktop -- feste Werkzeugliste, Maschinenkonto nur /api/desktop, Fremdtext-Sperre je Zug."""
import json
import unittest
from unittest import mock

from orchestrator.core import desktop_werkzeuge as dw
from orchestrator.core.hoa_tools import ToolContext
from orchestrator.core.team_auth import hat_modul, maschine_darf, modul_fuer_pfad

MASCHINE = {"username": "maco470-desktop", "role": "maschine", "allowed_modules": ["desktop"]}


class TestListe(unittest.TestCase):
    def test_1_nichts_sendet_loescht_kostet(self):
        verboten = {"mail_senden", "termin_loeschen", "delegate", "antrag_freigeben", "paper_order", "recherche_beauftragen",
                    "rechner_aktion", "set_budget", "kundenordner_link"}
        self.assertFalse(verboten & set(dw.ERLAUBT))
        namen = {s["name"] for s in dw.specs()}
        self.assertEqual(namen, set(dw.ERLAUBT))                     # jedes erlaubte Werkzeug existiert wirklich

    def test_2_unbekanntes_werkzeug_abgelehnt(self):
        d = dw.DesktopWerkzeuge(lambda: self.fail("Kontext darf gar nicht geholt werden"))
        r = d.ausfuehren("mail_senden", {"an": "x@y.de"}, "z1")
        self.assertFalse(r["ok"])

    def test_3_kuerzen(self):
        self.assertTrue(dw.kuerzen({"t": "x" * 9000}).endswith("…(gekuerzt)"))
        self.assertEqual(json.loads(dw.kuerzen({"a": 1})), {"a": 1})


class TestKonto(unittest.TestCase):
    def test_1_maschine_nur_desktop(self):
        m = modul_fuer_pfad("POST", "/api/desktop/werkzeug")
        self.assertEqual(m, "desktop")
        self.assertTrue(hat_modul(MASCHINE, m) and maschine_darf(MASCHINE, m))
        for pfad in ("/api/state", "/api/brain", "/api/chat", "/api/crm", "/api/aufgaben"):
            mod = modul_fuer_pfad("GET", pfad)
            self.assertFalse(hat_modul(MASCHINE, mod) and maschine_darf(MASCHINE, mod) if mod else maschine_darf(MASCHINE, mod), pfad)

    def test_2_menschen_unveraendert(self):
        team = {"role": "team", "allowed_modules": ["crm"]}
        self.assertTrue(maschine_darf(team, None))                   # Kernendpunkte bleiben fuer Menschen offen
        self.assertFalse(hat_modul({"role": "admin", "allowed_modules": ["administration"]}, "desktop"))


class TestSperre(unittest.TestCase):
    def test_1_verdacht_sperrt_nur_im_selben_zug(self):
        ctx = ToolContext.__new__(ToolContext)
        ctx.fremd_verdacht, ctx.knoepfe = ["telegram"], ["knopf"]
        d = dw.DesktopWerkzeuge(lambda: ctx)
        gesehen = []

        def lauf(name, args, c):
            gesehen.append((name, list(c.fremd_verdacht)))
            if name == "mail_lesen":
                c.fremd_verdacht.append({"werkzeug": "mail_lesen", "muster": ["ignoriere"]})
            return {"ok": True}

        with mock.patch("orchestrator.core.hoa_tools.run_tool", side_effect=lauf):
            d.ausfuehren("mail_lesen", {"message_id": "1"}, "z1")
            d.ausfuehren("todo_anlegen", {"titel": "x"}, "z1")
            d.ausfuehren("todo_anlegen", {"titel": "y"}, "z2")
        self.assertEqual(gesehen[1][1], [{"werkzeug": "mail_lesen", "muster": ["ignoriere"]}])   # gleicher Zug: Verdacht da
        self.assertEqual(gesehen[2][1], [])                                                     # neuer Zug: frisch
        self.assertEqual((ctx.fremd_verdacht, ctx.knoepfe), (["telegram"], ["knopf"]))          # Telegram-Kontext unberuehrt


if __name__ == "__main__":
    unittest.main()
