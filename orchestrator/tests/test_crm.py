import tempfile
import unittest
from pathlib import Path

from orchestrator.core.crm import CrmStore


class TestCrmStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.s = CrmStore(Path(self.dir.name) / "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_nachricht_erstellt_firma_neu(self):
        mid = self.s.nachricht_erfassen("Acme GmbH", "Wir wollen kooperieren", quelle="instagram",
                                        extern_id="ig1")
        self.assertTrue(mid.startswith("M-"))
        firmen = self.s.firmen()
        self.assertEqual(len(firmen), 1)
        self.assertEqual(firmen[0]["firma"], "Acme GmbH")
        self.assertEqual(firmen[0]["status"], "neu")       # neue Firma automatisch 'neu'
        self.assertEqual(firmen[0]["nachrichten"], 1)
        self.assertEqual(firmen[0]["quelle"], "instagram")

    def test_dedup_extern_id(self):
        self.s.nachricht_erfassen("Acme", "Hallo", extern_id="x1")
        zweite = self.s.nachricht_erfassen("Acme", "Hallo nochmal", extern_id="x1")
        self.assertEqual(zweite, "")                        # Duplikat (Webhook-Retry) -> nicht erfasst
        self.assertEqual(len(self.s.konversation("Acme")), 1)

    def test_status_pipeline_case_insensitiv(self):
        self.s.nachricht_erfassen("Acme", "Anfrage")
        self.s.status_setzen("acme", "angebot")             # anderer Case, gleiche Firma
        self.assertEqual(self.s.firmen()[0]["status"], "angebot")
        with self.assertRaises(ValueError):
            self.s.status_setzen("Acme", "quatsch")

    def test_todos_offen_und_erledigt(self):
        tid = self.s.todo_hinzufuegen("Acme", "nachfassen", begruendung="3 Tage offen")
        self.assertEqual(len(self.s.todos()), 1)
        self.s.todo_erledigen(tid)
        self.assertEqual(len(self.s.todos(nur_offen=True)), 0)
        self.assertEqual(len(self.s.todos(nur_offen=False)), 1)

    def test_uebersicht_pipeline(self):
        self.s.nachricht_erfassen("A", "x")
        self.s.nachricht_erfassen("B", "y")
        self.s.status_setzen("A", "angebot")
        u = self.s.uebersicht()
        self.assertEqual(u["firmen_gesamt"], 2)
        self.assertEqual(u["pipeline"]["angebot"], 1)
        self.assertEqual(u["pipeline"]["neu"], 1)

    def test_klassifikation_regelbasiert(self):
        from orchestrator.core.crm import klassifiziere
        self.assertEqual(klassifiziere("Hallo, wir haben Interesse an einer Kooperation!"), "kooperation")
        self.assertEqual(klassifiziere("Sponsoring-Anfrage fuer euren Kanal"), "kooperation")
        self.assertEqual(klassifiziere("Wie komme ich ins Stadion?"), "unklar")

    def test_verarbeite_eingang_kooperation_legt_todo(self):
        r = self.s.verarbeite_eingang("BrandX", "Sponsoring-Anfrage fuer eure Reichweite",
                                      quelle="instagram", extern_id="ig9")
        self.assertEqual(r["kategorie"], "kooperation")
        self.assertTrue(r["mid"] and r["todo_id"])       # neue Kooperation -> automatisch To-do
        self.assertEqual(len(self.s.todos()), 1)
        r2 = self.s.verarbeite_eingang("BrandX", "noch eine Kooperation", extern_id="ig10")
        self.assertEqual(r2["todo_id"], "")              # zweite Nachricht -> kein zweites To-do
        self.assertEqual(len(self.s.todos()), 1)

    def test_verarbeite_eingang_privat_kein_todo(self):
        r = self.s.verarbeite_eingang("FanY", "Super Spiel gestern!", extern_id="ig11")
        self.assertEqual(r["kategorie"], "unklar")
        self.assertEqual(r["todo_id"], "")
        self.assertEqual(len(self.s.todos()), 0)

    def test_write_through_projektion_nach_supabase(self):
        from orchestrator.governance.supabase import MockSupabaseClient
        from orchestrator.core.crm_projection import SupabaseCrmProjection
        mock = MockSupabaseClient()
        s = CrmStore(Path(self.dir.name) / "p.jsonl", projektor=SupabaseCrmProjection(mock))
        s.verarbeite_eingang("Acme GmbH", "Sponsoring-Kooperation gewuenscht", quelle="instagram",
                             extern_id="ig1")
        tabellen = [u[0] for u in mock.upserts]
        self.assertIn("crm_companies", tabellen)   # Firma projiziert
        self.assertIn("crm_messages", tabellen)    # Nachricht projiziert
        self.assertIn("crm_todos", tabellen)       # neue Kooperation -> To-do projiziert
        comp = next(u[1][0] for u in mock.upserts if u[0] == "crm_companies")
        self.assertEqual(comp["ref"], "acme gmbh")
        self.assertEqual(comp["status"], "neu")
        self.assertEqual(comp["updated_by"], "luna")
        msg = next(u[1][0] for u in mock.upserts if u[0] == "crm_messages")
        self.assertEqual(msg["extern_id"], "ig1")
        self.assertEqual(msg["kategorie"], "kooperation")

    def test_ohne_projektor_kein_fehler(self):
        # Store ohne Projektor arbeitet rein lokal (kein Crash).
        self.assertTrue(self.s.verarbeite_eingang("X", "hallo", extern_id="a")["mid"])

    def test_leak_schutz_beim_schreiben(self):
        s = CrmStore(Path(self.dir.name) / "l2.jsonl", secrets=["GEHEIMTOKEN123"])
        s.nachricht_erfassen("Acme", "mein token ist GEHEIMTOKEN123", extern_id="a")
        roh = (Path(self.dir.name) / "l2.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("GEHEIMTOKEN123", roh)


if __name__ == "__main__":
    unittest.main()
