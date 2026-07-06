"""Selbst-erneuernder Instagram-Token-Manager -- Austausch, Persistenz, Refresh-Fenster, Seitenwahl.

Alles offline (injizierter HTTP). Prueft: Seed -> long-lived Nutzer-Token -> permanenter Seiten-Token;
gespeicherter Token wird wiederverwendet; nahe Ablauf wird verlaengert; Fallback auf statischen Token.
"""
import json
import os
import tempfile
import time
import unittest

from orchestrator.governance.instagram_token import InstagramTokenManager, ig_reader_aus_env


class FakeGraph:
    """Minimaler Graph-Mock: zaehlt Aufrufe, liefert Austausch- + /me/accounts-Antworten."""

    def __init__(self):
        self.exchanges = 0
        self.accounts = 0
        self.last_account_token = None

    def http(self, path, params):
        if path == "oauth/access_token":
            self.exchanges += 1
            return {"access_token": "LL_" + params["fb_exchange_token"], "expires_in": 60 * 86400}
        if path == "me/accounts":
            self.accounts += 1
            self.last_account_token = params["access_token"]
            return {"data": [
                {"id": "p_other", "name": "Andere", "access_token": "PT_OTHER",
                 "instagram_business_account": {"id": "999", "username": "andere"}},
                {"id": "p_han", "name": "Hanserautisch", "access_token": "PT_HAN",
                 "instagram_business_account": {"id": "17841", "username": "hanserautisch"}},
            ]}
        raise AssertionError("unerwarteter Pfad: " + path)


class TestInstagramTokenManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = os.path.join(self.tmp, "ig_token.json")
        self.g = FakeGraph()

    def _mgr(self, **kw):
        return InstagramTokenManager(user_token_seed=kw.get("seed", "SEED"), app_secret="secret",
                                     app_id="APPID", state_path=self.store, http=self.g.http)

    def test_seed_wird_zu_longlived_und_seiten_token(self):
        m = self._mgr()
        pt = m.page_token(ig_user_id="17841")
        self.assertEqual(pt, "PT_HAN")                       # richtige Seite ueber IG-ID gewaehlt
        self.assertEqual(self.g.exchanges, 1)                # Seed einmal ausgetauscht
        self.assertEqual(self.g.last_account_token, "LL_SEED")  # /me/accounts mit long-lived Token
        gespeichert = json.load(open(self.store))
        self.assertEqual(gespeichert["user_token"], "LL_SEED")
        self.assertGreater(gespeichert["expires_at"], time.time() + 50 * 86400)

    def test_prozess_cache_kein_zweiter_call(self):
        m = self._mgr()
        m.page_token(ig_user_id="17841")
        m.page_token(ig_user_id="17841")
        self.assertEqual(self.g.accounts, 1)                 # zweiter Aufruf aus Prozess-Cache

    def test_gespeicherter_token_wird_wiederverwendet(self):
        json.dump({"user_token": "LL_ALT", "expires_at": int(time.time() + 40 * 86400)}, open(self.store, "w"))
        m = self._mgr(seed="")                               # kein Seed -> muss Store nutzen
        pt = m.page_token(ig_user_id="17841")
        self.assertEqual(pt, "PT_HAN")
        self.assertEqual(self.g.exchanges, 0)                # noch lange gueltig -> kein Austausch
        self.assertEqual(self.g.last_account_token, "LL_ALT")

    def test_nahe_ablauf_wird_verlaengert(self):
        json.dump({"user_token": "LL_ALT", "expires_at": int(time.time() + 3 * 86400)}, open(self.store, "w"))
        m = self._mgr(seed="")                               # <7 Tage -> verlaengern
        m.page_token(ig_user_id="17841")
        self.assertEqual(self.g.exchanges, 1)                # verlaengert (aus dem alten Token)
        self.assertEqual(self.g.last_account_token, "LL_LL_ALT")
        self.assertEqual(json.load(open(self.store))["user_token"], "LL_LL_ALT")

    def test_verfuegbar(self):
        self.assertTrue(self._mgr().verfuegbar())
        self.assertFalse(InstagramTokenManager(user_token_seed="", app_secret="", state_path=self.store).verfuegbar())

    def test_reader_fallback_auf_statischen_token(self):
        # Kein User-Token/Secret -> statischer INSTAGRAM_ACCESS_TOKEN wird genutzt.
        r = ig_reader_aus_env({"INSTAGRAM_ACCESS_TOKEN": "STATIC", "INSTAGRAM_IG_USER_ID": "17841"},
                              state_path=self.store)
        self.assertEqual(r.token, "STATIC")
        self.assertEqual(r.own_id, "17841")

    def test_reader_nutzt_manager_wenn_vorhanden(self):
        env = {"INSTAGRAM_USER_TOKEN": "SEED", "INSTAGRAM_APP_SECRET": "secret",
               "INSTAGRAM_APP_ID": "APPID", "INSTAGRAM_IG_USER_ID": "17841"}
        r = ig_reader_aus_env(env, state_path=self.store, http=self.g.http)
        self.assertEqual(r.token, "PT_HAN")                  # permanenter Seiten-Token statt statisch


if __name__ == "__main__":
    unittest.main()
