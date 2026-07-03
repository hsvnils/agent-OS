import tempfile
import unittest
from pathlib import Path

from orchestrator.core.crm import CrmStore
from orchestrator.core.crm_instagram import CrmInstagramTracker
from orchestrator.governance.instagram import InstagramConversations


class TestInstagramConversations(unittest.TestCase):
    def test_verfuegbar(self):
        self.assertFalse(InstagramConversations("", "123").verfuegbar)
        self.assertFalse(InstagramConversations("tok", "").verfuegbar)
        self.assertTrue(InstagramConversations("tok", "123").verfuegbar)

    def test_parsing_mit_http(self):
        def http(pfad, params):
            if pfad == "me/conversations":                      # DMs ueber den Seiten-Knoten
                self.assertEqual(params["platform"], "instagram")
                return {"data": [{"id": "c1"}, {"id": "c2"}]}
            return {"messages": {"data": [
                {"id": "m1", "from": {"id": "U1", "username": "partnerco"}, "message": "Hallo!"}]}}
        r = InstagramConversations("tok", "OWN", http=http)
        self.assertEqual(r.konversationen(), ["c1", "c2"])
        n = r.nachrichten("c1")
        self.assertEqual(n[0]["from_username"], "partnerco")
        self.assertEqual(n[0]["from_id"], "U1")
        self.assertEqual(n[0]["text"], "Hallo!")

    def test_konv_pfad_immer_me(self):
        self.assertEqual(InstagramConversations("t", "OWN")._konv_pfad(), "me/conversations")

    def test_http_fehler_leer(self):
        def boom(pfad, params):
            raise RuntimeError("net")
        r = InstagramConversations("tok", "OWN", http=boom)
        self.assertEqual(r.konversationen(), [])
        self.assertEqual(r.nachrichten("c1"), [])
        self.assertIn("net", r.letzter_fehler)

    def test_api_fehlerobjekt_sichtbar(self):
        r = InstagramConversations("tok", "OWN",
                                   http=lambda p, q: {"error": {"message": "(#100) requires page token"}})
        self.assertEqual(r.konversationen(), [])
        self.assertIn("page token", r.letzter_fehler)


class FakeReader:
    own_id = "OWN"
    verfuegbar = True

    def __init__(self, convs):
        self._c = convs

    def konversationen(self):
        return list(self._c.keys())

    def nachrichten(self, conv):
        return self._c[conv]


class TestCrmInstagramTracker(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.crm = CrmStore(Path(self.dir.name) / "crm.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def _reader(self):
        return FakeReader({"c1": [
            {"id": "m1", "from_id": "U1", "from_username": "partnerco",
             "text": "Hallo, wir wollen eine Kooperation!", "ts": "t1"},
            {"id": "m2", "from_id": "OWN", "from_username": "", "text": "Antwort von uns", "ts": "t2"},
            {"id": "m3", "from_id": "U1", "from_username": "partnerco", "text": "", "ts": "t3"},
        ]})

    def test_nur_eingehende_nichtleer_ins_crm(self):
        r = CrmInstagramTracker(crm=self.crm, reader=self._reader()).lauf()
        self.assertTrue(r["ok"])
        self.assertEqual(r["gesehen"], 1)     # eigene + leere uebersprungen
        self.assertEqual(r["neu"], 1)
        # im CRM gelandet
        nachr = [e for e in self.crm._events() if e.get("event") == "nachricht"]
        self.assertTrue(any(e.get("extern_id") == "m1" for e in nachr))

    def test_dedup_beim_zweiten_lauf(self):
        CrmInstagramTracker(crm=self.crm, reader=self._reader()).lauf()
        r2 = CrmInstagramTracker(crm=self.crm, reader=self._reader()).lauf()
        self.assertEqual(r2["neu"], 0)        # gleiche Message-IDs -> kein Duplikat

    def test_tracker_reicht_api_fehler_durch(self):
        reader = InstagramConversations("tok", "OWN", http=lambda p, q: {"error": {"message": "boom"}})
        res = CrmInstagramTracker(crm=self.crm, reader=reader).lauf()
        self.assertEqual(res["gesehen"], 0)
        self.assertIn("boom", res.get("api_fehler", ""))

    def test_ohne_token_hinweis(self):
        r = CrmInstagramTracker(crm=self.crm, reader=InstagramConversations("", "")).lauf()
        self.assertFalse(r["ok"])
        self.assertIn("Token", r["hinweis"])


if __name__ == "__main__":
    unittest.main()
