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

    def test_nachrichten_seit_blaettert_und_stoppt_am_cutoff(self):
        import datetime
        import time
        now = datetime.datetime.now(datetime.timezone.utc)

        def iso(days):
            return (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S+0000")

        calls = {"n": 0}

        def http(pfad, params):
            calls["n"] += 1
            f = params["fields"]
            if ".after(" not in f:                              # Seite 1 (neueste)
                return {"messages": {"data": [
                    {"id": "m1", "from": {"id": "U1", "username": "co"}, "message": "neu", "created_time": iso(1)}],
                    "paging": {"cursors": {"after": "A1"}}}}
            if "after(A1)" in f:                                # Seite 2: eine im Fenster, eine zu alt
                return {"messages": {"data": [
                    {"id": "m2", "from": {"id": "U1", "username": "co"}, "message": "mittel", "created_time": iso(5)},
                    {"id": "m3", "from": {"id": "U1", "username": "co"}, "message": "zu alt", "created_time": iso(70)}],
                    "paging": {"cursors": {"after": "A2"}}}}
            raise AssertionError("darf nach dem Cutoff nicht weiterblaettern")

        r = InstagramConversations("tok", "OWN", http=http)
        msgs = r.nachrichten_seit("c1", seit_ts=time.time() - 56 * 86400)   # 8 Wochen
        self.assertEqual([m["id"] for m in msgs], ["m1", "m2"])              # m3 (70 Tage) raus
        self.assertEqual(calls["n"], 2)                                     # Stopp am Cutoff, keine 3. Seite


class FakeReader:
    own_id = "OWN"
    verfuegbar = True

    def __init__(self, convs):
        self._c = convs

    def konversationen(self, *, limit=None):
        return list(self._c.keys())

    def nachrichten(self, conv):
        return self._c[conv]

    def nachrichten_seit(self, conv, *, seit_ts=0.0, max_seiten=40):   # Backfill nutzt dieselben Daten
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

    def test_backfill_zaehlt_und_dedupliziert(self):
        r = CrmInstagramTracker(crm=self.crm, reader=self._reader()).backfill(wochen=8)
        self.assertTrue(r["ok"])
        self.assertEqual(r["wochen"], 8)
        self.assertEqual(r["threads"], 1)
        self.assertEqual(r["nachrichten"], 3)      # transparente Aufschluesselung
        self.assertEqual(r["ausgehend"], 1)        # m2 (OWN)
        self.assertEqual(r["eingehend"], 2)        # m1 + m3
        self.assertEqual(r["eingehend_ohne_text"], 1)  # m3 (leer)
        self.assertEqual(r["gesehen"], 1)          # nur m1 (eingehend + Text)
        self.assertEqual(r["neu"], 1)
        r2 = CrmInstagramTracker(crm=self.crm, reader=self._reader()).backfill(wochen=8)
        self.assertEqual(r2["neu"], 0)             # gleiche Message-IDs -> Dedup

    def test_backfill_ohne_token_hinweis(self):
        r = CrmInstagramTracker(crm=self.crm, reader=InstagramConversations("", "")).backfill()
        self.assertFalse(r["ok"])
        self.assertIn("Token", r["hinweis"])


if __name__ == "__main__":
    unittest.main()
