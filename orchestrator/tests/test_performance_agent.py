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


class FakeNutzung:
    def __init__(self, events):
        self._evs = events

    def _events(self):
        return self._evs


def _agent() -> PerformanceAgent:
    reels = FakeEvents([
        {"typ": "einreichen", "id": "a", "ts": _iso(1.5)},
        {"typ": "einreichen", "id": "b", "ts": _iso(2.5)},
        {"typ": "status", "id": "a", "status": "freigegeben", "ts": _iso(1)},   # 12 h nach Einreichen
        {"typ": "status", "id": "a", "status": "gepostet", "ts": _iso(1)},
        {"typ": "status", "id": "b", "status": "abgelehnt", "ts": _iso(2)},     # 12 h nach Einreichen
        {"typ": "einreichen", "id": "alt", "ts": _iso(10)},          # Vorwoche
        {"typ": "status", "id": "alt", "status": "freigegeben", "ts": _iso(10)},
        {"typ": "einreichen", "id": "uralt", "ts": _iso(30)},        # ausserhalb beider Fenster
    ])
    antraege = FakeEvents([
        {"event": "eingereicht", "antrag_id": "x", "ts": _iso(3)},
        {"event": "freigegeben", "antrag_id": "x", "ts": _iso(3)},
        {"event": "eingereicht", "antrag_id": "y", "ts": _iso(4)},
        {"event": "abgelehnt", "antrag_id": "y", "ts": _iso(4)},
        {"event": "erledigt", "antrag_id": "x", "ts": _iso(2)},      # 24 h nach Einreichen
    ])
    cutter = FakeCutter([
        {"status": "done", "created_at": _iso(1.5), "updated_at": _iso(1)},     # 12 h
        {"status": "done", "created_at": _iso(2.25), "updated_at": _iso(2)},    # 6 h -> Median 9 h
        {"status": "failed", "created_at": _iso(3), "updated_at": _iso(3)},
        {"status": "done", "created_at": _iso(12), "updated_at": _iso(12)},     # Vorwoche
        {"status": "queued", "created_at": _iso(1), "updated_at": _iso(1)},     # zaehlt nicht
    ])
    akt = FakeAktivitaet([{"ts": _iso(1), "akteur": "HoA"}, {"ts": _iso(2), "akteur": "HoA"},
                          {"ts": _iso(3), "akteur": "CIO"}, {"ts": _iso(9), "akteur": "HoA"}])
    kosten = FakeEvents([{"ts": _iso(1), "eur": 0.5, "quelle": "hoa"},
                         {"ts": _iso(2), "eur": 0.25, "quelle": "web"},
                         {"ts": _iso(9), "eur": 2.0, "quelle": "hoa"}])
    nutzung = FakeNutzung([{"ts": _iso(1), "app": "investment"}, {"ts": _iso(2), "app": "investment"},
                           {"ts": _iso(3), "app": "cutter"}, {"ts": _iso(40), "app": "wissen"}])
    return PerformanceAgent(reels=reels, antraege=antraege, cutter=cutter, aktivitaet=akt, kosten=kosten,
                            nutzung=nutzung, apps=("investment", "cutter", "wissen", "team"))


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

    def test_reaktionszeiten(self):
        rz = self.b["woche"]["reaktionszeiten"]
        self.assertEqual(rz["cutter_h"], 9.0)              # Median aus 12 h und 6 h
        self.assertEqual(rz["antrag_h"], 24.0)
        self.assertEqual(rz["reel_entscheidung_h"], 12.0)

    def test_kosten_treiber(self):
        top = self.b["woche"]["kosten"]["top_quellen"]
        self.assertEqual(top, {"hoa": 0.5, "web": 0.25})   # nur Woche, nach EUR sortiert

    def test_nutzung_und_friedhof(self):
        n = self.b["woche"]["nutzung"]
        self.assertEqual(n["oeffnungen"], 3)               # wissen (40 Tage alt) nicht in der Woche
        self.assertEqual(n["je_app"]["investment"], 2)
        self.assertEqual(self.b["friedhof"], ["team", "wissen"])   # > 28 Tage nicht geoeffnet

    def test_friedhof_ohne_nutzungsdaten(self):
        b = PerformanceAgent(nutzung=FakeNutzung([])).bericht(jetzt=JETZT)
        self.assertIsNone(b["friedhof"])                   # keine Daten -> nichts faelschlich brachliegend

    def test_friedhof_junges_logging(self):
        """Logging juenger als 28 Tage -> KEIN Friedhof (sonst waere anfangs alles 'brachliegend')."""
        b = PerformanceAgent(nutzung=FakeNutzung([{"ts": _iso(2), "app": "investment"}]),
                             apps=("investment", "team")).bericht(jetzt=JETZT)
        self.assertIsNone(b["friedhof"])

    def test_historie(self):
        h = _agent().historie(wochen=3, jetzt=JETZT)
        self.assertEqual(len(h), 3)
        self.assertEqual(h[-1]["reels_erstellt"], 2)       # juengste Woche zuletzt
        self.assertEqual(h[-2]["reels_erstellt"], 1)       # Vorwoche
        self.assertEqual(h[-1]["fehler"], 1)
        self.assertEqual(h[-1]["kosten_eur"], 0.75)

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
