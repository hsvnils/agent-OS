"""ZEITERFASSUNG_GRUND (CEO 2026-10-09): Z1 feste Gruende der Arbeitszeit (Dreharbeiten, Postproduktion & Schnitt,
Konzept & Abstimmung, Sonstiges), Pflicht beim Nachtragen; Z2 Zeiten per Telegram nachtragen (nur nach ✅)."""
import json
import unittest
from datetime import date, timedelta
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.zeiterfassung import arbeit_text, auswertung, nachtrag
from orchestrator.tests.test_zeiterfassung import _setup

GESTERN = (jetzt().date() - timedelta(days=1)).isoformat()


class TestGrund(unittest.TestCase):
    def test_1_pruefung_und_pflicht(self):
        bh, ks, k, ab, nr, z = _setup()
        with self.assertRaisesRegex(ValueError, "Grund"):
            z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="10:00", arbeit_pflicht=True)
        with self.assertRaisesRegex(ValueError, "Grund muss"):
            z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="10:00", arbeit="urlaub")
        with self.assertRaisesRegex(ValueError, "Sonstiges"):
            z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="10:00", arbeit="sonstiges", arbeit_pflicht=True)
        z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="09:00", bis_uhr="12:00", arbeit="dreh", arbeit_pflicht=True)
        z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="13:00", bis_uhr="14:00", arbeit="Postproduktion & Schnitt",
                    taetigkeit="Farbkorrektur")                                  # Beschriftung wird auch erkannt
        z.eintragen(auftrag=nr, datum=GESTERN, von_uhr="15:00", bis_uhr="15:30", arbeit="sonstiges", taetigkeit="Messe")
        sz = z.stundenzettel(nr)["eintraege"]
        self.assertEqual([(x["arbeit"], x["taetigkeit"]) for x in sz],
                         [("dreh", "Dreharbeiten"), ("post", "Postproduktion & Schnitt – Farbkorrektur"), ("sonstiges", "Sonstiges: Messe")])
        r = auswertung(bh.eintraege(), GESTERN, GESTERN)
        self.assertEqual([(x["name"], x["minuten"]) for x in r["je_taetigkeit"]],
                         [("Dreharbeiten", 180), ("Postproduktion & Schnitt", 60), ("Sonstiges", 30)])

    def test_2_alte_freitexte_und_nachtraeglich(self):
        self.assertEqual(arbeit_text({"taetigkeit": "Schnitt"}), "Postproduktion & Schnitt")
        self.assertEqual(arbeit_text({"taetigkeit": "Dreh im Stadion"}), "Dreharbeiten – Dreh im Stadion")
        self.assertEqual(arbeit_text({"taetigkeit": "Steuerkram"}), "Sonstiges: Steuerkram")
        self.assertEqual(arbeit_text({}), "")
        bh, ks, k, ab, nr, z = _setup()
        r = z.starten(auftrag=nr)
        from datetime import datetime
        s = z.stoppen(ende=(datetime.fromisoformat(r["start"]) + timedelta(minutes=30)).isoformat(), arbeit="konzept")
        self.assertEqual(z.stundenzettel(nr)["eintraege"][0]["arbeit"], "konzept")
        z.details_setzen(s["id"], arbeit="post")                                 # Grund nach dem Stopp aendern
        self.assertEqual(z.stundenzettel(nr)["eintraege"][0]["taetigkeit"], "Postproduktion & Schnitt")


class TestNachtragErkennung(unittest.TestCase):
    H = date(2026, 10, 9)

    def test_3_saetze(self):
        n = nachtrag("Gestern 3 Stunden Schnitt für CR Container", self.H)
        self.assertEqual((n["datum"], n["minuten"], n["arbeit"], n["ziel"]), ("2026-10-08", 180, "post", "CR Container"))
        n = nachtrag("09.10. 10-14 Uhr Dreh AB-2026-0001", self.H)
        self.assertEqual((n["von_uhr"], n["bis_uhr"], n["arbeit"], n["auftrag"]), ("10:00", "14:00", "dreh", "AB-2026-0001"))
        self.assertEqual(nachtrag("heute 2,5 h Konzept bei Kiez Alm", self.H)["minuten"], 150)
        self.assertEqual(nachtrag("heute 1:30 h Schnitt", self.H)["minuten"], 90)
        self.assertEqual(nachtrag("28.12. 90 Minuten Meeting", self.H)["datum"], "2025-12-28")     # Vorjahr
        for chat in ("Gestern war schön", "Wie viel Zeit hatte ich gestern?", "gestern 3 h", "Erinner mich morgen"):
            self.assertIsNone(nachtrag(chat, self.H), chat)


class TestTelegramNachtrag(unittest.TestCase):
    def test_4_nur_nach_bestaetigung(self):
        from orchestrator.channels.telegram import bot
        bh, ks, k, ab, nr, z = _setup()
        gesendet = []
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append((m, p))), \
                mock.patch.object(bot, "_zeiterfassung", return_value=z):
            bot._ZEIT_NACHTRAG["abc123"] = nachtrag("gestern 2 Stunden für Brand X", jetzt().date()) | {"firma": k, "auftrag": nr}
            bot._zeit_nachtrag_weiter("T", "1", "abc123", z)                     # Grund fehlt -> Knoepfe
            kb = json.loads(gesendet[-1][1]["reply_markup"])["inline_keyboard"]
            self.assertEqual(kb[0][0]["callback_data"], "ztn:abc123:g:dreh")
            self.assertEqual(z.stundenzettel(nr)["eintraege"], [])               # noch nichts gespeichert
            bot._zeit_nachtrag_klick("T", "1", "ztn:abc123:g:post", 7)
            self.assertIn("Eintragen?", gesendet[-1][1]["text"])
            self.assertEqual(z.stundenzettel(nr)["eintraege"], [])
            bot._zeit_nachtrag_klick("T", "1", "ztn:abc123:ok", 7)
            x = z.stundenzettel(nr)["eintraege"]
            self.assertEqual([(e["minuten"], e["arbeit"], e["quelle"]) for e in x], [(120, "post", "Telegram")])
            self.assertIn("Nachgetragen", gesendet[-1][1]["text"])
            self.assertEqual(bot._zeit_nachtrag_klick("T", "1", "ztn:abc123:ok", 7), "Schon erledigt.")   # kein Doppel
            bot._ZEIT_NACHTRAG["def456"] = nachtrag("gestern 1 h Dreh", jetzt().date()) | {"firma": "", "auftrag": ""}
            bot._zeit_nachtrag_weiter("T", "1", "def456", z)                     # Auftrag fehlt -> Auftragsknoepfe
            self.assertEqual(json.loads(gesendet[-1][1]["reply_markup"])["inline_keyboard"][0][0]["callback_data"], f"ztn:def456:a:{nr}")
            bot._zeit_nachtrag_klick("T", "1", "ztn:def456:no", 8)
        self.assertEqual(len(z.stundenzettel(nr)["eintraege"]), 1)
        self.assertNotIn("def456", bot._ZEIT_NACHTRAG)


if __name__ == "__main__":
    unittest.main()
