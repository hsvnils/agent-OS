"""KUNDEN_FINANZEN Etappe 5: Ausgangsrechnungen -- Entwurf ohne Nummer, Festschreiben atomar + unveraenderlich,
Storno mit Gegenbeleg, Nummern lueckenlos, Pflichtangaben, Kleinunternehmer-Waechter, Zahlung, Faelligkeit."""
import json
import threading
import unittest
from datetime import timedelta
from unittest import mock

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import Buchhaltung, jetzt
from orchestrator.core.rechnungen import RechnungStore, ueberfaellige
from orchestrator.tests.test_angebote import FIRMA, POS, ApiBasis, _stores

FD = FIRMA | {"steuernummer": "30/000/00000"}


def _rs():
    bh, ks, st, k, ap = _stores()
    return bh, ks, RechnungStore(bh, ks), k, ap


def _entwurf(rs, k, ap, **extra):
    return rs.entwurf_anlegen({"firma": k, "ansprechpartner": ap, "positionen": POS,
                               "leistung_von": jetzt().date().isoformat()} | extra)["entwurf_id"]


class TestRechnungen(unittest.TestCase):
    def test_1_entwurf_ohne_nummer_festschreiben_mit_nummer(self):
        bh, ks, rs, k, ap = _rs()
        eid = _entwurf(rs, k, ap)
        self.assertEqual([e["daten"]["kreis"] for e in bh.eintraege("nummer")], ["K", "AP"])   # Entwurf: keine RE-Nummer
        self.assertEqual(rs.entwurf_aendern(eid, {"titel": "Herbst"})["geaendert"], ["titel"])
        r = rs.festschreiben(eid, FD, von="LUNA-OS:ceo")
        self.assertEqual(r["nummer"], f"RE-{jetzt().year}-0001")
        x = rs.get(r["nummer"])
        self.assertEqual((x["status"], x["summe_cent"], x["titel"]), ("offen", 102000, "Herbst"))
        self.assertEqual(x["faellig_am"], (jetzt().date() + timedelta(days=14)).isoformat())
        beleg = bh.eintraege("beleg")[-1]["daten"]
        self.assertEqual((beleg["art"], beleg["bezug"], beleg["aufbewahren_bis"][:4]), ("beleg", r["nummer"], str(jetzt().year + 8)))
        self.assertTrue((bh.dir / x["belege"][0]["pfad"]).read_bytes().startswith(b"%PDF"))
        self.assertIsNone(rs.get(eid))                                                  # Entwurf ist weg
        self.assertEqual((bh.pruefe_kette(), bh.pruefe_belege()), ([], []))

    def test_2_festgeschrieben_ist_unveraenderlich(self):
        bh, ks, rs, k, ap = _rs()
        eid = _entwurf(rs, k, ap)
        nr = rs.festschreiben(eid, FD)["nummer"]
        with self.assertRaises(KeyError):
            rs.entwurf_aendern(eid, {"titel": "zu spaet"})                              # Entwurf existiert nicht mehr
        with self.assertRaises(KeyError):
            rs.festschreiben(eid, FD)                                                   # nicht doppelt festschreibbar
        self.assertEqual(len([e for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "RE"]), 1)
        self.assertEqual(rs.get(nr)["status"], "offen")

    def test_3_pflichtangaben_und_nichts_verbraucht(self):
        bh, ks, rs, k, ap = _rs()
        eid = _entwurf(rs, k, ap, leistung_von="")
        with self.assertRaises(ValueError):
            rs.festschreiben(eid, FIRMA)                                                # ohne Steuernummer
        with self.assertRaises(ValueError):
            rs.festschreiben(eid, FD)                                                   # ohne Leistungsdatum
        self.assertEqual([e for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "RE"], [])
        self.assertEqual(bh.eintraege("beleg"), [])                                     # kein verwaistes PDF
        rs.entwurf_aendern(eid, {"leistung_von": "2026-09-01", "leistung_bis": "2026-09-30"})
        self.assertTrue(rs.festschreiben(eid, FD)["nummer"].endswith("-0001"))          # erste Nummer, lueckenlos

    def test_4_storno_mit_gegenbeleg_und_korrektur(self):
        bh, ks, rs, k, ap = _rs()
        nr = rs.festschreiben(_entwurf(rs, k, ap), FD)["nummer"]
        with self.assertRaises(ValueError):
            rs.stornieren(nr, FD)                                                       # Grund ist Pflicht
        r = rs.stornieren(nr, FD, grund="Falscher Betrag", korrektur=True)
        o, s = rs.get(nr), rs.get(r["storno"])
        self.assertEqual((o["status"], o["storniert_durch"]), ("storniert", r["storno"]))
        self.assertEqual((s["art"], s["bezug"], s["summe_cent"]), ("storno", nr, -102000))
        self.assertEqual(rs.umsatz(jetzt().year), 0)                                    # Storno hebt auf
        self.assertEqual(rs.get(r["korrektur_entwurf"])["summe_cent"], 102000)
        with self.assertRaises(ValueError):
            rs.stornieren(nr, FD, grund="nochmal")
        with self.assertRaises(ValueError):
            rs.stornieren(r["storno"], FD, grund="Storno vom Storno")
        self.assertEqual([e["daten"]["nummer"] for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "RE"],
                         [f"RE-{jetzt().year}-0001", f"RE-{jetzt().year}-0002"])

    def test_5_kleinunternehmer_waechter(self):
        bh, ks, rs, k, ap = _rs()
        gross = [{"beschreibung": "Saison", "menge": "1", "einzelpreis": "85.000"}]
        nr = rs.festschreiben(_entwurf(rs, k, ap, positionen=gross), FD)
        self.assertTrue(nr["warnung"])                                                   # 85 % -> Warnung
        eid = _entwurf(rs, k, ap, positionen=[{"beschreibung": "x", "menge": "1", "einzelpreis": "15.000,01"}])
        with self.assertRaises(ValueError) as cm:
            rs.festschreiben(eid, FD)
        self.assertIn("100.000", str(cm.exception))
        self.assertEqual(len([e for e in bh.eintraege("nummer") if e["daten"]["kreis"] == "RE"]), 1)
        rs.entwurf_aendern(eid, {"positionen": [{"beschreibung": "x", "menge": "1", "einzelpreis": "15.000"}]})
        self.assertTrue(rs.festschreiben(eid, FD)["nummer"])                             # genau 100.000 -> erlaubt

    def test_6_vorjahr_ueber_25000_blockiert(self):
        bh, ks, rs, k, ap = _rs()
        nr = rs.festschreiben(_entwurf(rs, k, ap, positionen=[{"beschreibung": "x", "menge": "1", "einzelpreis": "30.000"}]), FD)
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() + timedelta(days=370)):
            with self.assertRaises(ValueError) as cm:
                rs.festschreiben(_entwurf(rs, k, ap), FD)
        self.assertIn("Vorjahr", str(cm.exception))

    def test_7_zahlung_und_ueberfaellig(self):
        bh, ks, rs, k, ap = _rs()
        nr = rs.festschreiben(_entwurf(rs, k, ap, zahlungsziel_tage=0), FD)["nummer"]
        with mock.patch("orchestrator.core.rechnungen.jetzt", return_value=jetzt() + timedelta(days=1)):
            self.assertEqual([r["nummer"] for r in ueberfaellige(rs)], [nr])
        with self.assertRaises(ValueError):
            rs.bezahlt(nr, datum=(jetzt().date() + timedelta(days=3)).isoformat())    # Zukunft
        self.assertEqual(rs.bezahlt(nr, datum=jetzt().date().isoformat(), betrag="500")["rest_cent"], 52000)
        self.assertEqual(rs.get(nr)["status"], "offen")
        with self.assertRaises(ValueError):
            rs.bezahlt(nr, datum="", betrag="600")                                      # mehr als der Rest
        rs.bezahlt(nr, datum="")                                                        # Rest
        self.assertEqual((rs.get(nr)["status"], rs.get(nr)["bezahlt_cent"]), ("bezahlt", 102000))
        with self.assertRaises(ValueError):
            rs.stornieren(nr, FD, grund="x")                                            # bezahlt -> nicht stornieren
        self.assertEqual(ueberfaellige(rs), [])

    def test_8_parallel_lueckenlos(self):
        bh, ks, rs, k, ap = _rs()
        eids = [_entwurf(rs, k, ap) for _ in range(12)]
        nummern, fehler = [], []

        def arbeite(e):
            try:
                nummern.append(RechnungStore(Buchhaltung(bh.dir), ks).festschreiben(e, FD)["nummer"])
            except Exception as exc:                                                    # pragma: no cover
                fehler.append(exc)
        ts = [threading.Thread(target=arbeite, args=(e,)) for e in eids]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=60)
        self.assertEqual(fehler, [])
        self.assertEqual(sorted(nummern), [f"RE-{jetzt().year}-{i:04d}" for i in range(1, 13)])
        self.assertEqual(len(bh.eintraege("beleg")), 12)
        self.assertEqual((bh.pruefe_kette(), bh.pruefe_belege()), ([], []))

    def test_9_aus_auftrag(self):
        bh, ks, st, k, ap = _stores()
        an = st.anlegen({"firma": k, "positionen": POS, "zuschlaege": [{"name": "R", "prozent": 25}]})["nummer"]
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        ab = AuftragBuch(bh, ks, st)
        abnr = ab.aus_angebot(an, leistung_von="2026-10-01")["nummer"]
        rs = RechnungStore(bh, ks)
        e = rs.entwurf_aus_auftrag(ab.auftrag(abnr))["entwurf_id"]
        self.assertTrue(rs.entwurf_aus_auftrag(ab.auftrag(abnr))["vorhanden"])        # derselbe Entwurf
        x = rs.get(e)
        self.assertEqual((x["auftrag"], x["angebot"], x["summe_cent"], x["leistung_von"]), (abnr, an, 127500, "2026-10-01"))
        nr = rs.festschreiben(e, FD)["nummer"]
        with self.assertRaises(ValueError):
            rs.entwurf_aus_auftrag(ab.auftrag(abnr))                                    # schon abgerechnet
        rs.stornieren(nr, FD, grund="Test")
        self.assertTrue(rs.entwurf_aus_auftrag(ab.auftrag(abnr))["entwurf_id"])         # nach Storno wieder moeglich


class TestRechnungApi(ApiBasis):
    def setUp(self):
        super().setUp()
        fd = self.w.kunden_store.bh.dir / "firmendaten.json"
        fd.write_text(json.dumps(FD), encoding="utf-8")

    def _neu(self):
        r = self.c.post("/api/finanzen/rechnungen", json={"rechnung": {"firma": self.k, "ansprechpartner": self.ap,
                                                                       "positionen": POS, "leistung_von": "2026-09-01"}}).json()
        self.assertTrue(r["ok"], r)
        return r["entwurf_id"]

    def test_r1_ablauf(self):
        eid = self._neu()
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{eid}/pdf").status_code, 200)       # Vorschau
        self.assertFalse(self.c.post(f"/api/finanzen/rechnungen/{eid}/festschreiben", json={}).json()["ok"])
        r = self.c.post(f"/api/finanzen/rechnungen/{eid}/festschreiben", json={"bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        nr = r["nummer"]
        self.assertEqual(len(self.g.termine), 1)                                      # Faelligkeits-Erinnerung
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{nr}/pdf").status_code, 200)
        v = self.c.get(f"/api/finanzen/rechnungen/{nr}/versandvorschau").json()
        s = self.c.post(f"/api/finanzen/rechnungen/{nr}/senden", json={"an": "p@example.com", "betreff": v["betreff"],
                                                                        "text": v["text"], "bestaetigt": True}).json()
        self.assertTrue(s["ok"], s)
        self.assertEqual(self.g.gesendet[-1]["anhaenge"][0][0], f"Rechnung_{nr}.pdf")
        self.assertTrue(self.c.post(f"/api/finanzen/rechnungen/{nr}/bezahlt", json={"datum": ""}).json()["ok"])
        u = self.c.get("/api/finanzen/rechnungen").json()
        self.assertEqual((u["rechnungen"][0]["status"], u["waechter"]["umsatz_cent"]), ("bezahlt", 102000))

    def test_r2_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/finanzen/rechnungen"), "finanzen")
        self.assertIn("rechnungen", erlaubte_apps({"role": "owner", "allowed_modules": []}))
        self.assertNotIn("rechnungen", erlaubte_apps({"role": "admin", "allowed_modules": ["crm", "administration"]}))


if __name__ == "__main__":
    unittest.main()
