"""Instagram-Postfach-Archiv (Collab-Radar Phase 1): Store-Faltung/Dedup + Voll-Sync (ein/aus)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.ig_inbox import IgInboxStore, IgInboxSync


class FakeReader:
    own_id = "OWN"
    verfuegbar = True
    letzter_fehler = ""

    def __init__(self, threads):
        self._t = threads

    def konversationen(self, *, limit=None, deadline=0.0):
        return list(self._t.keys())

    def kontakt(self, conv):
        return self._t[conv]["kontakt"]

    def nachrichten_seit(self, conv, *, seit_ts=0.0, max_seiten=40, deadline=0.0):
        return self._t[conv]["msgs"]


class TestIgInboxStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = IgInboxStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_nachricht_dedup_und_faltung(self):
        self.store.nachricht_hinzu("U1", "partnerco", richtung="ein", text="Hi", medien=False,
                                   extern_id="m1", ts_msg="2026-06-01T10:00:00+0000")
        self.store.nachricht_hinzu("U1", "partnerco", richtung="aus", text="Klar", medien=False,
                                   extern_id="m2", ts_msg="2026-06-01T11:00:00+0000")
        # Duplikat (gleiche extern_id) -> nicht erneut
        self.assertEqual(self.store.nachricht_hinzu("U1", "partnerco", richtung="ein", text="x", medien=False,
                                                    extern_id="m1", ts_msg="t"), "")
        # Ohne ID -> uebersprungen
        self.assertEqual(self.store.nachricht_hinzu("U1", "p", richtung="ein", text="y", medien=False,
                                                    extern_id="", ts_msg="t"), "")
        k = self.store.kontakte()
        self.assertEqual(len(k), 1)
        self.assertEqual((k[0]["nachrichten"], k[0]["ein"], k[0]["aus"]), (2, 1, 1))
        self.assertEqual(k[0]["name"], "partnerco")

    def test_letzte_richtung_und_medien_marker(self):
        self.store.nachricht_hinzu("U1", "co", richtung="aus", text="hallo", medien=False,
                                   extern_id="a", ts_msg="2026-06-01T10:00:00+0000")
        self.store.nachricht_hinzu("U1", "co", richtung="ein", text="", medien=True,
                                   extern_id="b", ts_msg="2026-06-02T10:00:00+0000")
        k = self.store.zustand("U1")
        self.assertEqual(k["letzte_richtung"], "ein")
        self.assertEqual(k["letzter_text"], "[Medien]")
        verlauf = self.store.verlauf("U1")
        self.assertEqual([m["id"] for m in verlauf], ["a", "b"])   # chronologisch aelteste zuerst

    def test_analyse_gesehen_reminder_in_faltung(self):
        self.store.nachricht_hinzu("U1", "co", richtung="ein", text="Collab?", medien=False,
                                   extern_id="m1", ts_msg="2026-06-01T10:00:00+0000")
        self.assertTrue(self.store.braucht_analyse("U1"))          # noch nie analysiert
        self.store.analyse_setzen("U1", {"collab": True, "zusammenfassung": "Koop-Anfrage",
                                         "offene_todos": ["antworten"], "warten_auf": "uns",
                                         "letzte_nachricht_ts": "2026-06-01T10:00:00+0000", "modell": "haiku"})
        self.assertFalse(self.store.braucht_analyse("U1"))         # bis neue Nachricht kommt
        self.store.gesehen_setzen("U1", seen_ts="2026-06-02T09:00:00+0000", seen_mid="s1")
        self.store.reminder_setzen("U1")
        k = self.store.zustand("U1")
        self.assertTrue(k["analyse"]["collab"])
        self.assertEqual(k["gesehen_ts"], "2026-06-02T09:00:00+0000")
        self.assertIsNotNone(k["reminder_ts"])
        # neue Nachricht -> wieder analysebeduerftig
        self.store.nachricht_hinzu("U1", "co", richtung="ein", text="Noch da?", medien=False,
                                   extern_id="m2", ts_msg="2026-06-05T10:00:00+0000")
        self.assertTrue(self.store.braucht_analyse("U1"))


class TestIgInboxSync(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = IgInboxStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def _reader(self):
        return FakeReader({"c1": {"kontakt": {"id": "U1", "username": "partnerco"}, "msgs": [
            {"id": "m1", "from_id": "U1", "from_username": "partnerco", "text": "Hi, Collab?", "ts": "2026-06-01T10:00:00+0000"},
            {"id": "m2", "from_id": "OWN", "from_username": "hanserautisch", "text": "Klar!", "ts": "2026-06-01T11:00:00+0000"},
            {"id": "m3", "from_id": "U1", "from_username": "partnerco", "text": "", "ts": "2026-06-02T09:00:00+0000"},
        ]}})

    def test_voll_sync_spiegelt_ein_und_ausgehend(self):
        r = IgInboxSync(store=self.store, reader=self._reader()).voll_sync(wochen=99)
        self.assertTrue(r["ok"])
        self.assertEqual((r["threads"], r["nachrichten"], r["neu"]), (1, 3, 3))
        k = self.store.zustand("U1")
        self.assertEqual((k["ein"], k["aus"]), (2, 1))              # ausgehende m2 korrekt dem Kontakt zugeordnet
        self.assertEqual(k["name"], "partnerco")

    def test_voll_sync_dedupliziert(self):
        IgInboxSync(store=self.store, reader=self._reader()).voll_sync(wochen=99)
        r2 = IgInboxSync(store=self.store, reader=self._reader()).voll_sync(wochen=99)
        self.assertEqual(r2["neu"], 0)

    def test_voll_sync_ohne_reader(self):
        class Leer:
            verfuegbar = False
        r = IgInboxSync(store=self.store, reader=Leer()).voll_sync()
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
