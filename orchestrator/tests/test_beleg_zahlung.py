"""CEO 2026-11-06: Rechnung mit „EUR 39,99“ (WISO) wird erkannt; Bezahlt-/Lastschrift-Hinweise vom Beleg werden
vorgeschlagen und beim Buchen mitgebucht; das Briefing nennt je Beleg Absender, Betrag und Status."""
import base64
import unittest
from datetime import datetime

from orchestrator.core.beleg_briefing import text, vorheriges_briefing, zeilen
from orchestrator.core.eingangsbelege import mail_ist_beleg, vorschlag_mail, vorschlag_regeln, zahlung_erkennen
from orchestrator.tests.test_eingangsbelege import TEXT, _pdf

WISO = ("Hallo Max Muster, die Rechnung für Steuer-Software 2027 ist jetzt verfügbar. Ihre Rechnung in der Übersicht "   # erfundene Werte
        "Kundennummer: 12345678 Rechnungsnummer: 26RS00000001 Rechnungsdatum: 04.11.2026 Rechnungsbetrag: EUR 39,99 "
        "Zahlung Sie müssen sich um nichts kümmern. Den Rechnungsbetrag buchen wir am 01.12.2026 vom Konto: *******00 "
        "mit der Mandatsreferenz MD0000000000 ab.")


class TestErkennung(unittest.TestCase):
    def test_1_eur_vor_dem_betrag(self):
        betreff = "Ihre Online-Rechnung für Steuer-Software 2027, Re-Nr.: 26RS00000001"
        self.assertTrue(mail_ist_beleg(betreff, WISO))
        self.assertFalse(mail_ist_beleg(betreff, WISO.replace("EUR 39,99", "siehe Kundenkonto")))   # Gegenprobe
        v = vorschlag_mail(WISO, {"betreff": betreff, "von_name": "Buhl Data Service GmbH"})
        self.assertEqual((v["betrag"], v["rechnungsnummer"], v["rechnungsdatum"]), ("39,99", "26RS00000001", "2026-11-04"))

    def test_2_lastschrift_mit_datum_setzt_faelligkeit(self):
        v = vorschlag_regeln(WISO)
        self.assertEqual(v["zahlung"], {"status": "lastschrift", "datum": "2026-12-01", "weg": "Lastschrift"})
        self.assertEqual(v["faellig_am"], "2026-12-01")

    def test_3_bezahlt_hinweise(self):
        self.assertEqual(zahlung_erkennen("Sie haben eine Zahlung über 12,99 € an Dropbox gesendet. PayPal. "
                                          "Transaktionsdatum: 03.11.2026"),
                         {"status": "bezahlt", "datum": "2026-11-03", "weg": "PayPal"})
        self.assertEqual(zahlung_erkennen("Invoice Date paid November 3, 2026 Amount paid €20.00 Visa ending 4242"),
                         {"status": "bezahlt", "datum": "2026-11-03", "weg": "Kreditkarte"})
        self.assertEqual(zahlung_erkennen("Ihre Quittung von Apple Gesamt 2,99 €")["status"], "bezahlt")

    def test_4_offene_rechnung_kein_hinweis(self):
        self.assertEqual(zahlung_erkennen(TEXT), {})                                    # „Zahlbar bis“
        self.assertEqual(zahlung_erkennen("Rechnung 10,00 EUR Zahlungsart: Rechnung"), {})
        self.assertNotIn("zahlung", vorschlag_regeln(TEXT))
        self.assertEqual(zahlung_erkennen("Zahlbar bis 20.11. – bereits bezahlt"), {})   # Aufforderung ohne Datum


class TestBuchenMitZahlung(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.auftraege import AuftragStore
        from orchestrator.tests.test_angebote import _stores
        self.w = webapp
        self.orig = (webapp.kunden_store, webapp.backoffice)
        bh, ks, *_ = _stores()
        webapp.kunden_store, webapp.backoffice = ks, AuftragStore(bh.dir.parent / "b.jsonl")
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.kunden_store, self.w.backoffice = self.orig

    def _beleg(self, inhalt=TEXT):
        r = self.c.post("/api/finanzen/belege/hochladen", json={"dateien": [
            {"name": "Beleg.pdf", "daten": base64.b64encode(_pdf(inhalt)).decode()}]}).json()
        return r["ergebnisse"][0]["nummer"]

    FELDER = {"lieferant": "Druckerei Nord GmbH", "rechnungsnummer": "DN-2026-0815", "rechnungsdatum": "2026-09-12",
              "betrag": "1.190,00", "kategorie": "wareneinkauf"}

    def test_1_zahlung_wird_mitgebucht(self):
        nr = self._beleg()
        b = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": self.FELDER,
                        "bezahlt": {"datum": "2026-09-13", "notiz": "laut Beleg: PayPal"}}).json()
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["zahlung"]["bezahlt_am"], "2026-09-13")
        d = self.c.get(f"/api/finanzen/belege/{nr}").json()["beleg"]
        self.assertEqual((d["status"], d["bezahlt_am"]), ("gebucht", "2026-09-13"))

    def test_2_ohne_haken_bleibt_zahlung_offen(self):
        nr = self._beleg()
        b = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": self.FELDER}).json()
        self.assertTrue(b["ok"])
        self.assertNotIn("zahlung", b)
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{nr}").json()["beleg"]["bezahlt_am"], "")

    def test_3_zukunft_bucht_trotzdem_mit_hinweis(self):
        nr = self._beleg()
        b = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": self.FELDER,
                        "bezahlt": {"datum": "2099-01-01"}}).json()
        self.assertTrue(b["ok"])
        self.assertIn("Zukunft", b["zahlung_hinweis"])
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{nr}").json()["beleg"]["status"], "gebucht")

    def test_4_korrektur_bucht_keine_zweite_zahlung(self):
        nr = self._beleg()
        z = {"datum": "2026-09-13"}
        self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": self.FELDER, "bezahlt": z})
        b = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": self.FELDER, "bezahlt": z}).json()
        self.assertTrue(b["ok"])
        self.assertNotIn("zahlung", b)                                                  # nur beim ersten Buchen


def _e(typ, ts, daten, von="LUNA-Mail"):
    return {"typ": typ, "ts": ts, "von": von, "daten": daten}


class TestBriefing(unittest.TestCase):
    SEIT = datetime(2026, 11, 6, 8, 0)

    def _log(self):
        return [
            _e("eingang_angelegt", "2026-11-05T10:00:00+01:00", {"nummer": "ER-2026-0001", "dateiname": "alt.pdf"}),
            _e("eingang_angelegt", "2026-11-06T09:00:00+01:00", {"nummer": "ER-2026-0002", "dateiname": "w.pdf", "mail_id": "m2"}),
            _e("eingang_vorschlag", "2026-11-06T09:00:01+01:00", {"nummer": "ER-2026-0002", "vorschlag": {
                "lieferant": "Buhl Data Service GmbH", "betrag": "39,99",
                "zahlung": {"status": "lastschrift", "datum": "2026-12-01", "weg": "Lastschrift"}}}),
            _e("eingang_angelegt", "2026-11-06T09:30:00+01:00", {"nummer": "ER-2026-0003", "dateiname": "d.pdf"}),
            _e("eingang_gebucht", "2026-11-06T10:00:00+01:00", {"nummer": "ER-2026-0003", "felder": {
                "lieferant": "Dropbox", "betrag_cent": 1999}}, von="LUNA-OS:ceo"),
            _e("eingang_bezahlt", "2026-11-06T10:00:01+01:00", {"nummer": "ER-2026-0003", "datum": "2026-11-03",
                                                                "betrag_cent": 1999}, von="LUNA-OS:ceo"),
            _e("eigenbeleg_angelegt", "2026-11-06T11:00:00+01:00", {"nummer": "EB-2026-0001", "gegenpartei": "Sky",
                                                                    "betrag_cent": 3360}, von="LUNA-Abo (automatisch)"),
            _e("eigenbeleg_angelegt", "2026-11-06T11:05:00+01:00", {"nummer": "EB-2026-0002", "gegenpartei": "Anthropic",
                                                                    "betrag_cent": 10710}, von="LUNA-OS:ceo"),
            _e("akte_mail_offen", "2026-11-06T12:00:00+01:00", {"id": "D-1", "titel": "Ihre Rechnung Nr. 5",
                                                                "mail_von": "rechnung@firma.de", "mail_id": "m9"}),
            _e("akte_mail_offen", "2026-11-06T12:00:00+01:00", {"id": "D-2", "titel": "Ihre Online-Rechnung",
                                                                "mail_von": "x@buhl.de", "mail_id": "m2"}),
            _e("akte_mail_offen", "2026-11-06T12:01:00+01:00", {"id": "D-3", "titel": "Einladung zum Termin",
                                                                "mail_von": "a@b.de", "mail_id": "m3"}),
        ]

    def test_1_zeilen(self):
        z = zeilen(self._log(), self.SEIT)
        self.assertEqual(len(z), 4, z)
        self.assertFalse(any("ER-2026-0001" in x for x in z))                          # vor dem letzten Briefing
        self.assertIn("Buhl Data Service GmbH – 39,99 € → noch NICHT gebucht", z[0])
        self.assertIn("Lastschrift am 01.12.", z[0])
        self.assertIn("Dropbox – 19,99 € → gebucht von dir · bezahlt 03.11.", z[1])
        self.assertIn("Sky – 33,60 € → automatisch gebucht von LUNA", z[2])
        self.assertFalse(any("Anthropic" in x for x in z))                              # vom CEO selbst angelegt
        self.assertIn("D-1", z[3])                                                      # Rechnung als Brief abgelegt
        self.assertFalse(any("D-2" in x or "D-3" in x for x in z))                     # schon Beleg bzw. kein Rechnungswort

    def test_2_text_zu_tun_zuerst_und_begrenzt(self):
        t = text(self._log(), self.SEIT, max_zeilen=2)
        self.assertTrue(t.startswith("📥 Belege seit dem letzten Briefing (4):"))
        self.assertIn("Von Hand zu tun: 2 Punkte.", t)
        self.assertIn("… und 2 weitere", t)
        self.assertNotIn("Dropbox", t)                                                  # erledigtes faellt zuerst weg
        self.assertEqual(text(self._log(), datetime(2026, 11, 7)), "")

    def test_3_vorheriges_briefing(self):
        self.assertEqual(vorheriges_briefing(datetime(2026, 11, 7, 8, 2), [8, 20]), datetime(2026, 11, 6, 20, 0))
        self.assertEqual(vorheriges_briefing(datetime(2026, 11, 6, 20, 0), [8, 20]), datetime(2026, 11, 6, 8, 0))


if __name__ == "__main__":
    unittest.main()
