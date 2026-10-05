"""CLO_AUSBAU C1-C4: Skills geladen und gegatet, Rechtsquellen mit Stand/Pruefdatum, naechtlicher Abgleich meldet nur
neue Aenderungen, Pruef-Lauf parst/validiert die Modell-Antwort, Version 2 nur per Klick und nur einmal."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from orchestrator.core import clo_pruefung, rechtsquellen
from orchestrator.core.charter_loader import load_subagent
from orchestrator.core.dept_skills import lade_dept_skills
from orchestrator.core.vertrag_entwuerfe import ENTWUERFE
from orchestrator.tests.test_angebote import ApiBasis

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills" / "clo"


class _Seite:
    """Fake fuer gesetze-im-internet.de: liefert den gespeicherten Wortlaut, optional veraendert."""
    def __init__(self, aendern=()):
        self.aendern, self.texte = set(aendern), {q["url"]: q for q in rechtsquellen.quellen(SKILLS)}
        self.roh = {}
        for f in SKILLS.glob("*/quellen.md"):
            for m in rechtsquellen.KOPF.finditer(f.read_text(encoding="utf-8")):
                self.roh[m["url"]] = "\n".join(z[2:] for z in m["text"].strip("\n").split("\n"))

    def __call__(self, url):
        text = self.roh[url] + (" (geaendert)" if url in self.aendern else "")
        return f'<div class="jnhtml"><div>{text}</div>\n</div>'


class TestSkills(unittest.TestCase):
    def test_1_sieben_skills_geladen_und_im_prompt(self):
        block, meta = lade_dept_skills("clo", REPO)
        self.assertEqual(sorted(m["skill"] for m in meta if m["geladen"]),
                         ["agb-pruefung", "club-und-markenrechte", "ki-kennzeichnung", "kleinunternehmer-hinweise",
                          "musik-in-videos", "nutzungsrechte", "werbekennzeichnung"])
        self.assertIn("UWG § 5a Abs. 4", block)
        self.assertIn("Entwurf -- anwaltliche Pruefung erforderlich", block)
        self.assertIn("### Skill: werbekennzeichnung", load_subagent("agents/13_clo.md", "clo").system_prompt)

    def test_2_quellen_mit_stand_und_pruefdatum(self):
        qs = rechtsquellen.quellen(SKILLS)
        self.assertGreaterEqual(len(qs), 20)
        self.assertTrue(all(q["url"].startswith("https://www.gesetze-im-internet.de/") and q["stand"] and q["pruefen_bis"] for q in qs))
        self.assertIn("UStDV § 34a", {q["norm"] for q in qs})


class TestNachtlauf(unittest.TestCase):
    def test_1_unveraendert_geaendert_einmal_melden(self):
        z = Path(tempfile.mkdtemp()) / "rq.json"
        gemeldet = []
        notify = lambda text, **kw: gemeldet.append(text)
        erg = rechtsquellen.lauf(SKILLS, z, notify, heute=date(2026, 10, 6), holen=_Seite())
        self.assertEqual((len(erg["geaendert"]), erg["fehler"], gemeldet), (0, [], []))
        url = "https://www.gesetze-im-internet.de/uwg_2004/__5a.html"
        erg = rechtsquellen.lauf(SKILLS, z, notify, heute=date(2026, 10, 7), holen=_Seite([url]))
        self.assertEqual([g["norm"] for g in erg["geaendert"]], ["UWG § 5a"])
        self.assertIn("UWG § 5a hat sich geaendert", gemeldet[0])
        rechtsquellen.lauf(SKILLS, z, notify, heute=date(2026, 10, 8), holen=_Seite([url]))
        self.assertEqual(len(gemeldet), 1)                                       # bekannt -> nicht jede Nacht wiederholen

    def test_2_pruefdatum_und_netzfehler(self):
        erg = rechtsquellen.pruefen(SKILLS, heute=date(2027, 5, 1), holen=_Seite())
        self.assertEqual(len(erg["faellig"]), 6)                                # alle Skills mit Gesetzesquellen
        def kaputt(url):
            raise OSError("Netz weg")
        erg = rechtsquellen.pruefen(SKILLS, heute=date(2026, 10, 6), holen=kaputt)
        self.assertEqual((erg["geaendert"], len(erg["fehler"])), ([], erg["geprueft"]))   # Fehler sind keine Aenderung
        self.assertIn("nicht abrufbar", rechtsquellen.meldung(erg, set()))


class _Antwort:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


class _Modell:
    def __init__(self, text):
        self.text, self.anfragen = text, []
        self.chat = type("Ch", (), {"completions": self})()

    def create(self, **kw):
        self.anfragen.append(kw)
        return _Antwort(self.text)


class TestPruefung(unittest.TestCase):
    def test_1_parsen_validieren_version2(self):
        e = ENTWUERFE["nda"]
        antwort = {"gesamt": "solide", "paragraphen": [
            {"titel": e["paragraphen"][0]["titel"], "ampel": "rot", "fundstelle": "BGB § 307", "risiko": "x", "vorschlag": "y",
             "frage_anwaeltin": "z", "neuer_text": "Neuer Text {Kunde}"},
            {"titel": "§ 99 Erfunden", "ampel": "gruen", "neuer_text": "weg"},
            {"titel": e["paragraphen"][1]["titel"], "ampel": "blau"}],
            "fehlend": [{"titel": "§ 7 Neu", "begruendung": "fehlt", "text": "Text"}]}
        m = _Modell("Hier: " + json.dumps(antwort))
        erg = clo_pruefung.pruefe_vorlage("nda", e, system="CLO", quellen="Q", client=m, modell="test")
        self.assertEqual([p["titel"] for p in erg["paragraphen"]], [p["titel"] for p in e["paragraphen"]])   # nichts erfunden
        self.assertEqual(erg["paragraphen"][1]["ampel"], "gelb")                 # unbekannte Ampel -> gelb
        self.assertIn("nicht bewertet", erg["paragraphen"][2]["risiko"])         # fehlende Bewertung sichtbar
        v2 = clo_pruefung.version2(erg, e)
        self.assertEqual((v2[0]["text"], v2[1]["text"], v2[-1]["titel"]), ("Neuer Text {Kunde}", e["paragraphen"][1]["text"], "§ 7 Neu"))
        self.assertEqual(m.anfragen[0]["messages"][0]["content"], "CLO")          # Charta+Skills als System-Prompt
        self.assertIn("Q", m.anfragen[0]["messages"][1]["content"])

    def test_2_pdf(self):
        from pypdf import PdfReader
        import io
        b = {"datum": "2026-10-05", "modell": "test", "vorlagen": [{"art": "nda", "titel": "NDA", "gesamt": "ok",
             "paragraphen": [{"titel": "§ 1 X", "ampel": "rot", "fundstelle": "BGB § 307", "risiko": "R", "vorschlag": "V",
                              "frage_anwaeltin": "F", "neuer_text": ""}], "fehlend": []}]}
        t = PdfReader(io.BytesIO(clo_pruefung.pdf(b, firmendaten={"firma": "Test"}))).pages[0].extract_text()
        self.assertIn("Frage an die Anwältin: F", t)
        self.assertIn("anwaltliche Prüfung erforderlich", t)


class TestApi(ApiBasis):
    def test_a1_version2_nur_einmal_per_klick(self):
        b = {"datum": "2026-10-05", "modell": "t", "vorlagen": [], "version2": {"nda": [{"titel": "§ 1 A", "text": "B"}]}}
        f = Path(tempfile.mkdtemp()) / "b.json"
        f.write_text(json.dumps(b), encoding="utf-8")
        with mock.patch.object(clo_pruefung, "BERICHT", f), mock.patch("orchestrator.core.clo_pruefung.bericht_laden",
                                                                       lambda pfad=f: json.loads(f.read_text())):
            self.assertFalse(self.c.post("/api/crm/vertraege/nda/clo-version", json={}).json()["ok"])   # erst v1
            self.c.post("/api/crm/vertraege/alle/entwuerfe", json={})
            r = self.c.post("/api/crm/vertraege/nda/clo-version", json={}).json()
            self.assertTrue(r["ok"], r)
            v = self.c.get("/api/crm/vertraege/nda").json()["vorlage"]["versionen"]
            self.assertEqual((v[1]["quelle"], v[1]["status"]), (clo_pruefung.QUELLE_V2, "entwurf"))
            self.assertFalse(self.c.post("/api/crm/vertraege/nda/clo-version", json={}).json()["ok"])
            self.assertTrue(self.c.get("/api/crm/vertraege-pruefung").json()["vorhanden"])


if __name__ == "__main__":
    unittest.main()
