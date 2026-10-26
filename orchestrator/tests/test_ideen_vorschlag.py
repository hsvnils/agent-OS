"""KUNDEN_CHECKLISTE C3: 3 Ideen mit Skript-Geruest aus dem Briefing -- erst mit vollstaendigem Pflicht-Briefing, nur
Briefing-Inhalte (ohne Freigabe-Personen/Notizen) ans Modell, Antwort gekuerzt/geprueft, nichts gespeichert; Uebernahme
als Idee mit Skript-Geruest in der Beschreibung."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from orchestrator.core.ideen_vorschlag import als_idee, fehlende, kontext, vorschlag
from orchestrator.core.konzept import KonzeptStore
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_postings import REEL

BRIEF = {"ziel": "Mehr Reservierungen", "zielgruppe": "25-40, Hamburg", "botschaft": "Bestes Schnitzel der Stadt",
         "tonalitaet": "Du, locker", "donts": "keine Politik", "freigabe_an": "Anna Muster, 0170 1234567",
         "notizen": "Inhaber privat schwierig"}
ANTWORT = {"ideen": [{"titel": f"Idee {n}", "beschreibung": "B" * 2000, "format": "Reel", "ziel": "Reservierungen",
                      "hook": "Hook", "text": "Ablauf", "cta": "Jetzt reservieren", "laenge": "20 s", "boese": "x"}
                     for n in range(5)] + [{"titel": ""}]}


class _Client:
    def __init__(self, antwort):
        self.gesehen, self.antwort = [], antwort
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kw):
        self.gesehen.append(kw["messages"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.antwort))])


class TestIdeenVorschlag(unittest.TestCase):
    def setUp(self):
        bh, ks, st, k, ap = _stores()
        self.an = st.anlegen({"firma": k, "ansprechpartner": ap, "titel": "Herbst", "positionen": [REEL]})["nummer"]
        self.kz = KonzeptStore(bh, Path(tempfile.mkdtemp()))

    def test_1_erst_mit_pflicht_briefing(self):
        m = self.kz.mappe(self.an)
        self.assertEqual(fehlende(m), ["Ziel", "Zielgruppe", "Kernbotschaft", "Tonalität"])
        c = _Client(json.dumps(ANTWORT))
        with self.assertRaisesRegex(ValueError, "Briefing unvollständig"):
            vorschlag(m, system="s", client=c, modell="m")
        self.assertEqual(c.gesehen, [])                                       # kein Modellaufruf

    def test_2_nur_briefing_ohne_personen_und_gekuerzt(self):
        self.kz.briefing(self.an, BRIEF)
        self.kz.idee(self.an, {"titel": "Schon da"})
        m = self.kz.mappe(self.an)
        c = _Client("Hier mein Vorschlag:\n" + json.dumps(ANTWORT))
        erg = vorschlag(m, system="sys", client=c, modell="claude-sonnet-5-5", titel="Herbst")
        prompt = c.gesehen[0][1]["content"]
        for drin in ("Mehr Reservierungen", "Herbst", "Schon da", "keine Politik"):
            self.assertIn(drin, prompt)
        for raus in ("Anna Muster", "0170", "privat schwierig"):
            self.assertNotIn(raus, prompt)
        self.assertEqual(len(erg["ideen"]), 3)
        self.assertTrue(all(len(i["beschreibung"]) <= 900 and "boese" not in i for i in erg["ideen"]))
        self.assertEqual(len(m["ideen"]), len(self.kz.mappe(self.an)["ideen"]))   # nichts gespeichert
        with self.assertRaises(ValueError):
            vorschlag(m, system="s", client=_Client("kein json"), modell="m")

    def test_3_uebernahme_als_idee(self):
        i = {"titel": "Nachtschicht", "beschreibung": "Küche nachts", "format": "Reel", "ziel": "Reel 1", "hook": "Licht an",
             "text": "Schnitte", "cta": "Reservieren", "laenge": "20 s"}
        f = als_idee(i)
        self.assertIn("Skript-Gerüst", f["beschreibung"])
        self.assertIn("Hook: Licht an", f["beschreibung"])
        self.kz.idee(self.an, f)
        self.assertEqual(list(self.kz.mappe(self.an)["ideen"].values())[0]["titel"], "Nachtschicht")
        self.assertNotIn("Freigaben", kontext({"briefing": BRIEF}))


class TestIdeenApi(ApiBasis):
    def test_a1_vorschlag(self):
        an = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "T",
                                                               "positionen": [REEL]}}).json()
        nr = an.get("nummer") or (an.get("angebot") or {}).get("nummer")
        r = self.c.post(f"/api/crm/konzept-ideen/{nr}").json()
        self.assertFalse(r["ok"]); self.assertIn("Briefing unvollständig", r["hinweis"])
        self.assertTrue(self.c.post(f"/api/crm/konzept/{nr}/briefing", json={"felder": BRIEF}).json()["ok"])
        with mock.patch.object(self.w, "_cloud", return_value=(_Client(json.dumps(ANTWORT)), "claude")):
            r = self.c.post(f"/api/crm/konzept-ideen/{nr}").json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(r["ideen"]), 3)
        self.assertIn("Skript-Gerüst", r["ideen"][0]["idee_felder"]["beschreibung"])
        with mock.patch.object(self.w, "_cloud", return_value=(None, "")):
            self.assertIn("Kein Modell-Zugang", self.c.post(f"/api/crm/konzept-ideen/{nr}").json()["hinweis"])


if __name__ == "__main__":
    unittest.main()
