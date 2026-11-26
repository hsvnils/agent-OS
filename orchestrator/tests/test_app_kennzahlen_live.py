"""APP_KENNZAHLEN AK5/AK6: Live-Zahlen -- eigene Ablage (nie in den Tageswerten), Takt (Standard 15, 5-60), 401 haelt an bis
zur Freigabe, ab 4 Fehlschlaegen genau eine Meldung, Meilensteine ohne Dopplung, Verlauf nach 7 Tagen weg, veraltet ab 45
Minuten, Live-Abgleich, Token nie in Dateien. Kein Netz."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core import app_kennzahlen as ak
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_app_kennzahlen import TOKEN, berlin, z

T0 = berlin(2026, 11, 27, 12, 0)


def live(werte=None):
    w = werte or {"registrierte_stand": 768, "abo_aequivalente": 120.5, "registrierungen": 4}
    stand = "2026-11-27T11:00:00.1+00:00"
    return [z("2026-11-27", k, v, stand) for k, v in w.items()]


class FakeLive:
    def __init__(self, folgen):
        self.folgen, self.aufrufe = list(folgen), 0

    def __call__(self, **kw):
        self.aufrufe += 1
        f = self.folgen.pop(0) if self.folgen else live()
        if isinstance(f, ak.AbrufFehler):
            raise f
        return {"zeilen": f, "verworfen": 0, "anzahl": len(f), "revision": "t"}


class _Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ar = ak.Archiv(self.tmp.name)
        self.mel = []

    def tearDown(self):
        self.tmp.cleanup()

    def notify(self, text, **kw):
        self.mel.append((text, kw))

    def lauf(self, t, f, env=None):
        return ak.live_lauf(self.ar, jetzt=t, abruf=f, notify=self.notify, env=env or {})


class TestTaktUndAblage(_Basis):
    def test_takt_standard_und_einstellbar(self):
        f = FakeLive([])
        self.assertTrue(self.lauf(T0, f)["ok"])
        self.assertFalse(self.lauf(T0 + timedelta(minutes=14), f)["faellig"])
        self.assertTrue(self.lauf(T0 + timedelta(minutes=15), f)["ok"])
        self.assertFalse(ak.live_einstellen(self.tmp.name, takt_min=4)["ok"])           # nie unter 5
        self.assertFalse(ak.live_einstellen(self.tmp.name, takt_min=61)["ok"])
        self.assertTrue(ak.live_einstellen(self.tmp.name, takt_min=5)["ok"])
        self.assertFalse(self.lauf(T0 + timedelta(minutes=19), f)["faellig"])
        self.assertTrue(self.lauf(T0 + timedelta(minutes=20), f)["ok"])
        self.assertEqual(f.aufrufe, 3)
        self.assertEqual(self.lauf(T0 + timedelta(hours=1), f, env={"APP_KENNZAHLEN_LIVE": "0"}), {"aus": True})

    def test_nie_in_den_tageswerten_und_kein_token(self):
        self.lauf(T0, FakeLive([]))
        self.assertEqual(self.ar.werte(), {})                                            # Gegenprobe: Tageswerte leer
        lv = ak.live_lesen(self.tmp.name)
        self.assertEqual(len(lv["zeilen"]), 3)
        for p in Path(self.tmp.name).rglob("*"):
            if p.is_file():
                self.assertNotIn(TOKEN, p.read_text(encoding="utf-8"))

    def test_verlauf_aufraeumen(self):
        vd = Path(self.tmp.name) / "live_verlauf"
        vd.mkdir()
        for tag in ("2026-11-19", "2026-11-20", "2026-11-21"):
            (vd / f"{tag}.jsonl").write_text("{}\n")
        self.ar.uebernehmen([z("2026-11-01", "registrierungen", 3)], "t")
        (Path(self.tmp.name) / "log.jsonl").open("a").write('{"typ":"wert"}\n')           # beschaedigte Zeile wird uebersprungen
        self.lauf(T0, FakeLive([]))
        self.assertEqual(sorted(p.stem for p in vd.glob("*.jsonl")), ["2026-11-20", "2026-11-21", "2026-11-27"])
        self.assertEqual(len(self.ar.werte()), 1)                                         # Tageswerte unberuehrt


class TestFehler(_Basis):
    def test_401_haelt_an_bis_zur_freigabe(self):
        f = FakeLive([ak.AbrufFehler(401, "x")])
        self.lauf(T0, f)
        self.assertEqual(len(self.mel), 1)
        self.assertIn("401", self.mel[0][0])
        for m in (15, 30, 120):
            self.assertTrue(self.lauf(T0 + timedelta(minutes=m), f).get("gestoppt"))
        self.assertEqual(f.aufrufe, 1)                                                     # Gegenprobe: kein Abruf
        self.assertIn("401", ak.stoerung(self.ar, env={ak.TOKEN_ENV: TOKEN}) or "")
        ak.live_einstellen(self.tmp.name, freigeben=True, jetzt=T0 + timedelta(minutes=121))
        self.assertTrue(self.lauf(T0 + timedelta(minutes=122), f)["ok"])
        self.assertFalse(ak.live_ansicht(self.ar, jetzt=T0 + timedelta(minutes=123))["gestoppt"])

    def test_ab_vier_fehlschlaegen_genau_eine_meldung(self):
        f502 = ak.AbrufFehler(502, "x")
        f = FakeLive([f502] * 6 + [live()] + [f502] * 4)
        for i in range(11):
            self.lauf(T0 + timedelta(minutes=15 * i), f)
            if i == 2:
                self.assertEqual(self.mel, [])                                             # 3 Fehlschlaege: still
        texte = [m[0] for m in self.mel]
        self.assertEqual(sum("nicht erreichbar" in t for t in texte), 2)                  # je Stoerungsphase einmal
        self.assertEqual(f.aufrufe, 11)                                                    # nie sofort wiederholt


class TestMeilensteine(_Basis):
    def test_nicht_doppelt_auch_bei_sinkendem_wert(self):
        self.ar.melden_vermerken("meilenstein-basis", "t")                                 # Basis vom Tagesabruf
        self.ar.melden_vermerken("meilenstein:abo:100", "t")
        f = FakeLive([live({"registrierte_stand": 999, "abo_aequivalente": 120}),
                      live({"registrierte_stand": 1001, "abo_aequivalente": 251}),
                      live({"registrierte_stand": 998, "abo_aequivalente": 249}),
                      live({"registrierte_stand": 1002, "abo_aequivalente": 252})])
        for i in range(4):
            self.lauf(T0 + timedelta(minutes=15 * i), f)
        m = [t for t, _ in self.mel if "🎉" in t]
        self.assertEqual(len(m), 2)
        self.assertTrue(any("1.000 registrierte" in t for t in m) and any("250 Abo" in t for t in m))
        ak.pruefen(self.ar, jetzt=T0 + timedelta(days=1), notify=self.notify)             # Tagesabruf meldet nicht erneut
        self.assertEqual(len([t for t, _ in self.mel if "🎉" in t]), 2)


class TestAnsichtUndAbgleich(_Basis):
    def test_veraltet_ab_45_minuten(self):
        self.lauf(T0, FakeLive([]))
        self.assertFalse(ak.live_ansicht(self.ar, jetzt=T0 + timedelta(minutes=45))["veraltet"])
        self.assertTrue(ak.live_ansicht(self.ar, jetzt=T0 + timedelta(minutes=46))["veraltet"])
        s = ak.live_status(self.ar, jetzt=T0)
        self.assertEqual((s["kennzahlen"], s["verlauf_heute"]), (3, 1))
        self.assertNotIn("768", json.dumps(s))                                             # Status ohne Werte

    def test_live_abgleich(self):
        self.lauf(T0, FakeLive([live({"registrierte_stand": 768, "registrierungen": 4}) + [z("2026-11-27", "tipps", 10, dim1="ergebnis")]]))
        text = ("datum\tkennzahl\tdim1\tdim2\twert\tstand\n"
                "2026-11-27\tregistrierte_stand\t\t\t768\t2026-11-27 12:00:00+00\n"
                "2026-11-27\tregistrierungen\tNULL\tNULL\t5\t2026-11-27 12:00:00+00\n"
                "2026-11-27\ttipps\tergebnis\t\t10\t2026-11-27 12:00:00+00\n")
        r = ak.live_abgleich(self.ar, text)
        self.assertTrue(r["gleich"], r)
        self.assertEqual((r["knapp"], r["abweichend"]), (1, 0))                           # Zaehler +1 = knapp
        r = ak.live_abgleich(self.ar, text.replace("\t768\t", "\t770\t"))
        self.assertEqual(r["abweichend"], 1)                                               # Gegenprobe
        self.assertFalse(ak.live_abgleich(self.ar, "nix")["ok"])
        r = ak.live_abgleich(self.ar, "| 2026-11-27 | registrierte_stand | | | 768 | x |")
        self.assertEqual(r["zeilen"][[x["kennzahl"] for x in r["zeilen"]].index("registrierte_stand")]["stufe"], "gleich")


class TestApi(ApiBasis):
    def test_nur_ceo(self):
        with tempfile.TemporaryDirectory() as t:
            ar = ak.Archiv(t)
            with mock.patch.object(self.w, "_app_archiv", return_value=ar):
                self.assertTrue(self.c.get("/api/app-kennzahlen/live").json()["ok"])
                self.assertFalse(self.c.post("/api/app-kennzahlen/live/einstellung", json={"takt_min": 10}).json()["ok"])
                self.assertEqual(self.c.post("/api/app-kennzahlen/live/einstellung", json={"bestaetigt": True, "takt_min": 10}).json()["takt_min"], 10)
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    for url in ("/api/app-kennzahlen/live", "/api/app-kennzahlen/live/status"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
                    for url in ("/api/app-kennzahlen/live/einstellung", "/api/app-kennzahlen/live/abgleich"):
                        self.assertEqual(self.c.post(url, json={"bestaetigt": True}).status_code, 403, url)


if __name__ == "__main__":
    unittest.main()
