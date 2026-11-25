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


# -- KA1: Beitragszahlungen erkennen ----------------------------------------------------------------------------------
import tempfile                                                          # noqa: E402
from pathlib import Path                                                 # noqa: E402

from orchestrator.core import ofc                                        # noqa: E402
from orchestrator.core import ofc_eingang as oe                          # noqa: E402
from orchestrator.core.ofc_store import OfcStore, import_anwenden        # noqa: E402
from orchestrator.tests.test_ofc import _pdf_als_text                    # noqa: E402
from orchestrator.tests.test_ofc_eingang import _erhalten, _ordner       # noqa: E402

MITGLIEDER = om.auswerten([KOPF, _z("10", "Erika", GOLD, beitrag="40,00 €"), _z("11", "Paul", GOLD),
                           _z("12", "Lena", GOLD, beitrag="40,00 €"), _z("13", "Tom", "Standardmitgliedschaft (Kostenfrei)"),
                           _z("14", "Zoe", GOLD), _z("15", "Zoe", GOLD)])     # Zoe Muster doppelt


class TestKA1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = Path(self.tmp.name) / "Tickets 26-27"
        _ordner(s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
        self.st = OfcStore(Path(self.tmp.name) / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, s)
        self.env = mock.patch.dict(os.environ, {"OFC_BEITRAG_AB": "2027"})
        self.env.start()

    def tearDown(self):
        self.p.stop(); self.env.stop()
        self.tmp.cleanup()

    def plan(self, *mails):
        return oe.eingang_plan(self.st, list(mails), MITGLIEDER)["neu"]

    def test_6_beitrag_automatisch_ein_und_zwei_jahre(self):
        e = self.plan(_erhalten("Paul Muster", "40,00"))[0]
        self.assertEqual((e["zuordnung"], e["art"], [(b["nummer"], b["jahr"], b["cent"]) for b in e["beitrag"]]),
                         ("auto", "beitrag", [("11", 2027, 4000)]))
        e = self.plan(_erhalten("Paul Muster", "80,00"))[0]
        self.assertEqual([(b["jahr"], b["cent"]) for b in e["beitrag"]], [(2027, 4000), (2028, 4000)])
        oe.eingang_anwenden(self.st, [_erhalten("Paul Muster", "40,00")], mitglieder=MITGLIEDER)
        self.assertEqual(ob.bezahlt_je_jahr(self.st.stand())["11|2027"]["cent"], 4000)
        self.assertNotIn("11|2027", ob.offene_beitraege(self.st.stand(), MITGLIEDER, 2028))
        e = self.plan(_erhalten("Paul Muster", "40,00", tc="2PP22222PP2222222", mid="<p2@p>"))[0]
        self.assertEqual([(b["jahr"]) for b in e["beitrag"]], [2028])                          # naechstes offenes Jahr

    def test_7_ticket_geht_vor_ausser_mitteilung_nennt_beitrag(self):
        e = self.plan(_erhalten("Erika Muster", "35,00"))[0]
        self.assertEqual((e["zuordnung"], e["art"], e["tickets"]), ("auto", "ticket", ["262236181415-1"]))
        e = self.plan(_erhalten("Erika Muster", "40,00"))[0]
        self.assertEqual((e["zuordnung"], e["art"]), ("auto", "beitrag"))                     # kein Ticket passt
        e = self.plan(_erhalten("Lena Muster", "30,00", "Mitgliedsbeitrag"))[0]
        self.assertEqual((e["zuordnung"], e["beitrag_vorschlaege"][0]["beitrag"][0]["nummer"]), ("offen", "12"))
        e = self.plan(_erhalten("Unbekannt Person", "40,00", "Beitrag 2027"))[0]
        self.assertEqual(e["zuordnung"], "offen")                                             # nicht als „kein Ticket“

    def test_8_doppelter_name_kostenfrei_ohne_liste(self):
        self.assertEqual(self.plan(_erhalten("Zoe Muster", "40,00"))[0]["zuordnung"], "offen")
        self.assertEqual(len(self.plan(_erhalten("Zoe Muster", "40,00"))[0]["beitrag_vorschlaege"]), 2)
        self.assertEqual(self.plan(_erhalten("Tom Muster", "40,00"))[0]["zuordnung"], "offen")    # kostenfrei
        self.assertEqual(oe.eingang_plan(self.st, [_erhalten("Paul Muster", "40,00")])["neu"][0]["zuordnung"], "offen")

    def test_9_klick_beitrag_familie_alias_und_loesen(self):
        oe.eingang_anwenden(self.st, [_erhalten("Max Anders", "80,00")], mitglieder=MITGLIEDER)
        eid = "e-1EE11111EE1111111"
        self.assertFalse(oe.eingang_art(self.st, eid, "beitrag", beitrag=[], mitglieder=MITGLIEDER)["ok"])
        self.assertFalse(oe.eingang_art(self.st, eid, "xyz")["ok"])
        r = oe.eingang_art(self.st, eid, "beitrag", beitrag=[{"nummer": "11", "jahr": 2027}, {"nummer": "12", "jahr": 2027}],
                           mitglieder=MITGLIEDER)
        self.assertEqual((r["ok"], [b["cent"] for b in r["beitrag"]], r["aliase_neu"]), (True, [4000, 4000], ["11", "12"]))
        x = self.st.stand()["eingaenge"][eid]
        self.assertEqual((x["art"], x["zuordnung"], x["von_hand"]), ("beitrag", "manuell", True))
        e = self.plan(_erhalten("Max Anders", "80,00", tc="3MM33333MM3333333", mid="<m3@p>"))[0]
        self.assertEqual((e["zuordnung"], sorted((b["nummer"], b["jahr"]) for b in e["beitrag"])),
                         ("auto", [("11", 2028), ("12", 2028)]))                                # Familie ueber Alias
        oe.eingang_zuordnen(self.st, eid, [])                                                   # loesen
        x = self.st.stand()["eingaenge"][eid]
        self.assertEqual((x["zuordnung"], x["art"], x["beitrag"]), ("offen", None, []))
        self.assertTrue(oe.eingang_art(self.st, eid, "merch")["ok"])
        self.assertEqual(self.st.stand()["eingaenge"][eid]["art"], "merch")


class TestKA1Api(ApiBasis):
    def test_11_endpunkt_art_nur_ceo(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.w, "ROOT", Path(d)), \
                mock.patch.object(self.w, "_ofc_mitglieder_daten", return_value=MITGLIEDER):
            st = OfcStore(Path(d) / "fanclub")
            oe.eingang_anwenden(st, [_erhalten("Max Anders", "40,00")])
            r = self.c.post("/api/ofc/eingang/e-1EE11111EE1111111/art", json={"art": "beitrag", "beitrag": [{"nummer": "11", "jahr": 2027}]}).json()
            self.assertEqual((r["ok"], r["beitrag"][0]["cent"]), (True, 4000))
            self.assertFalse(self.c.post("/api/ofc/eingang/e-1EE11111EE1111111/art", json={"art": "beitrag", "beitrag": "x"}).json()["ok"])
            with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                self.assertEqual(self.c.post("/api/ofc/eingang/e-1EE11111EE1111111/art", json={"art": "merch"}).status_code, 403)
