import hashlib
import hmac
import unittest

from orchestrator.governance.instagram import InstagramAuth, InstagramMessaging, MockInstagramMessaging


class TestInstagram(unittest.TestCase):
    def setUp(self):
        self.ig = InstagramMessaging(InstagramAuth(app_secret="s3cr3t_app", verify_token="vtok"))

    def test_verify_challenge_ok(self):
        self.assertEqual(self.ig.verify_challenge("subscribe", "vtok", "12345"), "12345")

    def test_verify_challenge_falscher_token_oder_modus(self):
        self.assertIsNone(self.ig.verify_challenge("subscribe", "falsch", "12345"))
        self.assertIsNone(self.ig.verify_challenge("unsubscribe", "vtok", "12345"))

    def test_signatur_pruefung(self):
        body = b'{"hello":"world"}'
        sig = hmac.new(b"s3cr3t_app", body, hashlib.sha256).hexdigest()
        self.assertTrue(self.ig.signatur_gueltig(body, "sha256=" + sig))
        self.assertFalse(self.ig.signatur_gueltig(body, "sha256=deadbeef"))
        self.assertFalse(self.ig.signatur_gueltig(body, ""))            # kein Header -> ungueltig

    def test_nachrichten_aus_webhook_nur_eingehender_text(self):
        payload = {"object": "instagram", "entry": [{"messaging": [
            {"sender": {"id": "user1"}, "message": {"mid": "m1", "text": "Wir wollen kooperieren"}},
            {"sender": {"id": "me"}, "message": {"mid": "m2", "text": "echo", "is_echo": True}},   # eigenes Echo
            {"sender": {"id": "user2"}, "message": {"mid": "m3", "attachments": [{}]}},            # kein Text
        ]}]}
        ns = InstagramMessaging.nachrichten_aus_webhook(payload)
        self.assertEqual(len(ns), 1)
        self.assertEqual(ns[0]["extern_id"], "m1")
        self.assertEqual(ns[0]["absender"], "user1")
        self.assertIn("kooperieren", ns[0]["text"])

    def test_nachrichten_feldprobe_flach(self):
        # Metas "Feldprobe" sendet ein flaches {"field":"messages","value":{...}}
        payload = {"field": "messages", "value": {"sender": {"id": "12334"}, "recipient": {"id": "23245"},
                   "timestamp": "1527459824", "message": {"mid": "random_mid", "text": "random_text"}}}
        ns = InstagramMessaging.nachrichten_aus_webhook(payload)
        self.assertEqual(len(ns), 1)
        self.assertEqual(ns[0]["absender"], "12334")
        self.assertEqual(ns[0]["text"], "random_text")

    def test_nachrichten_changes_form(self):
        payload = {"object": "instagram", "entry": [{"changes": [{"field": "messages", "value": {
            "sender": {"id": "u9"}, "message": {"mid": "m9", "text": "Kooperation via changes"}}}]}]}
        ns = InstagramMessaging.nachrichten_aus_webhook(payload)
        self.assertEqual(len(ns), 1)
        self.assertEqual(ns[0]["absender"], "u9")

    def test_verfuegbar_und_fall_b(self):
        self.assertTrue(self.ig.verfuegbar())
        leer = InstagramMessaging(InstagramAuth())
        self.assertFalse(leer.verfuegbar())
        self.assertTrue(leer.fall_b()["fall_b"])

    def test_from_env(self):
        a = InstagramAuth.from_env({"INSTAGRAM_APP_SECRET": "x1234567890", "INSTAGRAM_VERIFY_TOKEN": "v"})
        self.assertEqual(a.app_secret, "x1234567890")
        self.assertTrue(a.verfuegbar())

    def test_mock_signatur_immer_gueltig(self):
        self.assertTrue(MockInstagramMessaging().signatur_gueltig(b"beliebig", ""))


if __name__ == "__main__":
    unittest.main()
