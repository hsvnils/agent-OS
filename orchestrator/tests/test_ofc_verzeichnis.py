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


class TestMV2(unittest.TestCase):
    """MV2: anlegen, aendern (nur Geaendertes), Nummer eindeutig, E-Mail geprueft, aufnehmen, kuendigen (Archiv, nichts
    geloescht), wieder aufnehmen, Verlauf, Export, Gekuendigte bekommen keine Nachrichten."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        daten = auswerten(_werte())
        zeile_cara = next(p["zeile"] for p in daten["mitglieder"] if p["vorname"] == "Cara")
        vz.import_anwenden(self.st, daten, {"0008": zeile_cara})
        self.p = {p["vorname"]: p for p in self.st.stand()["verzeichnis"].values()}

    def tearDown(self):
        self.tmp.cleanup()

    def test_anlegen_aendern_pruefen(self):
        r = vz.speichern(self.st, "", {"vorname": "Lea", "nachname": "Neu", "email": "lea@example.org", "mitgliedschaft": "gold"})
        self.assertEqual((r["ok"], r["nummer"]), (True, "0012"))                       # naechste freie Nummer
        self.assertFalse(vz.speichern(self.st, "", {"vorname": "X", "nummer": "0007"})["ok"])          # Nummer vergeben
        self.assertFalse(vz.speichern(self.st, "", {"vorname": "X", "email": "kaputt"})["ok"])
        self.assertFalse(vz.speichern(self.st, "", {"nachname": ""})["ok"])
        self.assertFalse(vz.speichern(self.st, "", {"vorname": "X", "mitgliedschaft": "platin"})["ok"])
        pid = self.p["Anna"]["id"]
        r = vz.speichern(self.st, pid, {"vorname": "Anna", "handy": "0171 9", "vorstand": True})
        self.assertEqual(r["geaendert"], ["handy", "vorstand"])                        # nur Geaendertes
        self.assertEqual(vz.speichern(self.st, pid, {"handy": "0171 9"})["geaendert"], [])
        self.assertIn(["handy", "vorstand"], [v["felder"] for v in vz.verlauf(self.st, pid)])

    def test_aufnehmen_kuendigen_wieder(self):
        neu = self.p["Neu"]["id"]
        r = vz.aufnehmen(self.st, neu, mitgliedschaft="standard")
        self.assertEqual(r["nummer"], "0012")
        self.assertEqual(self.st.stand()["verzeichnis"][neu]["status"], "mitglied")
        self.assertFalse(vz.aufnehmen(self.st, neu)["ok"])
        anna = self.p["Anna"]["id"]
        n_vorher = len(self.st.stand()["verzeichnis"])
        self.assertTrue(vz.kuendigen(self.st, anna, datum="2026-11-30", notiz="per Mail")["ok"])
        a = self.st.stand()["verzeichnis"][anna]
        self.assertEqual((a["status"], a["gekuendigt_am"]), ("archiv", "2026-11-30"))
        self.assertEqual(len(self.st.stand()["verzeichnis"]), n_vorher)                 # nichts geloescht
        self.assertEqual(vz.gekuendigte_nummern(self.st.stand()), {"0007"})
        self.assertEqual(vz.uebersicht(self.st.stand())["archiv"], 1)
        self.assertTrue(vz.wieder_aufnehmen(self.st, anna)["ok"])
        self.assertEqual(self.st.stand()["verzeichnis"][anna]["status"], "mitglied")
        self.assertEqual(vz.gekuendigte_nummern(self.st.stand()), set())

    def test_export(self):
        csv = vz.export_csv(self.st.stand(), "mitglied").decode("utf-8")
        self.assertIn("Nummer;Status;Anrede", csv)
        self.assertIn("anna@example.org", csv)
        self.assertNotIn("Neu;", csv.split("\n", 1)[1].split(";Neu;")[0] if ";Neu;" in csv else "")   # Anfrage nicht unter Mitglieder


class TestKeineNachrichtAnGekuendigte(unittest.TestCase):
    def test_zahlungsbitte_und_tickets_gesperrt(self):
        from unittest import mock
        from orchestrator.core import ofc, ofc_versand
        from orchestrator.core.ofc_store import bezahlt_markieren, import_anwenden, mitglied_setzen
        from orchestrator.core.ofc_wallet import wallet_von_hand
        from orchestrator.tests.test_ofc import _pdf_als_text
        from orchestrator.tests.test_ofc_store import _saison
        from orchestrator.tests.test_ofc_versand import MITGLIEDER, FakePf
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text):
            saison = _saison(Path(d))
            st = OfcStore(Path(d) / "fanclub")
            import_anwenden(st, saison)
            mitglied_setzen(st, "262236181415-1", "1004")
            st.erfassen("ofc_verzeichnis", {"id": "P-x", "nummer": "1004", "vorname": "Anna", "status": "mitglied"})
            self.assertEqual(ofc_versand.plan(st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["status"], "bereit")
            vz.kuendigen(st, "P-x")
            g = ofc_versand.plan(st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]
            self.assertEqual(g["status"], "gesperrt")                                   # Gegenprobe zum Zustand davor
            pf = FakePf()
            self.assertFalse(ofc_versand.senden(st, pf, "HSV vs FCB", "1004", MITGLIEDER)["ok"])
            with mock.patch.object(ofc, "nas_ordner", return_value=saison):
                bezahlt_markieren(st, ["262236181415-1"], True)
                wallet_von_hand(st, "262236181415-1", "https://www.eventimsports.de/wallet/x/1")
                self.assertEqual(ofc_versand.tickets_plan(st.stand(), "HSV vs FCB", MITGLIEDER)["gruppen"][0]["status"], "gesperrt")
                self.assertFalse(ofc_versand.tickets_senden(st, pf, "HSV vs FCB", "1004", MITGLIEDER, erneut=True)["ok"])
            self.assertEqual(pf.gesendet, [])


class TestApiMV2(ApiBasis):
    def test_endpunkte(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            st = OfcStore(Path(d) / "fanclub")
            with mock.patch.object(self.w, "_ofc_store", return_value=st):
                self.assertFalse(self.c.post("/api/ofc/verzeichnis", json={"felder": {"vorname": "A"}}).json()["ok"])   # ohne Bestaetigung
                r = self.c.post("/api/ofc/verzeichnis", json={"bestaetigt": True, "felder": {"vorname": "A", "nachname": "B"}}).json()
                self.assertTrue(r["ok"], r)
                self.assertEqual(self.c.get("/api/ofc/verzeichnis").json()["mitglieder"], 1)
                self.assertTrue(self.c.post(f"/api/ofc/verzeichnis/{r['id']}/kuendigen", json={"bestaetigt": True}).json()["ok"])
                self.assertEqual(self.c.get(f"/api/ofc/verzeichnis/{r['id']}").json()["person"]["status"], "archiv")
                self.assertIn("text/csv", self.c.get("/api/ofc/verzeichnis/export.csv?ansicht=archiv").headers["content-type"])
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    self.assertEqual(self.c.get("/api/ofc/verzeichnis").status_code, 403)
                    self.assertEqual(self.c.get("/api/ofc/verzeichnis/export.csv").status_code, 403)
                    self.assertEqual(self.c.post("/api/ofc/verzeichnis", json={"bestaetigt": True}).status_code, 403)
                    self.assertEqual(self.c.post(f"/api/ofc/verzeichnis/{r['id']}/wieder", json={"bestaetigt": True}).status_code, 403)


class TestMV3(unittest.TestCase):
    """MV3: LUNA als Quelle in derselben Form wie die Tabelle; Beitraege ohne Soll nach dem Kuendigungsjahr; Rueckweg google."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        daten = auswerten(_werte())
        zeile_cara = next(p["zeile"] for p in daten["mitglieder"] if p["vorname"] == "Cara")
        vz.import_anwenden(self.st, daten, {"0008": zeile_cara})
        self.p = {p["vorname"]: p for p in self.st.stand()["verzeichnis"].values()}

    def tearDown(self):
        self.tmp.cleanup()

    def test_quelle(self):
        self.assertEqual(vz.quelle(self.st.stand(), env={}), "luna")
        self.assertEqual(vz.quelle(self.st.stand(), env={"OFC_MITGLIEDER_QUELLE": "google"}), "google")
        self.assertEqual(vz.quelle({"verzeichnis": {}}, env={}), "google")

    def test_gleiche_form_und_aenderungen_wirken(self):
        vz.speichern(self.st, self.p["Anna"]["id"], {"email": "anna.neu@example.org"})
        d = vz.als_mitgliederliste(self.st.stand())
        m = {p["vorname"]: p for p in d["mitglieder"]}
        self.assertEqual(m["Anna"]["email"], "anna.neu@example.org")                  # Aenderung in LUNA zaehlt
        self.assertEqual((m["Anna"]["name"], m["Anna"]["nummer"], m["Bert"]["nummer"]), ("Anna Muster", "0007", "0011"))
        self.assertEqual(m["Bert"]["mitgliedschaft"], "Gold")
        self.assertEqual([p["vorname"] for p in d["anfragen"]], ["Neu"])
        for k in ("zeile", "status", "vorname", "nachname", "seit", "beitrag", "naechste_zahlung", "kommentar", "felder", "hinweise"):
            self.assertIn(k, m["Anna"])

    def test_beitraege_ohne_gekuendigte_im_folgejahr(self):
        from orchestrator.core.ofc_beitraege import beitraege
        vz.kuendigen(self.st, self.p["Anna"]["id"], datum="2027-03-01")
        d = vz.als_mitgliederliste(self.st.stand())
        nr27 = {x["nummer"] for x in beitraege(d, 2027)["mitglieder"]}
        nr28 = {x["nummer"] for x in beitraege(d, 2028)["mitglieder"]}
        self.assertIn("0007", nr27)                                                       # im Kuendigungsjahr noch Soll
        self.assertNotIn("0007", nr28)                                                    # danach nicht mehr
        self.assertIn("0011", nr28)

    def test_foerderbetrag_als_beitrag(self):
        from orchestrator.core.ofc_beitraege import soll
        vz.speichern(self.st, self.p["Fred"]["id"], {"foerder_betrag": "60,00 €", "seit": "01.01.2020"})
        fred = next(p for p in vz.als_mitgliederliste(self.st.stand())["mitglieder"] if p["vorname"] == "Fred")
        self.assertEqual(soll(fred, 2027)["soll_cent"], 6000)


class TestApiMV3(ApiBasis):
    def test_datenquelle_luna(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            st = OfcStore(Path(d) / "fanclub")
            st.erfassen("ofc_verzeichnis", {"id": "P-1", "nummer": "0042", "vorname": "Lina", "nachname": "Luna", "email": "l@example.org",
                                            "mitgliedschaft": "gold", "status": "mitglied", "seit": "01.01.2020"})
            with mock.patch.object(self.w, "_ofc_store", return_value=st), \
                    mock.patch.object(self.w, "_ofc_tabelle_daten", side_effect=AssertionError("Tabelle darf nicht gelesen werden")):
                d1 = self.w._ofc_mitglieder_daten()
                self.assertEqual((d1["quelle"], d1["mitglieder"][0]["nummer"]), ("luna", "0042"))
                self.assertEqual(self.c.get("/api/ofc/mitglieder").json()["blatt"], "LUNA-Verzeichnis")
                self.assertIn({"name": "Lina Luna", "nummer": "0042", "vorname": "Lina", "nachname": "Luna", "email": "l@example.org"},
                              self.c.get("/api/ofc/namen").json()["personen"])
            with mock.patch.object(self.w, "_ofc_store", return_value=st), mock.patch.dict("os.environ", {"OFC_MITGLIEDER_QUELLE": "google"}), \
                    mock.patch.object(self.w, "_ofc_tabelle_daten", return_value={"ok": True, "quelle": "google"}):
                self.assertEqual(self.w._ofc_mitglieder_daten()["quelle"], "google")       # Rueckweg
