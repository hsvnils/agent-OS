"""Self-Checks Frontdesk (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 3): Auftraege erteilen + Ehrlichkeitsregel (BF-25)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.aktivitaet import Aktivitaet
from orchestrator.core.antraege import Antraege
from orchestrator.core.auftraege import AuftragStore
from orchestrator.core.backends import MockBackend
from orchestrator.core.briefing import Agenda
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_conversation import (NACHFASSEN, NACHFASSEN_AUFTRAG, HoaConversation,
                                                behauptet_erledigung, kuendigt_an, wunsch_hintergrund)
from orchestrator.core.hoa_tools import ToolContext, run_tool
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


def _ctx():
    d = Path(tempfile.mkdtemp())
    return ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                       antraege=Antraege(d / "a.jsonl"), engine=None, finance_dir=ROOT / "finance", repo_root=d,
                       leak_secrets=[], aktivitaet=Aktivitaet(d / "akt.jsonl"), agenda=Agenda(d / "ag.jsonl"),
                       backoffice=AuftragStore(d / "b.jsonl"))


def _text(t):
    return type("R", (), {"content": [{"type": "text", "text": t}], "usage": None})()


def _tool(name, eingabe, tid="t1"):
    return type("R", (), {"content": [{"type": "tool_use", "id": tid, "name": name, "input": eingabe}], "usage": None})()


class _Client:
    def __init__(self, antworten):
        self.antworten, self.aufrufe, self.messages = list(antworten), [], self

    def create(self, **kw):
        self.aufrufe.append([dict(m) for m in kw["messages"]])
        return self.antworten.pop(0)


class TestFrontdesk(unittest.TestCase):
    def test_1_auftrag_erteilen_und_zeigen(self):
        ctx = _ctx()
        r = run_tool("auftrag_erteilen", {"aufgabe": "Fasse den Artikel zusammen: ...", "art": "zusammenfassung"}, ctx)
        self.assertTrue(r["ok"])
        self.assertTrue(r["id"].startswith("B-"))                          # nicht mit Antraegen (A-...) verwechselbar
        self.assertIn(f"#{r['kurz']}", r["hinweis"])
        liste = run_tool("auftraege_zeigen", {}, ctx)["auftraege"]
        self.assertEqual((liste[0]["kurz"], liste[0]["status"]), (r["kurz"], "neu"))
        self.assertFalse(run_tool("auftrag_erteilen", {"aufgabe": " ", "art": "entwurf"}, ctx)["ok"])

    def test_2_erkennung_von_behauptungen(self):
        self.assertTrue(behauptet_erledigung('Alles klar, ich habe "Reifen wechseln" in deine Agenda eingetragen.'))
        self.assertTrue(behauptet_erledigung("Die Mail wurde gesendet."))
        self.assertFalse(behauptet_erledigung("Soll ich das eintragen?"))
        self.assertFalse(behauptet_erledigung("Ich kann das gerne notieren."))
        self.assertFalse(behauptet_erledigung("Hallo Nils, wie kann ich helfen?"))
        # Faelle aus dem Gemini-Probelauf 2026-09-27: Behauptung ohne Hilfsverb + erfundene ID
        self.assertTrue(behauptet_erledigung("Auftrag B-3f2a angelegt: Analyse der Kosten. Ich melde mich."))
        self.assertTrue(behauptet_erledigung("Auftrag #B-42fb angelegt, ich melde mich."))
        self.assertFalse(behauptet_erledigung("Wenn es erledigt ist, melde ich mich."))

    def test_3_behauptung_ohne_werkzeug_wird_nachgefasst(self):
        ctx = _ctx()
        client = _Client([_text("Alles klar, ich habe es in deine Agenda eingetragen."),
                          _tool("notiz_hinzufuegen", {"text": "Reifen wechseln"}),
                          _text("Erledigt: 'Reifen wechseln' steht in deiner Agenda.")])
        antwort = HoaConversation(ctx, client=client).respond("Notier dir: Reifen wechseln")
        self.assertEqual(len(client.aufrufe), 3)
        self.assertEqual(client.aufrufe[1][-1]["content"], NACHFASSEN)       # Hinweis an das Modell
        self.assertIn("Agenda", antwort)
        self.assertTrue(any("Reifen" in str(p) for p in ctx.agenda.offene()))  # wirklich eingetragen
        self.assertEqual(len(ctx.aktivitaet.letzte(5, kategorie="ehrlichkeit")), 1)

    def test_4_nur_einmal_nachfassen(self):
        client = _Client([_text("Ich habe es eingetragen."), _text("Doch, ist eingetragen.")])
        antwort = HoaConversation(_ctx(), client=client).respond("Notier dir X")
        self.assertEqual((len(client.aufrufe), antwort), (2, "Doch, ist eingetragen."))

    def test_5_nach_echtem_werkzeug_kein_nachfassen(self):
        client = _Client([_tool("notiz_hinzufuegen", {"text": "X"}), _text("Ist eingetragen.")])
        HoaConversation(_ctx(), client=client).respond("Notier dir X")
        self.assertEqual(len(client.aufrufe), 2)

    def test_6_erfundene_auftrags_id_trotz_werkzeug_wird_nachgefasst(self):
        from orchestrator.core.hoa_conversation import unbekannte_auftrags_ids
        ctx = _ctx()
        echt = run_tool("auftrag_erteilen", {"aufgabe": "x", "art": "entwurf"}, ctx)["kurz"]
        self.assertEqual(unbekannte_auftrags_ids(f"Auftrag #{echt} angelegt.", ctx.backoffice), [])
        self.assertEqual(unbekannte_auftrags_ids("Auftrag B-3f2a angelegt.", ctx.backoffice), ["3f2a"])
        client = _Client([_tool("auftraege_zeigen", {}), _text("Auftrag #beef angelegt, ich melde mich."),
                          _text("Korrektur: Ich habe noch keinen neuen Auftrag angelegt.")])
        HoaConversation(ctx, client=client).respond("Was laeuft im Backoffice?")
        self.assertEqual(len(client.aufrufe), 3)

    def test_7_live_fall_ankuendigung_bei_hintergrund_wunsch(self):
        # Live-Test 2026-09-27 13:50: Gemini kuendigte an und rief kein Werkzeug auf.
        ctx = _ctx()
        client = _Client([_text("Absolut, mache ich. Hier ist die Auftrags-ID für den Entwurf:"),
                          _tool("auftrag_erteilen", {"aufgabe": "Mail an Thomas Berger ...", "art": "entwurf"}),
                          _text("Auftrag ist angelegt, ich melde mich.")])
        HoaConversation(ctx, client=client).respond(
            "Mach mir im Hintergrund einen Entwurf für eine kurze Mail an Thomas Berger, dass ich die Q3-Belege "
            "bis Freitag hochlade.")
        self.assertEqual(client.aufrufe[1][-1]["content"], NACHFASSEN_AUFTRAG)
        self.assertEqual(len(ctx.backoffice.list("neu")), 1)                 # Auftrag wirklich angelegt

    def test_8_wunsch_erfuellt_kein_nachfassen(self):
        client = _Client([_tool("auftrag_erteilen", {"aufgabe": "x", "art": "entwurf"}), _text("Angelegt, ich melde mich.")])
        HoaConversation(_ctx(), client=client).respond("Mach das bis morgen")
        self.assertEqual(len(client.aufrufe), 2)

    def test_9_erkennung_wunsch_und_ankuendigung(self):
        self.assertTrue(wunsch_hintergrund("Mach mir im Hintergrund einen Entwurf"))
        self.assertTrue(wunsch_hintergrund("Analysier das ausführlich"))
        self.assertFalse(wunsch_hintergrund("Was steht heute an?"))
        self.assertTrue(kuendigt_an("Absolut, mache ich. Hier ist die Auftrags-ID für den Entwurf:"))
        self.assertTrue(kuendigt_an("Klar, lege ich an."))
        self.assertFalse(kuendigt_an("Soll ich das so anlegen?"))
        self.assertFalse(kuendigt_an("Hallo Nils, wie kann ich helfen?"))


if __name__ == "__main__":
    unittest.main()
