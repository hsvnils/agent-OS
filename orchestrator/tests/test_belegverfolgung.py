"""BELEGVERFOLGUNG B1: verbundene Belege und Ereignisse -- gleiche Kette von jedem Glied, Beschriftungen, Korrektur nach
Storno (`korrektur_zu` und Altfaelle), Mahnstufen/Mahnverfahren/Akte-Dokument an der Altrechnung, keine fremden Belege,
Rechte (Rechnungen nur mit Modul Finanzen)."""
import unittest

from orchestrator.core.belegverfolgung import kette
from orchestrator.core.firmenakte import Firmenakte
from orchestrator.tests.test_altrechnungen import PDF, _rs
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mahnverfahren import _drei_mahnungen
from orchestrator.tests.test_rechnungen import FD
from orchestrator.tests.test_zahlungsbedingungen import HEUTE, _ablauf


def _kanten(k):
    return {(e["von"], e["text"], e["nach"]) for e in k["kanten"]}


class TestKette(unittest.TestCase):
    def test_1_angebot_auftrag_vorkasse_schluss_zahlung(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 10, "vorkasse": {"art": "prozent", "wert": 50}})
        v = rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr), vorkasse=True)["entwurf_id"], FD)["nummer"]
        rs.bezahlt(v, datum=HEUTE().isoformat())
        s = rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"], FD)["nummer"]
        anderes = st.anlegen({"firma": st.angebot(an)["firma"], "positionen": [{"beschreibung": "X", "menge": "1",
                                                                                   "einzelpreis": "1"}]})["nummer"]
        k = kette(bh.eintraege(), nr)
        arten = [(x["art"], x["nummer"]) for x in k["knoten"]]
        self.assertEqual(arten[:2], [("angebot", an), ("auftrag", nr)])
        self.assertIn(("vorkasse", v), arten)
        self.assertIn(("schlussrechnung", s), arten)
        self.assertNotIn(anderes, [x["nummer"] for x in k["knoten"]])        # gleiche Firma, aber nicht verbunden
        self.assertTrue({(an, "beauftragt", nr), (nr, "Vorkasse", v), (v, "abgezogen in", s), (v, "bezahlt", f"Z:{v}:0")}
                        <= _kanten(k))
        self.assertEqual((k["start"], k["vorher"]), (nr, 1))
        for glied in (an, v, s):                                               # gleiche Kette von jedem Glied aus
            self.assertEqual({x["id"] for x in kette(bh.eintraege(), glied)["knoten"]}, {x["id"] for x in k["knoten"]})
        self.assertEqual([x["gross"] for x in k["knoten"] if x["art"] == "zahlung"], [False])
        self.assertEqual(k["knoten"][0]["oeffnen"], {"act": "an-detail", "id": an})

    def test_2_storno_und_korrektur(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 14})
        r1 = rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"], FD)["nummer"]
        x = rs.stornieren(r1, FD, grund="Fehler", korrektur=True)
        self.assertEqual(rs.get(x["korrektur_entwurf"])["korrektur_zu"], r1)
        k = kette(bh.eintraege(), r1)
        self.assertTrue({(r1, "storniert durch", x["storno"]), (r1, "ersetzt durch", x["korrektur_entwurf"])} <= _kanten(k))
        r3 = rs.festschreiben(x["korrektur_entwurf"], FD)["nummer"]
        self.assertEqual(rs.get(r3)["korrektur_zu"], r1)
        self.assertIn((r1, "ersetzt durch", r3), _kanten(kette(bh.eintraege(), r3)))
        reihe = [x["nummer"] for x in kette(bh.eintraege(), r3)["knoten"]]
        self.assertEqual(reihe[-3:], [r1, x["storno"], r3])                    # gleicher Tag: Reihenfolge der Kette
        alt = [e for e in bh.eintraege()]                                      # Altfall ohne korrektur_zu: abgeleitet
        for e in alt:
            if e["typ"] == "rechnung_festgeschrieben":
                e["daten"].pop("korrektur_zu", None)
        self.assertIn((r1, "ersetzt durch", r3), _kanten(kette(alt, r3)))

    def test_3_altrechnung_mahnungen_verfahren_dokument(self):
        bh, ks, rs, k = _rs()
        ms = _drei_mahnungen(bh, ks, rs, k)
        ms.mahnverfahren_setzen("RG-11052026", datum=HEUTE().isoformat(), durch="Anwältin")
        Firmenakte(bh, ks).hochladen(k, PDF, "anwalt.pdf", titel="Schreiben der Anwältin", art="anwalt", bezug="RG-11052026")
        kk = kette(bh.eintraege(), "RG-11052026-M2")
        arten = [x["art"] for x in kk["knoten"]]
        self.assertEqual(arten.count("mahnung"), 3)
        self.assertEqual((arten[0], "mahnverfahren" in arten, "dokument" in arten), ("rechnung", True, True))
        self.assertEqual(kk["knoten"][kk["position"]]["nummer"], "RG-11052026-M2")
        self.assertTrue(kk["knoten"][kk["position"]]["oeffnen"]["url"].endswith("/RG-11052026-M2/pdf"))

    def test_4_rechte_und_unbekannt(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 14})
        r1 = rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"], FD)["nummer"]
        ohne = kette(bh.eintraege(), nr, finanzen=False)
        self.assertEqual([x["nummer"] for x in ohne["knoten"]], [an, nr])
        with self.assertRaises(PermissionError):
            kette(bh.eintraege(), r1, finanzen=False)
        with self.assertRaises(KeyError):
            kette(bh.eintraege(), "RE-2099-0001")


class TestApi(ApiBasis):
    def test_a1_endpunkt(self):
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        d = self.c.get(f"/api/crm/belege/{an}/verfolgung").json()
        self.assertEqual([x["nummer"] for x in d["knoten"]], [an, nr])
        self.assertEqual((d["vorher"], d["nachher"]), (0, 1))
        self.assertEqual(self.c.get("/api/crm/belege/AN-2099-0009/verfolgung").status_code, 404)


if __name__ == "__main__":
    unittest.main()
