"""BF-35: Der Chat kannte das heutige Datum nicht und trug „morgen 10 Uhr“ am 16.05.2024 ein (2026-09-28)."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from orchestrator.core.hoa_conversation import HoaConversation, system_prompt
from orchestrator.core.hoa_tools import run_tool
from orchestrator.governance.google_workspace import MockGoogleWorkspace
from orchestrator.tests.test_frontdesk import _ctx, _text, _tool


class _Client:
    def __init__(self, antworten):
        self.antworten, self.systeme, self.messages = list(antworten), [], self

    def create(self, **kw):
        self.systeme.append(kw["system"])
        return self.antworten.pop(0)


class TestChatDatum(unittest.TestCase):
    def test_1_prompt_enthaelt_heutiges_datum(self):
        p = system_prompt(datetime(2026, 9, 28, 11, 1, tzinfo=ZoneInfo("Europe/Berlin")))
        self.assertIn("Heute ist Montag, der 28.09.2026, 11:01 Uhr", p)
        self.assertIn("2026-MM-TT", p)

    def test_2_chat_schickt_das_datum_mit(self):
        client = _Client([_text("Hallo Nils")])
        HoaConversation(_ctx(), client=client).respond("Moin")
        heute = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y")
        self.assertIn(f"der {heute}", client.systeme[0])

    def test_3_termin_in_vergangenheit_wird_abgewiesen(self):
        ctx = _ctx()
        g = ctx.google = MockGoogleWorkspace()
        r = run_tool("termin_anlegen", {"titel": "LUNA-Konto-Test", "start": "2024-05-16T10:00:00",
                                        "ende": "2024-05-16T11:00:00", "bestaetigt": True}, ctx)
        self.assertFalse(r["ok"])
        self.assertIn("Vergangenheit", r["hinweis"])
        self.assertIn(datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d"), r["hinweis"])
        self.assertEqual(g.termine, [])                                                 # nichts eingetragen
        morgen = (datetime.now(ZoneInfo("Europe/Berlin")) + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
        r = run_tool("termin_anlegen", {"titel": "Test", "start": morgen, "ende": morgen, "bestaetigt": True}, ctx)
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(g.termine), 1)
        self.assertFalse(run_tool("termin_aendern", {"event_id": "e1", "start": "2024-05-16T10:00:00",
                                                     "bestaetigt": True}, ctx)["ok"])
        self.assertTrue(run_tool("termin_aendern", {"event_id": "e1", "titel": "nur Titel", "bestaetigt": True}, ctx)["ok"])

    def test_4_modell_korrigiert_nach_hinweis(self):
        ctx = _ctx()
        g = ctx.google = MockGoogleWorkspace()
        morgen = (datetime.now(ZoneInfo("Europe/Berlin")) + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
        client = _Client([_tool("termin_anlegen", {"titel": "T", "start": "2024-05-16T10:00:00", "ende": "2024-05-16T11:00:00",
                                                   "bestaetigt": True}, "t1"),
                          _tool("termin_anlegen", {"titel": "T", "start": morgen, "ende": morgen, "bestaetigt": True}, "t2"),
                          _text("Eingetragen.")])
        HoaConversation(ctx, client=client).respond("Trag mir morgen 10 Uhr T ein, ja passt")
        self.assertEqual([t["start"] for t in g.termine], [morgen])


if __name__ == "__main__":
    unittest.main()
