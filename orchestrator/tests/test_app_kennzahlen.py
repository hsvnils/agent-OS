"""APP_KENNZAHLEN AK1-AK3: Abruf, Archiv (Upsert nach stand), Lauf mit Wiederholung, Meldungen, Abgleich, Datenschutz.

Gegenproben: jeder Test beschreibt, welcher falsche Code ihn rot macht. Die Testdaten sind erfunden (echtes Format
aus dem Lesetest 2026-11-26), es gibt keinen Netzzugriff.
"""
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from orchestrator.core import app_kennzahlen as ak

TOKEN = "geheim-test-token-0123456789abcdef"
ENV = {ak.TOKEN_ENV: TOKEN}
TZ = ak._tz()


def z(datum, kennzahl, wert, stand="2026-11-25T01:30:00.4+00:00", dim1="", dim2=""):
    return {"datum": datum, "kennzahl": kennzahl, "dim1": dim1, "dim2": dim2, "wert": wert, "stand": stand}


def antwort(zeilen):
    return {"ok": True, "revision": "2026-11-25.k1c", "anzahl": len(zeilen), "zeilen": zeilen}


class _Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def oeffner(body=None, code=None, merk=None):
    def f(req, timeout):
        if merk is not None:
            merk.append(req)
        if code:
            raise urllib.error.HTTPError(req.full_url, code, "x", {}, io.BytesIO(b"{}"))
        return _Resp(json.dumps(body).encode())
    return f


class FakeAbruf:
    """Ersetzt `abrufen`: liefert Zeilen je Aufruf oder wirft Fehler aus einer Liste."""

    def __init__(self, folgen):
        self.folgen = list(folgen)
        self.aufrufe = []

    def __call__(self, von, bis, **kw):
        self.aufrufe.append((von, bis))
        f = self.folgen.pop(0) if self.folgen else []
        if isinstance(f, ak.AbrufFehler):
            raise f
        return {"zeilen": f, "verworfen": 0, "anzahl": len(f), "revision": "t"}


def berlin(y, m, d, h, mi):
    return datetime(y, m, d, h, mi, tzinfo=TZ)


class AbrufTest(unittest.TestCase):
    def test_get_mit_token_und_feste_adresse(self):
        merk = []
        r = ak.abrufen("2026-11-24", "2026-11-24", env=ENV, oeffnen=oeffner(antwort([z("2026-11-24", "registrierungen", 3)]), merk=merk))
        self.assertEqual(len(r["zeilen"]), 1)
        self.assertEqual(merk[0].get_method(), "GET")
        self.assertTrue(merk[0].full_url.startswith(ak.QUELLE_URL + "?von=2026-11-24&bis=2026-11-24"))
        self.assertEqual(merk[0].get_header("Authorization"), "Bearer " + TOKEN)

    def test_token_nie_im_fehlertext(self):
        # Gegenprobe: wer den Request oder die Ausnahme-Meldung in den Fehlertext uebernimmt, macht den Test rot.
        for code in (400, 401, 500, 502, 418):
            with self.assertRaises(ak.AbrufFehler) as cm:
                ak.abrufen("2026-11-24", "2026-11-24", env=ENV, oeffnen=oeffner(code=code))
            self.assertEqual(cm.exception.status, code)
            self.assertNotIn(TOKEN, str(cm.exception))
            self.assertNotIn(TOKEN, repr(cm.exception.__dict__))
            self.assertIsNone(cm.exception.__cause__)

        def kaputt(req, timeout):
            raise OSError("Verbindung zu " + req.get_header("Authorization"))
        with self.assertRaises(ak.AbrufFehler) as cm:
            ak.abrufen("2026-11-24", "2026-11-24", env=ENV, oeffnen=kaputt)
        self.assertEqual(cm.exception.status, 0)
        self.assertNotIn(TOKEN, str(cm.exception))

    def test_ohne_token_kein_abruf(self):
        merk = []
        with self.assertRaises(ak.AbrufFehler) as cm:
            ak.abrufen("2026-11-24", "2026-11-24", env={}, oeffnen=oeffner(antwort([]), merk=merk))
        self.assertEqual(cm.exception.status, 401)
        self.assertEqual(merk, [])

    def test_schema(self):
        with self.assertRaises(ak.AbrufFehler):
            ak.schema_pruefen({"ok": False, "zeilen": []})
        with self.assertRaises(ak.AbrufFehler):
            ak.schema_pruefen(["x"])
        r = ak.schema_pruefen(antwort([z("2026-11-24", "tipps", 4, dim1="ergebnis"), z("24.11.2026", "tipps", 1),
                                        z("2026-11-24", "DROP TABLE", 1), z("2026-11-24", "tipps", "7"),
                                        z("2026-11-24", "tipps", 1, stand="gestern"), "kaputt",
                                        z("2026-11-24", "tipps", True)]))
        self.assertEqual(len(r["zeilen"]), 1)
        self.assertEqual(r["verworfen"], 6)

    def test_abschnitte_400_tage_und_bis_heute(self):
        heute = date(2027, 8, 1)
        a = ak.abschnitte("2026-05-14", "2027-09-01", heute)
        self.assertEqual(a[0], ("2026-05-14", (date(2026, 5, 14) + timedelta(days=399)).isoformat()))
        self.assertEqual(a[-1][1], "2027-08-01")                  # nie nach heute
        for x, y in a:
            self.assertLessEqual((date.fromisoformat(y) - date.fromisoformat(x)).days + 1, 400)
        self.assertEqual(len(ak.abschnitte("2026-01-01", "2026-01-01", date(2026, 1, 1))), 1)
        self.assertEqual(ak.abschnitte("2026-01-02", "2026-01-01", date(2026, 1, 5)), [])


class ArchivTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ar = ak.Archiv(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_upsert_nach_stand(self):
        # Gegenprobe: ueberschreibt der Code immer (oder nie), wird der Test rot.
        self.assertEqual(self.ar.uebernehmen([z("2026-11-24", "registrierungen", 5, "2026-11-25T01:30:00+00:00")], "t1"), (1, 0))
        self.assertEqual(self.ar.uebernehmen([z("2026-11-24", "registrierungen", 4, "2026-11-25T01:00:00+00:00")], "t2"), (0, 0))
        self.assertEqual(self.ar.uebernehmen([z("2026-11-24", "registrierungen", 5, "2026-11-25T01:30:00+00:00")], "t2"), (0, 0))
        self.assertEqual(self.ar.uebernehmen([z("2026-11-24", "registrierungen", 7, "2026-11-26T01:30:00.123456+00:00")], "t3"), (0, 1))
        w = list(self.ar.werte().values())
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["wert"], 7)
        self.assertEqual(w[0]["abgerufen_am"], "t3")
        # neues Objekt liest dieselbe Datei gleich
        self.assertEqual(list(ak.Archiv(self.tmp.name).werte().values())[0]["wert"], 7)

    def test_dimensionen_getrennt_und_unbekannte_gespeichert(self):
        n, _ = self.ar.uebernehmen([z("2026-11-24", "tipps", 1, dim1="ergebnis"), z("2026-11-24", "tipps", 2, dim1="startelf"),
                                    z("2026-11-24", "aktive_nutzer", 9)], "t")
        self.assertEqual(n, 3)
        self.assertEqual(ak.status(self.ar, env=ENV)["unbekannt"], ["aktive_nutzer"])

    def test_zeitraum(self):
        heute = date(2026, 11, 26)
        self.assertEqual(ak.zeitraum(self.ar, heute), ("2026-05-14", "2026-11-25"))
        self.ar.uebernehmen([z("2026-11-24", "registrierungen", 1)], "t")
        self.assertEqual(ak.zeitraum(self.ar, heute), ("2026-11-21", "2026-11-25"))      # gestern-3
        self.assertEqual(ak.zeitraum(self.ar, date(2026, 12, 10)), ("2026-11-21", "2026-12-09"))  # Luecke: letzter Tag-3

    def test_status_ohne_werte(self):
        self.ar.uebernehmen([z("2026-11-24", "abo_mrr_brutto", 1234.56, dim1="gesamt")], "t")
        s = json.dumps(ak.status(self.ar, env=ENV))
        self.assertNotIn("1234", s)                                   # Gegenprobe: Werte im Status -> rot
        self.assertIn('"abo_mrr_brutto": 1', s)


class LaufTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ar = ak.Archiv(self.tmp.name)
        self.ar.uebernehmen([z("2026-11-20", "registrierungen", 1)], "t0")     # nicht leer -> wartet auf 06:30
        self.mel = []

    def tearDown(self):
        self.tmp.cleanup()

    def notify(self, text, **kw):
        self.mel.append((text, kw))

    def test_erst_ab_0630(self):
        f = FakeAbruf([[z("2026-11-25", "registrierungen", 2)]])
        self.assertFalse(ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 29), abruf=f, notify=self.notify)["abgeholt"])
        self.assertTrue(ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 30), abruf=f, notify=self.notify)["abgeholt"])
        self.assertEqual(f.aufrufe, [("2026-11-17", "2026-11-25")])
        self.assertFalse(ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 31), abruf=f, notify=self.notify)["abgeholt"])

    def test_leeres_archiv_sofort(self):
        leer = ak.Archiv(Path(self.tmp.name) / "leer")
        f = FakeAbruf([[z("2026-11-25", "registrierungen", 2)]])
        self.assertTrue(ak.lauf(leer, jetzt=berlin(2026, 11, 26, 3, 0), abruf=f)["abgeholt"])
        self.assertEqual(f.aufrufe, [("2026-05-14", "2026-11-25")])

    def test_502_wiederholt_nach_5_15_45(self):
        f502 = ak.AbrufFehler(502, "x")
        f = FakeAbruf([f502, f502, f502, f502, []])
        t0 = berlin(2026, 11, 26, 6, 30)
        plan = [(0, True), (4, False), (5, True), (19, False), (20, True), (64, False), (65, True), (200, False)]
        for minuten, erwartet in plan:
            r = ak.lauf(self.ar, jetzt=t0 + timedelta(minutes=minuten), abruf=f, notify=self.notify)
            self.assertEqual(r["abgeholt"], erwartet, minuten)
        self.assertEqual(len(f.aufrufe), 4)
        texte = [m[0] for m in self.mel]
        self.assertEqual(sum("Zwei Abrufe" in t for t in texte), 1)          # nur einmal gemeldet
        self.assertEqual(sum("Alle Abrufversuche" in t for t in texte), 1)
        self.assertTrue(all(m[1]["quelle"] == ak.QUELLE and m[1]["nach_briefing"] is False for m in self.mel))

    def test_401_sofort_melden_nicht_wiederholen(self):
        # Gegenprobe: wiederholt der Code nach 401, gibt es einen zweiten Aufruf -> rot.
        f = FakeAbruf([ak.AbrufFehler(401, "x"), []])
        t0 = berlin(2026, 11, 26, 6, 30)
        ak.lauf(self.ar, jetzt=t0, abruf=f, notify=self.notify)
        self.assertEqual(len(self.mel), 1)
        self.assertIn("401", self.mel[0][0])
        for m in (5, 20, 65, 300):
            ak.lauf(self.ar, jetzt=t0 + timedelta(minutes=m), abruf=f, notify=self.notify)
        self.assertEqual(len(f.aufrufe), 1)
        self.assertEqual(len(self.mel), 1)

    def test_400_nicht_wiederholen(self):
        f = FakeAbruf([ak.AbrufFehler(400, "x"), []])
        t0 = berlin(2026, 11, 26, 6, 30)
        for m in (0, 5, 20, 65):
            ak.lauf(self.ar, jetzt=t0 + timedelta(minutes=m), abruf=f, notify=self.notify)
        self.assertEqual(len(f.aufrufe), 1)

    def test_naechster_tag_neuer_versuch(self):
        f = FakeAbruf([ak.AbrufFehler(401, "x"), []])
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 30), abruf=f, notify=self.notify)
        self.assertTrue(ak.lauf(self.ar, jetzt=berlin(2026, 11, 27, 6, 30), abruf=f, notify=self.notify)["abgeholt"])


class MeldungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ar = ak.Archiv(self.tmp.name)
        self.mel = []

    def tearDown(self):
        self.tmp.cleanup()

    def notify(self, text, **kw):
        self.mel.append(text)

    def basis(self, extra=(), stand="2026-11-26T01:30:00+00:00", aeq=50, reg=1500):
        zeilen = [z("2026-11-25", "tagesabschluss_lauf", 1, stand), z("2026-11-25", "abo_aequivalente", aeq, stand),
                  z("2026-11-25", "registrierte_gesamt", reg, stand)] + list(extra)
        return zeilen

    def test_frische_erst_0645_und_einmal(self):
        f = FakeAbruf([[z("2026-11-25", "registrierungen", 1)]])
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 30), abruf=f, notify=self.notify)
        self.assertEqual(self.mel, [])                                  # 06:44 und frueher: noch nicht
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 44), abruf=f, notify=self.notify)
        self.assertEqual(self.mel, [])
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 6, 45), abruf=f, notify=self.notify)
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 7, 45), abruf=f, notify=self.notify)
        self.assertEqual(len(self.mel), 1)
        self.assertIn("Tagesabschluss", self.mel[0])

    def test_frische_zu_alt(self):
        f = FakeAbruf([self.basis(stand="2026-11-24T23:00:00+00:00")])   # 31 h vor 07:00 Berlin
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 7, 0), abruf=f, notify=self.notify)
        self.assertTrue(any("älter als 30" in t for t in self.mel))
        # frischer stand -> keine Meldung
        ar2 = ak.Archiv(Path(self.tmp.name) / "b")
        mel2 = []
        ak.lauf(ar2, jetzt=berlin(2026, 11, 26, 7, 0), abruf=FakeAbruf([self.basis()]), notify=lambda t, **k: mel2.append(t))
        self.assertFalse(any("Tagesabschluss" in t for t in mel2))

    def test_moderation_cron_function(self):
        extra = [z("2026-11-25", "moderation_aeltester_stunden", 30, dim1="meldungen"),
                 z("2026-11-25", "moderation_aeltester_stunden", 24, dim1="fangesaenge"),
                 z("2026-11-25", "cron_fehlschlaege", 1, dim1="job-a"),
                 z("2026-11-25", "function_fehler", 6)]
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 7, 0), abruf=FakeAbruf([self.basis(extra)]), notify=self.notify)
        t = " ".join(self.mel)
        self.assertIn("meldungen", t)
        self.assertNotIn("fangesaenge", t)                               # 24 ist nicht ueber 24
        self.assertIn("Cronjobs", t)
        self.assertIn("Function-Fehler", t)
        n = len(self.mel)
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 8, 0), abruf=FakeAbruf([]), notify=self.notify)
        self.assertEqual(len(self.mel), n)                              # nicht doppelt

    def test_function_fehler_grenze(self):
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 7, 0), abruf=FakeAbruf([self.basis([z("2026-11-25", "function_fehler", 5)])]),
                notify=self.notify)
        self.assertFalse(any("Function" in t for t in self.mel))

    def test_meilensteine_erst_nach_basis_und_einmal(self):
        # Erster Abruf: bereits erreichte Schwellen still vermerken (Gegenprobe: sonst 1.000-Meldung beim Erstabruf).
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 26, 7, 0), abruf=FakeAbruf([self.basis(aeq=120, reg=1500)]), notify=self.notify)
        self.assertFalse(any("🎉" in t for t in self.mel))
        ar_zeilen = [z("2026-11-26", "abo_aequivalente", 260, "2026-11-27T01:30:00+00:00"),
                     z("2026-11-26", "registrierte_gesamt", 2100, "2026-11-27T01:30:00+00:00"),
                     z("2026-11-26", "tagesabschluss_lauf", 1, "2026-11-27T01:30:00+00:00")]
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 27, 6, 30), abruf=FakeAbruf([ar_zeilen]), notify=self.notify)
        m = [t for t in self.mel if "🎉" in t]
        self.assertEqual(len(m), 2)
        self.assertTrue(any("250 Abo" in t for t in m))
        self.assertTrue(any("2.000 registrierte" in t for t in m))
        ak.lauf(self.ar, jetzt=berlin(2026, 11, 28, 6, 30), abruf=FakeAbruf([ar_zeilen]), notify=self.notify)
        self.assertEqual(len([t for t in self.mel if "🎉" in t]), 2)    # nicht taeglich


class AuswertungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ar = ak.Archiv(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fehlende_zeile_null_ausser_vor_ab(self):
        self.ar.uebernehmen([z("2026-11-20", "registrierungen", 3), z("2026-11-25", "abos_aktiv", 9, dim1="gesamt"),
                             z("2026-11-20", "registrierte_gesamt", 100), z("2026-11-25", "kontoloeschungen", 1)], "t")
        d = ak.auswertung(self.ar, "7", heute=date(2026, 11, 26))
        self.assertEqual(d["tage"][0], "2026-11-19")
        r = {x["kennzahl"]: x["werte"] for x in d["reihen"]}
        self.assertEqual(r["registrierungen"], [0, 3, 0, 0, 0, 0, 0])
        self.assertEqual(r["abos_aktiv"], [None] * 6 + [9])            # Momentaufnahme: keine 0 erfinden
        self.assertEqual(r["registrierte_gesamt"][1], 100)
        self.assertIsNone(r["registrierte_gesamt"][2])                 # Bestand: keine 0 erfinden
        self.assertEqual(r["kontoloeschungen"], [None] * 6 + [1])      # vor Messbeginn 25.11. keine Daten

    def test_saison(self):
        self.assertEqual(ak.saison_start(date(2026, 11, 26)), date(2026, 7, 1))
        self.assertEqual(ak.saison_start(date(2027, 3, 1)), date(2026, 7, 1))
        self.assertEqual(ak.saison_start(date(2027, 7, 1)), date(2027, 7, 1))

    def test_abgleich(self):
        self.ar.uebernehmen([z("2026-11-24", "tipps", 4, dim1="ergebnis"), z("2026-11-24", "tipps", 2, dim1="startelf"),
                             z("2026-11-24", "push_quote", 0.25, dim1="ios")], "t")
        text = "kennzahl | zeilen | summe | stand\ntipps | 2 | 6 | 2026-11-25\npush_quote\t1\t0.25\t2026-11-25"
        r = ak.abgleich(self.ar, "2026-11-24", text)
        self.assertTrue(r["gleich"], r)
        # Gegenprobe: abweichende Summe -> nicht gleich
        r = ak.abgleich(self.ar, "2026-11-24", "tipps,2,7\npush_quote,1,0.25")
        self.assertFalse(r["gleich"])
        self.assertEqual(r["abweichend"], 1)
        # fehlt eine Kennzahl auf einer Seite -> nicht gleich
        self.assertFalse(ak.abgleich(self.ar, "2026-11-24", "tipps,2,6")["gleich"])
        self.assertFalse(ak.abgleich(self.ar, "2026-11-24", "nix")["ok"])


class DatenschutzTest(unittest.TestCase):
    """App-Zahlen gehen an kein KI-Modell: nicht in Chat-Werkzeuge und nicht in den Chat-Verlauf des Bots."""

    def test_chat_werkzeuge_blenden_app_meldungen_aus(self):
        from orchestrator.core.antraege import Antraege
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        from orchestrator.core.notifications import Notifications
        from orchestrator.core.hoa import HeadOfAgents
        from orchestrator.governance.ceo_gate_hook import CeoGate
        from orchestrator.core.backends import MockBackend
        from orchestrator.core.subagents import load_all_subagents
        root = Path(ak.__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as t:
            n = Notifications(Path(t) / "log.jsonl")
            nid = n.enqueue("📱 App: 🎉 250 Abo-Äquivalente erreicht", quelle=ak.QUELLE, nach_briefing=False)
            n.enqueue("andere Meldung", quelle="x", nach_briefing=False)
            ctx = ToolContext(core=HeadOfAgents(MockBackend(), load_all_subagents(), gate=CeoGate()),
                              antraege=Antraege(Path(t) / "a.jsonl"), engine=None, finance_dir=root / "finance",
                              repo_root=root, leak_secrets=[], notifications=n)
            offen = run_tool("benachrichtigungen_zeigen", {}, ctx)
            self.assertEqual([o["text"] for o in offen["offen"]], ["andere Meldung"])
            d = run_tool("meldung_details", {"id": nid}, ctx)
            self.assertNotIn("250", json.dumps(d, ensure_ascii=False))

    def test_bot_gibt_app_meldung_nicht_in_den_chat(self):
        src = (Path(ak.__file__).resolve().parents[1] / "channels" / "telegram" / "bot.py").read_text(encoding="utf-8")
        i = src.index("if n.get(\"quelle\") == \"app_kennzahlen\":")
        self.assertLess(i, src.index("conv.messages.append({\"role\": \"user\", \"content\": kontext})"))


if __name__ == "__main__":
    unittest.main()


from orchestrator.tests.test_angebote import ApiBasis  # noqa: E402
from unittest import mock  # noqa: E402


class ApiTest(ApiBasis):
    def test_nur_ceo_und_glocke(self):
        with tempfile.TemporaryDirectory() as t:
            ar = ak.Archiv(Path(t) / "app_kennzahlen")
            ar.uebernehmen([z("2026-11-24", "registrierungen", 3)], "t")
            with mock.patch.object(self.w, "_app_archiv", return_value=ar), mock.patch.dict("os.environ", ENV):
                r = self.c.get("/api/app-kennzahlen/status").json()
                self.assertEqual(r["zeilen"], 1)
                self.assertTrue(self.c.get("/api/app-kennzahlen?zeitraum=alles").json()["ok"])
                self.assertIn("app_kennzahlen", self.c.get("/api/me").json()["apps"])
                ar.protokoll({"ts": "2026-11-26T05:30:00+00:00", "art": "lauf", "ok": False, "status": 502})
                hb = self.c.get("/api/handlungsbedarf").json()
                self.assertTrue(any(p["id"] == "app-kennzahlen" and p["bereich_id"] == "app" for p in hb["punkte"]))
                # Gegenprobe: Team-Rolle bekommt nichts (403) und keinen Glocken-Punkt
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen", "administration"]}):
                    for url in ("/api/app-kennzahlen/status", "/api/app-kennzahlen"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
                    self.assertEqual(self.c.post("/api/app-kennzahlen/abrufen").status_code, 403)
                    self.assertEqual(self.c.post("/api/app-kennzahlen/abgleich", json={}).status_code, 403)
                    hb = self.c.get("/api/handlungsbedarf").json()
                    self.assertFalse(any(p["id"] == "app-kennzahlen" for p in hb["punkte"]))
