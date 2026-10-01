"""KUNDEN_FINANZEN Etappe 28: Begriffe „Mahnstufe 1-3“ (Status) / „1.-3. Mahnung“ (Brief) und Status „Mahnverfahren“."""
import unittest
from datetime import date, timedelta

from orchestrator.core.handlungsbedarf import zusammenstellen
from orchestrator.core.mahnungen import BRIEF, STUFEN, MahnStore, folgemahnung_frage, mahnung_mail_text
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_altrechnungen import PDF, T, _rs
from orchestrator.tests.test_angebote import ApiBasis


def _drei_mahnungen(bh, ks, rs, k):
    rs.alt_erfassen({"firma": k, "nummer": "RG-11052026", "rechnungsdatum": T(140), "betrag": "4000"}, PDF)
    ms = MahnStore(bh, ks)
    for n in (100, 70, 30):
        ms.alt_erfassen("RG-11052026", datum=T(n))
    return ms


class TestBegriffe(unittest.TestCase):
    def test_1_status_und_brief(self):
        self.assertEqual((STUFEN[1], STUFEN[3]), ("Mahnstufe 1", "Mahnstufe 3"))
        self.assertEqual(BRIEF[3], "3. Mahnung")                     # wie in den CEO-PDFs, nicht „Letzte Mahnung“
        m = {"stufe": 3, "rechnung": "RE-2026-0001", "nummer": "MA-2026-0003", "faellig_am": "2026-08-01",
             "summe_cent": 100000, "frist": "2026-10-08"}
        betreff, text = mahnung_mail_text(m, None, {"inhaber": "Max Muster"})
        self.assertEqual(betreff, "3. Mahnung zu Rechnung RE-2026-0001")
        self.assertIn("letzte Mahnung", text)
        frage = folgemahnung_frage(m | {"titel": BRIEF[3], "offen_cent": 100000, "zinsen_cent": 0,
                                         "gebuehr_text": "Mahngebuehr", "gebuehr_cent": 0}, "Beispiel GmbH")
        self.assertIn("Frist der Mahnstufe 2", frage)
        self.assertIn("Mahnstufe 3 (3. Mahnung) jetzt senden?", frage)


class TestMahnverfahren(unittest.TestCase):
    def test_1_status_beruhigt_handlungsbedarf(self):
        bh, ks, rs, k = _rs()
        ms = _drei_mahnungen(bh, ks, rs, k)
        vorher = {t["id"]: t for t in geschaefts_todos(bh, ks)}
        self.assertTrue(vorher["re-ueber:RG-11052026"]["dringend"])
        ms.mahnverfahren_setzen("RG-11052026", datum=T(2), durch="Rechtsanwältin Muster", notiz="digital beantragt")
        nachher = {t["id"]: t for t in geschaefts_todos(bh, ks)}
        self.assertNotIn("re-ueber:RG-11052026", nachher)
        t = nachher["re-mahnverfahren:RG-11052026"]
        self.assertFalse(t["dringend"])
        self.assertIn("durch Rechtsanwältin Muster", t["detail"])
        hb = zusammenstellen(list(nachher.values()), heute=date.fromisoformat(T(0)))
        self.assertEqual([p["stufe"] for p in hb["punkte"] if p["id"] == "re-mahnverfahren:RG-11052026"], ["spaeter"])
        self.assertEqual(rs.get("RG-11052026")["status"], "offen")             # Rechnung bleibt offen

    def test_2_pruefungen(self):
        bh, ks, rs, k = _rs()
        ms = _drei_mahnungen(bh, ks, rs, k)
        for kw, fehler in (({"datum": (date.fromisoformat(T(0)) + timedelta(days=1)).isoformat()}, "Zukunft"),
                           ({"datum": ""}, "Datum"), ({"datum": T(200)}, "vor der Rechnung")):
            with self.assertRaisesRegex(ValueError, fehler):
                ms.mahnverfahren_setzen("RG-11052026", **kw)
        with self.assertRaises(KeyError):
            ms.mahnverfahren_setzen("RG-99999999", datum=T(1))
        rs.bezahlt("RG-11052026", datum=T(1))
        with self.assertRaisesRegex(ValueError, "bezahlt"):
            ms.mahnverfahren_setzen("RG-11052026", datum=T(1))
        self.assertNotIn("re-mahnverfahren:RG-11052026", {t["id"] for t in geschaefts_todos(bh, ks)})


class TestApi(ApiBasis):
    def test_a1_eintragen_und_anzeigen(self):
        bh = self.w.kunden_store.bh
        from orchestrator.core.rechnungen import RechnungStore
        _drei_mahnungen(bh, self.w.kunden_store, RechnungStore(bh, self.w.kunden_store), self.k)
        r = self.c.post("/api/finanzen/rechnungen/RG-11052026/mahnverfahren",
                        json={"datum": T(2), "durch": "Rechtsanwältin Muster"}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.get("/api/finanzen/rechnungen/RG-11052026").json()
        self.assertEqual((d["mahnverfahren"]["datum"], d["mahnverfahren"]["durch"]), (T(2), "Rechtsanwältin Muster"))
        self.assertFalse(self.c.post("/api/finanzen/rechnungen/RG-11052026/mahnverfahren", json={"datum": "x"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
