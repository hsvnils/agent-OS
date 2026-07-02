import tempfile
import unittest
from pathlib import Path

from orchestrator.core.content_feed import ContentFeed
from orchestrator.core.content_store import ContentStore, TREND_FELDER, TREND_STATUSES
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


class TestContentFeed(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cache = Path(self.dir.name) / "trends.jsonl"
        self.mock = MockSupabaseClient()
        self.trends = ContentStore(self.mock, "trend_signals", TREND_FELDER, self.cache,
                                   statuses=TREND_STATUSES)

    def tearDown(self):
        self.dir.cleanup()

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


if __name__ == "__main__":
    unittest.main()
