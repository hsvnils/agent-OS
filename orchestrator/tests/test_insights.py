import unittest
from datetime import datetime

from orchestrator.core.insights import Insights


class FakeAntraege:
    def list(self, status=None):
        return [
            {"antrag_id": "A-1", "titel": "Newsletter-Tool", "status": "eingereicht"},
            {"antrag_id": "A-2", "titel": "NAS-Backup", "status": "freigegeben"},
            {"antrag_id": "A-3", "titel": "Alt", "status": "erledigt"},
        ]


class FakeResearch:
    def list(self, status=None):
        return [{"ticket_id": "R-1", "frage": "Marktlage", "status": status}] if status == "offen" else []


class FakeAgenda:
    def offene(self):
        return [{"id": "AG-1", "text": "Steuerberater anrufen"}]


class FakeGoogle:
    def __init__(self, ok=True):
        self.ok = ok

    def kalender_agenda(self, tage=7):
        if not self.ok:
            return {"ok": False, "fall_b": True}
        return {"ok": True, "termine": [
            {"id": "e1", "titel": "Team-Call", "start": "2026-06-28T10:00:00"},
            {"id": "e2", "titel": "Morgen", "start": "2026-06-29T09:00:00"},
        ]}

    def neue_mails(self, max_results=10):
        if not self.ok:
            return {"ok": False}
        return {"ok": True, "mails": [{"von": "Partner X", "betreff": "Angebot"},
                                      {"von": "Bank", "betreff": "Kontoauszug"}]}


class TestInsights(unittest.TestCase):
    def test_lagebild_voll(self):
        ins = Insights(antraege=FakeAntraege(), research=FakeResearch(), agenda=FakeAgenda(),
                       google=FakeGoogle())
        d = ins.daten(jetzt=datetime(2026, 6, 28, 8, 0))
        # Entscheidungen: eingereicht zuerst, erledigt nicht enthalten
        self.assertEqual([x["id"] for x in d["entscheidungen"]], ["A-1", "A-2"])
        self.assertEqual(d["entscheidungen"][0]["status"], "eingereicht")
        # Nur der heutige Termin (28.06.)
        self.assertEqual(len(d["termine_heute"]), 1)
        self.assertEqual(d["termine_heute"][0]["zeit"], "10:00")
        self.assertTrue(d["mails"]["verfuegbar"])
        self.assertEqual(d["mails"]["anzahl"], 2)
        text = ins.lagebild(jetzt=datetime(2026, 6, 28, 8, 0))
        self.assertIn("Entscheidung", text)
        self.assertIn("Team-Call", text)

    def test_ohne_google(self):
        ins = Insights(antraege=FakeAntraege())
        d = ins.daten()
        self.assertEqual(d["termine_heute"], [])
        self.assertFalse(d["mails"]["verfuegbar"])
        # Funktioniert trotzdem (interne Stores)
        self.assertEqual(len(d["entscheidungen"]), 2)

    def test_google_fall_b(self):
        ins = Insights(antraege=FakeAntraege(), google=FakeGoogle(ok=False))
        d = ins.daten()
        self.assertEqual(d["termine_heute"], [])
        self.assertFalse(d["mails"]["verfuegbar"])

    def test_leeres_lagebild(self):
        ins = Insights()
        text = ins.lagebild()
        self.assertIn("Keine offenen Entscheidungen", text)


if __name__ == "__main__":
    unittest.main()
