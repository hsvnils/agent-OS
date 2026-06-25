"""Self-Checks IT-Selbstheilung -- offline. Harte Grenze: nur technisch+kostenfrei."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.antraege import Antraege
from orchestrator.core.notifications import Notifications
from orchestrator.core.self_healing import SelfHealing, ist_technisch_kostenfrei

ROOT = Path(__file__).resolve().parents[2]


class _FakeRes:
    def __init__(self, ok, status, bericht="ok"):
        self.ok = ok
        self.status = status
        self.branch = "antrag/x"
        self.bericht = bericht


class _FakeEngine:
    def __init__(self, ok=True, status="erledigt"):
        self._ok, self._status = ok, status
        self.umgesetzt = []

    def umsetzen(self, aid):
        self.umgesetzt.append(aid)
        return _FakeRes(self._ok, self._status)


class TestSelfHealing(unittest.TestCase):
    def test_1_klassifikator(self):
        self.assertTrue(ist_technisch_kostenfrei(
            {"kategorie": "technisch-kostenfrei", "titel": "Log-Format fixen", "beschreibung": "Bugfix"})[0])
        # nicht markiert -> nein
        self.assertFalse(ist_technisch_kostenfrei({"kategorie": "Innovation", "titel": "x"})[0])
        # markiert, aber Kosten-Stichwort -> nein
        self.assertFalse(ist_technisch_kostenfrei(
            {"kategorie": "technisch-kostenfrei", "titel": "Neues Abo kaufen", "beschreibung": ""})[0])

    def test_2_heilen_technisch_kostenfrei_merged(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        aid = antraege.stellen("Log-Format korrigieren", "Reiner Bugfix", von="cto",
                               kategorie="technisch-kostenfrei")
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        # merge_branch/commit_branch sind git-Operationen -> hier mocken wir sie weg.
        import orchestrator.core.self_healing as sh_mod
        import orchestrator.core.execution_live as live
        live_commit, live_merge = live.commit_branch, live.merge_branch
        live.commit_branch = lambda *a, **k: True
        live.merge_branch = lambda *a, **k: (True, "merged")
        try:
            sh = SelfHealing(antraege, _FakeEngine(ok=True, status="erledigt"),
                             repo_root=ROOT, notify=nb.enqueue)
            res = sh.heilen(aid)
        finally:
            live.commit_branch, live.merge_branch = live_commit, live_merge
        self.assertTrue(res["ok"])
        self.assertTrue(res["gemergt"])
        self.assertEqual(antraege.get(aid)["status"], "freigegeben")  # selbst freigegeben
        self.assertTrue(any(n["abteilung"] == "IT/Self-Healing" for n in nb.pending()))

    def test_3_heilen_lehnt_kostenpflichtiges_ab(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        aid = antraege.stellen("Neues kostenpflichtiges Tool", "kostet Geld", von="cto",
                               kategorie="technisch-kostenfrei")  # Stichwort 'kosten' -> blockiert
        sh = SelfHealing(antraege, _FakeEngine(), repo_root=ROOT)
        res = sh.heilen(aid)
        self.assertFalse(res["ok"])
        self.assertTrue(res["abgelehnt"])
        # NICHT umgesetzt
        self.assertEqual(antraege.get(aid)["status"], "eingereicht")

    def test_4_tests_rot_kein_merge(self):
        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        aid = antraege.stellen("Bugfix", "technisch", von="cto", kategorie="technisch-kostenfrei")
        nb = Notifications(Path(tempfile.mkdtemp()) / "n.jsonl")
        sh = SelfHealing(antraege, _FakeEngine(ok=False, status="fehlgeschlagen"),
                         repo_root=ROOT, notify=nb.enqueue)
        res = sh.heilen(aid)
        self.assertFalse(res["ok"])           # kein Merge bei roten Tests
        self.assertIn("fehlgeschlagen", " ".join(n["text"] for n in nb.pending()).lower())


if __name__ == "__main__":
    unittest.main()
