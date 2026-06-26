"""Self-Checks Phase 14 -- freie Visualisierung (SVG, ohne externe Dienste)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import visualisierung as viz
from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


class TestVisualisierung(unittest.TestCase):
    def test_1_mindmap_svg(self):
        spec = viz.aus_text("mindmap", "Plan", "Technik: API, DB; Markt: Trend")
        self.assertEqual(spec["type"], "mindmap")
        self.assertEqual(len(spec["zweige"]), 2)
        svg = viz.to_svg(spec)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertIn("Technik", svg)
        self.assertIn("API", svg)

    def test_2_balken_svg(self):
        spec = viz.aus_text("balken", "Kosten", "Mac=10, NAS=4, Gemini=0")
        self.assertEqual([w[0] for w in spec["werte"]], ["Mac", "NAS", "Gemini"])
        self.assertEqual(spec["werte"][0][1], 10.0)
        svg = viz.to_svg(spec)
        self.assertIn("<rect", svg)
        self.assertIn("Mac", svg)

    def test_3_graph_svg(self):
        spec = viz.aus_text("graph", "Fluss", "a-b, b-c, c-a")
        self.assertEqual(set(spec["knoten"]), {"a", "b", "c"})
        self.assertEqual(len(spec["kanten"]), 3)
        self.assertIn("<line", viz.to_svg(spec))

    def test_4_organigramm_aus_verzeichnis(self):
        spec = viz.organigramm()
        self.assertEqual(spec["type"], "organigramm")
        self.assertTrue(len(spec["zweige"]) >= 10)            # 14 Abteilungen
        svg = viz.to_svg(spec)
        self.assertIn("CFO", svg)
        self.assertIn("Head of Agents", svg)

    def test_5_svg_escaping(self):
        spec = viz.mindmap("T", "Wurzel", [{"label": "A<b>&", "kinder": []}])
        svg = viz.to_svg(spec)
        self.assertNotIn("<b>", svg)                          # injiziertes Markup escaped
        self.assertIn("&lt;b&gt;", svg)

    def test_6_tool_registriert_und_dispatch(self):
        self.assertIn("visualisiere", {t["name"] for t in tool_specs()})
        visuals = []
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], visuals=visuals)
        r = run_tool("visualisiere", {"art": "organigramm", "titel": "Unsere Struktur"}, ctx)
        self.assertTrue(r["ok"])
        self.assertEqual(len(visuals), 1)
        self.assertTrue(visuals[0]["svg"].startswith("<svg"))
        self.assertTrue(visuals[0]["dateiname"].endswith(".svg"))

    def test_7_leck_schutz(self):
        secret = "sk-ant-GEHEIMXYZ12345"
        visuals = []
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT,
                          leak_secrets=[secret], visuals=visuals)
        run_tool("visualisiere", {"art": "mindmap", "titel": f"Key {secret}", "inhalt": "A: x"}, ctx)
        self.assertNotIn(secret, visuals[0]["svg"])


if __name__ == "__main__":
    unittest.main()
