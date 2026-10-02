"""PROJEKTBERICHT P1: Postings je Position (Menge), veroeffentlicht am/Link, Kennzahlen als Zahlen, festgeschriebene
Konditionen und TKP-Vergleich; Katalog-Aenderungen wirken nie auf bestehende Auftraege/Belege."""
import unittest
from datetime import timedelta

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.katalog import Katalog
from orchestrator.core.postings import Postings, format_von, postings_aus, vergleich
from orchestrator.tests.test_angebote import ApiBasis, _stores

HEUTE = jetzt().date()
REEL = {"beschreibung": "Reel, Standalone", "menge": "2", "einheit": "Stück", "katalog_id": "reel_solo",
        "kontakte": 37000, "tkp_cent": 3000, "produktion_cent": 49000, "einzelpreis": "0"}          # 37.000 x 30 / 1.000 + 490 = 1.600 EUR
FEED = {"beschreibung": "Feed-Post oder Karussell", "menge": "1", "katalog_id": "feed",
        "kontakte": 52000, "tkp_cent": 2500, "produktion_cent": 26000, "einzelpreis": "0"}          # 1.300 + 260 = 1.560 EUR
PAUSCHAL = [{"beschreibung": "WhatsApp-Kanal", "menge": "1", "katalog_id": "wa", "einzelpreis": "100"},
            {"beschreibung": "Story-Paket", "menge": "1", "einzelpreis": "300"}]


def _auftrag(pos=None):
    bh, ks, st, k, ap = _stores()
    an = st.anlegen({"firma": k, "positionen": pos or [REEL, FEED] + PAUSCHAL})["nummer"]
    st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
    ab = AuftragBuch(bh, ks, st)
    nr = ab.aus_angebot(an)["nummer"]
    return bh, ab, nr, Postings(bh, ab, bh.dir.parent / "lieferungen")


class TestPostings(unittest.TestCase):
    def test_1_aus_menge_und_format(self):
        bh, ab, nr, ps = _auftrag()
        p = ps.liste(nr)
        self.assertEqual([(x["id"], x["titel"], x["format"], x["kontakt_feld"]) for x in p],
                         [(f"{nr}-P1-1", "Reel 1", "reel", "aufrufe"), (f"{nr}-P1-2", "Reel 2", "reel", "aufrufe"),
                          (f"{nr}-P2-1", "Bild-Post", "feed", "impressionen"), (f"{nr}-P4-1", "Story", "story", "aufrufe")])
        self.assertEqual(p[0]["plan"], {"kontakte": 37000, "tkp_cent": 3000, "produktion_cent": 49000, "preis_cent": 160000})
        self.assertIsNone(format_von({"beschreibung": "Spieltags-Paket", "katalog_id": "pk_match"}))
        self.assertEqual(format_von({"beschreibung": "TikTok-Video"}), ("reel", "TikTok"))

    def test_2_veroeffentlicht_pruefungen(self):
        bh, ab, nr, ps = _auftrag()
        pid = f"{nr}-P1-2"
        with self.assertRaisesRegex(ValueError, "Zukunft"):
            ps.veroeffentlichen(pid, datum=(HEUTE + timedelta(days=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "Link"):
            ps.veroeffentlichen(pid, datum=HEUTE.isoformat(), link="instagram reel")
        with self.assertRaises(KeyError):
            ps.veroeffentlichen(f"{nr}-P3-1", datum=HEUTE.isoformat())             # WhatsApp ist kein Posting
        ps.veroeffentlichen(pid, datum=(HEUTE - timedelta(days=7)).isoformat(), link="https://www.instagram.com/reel/abc/")
        x = ps.get(pid)
        self.assertEqual((x["datum"], x["plattform"], x["kennzahl_faellig"]), ((HEUTE - timedelta(days=7)).isoformat(), "Instagram", True))
        self.assertEqual([p["id"] for p in ps.faellige([ab.auftrag(nr)])], [pid])
        self.assertEqual(ps.faellige([ab.auftrag(nr)], heute=HEUTE - timedelta(days=1)), [])   # erst am 7. Tag

    def test_3_kennzahlen_als_zahlen_mit_verlauf(self):
        bh, ab, nr, ps = _auftrag()
        pid = f"{nr}-P2-1"
        with self.assertRaisesRegex(ValueError, "Impressionen fehlt"):
            ps.kennzahlen_setzen(pid, {"aufrufe": 5})                               # Feed zaehlt Impressionen
        ps.kennzahlen_setzen(pid, {"impressionen": "61.250", "likes": 900, "unbekannt": 3})
        ps.kennzahlen_setzen(pid, {"impressionen": 61300, "likes": 905}, quelle="screenshot")
        x = ps.get(pid)
        self.assertEqual(x["kennzahlen"], {"impressionen": 61300, "likes": 905})
        self.assertEqual(x["kennzahlen_quelle"], "screenshot")
        self.assertEqual([v["typ"] for v in x["verlauf"]], ["posting_kennzahlen"] * 2)

    def test_4_tkp_vergleich(self):
        bh, ab, nr, ps = _auftrag()
        ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": 50000})
        ps.kennzahlen_setzen(f"{nr}-P1-2", {"aufrufe": 30000})
        ps.kennzahlen_setzen(f"{nr}-P4-1", {"aufrufe": 8000})                     # Pauschale: nur Reichweite
        v = vergleich(ps.liste(nr))
        z = {r["id"]: r for r in v["zeilen"]}
        r1 = z[f"{nr}-P1-1"]
        self.assertEqual((r1["gegenwert_cent"], r1["mehrleistung_cent"], r1["erfuellung_pct"]), (199000, 39000, 135.1))
        self.assertEqual(r1["tkp_eff_cent"], round((160000 - 49000) / 50000 * 1000))   # 22,20 EUR statt 30 EUR
        self.assertEqual(z[f"{nr}-P1-2"]["mehrleistung_cent"], 139000 - 160000)
        self.assertIsNone(z[f"{nr}-P4-1"]["gegenwert_cent"])
        s = v["summe"]
        self.assertEqual((s["kontakte_plan"], s["kontakte_ist"], s["preis_cent"], s["mehrleistung_cent"], s["gemessen"]),
                         (74000, 80000, 320000, 18000, 3))
        self.assertEqual(s["mehrleistung_pct"], 5.6)

    def test_5_katalog_aenderung_wirkt_nicht_zurueck(self):
        bh, ab, nr, ps = _auftrag()
        vorher = (ab.auftrag(nr)["positionen"], ab.auftrag(nr)["summe_cent"], ps.liste(nr)[0]["plan"])
        kat = Katalog(bh)
        k = kat.laden()
        for g in k["gruppen"]:
            for it in g["items"]:
                if it["id"] == "reel_solo":
                    it |= {"kontakte": 10000, "produktion_cent": 99000, "tkp_min_cent": 5000, "tkp_max_cent": 6000}
        self.assertTrue(kat.speichern(k)["geaendert"])
        nachher = (ab.auftrag(nr)["positionen"], ab.auftrag(nr)["summe_cent"], ps.liste(nr)[0]["plan"])
        self.assertEqual(vorher, nachher)


class TestApi(ApiBasis):
    def test_a1_endpunkte_und_rechnung_festgeschrieben(self):
        r = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst",
                                                               "positionen": [REEL]}}).json()
        an = r["nummer"]
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        d = self.c.get(f"/api/crm/auftraege/{nr}/postings").json()
        self.assertEqual(len(d["postings"]), 2)
        self.assertEqual(d["konditionen"]["positionen"][0]["tkp_cent"], 3000)
        self.assertEqual(d["konditionen"]["festgeschrieben_am"], HEUTE.isoformat())
        pid = d["postings"][0]["id"]
        self.assertTrue(self.c.post(f"/api/crm/postings/{pid}/veroeffentlicht", json={"datum": HEUTE.isoformat()}).json()["ok"])
        k = self.c.post(f"/api/crm/postings/{pid}/kennzahlen", json={"werte": {"aufrufe": "40000"}}).json()
        self.assertTrue(k["ok"], k)
        self.assertEqual(self.c.get(f"/api/crm/auftraege/{nr}/postings").json()["vergleich"]["summe"]["kontakte_ist"], 40000)
        kat = Katalog(self.w.kunden_store.bh)
        kk = kat.laden()
        for g in kk["gruppen"]:
            for it in g["items"]:
                if it["id"] == "reel_solo":
                    it |= {"tkp_min_cent": 5000, "tkp_max_cent": 6000}
        kat.speichern(kk)
        re_ = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()
        self.assertTrue(re_["ok"], re_)
        pos = self.w._rechnungen().get(re_["entwurf_id"])["positionen"][0]
        self.assertEqual((pos["tkp_cent"], pos["einzelpreis_cent"]), (3000, 160000))


if __name__ == "__main__":
    unittest.main()
