"""Self-Checks JARVIS J9 „Wochenplanung mit Zeitbloecken“ -- offline, Fake-Kalender, Temp-Verzeichnisse."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.core import wochenplan as wp
from orchestrator.core.aufgaben import AufgabenStore

MO = datetime(2026, 11, 2, 8, 20)                      # Montag, kurz nach dem Morgen-Briefing


class FakeGoogle:
    def __init__(self, termine=None, ok=True):
        self.termine, self.ok, self.angelegt = list(termine or []), ok, []

    def verfuegbar(self):
        return True

    def kalender_agenda(self, tage=7, max_results=20):
        return {"ok": self.ok, "termine": list(self.termine)}

    def termin_anlegen(self, titel, start, ende, *, ort="", beschreibung="", bestaetigt=False):
        assert bestaetigt
        self.angelegt.append({"titel": titel, "start": start, "ende": ende})
        return {"ok": True, "termin_id": f"t{len(self.angelegt)}"}


def _t(start, ende, titel="Termin"):
    return {"titel": titel, "start": start, "ende": ende}


TERMINE = [_t("2026-11-02T10:00:00+01:00", "2026-11-02T11:00:00+01:00", "Dreh"),
           _t("2026-11-03", "2026-11-04", "Messe (ganztaegig)"),
           _t("2026-11-04T09:00:00+01:00", "2026-11-04T17:30:00+01:00", "Workshop")]


def _todo(i, titel, faellig="", uhrzeit="", angelegt="2026-10-01T10:00:00"):
    return {"id": f"A-0000000{i}", "titel": titel, "faellig": faellig, "uhrzeit": uhrzeit, "angelegt": angelegt}


class TestLuecken(unittest.TestCase):
    def test_1_luecken_mit_puffer_mittag_ganztags(self):
        l = wp.freie_luecken(TERMINE, MO)
        tage = {s.date().isoformat() for s, _ in l}
        self.assertNotIn("2026-11-03", tage)                          # ganztaegig -> ganzer Tag gesperrt
        self.assertNotIn("2026-11-04", tage)                          # Workshop 9-17:30 (+Puffer) laesst < 1 h
        mo = [(s.strftime("%H:%M"), e.strftime("%H:%M")) for s, e in l if s.date() == MO.date()]
        self.assertEqual(mo, [("13:00", "18:00")])                    # 9:00-9:45 und 11:15-12:00 zu kurz, Mittag frei
        self.assertTrue(all(e - s >= timedelta(hours=1) for s, e in l))

    def test_2_gate_kein_block_ueberschneidet_einen_termin(self):
        todos = [_todo(i, f"Aufgabe {i}") for i in range(10)]
        bloecke = wp.vorschlagen(todos, TERMINE, MO)
        self.assertEqual(len(bloecke), wp.MAX_BLOECKE)
        self.assertFalse(any(wp.kollidiert(b, TERMINE) for b in bloecke))
        enden = sorted((b["start"], b["ende"]) for b in bloecke)
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(enden, enden[1:])))      # Bloecke untereinander frei
        self.assertTrue(all(9 <= int(b["start"][11:13]) and b["ende"][11:16] <= "18:00" for b in bloecke))
        self.assertFalse(any("12:00" <= b["start"][11:16] < "13:00" for b in bloecke))

    def test_3_faelligkeit_und_kandidaten(self):
        g = {"ueberfaellig": [_todo(1, "Alt", "2026-10-20")], "heute": [_todo(2, "Fest", "2026-11-02", "15:00")],
             "demnaechst": [_todo(3, "Fr", "2026-11-06"), _todo(4, "Spaeter", "2026-11-20")],
             "ohne_datum": [_todo(6, "Neu", angelegt="2026-10-30T10:00:00"), _todo(5, "Uralt", angelegt="2026-09-01T10:00:00")]}
        k = [a["titel"] for a in wp.kandidaten(g, MO.date() + timedelta(days=6))]
        self.assertEqual(k, ["Alt", "Fr", "Uralt", "Neu"])            # feste Uhrzeit + naechste Woche raus
        # faellig Montag, aber Montag ist voll -> kein Block nach der Faelligkeit
        voll = TERMINE + [_t("2026-11-02T13:00:00+01:00", "2026-11-02T18:00:00+01:00")]
        self.assertEqual(wp.vorschlagen([_todo(7, "Heute faellig", "2026-11-02")], voll, MO), [])
        b = wp.vorschlagen([_todo(8, "Bis Fr", "2026-11-06")], voll, MO)
        self.assertEqual(b[0]["start"][:10], "2026-11-05")


class TestEintragen(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.st = wp.WochenplanStore(self.root / "wochenplan" / "log.jsonl")

    def test_1_nichts_ohne_bestaetigung_und_frisch_geprueft(self):
        g = FakeGoogle(TERMINE + [_t("2026-11-02T14:15:00+01:00", "2026-11-02T18:00:00+01:00")])   # Mo nur 13-14 frei
        AufgabenStore(self.root / "todos" / "log.jsonl").anlegen("Angebot Kiez Alm schreiben")
        AufgabenStore(self.root / "todos" / "log.jsonl").anlegen("Steuerordner sortieren")
        v = wp.vorschlag_erstellen(self.root, g, MO)
        self.assertEqual([b["start"] for b in v["bloecke"]], ["2026-11-02T13:00", "2026-11-05T09:00"])
        self.assertEqual(g.angelegt, [])                                # Vorschlag allein traegt nichts ein
        g.termine.append(_t(v["bloecke"][0]["start"] + ":00", v["bloecke"][0]["ende"] + ":00", "neu dazwischen"))
        res = self.st.entscheiden(v["id"], True, g)
        self.assertEqual(len(g.angelegt), 1)                            # belegter Block weggelassen
        self.assertIn("weggelassen", res)
        self.assertEqual((g.angelegt[0]["titel"][:2], g.angelegt[0]["start"]), ("🧱 ", "2026-11-05T09:00:00"))
        self.assertIn("Schon", self.st.entscheiden(v["id"], True, g))   # Doppelklick -> nichts doppelt
        self.assertEqual(len(g.angelegt), 1)

    def test_2_nein_kalender_aus_und_unbekannt(self):
        g = FakeGoogle([])
        p = self.st.vorschlag("2026-11-02", [{"todo": "A-1", "titel": "X", "start": "2026-11-02T13:00",
                                               "ende": "2026-11-02T14:00"}])
        self.assertIn("nichts", self.st.entscheiden(p["id"], False, g))
        self.assertEqual(g.angelegt, [])
        p2 = self.st.vorschlag("2026-11-02", p["bloecke"])
        self.assertIn("nichts eingetragen", self.st.entscheiden(p2["id"], True, FakeGoogle(ok=False)))
        self.assertEqual(self.st.get(p2["id"])["status"], "offen")
        self.assertIn("nicht mehr", self.st.entscheiden("W-gibtsnicht", True, g))

    def test_3_werkzeug_knoepfe_ohne_eintrag(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        AufgabenStore(self.root / "todos" / "log.jsonl").anlegen("Rechnungen ablegen")
        g = FakeGoogle([])
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=self.root, repo_root=self.root,
                          leak_secrets=[], google=g)
        out = run_tool("wochenplan_vorschlagen", {}, ctx)
        self.assertTrue(out["ok"])
        self.assertEqual([k["callback_data"].rsplit(":", 1)[1] for k in ctx.knoepfe], ["ja", "nein"])
        self.assertEqual(g.angelegt, [])


class TestRueckblick(unittest.TestCase):
    def test_1_text(self):
        fr = datetime(2026, 11, 6, 16, 0)
        t = wp.rueckblick(fr, erledigt=["Angebot schreiben", "Steuer"], offen=3,
                          rechnungen=[{"summe_cent": 160000}], offen_cent=400000,
                          naechste=[_t("2026-11-09T11:00:00+01:00", "2026-11-09T12:00:00+01:00", "Dreh Kiez Alm")])
        for teil in ("KW 45", "Erledigt: 2 To-dos – Angebot schreiben, Steuer", "Offen: 3 To-dos",
                     "1 über 1.600,00 €", "4.000,00 €", "1 Termin – zuerst Mo 11:00 Dreh Kiez Alm"):
            self.assertIn(teil, t)

    def test_2_aus_den_daten(self):
        root = Path(tempfile.mkdtemp())
        st = AufgabenStore(root / "todos" / "log.jsonl")
        x = st.anlegen("Erledigtes")
        st.erledigen(x["id"])
        st.anlegen("Offenes")
        t = wp.rueckblick_erstellen(root, None, datetime.now())
        self.assertIn("Erledigt: 1 To-do – Erledigtes", t)
        self.assertIn("Offen: 1 To-do", t)


if __name__ == "__main__":
    unittest.main()
