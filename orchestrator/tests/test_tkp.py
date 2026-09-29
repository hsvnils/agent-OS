"""KUNDEN_FINANZEN Etappe 16 (CEO 2026-09-29): Reichweiten-Formate kalkulieren Kontakte x TKP / 1.000 + Produktion;
TKP je Angebot waehlbar (Community-Fit), Rechnung und OMR-Vergleich (mit Link) im Angebot an-/abwaehlbar."""
import copy
import io
import json
import unittest

from pypdf import PdfReader

from orchestrator.core.angebote import AngebotStore, preisliste_pdf
from orchestrator.core.katalog import OMR, STANDARD, Katalog, pruefe, tkp_preis
from orchestrator.tests.test_angebote import FIRMA, _stores


def _text(pdf: bytes) -> str:
    return " ".join(" ".join(s.extract_text() for s in PdfReader(io.BytesIO(pdf)).pages).split())   # ohne Umbrueche


def _links(pdf: bytes) -> list[str]:
    out = []
    for s in PdfReader(io.BytesIO(pdf)).pages:
        for a in s.get("/Annots") or []:
            a = a.get_object()
            if a.get("/A") and a["/A"].get("/URI"):
                out.append(str(a["/A"]["/URI"]))
    return out


def _pos(k: dict, iid: str, tkp_euro: int | None = None, **x) -> dict:
    it = next(i for g in k["gruppen"] for i in g["items"] if i["id"] == iid)
    p = {"beschreibung": it["name"], "menge": "1", "einzelpreis_cent": it["preis_cent"], "katalog_id": iid}
    if it.get("kontakte"):
        p |= {k2: it[k2] for k2 in ("kontakte", "produktion_cent", "tkp_min_cent", "tkp_max_cent", "omr")}
        p["tkp_cent"] = (tkp_euro or it["tkp_min_cent"] // 100) * 100
    return p | x


class TestKatalogTkp(unittest.TestCase):
    def test_1_preise_und_migration(self):
        self.assertEqual((tkp_preis(52000, 2000, 26000), tkp_preis(52000, 2500, 26000), tkp_preis(52000, 3000, 26000)),
                         (130000, 156000, 182000))
        self.assertEqual((tkp_preis(34000, 2000, 10000), tkp_preis(34000, 3000, 10000)), (78000, 112000))
        self.assertEqual((tkp_preis(1001, 1500, 0), tkp_preis(1000, 1400, 0)), (2000, 1000))   # 15,02 -> 20 €, 14 -> 10 €
        bh, *_ = _stores()
        kat = Katalog(bh)
        alt = copy.deepcopy(STANDARD)                                                     # Live-Katalog von vorher: ohne TKP
        for g in alt["gruppen"]:
            for it in g["items"]:
                for f in ("kontakte", "produktion_cent", "tkp_min_cent", "tkp_max_cent", "omr"):
                    it.pop(f, None)
        kat.pfad.write_text(json.dumps(alt), encoding="utf-8")
        preise = {it["id"]: it["preis_cent"] // 100 for g in kat.laden()["gruppen"] for it in g["items"]}
        self.assertEqual({k: preise[k] for k in ("feed", "story", "reel_solo", "reel_int", "fb_post")},
                         {"feed": 1300, "story": 780, "reel_solo": 1600, "reel_int": 1050, "fb_post": 200})

    def test_2_validierung(self):
        k = copy.deepcopy(STANDARD)
        it = k["gruppen"][0]["items"][2]
        it |= {"kontakte": 52000, "produktion_cent": 26000, "tkp_min_cent": 3000, "tkp_max_cent": 2000}
        with self.assertRaises(ValueError):
            pruefe(k)                                                                   # Minimum > Maximum
        it |= {"tkp_min_cent": 2000, "tkp_max_cent": 3000, "preis_cent": 99, "omr": "quatsch"}
        f = pruefe(k)["gruppen"][0]["items"][2]
        self.assertEqual((f["preis_cent"], f["omr"]), (130000, ""))                    # Preis folgt dem TKP


class TestAngebotTkp(unittest.TestCase):
    def _angebot(self, **x):
        bh, ks, _, k, ap = _stores()
        (bh.dir / "firmendaten.json").write_text(json.dumps(FIRMA), encoding="utf-8")
        kat = Katalog(bh)
        st = AngebotStore(bh, ks, kat)
        kd = kat.laden()
        daten = {"firma": k, "ansprechpartner": ap, "positionen": [
            _pos(kd, "feed", 25, einzelpreis_cent=1),                                      # falscher Preis vom Client
            _pos(kd, "story"), _pos(kd, "x_post")]} | x
        return st, kat, st.anlegen(daten)["nummer"]

    def test_1_preis_folgt_tkp_und_bleibt_eingefroren(self):
        st, kat, nr = self._angebot()
        a = st.angebot(nr)
        self.assertEqual([p["einzelpreis_cent"] for p in a["positionen"]], [156000, 78000, 15000])
        self.assertEqual(a["positionen"][0]["tkp_cent"], 2500)
        self.assertEqual(a["summe_cent"], 156000 + 78000 + 15000)
        k = kat.laden()
        next(i for g in k["gruppen"] for i in g["items"] if i["id"] == "feed")["produktion_cent"] = 99900
        kat.speichern(k)
        self.assertEqual(st.angebot(nr)["summe_cent"], 156000 + 78000 + 15000)         # Katalog aendert nichts mehr
        with self.assertRaises(ValueError):
            st.aendern(nr, {"positionen": [_pos(kat.laden(), "feed", 600)]})           # TKP ueber 500 EUR

    def test_2_pdf_rechnung_und_omr_schaltbar(self):
        st, _, nr = self._angebot()
        b = st.angebot(nr)["bloecke"]
        self.assertEqual((b["tkp_zeigen"], b["omr_zeigen"]), (True, False))           # Standard: Rechnung ja, OMR nein
        t = _text(st.pdf(nr, FIRMA))
        self.assertIn("52.000 Kontakte × 25 € TKP = 1.300 € + 260 € Produktion ≈ 1.560 €", t)
        self.assertIn("In diesem Angebot: Feed-Post oder Karussell 25 €; Story-Serie, 3 Frames 20 €", t)
        self.assertNotIn("OMR", t)
        st.aendern(nr, {"omr_zeigen": True})
        pdf = st.pdf(nr, FIRMA)
        t = _text(pdf)
        self.assertIn("Instagram-Post 20–30 €, Instagram-Story 20–50 € TKP", t)
        self.assertIn(OMR["url"], _links(pdf))
        st.aendern(nr, {"tkp_zeigen": False, "zeige_kalkulation": False})
        t = _text(st.pdf(nr, FIRMA))
        self.assertNotIn("Kontakte ×", t)                                                # Rechnung ausgeblendet
        self.assertIn("Zum Vergleich: OMR", t)                                           # OMR bleibt (eigener Haken)

    def test_3_preisliste_mit_spanne_und_omr(self):
        st, kat, _ = self._angebot()
        pdf = preisliste_pdf(kat.laden(), FIRMA, logo=None)
        t = _text(pdf)
        self.assertIn("Passung zu Ihrer Zielgruppe 20–40 €", t)
        self.assertIn("34.000 Kontakte × 20 € TKP = 680 € + 100 € Produktion ≈ 780 €", t)
        self.assertIn(OMR["url"], _links(pdf))


if __name__ == "__main__":
    unittest.main()
