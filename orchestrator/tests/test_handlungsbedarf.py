"""LUNA_OS_UI_ROADMAP Etappe 3: Handlungsbedarf ueber alle Bereiche (Stufen, Bereiche, Zusatzquellen, Endpunkt)."""
import unittest
from datetime import date

from orchestrator.core.handlungsbedarf import zusammenstellen
from orchestrator.tests.test_angebote import ApiBasis

HEUTE = date(2026, 9, 30)


def _t(id_, bereich="Rechnungen", faellig="", dringend=False, **x):
    return {"id": id_, "bereich": bereich, "icon": "•", "titel": id_, "detail": "", "act": "go:dash", "act_id": "",
            "faellig": faellig, "dringend": dringend, "erledigen": None} | x


class TestZusammenstellen(unittest.TestCase):
    def test_1_stufen_und_bereiche(self):
        d = zusammenstellen([_t("ueberfaellig", faellig="2026-09-20", dringend=True),
                             _t("in5", "Angebote", faellig="2026-10-05"),
                             _t("in30", "Belege", faellig="2026-10-30"),
                             _t("ohne", "Zeiten"),
                             _t("reel", "Content", stufe="woche"),
                             _t("crm", "CRM", faellig="2026-09-30", dringend=True)], heute=HEUTE)
        st = {p["id"]: p["stufe"] for p in d["punkte"]}
        self.assertEqual(st, {"ueberfaellig": "dringend", "in5": "woche", "in30": "spaeter", "ohne": "spaeter",
                              "reel": "woche", "crm": "dringend"})
        self.assertEqual(d["zaehler"], {"dringend": 2, "woche": 2, "spaeter": 2, "gesamt": 6})
        self.assertEqual(d["bereiche"], {"geschaeft": 4, "content": 2})
        self.assertEqual([p["stufe"] for p in d["punkte"]], ["dringend"] * 2 + ["woche"] * 2 + ["spaeter"] * 2)

    def test_2_zusatzquellen(self):
        antraege = [{"titel": "Neue Funktion", "verlauf": [{"ts": "2026-09-28T10:00:00"}]},
                    {"titel": "Sicherheits-Audit: 2 Befunde beheben", "verlauf": [{"ts": "2026-09-29T10:00:00"}]}]
        d = zusammenstellen([], antraege=antraege, investment=[{"frage": "NVDA für 200 $ kaufen?"}],
                            betrieb={"bot_alter_min": 61.0, "unzugestellt": 2, "aelteste_unzugestellt_min": 45.0},
                            heute=HEUTE)
        p = {x["id"]: x for x in d["punkte"]}
        self.assertEqual(p["freigaben"]["stufe"], "woche")
        self.assertEqual(p["freigaben"]["bereich_id"], "luna")
        self.assertIn("2 Antrag", p["freigaben"]["titel"])
        self.assertEqual((p["investment-freigaben"]["stufe"], p["investment-freigaben"]["bereich_id"]), ("dringend", "investment"))
        self.assertEqual(p["betrieb-bot"]["stufe"], "dringend")
        self.assertEqual(p["betrieb-zustellung"]["stufe"], "dringend")
        self.assertEqual(d["zaehler"]["dringend"], 3)

    def test_3_ruhiger_betrieb_meldet_nichts(self):
        d = zusammenstellen([], betrieb={"bot_alter_min": 12.0, "unzugestellt": 1, "aelteste_unzugestellt_min": 5.0},
                            antraege=[], investment=[], heute=HEUTE)
        self.assertEqual(d["zaehler"]["gesamt"], 0)
        d = zusammenstellen([], betrieb={"bot_alter_min": None, "unzugestellt": 0}, heute=HEUTE)
        self.assertEqual(d["punkte"], [])


class TestApi(ApiBasis):
    def test_a1_endpunkt_deckt_todos(self):
        todos = self.c.get("/api/todos").json()
        d = self.c.get("/api/handlungsbedarf").json()
        ids = {p["id"] for p in d["punkte"]}
        self.assertTrue({t["id"] for t in todos["todos"]} <= ids)           # nichts aus „Zu erledigen“ geht verloren
        self.assertEqual(d["zaehler"]["gesamt"], len(d["punkte"]))
        self.assertEqual(sum(d["bereiche"].values()), len(d["punkte"]))
        self.assertTrue(all(p["stufe"] in ("dringend", "woche", "spaeter") for p in d["punkte"]))


if __name__ == "__main__":
    unittest.main()
