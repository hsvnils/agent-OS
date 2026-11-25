"""OFC_KASSE_ROADMAP KA0: Soll-Beitrag je Mitglied -- Schreibweisen der Mitgliedschaft, Gold 40 € (auch ohne Betrag),
abweichender Betrag als Hinweis, kostenfrei 0 €, Foerder ohne Betrag, Eintritt im Jahr anteilig ab Beitrittsmonat,
spaeterer Eintritt, Summen-Gegenprobe, nur lesend, Endpunkt nur CEO. Fixtures ohne echte Daten."""
import os
import unittest
from unittest import mock

from orchestrator.core import ofc_beitraege as ob
from orchestrator.core import ofc_mitglieder as om
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc_mitglieder import KOPF, _Rec


def _z(nr, vor, art, seit="01.01.2020", beitrag="", kommentar=""):
    z = [""] * len(KOPF)
    z[0], z[1], z[3], z[4], z[7], z[8], z[9], z[17] = "01.01.2020 10:00:00", nr, seit, beitrag, vor, "Muster", art, kommentar
    return z


GOLD, GOLD2 = "Goldmitgliedschaft (jährliche Zahlung)", "Goldmitgliedschaft (Jährliche Zahlung)"
WERTE = [KOPF,
         _z("1", "Anna", GOLD, beitrag="40,00 €"),
         _z("2", "Bert", GOLD2),                                         # ohne Betrag -> 40 €
         _z("3", "Cora", GOLD, beitrag="30,00 €"),                       # abweichend
         _z("4", "Dirk", "Standardmitgliedschaft (Kostenfrei)", beitrag="0,00 €"),
         _z("5", "Emil", "Fördermitgliedschaft (Beitrag bitte unten ins Kommentarfeld eintragen)", kommentar="gern 60 Euro"),
         _z("6", "Fina", GOLD, seit="15.04.2026", beitrag="40,00 €"),    # Eintritt im Jahr -> 9/12
         _z("7", "Gero", GOLD, seit="01.02.2027", beitrag="40,00 €"),    # erst ab 2027
         _z("8", "Hans", "Vorstand")]


class TestSoll(unittest.TestCase):
    def setUp(self):
        self.d = om.auswerten(WERTE)

    def test_1_arten_und_betraege(self):
        self.assertEqual([ob.art(x) for x in (GOLD, GOLD2, "Standardmitgliedschaft (Kostenfrei)", "Fördermitgliedschaft", "Vorstand", "?")],
                         ["gold", "gold", "standard", "foerder", "vorstand", "unbekannt"])
        self.assertEqual([ob.betrag_cent(x) for x in ("40,00 €", "40 €", "1.200,50", "", "x")], [4000, 4000, 120050, None, None])

    def test_2_soll_2026(self):
        r = ob.beitraege(self.d, 2026)
        m = {x["name"].split()[0]: x for x in r["mitglieder"]}
        self.assertEqual({k: v["soll_cent"] for k, v in m.items()},
                         {"Anna": 4000, "Bert": 4000, "Cora": 3000, "Dirk": 0, "Emil": 0, "Fina": 3000, "Gero": 0, "Hans": 0})
        self.assertEqual((m["Fina"]["anteilig"], m["Fina"]["faellig"]), (True, "2026-04-15"))
        self.assertEqual(m["Anna"]["faellig"], "2026-01-01")
        self.assertIn("40 € angenommen", m["Bert"]["hinweise"][0])
        self.assertIn("statt 40 €", m["Cora"]["hinweise"][0])
        self.assertIn("gern 60 Euro", m["Emil"]["hinweise"][0])
        self.assertIn("erst ab 2027", m["Gero"]["hinweise"][-1])
        self.assertEqual(m["Dirk"]["hinweise"], [])
        s = r["summen"]
        self.assertEqual((s["mitglieder"], s["gold"], s["standard"], s["foerder"], s["vorstand"], s["beitragspflichtig"], s["anteilig"]),
                         (8, 5, 1, 1, 1, 4, 1))
        self.assertEqual(s["soll_cent"], sum(x["soll_cent"] for x in r["mitglieder"]))           # Gegenprobe Summe

    def test_3_folgejahr_voll(self):
        m = {x["name"].split()[0]: x for x in ob.beitraege(self.d, 2027)["mitglieder"]}
        self.assertEqual((m["Fina"]["soll_cent"], m["Fina"]["anteilig"]), (4000, False))
        self.assertEqual((m["Gero"]["soll_cent"], m["Gero"]["faellig"]), (round(4000 * 11 / 12), "2027-02-01"))

    def test_4_fehler_und_nur_lesend(self):
        self.assertFalse(ob.beitraege({"ok": False, "hinweis": "x"})["ok"])
        src = open(ob.__file__, encoding="utf-8").read()
        for verboten in ("values().update", "values().append", "batchUpdate", "open(", "write_text", "erfassen("):
            self.assertNotIn(verboten, src, verboten)


class TestApi(ApiBasis):
    def test_5_endpunkt_nur_ceo(self):
        om._CACHE.clear()
        g = mock.Mock(); g.auth = _Rec(WERTE)
        with mock.patch.object(self.w, "_google", return_value=g), mock.patch.dict(os.environ, {"OFC_MITGLIEDER_TABELLE": ""}):
            d = self.c.get("/api/ofc/beitraege", params={"jahr": 2026}).json()
            self.assertEqual((d["ok"], d["jahr"], d["summen"]["soll_cent"]), (True, 2026, 14000))
            self.assertFalse(self.c.get("/api/ofc/beitraege", params={"jahr": 1999}).json()["ok"])
            self.assertTrue(all(a[0] in ("drive.files.list", "sheets.values.get") for a in g.auth.aufrufe))
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.get("/api/ofc/beitraege").status_code, 403)
        om._CACHE.clear()
        g.auth = mock.Mock(verfuegbar=mock.Mock(side_effect=RuntimeError("geheim-123")))
        with mock.patch.object(self.w, "_google", return_value=g):
            r = self.c.get("/api/ofc/beitraege", params={"neu": 1}).json()
            self.assertEqual(r["ok"], False); self.assertNotIn("geheim", r["hinweis"])
