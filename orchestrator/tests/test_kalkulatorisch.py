"""KUNDEN_FINANZEN Etappe 26: kalkulatorische Kosten (eigene Arbeitszeit, Fahrten) in Uebersicht und Exporten zuschaltbar --
EUeR, Kennzahlen, Journal-Buchungen und index.xml bleiben in allen Varianten unveraendert."""
import io
import zipfile
import unittest

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.finanzen import Finanzen
from orchestrator.core.jahresabschluss import export_zip
from orchestrator.core.zeiterfassung import kalkulatorisch
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_rechnungen import FD
from orchestrator.tests.test_zeiterfassung import _setup

J = jetzt().year


def _mit_zeit():
    bh, ks, k, ab, nr, z = _setup()
    e = z.eintragen(auftrag=nr, datum=jetzt().date().isoformat(), minuten=120)        # 2 h x 29,20 = 58,40
    z.fahrt_erfassen(e["id"], km=40)                                                  # 12,00
    return bh, ks, k, ab, nr, z


class TestKalkulatorisch(unittest.TestCase):
    def test_1_auswertung(self):
        bh, ks, k, ab, nr, z = _mit_zeit()
        kk = kalkulatorisch(bh.eintraege(), J)
        self.assertEqual((kk["zeit_cent"], kk["fahrt_cent"], kk["summe_cent"], kk["minuten"], kk["km"]), (5840, 1200, 7040, 120, 40))
        self.assertEqual([z_["art"] for z_ in kk["zeilen"]], ["Arbeitszeit", "Fahrt"])
        self.assertEqual(kalkulatorisch(bh.eintraege(), J - 1)["summe_cent"], 0)
        andere = {m for m in range(1, 13) if m != jetzt().month}
        self.assertEqual(kalkulatorisch(bh.eintraege(), J, andere)["summe_cent"], 0)    # Zeitraum-Filter

    def test_2_uebersicht_zusatz_eur_gleich(self):
        bh, ks, k, ab, nr, z = _mit_zeit()
        f = Finanzen(bh, ks)
        u = f.uebersicht(J)
        self.assertEqual(u["kalkulatorisch"]["summe_cent"], 7040)
        self.assertEqual(u["kalkulatorisch"]["gewinn_inkl_cent"], u["kennzahlen"]["gewinn_cent"] - 7040)
        bh2, ks2, *_ = _setup()
        leer = Finanzen(bh2, ks2)
        self.assertEqual(f.euer(J), leer.euer(J))                                       # EUeR wie ohne Zeiten
        self.assertEqual(u["kennzahlen"], leer.uebersicht(J)["kennzahlen"])

    def test_3_export_zip(self):
        bh, ks, k, ab, nr, z = _mit_zeit()
        ohne = zipfile.ZipFile(io.BytesIO(export_zip(bh, ks, J, FD)))
        mit = zipfile.ZipFile(io.BytesIO(export_zip(bh, ks, J, FD, kalkulatorisch=True)))
        self.assertNotIn("zusatz/kalkulatorisch.csv", ohne.namelist())
        csv_ = mit.read("zusatz/kalkulatorisch.csv").decode("utf-8-sig")
        self.assertIn("Arbeitszeit", csv_)
        self.assertIn(";58,40;", csv_)
        self.assertIn(";12,00;", csv_)
        self.assertIn("keine Betriebsausgabe", csv_)
        for datei in ("euer.csv", "journal.csv", "index.xml"):
            self.assertEqual(ohne.read(datei), mit.read(datei), datei)                  # amtliche Teile identisch
        self.assertNotIn("kalkulatorisch", mit.read("index.xml").decode("utf-8"))
        self.assertIn("KEINE Betriebsausgaben", mit.read("LIESMICH.txt").decode("utf-8"))


class TestApi(ApiBasis):
    def test_a1_journal_csv(self):
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"})
        self.c.post("/api/finanzen/zeit/eintrag", json={"auftrag": nr, "datum": jetzt().date().isoformat(), "minuten": "60", "arbeit": "dreh"})
        ohne = self.c.get(f"/api/finanzen/journal?jahr={J}&format=csv").text
        mit = self.c.get(f"/api/finanzen/journal?jahr={J}&format=csv&kalkulatorisch=1").text
        self.assertNotIn("Kalkulatorisch", ohne)
        self.assertTrue(mit.startswith(ohne.rstrip("\n").split("\n")[0]))
        self.assertIn("KEINE Betriebsausgaben", mit)
        self.assertIn("29,20", mit)
        u = self.c.get(f"/api/finanzen/uebersicht?jahr={J}").json()
        self.assertEqual(u["kalkulatorisch"]["zeit_cent"], 2920)


if __name__ == "__main__":
    unittest.main()
