"""OFC_MITGLIEDER MV0/MV1: Import-Vorschau (schreibt nichts, Konflikte), einmaliger Import (doppelte Nummern nach CEO-Wahl,
nie doppelt), Gold einheitlich, Vorstand als Haken, alle Felder, Abgleich Tabelle <-> LUNA. Fixtures ohne echte Daten."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import ofc_verzeichnis as vz
from orchestrator.core.ofc_mitglieder import auswerten
from orchestrator.core.ofc_store import OfcStore
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc_beitraege import GOLD, GOLD2, KOPF, _z


def _werte():
    a = _z("0007", "Anna", GOLD, beitrag="40,00 €")
    a[11], a[14], a[15], a[6], a[10] = "anna@example.org", "0170 1", "Weg 1, 20000 Hamburg", "Anna", "01.02.1990"
    b = _z("0008", "Bert", GOLD2)
    b[16] = "bert@example.org"                                            # nur zweite E-Mail-Spalte
    c = _z("0008", "Cara", "Standardmitgliedschaft (Kostenfrei)")          # doppelte Nummer
    d = _z("0009", "Vera", "Vorstand")
    e = _z("", "Neu", GOLD)                                               # Anfrage
    f = _z("0010", "Fred", "Fördermitgliedschaft (Beitrag bitte unten ins Kommentarfeld eintragen)", kommentar="60 Euro")
    return [KOPF, a, b, c, d, e, f]


class TestVerzeichnis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        self.daten = auswerten(_werte())

    def tearDown(self):
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts_und_zeigt_konflikte(self):
        v = vz.import_vorschau(self.daten, self.st.stand())
        self.assertEqual((v["mitglieder"], v["anfragen"]), (5, 1))
        self.assertEqual(v["mitgliedschaften"], {"Gold": 2, "Standard": 1, "unklar": 1, "Förder": 1})   # beide Gold-Schreibweisen
        self.assertEqual(v["vorstand"], 1)
        self.assertEqual(list(v["doppelte_nummern"]), ["0008"])
        self.assertEqual(v["naechste_nummer"], "0011")
        self.assertEqual(self.st.eintraege(), [])

    def test_import_mit_konfliktwahl_nie_doppelt(self):
        self.assertFalse(vz.import_anwenden(self.st, self.daten, {})["ok"])                  # Konflikt ungeloest
        self.assertEqual(self.st.eintraege(), [])
        zeile_cara = next(p["zeile"] for p in self.daten["mitglieder"] if p["vorname"] == "Cara")
        zeile_bert = next(p["zeile"] for p in self.daten["mitglieder"] if p["vorname"] == "Bert")
        r = vz.import_anwenden(self.st, self.daten, {"0008": zeile_cara})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["uebernommen"], 6)
        self.assertEqual(r["neue_nummern"], [{"zeile": zeile_bert, "alt": "0008", "neu": "0011"}])
        vzd = {p["vorname"]: p for p in self.st.stand()["verzeichnis"].values()}
        self.assertEqual((vzd["Cara"]["nummer"], vzd["Bert"]["nummer"]), ("0008", "0011"))
        self.assertEqual(vzd["Anna"]["email"], "anna@example.org")
        self.assertEqual((vzd["Anna"]["handy"], vzd["Anna"]["adresse"], vzd["Anna"]["geburtstag"]), ("0170 1", "Weg 1, 20000 Hamburg", "01.02.1990"))
        self.assertEqual(vzd["Bert"]["email"], "bert@example.org")                          # zweite Spalte als Ersatz
        self.assertEqual((vzd["Bert"]["mitgliedschaft"], vzd["Vera"]["vorstand"], vzd["Neu"]["status"]), ("gold", True, "anfrage"))
        n = len(self.st.eintraege())
        self.assertFalse(vz.import_anwenden(self.st, self.daten, {"0008": zeile_cara})["ok"])   # Gegenprobe: nie doppelt
        self.assertEqual(len(self.st.eintraege()), n)

    def test_abgleich(self):
        self.assertFalse(vz.abgleich(self.daten, self.st.stand())["importiert"])
        zeile_cara = next(p["zeile"] for p in self.daten["mitglieder"] if p["vorname"] == "Cara")
        vz.import_anwenden(self.st, self.daten, {"0008": zeile_cara})
        a = vz.abgleich(self.daten, self.st.stand())
        self.assertEqual(a["abweichungen"], 0, a)                                          # bewusst geloester Konflikt zaehlt nicht
        w = _werte()
        w[1][11] = "neu@example.org"                                                        # spaeter in der Tabelle geaendert
        a = vz.abgleich(auswerten(w), self.st.stand())
        self.assertEqual((a["abweichungen"], a["je_feld"]), (1, {"email": 1}))


class TestApi(ApiBasis):
    def test_nur_ceo(self):
        from unittest import mock
        with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
            self.assertEqual(self.c.get("/api/ofc/mitglieder/import/vorschau").status_code, 403)
            self.assertEqual(self.c.get("/api/ofc/mitglieder/abgleich").status_code, 403)
            self.assertEqual(self.c.post("/api/ofc/mitglieder/import", json={"bestaetigt": True}).status_code, 403)
        self.assertFalse(self.c.post("/api/ofc/mitglieder/import", json={}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
