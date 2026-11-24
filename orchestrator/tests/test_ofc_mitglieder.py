"""OFC_ROADMAP OM: Mitgliederliste -- Spalten erkennen, Mitglied (mit Nummer) vs. Anfrage, Dubletten, alle Spalten,
nur Lese-Aufrufe (Gegenprobe: kein Schreibaufruf), Cache ohne Platte, Endpunkt nur CEO. Fixtures ohne echte Daten."""
import os
import unittest
from unittest import mock

from orchestrator.core import ofc_mitglieder as om
from orchestrator.tests.test_angebote import ApiBasis

KOPF = ["Zeitstempel", "HSVInside-Mitglied", "Deine HSV-Mitgliedsnummer", "Mitglied seit:", "Beitrag", "Nächste Zahlung",
        "Wie sollen wir dich ansprechen?", "Wie lautet dein Vorname?", "Wie lautet dein Nachname?",
        "Welche Mitgliedschaft möchtest du anfragen?", "Wann hast du Geburtstag?", "Wie lautet deine E-Mailadresse?",
        "Bist du Mitglied beim HSV?", "Bist du bereits Mitglied eines anderen Fanclubs?", "Wie lautet deine Handynummer?",
        "Straße + Hausnummer, PLZ, Ort", "E-Mail-Adresse", "Teile uns hier gern noch etwas mit."]


def _zeile(ts, nr, vor, nach, art="Standardmitgliedschaft (Kostenfrei)", mail="test@example.org"):
    z = [""] * len(KOPF)
    z[0], z[1], z[3], z[7], z[8], z[9], z[11], z[14] = ts, nr, "01.01.2025" if nr else "", vor, nach, art, mail, "0170 0000000"
    return z


WERTE = [KOPF,
         _zeile("15.01.2024 10:00:00", "0002", "Erika", "Muster"),
         _zeile("16.01.2024 10:00:00", "0001", "Max", "Beispiel", "Goldmitgliedschaft (jährliche Zahlung)"),
         _zeile("01.03.2026 09:00:00", "", "Neu", "Anfrage"),
         _zeile("02.03.2026 09:00:00", "", "Max", "beispiel"),          # Name mehrfach (Gross/Klein egal)
         _zeile("03.03.2026 09:00:00", "0002", "Zweite", "Person")[:12],  # Nummer doppelt, kurze Zeile
         [""] * 5]                                                       # Leerzeile wird uebersprungen


class _Rec:
    """Faelscht die Google-Clients und merkt sich jeden Aufruf (Gegenprobe: nur list/get)."""

    def __init__(self, werte, files=None):
        self.werte, self.files_ = werte, files if files is not None else [{"id": "T1", "name": om.TABELLE_NAME}]
        self.aufrufe = []

    def verfuegbar(self):
        return True

    def service(self, api, version):
        rec = self

        class _Exec:
            def __init__(self, r):
                self.r = r

            def execute(self):
                return self.r

        class _Files:
            def list(self, **kw):
                rec.aufrufe.append(("drive.files.list", kw)); return _Exec({"files": rec.files_})

        class _Values:
            def get(self, **kw):
                rec.aufrufe.append(("sheets.values.get", kw)); return _Exec({"values": rec.werte})

        class _Sheets:
            def values(self):
                return _Values()

        class _Svc:
            def files(self):
                return _Files()

            def spreadsheets(self):
                return _Sheets()
        return _Svc()


class TestAuswerten(unittest.TestCase):
    def test_1_spalten_mitglied_anfrage_alle_felder(self):
        d = om.auswerten(WERTE)
        self.assertTrue(d["ok"])
        self.assertEqual(d["summe"], {"mitglieder": 3, "anfragen": 2, "zeilen": 5})
        self.assertEqual([p["nummer"] for p in d["mitglieder"]], ["0001", "0002", "0002"])   # nach Nummer
        self.assertEqual([p["name"] for p in d["anfragen"]], ["Max beispiel", "Neu Anfrage"])   # neueste zuerst
        p = d["mitglieder"][0]
        self.assertEqual((p["name"], p["mitgliedschaft"], p["email"], p["seit"], p["zeile"]),
                         ("Max Beispiel", "Goldmitgliedschaft (jährliche Zahlung)", "test@example.org", "01.01.2025", 3))
        self.assertIn(["Wie lautet deine Handynummer?", "0170 0000000"], p["felder"])        # alle Spalten (CEO)
        self.assertNotIn("Deine HSV-Mitgliedsnummer", [k for k, _ in p["felder"]])           # leere Felder weggelassen
        self.assertEqual(d["anfragen"][1]["eingang"], "2026-03-01")

    def test_2_dubletten(self):
        d = om.auswerten(WERTE)
        nr2 = [p for p in d["mitglieder"] if p["nummer"] == "0002"]
        self.assertTrue(all("Nummer 0002 mehrfach" in p["hinweise"] for p in nr2))
        self.assertIn("Name mehrfach", d["mitglieder"][0]["hinweise"])
        self.assertEqual(d["hinweise"], ["1 Mitgliedsnummer(n) mehrfach vergeben", "1 Name(n) mehrfach eingetragen"])
        self.assertEqual(om.namen_fuer_vorschlag(d)[0], {"name": "Max Beispiel", "nummer": "0001"})

    def test_3_spalten_fehlen_oder_leer(self):
        self.assertFalse(om.auswerten([])["ok"])
        r = om.auswerten([["Zeitstempel", "Name"], ["x", "y"]])
        self.assertFalse(r["ok"]); self.assertIn("nummer", r["hinweis"])
        sp = om.spalten_erkennen(KOPF)                                    # E-Mail-Spalten nicht verwechselt
        self.assertEqual((sp["email"], sp["email_absender"], sp["nummer"], sp["hsv_nr"]), (11, 16, 1, 2))


class TestLesen(unittest.TestCase):
    def setUp(self):
        om._CACHE.clear()

    def test_4_nur_lesend_cache_ohne_platte(self):
        a = _Rec(WERTE)
        with mock.patch.dict(os.environ, {"OFC_MITGLIEDER_TABELLE": "", "OFC_MITGLIEDER_BLATT": ""}):
            d = om.lesen(a, jetzt=1000.0)
            self.assertEqual((d["ok"], d["blatt"], d["summe"]["mitglieder"]), (True, "Formularantworten 1", 3))
            self.assertEqual([x[0] for x in a.aufrufe], ["drive.files.list", "sheets.values.get"])   # nur Lese-Aufrufe
            self.assertEqual(a.aufrufe[1][1], {"spreadsheetId": "T1", "range": "'Formularantworten 1'!A1:AZ"})
            om.lesen(a, jetzt=1100.0)
            self.assertEqual(len(a.aufrufe), 2)                                                     # aus dem Speicher
            om.lesen(a, neu=True, jetzt=1100.0)
            self.assertEqual(len(a.aufrufe), 4)
        with mock.patch.dict(os.environ, {"OFC_MITGLIEDER_TABELLE": "FEST", "OFC_MITGLIEDER_BLATT": "Mitglieder"}):
            b = _Rec(WERTE)
            om.lesen(b, neu=True)
            self.assertEqual(b.aufrufe, [("sheets.values.get", {"spreadsheetId": "FEST", "range": "'Mitglieder'!A1:AZ"})])
        c = _Rec(WERTE, files=[])
        with mock.patch.dict(os.environ, {"OFC_MITGLIEDER_TABELLE": ""}):
            self.assertIn("nicht gefunden", om.lesen(c, neu=True)["hinweis"])
        src = open(om.__file__, encoding="utf-8").read()
        for verboten in ("values().update", "values().append", "batchUpdate", "files().create", "open(", "write_text"):
            self.assertNotIn(verboten, src, verboten)                                               # Gegenprobe


class TestApi(ApiBasis):
    def test_5_endpunkt_nur_ceo(self):
        om._CACHE.clear()
        g = mock.Mock(); g.auth = _Rec(WERTE)
        with mock.patch.object(self.w, "_google", return_value=g), mock.patch.dict(os.environ, {"OFC_MITGLIEDER_TABELLE": ""}):
            d = self.c.get("/api/ofc/mitglieder").json()
            self.assertEqual((d["ok"], d["summe"]["anfragen"]), (True, 2))
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/mitglieder").status_code, 403)
        g.auth = mock.Mock(verfuegbar=mock.Mock(side_effect=RuntimeError("geheim-123")))
        with mock.patch.object(self.w, "_google", return_value=g):
            r = self.c.get("/api/ofc/mitglieder", params={"neu": 1}).json()
            self.assertEqual(r["ok"], False); self.assertNotIn("geheim", r["hinweis"])
