import tempfile
import unittest
from pathlib import Path

from orchestrator.core.security_agent import Finding, SecurityAgent, nach_sarif


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

    def test_osv_findet_vulnerable_pin(self):
        (self.root / "deploy").mkdir()
        (self.root / "deploy" / "Dockerfile").write_text(
            'RUN pip install "requests==2.0.0" "safe==1.0.0"\n', encoding="utf-8")
        def fake_http(url, body):
            return {"vulns": [{"id": "GHSA-xxxx"}]} if body["package"]["name"] == "requests" else {}
        f = self._agent(http=fake_http)._check_osv()
        self.assertEqual(f[0].schwere, "hoch")
        self.assertIn("requests 2.0.0", f[0].detail)
        self.assertIn("GHSA-xxxx", f[0].detail)

    def test_osv_sauber(self):
        (self.root / "deploy").mkdir()
        (self.root / "deploy" / "Dockerfile").write_text('RUN pip install "safe==1.0.0"\n', encoding="utf-8")
        f = self._agent(http=lambda url, body: {})._check_osv()
        self.assertEqual(f[0].schwere, "ok")

    def test_dockerfile_pins_parsing(self):
        (self.root / "deploy").mkdir()
        (self.root / "deploy" / "Dockerfile").write_text(
            'RUN pip install "a-b==1.2.3" "c==4.5" "pip>=26.1.2"\n', encoding="utf-8")
        pins = dict(self._agent()._dockerfile_pins())
        self.assertEqual(pins.get("a-b"), "1.2.3")
        self.assertEqual(pins.get("c"), "4.5")
        self.assertNotIn("pip", pins)   # >=-Pin wird bewusst ignoriert

    def test_audit_ohne_http_kein_osv(self):
        (self.root / "deploy").mkdir()
        (self.root / "deploy" / "Dockerfile").write_text('RUN pip install "x==1.0"\n', encoding="utf-8")
        findings = self._agent(http=None).audit()
        self.assertFalse(any(f.kategorie == "supply-chain" for f in findings))

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


    def test_sarif_grundstruktur_und_level_mapping(self):
        findings = [
            Finding("code-security", "hoch", "riskante Aufrufe", "mod.py:3 (eval())", "absichern"),
            Finding("hardening", "mittel", "Login offen", "kein Passwort", "Passwort setzen"),
            Finding("dependencies", "niedrig", "kein Audit", "", "pip-audit"),
            Finding("secret-hygiene", "ok", "alles gut", "", ""),   # ok -> kein SARIF-Result
        ]
        doc = nach_sarif(findings)
        self.assertEqual(doc["version"], "2.1.0")
        run = doc["runs"][0]
        results = run["results"]
        self.assertEqual(len(results), 3)                          # ok wurde ausgelassen
        levels = {r["ruleId"]: r["level"] for r in results}
        self.assertEqual(levels["code-security"], "error")
        self.assertEqual(levels["hardening"], "warning")
        self.assertEqual(levels["dependencies"], "note")
        self.assertIn("mod.py:3", results[0]["message"]["text"])
        self.assertEqual(results[0]["properties"]["empfehlung"], "absichern")
        # Regeln je Kategorie dedupliziert
        rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
        self.assertEqual(rule_ids, {"code-security", "hardening", "dependencies"})

    def test_sarif_leer_wenn_alles_ok(self):
        doc = nach_sarif([Finding("x", "ok", "gut", "", "")])
        self.assertEqual(doc["runs"][0]["results"], [])
        self.assertEqual(doc["runs"][0]["tool"]["driver"]["rules"], [])

    def test_sarif_regeln_dedupliziert(self):
        findings = [Finding("code-security", "hoch", "a", "", ""),
                    Finding("code-security", "mittel", "b", "", "")]
        rules = nach_sarif(findings)["runs"][0]["tool"]["driver"]["rules"]
        self.assertEqual(len(rules), 1)

    def test_agent_sarif_methode(self):
        run = lambda cmd: "orchestrator/.env\n" if "ls-files" in cmd else ""
        doc = self._agent(run=run, env={"LUNA_OS_PASSWORD": ""}).sarif()
        self.assertEqual(doc["version"], "2.1.0")
        self.assertTrue(doc["runs"][0]["results"])                 # .env getrackt -> mind. ein Result


if __name__ == "__main__":
    unittest.main()
