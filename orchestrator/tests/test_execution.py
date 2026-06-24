"""Self-Checks fuer die Execution-Engine (Phase 7), offline mit gemockter Ausfuehrung (ohne Kosten)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.execution import ExecutionEngine


def _engine(antraege, *, tests_ok=True, agent=None, secrets=None, changelog=None):
    return ExecutionEngine(
        antraege,
        make_workspace=lambda aid: (f"/tmp/ws-{aid}", f"antrag/{aid}"),
        run_agent=agent or (lambda task, cwd: "Datei angelegt, Self-Checks ausgefuehrt."),
        run_tests=lambda cwd: (tests_ok, "30/30 OK" if tests_ok else "1 failed"),
        diff=lambda cwd: "+ neue Datei docs/x.md",
        secrets=secrets, changelog=changelog,
    )


class TestExecution(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.antraege = Antraege(self.tmp / "log.jsonl")

    def _freigegeben(self, **kw):
        aid = self.antraege.stellen(kw.get("titel", "T"), kw.get("beschreibung", "B"),
                                    kategorie=kw.get("kategorie", ""), betroffen=kw.get("betroffen", ""))
        self.antraege.freigeben(aid)
        return aid

    def test_1_guard_nur_freigegebene(self):
        aid = self.antraege.stellen("offen", "...")  # bleibt 'eingereicht'
        res = _engine(self.antraege).umsetzen(aid)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "abgelehnt")
        self.assertEqual(self.antraege.get(aid)["status"], "eingereicht")  # unveraendert

    def test_2_workspace_branch(self):
        aid = self._freigegeben()
        res = _engine(self.antraege).umsetzen(aid)
        self.assertEqual(res.branch, f"antrag/{aid}")

    def test_3_status_erfolgreich(self):
        aid = self._freigegeben()
        res = _engine(self.antraege, tests_ok=True).umsetzen(aid)
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "erledigt")
        verlauf = [s["event"] for s in self.antraege.get(aid)["verlauf"]]
        self.assertEqual(verlauf, ["eingereicht", "freigegeben", "in_umsetzung", "erledigt"])

    def test_4_tests_rot_fehlgeschlagen(self):
        aid = self._freigegeben()
        res = _engine(self.antraege, tests_ok=False).umsetzen(aid)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "fehlgeschlagen")
        self.assertEqual(self.antraege.get(aid)["status"], "fehlgeschlagen")

    def test_5_charta_schutz(self):
        aid = self._freigegeben(titel="Charta aendern", betroffen="agents/03_cfo.md")
        res = _engine(self.antraege).umsetzen(aid)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "abgelehnt")
        self.assertIn("geschuetzte", res.bericht.lower())
        # Mit Mandats-Freigabe waere es erlaubt:
        aid2 = self._freigegeben(titel="Charta aendern", betroffen="agents/03_cfo.md", kategorie="mandat")
        self.assertTrue(_engine(self.antraege).umsetzen(aid2).ok)

    def test_6_leck_schutz_im_bericht(self):
        secret = "sk-ant-EXECSECRET-7"
        aid = self._freigegeben()
        res = _engine(self.antraege, agent=lambda t, c: f"Key {secret} benutzt", secrets=[secret]).umsetzen(aid)
        self.assertNotIn(secret, res.bericht)
        self.assertIn("[REDACTED]", res.bericht)


if __name__ == "__main__":
    unittest.main()
