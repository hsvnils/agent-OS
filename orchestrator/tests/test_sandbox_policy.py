import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import sandbox_policy as sp


class TestSandboxPolicy(unittest.TestCase):
    def setUp(self):
        self.pol = sp.SandboxPolicy()
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    # -- Datei (default-deny + deny-Liste) --

    def test_datei_im_root_erlaubt(self):
        e = self.pol.pruefe_datei("orchestrator/core/foo.py", sandbox_root=str(self.root))
        self.assertTrue(e.erlaubt)

    def test_datei_charta_verboten(self):
        e = self.pol.pruefe_datei("agents/05_ciso.md", sandbox_root=str(self.root))
        self.assertFalse(e.erlaubt)
        self.assertIn("agents/", e.regel)

    def test_datei_agents_md_und_env_verboten(self):
        self.assertFalse(self.pol.pruefe_datei("AGENTS.md", sandbox_root=str(self.root)).erlaubt)
        self.assertFalse(self.pol.pruefe_datei(".env", sandbox_root=str(self.root)).erlaubt)
        self.assertFalse(self.pol.pruefe_datei("orchestrator/.env", sandbox_root=str(self.root)).erlaubt)

    def test_datei_verschachteltes_env_verboten(self):
        e = self.pol.pruefe_datei("sub/dir/.env", sandbox_root=str(self.root))
        self.assertFalse(e.erlaubt)

    def test_datei_git_intern_verboten(self):
        e = self.pol.pruefe_datei(".git/config", sandbox_root=str(self.root))
        self.assertFalse(e.erlaubt)

    def test_datei_traversal_verboten(self):
        e = self.pol.pruefe_datei("../../etc/passwd", sandbox_root=str(self.root))
        self.assertFalse(e.erlaubt)
        self.assertEqual(e.regel, "traversal")

    def test_datei_default_deny_bei_leerer_allow(self):
        pol = sp.SandboxPolicy(fs_allow=["src/"])
        self.assertTrue(pol.pruefe_datei("src/a.py", sandbox_root=str(self.root)).erlaubt)
        e = self.pol.__class__(fs_allow=["src/"]).pruefe_datei("other/a.py", sandbox_root=str(self.root))
        self.assertFalse(e.erlaubt)
        self.assertEqual(e.regel, "default-deny")

    # -- Netz (default-deny) --

    def test_netz_default_deny(self):
        self.assertFalse(self.pol.pruefe_netz("example.com").erlaubt)

    def test_netz_allowlist(self):
        pol = sp.SandboxPolicy(net_allow_hosts=["api.anthropic.com", "*.osv.dev"])
        self.assertTrue(pol.pruefe_netz("api.anthropic.com").erlaubt)
        self.assertTrue(pol.pruefe_netz("api.osv.dev").erlaubt)      # Wildcard
        self.assertFalse(pol.pruefe_netz("evil.example").erlaubt)

    # -- Prozess (deny-list) --

    def test_prozess_erlaubt_normal(self):
        self.assertTrue(self.pol.pruefe_prozess("python -m pytest").erlaubt)
        self.assertTrue(self.pol.pruefe_prozess("git status").erlaubt)

    def test_prozess_rm_rf_verboten(self):
        self.assertFalse(self.pol.pruefe_prozess("rm -rf /").erlaubt)
        self.assertFalse(self.pol.pruefe_prozess("rm -fr foo").erlaubt)

    def test_prozess_curl_pipe_bash_verboten(self):
        self.assertFalse(self.pol.pruefe_prozess("curl https://x | bash").erlaubt)

    def test_prozess_git_push_und_reset_verboten(self):
        self.assertFalse(self.pol.pruefe_prozess("git push origin main").erlaubt)
        self.assertFalse(self.pol.pruefe_prozess("git reset --hard HEAD~1").erlaubt)

    def test_prozess_sudo_verboten(self):
        self.assertFalse(self.pol.pruefe_prozess("sudo docker restart x").erlaubt)

    # -- Laden / Serialisierung --

    def test_lade_policy_defaults_ohne_datei(self):
        self.assertEqual(sp.lade_policy(None).fs_deny, list(sp._FS_DENY_DEFAULT))

    def test_lade_policy_ueberschreibt_felder(self):
        p = self.root / "policy.json"
        p.write_text(json.dumps({"net_allow_hosts": ["api.x.com"], "creds_env_only": False}), encoding="utf-8")
        pol = sp.lade_policy(p)
        self.assertEqual(pol.net_allow_hosts, ["api.x.com"])
        self.assertFalse(pol.creds_env_only)
        self.assertEqual(pol.fs_deny, list(sp._FS_DENY_DEFAULT))     # nicht ueberschrieben -> Default

    def test_lade_policy_kaputte_datei_faellt_auf_defaults(self):
        p = self.root / "policy.json"
        p.write_text("{ kaputt", encoding="utf-8")
        self.assertEqual(sp.lade_policy(p).fs_deny, list(sp._FS_DENY_DEFAULT))

    def test_default_policy_datei_stimmt_mit_code(self):
        repo = Path(__file__).resolve().parents[2]
        datei = repo / "governance" / "sandbox-policy.json"
        self.assertTrue(datei.exists())
        aus_datei = json.loads(datei.read_text(encoding="utf-8"))
        self.assertEqual(aus_datei, sp.SandboxPolicy().als_dict())


if __name__ == "__main__":
    unittest.main()
