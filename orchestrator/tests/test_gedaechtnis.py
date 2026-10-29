"""Self-Checks JARVIS J8 „Bessere Suche im Gedaechtnis“ -- offline: Fake-Suchmodell, Temp-Verzeichnisse."""
import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import gedaechtnis as g
from orchestrator.core.antraege import Antraege
from orchestrator.core.aufgaben import AufgabenStore
from orchestrator.core.brain import Brain

# Fake-Suchmodell: Bedeutung = Themen-Achsen. „Handy“ und „Mobilfunk“ liegen auf derselben Achse, ohne gemeinsames Wort.
ACHSEN = [("handy", "mobilfunk", "telefon"), ("dreh", "video", "reel"), ("steuer", "finanzamt")]


class FakeEinbetter(g.Einbetter):
    def __init__(self, aus=False):
        super().__init__("http://fake", "fake-modell")
        self.aus, self.aufrufe = aus, 0

    def einbetten(self, texte, *, timeout=None):
        if self.aus:
            return None
        self.aufrufe += 1
        return [[1.0 if any(w in t.lower() for w in achse) else 0.0 for achse in ACHSEN] + [0.01] for t in texte]


def _doc(i, titel, text):
    return {"id": f"x:{i}", "quelle": "x", "ref": str(i), "titel": titel, "text": text, "datum": ""}


DOCS = [_doc(1, "klarmobil GmbH", "Laufende Ausgaben, Kategorie Mobilfunk-Vertrag"),
        _doc(2, "Auftrag Weihnachtsdreh", "Reel fuer Kiez Alm im Dezember"),
        _doc(3, "Steuerbescheid", "Post vom Finanzamt")]


class TestSuche(unittest.TestCase):
    def setUp(self):
        self.ix = g.VektorIndex(Path(tempfile.mkdtemp()) / "gedaechtnis" / "vektoren.json")

    def test_1_bedeutung_findet_ohne_gemeinsames_wort(self):
        frage = "Was zahlen wir fuers Handy?"
        self.assertEqual(g.wortsuche(frage, DOCS), [])                    # Wortsuche allein: nichts
        r = g.suchen(frage, DOCS, index=self.ix, einbetter=FakeEinbetter(), limit=1)
        self.assertEqual((r["modus"], r["treffer"][0]["id"]), ("bedeutung+wort", "x:1"))

    def test_2_suchmodell_aus_faellt_auf_wortsuche_zurueck(self):
        r = g.suchen("Weihnachtsdreh Kiez Alm", DOCS, index=self.ix, einbetter=FakeEinbetter(aus=True))
        self.assertEqual((r["modus"], r["treffer"][0]["id"]), ("wort", "x:2"))
        r = g.suchen("Weihnachtsdreh", DOCS)                               # ganz ohne Suchmodell
        self.assertEqual(r["modus"], "wort")

    def test_3_index_nur_geaenderte_neu_und_weggefallene_raus(self):
        e = FakeEinbetter()
        self.assertEqual(self.ix.aktualisieren(DOCS, e), 3)
        ix2 = g.VektorIndex(self.ix.pfad)                                 # frisch von der Platte
        self.assertEqual(ix2.aktualisieren(DOCS, e), 0)
        neu = [DOCS[0] | {"text": "Kategorie Telefon"}, DOCS[1]]
        self.assertEqual(ix2.aktualisieren(neu, e), 1)
        gespeichert = json.loads(self.ix.pfad.read_text())
        self.assertEqual(sorted(gespeichert["v"]), ["x:1", "x:2"])
        anderes = FakeEinbetter()
        anderes.modell = "anderes-modell"                                 # Modellwechsel -> alles neu
        self.assertEqual(g.VektorIndex(self.ix.pfad).aktualisieren(neu, anderes), 2)

    def test_4_einbetter_aus_der_konfiguration(self):
        e = g.einbetter_aus({"LOCAL_LLM_BASE_URL": "http://192.168.178.184:11434/v1"})
        self.assertEqual((e.url, e.modell), ("http://192.168.178.184:11434", g.MODELL_STANDARD))
        self.assertIsNone(g.einbetter_aus({"LOCAL_LLM_BASE_URL": "http://x:11434/v1", "GEDAECHTNIS": "aus"}))
        self.assertIsNone(g.einbetter_aus({}))
        self.assertEqual(g.einbetter_aus({"GEDAECHTNIS_EMBED_URL": "http://y:1/", "GEDAECHTNIS_MODELL": "m"}).modell, "m")


class TestDokumente(unittest.TestCase):
    def test_1_quellen_und_verworfene_antraege(self):
        root = Path(tempfile.mkdtemp())
        AufgabenStore(root / "todos" / "log.jsonl").anlegen("Steuererklaerung abgeben", faellig="2026-11-02")
        br = Brain(root / "brain" / "log.jsonl")
        br.merken("All-Inkl ist unser Webhoster fuer alle Domains", titel="Hosting")
        an = Antraege(root / "antraege" / "log.jsonl")
        offen = an.stellen("Backup pruefen", "Nachtlauf kontrollieren", von="cto")
        weg = an.stellen("Preismonitoring", "KOSTEN ~5 EUR/Monat", von="cfo")
        an.ablehnen(weg, grund="nicht wichtig")
        docs = g.dokumente(root, brain=br, antraege=an)
        ids = {d["id"] for d in docs}
        self.assertIn(f"antrag:{offen}", ids)
        self.assertNotIn(f"antrag:{weg}", ids)                            # abgelehnte Ideen sind Rauschen
        self.assertEqual({d["quelle"] for d in docs}, {"todo", "wissen", "antrag"})
        todo = next(d for d in docs if d["quelle"] == "todo")
        self.assertIn("faellig 02.11.2026", todo["text"])

    def test_2_geschaeftsdaten_firma(self):
        from orchestrator.core.buchhaltung import Buchhaltung
        from orchestrator.core.kunden import KundenStore
        root = Path(tempfile.mkdtemp())
        KundenStore(Buchhaltung(root / "buchhaltung")).firma_anlegen(
            {"name": "Kiez Alm Gastro GmbH", "ort": "Hamburg", "notiz": "Social-Media-Werbung Saison 2025/26"}, von="test")
        f = [d for d in g.dokumente(root) if d["quelle"] == "firma"]
        self.assertEqual(len(f), 1)
        self.assertIn("Social-Media-Werbung", f[0]["text"])
        self.assertTrue(f[0]["ref"].startswith("K-"))

    def test_3_werkzeug_brain_suchen(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        root = Path(tempfile.mkdtemp())
        AufgabenStore(root / "todos" / "log.jsonl").anlegen("Kiez Alm wegen Weihnachtskampagne anrufen")
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=root, repo_root=root, leak_secrets=[],
                          secret_dict={"GEDAECHTNIS": "aus"})
        out = run_tool("brain_suchen", {"frage": "Weihnachtskampagne Kiez Alm"}, ctx)
        self.assertEqual(out["suche"], "wort")
        self.assertEqual(out["treffer"][0]["quelle"], "todo")


if __name__ == "__main__":
    unittest.main()
