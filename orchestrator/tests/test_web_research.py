"""Self-Checks Phase 8 (Web-Research) -- offline, ohne Netz/Keys, mit MockProvider."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.web_research import (
    AnthropicProvider,
    BraveProvider,
    MockProvider,
    Treffer,
    WebResearch,
    route_komplexitaet,
)

ROOT = Path(__file__).resolve().parents[2]


def _ctx(web=None, secrets=None):
    core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())
    return ToolContext(core=core, antraege=Antraege(Path(tempfile.mkdtemp()) / "log.jsonl"),
                       engine=None, finance_dir=ROOT / "finance", repo_root=ROOT,
                       leak_secrets=secrets or [], web=web)


def _mock_web(secrets=None):
    return WebResearch(einfach=MockProvider("brave"), komplex=MockProvider("anthropic"),
                       secrets=secrets or [])


class TestWebResearch(unittest.TestCase):
    def test_1_router_einfach_vs_komplex(self):
        self.assertEqual(route_komplexitaet("wetter berlin heute"), "einfach")
        self.assertEqual(route_komplexitaet("vergleiche die fuehrenden KI-Agenten-Frameworks"), "komplex")
        # Explizite Tiefe schlaegt die Heuristik.
        self.assertEqual(route_komplexitaet("wetter berlin", tiefe="komplex"), "komplex")
        self.assertEqual(route_komplexitaet("vergleiche A und B", tiefe="einfach"), "einfach")

    def test_2_router_waehlt_provider(self):
        web = _mock_web()
        self.assertEqual(web.recherchiere("wetter berlin").provider, "brave")
        self.assertEqual(web.recherchiere("analysiere markttrends bei agenten").provider, "anthropic")

    def test_3_kein_provider_aktiv_ist_ceo_tor(self):
        # Echte Provider ohne Keys (leere env) -> kein Absturz, sondern Fall-B-Hinweis.
        web = WebResearch(einfach=BraveProvider({}), komplex=AnthropicProvider({}))
        erg = web.recherchiere("irgendwas")
        self.assertFalse(erg.ok)
        self.assertIn("CEO-Tor", erg.hinweis)
        self.assertIn("ANFRAGE an CEO", erg.freigabe_anfrage)

    def test_4_verfuegbarkeits_fallback(self):
        # Komplexe Anfrage, aber nur 'einfach' verfuegbar -> faellt auf 'einfach' zurueck.
        class _Aus(MockProvider):
            def verfuegbar(self):
                return False
        web = WebResearch(einfach=MockProvider("brave"), komplex=_Aus("anthropic"))
        erg = web.recherchiere("analysiere und vergleiche viele optionen ausfuehrlich")
        self.assertTrue(erg.ok)
        self.assertEqual(erg.provider, "brave")
        self.assertEqual(erg.stufe, "komplex")

    def test_5_leck_schutz(self):
        secret = "sk-ant-WEBSECRET-9"
        seed = {"frage": [Treffer(titel="ok", url="https://x.test", auszug=f"enthaelt {secret}")]}
        web = WebResearch(einfach=MockProvider("brave", seed=seed), komplex=MockProvider("anthropic"),
                          secrets=[secret])
        erg = web.recherchiere("frage")
        self.assertNotIn(secret, erg.treffer[0].auszug)
        self.assertIn("[REDACTED]", erg.treffer[0].auszug)

    def test_6_tool_spec_und_handler(self):
        self.assertIn("web_recherche", {t["name"] for t in tool_specs()})
        res = run_tool("web_recherche", {"query": "wetter berlin"}, _ctx(web=_mock_web()))
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "brave")
        self.assertTrue(res["treffer"])

    def test_7_handler_ohne_keys_meldet_ceo_tor(self):
        # ctx.web=None -> aus leerer Sicht: ohne Keys kommt der CEO-Tor-Hinweis (kein Absturz).
        res = run_tool("web_recherche", {"query": "wetter berlin"},
                       _ctx(web=WebResearch(einfach=BraveProvider({}), komplex=AnthropicProvider({}))))
        self.assertFalse(res["ok"])
        self.assertIn("CEO-Tor", res["hinweis"])

    def test_8_handler_ceo_tor_query(self):
        res = run_tool("web_recherche", {"query": "ein neues kostenpflichtiges Tool kaufen"},
                       _ctx(web=_mock_web()))
        self.assertTrue(res.get("blockiert"))


if __name__ == "__main__":
    unittest.main()
