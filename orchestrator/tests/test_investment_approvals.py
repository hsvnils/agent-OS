import tempfile
import unittest
from pathlib import Path

from orchestrator.investment.approvals import ApprovalStore


class TestApprovalStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.s = ApprovalStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_add_und_pending(self):
        aid = self.s.add("paper_order", {"symbol": "AAPL", "qty": 3, "side": "buy"}, frage="Kaufen?")
        pend = self.s.pending_unsent()
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]["id"], aid)
        self.assertEqual(pend[0]["payload"]["symbol"], "AAPL")

    def test_mark_sent_entfernt_aus_pending(self):
        aid = self.s.add("paper_order", {}, frage="?")
        self.s.mark_sent(aid)
        self.assertEqual(self.s.pending_unsent(), [])
        self.assertEqual(len(self.s.offen()), 1)   # weiterhin offen, nur gesendet

    def test_entscheiden_genehmigt(self):
        aid = self.s.add("paper_order", {"symbol": "AAPL"}, frage="?")
        a = self.s.entscheiden(aid, True, ergebnis="Order ausgefuehrt")
        self.assertEqual(a["status"], "genehmigt")
        self.assertEqual(a["ergebnis"], "Order ausgefuehrt")
        self.assertEqual(self.s.offen(), [])

    def test_entscheiden_idempotent(self):
        aid = self.s.add("paper_order", {}, frage="?")
        self.assertIsNotNone(self.s.entscheiden(aid, True))
        self.assertIsNone(self.s.entscheiden(aid, False))   # zweite Entscheidung prallt ab
        self.assertEqual(self.s.get(aid)["status"], "genehmigt")

    def test_entscheiden_unbekannt(self):
        self.assertIsNone(self.s.entscheiden("APV-nope", True))


class _FakeStore:
    def mode(self):
        return "paper"


class _FakeEngine:
    store = _FakeStore()

    def _aktueller_preis(self, symbol, asset):
        return 100.0

    def paper_konto(self):
        return {"ok": True, "konto": {"equity": 100000.0, "buying_power": 400000.0}}


class TestPaperOrderFreigabeTool(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.apv = ApprovalStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_tool_legt_freigabe_an(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=".", repo_root=".",
                          leak_secrets=[], investment=_FakeEngine(), approvals=self.apv)
        r = run_tool("paper_order_freigabe",
                     {"symbol": "AAPL", "qty": 3, "side": "buy", "konfidenz": 0.75, "signale": 2}, ctx)
        self.assertTrue(r["ok"])
        self.assertEqual(len(self.apv.pending_unsent()), 1)
        self.assertEqual(self.apv.get(r["freigabe_id"])["payload"]["symbol"], "AAPL")


if __name__ == "__main__":
    unittest.main()
