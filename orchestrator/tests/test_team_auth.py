import unittest

from orchestrator.core.team_auth import (TeamAuth, erlaubte_apps, hash_passwort, hat_modul,
                                         modul_fuer_pfad, module_fuer_rolle, pruefe_passwort)
from orchestrator.governance.supabase import MockSupabaseClient, SupabaseAuth, SupabaseClient


class TestPasswort(unittest.TestCase):
    def test_hash_roundtrip(self):
        h = hash_passwort("geheim123")
        self.assertTrue(h.startswith("pbkdf2_sha256$"))
        self.assertNotIn("geheim123", h)                 # nie Klartext
        self.assertTrue(pruefe_passwort("geheim123", h))
        self.assertFalse(pruefe_passwort("falsch", h))

    def test_hash_salt_zufaellig(self):
        self.assertNotEqual(hash_passwort("x"), hash_passwort("x"))   # unterschiedlicher Salt

    def test_pruefe_kaputter_hash(self):
        self.assertFalse(pruefe_passwort("x", "muell"))
        self.assertFalse(pruefe_passwort("x", ""))


class TestRollenModule(unittest.TestCase):
    def test_owner_hat_alles(self):
        u = {"role": "owner", "allowed_modules": []}
        self.assertTrue(hat_modul(u, "content_ops"))
        self.assertTrue(hat_modul(u, "administration"))

    def test_modul_liste(self):
        u = {"role": "content", "allowed_modules": ["content_ops"]}
        self.assertTrue(hat_modul(u, "content_ops"))
        self.assertFalse(hat_modul(u, "invest"))

    def test_erlaubte_apps(self):
        u = {"role": "content", "allowed_modules": ["content_ops"]}
        apps = erlaubte_apps(u)
        self.assertIn("home", apps)
        self.assertIn("trends", apps)
        self.assertIn("drafts", apps)
        self.assertNotIn("auftraege", apps)   # administration
        self.assertNotIn("crm", apps)

    def test_owner_alle_apps(self):
        apps = erlaubte_apps({"role": "owner", "allowed_modules": []})
        for a in ("trends", "crm", "investment", "auftraege", "finance", "luna", "home", "team"):
            self.assertIn(a, apps)

    def test_team_app_nur_administration(self):
        self.assertIn("team", erlaubte_apps({"role": "owner", "allowed_modules": []}))
        self.assertNotIn("team", erlaubte_apps({"role": "content", "allowed_modules": ["content_ops"]}))

    def test_module_fuer_rolle(self):
        self.assertEqual(module_fuer_rolle("owner"), ["content_ops", "crm", "invest", "administration"])
        self.assertEqual(module_fuer_rolle("content"), ["content_ops"])
        self.assertEqual(module_fuer_rolle("unbekannt"), ["content_ops"])


class TestPfadModul(unittest.TestCase):
    def test_content_ops(self):
        self.assertEqual(modul_fuer_pfad("GET", "/api/trends"), "content_ops")
        self.assertEqual(modul_fuer_pfad("POST", "/api/drafts/abc/status"), "content_ops")
        self.assertEqual(modul_fuer_pfad("GET", "/api/ai-inbox"), "content_ops")

    def test_crm_invest(self):
        self.assertEqual(modul_fuer_pfad("GET", "/api/crm"), "crm")
        self.assertEqual(modul_fuer_pfad("POST", "/api/investment/screen"), "invest")

    def test_administration(self):
        self.assertEqual(modul_fuer_pfad("POST", "/api/antraege/x/freigeben"), "administration")
        self.assertEqual(modul_fuer_pfad("POST", "/api/chat"), "administration")

    def test_team_verwaltung_gated(self):
        self.assertEqual(modul_fuer_pfad("GET", "/api/team"), "administration")
        self.assertEqual(modul_fuer_pfad("POST", "/api/team"), "administration")
        self.assertEqual(modul_fuer_pfad("POST", "/api/team/lisa/aktiv"), "administration")

    def test_kernendpunkt_kein_modul(self):
        self.assertIsNone(modul_fuer_pfad("GET", "/api/state"))
        self.assertIsNone(modul_fuer_pfad("GET", "/api/overview"))
        self.assertIsNone(modul_fuer_pfad("GET", "/api/antraege/x"))   # GET-Detail = Kern (lesen)


class TestTeamAuthStore(unittest.TestCase):
    def _mit_nutzer(self):
        mock = MockSupabaseClient()
        ta = TeamAuth(mock)
        # Nutzer direkt in die Mock-Rows legen (wie ein echter Datensatz mit Hash)
        mock.rows["luna_os_users"] = [{
            "id": "u1", "username": "lisa", "display_name": "Lisa", "role": "content",
            "allowed_modules": ["content_ops"], "is_active": True,
            "password_hash": hash_passwort("pw-lisa")}]
        return ta, mock

    def test_verify_ok(self):
        ta, _ = self._mit_nutzer()
        u = ta.verify("lisa", "pw-lisa")
        self.assertIsNotNone(u)
        self.assertEqual(u["role"], "content")
        self.assertNotIn("password_hash", u)   # Hash nie zurueckgeben

    def test_verify_falsches_passwort(self):
        ta, _ = self._mit_nutzer()
        self.assertIsNone(ta.verify("lisa", "falsch"))

    def test_verify_inaktiv(self):
        ta, mock = self._mit_nutzer()
        mock.rows["luna_os_users"][0]["is_active"] = False
        self.assertIsNone(ta.verify("lisa", "pw-lisa"))

    def test_verify_unbekannt(self):
        ta, _ = self._mit_nutzer()
        self.assertIsNone(ta.verify("niemand", "x"))

    def test_anlegen_hasht(self):
        mock = MockSupabaseClient()
        ta = TeamAuth(mock)
        r = ta.anlegen("max", "pw-max", role="team")
        self.assertTrue(r["ok"])
        tabelle, rows, on_conflict = mock.upserts[-1]
        self.assertEqual(tabelle, "luna_os_users")
        self.assertEqual(on_conflict, "username")
        self.assertNotIn("pw-max", rows[0]["password_hash"])          # kein Klartext
        self.assertTrue(rows[0]["password_hash"].startswith("pbkdf2"))
        self.assertEqual(rows[0]["allowed_modules"], ["content_ops", "crm"])  # role team

    def test_anlegen_explizite_module(self):
        mock = MockSupabaseClient()
        r = TeamAuth(mock).anlegen("t", "p", role="content", allowed_modules=["content_ops", "invest"])
        self.assertTrue(r["ok"])
        self.assertEqual(mock.upserts[-1][1][0]["allowed_modules"], ["content_ops", "invest"])

    def test_liste_ohne_hash(self):
        ta, _ = self._mit_nutzer()
        eintraege = ta.liste()
        self.assertEqual(eintraege[0]["username"], "lisa")
        self.assertNotIn("password_hash", eintraege[0])

    def test_offline_graceful(self):
        ta = TeamAuth(SupabaseClient(SupabaseAuth()))   # nicht verfuegbar
        self.assertFalse(ta.verfuegbar())
        self.assertIsNone(ta.verify("x", "y"))
        self.assertEqual(ta.liste(), [])
        self.assertFalse(ta.anlegen("x", "y")["ok"])


if __name__ == "__main__":
    unittest.main()
