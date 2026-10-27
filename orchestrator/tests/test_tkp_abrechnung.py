"""TKP_ABRECHNUNG T1-T3: Abrechnung nach erzielter Reichweite bzw. Festpreis mit Reichweiten-Ausgleich -- Angebot
(voraussichtlich, Hoechstbetrag, Klausel), Auftrag (eingefroren), Rechnung (Ist aus Postings, Ausgleich auch als Abzug,
Festschreiben erst nach Messung, Abweichung nur mit Grund)."""
import io
import re
import unittest

from pypdf import PdfReader

from orchestrator.core import tkp_abrechnung as tkp
from orchestrator.core.angebote import _positionen, inhalt_hash
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.postings import Postings
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import _stores
from orchestrator.tests.test_postings import FEED, PAUSCHAL, REEL
from orchestrator.tests.test_rechnungen import FD

TEXT = lambda pdf: re.sub(r"\s+", " ", " ".join(s.extract_text() for s in PdfReader(io.BytesIO(pdf)).pages))  # noqa: E731
HEUTE = jetzt().date().isoformat()
# REEL: 2 x (37.000 x 30 EUR + 490 EUR) = 2 x 1.600 EUR; FEED: 52.000 x 25 EUR + 260 EUR = 1.560 EUR; Pauschalen 400 EUR


def _ablauf(abrechnung, pos=None, zahlung=None):
    bh, ks, st, k, ap = _stores()
    d = {"firma": k, "positionen": pos or [REEL, FEED] + PAUSCHAL, "abrechnung": abrechnung}
    if zahlung:
        d["zahlung"] = zahlung
    an = st.anlegen(d)["nummer"]
    st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
    ab = AuftragBuch(bh, ks, st)
    nr = ab.aus_angebot(an, leistung_von=HEUTE)["nummer"]
    return bh, ks, st, an, ab, nr, Postings(bh, ab, bh.dir.parent / "lieferungen"), RechnungStore(bh, ks)


def _messen(ps, nr, reel=(40000, 50000), feed=60000):
    ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": reel[0]})
    ps.kennzahlen_setzen(f"{nr}-P1-2", {"aufrufe": reel[1]})
    if feed is not None:
        ps.kennzahlen_setzen(f"{nr}-P2-1", {"impressionen": feed})


def _ohne_summe(pos):
    return [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in pos]


class TestKopf(unittest.TestCase):
    def test_1_pruefen(self):
        self.assertEqual(tkp.pruefen(None), {})
        self.assertEqual(tkp.pruefen({"art": "fest"}), {})
        self.assertEqual(tkp.pruefen({"art": "reichweite"}), {"art": "reichweite", "deckel_prozent": 25})
        self.assertEqual(tkp.pruefen({"art": "reichweite", "deckel_prozent": ""}), {"art": "reichweite"})   # ohne Deckel
        self.assertEqual(tkp.pruefen({"art": "ausgleich", "ausgleich_tkp": "20"}),
                         {"art": "ausgleich", "deckel_prozent": 25, "toleranz_prozent": 10, "ausgleich_tkp_cent": 2000})
        for falsch in ({"art": "pauschal"}, {"art": "ausgleich", "toleranz_prozent": 60}, {"art": "reichweite", "deckel_prozent": -1},
                       {"art": "ausgleich", "ausgleich_tkp_cent": 50}):
            with self.assertRaises(ValueError, msg=falsch):
                tkp.pruefen(falsch)

    def test_2_festpreis_alte_staende_unveraendert(self):
        bh, ks, st, k, ap = _stores()
        an = st.anlegen({"firma": k, "positionen": [REEL]})["nummer"]
        a = st.angebot(an)
        self.assertNotIn("hoechst_cent", a)
        import hashlib, json
        from orchestrator.core.angebote import KOPF_FELDER
        roh = {"firma": k, "positionen": _positionen([REEL]), "abrechnung": {}}
        alt = {kk: roh.get(kk) for kk in KOPF_FELDER if kk not in ("nachfassen_tage", "ware", "abrechnung")}
        alt_hash = hashlib.sha256(json.dumps(alt | {"positionen": roh["positionen"]}, sort_keys=True,
                                             ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(inhalt_hash(roh), alt_hash)                                     # Hash wie vor T1


class TestAngebot(unittest.TestCase):
    def test_1_reichweite_voraussichtlich_hoechstens_vorkasse(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite"}, zahlung={"vorkasse": {"art": "prozent", "prozent": 50}})
        a = st.angebot(an)
        self.assertEqual(a["summe_cent"], 2 * 160000 + 156000 + 40000)
        # Deckel 25 %: Reel 46.250 x 30 = 1.387,50 + 490 = 1.877,50 (x2); Feed 65.000 x 25 = 1.625 + 260 = 1.885
        self.assertEqual(a["hoechst_cent"], 2 * 187750 + 188500 + 40000)
        self.assertEqual(a["vorkasse_basis_cent"], 2 * 49000 + 26000 + 40000)              # nur Produktion + Pauschalen
        t = TEXT(st.pdf(an, FD))
        self.assertIn("Gesamt (voraussichtlich)", t)
        self.assertIn("Abrechnung nach Reichweite", t)
        self.assertIn("höchstens 6.040,00 €", t)
        self.assertIn("Vorkasse auf die Produktion (820,00 €)", t)
        self.assertEqual(ab.auftrag(nr)["abrechnung"], {"art": "reichweite", "deckel_prozent": 25})   # eingefroren
        self.assertEqual(ab.auftrag(nr)["vorkasse_cent"], 82000)
        self.assertIn("Abrechnung nach Reichweite", TEXT(ab.pdf(nr, FD)))

    def test_2_ausgleich_klausel(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "ausgleich", "toleranz_prozent": 10})
        a = st.angebot(an)
        self.assertEqual(a["summe_cent"], 2 * 160000 + 156000 + 40000)                  # Festpreis bleibt
        t = TEXT(st.pdf(an, FD))
        self.assertIn("Reichweiten-Ausgleich: Geplant sind insgesamt 126.000 Kontakte", t)
        self.assertIn("um mehr als 10 %", t)
        self.assertNotIn("voraussichtlich", t)


class TestRechnung(unittest.TestCase):
    def test_1_reichweite_aus_postings(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite"})
        _messen(ps, nr)                                                                   # Reel 90.000, Feed 60.000
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"]
        pos = rs.get(eid)["positionen"]
        self.assertEqual([p["beschreibung"] for p in pos][:4],
                         ["Reel, Standalone", "Produktion: Reel, Standalone", "Feed-Post oder Karussell",
                          "Produktion: Feed-Post oder Karussell"])
        self.assertEqual(pos[0]["gesamt_cent"], 270000)                                  # 90.000 x 30 EUR (Deckel 92.500)
        self.assertEqual(pos[1]["gesamt_cent"], 98000)                                   # 2 x 490 EUR
        self.assertEqual(pos[2]["gesamt_cent"], 150000)                                  # 60.000 x 25 EUR
        self.assertIn("90.000 Aufrufe erzielt (geplant 74.000)", pos[0]["detail"])
        r = rs.get(rs.festschreiben(eid, FD)["nummer"])
        self.assertEqual(r["summe_cent"], 270000 + 98000 + 150000 + 26000 + 40000)
        self.assertIn("60.000 Impressionen erzielt", TEXT(rs._pdf(r, FD)))

    def test_2_deckel_greift(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite", "deckel_prozent": 10}, pos=[REEL])
        _messen(ps, nr, reel=(60000, 60000), feed=None)
        p = rs.get(rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"])["positionen"][0]
        self.assertEqual(p["reichweite"]["zeilen"][0]["abgerechnet"], 81400)              # 74.000 + 10 %
        self.assertEqual(p["gesamt_cent"], 244200)
        self.assertIn("begrenzt auf 81.400", p["detail"])

    def test_3_festschreiben_erst_nach_messung_dann_nachziehen(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite"})
        ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": 40000})                           # Reel 2 + Feed fehlen
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"]
        self.assertTrue(rs.get(eid)["positionen"][0]["reichweite"]["offen"])
        with self.assertRaisesRegex(ValueError, "Erzielte Kontakte fehlen noch"):
            rs.festschreiben(eid, FD)
        _messen(ps, nr)
        r = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))
        self.assertEqual((r["entwurf_id"], r["aktualisiert"]), (eid, True))              # derselbe Entwurf, nachgezogen
        self.assertEqual(rs.get(eid)["positionen"][0]["gesamt_cent"], 270000)
        rs.festschreiben(eid, FD)

    def test_4_abweichung_nur_mit_grund_und_bleibt_beim_nachziehen(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite"}, pos=[REEL])
        _messen(ps, nr, feed=None)
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"]
        pos = _ohne_summe(rs.get(eid)["positionen"])
        z = pos[0]["reichweite"]["zeilen"][0]
        z["ist"] = 80000
        with self.assertRaisesRegex(ValueError, "Grund"):
            rs.entwurf_aendern(eid, {"positionen": pos})
        z["grund"] = "Kunde misst mit eigenem Tool"
        rs.entwurf_aendern(eid, {"positionen": pos})
        self.assertEqual(rs.get(eid)["positionen"][0]["gesamt_cent"], 240000)
        ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": 41000})                           # neue Messung
        rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))
        z = rs.get(eid)["positionen"][0]["reichweite"]["zeilen"][0]
        self.assertEqual((z["gemessen"], z["ist"], z["grund"]), (91000, 80000, "Kunde misst mit eigenem Tool"))

    def test_5_ausgleich_toleranz_mehr_und_minder(self):
        # Plan Reel 74.000 + Feed 52.000 = 126.000 Kontakte
        faelle = [(70000, 50000, 0, "innerhalb der Toleranz"),                               # 120.000 = -4,8 %
                  (90000, 60000, (16000 * 3000 + 8000 * 2500) // 1000, "Mehrleistung"),        # +19 %: 480 + 200 EUR
                  (50000, 40000, -((24000 * 3000 + 12000 * 2500) // 1000), "Minderleistung")]  # -28,6 %
        for reel, feed, cent_erwartet, wort in faelle:
            bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "ausgleich", "deckel_prozent": ""})
            _messen(ps, nr, reel=(reel // 2, reel // 2), feed=feed)
            eid = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"]
            pos = rs.get(eid)["positionen"]
            aus = pos[-1]
            self.assertEqual(len(pos), 5, wort)                                           # Positionen + 1 Ausgleich
            self.assertEqual(aus["gesamt_cent"], cent_erwartet, wort)
            self.assertIn(wort, aus["beschreibung"] + aus["detail"])
            r = rs.get(rs.festschreiben(eid, FD)["nummer"])
            self.assertEqual(r["summe_cent"], 516000 + cent_erwartet, wort)

    def test_6_ausgleich_eigener_tkp_und_deckel(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "ausgleich", "ausgleich_tkp": "20", "deckel_prozent": 5})
        _messen(ps, nr, reel=(60000, 60000), feed=70000)                                  # +64.000 (+50,8 %)
        aus = rs.get(rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"])["positionen"][-1]
        # 64.000 x 20 EUR = 1.280 EUR, gedeckelt auf 5 % von (74.000 x 30 + 52.000 x 25 = 3.520 EUR) = 176 EUR
        self.assertEqual(aus["gesamt_cent"], 17600)
        self.assertIn("begrenzt auf 5 %", aus["detail"])

    def test_7_negativ_nur_als_ausgleich(self):
        with self.assertRaisesRegex(ValueError, "negativer Preis"):
            _positionen([{"beschreibung": "Gutschrift", "einzelpreis": "-10"}])
        with self.assertRaisesRegex(ValueError, "Reichweiten"):
            _positionen([{"beschreibung": "x", "reichweite": {"typ": "rabatt", "zeilen": []}}])

    def test_8_festpreis_ohne_aenderung(self):
        bh, ks, st, an, ab, nr, ps, rs = _ablauf(None)
        _messen(ps, nr)
        pos = rs.get(rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"])["positionen"]
        self.assertEqual(len(pos), 4)
        self.assertFalse(any(p.get("reichweite") for p in pos))


class TestT3(unittest.TestCase):
    def test_1_handlungsbedarf_bis_zur_rechnung(self):
        from orchestrator.core.todos import geschaefts_todos
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "reichweite"})
        tid = f"ab-tkp-rechnung:{nr}"
        ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": 40000})
        self.assertNotIn(tid, {t["id"] for t in geschaefts_todos(bh, ks)})               # noch nicht alles gemessen
        _messen(ps, nr)
        self.assertIn(tid, {t["id"] for t in geschaefts_todos(bh, ks)})
        rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"], FD)
        self.assertNotIn(tid, {t["id"] for t in geschaefts_todos(bh, ks)})               # Rechnung da -> weg
        self.assertNotIn(tid, {t["id"] for t in geschaefts_todos(bh, ks, finanzen=False)})

    def test_2_bericht_schenkt_nicht(self):
        from orchestrator.core import projektbericht as pb
        bh, ks, st, an, ab, nr, ps, rs = _ablauf({"art": "ausgleich"})
        _messen(ps, nr)
        d = pb.daten(ab.auftrag(nr), ps.liste(nr))
        f = pb.fazit_vorschlag(d)
        self.assertIn("Reichweiten-Ausgleich", f)
        self.assertNotIn("Mehrwert", f)
        t = TEXT(pb.pdf(d, firmendaten=FD, firma_name="Brand X", fazit=f))
        self.assertIn("Abgerechnet mit dem vereinbarten Reichweiten-Ausgleich", t)

    def test_3_hanserautisch_rechnung_mit_abzug(self):
        from orchestrator.core.angebote import AngebotStore
        from orchestrator.core.katalog import Katalog
        bh, ks, st0, k, ap = _stores()
        st = AngebotStore(bh, ks, Katalog(bh))
        an = st.anlegen({"firma": k, "positionen": [REEL], "abrechnung": {"art": "ausgleich"}})["nummer"]
        self.assertIn("Reichweiten-Ausgleich", TEXT(st.pdf(an, FD)))
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        ab = AuftragBuch(bh, ks, st)
        nr = ab.aus_angebot(an, leistung_von=HEUTE)["nummer"]
        ps, rs = Postings(bh, ab, bh.dir.parent / "lieferungen"), RechnungStore(bh, ks, Katalog(bh))
        _messen(ps, nr, reel=(30000, 30000), feed=None)                                   # -14.000 (-18,9 %)
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr), postings=ps.liste(nr))["entwurf_id"]
        pos = _ohne_summe(rs.get(eid)["positionen"])
        self.assertEqual(pos[-1]["einzelpreis_cent"], -42000)
        rs.entwurf_aendern(eid, {"positionen": pos + [{"beschreibung": "Extra", "menge": "1", "einzelpreis": "10"}]})
        rs.entwurf_aendern(eid, {"positionen": pos})                                     # Editor speichert Minus erneut
        r = rs.get(rs.festschreiben(eid, FD)["nummer"])
        self.assertEqual(r["summe_cent"], 320000 - 42000)
        t = TEXT(rs._pdf(r, FD))
        self.assertIn("Reichweiten-Ausgleich: Minderleistung", t)
        self.assertIn("-420,00 €", t)

    def test_4_vertrag_klauseln(self):
        from orchestrator.core.vertrag_entwuerfe import ENTWUERFE, REICHWEITE_KLAUSELN
        self.assertEqual(set(REICHWEITE_KLAUSELN), set(tkp.ARTEN))
        texte = [p["text"] for e in ENTWUERFE.values() for p in e["paragraphen"] if p["titel"] == "§ 8 Reichweite"]
        self.assertEqual(texte, ["{Reichweite}"])


if __name__ == "__main__":
    unittest.main()
