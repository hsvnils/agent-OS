"""KUNDEN_FINANZEN Etappe 25: Zeiterfassung und Nachkalkulation -- nur intern. Arbeitszeit ist kalkulatorisch (keine
Buchung, EUeR unveraendert), Fahrten sind echte Ausgaben (Eigenbeleg 0,30 EUR/km, Hin + Rueck per OpenStreetMap)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core.angebote import AngebotStore
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.routen import Routen
from orchestrator.core.todos import geschaefts_todos
from orchestrator.core.zeiterfassung import Zeiterfassung, befehl, firma_finden, erinnerung_faellig
from orchestrator.tests.test_angebote import POS, ApiBasis, _stores

HEIM = "Arthur-Soltau-Weg 7c 22889 Tangstedt"


class _Osm:
    def __init__(self, meter=23_450, fehler=False):
        self.meter, self.fehler, self.aufrufe = meter, fehler, []

    def __call__(self, url):
        self.aufrufe.append(url)
        if self.fehler:
            raise OSError("offline")
        if "nominatim" in url:
            return [{"lat": "53.7", "lon": "10.0"}]
        return {"routes": [{"distance": self.meter}]}


def _setup(osm=None):
    bh, ks, st, k, ap = _stores()                       # K-00001 Brand X GmbH, Hafenstr. 1, 20095 Hamburg
    an = st.anlegen({"firma": k, "positionen": POS})["nummer"]      # 1.020 EUR
    st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
    ab = AuftragBuch(bh, ks, st)
    nr = ab.aus_angebot(an)["nummer"]
    z = Zeiterfassung(bh, ks, auftraege=ab, routen=Routen(Path(tempfile.mkdtemp()) / "geo.json", http=osm or _Osm()),
                      heimadresse=HEIM)
    z.einstellen("5.061,21", "40")
    return bh, ks, k, ab, nr, z


class TestZeit(unittest.TestCase):
    def test_1_stundensatz_brutto(self):
        bh, ks, k, ab, nr, z = _setup()
        self.assertEqual(z.einstellungen()["stundensatz_cent"], 2920)                  # 5.061,21 x 12 / 2.080 h
        self.assertNotIn("5061", json.dumps([e["daten"] for e in bh.eintraege()]))     # Lohn nicht in der Kette
        with self.assertRaises(ValueError):
            z.einstellen("0", "40")

    def test_2_start_stopp_und_nachkalkulation(self):
        bh, ks, k, ab, nr, z = _setup()
        r = z.starten(auftrag=nr, quelle="Telegram")
        with self.assertRaises(ValueError):
            z.starten(auftrag=nr)                                                       # nur eine Zeit gleichzeitig
        ende = (datetime.fromisoformat(r["start"]) + timedelta(minutes=150)).isoformat()
        s = z.stoppen(ende=ende)
        self.assertEqual((s["minuten"], s["kosten_cent"]), (150, 7300))                 # 2,5 h x 29,20
        f = z.fahrt_erfassen(s["id"])                                                     # OSM: 23,45 km -> 47 km Hin+Rueck
        self.assertEqual((f["km"], f["betrag_cent"]), (47, 1410))
        z.fahrt_erfassen(s["id"], km=48)                                                # Korrektur: letzter Wert gilt
        z.fahrt_erfassen(s["id"], km=47)
        e2 = z.eintragen(auftrag=nr, datum=jetzt().date().isoformat(), von_uhr="09:00", bis_uhr="10:30")
        z.fahrt_erfassen(e2["id"], km="12")
        nk = z.nachkalkulation(ab.auftrag(nr))
        self.assertEqual((nk["minuten"], nk["zeit_cent"], nk["fahrt_cent"], nk["km"]), (240, 7300 + 4380, 1410 + 360, 59))
        self.assertEqual(nk["db_cent"], 102000 - 11680 - 1770)
        self.assertEqual(nk["stundenlohn_cent"], round((102000 - 1770) * 60 / 240))
        self.assertEqual([e for e in bh.eintraege() if e["typ"] == "eigenbeleg_angelegt"], [])   # nie ein Beleg
        z.stornieren(s["id"], "falsch")
        self.assertEqual(z.nachkalkulation(ab.auftrag(nr))["minuten"], 90)

    def test_3_nur_intern_eur_unveraendert(self):
        bh, ks, k, ab, nr, z = _setup()
        f = Finanzen(bh, ks)
        vorher = f.euer(jetzt().year)
        z.eintragen(auftrag=nr, datum=jetzt().date().isoformat(), minuten=600)          # 10 h Arbeitszeit
        self.assertEqual(f.euer(jetzt().year), vorher)                                  # Arbeitszeit ist keine Ausgabe
        z.fahrt_erfassen(z.fuer_auftrag(nr)[0]["id"], km=20)
        self.assertEqual(f.euer(jetzt().year), vorher)                                  # Firmenwagen: auch km fiktiv
        self.assertEqual(z.nachkalkulation(ab.auftrag(nr))["fahrt_cent"], 600)

    def test_4_eingaben_und_offline(self):
        bh, ks, k, ab, nr, z = _setup(osm=_Osm(fehler=True))
        for kw in ({"datum": "2099-01-01", "minuten": 30}, {"datum": jetzt().date().isoformat()},
                   {"datum": jetzt().date().isoformat(), "minuten": 0}, {"datum": jetzt().date().isoformat(), "minuten": 2000}):
            with self.assertRaises(ValueError, msg=kw):
                z.eintragen(auftrag=nr, **kw)
        with self.assertRaises(ValueError):
            z.eintragen(auftrag="AB-2099-9999", datum=jetzt().date().isoformat(), minuten=30)
        r = z.eintragen(auftrag=nr, datum=jetzt().date().isoformat(), von_uhr="22:00", bis_uhr="01:00")
        self.assertEqual(r["minuten"], 180)                                             # ueber Mitternacht
        with self.assertRaisesRegex(ValueError, "selbst eintragen"):
            z.fahrt_erfassen(r["id"])                                                     # offline: km von Hand

    def test_5_ohne_auftrag_und_todos(self):
        bh, ks, k, ab, nr, z = _setup()
        r = z.starten(firma=k)
        ids = {t["id"] for t in geschaefts_todos(bh, ks)}
        self.assertIn(f"zeit-zuordnen:{r['id']}", ids)
        z.stoppen()
        z.zuordnen(r["id"], nr)
        self.assertNotIn(f"zeit-zuordnen:{r['id']}", {t["id"] for t in geschaefts_todos(bh, ks)})
        x = {"start": (datetime.now() - timedelta(hours=11)).isoformat()}
        self.assertTrue(erinnerung_faellig(x))
        self.assertFalse(erinnerung_faellig({"start": datetime.now().isoformat()}))


class TestTelegram(unittest.TestCase):
    def test_1_befehle(self):
        self.assertEqual(befehl("Ich bin jetzt auf dem Weg zu CR Container"), {"art": "start", "ziel": "CR Container"})
        self.assertEqual(befehl("Bin auf dem Weg zur Kiez Alm!"), {"art": "start", "ziel": "Kiez Alm"})
        self.assertEqual(befehl("Bin wieder zuhause"), {"art": "stopp"})
        self.assertEqual(befehl("bin wieder daheim"), {"art": "stopp"})
        self.assertEqual(befehl("42 km"), {"art": "km", "km": "42"})
        self.assertEqual(befehl("Fahre jetzt nach Hause"), {"art": "stopp"})
        for kein in ("Wie weit ist es zu CR Container?", "Schreib CR Container eine Mail", "Hallo Luna"):
            self.assertIsNone(befehl(kein), kein)

    def test_2_firma_finden(self):
        bh, ks, k, ab, nr, z = _setup()
        cr = ks.firma_anlegen({"name": "CR Container Trading GmbH"})["nummer"]
        self.assertEqual(firma_finden(ks, "CR Container"), cr)
        self.assertEqual(firma_finden(ks, "Brand X"), k)                                # ganzer Name im Ziel
        self.assertEqual(firma_finden(ks, "Mond"), "")


class TestApi(ApiBasis):
    def test_a1_zeit_endpunkte(self):
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps({"strasse": "Arthur-Soltau-Weg 7c",
                                                                                  "plz": "22889", "ort": "Tangstedt"}))
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.assertTrue(self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"}).json()["ok"])
        r = self.c.post("/api/finanzen/zeit/eintrag", json={"auftrag": nr, "datum": jetzt().date().isoformat(),
                                                             "minuten": "90", "km": "30"}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.get(f"/api/finanzen/zeit?auftrag={nr}").json()
        self.assertEqual((d["nachkalkulation"]["minuten"], d["nachkalkulation"]["fahrt_cent"]), (90, 900))
        self.assertNotIn("monatsbrutto_cent", d["einstellungen"])                        # Lohn nicht in der Uebersicht


if __name__ == "__main__":
    unittest.main()
