"""SERIEN_UND_VORSTELLUNG V1/V2: Vorstellungs-Mail in einem Schritt (Firma erst nach erfolgreichem Versand als Interessent),
Dubletten, Akte + Kennung -> Antwort erkannt, Nachfassen nach 7 Tagen im Handlungsbedarf, Interessent -> Kunde."""
import unittest
from datetime import date, timedelta
from unittest import mock

from orchestrator.core.mail_antworten import antworten_pruefen
from orchestrator.core.vorstellung import liste, todos
from orchestrator.tests.test_allinkl_mail import ENV, FakeIMAP, FakeSMTP
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mail_antworten import CEO, Postfach, antwort


class TestVorstellung(ApiBasis):
    def _mit_allinkl(self, fn, smtp_fehler=None):
        p = []
        with mock.patch.object(self.w, "_google_secrets", return_value=ENV), \
             mock.patch("smtplib.SMTP_SSL", lambda *a, **k: FakeSMTP(p, smtp_fehler)), \
             mock.patch("imaplib.IMAP4_SSL", lambda *a, **k: FakeIMAP(p)):
            return fn(), p

    def test_1_vorschau(self):
        v = self.c.get("/api/crm/vorstellung/vorschau?name=Kiez%20Alm%20Gastro&vorname=Lena&nachname=Wirt").json()
        self.assertEqual(v["betreff"], "Hanserautisch × Kiez Alm Gastro – kurze Vorstellung")
        self.assertTrue(v["text"].startswith("Moin Lena Wirt,"))
        self.assertIn("canva.link", v["text"])                                       # Praesentation aus dem Katalog
        self.assertIn("§ 7 Abs. 2 UWG", v["hinweis_uwg"])
        self.assertIn("anfrage", v["anlaesse"])
        v = self.c.get(f"/api/crm/vorstellung/vorschau?firma={self.k}").json()
        self.assertEqual((v["an"], v["firma"]["nummer"]), ("anna@brandx.de", self.k))   # Mail des Ansprechpartners

    def test_2_neue_firma_erst_nach_versand(self):
        body = {"neu": {"name": "Kiez Alm Gastro GmbH", "vorname": "Lena", "nachname": "Wirt"}, "an": "lena@kiezalm.de",
                "betreff": "Hallo", "text": "Moin", "anlass": "anfrage"}
        self.assertFalse(self.c.post("/api/crm/vorstellung/senden", json=body).json()["ok"])          # ohne Bestaetigung
        r, p = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json=body | {"bestaetigt": True}).json(),
                                 smtp_fehler=OSError("weg"))
        self.assertFalse(r["ok"])
        self.assertFalse([f for f in self.w.kunden_store.firmen() if "Kiez" in f["name"]])                # Versand scheitert -> keine Firma
        r, p = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json=body | {"bestaetigt": True}).json())
        self.assertTrue(r["ok"], r)
        f = self.w.kunden_store.firma(r["firma"])
        self.assertEqual((f["typ"], r["neu_angelegt"], f["ansprechpartner_liste"][0]["mail"]), ("interessent", True, "lena@kiezalm.de"))
        self.assertTrue(r["firma"].startswith("K-"))
        akte = self.c.get(f"/api/crm/kunden/{r['firma']}/akte").json()
        self.assertEqual([d["art"] for d in akte["dokumente"]], ["mail"])                               # .eml in der Akte
        # Dublette: gleiche Domain -> Hinweis statt zweite Firma
        r2, _ = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json=body | {
            "bestaetigt": True, "neu": {"name": "Kiez-Alm"}, "an": "info@kiezalm.de"}).json())
        self.assertEqual((r2["ok"], r2.get("dublette")), (False, [r["firma"]]))
        # nur fuer den CEO
        with mock.patch.object(self.w, "hat_modul", return_value=False):
            self.assertIn("nur der CEO", self.c.post("/api/crm/vorstellung/senden", json=body | {"bestaetigt": True}).json()["hinweis"])

    def test_3_antwort_nachfassen_kunde(self):
        bh, ks = self.w.kunden_store.bh, self.w.kunden_store
        body = {"neu": {"name": "Hafenbar"}, "an": "chef@hafenbar.de", "betreff": "Hallo Hafenbar", "text": "Moin", "bestaetigt": True}
        r, p = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json=body).json())
        nr, mid = r["firma"], [x[1] for x in p if x[0] == "send"][0]["Message-ID"]
        heute = date.today()
        self.assertEqual(todos(bh, ks, heute), [])                                                     # erst nach 7 Tagen
        t = todos(bh, ks, heute + timedelta(days=7))
        self.assertEqual([(x["titel"], x["act"], x["act_id"]) for x in t], [("Nachfassen: Hafenbar", "vs-neu", nr)])
        meldungen = []
        neu = antworten_pruefen(bh, ks, Postfach([antwort("chef@hafenbar.de", "Re: Hallo Hafenbar", "Klingt gut!", auf=mid)]),
                                eigene=CEO, notify=lambda text, **kw: meldungen.append(text))
        self.assertEqual([(x["nummer"], x["ablage"]) for x in neu], [(nr, "akte")])
        self.assertIn(f"Antwort auf Vorstellung an Hafenbar ({nr})", meldungen[0])
        self.assertEqual(todos(bh, ks, heute + timedelta(days=7)), [])                                 # Antwort da -> kein Nachfassen
        self.assertTrue(liste(bh, ks, heute)[0]["antwort"])
        self.assertEqual(len(self.c.get(f"/api/crm/kunden/{nr}/akte").json()["dokumente"]), 2)
        # Interessent -> Kunde, sobald ein Angebot angenommen ist
        an = self.c.post("/api/crm/angebote", json={"angebot": {"firma": nr, "titel": "Test", "positionen": [
            {"beschreibung": "Reel", "menge": "1", "einzelpreis": "1000"}]}}).json()["nummer"]
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        self.c.post(f"/api/crm/angebote/{an}/status", json={"status": "angenommen"})
        self.assertEqual(ks.firma(nr)["typ"], "kunde")

    def test_4_kein_interesse_und_nachfassen(self):
        bh, ks = self.w.kunden_store.bh, self.w.kunden_store
        r, _ = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json={
            "firma": self.k, "an": "anna@brandx.de", "betreff": "Hallo", "text": "Moin", "bestaetigt": True}).json())
        self.assertEqual((r["firma"], r["neu_angelegt"]), (self.k, False))
        v = self.c.get(f"/api/crm/vorstellung/vorschau?firma={self.k}&nachfassen=1").json()
        self.assertIn("Kurze Nachfrage", v["betreff"])
        self.assertIn(date.today().strftime("%d.%m.%Y"), v["text"])                                    # Datum der ersten Mail
        self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json={
            "firma": self.k, "an": "anna@brandx.de", "betreff": v["betreff"], "text": v["text"], "bestaetigt": True, "nachfassen": True}).json())
        l = self.c.get("/api/crm/vorstellungen").json()["vorstellungen"]
        self.assertEqual((l[0]["anzahl"], l[0]["nachgefasst"]), (2, 1))
        self.assertTrue(self.c.post(f"/api/crm/vorstellungen/{self.k}/erledigt", json={}).json()["ok"])
        self.assertEqual(todos(bh, ks, date.today() + timedelta(days=30)), [])
        self.assertEqual(self.c.get("/api/crm/vorstellungen").json()["vorstellungen"][0]["erledigt"], "kein Interesse")
        self.assertFalse(self.c.post("/api/crm/vorstellungen/K-99999/erledigt", json={}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
