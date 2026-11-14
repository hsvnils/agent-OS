"""MONETARISIERUNG M3: Follower und Reichweiten je Plattform. Gegenproben: Vorschau schreibt nichts, Tagesreichweite wird
nicht addiert, kaputte CSV wird abgelehnt, Woche in der Zukunft wird abgelehnt. Exporte sind nachgebaut (keine echten Daten)."""
import base64
import tempfile
import unittest
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core.reichweite import (Reichweite, _datum, _zahl, csv_lesen, import_vorschau, instagram_uebernehmen,
                                          montag, spalte_erkennen)
from orchestrator.core.team_auth import modul_fuer_pfad
from orchestrator.tests.test_angebote import ApiBasis

META = ("﻿Seitenaufrufe Insights\n"                    # Titelzeile wie im Business-Suite-Export
        "Datum\tReichweite\tAufrufe\tNeue Follower\tInteraktionen\n"
        + "".join(f"2026-11-{t:02d}\t1.000\t2.500\t{t % 3}\t40\n" for t in range(2, 16)))   # Mo 02.11. - So 15.11.
TIKTOK = "Date;Video Views;Profile Views;Likes;Followers\n" + "".join(
    f"{t:02d}.11.2026;{100 * t};{t};5;{5000 + t}\n" for t in range(9, 16))


def _store():
    return Reichweite(Path(tempfile.mkdtemp()) / "reichweite" / "log.jsonl")


class TestLesen(unittest.TestCase):
    def test_1_zahlen_und_daten(self):
        self.assertEqual([_zahl(x) for x in ("1.234", "1,234", "1.234,5", "12,5", "", "-", "7 812")],
                         [1234, 1234, 1234, 12, None, None, 7812])
        self.assertEqual([_datum(x) for x in ("2026-11-02", "02.11.2026", "11/02/2026", "2026-11-02T00:00:00", "Summe")],
                         ["2026-11-02", "2026-11-02", "2026-11-02", "2026-11-02", None])
        self.assertEqual(montag("2026-11-15"), "2026-11-09")

    def test_2_spalten(self):
        erwartet = {"Datum": "_datum", "Date": "_datum", "Reach": "reichweite", "Erreichte Konten": "reichweite",
                    "Profile Views": "profilbesuche", "Video Views": "aufrufe", "Aufrufe": "aufrufe",
                    "Neue Follower": "follower_neu", "Abonnenten": "follower_neu", "Followers": "follower",
                    "Shares": "shares", "Link-Klicks": "link_klicks", "Likes": ""}
        self.assertEqual({k: spalte_erkennen(k) for k in erwartet}, erwartet)

    def test_3_csv_varianten(self):
        kopf, zeilen = csv_lesen(META.encode("utf-16"))
        self.assertEqual((kopf[0], len(zeilen)), ("Datum", 14))
        kopf, zeilen = csv_lesen(TIKTOK.encode("utf-8"))
        self.assertEqual((kopf[1], len(zeilen)), ("Video Views", 7))
        with self.assertRaisesRegex(ValueError, "Kopfzeile"):
            csv_lesen(b"a,b\n1,2\n")

    def test_4_vorschau_wochen(self):
        v = import_vorschau(META.encode("utf-16"))
        self.assertTrue(v["taeglich"])
        w = {x["woche"]: x for x in v["wochen"]}
        self.assertEqual(sorted(w), ["2026-11-02", "2026-11-09"])
        self.assertEqual(w["2026-11-02"]["werte"], {"aufrufe": 17500, "follower_neu": sum(t % 3 for t in range(2, 9)),
                                                    "interaktionen": 280})        # Reichweite nicht addiert
        self.assertTrue(any("Reichweite" in h for h in v["hinweise"]))
        t = import_vorschau(TIKTOK.encode())
        self.assertEqual(t["wochen"][0]["werte"], {"aufrufe": sum(100 * x for x in range(9, 16)),
                                                   "profilbesuche": sum(range(9, 16)), "follower": 5015})   # Stand = letzter Tag
        z = import_vorschau(TIKTOK.encode(), {"Likes": "interaktionen"})          # Zuordnung von Hand
        self.assertEqual(z["wochen"][0]["werte"]["interaktionen"], 35)
        with self.assertRaisesRegex(ValueError, "Metrik"):
            import_vorschau(TIKTOK.encode(), {"Likes": "gibtsnicht"})


class TestStore(unittest.TestCase):
    def test_1_erfassen_und_uebersicht(self):
        st = _store()
        st.erfassen("youtube", "2026-10-05", {"follower": "440"})
        st.erfassen("youtube", "2026-11-04", {"follower": "446", "aufrufe": "1.200"})
        st.erfassen("youtube", "2026-11-05", {"aufrufe": "1300"}, quelle="csv")     # gleiche Woche: neuer Wert gilt
        st.erfassen("instagram", "2026-06-01", {"follower": 100000, "reichweite": 5})
        st.erfassen("instagram", "2026-11-09", {"follower": 120000})
        u = st.uebersicht(date(2026, 11, 14))
        p = {x["id"]: x for x in u["plattformen"]}
        yt = p["youtube"]
        self.assertEqual((yt["follower"], yt["delta_4w"], yt["letzte"]["werte"]["aufrufe"]), (446, 6, 1300))
        self.assertEqual(yt["letzte"]["quellen"], {"follower": "hand", "aufrufe": "csv"})
        self.assertEqual(p["instagram"]["wochen"][0]["bruch"], True)                 # vor 15.06.2026 (Meta)
        self.assertEqual(p["instagram"]["wochen"][-1]["bruch"], False)
        self.assertEqual(u["follower_summe"], 120446)
        self.assertEqual(p["tiktok"]["luecken"], ["2026-11-02", "2026-10-26", "2026-10-19", "2026-10-12"])
        st.entfernen("youtube", "2026-11-03")
        self.assertEqual(st.uebersicht(date(2026, 11, 14))["plattformen"][3]["follower"], 440)

    def test_2_pruefungen(self):
        st = _store()
        for args in (("myspace", "2026-11-02", {"follower": 1}), ("tiktok", "2099-01-05", {"follower": 1}),
                     ("tiktok", "2026-11-02", {}), ("tiktok", "2026-11-02", {"likes": 1}),
                     ("tiktok", "2026-11-02", {"follower": "viele"}), ("tiktok", "kein-datum", {"follower": 1})):
            with self.assertRaises(ValueError, msg=args):
                st.erfassen(*args)
        self.assertFalse(st.pfad.exists())                                            # nichts geschrieben

    def test_3_instagram(self):
        @dataclass
        class Snap:
            followers: int = 0
            reach: int = 0
        st = _store()
        self.assertIsNone(instagram_uebernehmen(st, None))
        self.assertIsNone(instagram_uebernehmen(st, Snap()))
        e = instagram_uebernehmen(st, Snap(120345, 900000), date(2026, 11, 9))
        self.assertEqual((e["woche"], e["werte"]), ("2026-11-09", {"follower": 120345, "reichweite_28t": 900000}))


class TestApi(ApiBasis):
    def test_1_hand_import_entfernen(self):
        self.assertEqual(modul_fuer_pfad("GET", "/api/reichweite"), "content_ops")
        st = _store()
        with mock.patch.object(self.w, "_reichweite", return_value=st):
            self.assertTrue(self.c.post("/api/reichweite", json={"plattform": "tiktok", "woche": "2026-11-02",
                                                                 "werte": {"follower": "5.774"}}).json()["ok"])
            datei = base64.b64encode(TIKTOK.encode()).decode()
            v = self.c.post("/api/reichweite/import", json={"plattform": "tiktok", "datei": datei}).json()
            self.assertTrue(v["ok"], v)
            self.assertEqual(len(v["vorschau"]["wochen"]), 1)
            tiktok = lambda: next(p for p in self.c.get("/api/reichweite").json()["plattformen"] if p["id"] == "tiktok")
            self.assertEqual(len(tiktok()["wochen"]), 1)                              # Gegenprobe: Vorschau schreibt nichts
            s = self.c.post("/api/reichweite/import", json={"plattform": "tiktok", "datei": datei, "speichern": True}).json()
            self.assertEqual(s["gespeichert"], 1)
            self.assertEqual(tiktok()["follower"], 5015)
            self.assertFalse(self.c.post("/api/reichweite/import", json={"plattform": "tiktok", "datei": "%%%"}).json()["ok"])
            self.assertTrue(self.c.post("/api/reichweite/entfernen", json={"plattform": "tiktok", "woche": "2026-11-10"}).json()["ok"])
            self.assertEqual(tiktok()["follower"], 5774)

    def test_2_oberflaeche(self):
        js = (Path(self.w.__file__).parent / "static" / "app-v2.js").read_text(encoding="utf-8")
        for teil in ('id: "reichweite"', "/api/reichweite/import", 'data-act="rw-ig"', "rwKurve"):
            self.assertIn(teil, js)


if __name__ == "__main__":
    unittest.main()
