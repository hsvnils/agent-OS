"""Tests fuer den Leistungs-Agenten (CDO): Fenster-Logik, Quoten, Ampeln, Trend, Telegram-Text."""
import unittest
from datetime import datetime, timedelta

from orchestrator.core.performance_agent import PerformanceAgent

JETZT = datetime(2026, 7, 13, 9, 0, 0)          # Montag


def _iso(tage_zurueck: float) -> str:
    return (JETZT - timedelta(days=tage_zurueck)).isoformat(timespec="seconds")


class FakeEvents:
    def __init__(self, events):
        self._evs = events

    def _events(self):
        return self._evs


class FakeCutter:
    def __init__(self, rows):
        self._rows = rows

    def list(self, limit=100):
        return self._rows


class FakeAktivitaet:
    def __init__(self, events):
        self._evs = events

    def seit(self, start):
        return [e for e in self._evs if e["ts"] >= start.isoformat(timespec="seconds")]


def _agent() -> PerformanceAgent:
    reels = FakeEvents([
        {"typ": "einreichen", "id": "a", "ts": _iso(1)},
        {"typ": "einreichen", "id": "b", "ts": _iso(2)},
        {"typ": "status", "id": "a", "status": "freigegeben", "ts": _iso(1)},
        {"typ": "status", "id": "a", "status": "gepostet", "ts": _iso(1)},
        {"typ": "status", "id": "b", "status": "abgelehnt", "ts": _iso(2)},
        {"typ": "einreichen", "id": "alt", "ts": _iso(10)},          # Vorwoche
        {"typ": "status", "id": "alt", "status": "freigegeben", "ts": _iso(10)},
        {"typ": "einreichen", "id": "uralt", "ts": _iso(30)},        # ausserhalb beider Fenster
    ])
    antraege = FakeEvents([
        {"event": "eingereicht", "ts": _iso(3)},
        {"event": "freigegeben", "ts": _iso(3)},
        {"event": "eingereicht", "ts": _iso(4)},
        {"event": "abgelehnt", "ts": _iso(4)},
        {"event": "erledigt", "ts": _iso(2)},
    ])
    cutter = FakeCutter([
        {"status": "done", "updated_at": _iso(1)},
        {"status": "done", "updated_at": _iso(2)},
        {"status": "failed", "updated_at": _iso(3)},
        {"status": "done", "updated_at": _iso(12)},                  # Vorwoche
        {"status": "queued", "updated_at": _iso(1)},                 # zaehlt nicht als done/failed
    ])
    akt = FakeAktivitaet([{"ts": _iso(1), "akteur": "HoA"}, {"ts": _iso(2), "akteur": "HoA"},
                          {"ts": _iso(3), "akteur": "CIO"}, {"ts": _iso(9), "akteur": "HoA"}])
    kosten = FakeEvents([{"ts": _iso(1), "eur": 0.5}, {"ts": _iso(2), "eur": 0.25},
                         {"ts": _iso(9), "eur": 2.0}])
    return PerformanceAgent(reels=reels, antraege=antraege, cutter=cutter, aktivitaet=akt, kosten=kosten)


class TestBericht(unittest.TestCase):
    def setUp(self):
        self.b = _agent().bericht(jetzt=JETZT)

    def test_reels_fenster_und_quote(self):
        r = self.b["woche"]["reels"]
        self.assertEqual(r["erstellt"], 2)                # 'alt'/'uralt' nicht in der Woche
        self.assertEqual(r["freigabequote"], 0.5)          # 1 frei / 1 abgelehnt
        self.assertEqual(r["gepostet"], 1)
        self.assertEqual(self.b["vorwoche"]["reels"]["erstellt"], 1)

    def test_antraege(self):
        a = self.b["woche"]["antraege"]
        self.assertEqual(a["eingereicht"], 2)
        self.assertEqual(a["freigabequote"], 0.5)
        self.assertEqual(a["erledigt"], 1)

    def test_cutter(self):
        c = self.b["woche"]["cutter"]
        self.assertEqual((c["done"], c["failed"]), (2, 1))
        self.assertAlmostEqual(c["erfolgsquote"], 0.667, places=3)

    def test_aktivitaet_und_kosten(self):
        self.assertEqual(self.b["woche"]["aktivitaet"]["aktionen"], 3)
        self.assertEqual(self.b["woche"]["aktivitaet"]["top_akteure"]["HoA"], 2)
        self.assertEqual(self.b["woche"]["kosten"]["eur"], 0.75)
        self.assertEqual(self.b["vorwoche"]["kosten"]["eur"], 2.0)

    def test_ampeln_und_gesamt(self):
        amp = self.b["ampeln"]
        self.assertEqual(amp["reel_qualitaet"], "gelb")    # 50 %
        self.assertEqual(amp["pipeline"], "rot")           # 66,7 % < 70 %
        self.assertEqual(amp["fehler"], "gelb")            # 0 Reel-Fehler + 1 failed
        self.assertEqual(self.b["gesamt"], "rot")          # schlechteste belegte Ampel

    def test_leere_stores_kein_absturz(self):
        b = PerformanceAgent().bericht(jetzt=JETZT)
        self.assertIsNone(b["woche"]["reels"])
        self.assertIsNone(b["gesamt"])
        self.assertEqual(b["fehler_gesamt"], 0)

    def test_text(self):
        txt = _agent().als_text(self.b)
        self.assertIn("Leistungsbericht", txt)
        self.assertIn("Freigabequote 50 %", txt)
        self.assertIn("Fehler gesamt: 1", txt)
        # Leerer Agent liefert trotzdem einen Text (nur Kopf + Fehlerzeile)
        self.assertIn("Leistungsbericht", PerformanceAgent().als_text())


if __name__ == "__main__":
    unittest.main()
