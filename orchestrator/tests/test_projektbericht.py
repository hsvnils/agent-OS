"""PROJEKTBERICHT P3: Bericht (Summen, Plan gegen Ist, Stunden/km nur mit Haken), Versand nur mit Bestaetigung,
eingefroren in der Firmenakte, Status „abgeschlossen“ = geliefert + Bericht versendet + Rechnung bezahlt."""
import io
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.kunden import KundenStore
from orchestrator.core.projektbericht import daten, entfaellt, entwurf_speichern, fazit_vorschlag, pdf
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_postings import FEED, PAUSCHAL, REEL, _auftrag
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()
GESTERN = (HEUTE - timedelta(days=1)).isoformat()


def _text(b: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(s.extract_text() for s in PdfReader(io.BytesIO(b)).pages)


class TestBericht(unittest.TestCase):
    def setUp(self):
        self.bh, self.ab, self.nr, self.ps = _auftrag([REEL, FEED] + PAUSCHAL)
        for pid, w in ((f"{self.nr}-P1-1", {"aufrufe": 50000, "reichweite": 40000, "likes": 1800, "kommentare": 100,
                                             "geteilt": 50, "gespeichert": 50}),
                       (f"{self.nr}-P1-2", {"aufrufe": 30000, "reichweite": 20000, "likes": 900}),
                       (f"{self.nr}-P2-1", {"impressionen": 60000, "reichweite": 40000, "likes": 1000})):
            self.ps.veroeffentlichen(pid, datum=GESTERN, link="https://www.instagram.com/p/x/")
            self.ps.kennzahlen_setzen(pid, w)

    def test_1_summen_und_engagement(self):
        d = daten(self.ab.auftrag(self.nr), self.ps.liste(self.nr))
        s = d["summe"]
        self.assertEqual((s["kontakte_ist_alle"], s["reichweite"], s["interaktionen"]), (140000, 100000, 3900))
        self.assertEqual(s["engagement_pct"], 3.9)
        self.assertEqual(d["postings"][0]["engagement_pct"], 5.0)               # 2.000 / 40.000
        self.assertEqual(d["fehlen"], ["Story"])                                  # Story ohne Zahlen
        self.assertNotIn("stunden", d)
        f = fazit_vorschlag(d)
        self.assertIn("4 Postings", f)
        self.assertIn("140.000 Kontakte", f)

    def test_2_stunden_nur_mit_haken(self):
        sz = {"eintraege": [{"datum": GESTERN, "von": "09:00", "bis": "11:00", "pause_min": 0, "minuten": 120,
                             "taetigkeit": "Dreh", "km": 30}], "summe": {"minuten": 120, "km": 30}}
        a, ps = self.ab.auftrag(self.nr), self.ps.liste(self.nr)
        self.assertNotIn("stunden", daten(a, ps, stundenzettel=sz))
        d = daten(a, ps, stundenzettel=sz, mit_stunden=True)
        t = _text(pdf(d, firmendaten=FD, firma_name="Brand X GmbH", fazit="Danke!"))
        self.assertIn("Gesamt 2:00 h", t)
        self.assertNotIn("30 km", t)
        t = _text(pdf(daten(a, ps), firmendaten=FD, firma_name="Brand X GmbH", fazit="Danke!"))
        self.assertNotIn("Aufwand", t)
        self.assertIn("Plan gegen Ist", t)
        self.assertIn("Gegenwert Ist", t)

    def test_3_abschluss_und_handlungsbedarf(self):
        from orchestrator.core.rechnungen import RechnungStore
        ks = KundenStore(self.bh)
        self.ps.kennzahlen_setzen(f"{self.nr}-P4-1", {"aufrufe": 8000})
        ids = lambda: [t["id"].split(":")[0] for t in geschaefts_todos(self.bh, ks) if t["id"].endswith(self.nr)]
        self.assertNotIn("ab-bericht", ids())                                     # noch nicht geliefert
        self.ab.status_setzen(self.nr, "erledigt", datum=GESTERN)
        self.assertIn("ab-bericht", ids())
        self.assertFalse(self.ab.auftrag(self.nr)["abgeschlossen"])
        self.bh.erfassen("auftrag_bericht_versendet", {"nummer": self.nr, "akte_id": "D-1", "an": "a@b.de", "version": 1})
        self.assertNotIn("ab-bericht", ids())
        a = self.ab.auftrag(self.nr)
        self.assertEqual((a["abgeschlossen"], a["abschluss"]["bericht"], a["abschluss"]["bezahlt"]), (False, "versendet", False))
        rs = RechnungStore(self.bh, ks)
        eid = rs.entwurf_aus_auftrag(a)["entwurf_id"]
        rs.entwurf_aendern(eid, {"leistung_von": GESTERN})
        r = rs.festschreiben(eid, FD)
        self.assertFalse(self.ab.auftrag(self.nr)["abgeschlossen"])
        rs.bezahlt(r["nummer"], datum=HEUTE.isoformat())
        self.assertTrue(self.ab.auftrag(self.nr)["abgeschlossen"])
        self.assertTrue([x for x in self.ab.liste() if x["nummer"] == self.nr][0]["abgeschlossen"])

    def test_4_entwurf_und_entfaellt(self):
        entwurf_speichern(self.bh, self.ab, self.nr, fazit="Super Kampagne", stunden=True, km=False)
        self.assertEqual(self.ab.auftrag(self.nr)["bericht"]["fazit"], "Super Kampagne")
        with self.assertRaisesRegex(ValueError, "begruenden"):
            entfaellt(self.bh, self.ab, self.nr, "")
        entfaellt(self.bh, self.ab, self.nr, "reiner Dreh")
        self.assertEqual(self.ab.auftrag(self.nr)["abschluss"]["bericht"], "entfaellt")


class TestLernenP4(unittest.TestCase):
    def setUp(self):
        self.bh, self.ab, self.nr, self.ps = _auftrag([REEL, FEED])
        self.ks = KundenStore(self.bh)

    def test_1_ist_kontakte_median_und_kampagnen(self):
        from orchestrator.core.postings import ist_kontakte, kampagnen
        for pid, n in ((f"{self.nr}-P1-1", 50000), (f"{self.nr}-P1-2", 30000), (f"{self.nr}-P2-1", 61000)):
            self.ps.veroeffentlichen(pid, datum=GESTERN)
            self.ps.kennzahlen_setzen(pid, {"aufrufe" if "P1" in pid else "impressionen": n})
        ik = ist_kontakte(self.bh.eintraege())
        self.assertEqual(ik["reel_solo"], {"median": 40000, "anzahl": 2, "min": 30000, "max": 50000})
        self.assertEqual(ik["feed"]["median"], 61000)
        k = kampagnen(self.bh.eintraege(), self.ab.auftrag(self.nr)["firma"])
        self.assertEqual((k[0]["nummer"], k[0]["gemessen"], k[0]["postings"], k[0]["kontakte_ist"]), (self.nr, 3, 3, 141000))

    def test_2_messpunkt_30(self):
        from orchestrator.core.postings import lang_faellig
        pid = f"{self.nr}-P1-1"
        self.ps.veroeffentlichen(pid, datum=(HEUTE - timedelta(days=30)).isoformat())
        with self.assertRaisesRegex(ValueError, "7 Tagen"):
            self.ps.kennzahlen_setzen(pid, {"aufrufe": 1}, messpunkt=30)
        self.ps.kennzahlen_setzen(pid, {"aufrufe": 50000})
        self.assertTrue(lang_faellig(self.ps.get(pid)))
        ids = [t["id"] for t in geschaefts_todos(self.bh, self.ks)]
        self.assertIn(f"po-30:{pid}", ids)
        self.ps.kennzahlen_setzen(pid, {"aufrufe": 90000}, messpunkt=30)
        x = self.ps.get(pid)
        self.assertEqual((x["kennzahlen"]["aufrufe"], x["kennzahlen_30"]["aufrufe"]), (50000, 90000))   # Bericht: 7 Tage
        self.assertNotIn(f"po-30:{pid}", [t["id"] for t in geschaefts_todos(self.bh, self.ks)])
        self.assertFalse(lang_faellig(self.ps.get(f"{self.nr}-P2-1") | {"kennzahlen": {"impressionen": 1}, "datum": "2026-01-01"}))

    def test_3_folgeauftrag_14_tage(self):
        self.bh.erfassen("auftrag_bericht_versendet", {"nummer": self.nr, "akte_id": "D-1", "an": "a@b.de", "version": 1})
        folge = lambda heute: [t for t in geschaefts_todos(self.bh, self.ks, heute=heute) if t["id"] == f"ab-folge:{self.nr}"]
        self.assertFalse(folge(HEUTE + timedelta(days=13)))
        t = folge(HEUTE + timedelta(days=14))
        self.assertEqual((t[0]["stufe"], t[0]["erledigen"]["pfad"]), ("woche", f"/api/crm/auftraege/{self.nr}/folge-erledigt"))
        self.bh.erfassen("auftrag_folge_erledigt", {"nummer": self.nr})
        self.assertFalse(folge(HEUTE + timedelta(days=20)))


class TestApi(ApiBasis):
    def _auftrag(self):
        r = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst",
                                                               "positionen": [REEL]}}).json()
        self.c.post(f"/api/crm/angebote/{r['nummer']}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{r['nummer']}/auftrag", json={"annehmen": True}).json()["nummer"]
        for pid in (f"{nr}-P1-1", f"{nr}-P1-2"):
            self.c.post(f"/api/crm/postings/{pid}/veroeffentlicht", json={"datum": GESTERN})
            self.c.post(f"/api/crm/postings/{pid}/kennzahlen", json={"werte": {"aufrufe": 40000}})
        return nr

    def test_a1_vorschau_senden_akte(self):
        nr = self._auftrag()
        d = self.c.get(f"/api/crm/auftraege/{nr}/bericht").json()
        self.assertIn("80.000 Kontakte", d["fazit_vorschlag"])
        self.assertTrue(self.c.post(f"/api/crm/auftraege/{nr}/bericht", json={"fazit": "Top!", "stunden": False}).json()["ok"])
        p = self.c.get(f"/api/crm/auftraege/{nr}/bericht/pdf")
        self.assertEqual(p.headers["content-type"], "application/pdf")
        self.assertIn("Top!", _text(p.content))
        v = self.c.get(f"/api/crm/auftraege/{nr}/bericht/versandvorschau").json()
        self.assertEqual((v["an"], v["version"]), ("anna@brandx.de", 1))
        ohne = self.c.post(f"/api/crm/auftraege/{nr}/bericht/senden", json={"an": v["an"], "betreff": v["betreff"], "text": v["text"]}).json()
        self.assertFalse(ohne["ok"])                                              # ohne Bestaetigung nichts
        self.assertEqual(self.g.gesendet, [])
        r = self.c.post(f"/api/crm/auftraege/{nr}/bericht/senden", json={"an": v["an"], "betreff": v["betreff"], "text": v["text"],
                                                                          "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.g.gesendet[0]["anhaenge"][0][0], f"Projektbericht_{nr}.pdf")
        d = self.c.get(f"/api/crm/auftraege/{nr}/bericht").json()
        self.assertEqual(len(d["berichte"]), 1)
        archiv = self.c.get(f"/api/crm/auftraege/{nr}/bericht/pdf?archiv=1")
        self.assertIn("Top!", _text(archiv.content))
        self.c.post(f"/api/crm/auftraege/{nr}/bericht", json={"fazit": "Korrigiert"})   # spaeter: neue Version, alte bleibt
        self.assertIn("Top!", _text(self.c.get(f"/api/crm/auftraege/{nr}/bericht/pdf?archiv=1").content))
        self.assertIn("Version 2", _text(self.c.get(f"/api/crm/auftraege/{nr}/bericht/pdf").content))
        self.assertTrue(self.c.post(f"/api/crm/auftraege/{nr}/kundenstimme-entwurf", json={}).json()["ok"])  # P4: nur Entwurf
        self.assertEqual(len(self.g.gesendet), 1)                                  # weiterhin nur der Bericht gesendet
        akte = self.c.get(f"/api/crm/kunden/{self.k}/akte").json()
        self.assertEqual(akte["kampagnen"][0]["nummer"], nr)
        self.assertEqual(self.c.get("/api/crm/katalog").json()["ist_kontakte"]["reel_solo"]["median"], 40000)
        self.assertEqual([(x["art"], x["bezug"]) for x in akte["dokumente"] if x["art"] == "bericht"], [("bericht", nr)])


if __name__ == "__main__":
    unittest.main()
