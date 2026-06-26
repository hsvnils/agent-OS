"""Self-Checks zentrales Agenten-Aktivitaetsprotokoll (Antrag adc5) -- offline, ohne Netz."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.aktivitaet import Aktivitaet
from orchestrator.core.antraege import Antraege
from orchestrator.core.backends import MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.subagents import load_all_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate

ROOT = Path(__file__).resolve().parents[2]


def _store():
    return Aktivitaet(Path(tempfile.mkdtemp()) / "ak.jsonl")


class TestAktivitaet(unittest.TestCase):
    def test_1_log_und_letzte_neueste_zuerst(self):
        ak = _store()
        ak.log("cfo", "Kostenpruefung gestartet", kategorie="aktion")
        ak.log("CEO", "Antrag freigegeben", kategorie="governance", bezug="A-1")
        letzte = ak.letzte(10)
        self.assertEqual(letzte[0]["akteur"], "CEO")          # neueste zuerst
        self.assertEqual(letzte[0]["bezug"], "A-1")
        self.assertEqual(len(letzte), 2)

    def test_2_filter_akteur(self):
        ak = _store()
        ak.log("cfo", "A")
        ak.log("cto", "B")
        nur_cfo = ak.letzte(10, akteur="cfo")
        self.assertEqual(len(nur_cfo), 1)
        self.assertEqual(nur_cfo[0]["akteur"], "cfo")

    def test_3_leerer_eintrag_ignoriert(self):
        self.assertEqual(_store().log("   ", "  "), "")

    def test_4_zusammenfassung_zaehlt(self):
        ak = _store()
        ak.log("cfo", "x", kategorie="governance")
        ak.log("cfo", "y", kategorie="aktion")
        ak.log("cto", "z", kategorie="governance")
        z = ak.zusammenfassung(stunden=24)
        self.assertEqual(z["gesamt"], 3)
        self.assertEqual(z["je_akteur"]["cfo"], 2)
        self.assertEqual(z["je_kategorie"]["governance"], 2)

    def test_5_leck_schutz(self):
        secret = "sk-ant-GEHEIMWERT12345"
        ak = Aktivitaet(Path(tempfile.mkdtemp()) / "ak.jsonl", secrets=[secret])
        ak.log("it", f"Key benutzt {secret}", detail=f"wert {secret}")
        e = ak.letzte(1)[0]
        self.assertNotIn(secret, e["aktion"])

    def test_6_durable(self):
        path = Path(tempfile.mkdtemp()) / "ak.jsonl"
        Aktivitaet(path).log("ceo", "bleibt")
        self.assertEqual(len(Aktivitaet(path).letzte(10)), 1)   # ueberlebt Neustart

    def test_7_changelog_wrapper_speist_protokoll(self):
        """Zentrale Wiring-Idee: Antrags-Lebenszyklus ueber den Changelog-Callback landet im Protokoll."""
        ak = _store()

        def changelog(actor, was, warum="", betroffen=""):
            ak.log(actor, was, kategorie="governance", detail=warum, bezug=betroffen)

        antraege = Antraege(Path(tempfile.mkdtemp()) / "a.jsonl", changelog=changelog)
        aid = antraege.stellen("Testantrag", "x", von="cfo")
        antraege.freigeben(aid)
        eintraege = ak.letzte(10)
        self.assertTrue(any(aid in (e.get("bezug", "") or "") for e in eintraege))
        self.assertTrue(any("freigegeben" in (e.get("aktion", "") or "").lower() for e in eintraege))

    def test_8_tool_registriert_und_dispatch(self):
        self.assertIn("aktivitaet_protokoll", {t["name"] for t in tool_specs()})
        ak = _store()
        ak.log("cfo", "Kostenpruefung", kategorie="aktion", bezug="K-1")
        ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                          antraege=Antraege(Path(tempfile.mkdtemp()) / "a.jsonl"), engine=None,
                          finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=[], aktivitaet=ak)
        r = run_tool("aktivitaet_protokoll", {"anzahl": "5"}, ctx)
        self.assertEqual(len(r["eintraege"]), 1)
        self.assertEqual(r["eintraege"][0]["akteur"], "cfo")
        self.assertEqual(r["zusammenfassung_24h"]["gesamt"], 1)

    def test_9_seit_zeitfenster(self):
        ak = _store()
        ak.log("cfo", "neu")
        self.assertEqual(len(ak.seit(datetime.now() - timedelta(hours=1))), 1)
        self.assertEqual(len(ak.seit(datetime.now() + timedelta(hours=1))), 0)


if __name__ == "__main__":
    unittest.main()
