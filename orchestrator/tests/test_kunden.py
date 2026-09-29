"""Self-Checks Kunden-Stammdaten (KUNDEN_FINANZEN_ROADMAP.md, Etappe 2): Firmen K-, Ansprechpartner AP-, Verlauf,
Collab-Zuordnung, LUNA-OS-API + Rechte."""
import tempfile
import threading
import unittest
from pathlib import Path

from orchestrator.core.buchhaltung import Buchhaltung
from orchestrator.core.kunden import DubletteFehler, KundenStore


def _ks():
    return KundenStore(Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung"))


class TestKundenStore(unittest.TestCase):
    def test_1_firma_mit_zwei_ansprechpartnern(self):
        ks = _ks()
        k = ks.firma_anlegen({"name": "Muster GmbH", "ort": "Hamburg", "rechnungsmail": "rechnung@muster.de"},
                             von="LUNA-OS:ceo")["nummer"]
        self.assertEqual(k, "K-00001")
        self.assertEqual(ks.firma_anlegen({"name": "Zweite AG", "typ": "lieferant"})["nummer"], "L-00001")  # eigener Kreis
        a1 = ks.ansprechpartner_anlegen(k, {"vorname": "Anna", "nachname": "Muster", "rolle": "Marketing"})["nummer"]
        a2 = ks.ansprechpartner_anlegen(k, {"nachname": "Berger", "mail": "b@muster.de"})["nummer"]
        self.assertEqual((a1, a2), ("AP-00001", "AP-00002"))
        f = ks.firma(k)
        self.assertEqual((f["name"], f["typ"], f["aktiv"]), ("Muster GmbH", "kunde", True))
        self.assertEqual([a["nummer"] for a in f["ansprechpartner_liste"]], [a1, a2])
        self.assertEqual(ks.firmen()[0]["ansprechpartner"], 2)
        self.assertEqual(ks.bh.pruefe_kette(), [])

    def test_2_aenderung_mit_verlauf_nichts_ueberschrieben(self):
        ks = _ks()
        k = ks.firma_anlegen({"name": "Muster GmbH", "ort": "Hamburg"}, von="LUNA-OS:ceo")["nummer"]
        self.assertEqual(ks.firma_aendern(k, {"ort": "Tangstedt", "name": "Muster GmbH"}, von="LUNA-OS:ceo"),
                         {"geaendert": {"ort": "Tangstedt"}})                       # nur echte Aenderungen
        self.assertEqual(ks.firma_aendern(k, {"ort": "Tangstedt"}), {"geaendert": {}})  # nichts -> kein Eintrag
        f = ks.firma(k)
        self.assertEqual(f["ort"], "Tangstedt")
        self.assertEqual([v["typ"] for v in f["verlauf"]], ["firma_angelegt", "firma_geaendert"])
        self.assertEqual(f["verlauf"][0]["felder"]["ort"], "Hamburg")                 # alter Wert bleibt sichtbar
        self.assertEqual(len(ks.bh.eintraege("firma_geaendert")), 1)
        ks.firma_aendern(k, {"aktiv": False})
        self.assertEqual(ks.firmen(nur_aktive=True), [])

    def test_3_validierung(self):
        ks = _ks()
        for falsch in ({"name": " "}, {"name": "X", "typ": "freund"}, {"name": "X", "rechnungsmail": "kein-mail"},
                       {"name": "X", "zahlungsziel_tage": "viel"}, {"name": "X", "zahlungsziel_tage": 999}):
            with self.assertRaises(ValueError, msg=falsch):
                ks.firma_anlegen(falsch)
        with self.assertRaises(ValueError):
            ks.firma_anlegen("kein dict")
        self.assertEqual(ks.bh.eintraege(), [])                                       # keine Nummer verbraucht
        k = ks.firma_anlegen({"name": "X", "unbekannt": "weg", "zahlungsziel_tage": "14"})["nummer"]
        self.assertNotIn("unbekannt", ks.firma(k))
        self.assertEqual(ks.firma(k)["zahlungsziel_tage"], 14)
        with self.assertRaises(KeyError):
            ks.ansprechpartner_anlegen("K-09999", {"vorname": "A"})
        with self.assertRaises(ValueError):
            ks.ansprechpartner_anlegen(k, {"rolle": "ohne Namen"})
        with self.assertRaises(KeyError):
            ks.firma_aendern("K-09999", {"ort": "x"})
        self.assertEqual(len(ks.bh.eintraege("nummer")), 1)                          # Fehlversuche ohne Nummer

    def test_4_dublette(self):
        ks = _ks()
        ks.firma_anlegen({"name": "Muster GmbH"})
        with self.assertRaises(DubletteFehler) as cm:
            ks.firma_anlegen({"name": "  muster   gmbh "})
        self.assertEqual(cm.exception.nummern, ["K-00001"])
        self.assertEqual(ks.firma_anlegen({"name": "Muster GmbH"}, trotz_dublette=True)["nummer"], "K-00002")

    def test_5_collab_zuordnung_eindeutig(self):
        ks = _ks()
        k1 = ks.firma_anlegen({"name": "A"})["nummer"]
        k2 = ks.firma_anlegen({"name": "B"})["nummer"]
        ks.collab_zuordnen(k1, "Brand_X ")
        ks.collab_zuordnen(k1, "brand_x")                                           # doppelt -> kein Eintrag
        self.assertEqual(len(ks.bh.eintraege("collab_zugeordnet")), 1)
        self.assertEqual(ks.collab_zuordnung(), {"brand_x": k1})
        ks.collab_zuordnen(k2, "Brand_X")                                           # umhaengen
        self.assertEqual(ks.collab_zuordnung(), {"brand_x": k2})
        self.assertEqual(ks.firma(k1)["collab"], [])
        ks.collab_loesen(k2, "brand_x")
        self.assertEqual(ks.collab_zuordnung(), {})
        self.assertEqual(ks.firmen(suche="brand"), [])

    def test_6_suche(self):
        ks = _ks()
        k = ks.firma_anlegen({"name": "Muster GmbH", "ort": "Hamburg"})["nummer"]
        ks.firma_anlegen({"name": "Andere AG"})
        ks.ansprechpartner_anlegen(k, {"vorname": "Anna", "nachname": "Berger"})
        self.assertEqual([f["nummer"] for f in ks.firmen(suche="berger")], [k])
        self.assertEqual([f["nummer"] for f in ks.firmen(suche="k-00001")], [k])
        self.assertEqual([f["nummer"] for f in ks.firmen(suche="HAMBURG")], [k])
        self.assertEqual(len(ks.firmen()), 2)

    def test_7_parallel_anlegen_eindeutige_nummern(self):
        ks = _ks()
        nummern = []

        def arbeite(i):
            s = KundenStore(Buchhaltung(ks.bh.dir))
            for j in range(5):
                nummern.append(s.firma_anlegen({"name": f"F{i}-{j}"})["nummer"])

        ts = [threading.Thread(target=arbeite, args=(i,)) for i in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=30)
        self.assertEqual(sorted(nummern), [f"K-{i:05d}" for i in range(1, 31)])
        self.assertEqual(len(ks.firmen()), 30)                                       # jede Nummer hat ihre Firma
        self.assertEqual(ks.bh.pruefe_kette(), [])


class TestKundenApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.crm import CrmStore
        self.w = webapp
        tmp = Path(tempfile.mkdtemp())
        self.orig = (webapp.kunden_store, webapp.crm_store)
        webapp.kunden_store = KundenStore(Buchhaltung(tmp / "buchhaltung"))
        webapp.crm_store = CrmStore(tmp / "crm.jsonl")
        webapp.crm_store.nachricht_erfassen("Brand_X", "Kooperation?", quelle="instagram")
        webapp.crm_store.nachricht_erfassen("Andere Marke", "Hallo", quelle="gmail")
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.kunden_store, self.w.crm_store = self.orig

    def test_1_ablauf_ueber_die_api(self):
        liste = self.c.get("/api/crm/kunden").json()
        self.assertEqual(liste["firmen"], [])
        self.assertEqual({f["firma"] for f in liste["collab_ohne_nummer"]}, {"Brand_X", "Andere Marke"})
        r = self.c.post("/api/crm/kunden", json={"firma": {"name": "Brand X GmbH", "typ": "partner"},
                                                 "collab": "Brand_X"}).json()
        self.assertEqual(r, {"ok": True, "nummer": "P-00001"})
        liste = self.c.get("/api/crm/kunden").json()
        self.assertEqual([f["firma"] for f in liste["collab_ohne_nummer"]], ["Andere Marke"])
        self.assertTrue(self.c.post("/api/crm/kunden/P-00001/ansprechpartner",
                                    json={"ansprechpartner": {"vorname": "Anna"}}).json()["ok"])
        self.assertEqual(self.c.post("/api/crm/ansprechpartner/AP-00001",
                                     json={"ansprechpartner": {"rolle": "Chefin"}}).json(),
                         {"ok": True, "geaendert": {"rolle": "Chefin"}})
        d = self.c.get("/api/crm/kunden/p-00001").json()["firma"]
        self.assertEqual((d["collab"], d["ansprechpartner_liste"][0]["rolle"]), (["brand_x"], "Chefin"))
        self.assertTrue(d["verlauf"][0]["von"].startswith("LUNA-OS:"))
        self.assertEqual(self.c.get("/api/crm/kunden/K-00077").status_code, 404)

    def test_2_fehler_mit_grund(self):
        self.c.post("/api/crm/kunden", json={"firma": {"name": "A"}})
        r = self.c.post("/api/crm/kunden", json={"firma": {"name": "a"}}).json()
        self.assertEqual((r["ok"], r["dublette"]), (False, ["K-00001"]))
        self.assertFalse(self.c.post("/api/crm/kunden", json={"firma": "quatsch"}).json()["ok"])
        self.assertIn("Nicht gefunden", self.c.post("/api/crm/kunden/K-00009", json={"firma": {"ort": "x"}}).json()["hinweis"])

    def test_3_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/crm/kunden"), "crm")
        self.assertEqual(modul_fuer_pfad("POST", "/api/crm/ansprechpartner/AP-00001"), "crm")
        self.assertIn("kunden", erlaubte_apps({"role": "team", "allowed_modules": ["crm"]}))
        self.assertNotIn("kunden", erlaubte_apps({"role": "content", "allowed_modules": ["content_ops"]}))


if __name__ == "__main__":
    unittest.main()
