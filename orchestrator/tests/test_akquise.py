"""PARTNERLISTE P1-P3 (CEO 2026-10-09): Akquise-Ideen getrennt vom Kundenstamm (loeschbar, nicht in der Kette),
Erfassung per Telegram, Anschreiben ueber die Vorstellungs-Mail (Idee -> angeschrieben -> Interessent/Kunde)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core.akquise import IdeenStore, mit_stand, telegram_idee
from orchestrator.core.kunden import DubletteFehler
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests import test_vorstellung as _tv


class TestStore(unittest.TestCase):
    def setUp(self):
        self.st = IdeenStore(Path(tempfile.mkdtemp()) / "akquise")

    def test_1_anlegen_aendern_loeschen(self):
        x = self.st.anlegen({"name": "  Kiez   Burger ", "art": "kunde", "notiz": "Food-Reels", "web": "https://www.kiezburger.de"})
        self.assertEqual((x["name"], x["art"], x["status"], x["quelle"]), ("Kiez Burger", "kunde", "idee", "LUNA-OS"))
        with self.assertRaises(ValueError):
            self.st.anlegen({"name": ""})
        with self.assertRaises(ValueError):
            self.st.anlegen({"name": "X", "art": "lieferant"})
        with self.assertRaises(ValueError):
            self.st.aendern(x["id"], {"mail": "kaputt@"})
        y = self.st.aendern(x["id"], {"ort": "Hamburg", "status": "kein_interesse"})
        self.assertEqual((y["ort"], y["status"], len(y["verlauf"])), ("Hamburg", "kein_interesse", 2))
        with self.assertRaises(ValueError):
            self.st.aendern(x["id"], {"status": "kunde"})                     # Kunde/Antwort nur aus der Vorstellung
        self.st.loeschen(x["id"])
        self.assertEqual(self.st.liste(), [])
        self.assertNotIn("Kiez", self.st.datei.read_text(encoding="utf-8"))  # wirklich weg, nicht nur markiert

    def test_2_dubletten_ideen_und_kundenstamm(self):
        bh, ks, st, k, ap = _stores()                                        # K-00001 Brand X GmbH, anna@brandx.de
        self.st.anlegen({"name": "Kiez Burger GmbH", "web": "kiezburger.de"})
        for daten, wer in (({"name": "Kiez Burger"}, "idee"), ({"name": "KB", "mail": "info@kiezburger.de"}, "idee"),
                           ({"name": "Brand X"}, "firma"), ({"name": "BX", "mail": "chef@brandx.de"}, "firma")):
            with self.assertRaises(DubletteFehler, msg=daten) as cm:
                self.st.anlegen(daten, kunden=ks)
            self.assertIn(wer, [g["art"] for g in self.st.dubletten(daten["name"], "", daten.get("mail", ""), ks)])
            self.assertTrue(cm.exception.nummern)
        self.st.anlegen({"name": "Ganz Neu", "mail": "a@gmail.com"}, kunden=ks)                 # Freemail = keine Dublette
        self.st.anlegen({"name": "Kiez Burger"}, kunden=ks, trotz_dublette=True)
        self.assertEqual(len(self.st.liste()), 3)
        self.assertNotIn("Kiez Burger", json.dumps(bh.eintraege(), ensure_ascii=False))       # nie in der Kette

    def test_3_telegram_saetze(self):
        self.assertEqual(telegram_idee("Partner-Idee: Kiez Burger – passt für Food-Reels"),
                         {"name": "Kiez Burger", "notiz": "passt für Food-Reels", "art": "partner"})
        self.assertEqual(telegram_idee("Kunden-Idee: Elbphilharmonie Gastro, Food Reels")["art"], "kunde")
        self.assertEqual(telegram_idee("Merk dir Hafenbar als möglichen Kunden, Hafen-Content"),
                         {"name": "Hafenbar", "notiz": "Hafen-Content", "art": "kunde"})
        self.assertEqual(telegram_idee("Akquise: Hamburger Volksbank")["name"], "Hamburger Volksbank")
        for chat in ("merk dir den Termin morgen", "Idee für ein Reel: Derby", "Idee: Kiez Burger", "Partner-Idee: wer passt?",
                     "Was ist mit Kiez Burger?"):
            self.assertIsNone(telegram_idee(chat), chat)

    def test_4_stand_aus_vorstellung(self):
        ideen = [{"id": "I-1", "status": "angeschrieben", "firma": "K-1"}, {"id": "I-2", "status": "angeschrieben", "firma": "K-2"},
                 {"id": "I-3", "status": "angeschrieben", "firma": "K-3"}, {"id": "I-4", "status": "idee", "firma": ""}]
        vs = [{"firma": "K-1", "antwort": "2026-10-09", "erledigt": ""}, {"firma": "K-2", "antwort": "", "erledigt": "kein Interesse"}]
        kunden = mock.Mock(firma=lambda n: {"K-3": {"typ": "kunde", "name": "Drei"}}.get(n, {"typ": "interessent"}))
        self.assertEqual([x["status"] for x in mit_stand(ideen, vs, kunden)], ["antwort", "kein_interesse", "kunde", "idee"])


class TestApi(ApiBasis):
    def setUp(self):
        super().setUp()
        self.st = IdeenStore(Path(tempfile.mkdtemp()) / "akquise")
        self._p = mock.patch.object(self.w, "_ideen", return_value=self.st)
        self._p.start()

    def tearDown(self):
        self._p.stop()
        super().tearDown()

    def test_5_liste_anlegen_suchen(self):
        r = self.c.post("/api/crm/ideen", json={"idee": {"name": "Kiez Burger", "art": "partner", "notiz": "Food"}}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.post("/api/crm/ideen", json={"idee": {"name": "Brand X GmbH"}}).json()       # gibt es als Firma
        self.assertEqual((d["ok"], d["dublette"]), (False, [self.k]))
        iid = r["idee"]["id"]
        self.assertTrue(self.c.post(f"/api/crm/ideen/{iid}", json={"idee": {"ort": "Hamburg"}}).json()["ok"])
        l = self.c.get("/api/crm/ideen").json()
        self.assertEqual(([x["ort"] for x in l["ideen"]], l["arten"]["partner"]), (["Hamburg"], "potenzieller Partner"))
        fake = mock.Mock(fuer_idee=lambda name, web: {"vorschlaege": {"web": "https://kiezburger.de", "ort": "Hamburg"},
                                                      "quelle": "https://kiezburger.de/impressum", "hinweis": ""})
        with mock.patch.object(self.w, "_recherche", return_value=fake):
            s = self.c.post(f"/api/crm/ideen/{iid}/suchen", json={}).json()
        self.assertEqual(s["vorschlaege"]["web"], "https://kiezburger.de")
        self.assertEqual(self.st.get(iid)["web"], "")                                         # nur Vorschlag, nichts gespeichert
        self.assertTrue(self.c.post(f"/api/crm/ideen/{iid}/loeschen", json={}).json()["ok"])
        self.assertEqual(self.c.get("/api/crm/ideen").json()["ideen"], [])


class TestAnschreiben(_tv.TestVorstellung):
    """P3 ueber die echte Vorstellungs-Mail (All-Inkl-Fake): Idee -> angeschrieben, Firma als Interessent."""
    def setUp(self):
        super().setUp()
        self.st = IdeenStore(Path(tempfile.mkdtemp()) / "akquise")
        self._p = mock.patch.object(self.w, "_ideen", return_value=self.st)
        self._p.start()

    def tearDown(self):
        self._p.stop()
        super().tearDown()

    def test_6_idee_anschreiben(self):
        v = self.c.get("/api/crm/vorstellung/vorschau?name=Hafenbar&partner=1").json()
        self.assertEqual(v["betreff"], "Hanserautisch × Hafenbar – Idee für eine Partnerschaft")
        self.assertIn("Partnerschaft", v["text"])
        x = self.st.anlegen({"name": "Hafenbar", "mail": "chef@hafenbar.de"})
        r, _ = self._mit_allinkl(lambda: self.c.post("/api/crm/vorstellung/senden", json={
            "neu": {"name": "Hafenbar"}, "an": "chef@hafenbar.de", "betreff": v["betreff"], "text": v["text"],
            "bestaetigt": True, "idee": x["id"]}).json())
        self.assertTrue(r["ok"], r)
        y = self.st.get(x["id"])
        self.assertEqual((y["status"], y["firma"], r["idee"]), ("angeschrieben", r["firma"], x["id"]))
        self.assertEqual(self.w.kunden_store.firma(r["firma"])["typ"], "interessent")
        self.assertEqual(self.c.get("/api/crm/ideen").json()["ideen"][0]["firma_name"], "Hafenbar")

    # die geerbten Vorstellungs-Tests nicht doppelt laufen lassen
    test_1_vorschau = test_2_neue_firma_erst_nach_versand = test_3_antwort_nachfassen_kunde = None
    test_4_kein_interesse_und_nachfassen = None


class TestTelegram(unittest.TestCase):
    def test_7_idee_und_rueckgaengig(self):
        from orchestrator.channels.telegram import bot
        st = IdeenStore(Path(tempfile.mkdtemp()) / "akquise")
        gesendet = []
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append((m, p))), \
                mock.patch.object(bot, "_ideen", return_value=st), mock.patch.object(bot, "ROOT", Path(tempfile.mkdtemp())):
            bot._akquise_idee("T", "1", telegram_idee("Partner-Idee: Kiez Burger – Food-Reels"))
            x = st.liste()[0]
            self.assertIn("Gemerkt: Kiez Burger", gesendet[-1][1]["text"])
            kb = json.loads(gesendet[-1][1]["reply_markup"])["inline_keyboard"][0]
            self.assertEqual([b["callback_data"] for b in kb], [f"akq:{x['id']}:such", f"akq:{x['id']}:del"])
            bot._akquise_idee("T", "1", telegram_idee("Partner-Idee: Kiez Burger"))         # Dublette -> nachfragen
            self.assertEqual(len(st.liste()), 1)
            key = json.loads(gesendet[-1][1]["reply_markup"])["inline_keyboard"][0][0]["callback_data"].split(":")[1]
            bot._akquise_klick("T", "1", f"akq:{key}:no", 5)
            self.assertEqual(len(st.liste()), 1)
            self.assertEqual(bot._akquise_klick("T", "1", f"akq:{x['id']}:del", 6), "Entfernt")
        self.assertEqual(st.liste(), [])


if __name__ == "__main__":
    unittest.main()
