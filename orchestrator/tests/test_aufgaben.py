"""TODOS_ROADMAP T1-T3: eigene To-dos -- Speicher (Gruppen nach Faelligkeit, Standard-Erinnerung 09:00, erledigen,
loeschen), Kalender-Abgleich (anlegen, verschieben, loeschen nur eigene Termine), Telegram-Erinnerung genau einmal je
Zeitpunkt, Knoepfe (Erledigt, +1 Std., morgen, Rueckgaengig), LUNA-Werkzeug ohne Rueckfrage, API und „Zu erledigen“."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from orchestrator.core.aufgaben import (AufgabenStore, erinnerungen_senden, kalender_abgleichen, knopf, morgen_frueh,
                                        zusammenfassung)
from orchestrator.governance.google_workspace import MockGoogleWorkspace
from orchestrator.tests.test_angebote import ApiBasis

J = datetime(2026, 10, 27, 14, 0)


class TestSpeicher(unittest.TestCase):
    def setUp(self):
        self.st = AufgabenStore(Path(tempfile.mkdtemp()) / "todos" / "log.jsonl")

    def test_1_anlegen_und_gruppen(self):
        a = self.st.anlegen("Steuer", faellig="2026-10-27")
        self.assertEqual(a["erinnerung"], "2026-10-27T09:00")                       # ohne Uhrzeit: 09:00
        b = self.st.anlegen("Kiez Alm anrufen", faellig="2026-10-31", uhrzeit="10:00")
        self.assertEqual(b["erinnerung"], "2026-10-31T10:00")
        c = self.st.anlegen("Irgendwann", erinnerung="")
        d = self.st.anlegen("Alt", faellig="2026-10-20", erinnerung="")
        g = self.st.liste(heute="2026-10-27")
        self.assertEqual([[x["id"] for x in g[k]] for k in ("ueberfaellig", "heute", "demnaechst", "ohne_datum")],
                         [[d["id"]], [a["id"]], [b["id"]], [c["id"]]])
        self.st.erledigen(a["id"])
        self.assertEqual([x["id"] for x in self.st.liste(heute="2026-10-27")["erledigt"]], [a["id"]])
        self.st.erledigen(a["id"], False)
        self.assertEqual(self.st.get(a["id"])["status"], "offen")
        self.st.loeschen(c["id"])
        self.assertIsNone(self.st.get(c["id"]))
        for falsch in (lambda: self.st.anlegen(" "), lambda: self.st.anlegen("x", uhrzeit="10:00"),
                       lambda: self.st.anlegen("x", faellig="27.10.2026"), lambda: self.st.anlegen("x", erinnerung="morgen")):
            with self.assertRaises(ValueError):
                falsch()
        with self.assertRaises(KeyError):
            self.st.erledigen("A-00000000")

    def test_2_erinnerung_genau_einmal_und_knoepfe(self):
        a = self.st.anlegen("Steuer", faellig="2026-10-27", uhrzeit="13:30")
        gesendet = []
        senden = lambda text, k: gesendet.append((text, k)) or True
        self.assertEqual(erinnerungen_senden(self.st, senden, jetzt=datetime(2026, 10, 27, 13, 0)), [])
        self.assertEqual(erinnerungen_senden(self.st, senden, jetzt=J), [a["id"]])
        self.assertEqual(erinnerungen_senden(self.st, senden, jetzt=J), [])               # nur einmal
        self.assertIn("Steuer", gesendet[0][0])
        self.assertEqual([x["callback_data"] for x in gesendet[0][1][0]], [f"auf:{a['id']}:ok", f"auf:{a['id']}:1h", f"auf:{a['id']}:morgen"])
        g = MockGoogleWorkspace()
        self.assertIn("Verschoben", knopf(self.st, g, a["id"], "1h", jetzt=J))
        self.assertEqual(self.st.get(a["id"])["erinnerung"], "2026-10-27T15:00")
        self.assertEqual(erinnerungen_senden(self.st, senden, jetzt=datetime(2026, 10, 27, 15, 1)), [a["id"]])  # neu faellig
        knopf(self.st, g, a["id"], "morgen", jetzt=J)
        self.assertEqual(self.st.get(a["id"])["erinnerung"], morgen_frueh(J))
        self.assertIn("Erledigt", knopf(self.st, g, a["id"], "ok", jetzt=J))
        self.assertEqual(self.st.get(a["id"])["status"], "erledigt")
        nicht_angekommen = lambda text, k: False
        b = self.st.anlegen("Zwei", erinnerung="2026-10-27T12:00")
        erinnerungen_senden(self.st, nicht_angekommen, jetzt=J)
        self.assertEqual(self.st.get(b["id"])["erinnert"], "")                             # erneut versuchen

    def test_3_kalender_abgleich(self):
        g = MockGoogleWorkspace()
        g.standard_einladung = "ceo@test"
        a = self.st.anlegen("Steuer", faellig="2099-10-27", uhrzeit="10:00")
        self.assertEqual(kalender_abgleichen(self.st, g, a), "")
        self.assertEqual(g.termine[-1]["titel"], "✅ Steuer")
        self.assertEqual(g.termine[-1]["start"], "2099-10-27T10:00:00")
        tid = self.st.get(a["id"])["termin_id"]
        self.assertTrue(tid)
        x = self.st.erledigen(a["id"])
        kalender_abgleichen(self.st, g, x)
        self.assertEqual(g.geloeschte_termine, [tid])                                     # kuenftiger eigener Termin weg
        self.assertEqual(self.st.get(a["id"])["termin_id"], "")
        ohne = self.st.anlegen("Ohne", erinnerung="")
        n = len(g.termine)
        kalender_abgleichen(self.st, g, ohne)
        self.assertEqual(len(g.termine), n)
        self.assertIn("nicht verbunden", kalender_abgleichen(self.st, None, a))
        self.assertIn("Rückgängig", knopf(self.st, g, ohne["id"], "weg"))
        self.assertIsNone(self.st.get(ohne["id"]))


class TestWerkzeug(unittest.TestCase):
    def test_4_todo_anlegen_ohne_rueckfrage(self):
        from orchestrator.core.hoa_tools import _run_tool
        root = Path(tempfile.mkdtemp())
        g = MockGoogleWorkspace()
        ctx = SimpleNamespace(repo_root=root, google=g, knoepfe=[], leak_secrets=[])
        r = _run_tool("todo_anlegen", {"titel": "Kiez Alm anrufen", "faellig": "2099-10-31", "uhrzeit": "10:00"}, ctx)
        self.assertTrue(r["ok"], r)
        self.assertIn("Kiez Alm anrufen", r["zusammenfassung"])
        self.assertEqual(ctx.knoepfe[0]["callback_data"], f"auf:{r['id']}:weg")
        self.assertEqual(len(g.termine), 1)                                               # Termin ohne Bestaetigung
        st = AufgabenStore(root / "todos" / "log.jsonl")
        self.assertEqual(st.get(r["id"])["quelle"], "Telegram/Chat")
        v = _run_tool("todo_anlegen", {"titel": "Zu spaet", "erinnerung": "2020-01-01T09:00"}, ctx)
        self.assertFalse(v["ok"])
        self.assertIn("Vergangenheit", v["hinweis"])
        z = _run_tool("todos_zeigen", {}, ctx)
        self.assertEqual(z["demnaechst"][0]["titel"], "Kiez Alm anrufen")
        e = _run_tool("todo_erledigen", {"id": r["id"]}, ctx)
        self.assertTrue(e["ok"])
        self.assertFalse(_run_tool("todo_erledigen", {"id": "A-00000000"}, ctx)["ok"])

    def test_5_injektionsschutz_und_auswahl(self):
        from orchestrator.core.input_guard import AKTIONS_WERKZEUGE
        from orchestrator.core.werkzeugauswahl import gruppen_fuer
        self.assertIn("todo_anlegen", AKTIONS_WERKZEUGE)                                   # nach Fremdtext mit Verdacht gesperrt
        for satz in ("To-do: Steuer machen", "Erinnere mich morgen an die Steuer", "Todo Kiez Alm"):
            self.assertIn("aufgaben", gruppen_fuer(satz), satz)


class TestAufgabenApi(ApiBasis):
    def setUp(self):
        super().setUp()
        from unittest import mock
        self._root = mock.patch.object(self.w, "ROOT", Path(tempfile.mkdtemp()))
        self._root.start()

    def tearDown(self):
        self._root.stop()
        super().tearDown() if hasattr(super(), "tearDown") else None

    def test_a1_ablauf(self):
        r = self.c.post("/api/aufgaben", json={"titel": "Steuer", "faellig": "2020-01-01", "uhrzeit": "09:30"}).json()
        self.assertTrue(r["ok"], r)
        aid = r["aufgabe"]["id"]
        self.assertFalse(self.c.post("/api/aufgaben", json={"titel": ""}).json()["ok"])
        d = self.c.get("/api/aufgaben").json()
        self.assertEqual(d["gruppen"]["ueberfaellig"][0]["id"], aid)
        t = {x["id"]: x for x in self.c.get("/api/todos").json()["todos"]}
        self.assertIn(f"auf:{aid}", t)                                                     # in „Zu erledigen“
        self.assertEqual(t[f"auf:{aid}"]["erledigen"]["pfad"], f"/api/aufgaben/{aid}/erledigen")
        self.assertTrue(self.c.post(f"/api/aufgaben/{aid}", json={"titel": "Steuer 2026"}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/aufgaben/{aid}/erledigen", json={}).json()["ok"])
        self.assertNotIn(f"auf:{aid}", {x["id"] for x in self.c.get("/api/todos").json()["todos"]})
        self.assertTrue(self.c.post(f"/api/aufgaben/{aid}/loeschen", json={}).json()["ok"])
        self.assertEqual(self.c.get("/api/aufgaben").json()["gruppen"]["erledigt"], [])


if __name__ == "__main__":
    unittest.main()
