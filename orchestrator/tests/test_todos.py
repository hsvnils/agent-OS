"""CEO 2026-09-28: offene To-dos des Tagesbetriebs auf der Hauptseite -- abgeleitet aus der Kette, verschwinden mit
der erledigten Arbeit; „Nachgefasst“ loescht den Nachfass-Termin (auch heute/vergangen); Freigaben bleiben draussen."""
import unittest
from datetime import timedelta

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eingangsbelege import EingangStore
from orchestrator.core.erinnerungen import erledigte_entfernen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import POS, ApiBasis, _stores
from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_erinnerungen import _Kalender
from orchestrator.tests.test_rechnungen import FD, _entwurf


def _tag(n):
    return (jetzt().date() + timedelta(days=n)).isoformat()


class TestTodos(unittest.TestCase):
    def test_1_quellen_und_verschwinden(self):
        bh, ks, st, k, ap = _stores()
        rs, eb = RechnungStore(bh, ks), EingangStore(bh)
        a1 = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        st.status_setzen(a1, "versendet", termine=[{"datum": _tag(0), "titel": f"Angebot {a1} nachfassen: X", "id": "n1"}])
        a2 = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        st.status_setzen(a2, "versendet", termine=[{"datum": _tag(5), "titel": f"Angebot {a2} nachfassen: X", "id": "n2"}])
        r = rs.festschreiben(_entwurf(rs, k, ap, zahlungsziel_tage=0), FD)["nummer"]
        nr = eb.aufnehmen(_pdf("Druckerei Nord\nRechnung\nGesamt 10,00 EUR " + "x" * 20), "d.pdf")["nummer"]
        ids = {t["id"] for t in geschaefts_todos(bh, ks)}
        self.assertIn(f"an-nachfassen:{a1}", ids)                                       # heute faellig
        self.assertNotIn(f"an-nachfassen:{a2}", ids)                                    # erst in 5 Tagen
        self.assertIn(f"bl-pruefen:{nr}", ids)
        self.assertNotIn(f"re-ueber:{r}", ids)                                          # heute faellig, nicht ueber
        heute_plus = jetzt().date() + timedelta(days=1)
        self.assertIn(f"re-ueber:{r}", {t["id"] for t in geschaefts_todos(bh, ks, heute=heute_plus)})
        t = next(t for t in geschaefts_todos(bh, ks) if t["id"] == f"an-nachfassen:{a1}")
        self.assertTrue(t["dringend"])
        self.assertEqual(t["erledigen"]["pfad"], f"/api/crm/angebote/{a1}/nachgefasst")
        # erledigen: nachgefasst -> To-do weg + Termin geloescht (auch wenn heute)
        st.nachgefasst(a1)
        with self.assertRaises(ValueError):
            st.nachgefasst(a1)
        k_ = _Kalender()
        self.assertEqual([x["id"] for x in erledigte_entfernen(bh, k_)], ["n1"])
        # Beleg gebucht -> To-do weg
        eb.buchen(nr, {"lieferant": "Druckerei", "rechnungsdatum": _tag(0), "betrag": "10", "kategorie": "wareneinkauf"})
        ids = {t["id"] for t in geschaefts_todos(bh, ks)}
        self.assertNotIn(f"an-nachfassen:{a1}", ids)
        self.assertNotIn(f"bl-pruefen:{nr}", ids)
        self.assertFalse(any(t["bereich"] in ("Belege", "Rechnungen") for t in geschaefts_todos(bh, ks, finanzen=False)))

    def test_2_auftrag_erledigt_ohne_rechnung(self):
        bh, ks, st, k, ap = _stores()
        a = st.anlegen({"firma": k, "ansprechpartner": ap, "positionen": POS})["nummer"]
        st.status_setzen(a, "versendet"); st.status_setzen(a, "angenommen")
        ab = AuftragBuch(bh, ks, st)
        nr = ab.aus_angebot(a)["nummer"]
        self.assertNotIn(f"ab-rechnung:{nr}", {t["id"] for t in geschaefts_todos(bh, ks)})      # noch in Arbeit
        ab.status_setzen(nr, "erledigt")
        self.assertIn(f"ab-rechnung:{nr}", {t["id"] for t in geschaefts_todos(bh, ks)})
        self.assertEqual(geschaefts_todos(bh, ks, finanzen=False, crm=False), [])


class TestTodosApi(ApiBasis):
    def test_a1_hauptseite_ohne_freigaben(self):
        nr = self._neu()
        self.c.post(f"/api/crm/angebote/{nr}/versendet")
        self.w.crm_store.todo_hinzufuegen("Brand_X", "Rückruf wegen Kampagne", faellig=_tag(-1))
        d = self.c.get("/api/todos").json()
        bereiche = {t["bereich"] for t in d["todos"]}
        self.assertIn("CRM", bereiche)
        self.assertNotIn("Freigaben", bereiche)
        crm = next(t for t in d["todos"] if t["bereich"] == "CRM")
        self.assertTrue(crm["dringend"])
        self.assertTrue(self.c.post(crm["erledigen"]["pfad"]).json()["ok"])
        self.assertNotIn("CRM", {t["bereich"] for t in self.c.get("/api/todos").json()["todos"]})
        termine = self.w._angebote().angebot(nr)["versendet_termine"]
        nf = next(t["id"] for t in termine if "nachfassen" in t["titel"])
        r = self.c.post(f"/api/crm/angebote/{nr}/nachgefasst", json={}).json()
        self.assertTrue(r["ok"], r)
        self.assertIn(nf, self.g.geloeschte_termine)                                     # Kalendertermin sofort weg
        self.assertNotIn(next(t["id"] for t in termine if "nachfassen" not in t["titel"]), self.g.geloeschte_termine)


if __name__ == "__main__":
    unittest.main()


class TestFinanzcheck(unittest.TestCase):
    """CEO 2026-09-28: Die Finanzagenten achten darauf, dass alles eingetragen ist und laeuft -- und erinnern."""

    def _monat(self, d, minus):
        from orchestrator.core.todos import _monat
        return _monat(d, minus)

    def test_1_monatsabgleich(self):
        from datetime import date
        from orchestrator.core.eigenbelege import EigenbelegStore
        from orchestrator.core.todos import QUITTUNG, cfo_meldung
        bh, ks, *_ = _stores()
        EigenbelegStore(bh).anlegen({"art": "einnahme", "datum": _tag(0), "betrag": "10", "text": "YouTube"})
        h = jetzt().date()
        self.assertNotIn("Finanzen", {t["bereich"] for t in geschaefts_todos(bh, ks, heute=h)})   # Monat laeuft noch
        naechster = date(h.year + (h.month == 12), h.month % 12 + 1, 3)
        t = next(t for t in geschaefts_todos(bh, ks, heute=naechster) if t["id"].startswith("monat:"))
        self.assertEqual(t["id"], f"monat:{h.year}-{h.month:02d}")
        self.assertTrue(t["dringend"])
        self.assertIn("1 Zahlungseingang", t["detail"])
        self.assertIn("Kontoauszug", cfo_meldung(geschaefts_todos(bh, ks, heute=naechster)))
        self.assertNotIn("Kontoauszug", cfo_meldung(geschaefts_todos(bh, ks, heute=date(naechster.year, naechster.month, 2))))
        bh.erfassen(QUITTUNG, {"schluessel": t["id"]})
        self.assertFalse(any(x["id"] == t["id"] for x in geschaefts_todos(bh, ks, heute=naechster)))

    def test_2_wiederkehrender_posten_fehlt(self):
        from datetime import date
        from orchestrator.core.todos import QUITTUNG
        bh, ks, *_ = _stores()
        eb = EingangStore(bh)
        h = date(jetzt().year, jetzt().month, 15)
        for i, (mon, txt) in enumerate(((self._monat(h, 2), "a"), (self._monat(h, 1), "b"))):
            nr = eb.aufnehmen(_pdf(f"Adobe Rechnung {txt} " + "x" * 30), f"adobe{i}.pdf")["nummer"]
            eb.buchen(nr, {"lieferant": "Adobe", "rechnungsdatum": f"{mon}-05", "betrag": "71,39", "kategorie": "software"})
        t = [x for x in geschaefts_todos(bh, ks, heute=h) if x["id"].startswith("fehlt:")]
        self.assertEqual([x["titel"] for x in t], [f"Adobe: Rechnung für {h.month:02d}/{h.year} fehlt?"])
        self.assertTrue(t[0]["dringend"])
        self.assertEqual([], [x for x in geschaefts_todos(bh, ks, heute=date(h.year, h.month, 9)) if x["id"].startswith("fehlt:")])
        bh.erfassen(QUITTUNG, {"schluessel": t[0]["id"]})
        self.assertEqual([], [x for x in geschaefts_todos(bh, ks, heute=h) if x["id"].startswith("fehlt:")])

    def test_3_offen_gebliebenes_wird_dringend(self):
        from datetime import date
        bh, ks, *_ = _stores()
        eb = EingangStore(bh)
        nr = eb.aufnehmen(_pdf("Kamera Laden Rechnung " + "x" * 30), "k.pdf")["nummer"]
        eb.buchen(nr, {"lieferant": "Kameraladen", "rechnungsdatum": _tag(0), "betrag": "50", "kategorie": "gwg"})
        self.assertNotIn(f"bl-zahlung:{nr}", {t["id"] for t in geschaefts_todos(bh, ks)})     # ohne Faelligkeit: erst spaeter
        spaeter = jetzt().date() + timedelta(days=31)
        t = next(t for t in geschaefts_todos(bh, ks, heute=spaeter) if t["id"] == f"bl-zahlung:{nr}")
        self.assertTrue(t["dringend"])


class TestFinanzcheckApi(ApiBasis):
    def test_q1_quittieren_nur_bekannte_schluessel(self):
        self.assertFalse(self.c.post("/api/finanzen/hinweis-quittieren", json={"schluessel": "irgendwas"}).json()["ok"])
        self.assertTrue(self.c.post("/api/finanzen/hinweis-quittieren", json={"schluessel": "monat:2026-09"}).json()["ok"])
        self.assertTrue(self.c.post("/api/finanzen/hinweis-quittieren", json={"schluessel": "fehlt:adobe:2026-10"}).json()["ok"])
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/finanzen/hinweis-quittieren"), "finanzen")
