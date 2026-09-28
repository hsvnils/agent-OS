"""KUNDEN_FINANZEN Etappe 7: Zahlungen + EUeR-Journal. Gate: ein Probejahr mit Testdaten ergibt nachvollziehbare
EUeR-Summen -- die Erwartungswerte unten sind von Hand gerechnet (Kommentare)."""
import json
import unittest
from datetime import date
from unittest import mock

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eigenbelege import EigenbelegStore, zuordnung_pruefen
from orchestrator.core.eingangsbelege import EingangStore
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_rechnungen import FD, _entwurf

VJ = jetzt().year - 1                        # Probejahr = Vorjahr (alle Daten liegen sicher in der Vergangenheit)


def d(mmtt: str, jahr: int = VJ) -> str:
    return f"{jahr}-{mmtt}"


def _beleg(eb: EingangStore, text: str, betrag: str, kategorie: str, datum: str, **extra) -> str:
    nr = eb.aufnehmen(_pdf(text + " " * 30 + "Beleg"), f"{text}.pdf")["nummer"]
    eb.buchen(nr, {"lieferant": text, "rechnungsdatum": datum, "betrag": betrag, "kategorie": kategorie} | extra)
    return nr


class TestProbejahr(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, _, self.k, self.ap = _stores()
        self.rs, self.eb, self.eig = RechnungStore(self.bh, self.ks), EingangStore(self.bh), EigenbelegStore(self.bh)
        self.f = Finanzen(self.bh, self.ks)

    def _probejahr(self):
        rs, eb, eig = self.rs, self.eb, self.eig
        r1 = rs.festschreiben(_entwurf(rs, self.k, self.ap), FD)["nummer"]                      # 1.020,00
        r2 = rs.festschreiben(_entwurf(rs, self.k, self.ap), FD)["nummer"]                      # 1.020,00
        rs.bezahlt(r1, datum=d("03-10"))                                                       # +1.020,00
        rs.bezahlt(r2, datum=d("11-20"), betrag="500")                                         # +500,00 (Teilzahlung)
        rs.bezahlt(r2, datum=d("11-21"), betrag="100")                                         # +100,00 ...
        rs.zahlung_stornieren(r2, 1, "falsch erfasst")                                         # ... storniert
        eig.anlegen({"art": "einnahme", "datum": d("06-30"), "betrag": "250,50", "text": "YouTube-Auszahlung Juni",
                     "gegenpartei": "Google Ireland"})                                         # +250,50
        e3 = eig.anlegen({"art": "ausgabe", "datum": d("07-01"), "betrag": "99", "kategorie": "werbung",
                          "text": "Falsch gebucht"})["nummer"]
        eig.stornieren(e3, "doppelt")                                                          # zaehlt nicht
        b1 = _beleg(eb, "Druckerei", "119,00", "wareneinkauf", d("02-01"))
        eb.bezahlt(b1, d("02-05"))                                                             # -119,00
        b2 = _beleg(eb, "Restaurant", "100,00", "bewirtung", d("04-01"))
        eb.bezahlt(b2, d("04-01"))                                                             # -70,00 (70 %)
        b3 = _beleg(eb, "Laptop", "1.500,00", "anlage", d("09-15"), nutzungsdauer_jahre=1)
        eb.bezahlt(b3, d("09-15"))                                                             # AfA 1.500,00 (ND 1)
        b4 = _beleg(eb, "Kamera", "1.200,00", "anlage", d("09-10"), nutzungsdauer_jahre=3)
        eb.bezahlt(b4, d("09-12"), betrag="200")                                               # Zahlung wirkt nicht
        # AfA Kamera: Sep-Dez = 4 Monate von 36 -> 1.200 * 4/36 = 133,33
        b5 = _beleg(eb, "Hosting Januar", "12,00", "software", d("12-28"))
        eb.bezahlt(b5, d("12-28"), zuordnung_jahr=VJ + 1)                                      # 10-Tage-Regel -> Folgejahr
        b6 = _beleg(eb, "Mikrofon", "300,00", "gwg", d("05-02"))
        eb.bezahlt(b6, d("05-02"), betrag="100")                                               # -100,00 (Teilzahlung)
        return {"r1": r1, "r2": r2, "b3": b3, "b4": b4, "b5": b5, "b6": b6}

    def test_1_euer_summen_von_hand(self):
        self._probejahr()
        eu = self.f.euer(VJ)
        # Einnahmen: 1.020,00 + 500,00 + 250,50 = 1.770,50
        self.assertEqual(eu["einnahmen_cent"], 177050)
        pos = {p["kategorie"]: p["betrag_cent"] for p in eu["ausgaben"]}
        # Ausgaben: Waren 119,00; Bewirtung 70,00; GWG 100,00; AfA 1.500,00 + 133,33 = 1.633,33
        self.assertEqual(pos, {"wareneinkauf": 11900, "bewirtung": 7000, "gwg": 10000, "anlage": 163333})
        self.assertEqual(eu["ausgaben_cent"], 11900 + 7000 + 10000 + 163333)                  # 1.922,33
        self.assertEqual(eu["gewinn_cent"], 177050 - 192233)                                  # -151,83
        self.assertEqual(eu["bewirtung_nicht_abziehbar_cent"], 3000)
        # Folgejahr: nur das Hosting (10-Tage-Regel) + AfA Kamera 12/36 = 400,00
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(year=VJ + 1, month=12, day=31)):
            eu2 = self.f.euer(VJ + 1)                                                        # Jahresende: volle AfA
        self.assertEqual({p["kategorie"]: p["betrag_cent"] for p in eu2["ausgaben"]}, {"software": 1200, "anlage": 40000})
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(year=VJ + 1, month=9, day=15)):
            eu2 = self.f.euer(VJ + 1)                                                        # laufend: bis September 9/36
        self.assertEqual({p["kategorie"]: p["betrag_cent"] for p in eu2["ausgaben"]}, {"software": 1200, "anlage": 30000})

    def test_2_journal_zeigt_stornos_zaehlt_sie_nicht(self):
        ids = self._probejahr()
        j = self.f.journal(VJ)
        storniert = [z for z in j if z["storniert"]]
        self.assertEqual(sorted(z["bezug"] for z in storniert), sorted([ids["r2"], f"EB-{VJ}-0002"]))
        self.assertTrue(all(z["abziehbar_cent"] == 0 for z in storniert))
        self.assertEqual([z["datum"] for z in j], sorted(z["datum"] for z in j))             # nach Zahlungsdatum
        self.assertNotIn(ids["b5"], {z["bezug"] for z in j})                                 # Hosting im Folgejahr
        from orchestrator.core.finanzen import journal_csv
        csv = journal_csv(j)
        self.assertIn("1020,00", csv)
        self.assertIn("YouTube-Auszahlung Juni", csv)

    def test_3_anlagen_und_uebersicht(self):
        ids = self._probejahr()
        a = {x["beleg"]: x for x in self.f.anlagen(VJ)}
        self.assertEqual((a[ids["b4"]]["afa_jahr_cent"], a[ids["b4"]]["restwert_cent"]), (13333, 106667))
        self.assertEqual(a[ids["b3"]]["restwert_cent"], 0)
        a2 = {x["beleg"]: x for x in self.f.anlagen(VJ + 3)}                                 # Ende ND: Rest 0
        self.assertEqual((a2[ids["b4"]]["afa_bis_cent"], a2[ids["b4"]]["afa_jahr_cent"]), (120000, 26667))
        with mock.patch("orchestrator.core.finanzen.jetzt",
                        return_value=jetzt().replace(year=VJ, month=12, day=31)):
            u = self.f.uebersicht(VJ)
        self.assertEqual(u["kennzahlen"]["einnahmen_cent"], 177050)
        self.assertEqual(u["forderungen"]["summe_cent"], 102000 - 50000)                     # r2 Rest 520,00
        # Verbindlichkeiten: Kamera 1.000,00 + Mikrofon 200,00 (Hosting ist bezahlt)
        self.assertEqual(u["verbindlichkeiten"]["summe_cent"], 100000 + 20000)
        self.assertEqual(u["monate"][2]["einnahmen_cent"], 102000)                           # Maerz
        self.assertEqual(u["monate"][3]["ausgaben_cent"], 7000)                              # April, Bewirtung 70 %
        self.assertEqual(u["kunden"][0]["betrag_cent"], 152000)                              # Brand X: 1.020 + 500
        # Waechter zaehlt Eigenbeleg-Einnahmen mit (Rechnungen tragen das heutige Datum, daher nur 250,50 im VJ)
        self.assertEqual(u["waechter"]["umsatz_cent"], 25050)

    def test_4_regeln(self):
        with self.assertRaises(ValueError):
            _beleg(self.eb, "Teure Kamera", "900,00", "gwg", d("03-01"))                    # > 800 € kein GWG
        with self.assertRaises(ValueError):
            _beleg(self.eb, "Server", "900,00", "anlage", d("03-01"))                       # ND fehlt
        with self.assertRaises(ValueError):
            self.eig.anlegen({"art": "ausgabe", "datum": d("03-01"), "betrag": "10", "kategorie": "anlage", "text": "x y z"})
        with self.assertRaises(ValueError):
            self.eig.anlegen({"art": "einnahme", "datum": d("03-01"), "betrag": "10", "text": ""})   # Text Pflicht
        with self.assertRaises(ValueError):
            self.eig.anlegen({"art": "einnahme", "datum": "2999-01-01", "betrag": "10", "text": "Zukunft"})
        self.assertIsNone(zuordnung_pruefen("2025-12-28", 2025))
        self.assertEqual(zuordnung_pruefen("2025-12-28", 2026), 2026)
        self.assertEqual(zuordnung_pruefen("2026-01-10", 2025), 2025)
        for tag, jahr in (("2025-12-21", 2026), ("2026-01-11", 2025), ("2025-12-28", 2024), ("2025-06-01", 2026)):
            with self.assertRaises(ValueError):
                zuordnung_pruefen(tag, jahr)

    def test_5_zahlungen_grenzen_und_storno(self):
        rs, eb = self.rs, self.eb
        nr = _beleg(eb, "Licht", "50,00", "gwg", d("03-01"))
        with self.assertRaises(ValueError):
            eb.bezahlt(nr, d("03-02"), betrag="60")                                          # mehr als offen
        eb.bezahlt(nr, d("03-02"))
        with self.assertRaises(ValueError):
            eb.bezahlt(nr, d("03-03"))                                                       # schon bezahlt
        eb.zahlung_stornieren(nr, 0, "falsches Konto")
        self.assertEqual((eb.get(nr)["bezahlt_cent"], eb.get(nr)["bezahlt_am"]), (0, ""))
        with self.assertRaises(ValueError):
            eb.zahlung_stornieren(nr, 0, "nochmal")
        r = rs.festschreiben(_entwurf(rs, self.k, self.ap), FD)["nummer"]
        rs.bezahlt(r, datum=d("05-01"))
        self.assertEqual(rs.get(r)["status"], "bezahlt")
        rs.zahlung_stornieren(r, 0, "Ruecklastschrift")
        self.assertEqual((rs.get(r)["status"], rs.get(r)["bezahlt_cent"]), ("offen", 0))
        rs.stornieren(r, FD, grund="nach Storno der Zahlung moeglich")                      # keine Zahlung mehr

    def test_6_altbestand_zahlung_ohne_betrag(self):
        nr = _beleg(self.eb, "Alt", "51,92", "gwg", d("09-22"))
        self.bh.erfassen("eingang_bezahlt", {"nummer": nr, "datum": d("09-22")})             # Format vor Etappe 7
        x = self.eb.get(nr)
        self.assertEqual((x["bezahlt_cent"], x["bezahlt_am"]), (5192, d("09-22")))
        self.assertEqual(self.f.euer(VJ)["ausgaben_cent"], 5192)

    def test_7_gutschrift_facebook_ist_einnahme(self):
        from orchestrator.core.eingangsbelege import vorschlag_llm, vorschlag_regeln
        text = ("Meta Platforms Ireland Limited\nGutschrift (Selbstfakturierung)\nFacebook-Monetarisierung August\n"
                "Belegnummer: FB-2025-0815\nBelegdatum: 05.09.2025\nGesamtbetrag 312,40 EUR")
        v = vorschlag_regeln(text)
        self.assertEqual((v["art"], v["kategorie"], v["betrag"]), ("einnahme", "umsatz", "312,40"))
        self.assertEqual(vorschlag_regeln("Druckerei Nord\nRechnung\nGesamt 10,00 EUR")["art"], "ausgabe")
        self.assertEqual(vorschlag_llm('{"art": "einnahme", "kategorie": "werbung", "betrag": "5"}')["kategorie"], "umsatz")
        self.assertEqual(vorschlag_llm('{"art": "quatsch", "kategorie": "werbung"}')["art"], "ausgabe")
        meta = ("Meta Platforms Ireland Ltd.\nREMITTANCE\nPayee: Nils Krüger\nPayment Number: 29163590826663755\n"
                "Payment Date: 25-Sep-2026\nPayment Currency: USD\nPayment Amount: 282.37\nTotal: $282.37")
        m = vorschlag_regeln(meta)                                                      # echtes Zahlungsavis (gekuerzt)
        self.assertEqual((m["art"], m["rechnungsnummer"], m["rechnungsdatum"], m["betrag"], m["waehrung"], m["betrag_fremd"]),
                         ("einnahme", "29163590826663755", "2026-09-25", "", "USD", "282,37"))
        self.assertEqual(vorschlag_llm('{"art": "einnahme", "waehrung": "USD", "betrag": "282,37"}')["betrag"], "")
        nr = _beleg(self.eb, "Meta Platforms Ireland", "312,40", "umsatz", d("09-05"), art="einnahme")
        with self.assertRaises(ValueError):                                                  # Einnahme ist kein GWG
            self.eb.buchen(nr, {"lieferant": "Meta", "rechnungsdatum": d("09-05"), "betrag": "1", "kategorie": "gwg",
                                "art": "einnahme"})
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(year=VJ, month=12, day=31)):
            u = self.f.uebersicht(VJ)
        self.assertEqual((u["forderungen"]["summe_cent"], u["verbindlichkeiten"]["summe_cent"]), (31240, 0))
        self.assertEqual(u["forderungen"]["liste"][0]["act"], "bl-detail")
        self.assertEqual(self.rs.umsatz(VJ, eintraege=self.bh.eintraege()), 31240)          # KU-Grenze zaehlt mit
        self.eb.bezahlt(nr, d("09-20"))                                                      # Geldeingang
        eu = self.f.euer(VJ)
        self.assertEqual((eu["einnahmen_cent"], eu["ausgaben_cent"]), (31240, 0))
        z = self.f.journal(VJ)[0]
        self.assertEqual((z["art"], z["gegenpartei"], z["position"][:17]), ("einnahme", "Meta Platforms Ireland", "Betriebseinnahmen"))

    def test_8_cockpit_zeitraeume_und_drilldown_stimmen(self):
        """Etappe 8, Gate „Zahlen gegen Rohdaten“: jede Kennzahl = Summe ihrer Posten; Monate/Quartale = Jahr."""
        from orchestrator.core.finanzen import kennzahlen
        self._probejahr()
        eu = self.f.euer(VJ)
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(year=VJ, month=12, day=31)):
            u = self.f.uebersicht(VJ)
            q3 = self.f.uebersicht(VJ, "q3")
            m09 = self.f.uebersicht(VJ, "m09")
        jahr = u["kennzahlen"]
        self.assertEqual((jahr["einnahmen_cent"], jahr["ausgaben_cent"]), (eu["einnahmen_cent"], eu["ausgaben_cent"]))
        self.assertEqual(sum(m["ausgaben_cent"] for m in u["monate"]), eu["ausgaben_cent"])      # AfA monatlich, Summe = Jahr
        self.assertEqual(sum(q["gewinn_cent"] for q in u["quartale"]), eu["gewinn_cent"])
        for zr, ueb in (("jahr", u), ("q3", q3), ("m09", m09)):
            self.assertEqual(kennzahlen(self.f.posten(VJ, zr)), ueb["kennzahlen"], zr)
        # September: Laptop ND 1 (voll im Monat) + Kamera 1.200/36 (Sep) = 1.500,00 + 33,33
        self.assertEqual(m09["kennzahlen"]["ausgaben_cent"], 150000 + 3333)
        self.assertEqual(sum(z["abziehbar_cent"] for z in self.f.posten(VJ, art="ausgabe", kategorie="anlage")), 163333)
        kunde = self.f.posten(VJ, art="einnahme", gegenpartei="google ireland")
        self.assertEqual([z["betrag_cent"] for z in kunde], [25050])
        with self.assertRaises(ValueError):
            self.f.posten(VJ, "q5")
        # laufendes Jahr: Abschreibung nur bis zum aktuellen Monat (keine Vorwegnahme kuenftiger Monate)
        with mock.patch("orchestrator.core.finanzen.jetzt", return_value=jetzt().replace(year=VJ, month=10, day=15)):
            afa = [z["monat"] for z in self.f.posten(VJ, kategorie="anlage") if z["quelle"] == "afa"]
        self.assertEqual(max(afa), 10)

    def test_9_ki_kosten_jahr(self):
        import tempfile
        from pathlib import Path
        from orchestrator.core.kosten import KostenStore
        ks = KostenStore(Path(tempfile.mkdtemp()) / "k.jsonl")
        for ts, eur in (("2026-01-05T10:00:00", 1.5), ("2026-01-20T10:00:00", 0.25), ("2026-09-01T10:00:00", 2.0),
                        ("2025-12-31T23:00:00", 9.0)):
            ks._append({"ts": ts, "quelle": "chat", "modell": "x", "provider": "gemini" if eur < 2 else "anthropic",
                        "in": 1, "out": 1, "eur": eur})
        j = ks.jahr(2026)
        self.assertEqual((j["monate_eur"][0], j["monate_eur"][8], j["gesamt_eur"]), (1.75, 2.0, 3.75))
        self.assertEqual(list(j["je_provider"]), ["anthropic", "gemini"])


class TestFinanzenApi(ApiBasis):
    def test_a1_ablauf(self):
        r = self.c.post("/api/finanzen/eigenbelege", json={"buchung": {
            "art": "einnahme", "datum": date.today().isoformat(), "betrag": "80", "text": "Instagram-Bonus"}}).json()
        self.assertTrue(r["ok"], r)
        u = self.c.get("/api/finanzen/uebersicht").json()
        self.assertEqual(u["kennzahlen"]["einnahmen_cent"], 8000)
        j = self.c.get("/api/finanzen/journal").json()
        self.assertEqual(j["zeilen"][0]["bezug"], r["nummer"])
        csv = self.c.get("/api/finanzen/journal?format=csv")
        self.assertIn("text/csv", csv.headers["content-type"])
        self.assertIn("Instagram-Bonus", csv.text)
        self.assertFalse(self.c.post(f"/api/finanzen/eigenbelege/{r['nummer']}/stornieren", json={}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/finanzen/eigenbelege/{r['nummer']}/stornieren",
                                    json={"grund": "Test"}).json()["ok"])
        self.assertEqual(self.c.get("/api/finanzen/euer").json()["einnahmen_cent"], 0)
        self.assertIn("ausgabe", self.c.get("/api/finanzen/eigenbelege").json()["kategorien"])
        p = self.c.get("/api/finanzen/posten?zeitraum=jahr&art=einnahme").json()
        self.assertEqual(p["kennzahlen"]["einnahmen_cent"], 0)                               # storniert zaehlt nicht
        self.assertEqual(self.c.get("/api/finanzen/posten?zeitraum=q9").status_code, 400)
        self.assertEqual(self.c.get("/api/finanzen/uebersicht?zeitraum=m13").status_code, 400)
        self.assertIn("budget", self.c.get("/api/finanzen/ki-kosten").json())
        self.assertFalse(self.c.post("/api/finanzen/belege/ER-1999-0001/zahlung-stornieren",
                                     json={"index": "x", "grund": "g"}).json()["ok"])

    def test_a2_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/finanzen/uebersicht"), "finanzen")
        self.assertIn("finanzen", erlaubte_apps({"role": "owner", "allowed_modules": []}))
        self.assertNotIn("finanzen", erlaubte_apps({"role": "admin", "allowed_modules": ["crm", "administration"]}))


if __name__ == "__main__":
    unittest.main()
