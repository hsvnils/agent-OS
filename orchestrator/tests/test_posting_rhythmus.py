"""MONETARISIERUNG M4: Posting-Rhythmus Soll/Ist. Gate: die Ist-Zaehlung einer Stichwoche stimmt (Medienliste wie von
Meta, Zeitpunkte in UTC, gezaehlt in Europe/Berlin). Gegenproben: Grenze Sonntag/Montag, unvollstaendige erste Woche,
kein doppeltes Schreiben, Soll-Aenderung wirkt nicht rueckwirkend, unbekanntes Ist wird nicht geraten."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core.posting_rhythmus import (auswertung, briefing_zeilen, instagram_abrufen, instagram_beitraege,
                                                instagram_zaehlen, soll_setzen)
from orchestrator.core.reel_store import ReelStore
from orchestrator.core.reichweite import Reichweite, montag
from orchestrator.core.social_kit import MetaInsights
from orchestrator.tests.test_angebote import ApiBasis

# Stichwoche Mo 02.11. - So 08.11.2026 (MEZ = UTC+1)
POSTS = [
    {"timestamp": "2026-11-08T23:00:00+0000", "media_product_type": "FEED"},    # Mo 09.11. 00:00 Berlin -> Folgewoche
    {"timestamp": "2026-11-08T22:59:00+0000", "media_product_type": "REELS"},   # So 08.11. 23:59 Berlin
    {"timestamp": "2026-11-06T18:00:00+0000", "media_product_type": "REELS"},
    {"timestamp": "2026-11-04T10:00:00+0000", "media_product_type": "FEED"},
    {"timestamp": "2026-11-01T23:30:00+0000", "media_product_type": "REELS"},   # Mo 02.11. 00:30 Berlin (UTC noch Sonntag)
    {"timestamp": "2026-11-01T22:30:00+0000", "media_product_type": "FEED"},    # So 01.11. 23:30 Berlin -> Vorwoche
    {"timestamp": "2026-10-28T09:00:00+0000", "media_product_type": "CAROUSEL_ALBUM"},
    {"timestamp": "2026-10-20T10:00:00+0000", "media_product_type": "FEED"},    # aelteste: Woche 19.10. unvollstaendig
]
SONNTAG = date(2026, 11, 15)


def _store():
    return Reichweite(Path(tempfile.mkdtemp()) / "reichweite" / "log.jsonl")


def _plattform(ausw, p, f):
    return next(x for x in next(y for y in ausw["plattformen"] if y["id"] == p)["formate"] if x["id"] == f)


class TestZaehlen(unittest.TestCase):
    def test_1_stichwoche(self):
        z = instagram_zaehlen(POSTS)
        self.assertEqual(z["2026-11-02"], {"beitraege": 4, "beitraege_kurz": 3})                 # Gate
        self.assertEqual(z["2026-10-26"], {"beitraege": 2, "beitraege_kurz": 0})
        self.assertEqual(z["2026-11-09"], {"beitraege": 1, "beitraege_kurz": 0})
        self.assertNotIn("2026-10-19", z)                                                     # Liste reicht nicht ganz zurueck
        self.assertIn("2026-10-19", instagram_zaehlen(POSTS, voll=True))                      # ganze Historie: zaehlt

    def test_2_schreiben_ohne_dubletten(self):
        st = _store()
        self.assertEqual(instagram_beitraege(st, POSTS, SONNTAG), ["2026-10-26", "2026-11-02", "2026-11-09"])
        self.assertEqual(instagram_beitraege(st, POSTS, SONNTAG), [])                          # unveraendert: nichts neu
        self.assertEqual(st.wochen()["instagram"]["2026-11-02"]["quellen"]["beitraege"], "api")
        self.assertEqual(instagram_beitraege(st, None, SONNTAG), [])

    def test_3_medienliste_abrufen(self):
        abrufe = []
        def http(url, params):
            abrufe.append((url, params))
            return {"data": POSTS[:3]}
        mi = MetaInsights("t", "123", http=http)
        st = _store()
        self.assertEqual(instagram_abrufen(st, mi, SONNTAG), ["2026-11-02", "2026-11-09"])    # 3 < 50 -> ganze Historie
        self.assertEqual(abrufe[0][1]["fields"], "timestamp,media_product_type")
        self.assertIsNone(instagram_abrufen(st, MetaInsights("t", "123", http=lambda u, p: {"error": {"code": 190}})))
        self.assertIsNone(MetaInsights("", "").beitraege())


class TestAuswertung(unittest.TestCase):
    def setUp(self):
        self.st = _store()
        instagram_beitraege(self.st, POSTS, SONNTAG)

    def test_1_soll_ist_und_status(self):
        a = auswertung(self.st, None, SONNTAG)
        self.assertEqual((a["aktuelle_woche"], len(a["wochen"]), a["tage_rest"]), ("2026-11-09", 8, 0))
        ig = _plattform(a, "instagram", "beitraege")
        st = {v["woche"]: v["status"] for v in ig["verlauf"]}
        self.assertEqual((st["2026-11-02"], st["2026-10-26"], st["2026-11-09"], st["2026-10-19"]),
                         ("ok", "unter", "offen", "unbekannt"))
        self.assertEqual((ig["erfuellt"], ig["bewertet"], ig["hinter_tempo"]), (1, 2, True))
        tt = _plattform(a, "tiktok", "videos")
        self.assertEqual((tt["aktuell"]["status"], tt["hinter_tempo"]), ("unbekannt", False))  # nichts geraten

    def test_2_soll_gilt_ab_woche(self):
        self.st.erfassen("tiktok", "2026-11-02", {"beitraege": 4, "beitraege_lang": 1})
        self.st.erfassen("tiktok", "2026-11-09", {"beitraege_lang": 1})
        self.assertEqual(soll_setzen(self.st, "tiktok", "lang", "2", "", date(2026, 11, 12))["ab"], "2026-11-09")
        v = {x["woche"]: x for x in _plattform(auswertung(self.st, None, SONNTAG), "tiktok", "lang")["verlauf"]}
        self.assertEqual((v["2026-11-02"]["soll_min"], v["2026-11-02"]["status"]), (1, "ok"))   # nicht rueckwirkend
        self.assertEqual((v["2026-11-09"]["soll_min"], v["2026-11-09"]["status"]), (2, "offen"))
        for args in (("tiktok", "lang", 3, 2), ("tiktok", "lang", 51), ("tiktok", "reels", 1), ("myspace", "x", 1),
                     ("tiktok", "lang", "viele")):
            with self.assertRaises(ValueError, msg=args):
                soll_setzen(self.st, *args)

    def test_3_facebook_pipeline_mindestens(self):
        reels = ReelStore(Path(tempfile.mkdtemp()) / "log.jsonl")
        for i in range(2):
            rid = reels.einreichen(datum="2026-11-14", thema="HSV", caption="#hsv", video=f"r{i}.mp4")
            reels.status_setzen(rid, "gepostet", fb_video_id=f"fb{i}")
        reels.einreichen(datum="2026-11-14", thema="HSV", caption="#hsv", video="r9.mp4")         # nicht gepostet
        heute = date.today()
        fb = lambda: _plattform(auswertung(self.st, reels, heute), "facebook", "beitraege")["aktuell"]
        self.assertEqual((fb()["ist"], fb()["mindestens"], fb()["quelle"]), (2, True, "pipeline"))
        self.st.erfassen("facebook", heute.isoformat(), {"beitraege": 5})
        self.assertEqual((fb()["ist"], fb()["mindestens"]), (5, False))                        # eingetragener Wert gilt
        self.assertEqual(fb()["woche"], montag(heute))

    def test_4_briefing(self):
        self.st.erfassen("tiktok", "2026-11-02", {"beitraege": 2})
        self.assertEqual(briefing_zeilen(auswertung(self.st, None, date(2026, 11, 9))), [])      # Montag: still
        di = briefing_zeilen(auswertung(self.st, None, date(2026, 11, 10)))
        self.assertEqual(di, ["Letzte Woche unter Soll: TikTok Videos 2 von 3–5"])
        mi = briefing_zeilen(auswertung(self.st, None, date(2026, 11, 11)))                      # 1 Beitrag, Tempo 2
        self.assertEqual(mi, ["Instagram Beiträge (Feed und Reels): diese Woche 1 von 3–5, noch 4 Tag(e) bis Sonntag",
                              "Instagram davon Reels: diese Woche 0 von 2–5, noch 4 Tag(e) bis Sonntag"])
        self.st.erfassen("instagram", "2026-11-09", {"beitraege": 2, "beitraege_kurz": 1})
        self.assertEqual(briefing_zeilen(auswertung(self.st, None, date(2026, 11, 11))), [])     # von Hand: kein Tempo-Hinweis
        self.assertEqual(briefing_zeilen(auswertung(self.st, None, date(2026, 11, 14))), [])     # Samstag, Tempo 3 -- Hand
        instagram_beitraege(self.st, POSTS, SONNTAG)                                              # Zaehlung kommt zurueck
        sa = briefing_zeilen(auswertung(self.st, None, date(2026, 11, 14)))
        self.assertEqual(len(sa), 2)


class TestApi(ApiBasis):
    def test_1_rhythmus_und_soll(self):
        st = _store()
        instagram_beitraege(st, POSTS, SONNTAG)
        reels = ReelStore(Path(tempfile.mkdtemp()) / "log.jsonl")
        with mock.patch.object(self.w, "_reichweite", return_value=st), mock.patch.object(self.w, "reel_store", reels):
            r = self.c.get("/api/reichweite").json()["rhythmus"]
            self.assertEqual([p["id"] for p in r["plattformen"]], ["instagram", "facebook", "tiktok", "youtube"])
            self.assertTrue(self.c.post("/api/reichweite/soll", json={"plattform": "youtube", "format": "shorts",
                                                                      "min": "3", "max": "6"}).json()["ok"])
            self.assertFalse(self.c.post("/api/reichweite/soll", json={"plattform": "youtube", "format": "shorts",
                                                                       "min": "7", "max": "6"}).json()["ok"])
            yt = _plattform(self.c.get("/api/reichweite").json()["rhythmus"], "youtube", "shorts")
            self.assertEqual((yt["soll_min"], yt["soll_max"]), (3, 6))

    def test_2_oberflaeche(self):
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        for teil in ("rwRhythmus", "/api/reichweite/soll", 'data-act="rw-soll-speichern"', "v2-rw-wk"):
            self.assertIn(teil, js)


if __name__ == "__main__":
    unittest.main()
