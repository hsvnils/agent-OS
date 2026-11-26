"""OFC_KASSE_ROADMAP KA3-KA5: Kassenbuch (Buchungen aus Eingaengen, eigenen Zahlungen, Handbuchungen), Kassenstand ab
Anfangsbestand, Storno statt Loeschen, Kategorie per Klick, Beleg nur neu, „Spaeter bezahlen“ vorgemerkt, nur CEO.
Fixtures ohne echte Daten."""
import base64
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core import ofc_eingang as oe
from orchestrator.core import ofc_kasse as ok
from orchestrator.core.ofc_store import OfcStore, import_anwenden
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import _pdf_als_text
from orchestrator.tests.test_ofc_eingang import _erhalten, _ordner, _pp


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = Path(self.tmp.name) / "Tickets 26-27"
        _ordner(s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, s)
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00"),
                                      _erhalten("Fremde Person", "12,00", tc="2FF22222FF2222222", mid="<f@p>")])
        bank = _pp("Sie haben eine Rückzahlung gesendet", "Sie haben eine Rückzahlung an Hamburger Sparkasse AG ••1234 gesendet\n"
                   "Betrag 20,00\xa0€\xa0EUR\nTransaktionscode\n8BB88888BB8888888\n", "<b@p>")
        oe.eingang_anwenden(self.st, [bank])
        for z in ({"id": "z-1", "art": "gesendet", "betrag_cent": 7000, "datum": "2026-10-05", "zuordnung": "auto", "spiel": "HSV vs FCB",
                   "haendler": "CTS EVENTIM"},
                  {"id": "z-2", "art": "spaeter", "betrag_cent": 3000, "datum": "2026-10-01", "zuordnung": "auto", "spiel": "HSV vs FCB"},
                  {"id": "z-3", "art": "erstattung", "betrag_cent": 1000, "datum": "2026-10-09", "zuordnung": "auto"}):
            self.st.erfassen("ofc_zahlung", z)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()


class TestKasse(_Basis):
    def test_1_buchungen_aus_quellen(self):
        b = {x["id"]: x for x in ok.buchungen(self.st.stand(), heute=date(2026, 10, 20))}
        self.assertEqual((b["eingang:e-1EE11111EE1111111"]["betrag_cent"], b["eingang:e-1EE11111EE1111111"]["kategorie"]), (3500, "tickets"))
        self.assertEqual(b["eingang:e-2FF22222FF2222222"]["kategorie"], "offen")
        self.assertEqual((b["eingang:e-8BB88888BB8888888"]["betrag_cent"], b["eingang:e-8BB88888BB8888888"]["kategorie"]), (-2000, "auszahlung"))
        self.assertEqual((b["zahlung:z-1"]["betrag_cent"], b["zahlung:z-1"]["kategorie"]), (-7000, "tickets"))
        self.assertEqual((b["zahlung:z-2"]["status"], b["zahlung:z-2"]["datum"]), ("vorgemerkt", "2026-10-31"))   # faellig +30
        self.assertEqual(b["zahlung:z-3"]["betrag_cent"], 1000)
        self.assertEqual(ok.buchungen(self.st.stand(), heute=date(2026, 11, 20))[0]["status"] in ("gebucht", "vorgemerkt"), True)
        x = {y["id"]: y for y in ok.buchungen(self.st.stand(), heute=date(2026, 11, 20))}
        self.assertEqual(x["zahlung:z-2"]["status"], "gebucht")                                  # >5 Tage nach Faelligkeit

    def test_2_kassenstand_anfangsbestand_storno(self):
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertIsNone(k["kassenstand_cent"])
        self.assertEqual((k["einnahmen_cent"], k["ausgaben_cent"], k["vorgemerkt_cent"]), (5700, -9000, -3000))
        ok.anfangsbestand_setzen(self.st, "2026-10-06", 10000)
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertEqual(k["kassenstand_cent"], 10000 + 3500 + 1200 - 2000 + 1000)          # ab 06.10.: Eingaenge 07.10., Erstattung 09.10.
        r = ok.buchung_anlegen(self.st, datum="2026-10-10", betrag_cent=-349, kategorie="gebuehren", text="PayPal-Gebühr")
        self.assertTrue(r["ok"])
        self.assertEqual(ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))["kassenstand_cent"], 13700 - 349)
        ok.storno(self.st, r["id"])
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        self.assertEqual(k["kassenstand_cent"], 13700)
        self.assertEqual([b["status"] for b in k["buchungen"] if b["id"] == "kasse:" + r["id"]], ["storniert"])  # bleibt sichtbar
        ok.storno(self.st, r["id"], zurueck=True)
        self.assertEqual(ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))["kassenstand_cent"], 13700 - 349)
        self.assertFalse(ok.storno(self.st, "eingang:x")["ok"])
        ok.anfangsbestand_setzen(self.st, "2026-10-01", 0)                                       # Historie, der letzte gilt
        self.assertEqual(len(self.st.stand()["kasse_start"]), 2)

    def test_3_eingaben_pruefen_kategorie_beleg(self):
        for kw in ({"datum": "x", "betrag_cent": 1, "kategorie": "gebuehren", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 0, "kategorie": "gebuehren", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 1, "kategorie": "offen", "text": "a"},
                   {"datum": "2026-10-01", "betrag_cent": 1, "kategorie": "gebuehren", "text": " "}):
            self.assertFalse(ok.buchung_anlegen(self.st, **kw)["ok"], kw)
        self.assertFalse(ok.buchung_anlegen(self.st, datum="2026-10-01", betrag_cent=-100, kategorie="auslagen", text="x",
                                            beleg=b"MZ", beleg_name="a.exe")["ok"])
        r = ok.buchung_anlegen(self.st, datum="2026-10-01", betrag_cent=-100, kategorie="auslagen", text="Kleber", beleg=b"%PDF-1.4", beleg_name="q.pdf")
        p = ok.beleg_pfad(self.st, r["id"])
        self.assertTrue(p and p.read_bytes().startswith(b"%PDF"))
        self.assertIsNone(ok.beleg_pfad(self.st, "k-gibtsnicht"))
        self.assertTrue(ok.kategorie_setzen(self.st, "eingang:e-2FF22222FF2222222", "spenden")["ok"])
        b = {x["id"]: x for x in ok.buchungen(self.st.stand())}
        self.assertEqual(b["eingang:e-2FF22222FF2222222"]["kategorie"], "spenden")
        self.assertFalse(ok.kategorie_setzen(self.st, "eingang:gibtsnicht", "spenden")["ok"])
        self.assertFalse(ok.kategorie_setzen(self.st, "eingang:e-2FF22222FF2222222", "xyz")["ok"])
        src = Path(ok.__file__).read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "os.remove", "os.replace", "shutil", '"wb"'):
            self.assertNotIn(verboten, src, verboten)


class TestKasseApi(ApiBasis):
    def test_4_endpunkte_nur_ceo(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.w, "ROOT", Path(d)):
            self.assertTrue(self.c.get("/api/ofc/kasse").json()["ok"])
            self.assertFalse(self.c.post("/api/ofc/kasse/buchung", json={"datum": "2026-10-01", "betrag_cent": -100}).json()["ok"])
            r = self.c.post("/api/ofc/kasse/buchung", json={"datum": "2026-10-01", "betrag_cent": -100, "kategorie": "gebuehren",
                                                            "text": "Gebühr", "bestaetigt": True,
                                                            "beleg": {"name": "b.png", "daten": base64.b64encode(b"\x89PNG").decode()}}).json()
            self.assertTrue(r["ok"])
            self.assertEqual(self.c.get(f"/api/ofc/kasse/beleg/{r['id']}").headers["content-type"], "image/png")
            self.assertTrue(self.c.post("/api/ofc/kasse/anfangsbestand", json={"datum": "2026-09-30", "betrag_cent": 5000, "bestaetigt": True}).json()["ok"])
            self.assertEqual(self.c.get("/api/ofc/kasse").json()["kassenstand_cent"], 4900)
            self.assertTrue(self.c.post("/api/ofc/kasse/storno", json={"id": r["id"], "bestaetigt": True}).json()["storniert"])
            self.assertTrue(self.c.post("/api/ofc/kasse/kategorie", json={"quelle": "kasse:" + r["id"], "kategorie": "auslagen"}).json()["ok"])
            self.assertFalse(self.c.post("/api/ofc/kasse/anfangsbestand", json={"datum": "2026-09-30", "betrag_cent": "x", "bestaetigt": True}).json()["ok"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/kasse").status_code, 403)
                self.assertEqual(self.c.get(f"/api/ofc/kasse/beleg/{r['id']}").status_code, 403)
                for url in ("/api/ofc/kasse/buchung", "/api/ofc/kasse/storno", "/api/ofc/kasse/kategorie", "/api/ofc/kasse/anfangsbestand"):
                    self.assertEqual(self.c.post(url, json={"bestaetigt": True}).status_code, 403, url)


# -- KA4: Abgleich mit dem PayPal-Kontoauszug -------------------------------------------------------------------------
from orchestrator.core import ofc_kasse_import as ki                     # noqa: E402

KOPF_AKT = '"Datum","Uhrzeit","Zeitzone","Beschreibung","Währung","Brutto","Entgelt","Netto","Guthaben","Transaktionscode","Absender E-Mail-Adresse","Name","Hinweis"'


def _akt(*zeilen):
    return ("﻿" + KOPF_AKT + "\n" + "\n".join(zeilen) + "\n").encode("utf-8")


CSV = _akt(
    '"01.10.2026","10:00:00","Europe/Berlin","Zahlung erhalten","EUR","40,00","0,00","40,00","140,00","9AA99999AA9999999","a@example.org","Alt Person",""',
    '"05.10.2026","11:00:00","Europe/Berlin","Zahlung an Händler","EUR","-70,00","0,00","-70,00","70,00","7ZZ77777ZZ7777777","","CTS EVENTIM",""',
    '"07.10.2026","10:00:00","Europe/Berlin","Zahlung erhalten","EUR","35,00","0,00","35,00","105,00","1EE11111EE1111111","b@example.org","Ben Beispiel",""',
    '"08.10.2026","09:00:00","Europe/Berlin","Zahlung erhalten","EUR","10,00","-0,55","9,45","114,45","4GG44444GG4444444","c@example.org","Shop Kunde",""',
    '"09.10.2026","09:00:00","Europe/Berlin","Allgemeine Währungsumrechnung","USD","-5,00","0,00","-5,00","114,45","5UU55555UU5555555","","",""',
    '"10.10.2026","09:00:00","Europe/Berlin","Abbuchung auf Bankkonto","EUR","-14,45","0,00","-14,45","100,00","6BB66666BB6666666","","",""')


# Muster aus dem echten Aktivitaeten-Export (KA4b), Namen und Codes erfunden
kopf = ('"Datum","Uhrzeit","Zeitzone","Name","Typ","Status","Währung","Brutto","Gebühr","Netto","Absender E-Mail-Adresse",'
        '"Empfänger E-Mail-Adresse","Transaktionscode","Guthaben","Zugehöriger Transaktionscode","Auswirkung auf Guthaben"')
z = lambda d, u, n, t, st, b, tc, g, bez, w: f'"{d}","{u}","MEZ","{n}","{t}","{st}","EUR","{b}","0,00","{b}","","","{tc}","{g}","{bez}","{w}"'  # noqa: E731
CSV_ECHT = ("\ufeff" + kopf + "\n" + "\n".join([
    z("01.10.2026", "10:00:00", "Mitglied A", "Handyzahlung", "Abgeschlossen", "41,00", "T01", "141,00", "", "Haben"),
    z("02.10.2026", "10:00:00", "Ticketshop", "PayPal Express-Zahlung", "Abgeschlossen", "-392,00", "T02", "-251,00", "", "Soll"),
    z("02.10.2026", "10:00:00", "", "Zahlung per PayPal-Käuferkredit", "Abgeschlossen", "392,00", "T03", "141,00", "T02", "Haben"),
    z("14.10.2026", "02:35:00", "PayPal Europe", "Allgemeine Zahlung", "Abgeschlossen", "-392,00", "T04", "-251,00", "", "Soll"),
    z("14.10.2026", "02:35:00", "", "Bankgutschrift auf PayPal-Konto", "Ausstehend", "392,00", "T05", "141,00", "T04", "Haben"),
    z("20.10.2026", "01:39:14", "", "Verbindlichkeiten", "Abgeschlossen", "392,00", "T06", "533,00", "T05", "Haben"),
    z("20.10.2026", "01:39:14", "", "Rückbuchung von ACH-Gutschrift", "Abgeschlossen", "-392,00", "T07", "141,00", "T05", "Soll"),
    z("20.10.2026", "01:39:15", "PayPal Europe", "Rückbuchung", "Abgeschlossen", "392,00", "T08", "533,00", "T04", "Haben"),
    z("20.10.2026", "01:39:15", "", "Forderungen", "Abgeschlossen", "-392,00", "T09", "141,00", "T08", "Soll"),
    z("21.10.2026", "09:00:00", "", "Anforderung gesendet", "Abgeschlossen", "58,00", "T10", "141,00", "", "Memo"),
    z("22.10.2026", "09:00:00", "", "Von Nutzer eingeleitete Abbuchung", "Wird bearbeitet", "-100,00", "T11", "41,00", "", "Soll"),
]) + "\n").encode("utf-8")


class TestImport(_Basis):
    def test_5_lesen_und_abgleich(self):
        g = ki.csv_lesen(CSV)
        self.assertEqual((g["ok"], g["format"], len(g["zeilen"])), (True, "aktivitaeten", 6))
        self.assertEqual((g["zeilen"][3]["brutto_cent"], g["zeilen"][3]["gebuehr_cent"], g["zeilen"][3]["guthaben_cent"]), (1000, -55, 11445))
        n = len(self.st.eintraege())
        v = ki.import_plan(self.st.stand(), g["zeilen"])
        self.assertEqual(len(self.st.eintraege()), n)                                              # Vorschau schreibt nichts
        e = {x["tc"]: x for x in v["zeilen"]}
        self.assertEqual(e["1EE11111EE1111111"]["ergebnis"], "bekannt")
        self.assertEqual((e["7ZZ77777ZZ7777777"]["ergebnis"], e["7ZZ77777ZZ7777777"]["buchung"]), ("passt", "zahlung:z-1"))
        self.assertEqual((e["9AA99999AA9999999"]["ergebnis"], e["9AA99999AA9999999"]["kategorie"]), ("neu", "offen"))  # KA4b: zuordnen
        self.assertEqual(e["6BB66666BB6666666"]["kategorie"], "auszahlung")
        self.assertEqual(e["5UU55555UU5555555"]["ergebnis"], "uebersprungen")
        self.assertTrue(e["4GG44444GG4444444"]["gebuehr_neu"])
        self.assertEqual((e["4GG44444GG4444444"]["ergebnis"], e["4GG44444GG4444444"]["buchung"]), ("passt", "zahlung:z-3"))  # Betrag +-3 Tage
        self.assertEqual((v["neu"], v["gebuehren"], v["neu_cent"], v["gebuehren_cent"]), (2, 1, 4000 - 1445, -55))
        self.assertEqual(v["vergleich"]["start_vorschlag"], {"datum": "2026-10-01", "betrag_cent": 10000})
        self.assertNotIn("luna_cent", v["vergleich"])

    def test_6_uebernehmen_doppelt_storno(self):
        r = ki.import_anwenden(self.st, CSV, "auszug.csv", anfangsbestand_uebernehmen=True)
        self.assertEqual((r["ok"], r["gebucht"]), (True, 3))
        self.assertTrue((self.st.dir / "importe" / f"{r['import_id']}.csv").read_bytes() == CSV)
        st = self.st.stand()
        self.assertEqual(st["kasse_start"][-1]["betrag_cent"], 10000)
        v = ki.import_plan(st, ki.csv_lesen(CSV)["zeilen"])
        self.assertEqual((v["neu"], v["gebuehren"]), (0, 0))                                        # zweiter Import: nichts doppelt
        self.assertEqual(ki.import_anwenden(self.st, CSV, "auszug.csv")["gebucht"], 0)
        k = ok.kassenbuch(self.st.stand(), heute=date(2026, 10, 20))
        b = {x["id"]: x for x in k["buchungen"]}
        self.assertTrue(any(x["kategorie"] == "gebuehren" and x["betrag_cent"] == -55 for x in b.values()))
        s = ki.import_storno(self.st, r["import_id"])
        self.assertEqual(s["storniert"], 3)
        self.assertTrue(all(x["status"] == "storniert" for x in ok.kassenbuch(self.st.stand())["buchungen"] if x.get("import_id") == r["import_id"]))
        self.assertFalse(ki.import_storno(self.st, "i-gibtsnicht")["ok"])
        self.assertEqual(ki.import_plan(self.st.stand(), ki.csv_lesen(CSV)["zeilen"])["neu"], 2)     # nach Storno wieder neu

    def test_7b_echter_export_ka4b(self):
        """Muster aus dem echten Aktivitaeten-Export: Ausstehend zaehlt, PayPal-intern hebt sich auf, Spaeter bezahlen, Ruecklastschrift."""
        roh = CSV_ECHT
        g = ki.csv_lesen(roh)
        self.assertEqual(len(g["zeilen"]), 11)
        v = ki.import_plan({}, g["zeilen"])
        e = {x["tc"]: x for x in v["zeilen"]}
        self.assertEqual((e["T02"]["ergebnis"], e["T03"]["ergebnis"]), ("finanziert", "finanziert"))
        self.assertEqual((e["T06"]["ergebnis"], e["T09"]["ergebnis"]), ("technisch", "technisch"))      # Sekunden weichen ab
        self.assertEqual((e["T04"]["kategorie"], e["T05"]["kategorie"]), ("tickets", "einzahlung"))   # Ausstehend zaehlt
        self.assertEqual((e["T07"]["kategorie"], e["T08"]["kategorie"]), ("einzahlung", "tickets"))   # Rueckbuchung erbt
        self.assertEqual(e["T10"]["ergebnis"], "uebersprungen")
        self.assertEqual(e["T11"]["kategorie"], "auszahlung")
        self.assertEqual((v["lastschrift_zurueck"], v["lastschrift_zurueck_cent"]), (1, -39200))
        start = v["vergleich"]["start_vorschlag"]["betrag_cent"]
        self.assertEqual(start, 10000)
        self.assertEqual(start + sum(x["brutto_cent"] for x in v["zeilen"] if x["zaehlt"]), v["vergleich"]["paypal_cent"])  # Guthaben geht auf
        with tempfile.TemporaryDirectory() as d:
            leer = OfcStore(Path(d) / "fanclub")
            r = ki.import_anwenden(leer, roh, "export.csv", anfangsbestand_uebernehmen=True)
            self.assertEqual((r["gebucht"], r["nicht_gebucht"]), (6, []))                  # 11 - Memo - 2 finanziert - 2 technisch
            self.assertEqual(ki.import_plan(leer.stand(), g["zeilen"])["vergleich"]["abweichung_cent"], 0)
            self.assertEqual(ok.kassenbuch(leer.stand(), heute=date(2026, 10, 30))["kassenstand_cent"], 4100)

    def test_7_formate_und_fehler(self):
        leer = ('﻿"RH","Name des Berichts"\n"RH","BALANCE_RECONCILIATION_REPORT"\n"RD","Händlerkonto-ID","Erstellt am"\n'
                '"RF","Dateinummer","Einträge insgesamt"\n').encode("utf-8")
        g = ki.csv_lesen(leer)
        self.assertEqual((g["format"], g["zeilen"]), ("abgleichsbericht", []))
        self.assertIn("0 Einträge", g["hinweis"])
        rd = ('"RH","x"\n"RD","Händlerkonto-ID","Datensatznummer","Erstellt am","Bruttotransaktionsbetrag","Bruttogebühren gesamt","Kundenname","Transaktionswährung"\n'
              '"RD","M1","3XX33333XX3333333","2026/10/02 10:00:00 +0200","12,50","-0,40","Neu Kunde","EUR"\n').encode("utf-8")
        g = ki.csv_lesen(rd)
        z = g["zeilen"][0]
        self.assertEqual((z["datum"], z["brutto_cent"], z["gebuehr_cent"], z["tc"], z["name"]), ("2026-10-02", 1250, -40, "3XX33333XX3333333", "Neu Kunde"))
        self.assertFalse(ki.csv_lesen(b"")["ok"])
        self.assertFalse(ki.csv_lesen(b"a,b,c\n1,2,3\n")["ok"])
        self.assertFalse(ki.csv_lesen(b"x" * (ki.MAX_BYTES + 1))["ok"])
        sem = ("Datum;Name;Brutto;Gebühr;Transaktionscode\n02.10.2026;X;1.234,56;0;T1\n").encode("latin-1")
        self.assertEqual(ki.csv_lesen(sem)["zeilen"][0]["brutto_cent"], 123456)
        src = Path(ki.__file__).read_text(encoding="utf-8")
        for verboten in ("unlink", "rmtree", "os.remove", "os.replace", "shutil", '"wb"'):
            self.assertNotIn(verboten, src, verboten)


class TestImportApi(ApiBasis):
    def test_8_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.w, "ROOT", Path(d)):
            datei = {"name": "a.csv", "daten": base64.b64encode(CSV).decode()}
            v = self.c.post("/api/ofc/kasse/import/vorschau", json={"datei": datei}).json()
            self.assertEqual((v["ok"], v["neu"]), (True, 5))                                          # leere Kasse: alles neu
            self.assertFalse(self.c.post("/api/ofc/kasse/import", json={"datei": datei}).json()["ok"])
            r = self.c.post("/api/ofc/kasse/import", json={"datei": datei, "bestaetigt": True}).json()
            self.assertEqual((r["ok"], r["gebucht"]), (True, 6))
            self.assertNotIn("zeilen", r)
            self.assertEqual(len(self.c.get("/api/ofc/kasse/importe").json()["importe"]), 1)
            self.assertTrue(self.c.post(f"/api/ofc/kasse/import/{r['import_id']}/storno", json={"bestaetigt": True}).json()["ok"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/kasse/importe").status_code, 403)
                self.assertEqual(self.c.post("/api/ofc/kasse/import/vorschau", json={"datei": datei}).status_code, 403)
                self.assertEqual(self.c.post("/api/ofc/kasse/import", json={"datei": datei, "bestaetigt": True}).status_code, 403)


# -- KA5: Kassenbericht -----------------------------------------------------------------------------------------------
class TestBericht(_Basis):
    def test_9_summen_gehen_auf_jahresgrenze_stichtag(self):
        b = ok.kassenbericht(self.st.stand(), 2026, heute=date(2026, 12, 1))
        self.assertIsNone(b["anfangsbestand_cent"]); self.assertIsNone(b["endbestand_cent"])
        self.assertEqual(sum(k["einnahmen_cent"] + k["ausgaben_cent"] for k in b["je_kategorie"]), b["einnahmen_cent"] + b["ausgaben_cent"])
        ok.anfangsbestand_setzen(self.st, "2025-12-01", 5000)
        ok.buchung_anlegen(self.st, datum="2025-12-15", betrag_cent=-1000, kategorie="auslagen", text="Vorjahr")
        ok.buchung_anlegen(self.st, datum="2027-01-02", betrag_cent=-700, kategorie="gebuehren", text="Folgejahr")
        b = ok.kassenbericht(self.st.stand(), 2026, heute=date(2026, 12, 1))
        self.assertEqual((b["ab"], b["anfangsbestand_cent"]), ("2026-01-01", 4000))                 # 5000 - 1000 aus Dez. 2025
        self.assertEqual(b["endbestand_cent"], 4000 + b["einnahmen_cent"] + b["ausgaben_cent"])
        self.assertEqual(b["endbestand_cent"], ok.kassenbericht(self.st.stand(), 2027, heute=date(2026, 12, 1))["anfangsbestand_cent"])
        self.assertFalse(any(k["kategorie"] == "gebuehren" for k in b["je_kategorie"]))             # Folgejahr nicht drin
        ok.anfangsbestand_setzen(self.st, "2026-10-06", 10000)                                       # Stichtag mitten im Jahr
        b = ok.kassenbericht(self.st.stand(), 2026, heute=date(2026, 12, 1))
        self.assertEqual((b["ab"], b["anfangsbestand_cent"]), ("2026-10-06", 10000))
        self.assertIsNone(ok.kassenbericht(self.st.stand(), 2025)["anfangsbestand_cent"])
        self.assertEqual(ok.kassenbericht(self.st.stand(), 2030)["buchungen"], 0)

    def test_10_pdf_hochkant_csv(self):
        ok.anfangsbestand_setzen(self.st, "2026-01-01", 0)
        b = ok.kassenbericht(self.st.stand(), 2026, beitraege={"ok": True, "erfasst": True,
                             "stand": {"offen": 2, "teilweise": 0, "offen_cent": 8000, "quote": 50}})
        from pypdf import PdfReader
        import io
        r = PdfReader(io.BytesIO(ok.bericht_pdf(b)))
        self.assertLess(float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height))
        t = r.pages[0].extract_text()
        self.assertIn("Kassenbericht 2026", t); self.assertIn("Beitragsquote 50", t)
        c = ok.bericht_csv(self.st.stand(), b).decode("utf-8-sig").splitlines()
        self.assertTrue(c[0].startswith("Datum;Betrag;Kategorie")); self.assertEqual(len(c), 1 + b["buchungen"])


class TestBerichtApi(ApiBasis):
    def test_11_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.w, "ROOT", Path(d)), \
                mock.patch.object(self.w, "_ofc_mitglieder_daten", return_value=None):
            self.assertTrue(self.c.get("/api/ofc/kasse/bericht", params={"jahr": 2026}).json()["ok"])
            self.assertFalse(self.c.get("/api/ofc/kasse/bericht", params={"jahr": 1999}).json()["ok"])
            self.assertTrue(self.c.get("/api/ofc/kasse/bericht.pdf", params={"jahr": 2026}).content.startswith(b"%PDF"))
            self.assertIn("Datum;Betrag", self.c.get("/api/ofc/kasse/bericht.csv", params={"jahr": 2026}).content.decode("utf-8-sig"))
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                for url in ("/api/ofc/kasse/bericht", "/api/ofc/kasse/bericht.pdf", "/api/ofc/kasse/bericht.csv"):
                    self.assertEqual(self.c.get(url).status_code, 403, url)
