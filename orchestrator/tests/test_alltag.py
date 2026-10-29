"""JARVIS_ALLTAG Paket A: J1 Sprachnachrichten (Fehler nie als Text), J2 Sprechfassung des Briefings, J3 Abfahrts-
Erinnerung (Puffer, einmal je Termin, nur mit Ort), J4 Kundenpflege (Kontakt, Geburtstag, Jahrestag, erledigt)."""
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from orchestrator.core import alltag
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.tests.test_angebote import _stores

J = datetime(2026, 10, 28, 9, 0)


class TestSprechfassung(unittest.TestCase):
    def test_1_symbole_kennungen_links_weg(self):
        t = ("☀️ Guten Morgen!\n- 📅 10:00 Dreh bei Kiez Alm\n  - CTO: Update fertig  (#a1b2)\nhttps://x.de/y\n"
             "Nachts von den Agenten (Details: „zeig #xxxx\"):")
        s = alltag.sprechfassung(t)
        self.assertEqual(s, "Guten Morgen! 10:00 Dreh bei Kiez Alm. CTO: Update fertig. Nachts von den Agenten.")

    def test_2_kuerzen_an_satzgrenze(self):
        s = alltag.sprechfassung("\n".join(f"Punkt {i} ist erledigt" for i in range(400)), max_zeichen=300)
        self.assertLessEqual(len(s), 300 + 40)
        self.assertTrue(s.endswith("Den Rest findest du im Briefing-Text."))
        self.assertIn("erledigt. Den Rest", s)


class TestAbfahrt(unittest.TestCase):
    T = [{"id": "e1", "titel": "Dreh Kiez Alm", "start": "2026-10-28T11:00:00+01:00", "ort": "Reeperbahn 1, 20359 Hamburg"},
         {"id": "e2", "titel": "Call", "start": "2026-10-28T11:30:00+01:00", "ort": "Zoom https://zoom.us/j/1"},
         {"id": "e3", "titel": "Ganztags", "start": "2026-10-28", "ort": "Hamburg Messe"},
         {"id": "e4", "titel": "Morgen", "start": "2026-10-29T11:00:00+01:00", "ort": "Reeperbahn 1, Hamburg"}]

    def faellig(self, jetzt_, gesendet=()):
        return alltag.faellige_abfahrten(self.T, jetzt_, lambda ort: 40.0, lambda s: s in gesendet)

    def test_1_puffer_und_zeitpunkt(self):
        self.assertEqual(alltag.abfahrt(datetime(2026, 10, 28, 11, 0), 40), datetime(2026, 10, 28, 10, 10))   # 40+10 Min.
        self.assertEqual(alltag.abfahrt(datetime(2026, 10, 28, 11, 0), 100), datetime(2026, 10, 28, 9, 5))   # 100+15 Min.
        self.assertEqual(self.faellig(datetime(2026, 10, 28, 9, 59)), [])                                  # zu frueh
        x = self.faellig(datetime(2026, 10, 28, 10, 0))
        self.assertEqual([y["titel"] for y in x], ["Dreh Kiez Alm"])                                       # nur mit echtem Ort
        self.assertIn("in 10 Min. losfahren", alltag.abfahrt_text(x[0], datetime(2026, 10, 28, 10, 0)))
        self.assertIn("google.com/maps/dir", alltag.abfahrt_text(x[0], datetime(2026, 10, 28, 10, 0)))

    def test_2_einmal_und_nicht_nach_beginn(self):
        x = self.faellig(datetime(2026, 10, 28, 10, 5))
        self.assertEqual(self.faellig(datetime(2026, 10, 28, 10, 6), gesendet={x[0]["schluessel"]}), [])
        self.assertEqual(self.faellig(datetime(2026, 10, 28, 11, 1)), [])
        self.assertIsNone(alltag._zeit("2026-10-28"))
        self.assertFalse(alltag.braucht_fahrt("Teams-Meeting"))
        self.assertTrue(alltag.braucht_fahrt("Hafenstr. 1, Hamburg"))

    def test_3_ohne_route_keine_erinnerung(self):
        self.assertEqual(alltag.faellige_abfahrten(self.T, datetime(2026, 10, 28, 10, 30), lambda o: None, lambda s: False), [])


class TestKundenpflege(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, self.st, self.k, self.ap = _stores()
        an = self.st.anlegen({"firma": self.k, "titel": "Herbst", "positionen": [{"beschreibung": "Reel", "einzelpreis": "100"}]})["nummer"]
        self.st.status_setzen(an, "versendet"); self.st.status_setzen(an, "angenommen")
        self.nr = AuftragBuch(self.bh, self.ks, self.st).aus_angebot(an, leistung_von=jetzt().date().isoformat())["nummer"]

    def hinweise(self, heute, tage=60):
        return alltag.kundenpflege(self.bh.eintraege(), [self.ks.firma(f["nummer"]) for f in self.ks.firmen()], heute, tage=tage)

    def test_1_lange_kein_kontakt_und_erledigt(self):
        heute = jetzt().date()
        self.assertEqual([h for h in self.hinweise(heute + timedelta(days=59)) if h["art"] == "kontakt"], [])
        h = [x for x in self.hinweise(heute + timedelta(days=61)) if x["art"] == "kontakt"]
        self.assertEqual(len(h), 1)
        self.assertIn("vor 61 Tagen", h[0]["detail"])
        self.bh.erfassen("kundenpflege_erledigt", {"schluessel": h[0]["id"], "firma": self.k})   # gemeldet = Kontakt
        self.assertEqual([x for x in self.hinweise(heute + timedelta(days=61)) if x["art"] == "kontakt"], [])

    def test_2_geburtstag(self):
        heute = jetzt().date()
        tag = heute + timedelta(days=2)
        self.ks.ansprechpartner_aendern(self.ap, {"geburtstag": f"{tag:%d.%m.}1990"})
        g = [x for x in self.hinweise(heute) if x["art"] == "geburtstag"]
        self.assertEqual(len(g), 1)
        self.assertIn("Anna Muster", g[0]["titel"])
        self.assertEqual([x for x in self.hinweise(heute - timedelta(days=5)) if x["art"] == "geburtstag"], [])
        with self.assertRaisesRegex(ValueError, "Geburtstag"):
            self.ks.ansprechpartner_aendern(self.ap, {"geburtstag": "irgendwann"})
        self.assertEqual(alltag.geburtstag("1990-12-24"), (12, 24))
        self.assertIsNone(alltag.geburtstag("31.13."))

    def test_3_jahrestag(self):
        heute = jetzt().date()
        nae = [x for x in self.hinweise(heute + timedelta(days=366)) if x["art"] == "jahrestag"]
        self.assertEqual([x["id"] for x in nae], [f"kp-jahrestag:{self.nr}"])
        self.assertEqual([x for x in self.hinweise(heute + timedelta(days=200)) if x["art"] == "jahrestag"], [])

    def test_4_im_handlungsbedarf_und_abschaltbar(self):
        from orchestrator.core.todos import geschaefts_todos
        ids = {t["id"] for t in geschaefts_todos(self.bh, self.ks, heute=jetzt().date() + timedelta(days=70))}
        self.assertTrue(any(i.startswith("kp-kontakt:") for i in ids))
        from orchestrator.investment.store import InvestmentStore
        InvestmentStore(self.bh.dir.parent / "investment" / "log.jsonl").set_setting("kundenpflege_tage", 0)
        ids = {t["id"] for t in geschaefts_todos(self.bh, self.ks, heute=jetzt().date() + timedelta(days=70))}
        self.assertFalse(any(i.startswith("kp-") for i in ids))


class TestSprachErgaenzung(unittest.TestCase):
    """J2c: vier Bloecke statt alles vorlesen -- Begruessung, der Tag, wichtig heute (hoechstens 3), nur Zahlen."""
    T = [{"start": "2026-10-29T15:30:00+01:00", "titel": "Call", "ort": "Zoom"},
         {"start": "2026-10-29T11:00:00+01:00", "titel": "Dreh bei Kiez Alm", "ort": "Spielbudenplatz 1, 20359 Hamburg"},
         {"start": "2026-10-29", "titel": "Feiertag"}, {"start": "2026-10-30T09:00:00+01:00", "titel": "Morgen"}]

    def test_1_vier_bloecke(self):
        s = alltag.sprach_ergaenzung(datetime(2026, 10, 29, 8, 1), termine=self.T, fahrzeit=lambda ort: 25,
                                     wichtig=["Rechnung überfällig für Kiez Alm Gastro GmbH", "B", "C", "D", "E"],
                                     zahlen=[(12, "ein Antrag wartet auf dich", "Anträge warten auf dich"),
                                             (1, "ein offenes Research-Ticket", "offene Research-Tickets"), (0, "x", "y")])
        self.assertEqual(s, "Guten Morgen, Nils. Heute ist Donnerstag, der 29. Oktober. Heute hast du 3 Termine. "
                            "Der nächste: um 11 Uhr Dreh bei Kiez Alm, losfahren um 10 Uhr 25. "
                            "Wichtig heute: Rechnung überfällig für Kiez Alm Gastro GmbH. B. C. "
                            "Dazu kommen 2 weitere Punkte unter Zu erledigen. "
                            "Außerdem: 12 Anträge warten auf dich, ein offenes Research-Ticket. Die Details stehen im Text.")

    def test_2_leerer_tag_und_online_termin(self):
        self.assertEqual(alltag.sprach_ergaenzung(datetime(2026, 11, 2, 8, 0), name="Nils"),
                         "Guten Morgen, Nils. Heute ist Montag, der 2. November. Im Kalender steht heute nichts. "
                         "Dringend ist heute nichts. Die Details stehen im Text.")
        s = alltag.sprach_ergaenzung(datetime(2026, 10, 29, 12, 0), termine=self.T[:1], fahrzeit=lambda ort: 25)
        self.assertIn("Heute hast du einen Termin: um 15 Uhr 30 Call.", s)         # Online -> keine Abfahrt
        s = alltag.sprach_ergaenzung(datetime(2026, 10, 29, 8, 0), termine=self.T[2:3])
        self.assertIn("Heute hast du einen Termin, ganztägig.", s)
        s = alltag.sprach_ergaenzung(datetime(2026, 10, 29, 8, 0), kalender_ok=False)
        self.assertIn("Den Kalender konnte ich heute nicht lesen.", s)
        self.assertNotIn("Im Kalender steht heute nichts", s)

    def test_3_sprechpunkt_ohne_belegnummer(self):
        self.assertEqual(alltag.sprechpunkt("Angebot AN-2026-0012 nachfassen", "Hafenbar · Herbstkampagne"),
                         "Angebot nachfassen für Hafenbar")
        self.assertEqual(alltag.sprechpunkt("Rechnung RE-2026-0007 überfällig", "Kiez Alm Gastro GmbH; Zahlungserinnerung "
                                            "oder Mahnstufe 1 erstellen"), "Rechnung überfällig für Kiez Alm Gastro GmbH")
        self.assertEqual(alltag.sprechpunkt("Kontoauszug 10/2026 abgleichen", "Monat noch offen, 3 Buchungen"),
                         "Kontoauszug 10/2026 abgleichen")                     # Detail mit Zahlen -> kein Anhaengsel
        self.assertEqual(alltag.sprechpunkt("🎂 Geburtstag: Anna Muster", "Kiez Alm"), "Geburtstag: Anna Muster für Kiez Alm")


class TestSprachnachricht(unittest.TestCase):
    def test_1_fehler_wird_nie_text(self):
        from orchestrator.channels.telegram import bot
        with mock.patch.object(bot.urllib.request, "urlopen", side_effect=OSError("kaputt")):
            self.assertEqual(bot._transcribe(b"ogg", "key"), "")


if __name__ == "__main__":
    unittest.main()
