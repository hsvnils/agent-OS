"""Self-Checks Phase 11 (Google Workspace) -- offline, ohne google-Libs/Netz/Credentials."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.google_workspace import (
    GoogleAuth,
    GoogleWorkspace,
    MockGoogleWorkspace,
)

ROOT = Path(__file__).resolve().parents[2]


def _ctx(google=None, secrets=None):
    core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate())
    return ToolContext(core=core, antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"),
                       engine=None, finance_dir=ROOT / "finance", repo_root=ROOT,
                       leak_secrets=secrets or [], google=google or MockGoogleWorkspace())


class TestGoogleWorkspace(unittest.TestCase):
    def test_1_ohne_credentials_fall_b(self):
        # Echte Integration ohne Credentials -> Fall-B-Hinweis, KEIN Absturz, KEIN Netz.
        gw = GoogleWorkspace(GoogleAuth.from_env({}))
        self.assertFalse(gw.verfuegbar())
        r = gw.mail_suchen("is:unread")
        self.assertFalse(r["ok"])
        self.assertTrue(r.get("fall_b"))
        self.assertIn("ANFRAGE an CEO", r["freigabe_anfrage"])

    def test_2_credentials_vollstaendig(self):
        gw = GoogleWorkspace(GoogleAuth.from_env({
            "GOOGLE_OAUTH_CLIENT_ID": "x", "GOOGLE_OAUTH_CLIENT_SECRET": "y",
            "GOOGLE_OAUTH_REFRESH_TOKEN": "z"}))
        self.assertTrue(gw.verfuegbar())

    def test_3_lesen_tools(self):
        ctx = _ctx()
        self.assertTrue(run_tool("mail_suchen", {"query": "is:unread"}, ctx)["ok"])
        self.assertTrue(run_tool("kalender_agenda", {}, ctx)["ok"])
        self.assertTrue(run_tool("drive_suchen", {"query": "vertrag"}, ctx)["ok"])
        self.assertTrue(run_tool("tabelle_lesen", {"spreadsheet_id": "s1"}, ctx)["ok"])

    def test_4_senden_ist_gated(self):
        ctx = _ctx()
        # Ohne bestaetigt -> nur Vorschau, NICHT gesendet.
        vor = run_tool("mail_senden", {"an": "x@test", "betreff": "Hi", "text": "Servus"}, ctx)
        self.assertFalse(vor["ok"])
        self.assertTrue(vor["bestaetigung_noetig"])
        self.assertEqual(ctx.google.gesendet, [])
        # Mit bestaetigt=true -> gesendet.
        ok = run_tool("mail_senden",
                      {"an": "x@test", "betreff": "Hi", "text": "Servus", "bestaetigt": True}, ctx)
        self.assertTrue(ok["ok"])
        self.assertEqual(len(ctx.google.gesendet), 1)

    def test_5_termin_und_tabelle_gated(self):
        ctx = _ctx()
        t = run_tool("termin_anlegen", {"titel": "Call", "start": "2026-06-26T10:00:00",
                                        "ende": "2026-06-26T11:00:00"}, ctx)
        self.assertTrue(t["bestaetigung_noetig"])
        self.assertEqual(ctx.google.termine, [])
        s = run_tool("tabelle_schreiben", {"spreadsheet_id": "s1", "bereich": "A1",
                                           "werte": [["x"]]}, ctx)
        self.assertTrue(s["bestaetigung_noetig"])

    def test_5b_standard_einladung(self):
        # Konfigurierte Standard-Einladung (z. B. private iCloud) ist in Vorschau UND Ergebnis.
        gw = MockGoogleWorkspace(standard_einladung="hsvnils@icloud.com")
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], google=gw)
        vor = run_tool("termin_anlegen", {"titel": "Call", "start": "2026-06-26T10:00:00",
                                          "ende": "2026-06-26T11:00:00"}, ctx)
        self.assertIn("hsvnils@icloud.com", vor["vorschau"]["einladung"])
        ok = run_tool("termin_anlegen", {"titel": "Call", "start": "2026-06-26T10:00:00",
                                         "ende": "2026-06-26T11:00:00", "bestaetigt": True}, ctx)
        self.assertEqual(ok["eingeladen"], ["hsvnils@icloud.com"])

    def test_6_entwurf_ist_sicher(self):
        # Entwurf ist ohne Bestaetigung erlaubt (sendet nicht).
        r = run_tool("mail_entwurf", {"an": "x@test", "betreff": "B", "text": "T"}, _ctx())
        self.assertTrue(r["ok"])
        self.assertIn("entwurf_id", r)

    def test_7_tool_specs_vorhanden(self):
        names = {t["name"] for t in tool_specs()}
        for n in ("mail_suchen", "mail_senden", "kalender_agenda", "termin_anlegen",
                  "drive_suchen", "drive_lesen", "tabelle_lesen", "tabelle_schreiben"):
            self.assertIn(n, names)

    def test_8_leck_schutz_im_ergebnis(self):
        secret = "ya29-GEHEIMESTOKEN"

        class _Leak(MockGoogleWorkspace):
            def mail_lesen(self, message_id):
                return {"ok": True, "mail": {"von": "a@test", "text": f"token {secret}"}}

        res = run_tool("mail_lesen", {"message_id": "m1"}, _ctx(google=_Leak(), secrets=[secret]))
        self.assertNotIn(secret, str(res))
        self.assertIn("[REDACTED]", str(res))


if __name__ == "__main__":
    unittest.main()
