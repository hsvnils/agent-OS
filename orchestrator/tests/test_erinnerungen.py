"""CEO 2026-09-28: Kalender-Erinnerungen erledigter Angebote/Rechnungen loescht LUNA selbststaendig -- nur eigene,
protokollierte, kommende Termine; idempotent; von Hand geloeschte gelten als erledigt; Fehler -> spaeter erneut."""
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.erinnerungen import erledigte_entfernen, faellige_loeschungen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import POS, ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD, _entwurf


class _Kalender:
    def __init__(self, fehler=None):
        self.geloescht, self.fehler = [], dict(fehler or {})
    def verfuegbar(self): return True
    def termin_loeschen(self, event_id, *, bestaetigt=False):
        assert bestaetigt
        if event_id in self.fehler:
            return {"ok": False, "hinweis": self.fehler.pop(event_id)}
        self.geloescht.append(event_id)
        return {"ok": True, "geloescht": True}


def _tag(n):
    return (jetzt().date() + timedelta(days=n)).isoformat()


class TestErinnerungen(unittest.TestCase):
    def test_1_angebot_angenommen_und_abgelehnt(self):
        bh, ks, st, k, ap = _stores()
        a1 = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        a2 = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        a3 = st.anlegen({"firma": k, "positionen": POS})["nummer"]
        st.status_setzen(a1, "versendet", termine=[{"datum": _tag(7), "titel": "nachfassen", "id": "e1"},
                                                   {"datum": _tag(-1), "titel": "vorbei", "id": "e0"}])
        st.erinnerungen_ergaenzen(a1, [{"datum": _tag(20), "titel": "laeuft ab", "id": "e1b"}])
        st.status_setzen(a2, "versendet", termine=[{"datum": _tag(7), "titel": "nachfassen", "id": "e2"}])
        st.status_setzen(a3, "versendet", termine=[{"datum": _tag(7), "titel": "nachfassen", "id": "e3"}])
        self.assertEqual(faellige_loeschungen(bh.eintraege()), [])                     # alles noch offen
        st.status_setzen(a1, "angenommen")
        st.status_setzen(a2, "abgelehnt")
        g = _Kalender()
        weg = erledigte_entfernen(bh, g)
        self.assertEqual(sorted(g.geloescht), ["e1", "e1b", "e2"])                      # e0 vergangen, e3 offen
        self.assertEqual({x["bezug"] for x in weg}, {a1, a2})
        self.assertEqual(erledigte_entfernen(bh, g), [])                               # idempotent
        self.assertEqual(len(bh.eintraege("kalender_erinnerung_entfernt")), 3)

    def test_2_rechnung_bezahlt_storniert_und_fehler(self):
        bh, ks, st, k, ap = _stores()
        rs = RechnungStore(bh, ks)
        r1 = rs.festschreiben(_entwurf(rs, k, ap), FD)["nummer"]
        r2 = rs.festschreiben(_entwurf(rs, k, ap), FD)["nummer"]
        r3 = rs.festschreiben(_entwurf(rs, k, ap), FD)["nummer"]
        for nr, eid in ((r1, "f1"), (r2, "f2"), (r3, "f3")):
            rs.erinnerung_merken(nr, {"datum": _tag(14), "id": eid})
        rs.bezahlt(r1, datum="")
        rs.stornieren(r2, FD, grund="falsch")
        g = _Kalender(fehler={"f1": "HttpError 503 Backend Error", "f2": "HttpError 410 Resource has been deleted"})
        weg = erledigte_entfernen(bh, g)
        self.assertEqual([x["id"] for x in weg], ["f2"])                               # von Hand geloescht = erledigt
        self.assertEqual(g.geloescht, [])
        self.assertEqual([x["id"] for x in erledigte_entfernen(bh, g)], ["f1"])        # 503 -> naechster Lauf
        self.assertEqual(g.geloescht, ["f1"])                                          # f3 (offen) bleibt

    def test_3_ohne_google_nichts(self):
        bh, *_ = _stores()
        self.assertEqual(erledigte_entfernen(bh, None), [])


class TestErinnerungenApi(ApiBasis):
    def test_a1_annehmen_loescht_sofort(self):
        nr = self._neu()
        v = self.c.post(f"/api/crm/angebote/{nr}/versendet").json()
        ids = [t["id"] for t in v["termine"]]
        self.assertTrue(ids)
        r = self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "angenommen"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(sorted(self.g.geloeschte_termine), sorted(ids))
        self.assertIn("Kalender-Erinnerung", " ".join(r["hinweise"]))
        r = self.c.post(f"/api/crm/angebote/{nr}/status", json={"status": "abgelehnt"}).json()
        self.assertFalse(r["ok"])                                                      # Fachfehler bleibt sichtbar
        self.assertEqual(len(self.g.geloeschte_termine), len(ids))


if __name__ == "__main__":
    unittest.main()
