"""VIDEOGRAF V2/V3: Agent 17 laedt seine 5 Skills; Vorschlaege in der Konzept-Mappe -- Kontext ohne Kontaktdaten,
Antwort validiert, nichts gespeichert, Szenen nur per Klick (mit Quelle) uebernommen, Nutzung gezaehlt."""
import json
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core import videograf
from orchestrator.core.dept_skills import lade_dept_skills
from orchestrator.core.subagents import load_all_subagents
from orchestrator.tests.test_angebote import POS, ApiBasis

REPO = Path(__file__).resolve().parents[2]
ANTWORT = {"szenen": [{"titel": "Hook: Zapfhahn Nahaufnahme", "einstellung": "Detail, Untersicht, statisch", "ort": "Theke",
                       "requisite": "Bierglas", "dauer": "2 s", "notiz": "Zeitlupe 120 fps"}]
           + [{"titel": f"Szene {i}", "einstellung": "Halbnah"} for i in range(20)] + [{"einstellung": "ohne Titel"}],
           "licht_ton": "Fensterlicht nutzen.", "equipment": ["Gimbal", "Funkmikro"], "ablauf": "Vor Oeffnung drehen.",
           "hinweise": "Gaeste nur mit Einverstaendnis."}


class _Modell:
    def __init__(self, text):
        self.text, self.anfragen = text, []
        self.chat = type("Ch", (), {"completions": self})()

    def create(self, **kw):
        self.anfragen.append(kw)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": self.text})()})()]})()


class TestSkills(unittest.TestCase):
    def test_fuenf_skills_im_prompt(self):
        _, meta = lade_dept_skills("vid", REPO)
        self.assertEqual(sorted(m["skill"] for m in meta if m["geladen"]),
                         ["b-roll-und-schnittdenken", "bildsprache-und-kamera", "equipment-und-drehplan", "licht-und-ton",
                          "shotlist-erstellen"])
        self.assertIn("### Skill: shotlist-erstellen", load_all_subagents()["vid"].system_prompt)


class TestVorschlag(ApiBasis):
    def setUp(self):
        super().setUp()
        self.an = self._neu()
        P = lambda t, b: self.c.post(f"/api/crm/konzept/{self.an}/{t}", json=b).json()
        P("briefing", {"felder": {"ziel": "Abendgeschaeft beleben", "zielgruppe": "Kiez-Publikum", "freigabe_an": "Frau Geheim",
                                  "notizen": "Privatnummer 0151 999"}})
        self.idee = P("idee", {"titel": "Feierabend am Tresen", "beschreibung": "Zapfen, Anstossen", "format": "Reel"})["id"]
        P("skript", {"position": 1, "nr": 1, "hook": "Der beste Zapfhahn am Kiez?", "text": "Wir zapfen …"})
        P("dreh", {"felder": {"datum": "2026-10-20", "zeit": "17:00", "ort": "Kiez", "ansprechpartner": "Herr Kontakt",
                               "telefon": "0151 123456"}})

    def test_1_kontext_ohne_kontaktdaten(self):
        m = self.w._konzept().mappe(self.an)
        t = videograf.kontext(m, "idee", self.idee)
        self.assertIn("Feierabend am Tresen", t)
        self.assertIn("Abendgeschaeft beleben", t)
        for privat in ("Herr Kontakt", "0151", "Frau Geheim", "Privatnummer"):
            self.assertNotIn(privat, t)
        self.assertIn("Wir zapfen", videograf.kontext(m, "skript", "S-1-1"))
        with self.assertRaises(KeyError):
            videograf.kontext(m, "idee", "I-gibtsnicht")

    def test_2_antwort_validiert(self):
        modell = _Modell("```json\n" + json.dumps(ANTWORT) + "\n```")
        r = videograf.vorschlag(self.w._konzept().mappe(self.an), "idee", self.idee, system="SYS", client=modell)
        self.assertEqual(len(r["szenen"]), videograf.MAX_SZENEN)                # gekappt, Szene ohne Titel verworfen
        self.assertEqual(r["szenen"][0]["einstellung"], "Detail, Untersicht, statisch")
        self.assertEqual(set(r["szenen"][0]), {"titel", "einstellung", "ort", "requisite", "dauer", "notiz"})
        self.assertEqual((r["equipment"], r["quelle"]), (["Gimbal", "Funkmikro"], videograf.QUELLE))
        self.assertEqual(modell.anfragen[0]["messages"][0]["content"], "SYS")
        with self.assertRaises(ValueError):
            videograf.vorschlag(self.w._konzept().mappe(self.an), "idee", self.idee, system="S", client=_Modell("keine Ahnung"))

    def test_3_api_speichert_nichts_und_zaehlt(self):
        vorher = self.w._konzept().mappe(self.an)
        gezaehlt = []
        with mock.patch("openai.OpenAI", return_value=_Modell(json.dumps(ANTWORT))), \
             mock.patch.object(self.w, "_google_secrets", return_value={"GEMINI_API_KEY": "x" * 20}), \
             mock.patch("orchestrator.core.agenten_profil.AgentenNutzung.erfassen",
                        lambda self_, agent, **kw: gezaehlt.append((agent, kw["quelle"], kw["ok"]))):
            r = self.c.post(f"/api/crm/konzept-videograf/{self.an}", json={"art": "skript", "id": "S-1-1"}).json()
            fehlt = self.c.post(f"/api/crm/konzept-videograf/{self.an}", json={"art": "idee", "id": "I-nix"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["szenen"][0]["titel"], "Hook: Zapfhahn Nahaufnahme")
        self.assertFalse(fehlt["ok"])
        self.assertEqual(self.w._konzept().mappe(self.an)["szenen"], vorher["szenen"])   # nichts gespeichert
        self.assertEqual(gezaehlt, [("vid", "konzept", True), ("vid", "konzept", False)])
        # Uebernahme per Klick: Szene mit Quelle
        z = r["szenen"][0] | {"quelle": r["quelle"]}
        self.assertTrue(self.c.post(f"/api/crm/konzept/{self.an}/szene", json=z).json()["ok"])
        s = self.w._konzept().mappe(self.an)["szenen_liste"][-1]
        self.assertEqual((s["titel"], s["quelle"]), ("Hook: Zapfhahn Nahaufnahme", "Videograf-Agent (Vorschlag)"))

    def test_4_ohne_schluessel_klare_meldung(self):
        with mock.patch.object(self.w, "_google_secrets", return_value={}):
            r = self.c.post(f"/api/crm/konzept-videograf/{self.an}", json={"art": "idee", "id": self.idee}).json()
        self.assertEqual((r["ok"], r["hinweis"]), (False, "Kein Gemini-Zugang konfiguriert."))


if __name__ == "__main__":
    unittest.main()
