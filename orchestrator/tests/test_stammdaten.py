"""KUNDEN_FINANZEN Etappe 14 (CEO 2026-09-29): Lieferanten/Dienstleister `L-`, Partner `P-`, Kunden `K-`; Adresse,
USt-ID, unsere Kundennummer, Vertraege, Zahlungsweg; jeder Beleg haengt an einer Stammdaten-Nummer."""
import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from orchestrator.core.buchhaltung import Buchhaltung, jetzt
from orchestrator.core.eigenbelege import EigenbelegStore
from orchestrator.core.eingangsbelege import EingangStore
from orchestrator.core.kunden import KundenStore
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import TEXT, _pdf


def _ks():
    return KundenStore(Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung"))


def _monat(n: int) -> str:
    """Erster Tag des Monats vor n Monaten (ISO)."""
    h = jetzt().date()
    j, m = h.year, h.month - n
    while m <= 0:
        j, m = j - 1, m + 12
    return date(j, m, 1).isoformat()


class TestNummernkreise(unittest.TestCase):
    def test_1_je_rolle_eigener_kreis(self):
        ks = _ks()
        nr = [ks.firma_anlegen({"name": n, "typ": t})["nummer"] for n, t in
              (("Kunde A", "kunde"), ("Calumet", "lieferant"), ("Meta", "partner"), ("Anthropic", "lieferant"))]
        self.assertEqual(nr, ["K-00001", "L-00001", "P-00001", "L-00002"])
        self.assertEqual(ks.firma("L-00002")["anzeige"], "L-00002")

    def test_2_alte_k_nummer_bekommt_l_nummer(self):
        """Live-Fall: Lieferanten wurden bis 2026-09-29 als K-00003 ... angelegt."""
        ks = _ks()
        k = ks.firma_anlegen({"name": "Calumet Photo Video GmbH"})["nummer"]
        ks.firma_aendern(k, {"typ": "lieferant"})
        self.assertEqual(ks.firma(k)["anzeige"], k)                                 # noch keine L-Nummer
        l = ks.rollennummer_sichern(k)
        self.assertEqual(l, "L-00001")
        self.assertEqual(ks.rollennummer_sichern("L-00001"), "L-00001")             # idempotent, auch ueber die L-Nr.
        f = ks.firma("l-00001")
        self.assertEqual((f["nummer"], f["anzeige"], f["nummern"]), (k, "L-00001", [k, "L-00001"]))
        ks.firma_aendern("L-00001", {"ort": "Hamburg"})                             # Aendern ueber die neue Nummer
        self.assertEqual(ks.firma(k)["ort"], "Hamburg")
        self.assertEqual(len([e for e in ks.bh.eintraege() if e["typ"] == "firma_nummer_ergaenzt"]), 1)
        self.assertEqual(ks.bh.pruefe_kette(), [])

    def test_3_felder_vertraege_luecken(self):
        ks = _ks()
        nr = ks.firma_anlegen({"name": "Apple Distribution International Ltd.", "typ": "lieferant",
                               "kundennummer_bei": "hsvnils@icloud.com", "zahlungsweg": "Mastercard •••• 1364",
                               "vertraege": [{"bezeichnung": "AppleCare+ iPhone 17 Pro", "nummer": "970366625006251"},
                                             {"bezeichnung": "", "nummer": ""}, "kaputt"]})["nummer"]
        f = ks.firma(nr)
        self.assertEqual(f["vertraege"], [{"bezeichnung": "AppleCare+ iPhone 17 Pro", "nummer": "970366625006251",
                                           "notiz": ""}])
        self.assertEqual(f["luecken"], ["Adresse", "Land", "USt-IdNr./Steuernummer"])
        ks.firma_aendern(nr, {"strasse": "Hollyhill Industrial Estate", "ort": "Cork", "land": "Irland",
                              "ustid": "IE9700053D"})                                 # Ausland: ohne PLZ vollstaendig
        self.assertEqual(ks.firma(nr)["luecken"], [])
        self.assertEqual([x["nummer"] for x in ks.firmen(suche="970366625006251")], [nr])   # Suche ueber Vertragsnr.
        with self.assertRaises(ValueError):
            ks.firma_aendern(nr, {"vertraege": "keine Liste"})

    def test_4_finden_und_zuordnen(self):
        ks = _ks()
        apple = ks.firma_anlegen({"name": "Apple Distribution International", "typ": "lieferant"})["nummer"]
        ks.firma_anlegen({"name": "Amazon.de", "typ": "lieferant"})
        self.assertEqual(ks.finde("Apple"), apple)                                  # erstes Namenswort
        self.assertEqual(ks.finde("apple distribution international"), apple)
        self.assertEqual(ks.finde("Appleton Studios"), "")
        nr = ks.zuordnen("Apple", absender="no_reply@email.apple.com")
        self.assertEqual(nr, apple)
        self.assertIn("no_reply@email.apple.com", ks.firma(apple)["rechnungs_absender"])   # gelernt
        self.assertEqual(ks.finde("Irgendwas", "no_reply@email.apple.com"), apple)          # Absender schlaegt Namen
        ks.firma_aendern(apple, {"rechnungs_absender": "apple.com"})
        self.assertEqual(ks.finde("", "your_order@orders.apple.com"), apple)               # Domain inkl. Subdomain
        ms = ks.zuordnen("Microsoft Payments", absender="service@paypal.de")        # PayPal-Beleg
        self.assertNotIn("paypal", ks.firma(ms)["rechnungs_absender"] or "")      # Zahlungsdienst nie lernen
        self.assertEqual(ks.zuordnen("DAZN DACH GmbH", absender="service@paypal.de") == ms, False)
        meta = ks.zuordnen("Meta Platforms Ireland Ltd.", art="einnahme")
        self.assertEqual(ks.firma(meta)["anzeige"], "P-00001")                           # Einnahme -> Partner
        with self.assertRaises(ValueError):
            ks.zuordnen("")


class TestStammdatenApi(ApiBasis):
    def _beleg(self, text=TEXT, name="r.pdf", **felder):
        st = EingangStore(self.w.kunden_store.bh)
        nr = st.aufnehmen(_pdf(text), name)["nummer"]
        return st, nr

    def test_a_buchen_immer_mit_nummer(self):
        ks = self.w.kunden_store
        alt = ks.firma_anlegen({"name": "Druckerei Nord GmbH", "typ": "lieferant"})["nummer"]   # L-00001
        st, nr = self._beleg()
        d = self.c.get(f"/api/finanzen/belege/{nr}").json()
        self.assertEqual(d["firma_vorschlag"]["anzeige"], "L-00001")
        self.assertIn("L-00001", [x["anzeige"] for x in d["lieferanten"]])
        felder = {"lieferant": "Druckerei Nord GmbH", "rechnungsdatum": "2026-09-12", "betrag": "1.190,00",
                  "kategorie": "werbung"}
        self.assertFalse(self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": felder | {"lieferant": ""}}).json()["ok"])
        r = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": felder | {"lieferant_firma": "L-00001"}}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(st.get(nr)["felder"]["lieferant_firma"], alt)
        st2, nr2 = self._beleg(TEXT.replace("Druckerei Nord", "Neuer Laden"), "n.pdf")
        r = self.c.post(f"/api/finanzen/belege/{nr2}/buchen", json={"felder": felder | {"lieferant": "Neuer Laden GmbH"}}).json()
        self.assertTrue(r["ok"], r)
        neu = ks.firma(st2.get(nr2)["felder"]["lieferant_firma"])
        self.assertEqual((neu["name"], neu["typ"], neu["anzeige"]), ("Neuer Laden GmbH", "lieferant", "L-00002"))
        self.assertFalse(self.c.post(f"/api/finanzen/belege/{nr2}/buchen",
                                     json={"felder": felder | {"lieferant_firma": "L-09999"}}).json()["ok"])
        j = self.c.get("/api/finanzen/journal?jahr=2026&firma=L-00001").json()["zeilen"]
        self.assertEqual(j, [])                                                     # noch nicht bezahlt
        st.bezahlt(nr, "2026-09-20")
        st2.bezahlt(nr2, "2026-09-21")                                             # andere Firma: darf nicht erscheinen
        j = self.c.get("/api/finanzen/journal?jahr=2026&firma=L-00001").json()["zeilen"]
        self.assertEqual([(z["bezug"], z["firma_nr"]) for z in j], [(nr, "L-00001")])
        csv = self.c.get("/api/finanzen/journal?jahr=2026&format=csv").text
        self.assertIn(";Nr.;Gegenpartei;", csv)
        self.assertIn(";L-00001;Druckerei Nord GmbH;", csv)

    def test_b_eigenbeleg_und_nachzuordnung(self):
        ks = self.w.kunden_store
        bh = ks.bh
        alt = ks.firma_anlegen({"name": "Calumet Photo Video GmbH", "typ": "kunde"})["nummer"]
        ks.firma_aendern(alt, {"typ": "lieferant"})                                 # wie live: K-Nummer, Lieferant
        st, nr = self._beleg(TEXT.replace("Druckerei Nord GmbH", "Calumet Photo Video GmbH"))
        st.buchen(nr, {"lieferant": "Calumet Photo Video GmbH", "rechnungsdatum": "2026-09-12", "betrag": "51,92",
                       "kategorie": "gwg"})                                         # Altbeleg ohne Nummer
        eb = EigenbelegStore(bh)
        e1 = eb.anlegen({"art": "ausgabe", "datum": "2026-06-01", "betrag": "96,09", "kategorie": "fremdleistungen",
                         "text": "Logo-Design", "gegenpartei": "Fiverr"})["nummer"]
        e2 = eb.anlegen({"art": "ausgabe", "datum": "2026-06-02", "betrag": "5", "kategorie": "buero",
                         "text": "Porto bar"})["nummer"]
        p = self.c.post("/api/finanzen/stammdaten/zuordnen", json={"probe": True}).json()
        self.assertTrue(p["ok"], p)
        self.assertEqual([(x["beleg"], x["firma"]) for x in p["plan"]], [(nr, alt), (e1, "")])
        self.assertEqual((p["ohne_gegenpartei"], p["rollennummern_fuer"]), ([e2], [alt]))
        self.assertEqual(st.get(nr)["felder"].get("lieferant_firma"), "")           # Probe schreibt nichts
        r = self.c.post("/api/finanzen/stammdaten/zuordnen", json={}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["zugeordnet"], [{"beleg": nr, "firma": "L-00001"}, {"beleg": e1, "firma": "L-00002"}])
        self.assertEqual(st.get(nr)["felder"]["lieferant_firma"], alt)
        self.assertEqual(eb.get(e1)["firma"], ks.finde("Fiverr"))
        p = self.c.post("/api/finanzen/stammdaten/zuordnen", json={"probe": True}).json()
        self.assertEqual((p["plan"], p["rollennummern_fuer"]), ([], []))              # nichts mehr zu tun
        # neuer Eigenbeleg ueber eine gewaehlte Nummer
        r = self.c.post("/api/finanzen/eigenbelege", json={"buchung": {
            "art": "ausgabe", "datum": "2026-07-01", "betrag": "10", "kategorie": "gwg", "text": "Filter",
            "firma": "L-00001"}}).json()
        self.assertTrue(r["ok"], r)
        x = eb.get(r["nummer"])
        self.assertEqual((x["firma"], x["gegenpartei"]), (alt, "Calumet Photo Video GmbH"))

    def test_c_detail_abo_export_cfo(self):
        from orchestrator.core import jahresabschluss as ja
        from orchestrator.core.todos import finanzcheck
        ks = self.w.kunden_store
        st = EingangStore(ks.bh)
        belege = []
        for i, (monat, betrag, name) in enumerate(((_monat(2), "14,99", "Apple"),          # zwei Schreibweisen,
                                                   (_monat(1), "15,49", "Apple Distribution International"))):   # eine Nr.
            nr = st.aufnehmen(_pdf(f"Apple {i} " * 10), f"a{i}.pdf")["nummer"]
            r = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"felder": {
                "lieferant": name, "rechnungsdatum": monat, "betrag": betrag, "kategorie": "software"}}).json()
            self.assertTrue(r["ok"], r)
            st.bezahlt(nr, monat)
            belege.append(nr)
        firmen = [f for f in ks.firmen() if f["typ"] == "lieferant"]
        self.assertEqual(len(firmen), 1)                                            # „Apple Distribution …“ = Apple
        d = self.c.get(f"/api/crm/kunden/{firmen[0]['anzeige']}").json()
        bu = d["buchungen"]
        self.assertEqual(sorted(b["nummer"] for b in bu["belege"]), belege)
        self.assertEqual(sum(x["ausgaben_cent"] for x in bu["je_jahr"].values()), 1499 + 1549)
        self.assertEqual(bu["abo"]["monatlich_cent"], 1549)
        self.assertEqual(len(bu["abo"]["monate"]), 2)
        # CFO: wiederkehrend je Stammdaten-Nummer (verschiedene Schreibweisen zaehlen zusammen)
        heute = date.fromisoformat(_monat(0)).replace(day=15)
        hinweise = [t for t in finanzcheck(ks.bh.eintraege(), heute) if "fehlt?" in t.get("titel", "")]
        self.assertEqual(len(hinweise), 1)
        self.assertIn("Apple", hinweise[0]["titel"])
        # Export: Nummern-Spalten
        jahr = int(_monat(1)[:4])
        z = zipfile.ZipFile(io.BytesIO(ja.export_zip(ks.bh, ks, jahr, {"firma": "Test", "inhaber": "Nils"})))
        kunden = z.read("kunden.csv").decode("utf-8-sig")
        self.assertIn("Rollennummer", kunden.splitlines()[0])
        self.assertIn(firmen[0]["anzeige"], z.read("eingangsbelege.csv").decode("utf-8-sig"))
        self.assertIn("Partner_Nr", z.read("journal.csv").decode("utf-8-sig").splitlines()[0])
        self.assertIn("Lieferant_Nr", z.read("index.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
