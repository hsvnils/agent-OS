import tempfile
import unittest
from pathlib import Path

from orchestrator.core.security_agent import SecurityAgent


class TestSecurityAgent(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / ".gitignore").write_text(".env\nclient_secret*.json\n*token*.json\n", encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def _agent(self, *, run=None, env=None, **kw):
        return SecurityAgent(repo_root=self.root, env=env or {"LUNA_OS_PASSWORD": "geheim"}, run=run, **kw)

    def _schweren(self, findings):
        return {f.titel: f.schwere for f in findings}

    def test_gitignore_ok(self):
        f = self._agent()._check_secret_hygiene()
        self.assertIn("ok", [x.schwere for x in f if "gitignore" in x.titel.lower() or "deckt" in x.titel])

    def test_gitignore_fehlt_muster(self):
        (self.root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")  # keine Secret-Muster
        f = self._agent()._check_secret_hygiene()
        self.assertTrue(any(x.schwere == "hoch" and "gitignore" in x.titel.lower() for x in f))

    def test_secret_leak_getrackt(self):
        run = lambda cmd: "orchestrator/app.py\norchestrator/.env\nclient_secret_123.json\n"
        f = self._agent(run=run)._check_secret_hygiene()
        leak = [x for x in f if x.kategorie == "secret-leak"][0]
        self.assertEqual(leak.schwere, "hoch")
        self.assertIn(".env", leak.detail)

    def test_secret_leak_sauber(self):
        run = lambda cmd: "orchestrator/app.py\n.env.example\nREADME.md\n"   # .example ist ok
        f = self._agent(run=run)._check_secret_hygiene()
        leak = [x for x in f if x.kategorie == "secret-leak"][0]
        self.assertEqual(leak.schwere, "ok")

    def test_hardening_login_offen(self):
        f = self._agent(env={"LUNA_OS_PASSWORD": ""})._check_hardening()
        self.assertTrue(any(x.schwere == "mittel" and "Login" in x.titel for x in f))

    def test_hardening_login_aktiv(self):
        f = self._agent(env={"LUNA_OS_PASSWORD": "stark"})._check_hardening()
        self.assertTrue(any(x.schwere == "ok" and "Login" in x.titel for x in f))

    def test_dependencies_verwundbar(self):
        run = lambda cmd: '{"dependencies":[{"name":"requests","version":"2.0","vulns":[{"id":"CVE-x"}]},{"name":"safe","version":"1.0","vulns":[]}]}'
        f = self._agent(run=run)._check_dependencies()
        self.assertEqual(f[0].schwere, "hoch")
        self.assertIn("requests", f[0].detail)

    def test_dependencies_cve_und_fix_im_detail(self):
        run = lambda cmd: '{"dependencies":[{"name":"requests","version":"2.0","vulns":[{"id":"CVE-x","fix_versions":["2.3.1"]}]}]}'
        f = self._agent(run=run)._check_dependencies()
        self.assertEqual(f[0].schwere, "hoch")
        self.assertIn("requests 2.0", f[0].detail)
        self.assertIn("CVE-x", f[0].detail)
        self.assertIn("2.3.1", f[0].detail)

    def test_dependencies_sauber(self):
        run = lambda cmd: '{"dependencies":[{"name":"safe","version":"1.0","vulns":[]}]}'
        f = self._agent(run=run)._check_dependencies()
        self.assertEqual(f[0].schwere, "ok")

    def test_dependencies_kein_runner(self):
        f = self._agent(run=None)._check_dependencies()
        self.assertEqual(f[0].schwere, "niedrig")

    def test_code_security_findet_gefaehrliche_aufrufe(self):
        (self.root / "orchestrator").mkdir()
        (self.root / "orchestrator" / "mod.py").write_text(
            "import os, subprocess\n"
            "def f(x):\n"
            "    os.system(x)\n"
            "    subprocess.run(x, shell=True)\n"
            "    eval(x)\n"
            "    subprocess.run(['ls', '-la'])\n",   # sicher -> darf NICHT flaggen
            encoding="utf-8")
        f = self._agent()._check_code_security()
        hoch = [x for x in f if x.schwere == "hoch"]
        self.assertTrue(hoch)
        self.assertIn("os.system", hoch[0].detail)
        self.assertIn("shell=True", hoch[0].detail)
        self.assertIn("eval()", hoch[0].detail)

    def test_code_security_sauberes_subprocess_ok(self):
        (self.root / "orchestrator").mkdir()
        (self.root / "orchestrator" / "mod.py").write_text(
            "import subprocess\n"
            "def f():\n"
            "    return subprocess.run(['ls'], capture_output=True, text=True)\n",
            encoding="utf-8")
        f = self._agent()._check_code_security()
        self.assertEqual(f[0].schwere, "ok")

    def test_code_security_ignoriert_strings_und_testdateien(self):
        (self.root / "orchestrator" / "tests").mkdir(parents=True)
        (self.root / "orchestrator" / "tests" / "test_x.py").write_text(
            "import os\nos.system('rm -rf /')\n", encoding="utf-8")           # Testdatei -> ignoriert
        (self.root / "orchestrator" / "mod.py").write_text(
            "MUSTER = 'os.system'\nHINWEIS = 'nutze kein eval()'\n", encoding="utf-8")  # nur Strings
        f = self._agent()._check_code_security()
        self.assertEqual(f[0].schwere, "ok")

    def test_lauf_liefert_risiko_score(self):
        run = lambda cmd: "orchestrator/.env\n" if "ls-files" in cmd else ""
        a = self._agent(run=run, env={"LUNA_OS_PASSWORD": ""}, notify=lambda text, **kw: None)
        r = a.lauf()
        self.assertIn("score", r)
        self.assertGreater(r["score"], 0)
        self.assertLessEqual(r["score"], 100)

    def test_lauf_meldet_und_antrag(self):
        gemeldet = []
        class FakeAntraege:
            def __init__(self): self.calls = []
            def stellen(self, titel, beschreibung, *, von="", kategorie=""):
                self.calls.append((titel, von, kategorie)); return "A-1"
        ant = FakeAntraege()
        # .env getrackt -> mind. ein Befund
        run = lambda cmd: "orchestrator/.env\n" if "ls-files" in cmd else ""
        a = self._agent(run=run, env={"LUNA_OS_PASSWORD": ""},
                        notify=lambda text, **kw: gemeldet.append((text, kw)), antraege=ant)
        r = a.lauf(als_antrag=True)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["befunde"], 1)
        self.assertEqual(len(gemeldet), 1)
        self.assertEqual(gemeldet[0][1]["kategorie"], "security")
        self.assertEqual(r["antrag_id"], "A-1")
        self.assertEqual(ant.calls[0][1], "CISO/Security")

    def test_lauf_ohne_luecken_kein_antrag(self):
        gemeldet = []
        run = lambda cmd: "orchestrator/app.py\n" if "ls-files" in cmd else '{"dependencies":[]}'
        a = self._agent(run=run, env={"LUNA_OS_PASSWORD": "stark"},
                        notify=lambda text, **kw: gemeldet.append(text))
        r = a.lauf(als_antrag=True)
        self.assertEqual(r["befunde"], 0)
        self.assertEqual(gemeldet, [])            # keine Luecke -> keine Meldung
        self.assertIsNone(r["antrag_id"])


if __name__ == "__main__":
    unittest.main()
