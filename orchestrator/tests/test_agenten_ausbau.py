"""AGENTEN_AUSBAU A1/A2/A4: Fachagenten-Anfragen werden ohne Inhalte gezaehlt, CIO/Risk sind befragbar, Agenten-Profil
(Charta, Skills, Quellen, Watcher, Nutzung) per API, Leistungsbericht „wer wird gefragt“, neue Skills fuer CFO/CCO/CRO/
CDO geladen und gegatet, CFO-Quellen im Nachtlauf aller Agenten, Watcher-Themen auf das Geschaeft ausgerichtet."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from orchestrator.core import rechtsquellen
from orchestrator.core.agenten_profil import AgentenNutzung, profil, uebersicht
from orchestrator.core.backends import MockBackend
from orchestrator.core.dept_skills import lade_dept_skills
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.hoa_tools import ToolContext, run_tool, tool_specs
from orchestrator.core.performance_agent import PerformanceAgent
from orchestrator.core.subagents import load_all_subagents
from orchestrator.core.watch_config import DEPARTMENT_WATCH, themen_fuer
from orchestrator.governance.ceo_gate_hook import CeoGate

REPO = Path(__file__).resolve().parents[2]
NEU = {"cfo": ["abschluss-check-euer", "beleg-gobd-pruefung", "liquiditaetsvorschau", "preis-margen-analyse"],
       "cco": ["briefing-zu-konzept", "content-kalender", "hook-und-skript", "reel-dramaturgie"],
       "cro": ["angebot-nachfassen", "folgeauftrag-upsell"], "cdo": ["kampagnen-auswertung"]}


def _ctx(backend, nutzung):
    core = HeadOfAgents(backend, load_all_subagents(), gate=CeoGate(), leak_secrets=[])
    return ToolContext(core=core, antraege=None, engine=None, finance_dir=REPO / "finance", repo_root=REPO,
                       leak_secrets=[], agenten_nutzung=nutzung)


def _log(tmp, zeilen):
    p = Path(tmp) / "agenten_nutzung" / "log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(z) + "\n" for z in zeilen), encoding="utf-8")
    return AgentenNutzung(p)


class TestA1Nutzung(unittest.TestCase):
    def test_1_delegate_wird_ohne_inhalt_protokolliert(self):
        n = AgentenNutzung(Path(tempfile.mkdtemp()) / "log.jsonl")
        r = run_tool("delegate", {"an": "cfo", "aufgabe": "Geheime Kundenfrage KIEZALM Umsatz"}, _ctx(MockBackend(), n))
        self.assertIn("ergebnis", r)
        e = json.loads(n.path.read_text(encoding="utf-8").strip())
        self.assertEqual((e["agent"], e["ok"], e["quelle"], e["skills"]), ("cfo", True, "delegate", 4))
        self.assertNotIn("KIEZALM", n.path.read_text(encoding="utf-8"))          # keine Inhalte im Protokoll

    def test_2_fehler_wird_gezaehlt_gate_blockiert_nicht(self):
        def kaputt(msg, ctx):
            raise RuntimeError("Modell weg")
        n = AgentenNutzung(Path(tempfile.mkdtemp()) / "log.jsonl")
        r = run_tool("delegate", {"an": "cro", "aufgabe": "Frage"}, _ctx(MockBackend({"cro": kaputt}), n))
        self.assertIn("fehler", r)
        r = run_tool("delegate", {"an": "cto", "aufgabe": "ein neues kostenpflichtiges Tool beschaffen"},
                     _ctx(MockBackend(), n))
        self.assertTrue(r.get("blockiert"))                                      # CEO-Tor: gar keine Anfrage
        z = n.zaehlen(datetime.now() - timedelta(days=1))
        self.assertEqual(set(z), {"cro"})
        self.assertEqual((z["cro"]["anzahl"], z["cro"]["fehler"]), (1, 1))

    def test_3_ohne_store_kein_protokoll(self):
        r = run_tool("delegate", {"an": "berater", "aufgabe": "Strategie"}, _ctx(MockBackend(), None))
        self.assertIn("ergebnis", r)

    def test_4_cio_und_risk_befragbar(self):
        n = AgentenNutzung(Path(tempfile.mkdtemp()) / "log.jsonl")
        for an in ("cio", "risk"):
            self.assertIn("ergebnis", run_tool("delegate", {"an": an, "aufgabe": "Lage?"}, _ctx(MockBackend(), n)))
        spec = next(t for t in tool_specs() if t["name"] == "delegate")
        self.assertIn("cio", json.dumps(spec)), self.assertIn("risk", json.dumps(spec))

    def test_5_zaehlen_nach_fenster(self):
        jetzt = datetime(2026, 10, 5, 12)
        n = _log(tempfile.mkdtemp(), [
            {"ts": "2026-10-04T10:00:00", "agent": "cfo", "ok": True, "dauer_ms": 2000},
            {"ts": "2026-10-03T10:00:00", "agent": "cfo", "ok": True, "dauer_ms": 4000},
            {"ts": "2026-08-01T10:00:00", "agent": "cfo", "ok": False, "dauer_ms": 9000},
            {"ts": "2026-10-04T11:00:00", "agent": "cco", "ok": True, "dauer_ms": 1000}])
        z30 = n.zaehlen(jetzt - timedelta(days=30), jetzt)
        self.assertEqual((z30["cfo"]["anzahl"], z30["cfo"]["fehler"], z30["cfo"]["median_s"]), (2, 0, 4.0))
        self.assertEqual(n.zaehlen(jetzt - timedelta(days=90), jetzt)["cfo"]["anzahl"], 3)


class TestZeitzone(unittest.TestCase):
    """BF-57: Container laufen in UTC -- das Protokoll schreibt deutsche Zeit mit Zeitzone, liest Alt-Eintraege als UTC."""
    def test_deutsche_zeit_unter_utc(self):
        import os
        import time
        alt = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        time.tzset()
        try:
            n = AgentenNutzung(Path(tempfile.mkdtemp()) / "log.jsonl")
            n.erfassen("cfo", ok=True, dauer_ms=1, quelle="werkzeug")
            ts = json.loads(n.path.read_text(encoding="utf-8"))["ts"]
            self.assertRegex(ts, r"\+0[12]:00$")                                 # deutsche Zeit mit Zeitzone
            jetzt_utc = datetime.now()                                           # naive = Container-Zeit (UTC)
            z = n.zaehlen(jetzt_utc - timedelta(minutes=5), jetzt_utc + timedelta(minutes=5))
            self.assertEqual(z["cfo"]["anzahl"], 1)
            # Alt-Eintrag ohne Zeitzone (UTC, vor dem Fix) wird als UTC gelesen und deutsch angezeigt
            with n.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": "2026-10-05T12:52:44", "agent": "clo", "ok": True, "dauer_ms": 5}) + "\n")
            z = n.zaehlen(datetime(2026, 10, 5, 12), datetime(2026, 10, 5, 13))
            self.assertEqual(z["clo"]["zuletzt"], "2026-10-05T14:52:44+02:00")
        finally:
            if alt is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = alt
            time.tzset()


class TestA1Profil(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.watch = Path(self.tmp) / "watch.jsonl"
        self.watch.write_text("".join(json.dumps(z) + "\n" for z in [
            {"ts": "2026-10-01T09:00:00", "typ": "finding", "abteilung": "cfo", "titel": "E-Rechnung neu", "url": "https://a"},
            {"ts": "2026-10-02T09:00:00", "typ": "finding", "abteilung": "cfo", "titel": "GoBD", "url": "https://b"},
            {"ts": "2026-10-02T09:00:00", "typ": "finding", "abteilung": "cto", "titel": "x", "url": "https://c"},
            {"ts": "2026-10-02T09:00:00", "typ": "run", "job": "dept:cfo"}]), encoding="utf-8")
        self.n = _log(self.tmp, [{"ts": "2026-10-04T10:00:00", "agent": "cfo", "ok": True, "dauer_ms": 2000}])

    def test_1_profil_cfo(self):
        p = profil(REPO, "cfo", watch_log=self.watch, nutzung=self.n, jetzt=datetime(2026, 10, 5))
        self.assertEqual(p["charta"]["status"], "aktiv")
        self.assertEqual(sorted(s["name"] for s in p["skills"] if s["geladen"]), NEU["cfo"])
        self.assertGreaterEqual(len(p["quellen"]), 9)
        self.assertTrue(all(q["stand"] and q["pruefen_bis"] for q in p["quellen"]))
        self.assertEqual([f["titel"] for f in p["funde"]], ["GoBD", "E-Rechnung neu"])  # neueste zuerst
        self.assertEqual((p["funde_gesamt"], p["nutzung"]["tage30"]["anzahl"]), (2, 1))
        self.assertIn("Kleinunternehmerregelung Aenderung 2026", p["watcher"])

    def test_2_alias_und_unbekannt(self):
        self.assertEqual(profil(REPO, "researcher", watch_log=self.watch, nutzung=self.n)["key"], "res")
        self.assertEqual(profil(REPO, "hoa", watch_log=self.watch, nutzung=self.n)["skills"], [])
        with self.assertRaises(KeyError):
            profil(REPO, "../agents/x", watch_log=self.watch, nutzung=self.n)

    def test_3_uebersicht_alle_agenten(self):
        u = {x["key"]: x for x in uebersicht(REPO, watch_log=self.watch, nutzung=self.n)}
        self.assertEqual(len(u), 19)                                             # HoA + 15 + CIO + Risk + Videograf
        self.assertEqual((u["cfo"]["skills"], u["cfo"]["funde"], u["cfo"]["nutzung30"]), (4, 2, 1))
        self.assertEqual(u["clo"]["skills"], 7)

    def test_4_api(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        c = TestClient(webapp.app)
        r = c.get("/api/agenten/cco/profil")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["skills"]), 4)
        self.assertEqual(c.get("/api/agenten/gibtsnicht/profil").status_code, 404)
        self.assertEqual(len(c.get("/api/agenten-uebersicht").json()["agenten"]), 19)


class TestA1Leistungsbericht(unittest.TestCase):
    def test_wer_wird_gefragt(self):
        jetzt = datetime.now()
        ts = lambda tage: (jetzt - timedelta(days=tage)).isoformat(timespec="seconds")
        n = _log(tempfile.mkdtemp(), [{"ts": ts(1), "agent": "cfo", "ok": True, "dauer_ms": 1},
                                      {"ts": ts(2), "agent": "cfo", "ok": True, "dauer_ms": 1},
                                      {"ts": ts(3), "agent": "clo", "ok": False, "dauer_ms": 1},
                                      {"ts": ts(9), "agent": "cro", "ok": True, "dauer_ms": 1}])
        a = PerformanceAgent(fachagenten=n)
        b = a.bericht(jetzt)
        self.assertEqual(b["woche"]["fachagenten"], {"anfragen": 3, "fehler": 1, "direkt": 3, "werkzeug": 0,
                                                       "je_agent": {"cfo": 2, "clo": 1}})
        self.assertEqual(b["vorwoche"]["fachagenten"]["anfragen"], 1)
        self.assertIn("Fachagenten: 3 Anfragen", a.als_text(b))
        self.assertIn("cfo (2)", a.als_text(b))
        self.assertNotIn("Fachagenten", PerformanceAgent().als_text())           # ohne Store keine Zeile


class TestA2Skills(unittest.TestCase):
    def test_1_neue_skills_geladen_und_im_prompt(self):
        for key, namen in NEU.items():
            _, meta = lade_dept_skills(key, REPO)
            geladen = {m["skill"] for m in meta if m["geladen"]}
            self.assertTrue(set(namen) <= geladen, (key, geladen))
            self.assertTrue(all(m["verdikt"] != "abgelehnt" for m in meta))
        spec = load_all_subagents()["cfo"]
        self.assertIn("### Skill: beleg-gobd-pruefung", spec.system_prompt)
        self.assertIn("UStDV § 34a", spec.system_prompt)

    def test_2_cfo_quellen_amtlich_mit_stand(self):
        qs = rechtsquellen.quellen(REPO / "skills" / "cfo")
        self.assertEqual({q["norm"] for q in qs}, {"UStG § 14", "UStG § 14c", "UStDV § 34a", "AO § 146", "AO § 147",
                                                   "EStG § 4", "EStG § 6", "EStG § 11", "AO § 141"})
        self.assertTrue(all(q["agent"] == "cfo" and q["stand"] == "2026-10-05" and q["pruefen_bis"] == "2027-04-05"
                            for q in qs))
        gobd = (REPO / "skills" / "cfo" / "beleg-gobd-pruefung" / "quellen.md").read_text(encoding="utf-8")
        self.assertIn("GoBD", gobd)                                              # nur Verweis, kein Wortlaut

    def test_3_nachtlauf_ueber_alle_agenten(self):
        alle = rechtsquellen.quellen(REPO / "skills")
        self.assertEqual({q["agent"] for q in alle}, {"clo", "cfo", "ciso", "chro"})
        roh = {}
        for f in (REPO / "skills").rglob("quellen.md"):
            for m in rechtsquellen.KOPF.finditer(f.read_text(encoding="utf-8")):
                roh[m["url"]] = "\n".join(z[2:] for z in m["text"].strip("\n").split("\n"))
        url = "https://www.gesetze-im-internet.de/ao_1977/__147.html"
        holen = lambda u: f'<div class="jnhtml"><div>{roh[u] + (" (neu)" if u == url else "")}</div>\n</div>'
        gemeldet = []
        erg = rechtsquellen.lauf(REPO / "skills", Path(tempfile.mkdtemp()) / "rq.json",
                                 lambda text, **kw: gemeldet.append(text), heute=date(2026, 10, 6), holen=holen)
        self.assertEqual([(g["agent"], g["norm"]) for g in erg["geaendert"]], [("cfo", "AO § 147")])
        self.assertIn("CFO/beleg-gobd-pruefung", gemeldet[0])
        # Gegenprobe: ohne Aenderung keine Meldung
        gemeldet.clear()
        holen_alt = lambda u: f'<div class="jnhtml"><div>{roh[u]}</div>\n</div>'
        erg = rechtsquellen.lauf(REPO / "skills", Path(tempfile.mkdtemp()) / "rq.json",
                                 lambda text, **kw: gemeldet.append(text), heute=date(2026, 10, 6), holen=holen_alt)
        self.assertEqual((erg["geaendert"], gemeldet), ([], []))


PAKET2 = {"ciso": ["datenschutz-check", "secret-hygiene", "zugriffs-pruefung"],
           "cto": ["deploy-checkliste", "fehlersuche", "release-notizen"], "res": ["quellenbewertung"],
           "chro": ["freien-abrechnung", "freien-briefing", "freien-vereinbarung-pruefen"],
           "cko": ["clip-suche", "quellenpflege", "wissen-ablegen"],
           "cpo": ["funktionsantrag-bewerten", "nutzungsdaten-auswerten"],
           "cxo": ["kunden-dokument-pruefen", "mobil-check"], "cao": ["dienstleister-vertrag-pruefen", "fristen-uebersicht"]}


class TestPaket2Skills(unittest.TestCase):
    def test_1_a3_a5_skills_geladen(self):
        alle = load_all_subagents()
        for key, namen in PAKET2.items():
            _, meta = lade_dept_skills(key, REPO)
            self.assertEqual(sorted(m["skill"] for m in meta if m["geladen"]), namen, key)
            for n in namen:
                self.assertIn(f"### Skill: {n}", alle[key].system_prompt)

    def test_2_quellen_ciso_chro(self):
        qs = rechtsquellen.quellen(REPO / "skills")
        self.assertEqual({q["norm"] for q in qs if q["agent"] == "ciso"}, {"TDDDG § 25", "BDSG § 26", "BDSG § 38"})
        self.assertEqual({q["norm"] for q in qs if q["agent"] == "chro"}, {"SGB IV § 7", "SGB IV § 7a"})
        self.assertIn("https://www.gesetze-im-internet.de/ttdsg/__25.html", {q["url"] for q in qs})
        ds = (REPO / "skills" / "ciso" / "datenschutz-check" / "quellen.md").read_text(encoding="utf-8")
        self.assertIn("DSGVO", ds)                                               # Verweis, kein Wortlaut

    def test_3_profil_researcher_und_rand_agenten(self):
        n, w = AgentenNutzung(Path(tempfile.mkdtemp()) / "n.jsonl"), Path(tempfile.mkdtemp()) / "w.jsonl"
        u = {x["key"]: x for x in uebersicht(REPO, watch_log=w, nutzung=n)}
        self.assertEqual({k: u[k]["skills"] for k in PAKET2}, {k: len(v) for k, v in PAKET2.items()})
        self.assertEqual(profil(REPO, "researcher", watch_log=w, nutzung=n)["skills"][0]["name"], "quellenbewertung")
        self.assertEqual([k for k, x in u.items() if x["skills"] == 0], ["hoa", "cio", "risk"])
        self.assertEqual(u["vid"]["skills"], 5)                                 # VIDEOGRAF V2


class TestA4Watcher(unittest.TestCase):
    def test_themen_auf_das_geschaeft(self):
        self.assertEqual(len(DEPARTMENT_WATCH), 15)
        for key, t in DEPARTMENT_WATCH.items():
            self.assertTrue(3 <= len(t["suche"]) <= 8, key)                     # token-frugal
        self.assertTrue(any("Kleinunternehmer" in s for s in themen_fuer("cfo")["suche"]))
        self.assertTrue(any("Fussball" in s for s in themen_fuer("cco")["suche"]))
        self.assertTrue(any("Influencer Preise" in s for s in themen_fuer("cro")["suche"]))
        alt = {"LLM API pricing changes", "AI sales automation", "AI video generation tools", "AI recruiting tools"}
        self.assertFalse(alt & {s for t in DEPARTMENT_WATCH.values() for s in t["suche"]})


if __name__ == "__main__":
    unittest.main()
