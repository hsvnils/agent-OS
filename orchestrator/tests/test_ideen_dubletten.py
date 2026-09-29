"""BETRIEB_ROADMAP Etappe 1 (CEO-Go 2026-09-29): Ideen-Laeufe reichen kein Thema zweimal ein -- Vergleich gegen alle
bisherigen Antraege (auch abgelehnte), kalibriert an den echten Titeln Juni–September 2026; Selbst-Entwicklung laeuft
woechentlich."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from orchestrator.core.antraege import Antraege
from orchestrator.core.innovation import InnovationPipeline, finde_dublette
from orchestrator.core.self_development import SelfDevelopment, selfdev_wochentag

DUBLETTEN = [  # (frueher, spaeter) -- echte Wiederholungen aus dem Antrags-Store
    ("Etablierung eines zentralen Infrastruktur-Monitorings", "Einführung eines zentralen Infrastruktur-Monitorings"),
    ("Etablierung eines zentralen Infrastruktur-Monitorings",
     "Implementierung eines zentralen Infrastruktur-Monitorings und Alerting-Systems"),
    ("Aufbau eines zentralen Technik-Inventars", "Etablierung eines zentralen technischen Infrastruktur-Inventars"),
    ("Standardisierung des Richtwerts je 1.000 Follower.", "Festlegung des CEO-Richtwerts pro 1.000 Follower"),
    ("Aktivierung des Research-Agenten", "Implementierung eines dedizierten Research-Agenten."),
    ("Etablierung eines direkten Nutzer-Feedback-Kanals", "Einführung eines systematischen Nutzer-Feedback-Kanals"),
    ("Einführung eines zentralen Registers für Secrets und Zugriffsrechte",
     "Etablierung eines zentralen Secrets- und Zugriffs-Inventory"),
]
KEINE = [  # verschiedene Themen -- duerfen nicht als Dublette gelten
    ("Investment Agent: Research statt Ausführung – technisch erzwungenes Mandat", "Aktivierung des Research-Agenten"),
    ("Investment Agent: Research statt Ausführung – technisch erzwungenes Mandat", "Zentrales Agenten-Mandatsregister"),
    ("Kosten-Sammler: Verbrauchsdaten automatisch ziehen statt manuell erfassen", "Aktivierung des Research-Agenten"),
    ("Einführung von Data Storytelling zur strategischen Entscheidungsunterstützung",
     "Einführung eines zentralen Infrastruktur-Monitorings"),
    ("Pilotprojekt Vektordatenbank zur verbesserten Datenintegration", "Implementierung des Daten-Ingest-Agenten"),
]


def _antrag(titel, status="abgelehnt", aid="A-1"):
    return {"antrag_id": aid, "titel": titel, "status": status}


class _Backend:
    """Fachagenten-Antworten je Agent; zaehlt die Aufrufe (CTO/CFO duerfen bei Dubletten nicht laufen)."""
    def __init__(self, idee):
        self.idee, self.aufrufe = idee, []
    def respond(self, agent, system, prompt, ctx):
        self.aufrufe.append(agent)
        return {"cto": "machbar, klein", "cfo": "KOSTEN: 0 EUR einmalig, 0 EUR/Monat"}.get(agent, self.idee)


def _core(idee):
    return SimpleNamespace(backend=_Backend(idee), subagents={})


class TestDublettenVergleich(unittest.TestCase):
    def test_1_echte_wiederholungen_werden_erkannt(self):
        for alt, neu in DUBLETTEN:
            with self.subTest(neu=neu):
                self.assertIsNotNone(finde_dublette(neu, [_antrag(alt)]))

    def test_2_verschiedene_themen_nicht(self):
        for alt, neu in KEINE:
            with self.subTest(neu=neu):
                self.assertIsNone(finde_dublette(neu, [_antrag(alt)]))

    def test_3_fehler_antraege_zaehlen_nicht(self):
        fehler = _antrag("(nicht verfügbar — Modell/Backend-Fehler: Modellaufruf fuer 'cto' fehlgeschlagen)")
        self.assertIsNone(finde_dublette("Modellaufruf Fehler fehlgeschlagen beheben", [fehler]))


class TestPipeline(unittest.TestCase):
    def _store(self, *titel_status):
        st = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl")
        for titel, status in titel_status:
            aid = st.stellen(titel, "x", von="cto (Selbst-Entwicklung)", kategorie="Innovation/Beschaffung (Kosten pruefen)")
            if status == "abgelehnt":
                st.ablehnen(aid, grund="bereits umgesetzt")
        return st

    def test_1_abgelehntes_thema_kommt_nicht_wieder(self):
        st = self._store(("Etablierung eines zentralen Infrastruktur-Monitorings", "abgelehnt"))
        core = _core("Einführung eines zentralen Infrastruktur-Monitorings\nDamit Ausfaelle frueh auffallen.")
        erg = InnovationPipeline(core, antraege=st).run("Infrastruktur", abteilung="cdo", wissen="x")
        self.assertIsNone(erg.antrag_id)
        self.assertEqual(erg.dublette["status"], "abgelehnt")
        self.assertEqual(core.backend.aufrufe, ["cdo"])                     # nur die Idee, keine CTO/CFO-Bewertung
        self.assertEqual(len(st.list()), 1)

    def test_2_neues_thema_wird_eingereicht(self):
        st = self._store(("Etablierung eines zentralen Infrastruktur-Monitorings", "abgelehnt"))
        core = _core("Automatische Untertitel fuer Reels\nMehr Reichweite ohne Ton.")
        erg = InnovationPipeline(core, antraege=st).run("Content", abteilung="cco", wissen="x")
        self.assertIsNotNone(erg.antrag_id)
        self.assertIsNone(erg.dublette)
        self.assertEqual(len(st.list()), 2)

    def test_3_selbstentwicklung_meldet_nichts_bei_dublette(self):
        st = self._store(("Aktivierung des Research-Agenten", "abgelehnt"))
        meldungen = []
        sd = SelfDevelopment(_core("Implementierung eines dedizierten Research-Agenten\nFuer bessere Recherche."),
                             antraege=st, notify=lambda *a, **k: meldungen.append(a))
        erg = sd.vorschlag_fuer("cco")
        self.assertIsNone(erg.antrag_id)
        self.assertIn("Thema schon beantragt", erg.hinweis)
        self.assertEqual(meldungen, [])


class TestWochentakt(unittest.TestCase):
    def test_wochentag(self):
        self.assertEqual([selfdev_wochentag(x) for x in (None, "", "mo", "Mittwoch", "so", "4", "9", "quatsch")],
                         [0, 0, 0, 2, 6, 4, 0, 0])


if __name__ == "__main__":
    unittest.main()
