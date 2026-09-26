"""Self-Checks Werkzeugauswahl im Chat (WERKZEUGAUSWAHL_ROADMAP.md, Etappe 2) -- offline, Fake-Modell."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import werkzeugauswahl as w
from orchestrator.core.aktivitaet import Aktivitaet
from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_conversation import HoaConversation
from orchestrator.core.hoa_tools import ToolContext, tool_specs
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


def _text(t):
    return type("R", (), {"content": [{"type": "text", "text": t}], "usage": None})()


def _tool(name, eingabe=None, tid="t1"):
    return type("R", (), {"content": [{"type": "tool_use", "id": tid, "name": name, "input": eingabe or {}}],
                          "usage": None})()


class _Client:
    """Spielt vorgegebene Antworten ab und merkt sich, welche Werkzeuge das Modell je Aufruf gesehen hat."""
    def __init__(self, antworten):
        self.antworten, self.gesehen, self.messages = list(antworten), [], self

    def create(self, **kw):
        self.gesehen.append({t["name"] for t in kw["tools"]})
        return self.antworten.pop(0)


def _conv(antworten, schalter="an"):
    akt = Aktivitaet(Path(tempfile.mkdtemp()) / "akt.jsonl")
    ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                      antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                      finance_dir=ROOT / "finance", repo_root=Path(tempfile.mkdtemp()), leak_secrets=[],
                      aktivitaet=akt, secret_dict={"WERKZEUGAUSWAHL": schalter})
    client = _Client(antworten)
    return HoaConversation(ctx, client=client), client, akt


class TestWerkzeugauswahlChat(unittest.TestCase):
    def test_1_schalter_aus_alle_werkzeuge(self):
        conv, client, _ = _conv([_text("ok")], schalter="")
        conv.respond("Hallo")
        self.assertEqual(client.gesehen[0], {t["name"] for t in tool_specs()})

    def test_2_hallo_nur_kern_kalender_mit_gruppe(self):
        conv, client, _ = _conv([_text("Hallo!"), _text("Termine ...")])
        conv.respond("Hallo LUNA")
        self.assertEqual(client.gesehen[0], set(w.KERN))
        conv.respond("Was steht diese Woche im Kalender?")
        self.assertIn("kalender_agenda", client.gesehen[1])
        self.assertNotIn("paper_order", client.gesehen[1])

    def test_3_nachladen_per_werkzeug(self):
        conv, client, akt = _conv([_tool("werkzeuge_laden", {"gruppe": "mail"}), _text("Hier deine Mails")])
        conv.respond("Hallo, kannst du was für mich nachsehen?")
        self.assertNotIn("posteingang", client.gesehen[0])
        self.assertIn("posteingang", client.gesehen[1])                        # direkt im naechsten Aufruf da
        self.assertIn("mail", conv.gruppen)

    def test_4_nicht_gezeigtes_werkzeug_wird_ausgefuehrt_und_nachgeladen(self):
        conv, client, akt = _conv([_tool("autonomie_status"), _text("Alles laeuft.")])
        conv.respond("Hallo")
        self.assertNotIn("autonomie_status", client.gesehen[0])
        self.assertIn("autonomie_status", client.gesehen[1])
        e = akt.letzte(5, kategorie="werkzeug")[0]
        self.assertEqual((e["aktion"], e["detail"]), ("Werkzeug autonomie_status", "nachgeladen"))

    def test_5_protokoll_vorausgewaehlt(self):
        conv, client, akt = _conv([_tool("antraege_zeigen"), _text("3 offen")])
        conv.respond("Welche Anträge sind offen?")
        self.assertEqual(akt.letzte(1, kategorie="werkzeug")[0]["detail"], "vorausgewaehlt")

    def test_6_gruppen_bleiben_und_verfallen_nach_pause(self):
        conv, client, _ = _conv([_text("a"), _text("b"), _text("c")])
        conv.respond("Was steht im Kalender?")
        conv.respond("Und danach?")
        self.assertIn("kalender_agenda", client.gesehen[1])                    # Gruppe bleibt im Gespraech
        conv.letzte_nachricht -= 3 * 3600
        conv.respond("Hallo")
        self.assertEqual(client.gesehen[2], set(w.KERN))                       # nach Pause frisch

    def test_7_unbekannte_gruppe(self):
        conv, client, _ = _conv([_tool("werkzeuge_laden", {"gruppe": "quatsch"}), _text("ok")])
        conv.respond("Hallo")
        self.assertEqual(conv.gruppen, set())


if __name__ == "__main__":
    unittest.main()
