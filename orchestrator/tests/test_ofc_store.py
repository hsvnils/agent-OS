"""OFC_ROADMAP O1: Fanclub-Speicher und Import -- Vorschau schreibt nichts, Import ist wiederholbar (keine Dubletten),
Namen aus Dateinamen nur beim ersten Erfassen, Verschieben nach „Abgeschlossen“ = gleiches Spiel, Hinweise (Rechnung fehlt,
Bestellung ohne Rechnung, Datei fehlt, ohne Namen), Dateien nur die zugeordneten (kein freier Pfad), nur CEO."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core.ofc_store import OfcStore, datei_pfad, import_anwenden, import_plan, spiel_detail, uebersicht
from orchestrator.core.team_auth import erlaubte_apps
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import HEIM, _pdf_als_text


def _saison(d: Path) -> Path:
    s = d / "Tickets 26-27"
    h = s / "HSV vs FCB"
    h.mkdir(parents=True)
    (h / "Rechnung.pdf").write_text(HEIM, encoding="utf-8")
    (h / "262236181415-1-Anna.pdf").write_text("Ticketnummer: 262236181415-1", encoding="utf-8")
    (h / "262236189999-1-Ben.pdf").write_text("Ticketnummer: 262236189999-1", encoding="utf-8")   # Bestellung ohne Rechnung
    w = s / "SVW vs HSV"
    w.mkdir()
    (w / "162236525621-7.pdf").write_text("Ticket Nummer: 162236525621-7", encoding="utf-8")
    return s


class TestImport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = _saison(self.d)
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_1_vorschau_schreibt_nichts_import_wiederholbar(self):
        v = import_plan(self.st, self.s)
        self.assertEqual((sorted(v["spiele_neu"]), v["tickets_neu"], v["namen_neu"]), (["HSV vs FCB", "SVW vs HSV"], 4, 2))
        self.assertFalse(self.st.pfad.exists())                                          # Dry-Run schreibt nichts
        import_anwenden(self.st, self.s, von="test")
        n = len(self.st.eintraege())
        v2 = import_plan(self.st, self.s)
        self.assertEqual((v2["spiele_neu"], v2["spiele_geaendert"], v2["tickets_neu"], v2["tickets_geaendert"]), ([], [], 0, 0))
        import_anwenden(self.st, self.s, von="test")
        self.assertEqual(len(self.st.eintraege()), n + 1)                                  # nur der Import-Vermerk
        st = self.st.stand()
        self.assertEqual(len(st["tickets"]), 4)
        t = st["tickets"]["262236181415-2"]                                              # in der Rechnung, Datei fehlt
        self.assertEqual((t["datei"], t["block"], t["preis_cent"]), ("", "28C", 3500))
        self.assertTrue(st["tickets"]["262236189999-1"]["ohne_rechnung"])

    def test_2_name_nur_beim_ersten_mal_und_verschieben(self):
        import_anwenden(self.st, self.s)
        self.st.erfassen("ofc_ticket", {"ticketnr": "262236181415-1", "name": "Anna Neu"})   # spaeter in LUNA geaendert (O2)
        h = self.s / "HSV vs FCB"
        (h / "262236181415-1-Anna.pdf").rename(h / "262236181415-1-Andere.pdf")              # Datei von Hand umbenannt
        ab = self.s / "Abgeschlossen"
        ab.mkdir()
        (self.s / "SVW vs HSV").rename(ab / "SVW vs HSV")                                     # Spiel verschoben
        v = import_plan(self.st, self.s)
        self.assertEqual((v["spiele_neu"], v["spiele_geaendert"]), ([], ["SVW vs HSV"]))
        import_anwenden(self.st, self.s)
        st = self.st.stand()
        self.assertEqual((st["tickets"]["262236181415-1"]["name"], st["tickets"]["262236181415-1"]["datei"]),
                         ("Anna Neu", "262236181415-1-Andere.pdf"))                         # Name bleibt, Datei folgt
        self.assertEqual((st["spiele"]["SVW vs HSV"]["abgeschlossen"], st["spiele"]["SVW vs HSV"]["pfad"]),
                         (True, "Abgeschlossen/SVW vs HSV"))

    def test_3_uebersicht_hinweise_status(self):
        import_anwenden(self.st, self.s)
        u = uebersicht(self.st, heute=date(2026, 11, 24))
        sp = {x["id"]: x for x in u["spiele"]}
        h = sp["HSV vs FCB"]
        self.assertEqual((h["status"], h["karten"], h["mit_name"], h["heimspiel"], h["summe_cent"]), ("offen", 3, 2, True, 7000))
        self.assertIn("1 weitere Bestellung(en) ohne Rechnung", h["hinweise"])
        self.assertIn("1 Ticket-Datei(en) fehlen", h["hinweise"])
        self.assertIn("Rechnung fehlt im Ordner", sp["SVW vs HSV"]["hinweise"])
        self.assertEqual(sp["SVW vs HSV"]["spiel"], "SVW vs HSV")                          # Titel = Ordner ohne Rechnung
        self.assertEqual(uebersicht(self.st, heute=date(2026, 12, 1))["spiele"][0]["status"], "vorbei")

    def test_4_dateien_nur_zugeordnete(self):
        import_anwenden(self.st, self.s)
        self.assertTrue(datei_pfad(self.st, "HSV vs FCB", "262236181415-1-Anna.pdf", self.s).is_file())
        self.assertTrue(datei_pfad(self.st, "HSV vs FCB", "Rechnung.pdf", self.s).is_file())
        for boes in ("../SVW vs HSV/162236525621-7.pdf", "ATGB.pdf", "", "/etc/passwd"):
            self.assertIsNone(datei_pfad(self.st, "HSV vs FCB", boes, self.s), boes)
        self.assertIsNone(datei_pfad(self.st, "gibtsnicht", "Rechnung.pdf", self.s))
        self.assertEqual(len(spiel_detail(self.st, "HSV vs FCB")["tickets"]), 3)


class TestApi(ApiBasis):
    def test_5_endpunkte_nur_ceo(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            _saison(Path(d))
            v = self.c.get("/api/ofc/import/vorschau").json()
            self.assertEqual((v["ok"], v["tickets_neu"]), (True, 4))
            self.assertNotIn("ereignisse", v)
            self.assertFalse(self.c.post("/api/ofc/import", json={}).json()["ok"])            # ohne Bestaetigung
            self.assertFalse((Path(d) / "fanclub" / "log.jsonl").exists())
            r = self.c.post("/api/ofc/import", json={"bestaetigt": True}).json()
            self.assertEqual(len(r["spiele_neu"]), 2)
            u = self.c.get("/api/ofc/uebersicht").json()
            self.assertEqual((u["summe"]["spiele"], u["saison_ordner"]), (2, "Tickets 26-27"))
            self.assertEqual(self.c.get("/api/ofc/spiel/HSV vs FCB").json()["spiel"]["gegner"], "FC Bayern Muenchen")
            r = self.c.get("/api/ofc/spiel/HSV vs FCB/datei", params={"name": "Rechnung.pdf"})
            self.assertEqual((r.status_code, r.headers["content-type"]), (200, "application/pdf"))
            self.assertEqual(self.c.get("/api/ofc/spiel/HSV vs FCB/datei", params={"name": "../x.pdf"}).status_code, 404)
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                for url in ("/api/ofc/uebersicht", "/api/ofc/spiel/HSV vs FCB", "/api/ofc/import/vorschau"):
                    self.assertEqual(self.c.get(url).status_code, 403, url)
                self.assertEqual(self.c.post("/api/ofc/import", json={"bestaetigt": True}).status_code, 403)
        self.assertIn("ofc", erlaubte_apps({"role": "owner"}))
        self.assertNotIn("ofc", erlaubte_apps({"role": "admin", "allowed_modules": ["finanzen", "administration"]}))
