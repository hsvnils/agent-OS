"""FACHAGENTEN_ROUTING R1-R4: Zustaendigkeitskarte vollstaendig und im Blick des Modells, Routing-Regel im System-Prompt,
Geschaeftsregeln lesbar ohne Kunden-/Rechnungsdaten, Werkzeug-Antworten zaehlen beim zustaendigen Bereich, Sachfragen
ohne Abteilungsnamen bekommen das noetige Werkzeug angeboten."""
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core import werkzeugauswahl as w
from orchestrator.core.agenten_profil import AgentenNutzung
from orchestrator.core.backends import MockBackend
from orchestrator.core.buchhaltung import Buchhaltung
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_conversation import TEXT_SYSTEM_PROMPT
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.kunden import KundenStore
from orchestrator.core.subagents import ALL_AGENT_CHARTERS, load_all_subagents
from orchestrator.core.vertraege import VertragStore
from orchestrator.core.zustaendigkeit import (ROUTING_REGEL, WERKZEUG_BEREICH, bereich_von,
                                              geschaeftsregeln, pruefe_vollstaendig)
from orchestrator.governance.ceo_gate_hook import CeoGate

REPO = Path(__file__).resolve().parents[2]

# R4: Sachfragen ohne Abteilungsnamen -> (noetiges Werkzeug, zustaendiger Bereich)
SACHFRAGEN = [
    ("Wie hoch ist das monatliche Budget?", "frage_finance", "cfo"),
    ("Wie sind unsere aktuellen Zahlungsbedingungen?", "geschaeftsregeln", "cfo"),
    ("Wie lange hat ein Kunde Zeit, eine Rechnung zu bezahlen?", "geschaeftsregeln", "cfo"),
    ("Verlangen wir eine Anzahlung?", "geschaeftsregeln", "cfo"),
    ("Was kostet bei uns ein Reel?", "geschaeftsregeln", "cfo"),
    ("Welche Verzugszinsen duerfen wir verlangen?", "geschaeftsregeln", "cfo"),   # Probelauf: delegate->clo auch ok
    ("Was rechnen wir pro Projektstunde ab?", "geschaeftsregeln", "cfo"),
    ("Darf ich im Reel Musik aus den Charts nutzen?", "delegate", "clo"),
    ("Muss ich bei einem bezahlten Post Werbung drueberschreiben?", "delegate", "clo"),
    ("Worauf sollten wir achten, damit unsere Projektberichte bei Kunden gut ankommen?", "delegate", "cxo"),
    ("Was kostet uns ein Kameramann pro Tag?", "delegate", "chro"),
    ("Welche Zugaenge sollten wir mal pruefen?", "delegate", "ciso"),
    ("Hast du eine Idee fuer einen Hook zum Derby?", "delegate", "cco"),
    ("Wie lief die letzte Kampagne im Vergleich zur vorigen?", "delegate", "cdo"),
    ("Wann laufen unsere Versicherungen aus?", "delegate", "cao"),
    ("Wie fassen wir bei einem Angebot ohne Antwort nach?", "delegate", "cro"),
    ("Lohnt sich ein zweiter Kanal fuer uns?", "delegate", "berater"),
    ("Warum laedt die Seite auf dem Handy so langsam?", "delegate", "cto"),
    ("Wie sollten wir als Marke klingen, eher frech oder serioes?", "delegate", "cbo"),
    ("Findest du im Archiv eine Choreo-Szene vom letzten Heimspiel?", "delegate", "cko"),
]


class TestR1Karte(unittest.TestCase):
    def test_1_karte_vollstaendig_und_in_delegate(self):
        self.assertEqual(pruefe_vollstaendig(), [])
        d = next(t for t in tool_specs() if t["name"] == "delegate")["description"]
        for k in ALL_AGENT_CHARTERS:
            self.assertIn(f"{k}=", d)

    def test_2_routing_regel_im_system_prompt(self):
        self.assertIn(ROUTING_REGEL, TEXT_SYSTEM_PROMPT)
        self.assertIn("nennt nie eine Abteilung", TEXT_SYSTEM_PROMPT)


class TestR2Geschaeftsregeln(unittest.TestCase):
    def setUp(self):
        self.bh = Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")
        ks = KundenStore(self.bh)
        k = ks.firma_anlegen({"name": "Kiez Alm Gastro GmbH", "strasse": "Hafenstr. 1", "plz": "20095", "ort": "Hamburg",
                              "rechnungsmail": "rechnung@kiezalm.example", "zahlungsziel_tage": 30})["nummer"]
        ks.ansprechpartner_anlegen(k, {"vorname": "Anna", "nachname": "Muster", "mail": "anna@kiezalm.example"})

    def test_1_regeln_ohne_personenbezug(self):
        r = geschaeftsregeln(self.bh)
        self.assertEqual(r["zahlungsbedingungen"]["zahlungsziel_standard_tage"], 14)
        self.assertEqual(r["mahnwesen"]["pauschale_unternehmer"], "40,00 €")
        self.assertTrue(any(f["name"].startswith("Reel") for f in r["katalog"]["formate"]))
        self.assertIn("keine AGB-Fassung in Kraft", r["agb"]["status"])
        roh = json.dumps(r, ensure_ascii=False)
        for privat in ("Kiez Alm", "kiezalm", "Muster", "Hafenstr", "K-0"):
            self.assertNotIn(privat, roh)

    def test_2_thema_und_agb_in_kraft(self):
        self.assertEqual(set(geschaeftsregeln(self.bh, "katalog")) - {"hinweis"}, {"katalog"})
        vs = VertragStore(self.bh)
        vs.version_anlegen("agb", titel="AGB", paragraphen=[{"titel": "§ 5 Zahlung", "text": "Zahlbar in 14 Tagen."},
                                                            {"titel": "§ 1 Geltung", "text": "B2B."}])
        vs.status_setzen("agb", 1, "geprueft", pruefer="Anwaeltin", datum="2026-10-05")
        a = geschaeftsregeln(self.bh, "agb")["agb"]
        self.assertEqual((a["status"], [p["titel"] for p in a["zahlungsparagraphen"]]), ("in Kraft", ["§ 5 Zahlung"]))

    def test_3_werkzeug(self):
        core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate(), leak_secrets=[])
        ctx = ToolContext(core=core, antraege=None, engine=None, finance_dir=REPO / "finance",
                          repo_root=self.bh.dir.parent, leak_secrets=[])
        r = run_tool("geschaeftsregeln", {"thema": "zahlung"}, ctx)
        self.assertIn("zahlungsbedingungen", r)
        self.assertNotIn("katalog", r)


class TestR3Zaehlung(unittest.TestCase):
    def test_1_jedes_werkzeug_hat_gueltigen_bereich(self):
        namen = {t["name"] for t in tool_specs()}
        self.assertEqual(sorted(set(WERKZEUG_BEREICH) - namen), [])            # nur echte Werkzeuge
        self.assertTrue(all(bereich_von(n) in set(ALL_AGENT_CHARTERS) | {"hoa"} for n in namen))
        self.assertEqual((bereich_von("frage_finance"), bereich_von("kalender_agenda")), ("cfo", "hoa"))

    def test_2_werkzeug_zaehlt_beim_bereich_delegate_einmal(self):
        n = AgentenNutzung(Path(tempfile.mkdtemp()) / "log.jsonl")
        core = HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate(), leak_secrets=[])
        ctx = ToolContext(core=core, antraege=None, engine=None, finance_dir=REPO / "finance", repo_root=REPO,
                          leak_secrets=[], agenten_nutzung=n)
        run_tool("frage_finance", {"frage": "Budget?"}, ctx)
        run_tool("delegate", {"an": "clo", "aufgabe": "Musik im Reel?"}, ctx)
        run_tool("notiz_hinzufuegen", {"text": "x"}, ctx)                       # LUNA selbst -> zaehlt nicht
        z = n.zaehlen(datetime.now() - timedelta(days=1))
        self.assertEqual({k: (v["direkt"], v["werkzeug"]) for k, v in z.items()}, {"cfo": (0, 1), "clo": (1, 0)})
        self.assertNotIn("Budget", n.path.read_text(encoding="utf-8"))          # keine Inhalte


class TestR4Sachfragen(unittest.TestCase):
    def test_1_noetiges_werkzeug_wird_angeboten(self):
        fehlt = [(f, wz) for f, wz, _ in SACHFRAGEN if wz not in w.auswahl(f)[0]]
        self.assertEqual(fehlt, [])

    def test_2_fragen_ohne_abteilungsnamen_und_breit(self):
        """CEO-Vorgabe: Sachfragen nennen nie eine Abteilung. Ob das Modell richtig zuordnet, misst der Probelauf
        (`scripts/routing_probelauf.py`, ueber Gemini) -- offline pruefbar ist nur das Angebot der Werkzeuge (test_1)."""
        namen = re.compile(r"\b(" + "|".join(list(ALL_AGENT_CHARTERS) + ["researcher", "luna", "abteilung", "agent"]) + r")\b", re.I)
        self.assertEqual([f for f, _, _ in SACHFRAGEN if namen.search(f)], [])
        self.assertGreaterEqual(len({b for _, _, b in SACHFRAGEN}), 12)
        self.assertEqual(len(SACHFRAGEN), 20)

if __name__ == "__main__":
    unittest.main()
