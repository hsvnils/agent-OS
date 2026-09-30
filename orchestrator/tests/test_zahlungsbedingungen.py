"""KUNDEN_FINANZEN Etappe 18: Zahlungsbedingungen je Angebot, Vorkasse (Prozent/Euro) als eigene Vorkasse-Rechnung,
Schlussrechnung mit Abzug, Payment-Check im Kalender."""
import io
import json
import re
import unittest
from datetime import timedelta

from pypdf import PdfReader

from orchestrator.core import zahlungsbedingungen as zb
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import POS, ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD

HEUTE = lambda: jetzt().date()                     # noqa: E731
TEXT = lambda pdf: re.sub(r"\s+", " ", " ".join(s.extract_text() for s in PdfReader(io.BytesIO(pdf)).pages))  # noqa: E731


def _ablauf(zahlung):
    """Angebot (1.020 €) mit Zahlungsbedingungen -> angenommen -> Auftrag."""
    bh, ks, st, k, ap = _stores()
    an = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": POS, "zahlung": zahlung})["nummer"]
    st.status_setzen(an, "versendet")
    st.status_setzen(an, "angenommen")
    ab = AuftragBuch(bh, ks, st)
    nr = ab.aus_angebot(an, leistung_von=HEUTE().isoformat())["nummer"]
    return bh, ks, st, ab, RechnungStore(bh, ks), an, nr


class TestModul(unittest.TestCase):
    def test_1_pruefen_und_rechnen(self):
        z = zb.pruefen({"ziel_tage": "30", "vorkasse": {"art": "prozent", "wert": "33,3"}})
        self.assertEqual(z, {"ziel_tage": 30, "vorkasse": {"art": "prozent", "prozent": 33.3, "frist_tage": 7}})
        self.assertEqual(zb.pruefen(z), z)                                       # idempotent (Auftrag -> Rechnung)
        self.assertEqual(zb.vorkasse_cent(z, 100001), 33300)                     # kaufmaennisch gerundet
        e = zb.pruefen({"vorkasse": {"art": "euro", "wert": "1.500", "frist_datum": "2026-12-01"}}, ziel_vorschlag=21)
        self.assertEqual(e["vorkasse"], {"art": "euro", "cent": 150000, "frist_datum": "2026-12-01"})
        self.assertEqual((e["ziel_tage"], zb.vorkasse_cent(e, 100000)), (21, 100000))   # nie ueber der Summe
        self.assertEqual(zb.pruefen(None), {"ziel_tage": 14})
        self.assertEqual(zb.vorkasse_frist(z, "2026-09-30"), "2026-10-07")
        for falsch in ({"ziel_tage": 200}, {"vorkasse": {"art": "prozent", "wert": 0}},
                       {"vorkasse": {"art": "prozent", "wert": 101}}, {"vorkasse": {"art": "euro", "wert": "-5"}},
                       {"vorkasse": {"art": "bar", "wert": 5}}, {"vorkasse": {"art": "euro", "wert": 5, "frist_tage": 91}}):
            with self.assertRaises(ValueError, msg=falsch):
                zb.pruefen(falsch)

    def test_2_texte(self):
        z = zb.pruefen({"ziel_tage": 14, "vorkasse": {"art": "prozent", "wert": 50}, "text": "Danke!"})
        t = zb.text(z, 260000)
        self.assertIn("50 % Vorkasse (1.300,00 €), zahlbar bis 7 Tage nach Auftragsbestätigung", t)
        self.assertIn("Restbetrag (1.300,00 €) zahlbar innerhalb von 14 Tagen", t)
        self.assertTrue(t.endswith("Danke!"))
        self.assertIn("bis zum 07.10.2026", zb.text(z, 260000, ab_datum="2026-09-30"))
        self.assertNotIn("Restbetrag", zb.text(zb.pruefen({"vorkasse": {"art": "prozent", "wert": 100}}), 5000))
        self.assertEqual(zb.text(zb.pruefen({"ziel_tage": 0}), 5000),
                         "Zahlungsbedingungen: zahlbar sofort nach Rechnungsstellung ohne Abzug.")
        self.assertEqual(zb.text(None, 5000), "")                                  # alte Angebote: kein Satz


class TestAblauf(unittest.TestCase):
    def test_1_vorschlag_aus_kunde_und_alte_angebote(self):
        bh, ks, st, k, ap = _stores()
        ks.firma_aendern(k, {"zahlungsziel_tage": 30})
        a = st.angebot(st.anlegen({"firma": k, "positionen": POS})["nummer"])
        self.assertEqual(a["zahlung"], {"ziel_tage": 30})
        b = st.angebot(st.anlegen({"firma": k, "positionen": POS, "zahlung": {"ziel_tage": ""}})["nummer"])
        self.assertEqual(b["zahlung"], {"ziel_tage": 30})                         # leeres Feld = Kundendaten
        self.assertIn("zahlbar innerhalb von 30 Tagen", TEXT(st.pdf(a["nummer"], FD)))

    def test_2_vorkasse_rechnung_und_schlussrechnung(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 10, "vorkasse": {"art": "prozent", "wert": 50}})
        self.assertIn("50 % Vorkasse (510,00 €)", TEXT(st.pdf(an, FD)))
        a = ab.auftrag(nr)
        self.assertEqual((a["vorkasse_cent"], a["vorkasse_faellig"]), (51000, (HEUTE() + timedelta(days=7)).isoformat()))
        self.assertIn("bis zum " + (HEUTE() + timedelta(days=7)).strftime("%d.%m.%Y"), TEXT(ab.pdf(nr, FD)))
        # Vorkasse-Rechnung
        e1 = rs.entwurf_aus_auftrag(a, vorkasse=True)["entwurf_id"]
        self.assertEqual(rs.entwurf_aus_auftrag(a, vorkasse=True), {"entwurf_id": e1, "vorhanden": True})
        v = rs.festschreiben(e1, FD)
        x = rs.get(v["nummer"])
        self.assertEqual((x["art"], x["summe_cent"], x["faellig_am"]),
                         ("anzahlung", 51000, (HEUTE() + timedelta(days=7)).isoformat()))
        self.assertIn("Vorkasse-Rechnung", TEXT(rs._pdf(x, FD)))
        with self.assertRaises(ValueError):
            rs.entwurf_aus_auftrag(a, vorkasse=True)                              # keine zweite Vorkasse-Rechnung
        # Schlussrechnung: Abzug nach Zuschlaegen/Rabatt, Zahlungsziel aus dem Angebot
        e2 = rs.entwurf_aus_auftrag(a)["entwurf_id"]
        self.assertEqual(rs.get(e2)["summe_cent"], 51000)                          # Vorschau zeigt schon den Rest
        s = rs.festschreiben(e2, FD)
        y = rs.get(s["nummer"])
        self.assertEqual((y["art"], y["summe_cent"], y["summen"]["vor_abzug_cent"]), ("rechnung", 51000, 102000))
        self.assertEqual(y["abzuege"], [{"nummer": v["nummer"], "datum": HEUTE().isoformat(), "betrag_cent": 51000}])
        self.assertEqual(y["faellig_am"], (HEUTE() + timedelta(days=10)).isoformat())
        t = TEXT(rs._pdf(y, FD))
        self.assertIn("Schlussrechnung", t)
        self.assertIn(f"abzgl. Vorkasse {v['nummer']}", t)
        self.assertEqual(rs.umsatz(HEUTE().year), 102000)                          # nur einmal gezaehlt
        with self.assertRaises(ValueError):
            rs.entwurf_aus_auftrag(a, vorkasse=True)                              # nach der Schlussrechnung nicht mehr
        # Storno-Reihenfolge: erst Schluss, dann Vorkasse
        with self.assertRaises(ValueError):
            rs.stornieren(v["nummer"], FD, grund="Test")
        st_nr = rs.stornieren(s["nummer"], FD, grund="Test")["storno"]
        self.assertEqual(rs.get(st_nr)["summe_cent"], -51000)
        self.assertEqual(rs.umsatz(HEUTE().year), 51000)
        rs.stornieren(v["nummer"], FD, grund="Test")
        self.assertEqual(rs.umsatz(HEUTE().year), 0)
        self.assertEqual((bh.pruefe_kette(), bh.pruefe_belege()), ([], []))

    def test_3_ohne_vorkasse_und_voll_vorkasse(self):
        bh, ks, st, ab, rs, an, nr = _ablauf(None)
        a = ab.auftrag(nr)
        self.assertNotIn("vorkasse_cent", a)
        with self.assertRaises(ValueError):
            rs.entwurf_aus_auftrag(a, vorkasse=True)
        r = rs.get(rs.festschreiben(rs.entwurf_aus_auftrag(a)["entwurf_id"], FD)["nummer"])
        self.assertEqual((r["art"], r["summe_cent"], r.get("abzuege")), ("rechnung", 102000, None))
        bh, ks, st, ab, rs, an, nr = _ablauf({"vorkasse": {"art": "euro", "wert": "2000", "frist_tage": 0}})
        a = ab.auftrag(nr)
        self.assertEqual((a["vorkasse_cent"], a["vorkasse_faellig"]), (102000, HEUTE().isoformat()))
        rs.festschreiben(rs.entwurf_aus_auftrag(a, vorkasse=True)["entwurf_id"], FD)
        with self.assertRaisesRegex(ValueError, "vollstaendig berechnet"):
            rs.festschreiben(rs.entwurf_aus_auftrag(a)["entwurf_id"], FD)

    def test_3b_vorkasse_entwurf_nach_schlussrechnung(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"vorkasse": {"art": "prozent", "wert": 20}})
        a = ab.auftrag(nr)
        e1 = rs.entwurf_aus_auftrag(a, vorkasse=True)["entwurf_id"]            # Vorkasse-Entwurf liegt noch rum ...
        s = rs.festschreiben(rs.entwurf_aus_auftrag(a)["entwurf_id"], FD)      # ... Rechnung ohne Abzug geht raus
        self.assertEqual(rs.get(s["nummer"])["summe_cent"], 102000)
        with self.assertRaisesRegex(ValueError, "keine weitere Vorkasse"):
            rs.festschreiben(e1, FD)                                             # sonst doppelter Umsatz
        self.assertEqual(rs.umsatz(HEUTE().year), 102000)

    def test_4_todos(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"vorkasse": {"art": "prozent", "wert": 30}})
        ids = lambda: {t["id"] for t in geschaefts_todos(bh, ks)}          # noqa: E731
        self.assertIn(f"ab-vorkasse:{nr}", ids())
        rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr), vorkasse=True)["entwurf_id"], FD)
        self.assertNotIn(f"ab-vorkasse:{nr}", ids())
        ab.status_setzen(nr, "erledigt")
        self.assertIn(f"ab-rechnung:{nr}", ids())                                  # Vorkasse ist keine Schlussrechnung


class TestApi(ApiBasis):
    def setUp(self):
        super().setUp()
        (self.w.kunden_store.bh.dir / "firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")

    def test_a1_payment_check_und_aufraeumen(self):
        an = self._neu(zahlung={"ziel_tage": 14, "vorkasse": {"art": "euro", "wert": "300", "frist_tage": 5}})
        self.assertTrue(self.c.post(f"/api/crm/angebote/{an}/versendet").json()["ok"])
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        d = self.c.get(f"/api/crm/auftraege/{nr}").json()
        self.assertIn("Vorkasse von 300,00 €", d["zahlung_text"])
        r = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={"vorkasse": True}).json()
        self.assertTrue(r["ok"], r)
        n0 = len(self.g.termine)
        f = self.c.post(f"/api/finanzen/rechnungen/{r['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()
        self.assertTrue(f["ok"], f)
        t = self.g.termine[n0]
        self.assertTrue(t["titel"].startswith(f"💶 Payment-Check: Vorkasse {f['nummer']} (300,00 €)"), t)
        self.assertEqual(t["start"], (HEUTE() + timedelta(days=5)).isoformat() + "T09:00:00")
        self.assertEqual([x["art"] for x in self.c.get(f"/api/crm/auftraege/{nr}").json()["rechnungen"]], ["anzahlung"])
        b = self.c.post(f"/api/finanzen/rechnungen/{f['nummer']}/bezahlt", json={"datum": ""}).json()
        self.assertTrue(b["ok"], b)
        tid = self.c.get(f"/api/finanzen/rechnungen/{f['nummer']}").json()["rechnung"]["erinnerung"]["id"]
        self.assertIn(tid, self.g.geloeschte_termine)                                # Zahlung da -> Payment-Check weg
        s = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{s['entwurf_id']}").json()["rechnung"]["summe_cent"], 72000)


if __name__ == "__main__":
    unittest.main()
