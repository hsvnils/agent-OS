"""PROJEKTZEITEN Z1: Stundenzettel (Datum, Ein, Aus, Pause, Dauer, Taetigkeit, km; Summen je Tag und gesamt),
Korrektur mit Verlauf, Taetigkeit nach dem Stopp (auch per Telegram)."""
import json
import unittest
from datetime import datetime, timedelta
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_zeiterfassung import _setup

GESTERN = (jetzt().date() - timedelta(days=1)).isoformat()
VORGESTERN = (jetzt().date() - timedelta(days=2)).isoformat()


class TestStundenzettel(unittest.TestCase):
    def test_1_zeilen_und_summen(self):
        bh, ks, k, ab, nr, z = _setup()
        a = z.eintragen(auftrag=nr, datum=VORGESTERN, von_uhr="09:00", bis_uhr="12:30", pause_min="30", taetigkeit="Dreh")
        z.eintragen(auftrag=nr, datum=VORGESTERN, von_uhr="14:00", bis_uhr="15:00", taetigkeit="Schnitt")
        z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="22:00", bis_uhr="01:00", taetigkeit="Schnitt")   # ueber Mitternacht
        z.fahrt_erfassen(a["id"], km=40)
        self.assertEqual(a["minuten"], 180)                                       # 3,5 h - 30 min Pause
        sz = z.stundenzettel(nr)
        self.assertEqual([(e["datum"], e["von"], e["bis"], e["pause_min"], e["minuten"], e["taetigkeit"]) for e in sz["eintraege"]],
                         [(VORGESTERN, "09:00", "12:30", 30, 180, "Dreh"), (VORGESTERN, "14:00", "15:00", 0, 60, "Schnitt"),
                          (GESTERN, "22:00", "01:00", 0, 180, "Schnitt")])
        self.assertEqual([(t["datum"], t["minuten"], t["km"]) for t in sz["tage"]], [(VORGESTERN, 240, 40), (GESTERN, 180, 0)])
        self.assertEqual((sz["summe"]["minuten"], sz["summe"]["km"]), (420, 40))
        self.assertEqual(sz["summe"]["kosten_cent"], round(420 * 2920 / 60))     # Pause kostet nichts
        self.assertEqual(z.taetigkeiten(), ["Schnitt", "Dreh"])
        with self.assertRaisesRegex(ValueError, "Pause"):
            z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="10:00", pause_min="60")

    def test_2_stoppen_mit_taetigkeit_und_details(self):
        bh, ks, k, ab, nr, z = _setup()
        r = z.starten(auftrag=nr)
        ende = (datetime.fromisoformat(r["start"]) + timedelta(minutes=95)).isoformat()
        s = z.stoppen(ende=ende, taetigkeit="  Dreh   Stadion ", pause_min=5)
        self.assertEqual(s["minuten"], 90)
        x = z.stundenzettel(nr)["eintraege"][0]
        self.assertEqual((x["taetigkeit"], x["pause_min"], x["minuten"]), ("Dreh Stadion", 5, 90))
        z.details_setzen(s["id"], taetigkeit="Dreh", pause_min=15, notiz="Regen")
        x = z.stundenzettel(nr)["eintraege"][0]
        self.assertEqual((x["taetigkeit"], x["pause_min"], x["minuten"], x["notiz"]), ("Dreh", 15, 80, "Regen"))

    def test_3_korrektur_mit_verlauf(self):
        bh, ks, k, ab, nr, z = _setup()
        e = z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="18:00", taetigkeit="Dreh")
        with self.assertRaisesRegex(ValueError, "begruenden"):
            z.korrigieren(e["id"], datum=GESTERN, von_uhr="09:00", bis_uhr="12:00")
        r = z.korrigieren(e["id"], datum=GESTERN, von_uhr="09:00", bis_uhr="12:00", pause_min=15, grund="Stoppen vergessen")
        self.assertEqual(r["minuten"], 165)
        x = z._falte()[e["id"]]
        self.assertEqual(x["korrekturen"][0]["vorher"]["ende"][11:16], "18:00")
        self.assertEqual(z.stundenzettel(nr)["eintraege"][0]["korrigiert"], 1)
        typen = [ev["typ"] for ev in bh.eintraege() if ev["daten"].get("id") == e["id"]]
        self.assertEqual(typen, ["zeit_eintrag", "zeit_korrigiert"])           # nichts ueberschrieben, nur angehaengt

    def test_4_telegram_taetigkeit(self):
        from orchestrator.channels.telegram import bot
        bh, ks, k, ab, nr, z = _setup()
        z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="10:00", taetigkeit="Schnitt")
        e = z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="11:00", bis_uhr="12:00")
        gesendet = []
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append(p)):
            bot._zeit_taet_frage("T", "1", z, e["id"])
        kb = json.loads(gesendet[0]["reply_markup"])["inline_keyboard"]
        self.assertEqual([b["text"] for b in kb[0]], ["Schnitt"])
        self.assertEqual(kb[0][0]["callback_data"], f"ztt:{e['id']}:0")
        self.assertLessEqual(max(len(b["callback_data"].encode()) for r in kb for b in r), 64)   # Telegram-Grenze


class TestApi(ApiBasis):
    def test_a1_endpunkte(self):
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"})
        r = self.c.post("/api/finanzen/zeit/eintrag", json={"auftrag": nr, "datum": GESTERN, "von": "09:00", "bis": "11:00",
                                                             "taetigkeit": "Dreh", "pause_min": "10"}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.get(f"/api/finanzen/zeit?auftrag={nr}").json()
        self.assertEqual(d["stundenzettel"]["summe"]["minuten"], 110)
        self.assertEqual(d["taetigkeiten"], ["Dreh"])
        k = self.c.post(f"/api/finanzen/zeit/{r['id']}/korrigieren", json={"datum": GESTERN, "von": "09:00", "bis": "10:00",
                                                                           "grund": "falsch"}).json()
        self.assertTrue(k["ok"], k)
        self.assertTrue(self.c.post(f"/api/finanzen/zeit/{r['id']}/details", json={"taetigkeit": "Schnitt"}).json()["ok"])
        x = self.c.get(f"/api/finanzen/zeit?auftrag={nr}").json()["stundenzettel"]["eintraege"][0]
        self.assertEqual((x["minuten"], x["taetigkeit"]), (60, "Schnitt"))


if __name__ == "__main__":
    unittest.main()
