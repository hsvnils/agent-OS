import tempfile
import unittest
from pathlib import Path

from orchestrator.core.content_feed import ContentFeed
from orchestrator.core.content_store import (ContentStore, DRAFT_FELDER, DRAFT_STATUSES, IDEA_FELDER,
                                             IDEA_STATUSES, TREND_FELDER, TREND_STATUSES)
from orchestrator.core.research_tickets import ResearchTickets
from orchestrator.core.scheduler import WatchStore
from orchestrator.governance.supabase import MockSupabaseClient
from orchestrator.governance.web_research import RechercheErgebnis, Treffer


class FakeWeb:
    """Deterministische Web-Recherche: liefert je Thema feste Treffer (kein Netz, keine Kosten)."""

    def __init__(self, treffer_je_thema, ok=True):
        self._map = treffer_je_thema
        self._ok = ok

    def recherchiere(self, thema, **kw):
        return RechercheErgebnis(ok=self._ok, provider="fake", treffer=list(self._map.get(thema, [])))


class _Spec:
    system_prompt = ""


class FakeCore:
    """Minimales HeadOfAgents-Double: backend.respond gibt eine feste Antwort, subagents.get einen Spec."""

    def __init__(self, antwort=""):
        self.antwort = antwort
        self.calls = []
        outer = self

        class _Backend:
            def respond(self, key, system, prompt, meta):
                outer.calls.append((key, prompt))
                return outer.antwort

        class _Subs:
            def get(self, key):
                return _Spec()

        self.backend = _Backend()
        self.subagents = _Subs()


class TestContentFeed(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cache = Path(self.dir.name) / "trends.jsonl"
        self.mock = MockSupabaseClient()
        self.trends = ContentStore(self.mock, "trend_signals", TREND_FELDER, self.cache,
                                   statuses=TREND_STATUSES)

    def tearDown(self):
        self.dir.cleanup()

    def _ideas(self):
        return ContentStore(self.mock, "ideas", IDEA_FELDER, Path(self.dir.name) / "ideas.jsonl",
                            statuses=IDEA_STATUSES)

    def _drafts(self):
        return ContentStore(self.mock, "content_drafts", DRAFT_FELDER, Path(self.dir.name) / "drafts.jsonl",
                            statuses=DRAFT_STATUSES)

    def _feed(self, web, **kw):
        return ContentFeed(web=web, trends_store=self.trends, themen=["thema-a"], **kw)

    def test_lauf_legt_kandidaten_an(self):
        web = FakeWeb({"thema-a": [
            Treffer(titel="Trend 1", url="https://x.test/1", auszug="A"),
            Treffer(titel="Trend 2", url="https://x.test/2", auszug="B"),
        ]})
        r = self._feed(web).trend_lauf()
        self.assertTrue(r["ok"])
        self.assertEqual(r["erzeugt"], 2)
        tabelle, rows, _ = self.mock.upserts[-1]
        self.assertEqual(tabelle, "trend_signals")
        self.assertEqual(rows[0]["status"], "new")
        self.assertEqual(rows[0]["source_type"], "web")

    def test_dedup_gegen_bestehende_urls(self):
        self.mock.rows["trend_signals"] = [{"id": "t1", "source_url": "https://x.test/1"}]
        web = FakeWeb({"thema-a": [
            Treffer(titel="Alt", url="https://x.test/1"),      # schon vorhanden -> raus
            Treffer(titel="Neu", url="https://x.test/9"),
        ]})
        r = self._feed(web).trend_lauf()
        self.assertEqual(r["erzeugt"], 1)
        self.assertEqual(self.mock.upserts[-1][1][0]["source_url"], "https://x.test/9")

    def test_dedup_innerhalb_eines_laufs(self):
        web = FakeWeb({"thema-a": [
            Treffer(titel="X", url="https://x.test/dup"),
            Treffer(titel="X2", url="https://x.test/dup"),     # gleiche URL zweimal
        ]})
        self.assertEqual(self._feed(web).trend_lauf()["erzeugt"], 1)

    def test_max_gesamt_stoppt(self):
        web = FakeWeb({"thema-a": [Treffer(titel=f"T{i}", url=f"https://x.test/{i}") for i in range(10)]})
        self.assertEqual(self._feed(web).trend_lauf(max_gesamt=3)["erzeugt"], 3)

    def test_max_pro_thema(self):
        web = FakeWeb({"thema-a": [Treffer(titel=f"T{i}", url=f"https://x.test/{i}") for i in range(10)]})
        self.assertEqual(self._feed(web).trend_lauf(max_pro_thema=2)["erzeugt"], 2)

    def test_treffer_ohne_url_uebersprungen(self):
        web = FakeWeb({"thema-a": [Treffer(titel="ohne", url=""), Treffer(titel="mit", url="https://x.test/1")]})
        self.assertEqual(self._feed(web).trend_lauf()["erzeugt"], 1)

    def test_notbremse_pausiert(self):
        ws = WatchStore(Path(self.dir.name) / "watch.jsonl")
        ws.set_pause(True)
        web = FakeWeb({"thema-a": [Treffer(titel="T", url="https://x.test/1")]})
        r = self._feed(web, watch_store=ws).trend_lauf()
        self.assertTrue(r["pausiert"])
        self.assertEqual(r["erzeugt"], 0)
        self.assertEqual(self.mock.upserts, [])

    def test_recherche_fehlgeschlagen_erzeugt_nichts(self):
        self.assertEqual(self._feed(FakeWeb({}, ok=False)).trend_lauf()["erzeugt"], 0)

    def test_research_ticket_und_notify(self):
        gemeldet = []
        tickets = ResearchTickets(Path(self.dir.name) / "research.jsonl")
        web = FakeWeb({"thema-a": [Treffer(titel="T", url="https://x.test/1", auszug="A")]})
        feed = self._feed(web, research=tickets,
                          notify=lambda text, **kw: gemeldet.append((text, kw)))
        feed.trend_lauf()
        self.assertEqual(len(gemeldet), 1)
        self.assertEqual(gemeldet[0][1]["kategorie"], "content")
        erledigt = tickets.list(status="erledigt")
        self.assertEqual(len(erledigt), 1)
        self.assertEqual(erledigt[0]["provider"], "brave")

    def test_default_themen_aus_watch_config(self):
        # Ohne explizite Themen -> kuratierte Content-Themen (Abteilung 'cco').
        feed = ContentFeed(web=FakeWeb({}), trends_store=self.trends)
        self.assertTrue(feed.themen)

    # -- Ideen-Stufe --

    def test_ideen_aus_trends(self):
        self.mock.rows["trend_signals"] = [{"id": "t1", "title": "Retro-Trikots", "status": "new",
                                            "description": "Alte Trikots sind wieder gefragt."}]
        core = FakeCore("TITEL: Retro-Trikot-Reel\nIDEE: Zeige die Top-5 Retro-Trikots.\nFORMAT: Reel")
        feed = ContentFeed(web=FakeWeb({}), trends_store=self.trends, ideas_store=self._ideas(), core=core)
        r = feed.ideen_lauf()
        self.assertEqual(r["erzeugt"], 1)
        tabelle, rows, _ = self.mock.upserts[-1]
        self.assertEqual(tabelle, "ideas")
        self.assertEqual(rows[0]["title"], "Retro-Trikot-Reel")
        self.assertEqual(rows[0]["status"], "inbox")
        self.assertEqual(rows[0]["source_type"], "trend")
        # Trend wurde als verarbeitet markiert (new -> reviewing)
        pt, patch, params = self.mock.patches[-1]
        self.assertEqual(pt, "trend_signals")
        self.assertEqual(patch["status"], "reviewing")
        self.assertIn("id=eq.t1", params)

    def test_ideen_nur_status_new(self):
        self.mock.rows["trend_signals"] = [{"id": "t1", "title": "X", "status": "approved"}]
        core = FakeCore("TITEL: T\nIDEE: I\nFORMAT: Reel")
        feed = ContentFeed(web=FakeWeb({}), trends_store=self.trends, ideas_store=self._ideas(), core=core)
        self.assertEqual(feed.ideen_lauf()["erzeugt"], 0)   # nicht 'new' -> ignoriert

    def test_ideen_ohne_core_no_op(self):
        self.mock.rows["trend_signals"] = [{"id": "t1", "title": "X", "status": "new"}]
        feed = ContentFeed(web=FakeWeb({}), trends_store=self.trends, ideas_store=self._ideas())
        self.assertFalse(feed.ideen_lauf()["ok"])

    # -- Draft-Stufe --

    def test_drafts_aus_ideen(self):
        self.mock.rows["ideas"] = [{"id": "i1", "title": "Retro-Trikot-Reel", "status": "inbox",
                                    "description": "Top-5 Retro-Trikots."}]
        core = FakeCore("HOOK: Diese Trikots wollen alle!\nCAPTION: Unsere Top 5.\nHASHTAGS: #hsv #retro #trikot")
        feed = ContentFeed(web=FakeWeb({}), trends_store=self.trends, ideas_store=self._ideas(),
                           drafts_store=self._drafts(), core=core)
        r = feed.drafts_lauf()
        self.assertEqual(r["erzeugt"], 1)
        tabelle, rows, _ = self.mock.upserts[-1]
        self.assertEqual(tabelle, "content_drafts")
        self.assertEqual(rows[0]["platform"], "instagram")
        self.assertEqual(rows[0]["status"], "idea")
        self.assertEqual(rows[0]["hook"], "Diese Trikots wollen alle!")
        self.assertEqual(rows[0]["hashtags"], ["#hsv", "#retro", "#trikot"])   # text[] -> Liste
        # Idee als verarbeitet markiert (inbox -> sorted)
        self.assertEqual(self.mock.patches[-1][1]["status"], "sorted")

    def test_feld_parse_robust(self):
        # Markdown-Schmuck vor dem Label darf nicht stoeren.
        self.assertEqual(ContentFeed._feld("**HOOK:** Fesselnder Satz", "HOOK"), "Fesselnder Satz")
        self.assertEqual(ContentFeed._feld("- TITEL: Mein Titel", "TITEL"), "Mein Titel")

    def test_pipeline_lauf(self):
        self.mock.rows["trend_signals"] = [{"id": "t1", "title": "Trend", "status": "new"}]
        self.mock.rows["ideas"] = [{"id": "i1", "title": "Idee", "status": "inbox"}]
        core = FakeCore("TITEL: T\nIDEE: I\nFORMAT: Reel\nHOOK: H\nCAPTION: C\nHASHTAGS: #a #b")
        web = FakeWeb({"thema-a": [Treffer(titel="Neu", url="https://x.test/1")]})
        feed = ContentFeed(web=web, trends_store=self.trends, ideas_store=self._ideas(),
                           drafts_store=self._drafts(), core=core, themen=["thema-a"])
        r = feed.pipeline_lauf(max_pro_stufe=5)
        self.assertTrue(r["ok"])
        self.assertEqual(r["trends"], 1)
        self.assertEqual(r["ideen"], 1)
        self.assertEqual(r["drafts"], 1)

    def test_pipeline_pausiert(self):
        ws = WatchStore(Path(self.dir.name) / "watch.jsonl")
        ws.set_pause(True)
        core = FakeCore("TITEL: T\nIDEE: I")
        feed = ContentFeed(web=FakeWeb({"thema-a": [Treffer(titel="N", url="https://x.test/1")]}),
                           trends_store=self.trends, ideas_store=self._ideas(),
                           drafts_store=self._drafts(), core=core, watch_store=ws, themen=["thema-a"])
        r = feed.pipeline_lauf()
        self.assertTrue(r["pausiert"])
        self.assertEqual(self.mock.upserts, [])


if __name__ == "__main__":
    unittest.main()
