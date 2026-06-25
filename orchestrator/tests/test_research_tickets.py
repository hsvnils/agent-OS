"""Self-Checks Phase 8.5 (Research-Tickets) -- offline, ohne Netz/Keys."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.research_tickets import ResearchTickets
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.web_research import MockProvider, Treffer, WebResearch

ROOT = Path(__file__).resolve().parents[2]


def _store():
    return ResearchTickets(Path(tempfile.mkdtemp()) / "research.jsonl")


def _ctx(web=None, research=None, secrets=None):
    core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())
    return ToolContext(core=core, antraege=Antraege(Path(tempfile.mkdtemp()) / "log.jsonl"),
                       engine=None, finance_dir=ROOT / "finance", repo_root=ROOT,
                       leak_secrets=secrets or [], web=web, research=research or _store())


class TestResearchTickets(unittest.TestCase):
    def test_1_lebenszyklus(self):
        s = _store()
        tid = s.erstellen("was ist neu bei agenten?", abteilung="cpo")
        self.assertEqual(s.get(tid)["status"], "offen")
        self.assertTrue(s.in_arbeit(tid))
        self.assertTrue(s.erledigen(tid, provider="brave", befund="Befund X",
                                    quellen=["https://a.test"], stufe="einfach"))
        t = s.get(tid)
        self.assertEqual(t["status"], "erledigt")
        self.assertEqual(t["abteilung"], "cpo")
        self.assertEqual(t["quellen"], ["https://a.test"])
        self.assertEqual(len(t["verlauf"]), 3)

    def test_2_unbekanntes_ticket(self):
        self.assertFalse(_store().in_arbeit("R-gibtsnicht"))

    def test_3_filter_und_get(self):
        s = _store()
        a = s.erstellen("a"); s.in_arbeit(a); s.erledigen(a, provider="brave", befund="x", quellen=[])
        s.erstellen("b")  # bleibt offen
        self.assertEqual(len(s.list()), 2)
        self.assertEqual(len(s.list("offen")), 1)
        self.assertEqual(len(s.list("erledigt")), 1)

    def test_4_leck_schutz_im_ticket(self):
        secret = "sk-ant-TICKETSECRET-7"
        s = ResearchTickets(Path(tempfile.mkdtemp()) / "r.jsonl", secrets=[secret])
        tid = s.erstellen("frage")
        s.in_arbeit(tid)
        s.erledigen(tid, provider="brave", befund=f"geheim {secret}", quellen=[])
        self.assertNotIn(secret, s.get(tid)["befund"])

    def test_5_tools_beauftragen_zeigen_ticket(self):
        web = WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic"))
        ctx = _ctx(web=web)
        beauftragt = run_tool("recherche_beauftragen",
                              {"frage": "neueste frameworks", "abteilung": "berater"}, ctx)
        self.assertTrue(beauftragt["ok"])
        tid = beauftragt["ticket_id"]
        # zeigen
        liste = run_tool("recherche_tickets_zeigen", {}, ctx)
        self.assertEqual(liste["anzahl"], 1)
        self.assertEqual(liste["tickets"][0]["abteilung"], "berater")
        # einzelnes Ticket
        einzel = run_tool("recherche_ticket", {"ticket_id": tid}, ctx)
        self.assertEqual(einzel["ticket"]["status"], "erledigt")
        self.assertEqual(einzel["ticket"]["frage"], "neueste frameworks")

    def test_6_ticket_nicht_gefunden(self):
        res = run_tool("recherche_ticket", {"ticket_id": "R-x"}, _ctx())
        self.assertIn("fehler", res)

    def test_7_researcher_ist_konsultierbar(self):
        # res (Agent 15) ist als Spezialist verdrahtet + in der delegate-Liste.
        self.assertIn("res", load_all_subagents())
        delegate = next(t for t in tool_specs() if t["name"] == "delegate")
        self.assertIn("res", delegate["description"])

    def test_8_befund_aus_treffern_wenn_keine_synthese(self):
        from orchestrator.governance.web_research import RechercheErgebnis

        class _BraveLike:
            name = "brave"

            def verfuegbar(self):
                return True

            def suche(self, query, *, max_results=5):
                # Wie Brave: nur Treffer, KEINE Synthese.
                return RechercheErgebnis(ok=True, provider="brave",
                                         treffer=[Treffer(titel="T1", url="https://x.test", auszug="A")])

        web = WebResearch(einfach=_BraveLike(), komplex=MockProvider("anthropic"))
        res = run_tool("recherche_beauftragen", {"frage": "frage"}, _ctx(web=web))
        self.assertTrue(res["ok"])
        self.assertIn("T1", res["befund"])  # Befund aus Treffern gebaut
        self.assertEqual(res["quellen"], ["https://x.test"])


if __name__ == "__main__":
    unittest.main()
