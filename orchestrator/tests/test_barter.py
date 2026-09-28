"""KUNDEN_FINANZEN Etappe 12: Barter-Deals -- Ware als (Teil-)Gegenleistung durch Angebot, Auftrag, Rechnung, Ware-Eingang
(Einnahme zum Endpreis), Verwendung (Content = Anschaffung, privat, Leihgabe), EUeR, KU-Grenze, Mahnung nur Geldteil.
Roadmap-Verifikation: 500 EUR Geld + Ware 300 EUR -> Rechnung 800, offen 500; Content/GWG: Einnahmen 800, Ausgaben 300."""
import unittest
from datetime import timedelta
from unittest import mock

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.mahnungen import MahnStore
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_rechnungen import FD

POS800 = [{"beschreibung": "Reel-Kooperation", "menge": "1", "einheit": "Stück", "einzelpreis": "800"}]
WARE = {"text": "Kamera-Rig XY", "wert": "300"}


class TestBarter(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, self.st, self.k, self.ap = _stores()
        self.rs, self.f = RechnungStore(self.bh, self.ks), Finanzen(self.bh, self.ks)

    def _rechnung(self, ware=WARE, **extra):
        eid = self.rs.entwurf_anlegen({"firma": self.k, "ansprechpartner": self.ap, "positionen": POS800,
                                       "leistung_von": jetzt().date().isoformat(), "ware": ware} | extra)["entwurf_id"]
        return self.rs.festschreiben(eid, FD)["nummer"]

    def test_1_angebot_auftrag_rechnung_durchgaengig(self):
        import io
        from pypdf import PdfReader
        import re as _re
        text = lambda pdf: _re.sub(r"\s+", " ", " ".join(s.extract_text() for s in PdfReader(io.BytesIO(pdf)).pages))
        an = self.st.anlegen({"firma": self.k, "ansprechpartner": self.ap, "positionen": POS800, "ware": WARE,
                              "layout": "standard"})["nummer"]
        a = self.st.angebot(an)
        self.assertEqual((a["summe_cent"], a["ware_cent"], a["geld_cent"]), (80000, 30000, 50000))
        self.assertIn("in Ware (Kamera-Rig XY)", text(self.st.pdf(an, FD)))
        self.st.status_setzen(an, "versendet"); self.st.status_setzen(an, "angenommen")
        ab = AuftragBuch(self.bh, self.ks, self.st)
        nr = ab.aus_angebot(an, leistung_von=jetzt().date().isoformat())["nummer"]
        self.assertEqual(ab.auftrag(nr)["ware"], {"text": "Kamera-Rig XY", "wert_cent": 30000})
        self.assertIn("in Ware (Kamera-Rig XY)", text(ab.pdf(nr, FD)))
        eid = self.rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"]
        re = self.rs.festschreiben(eid, FD)["nummer"]
        r = self.rs.get(re)
        self.assertEqual((r["summe_cent"], r["ware_cent"], r["geld_cent"]), (80000, 30000, 50000))
        t = text((self.bh.dir / r["belege"][0]["pfad"]).read_bytes())
        self.assertIn("tauschähnlicher Umsatz", t)
        self.assertIn("in Geld zu zahlen", t)

    def test_2_geld_und_ware_content(self):
        re = self._rechnung()
        with self.assertRaises(ValueError):
            self.rs.bezahlt(re, datum="", betrag="600")                                      # nur 500 in Geld offen
        self.rs.bezahlt(re, datum="")                                                        # Rest = 500
        self.assertEqual(self.rs.get(re)["status"], "offen")                                 # Ware fehlt noch
        self.assertIn(f"re-ware:{re}", {t["id"] for t in geschaefts_todos(self.bh, self.ks)})
        r = self.rs.ware_erhalten(re, wert_nachweis="289,99")                                # eigener Nachweis zaehlt
        self.assertEqual((r["wert_cent"], r["kategorie"]), (28999, "gwg"))
        self.assertEqual(self.rs.get(re)["status"], "bezahlt")
        eu = self.f.euer(jetzt().year)
        self.assertEqual((eu["einnahmen_cent"], eu["ausgaben_cent"]), (50000 + 28999, 28999))
        self.assertEqual({p["kategorie"]: p["betrag_cent"] for p in eu["einnahmen"]}, {"umsatz": 50000, "barter": 28999})
        self.assertEqual(self.rs.umsatz(jetzt().year), 80000)                                # KU-Grenze: voller Wert
        with self.assertRaises(ValueError):
            self.rs.ware_erhalten(re)                                                        # doppelt
        with self.assertRaises(ValueError):
            self.rs.stornieren(re, FD, grund="x")                                            # erst Ware stornieren

    def test_3_privat_und_leihgabe_und_storno(self):
        re = self._rechnung(ware={"text": "Parfum", "wert": "800"})                           # reiner Barter
        self.assertEqual(self.rs.get(re)["geld_cent"], 0)
        with self.assertRaises(ValueError):
            self.rs.bezahlt(re, datum="")                                                    # kein Geld zu zahlen
        self.rs.ware_erhalten(re, verwendung="privat")
        eu = self.f.euer(jetzt().year)
        self.assertEqual((eu["einnahmen_cent"], eu["ausgaben_cent"]), (80000, 0))           # privat: nur Einnahme
        self.rs.ware_stornieren(re, "falsch erfasst")
        self.assertEqual(self.rs.get(re)["status"], "offen")
        self.rs.ware_erhalten(re, verwendung="leihgabe")
        self.assertEqual(self.f.euer(jetzt().year)["einnahmen_cent"], 0)                    # Leihgabe: keine Einnahme
        j = [z for z in self.f.journal(jetzt().year) if z["bezug"] == re]
        self.assertEqual([(z["kategorie"], z["storniert"]) for z in j], [("barter", True)])  # Storno sichtbar

    def test_4_anlage_und_mahnung_nur_geld(self):
        vor = jetzt() - timedelta(days=40)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=vor):
            re = self._rechnung(ware={"text": "Kamera", "wert": "1200"}, positionen=[{"beschreibung": "Kampagne", "menge": "1",
                                                                                   "einheit": "", "einzelpreis": "2000"}])
        with self.assertRaises(ValueError):
            self.rs.ware_erhalten(re)                                                        # > 800 -> Anlage ohne ND
        self.rs.ware_erhalten(re, nutzungsdauer_jahre=7)
        a = self.f.anlagen(jetzt().year)
        self.assertEqual([(x["bezeichnung"], x["ak_cent"], x["nutzungsdauer_jahre"]) for x in a], [("Kamera", 120000, 7)])
        m = MahnStore(self.bh, self.ks).berechnen(re)
        self.assertEqual(m["offen_cent"], 80000)                                             # nur Geldteil 2.000 - 1.200
        self.rs.bezahlt(re, datum="")
        with self.assertRaises(ValueError):
            MahnStore(self.bh, self.ks).berechnen(re)                                       # bezahlt

    def test_5_pruefungen(self):
        with self.assertRaises(ValueError):
            self._rechnung(ware={"text": "Zu viel", "wert": "900"})                          # Ware > Summe
        with self.assertRaises(ValueError):
            self._rechnung(ware={"text": "", "wert": "10"})                                  # Ware ohne Text
        re = self._rechnung(ware={})
        self.assertEqual((self.rs.get(re)["ware_cent"], self.rs.get(re)["geld_cent"]), (0, 80000))
        with self.assertRaises(ValueError):
            self.rs.ware_erhalten(re)                                                        # keine Ware vereinbart


class TestBarterApi(ApiBasis):
    def test_a1_ware_erhalten_mit_nachweis(self):
        import base64
        import json
        self.w.kunden_store.bh.dir.joinpath("firmendaten.json").write_text(json.dumps(FD), encoding="utf-8")
        e = self.c.post("/api/finanzen/rechnungen", json={"rechnung": {"firma": self.k, "positionen": POS800,
                                                                       "leistung_von": jetzt().date().isoformat(), "ware": WARE}}).json()
        re = self.c.post(f"/api/finanzen/rechnungen/{e['entwurf_id']}/festschreiben", json={"bestaetigt": True}).json()["nummer"]
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{re}/pdf").status_code, 200)
        r = self.c.post(f"/api/finanzen/rechnungen/{re}/ware-erhalten", json={
            "wert_nachweis": "299", "verwendung": "content", "kategorie": "gwg",
            "nachweise": [{"name": "shop.png", "daten": base64.b64encode(b"\x89PNG fake").decode()}]}).json()
        self.assertTrue(r["ok"], r)
        d = self.c.get(f"/api/finanzen/rechnungen/{re}").json()["rechnung"]
        self.assertEqual(len(d["ware_erhalten"]["nachweise"]), 1)
        self.assertTrue(self.c.post(f"/api/finanzen/rechnungen/{re}/ware-stornieren", json={"grund": "Test"}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
