"""KUNDEN_FINANZEN Etappe 9: Jahresabschluss -- Pruefung, EUeR je Zeile, Export (Gate: vollstaendig, Stichprobe)."""
import csv
import io
import json
import zipfile
from unittest import mock
from xml.dom import minidom

from orchestrator.core import jahresabschluss as ja
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.todos import QUITTUNG
from orchestrator.tests.test_angebote import ApiBasis
import unittest

from orchestrator.tests.test_finanzen import VJ, ProbejahrBasis
from orchestrator.tests.test_rechnungen import FD


class TestJahresabschluss(ProbejahrBasis, unittest.TestCase):
    def _zip(self):
        return zipfile.ZipFile(io.BytesIO(ja.export_zip(self.bh, self.ks, VJ, FD | {"inhaber": "Nils"})))

    def test_j1_export_vollstaendig(self):
        self._probejahr()
        z = self._zip()
        namen = set(z.namelist())
        for n in ("journal.csv", "euer.csv", "anlagen.csv", "ausgangsrechnungen.csv", "eingangsbelege.csv",
                  "eigenbelege.csv", "kunden.csv", "index.xml", "kassenbuch/log.jsonl", "kassenbuch/pruefung.txt",
                  f"EUER_{VJ}.pdf", "LIESMICH.txt"):
            self.assertIn(n, namen)
        # Stichprobe: jede Zahlung des Journals steht in journal.csv, Summen passen zur EUeR
        rows = list(csv.DictReader(io.StringIO(z.read("journal.csv").decode("utf-8")), delimiter=";"))
        self.assertEqual(len(rows), len(self.f.journal(VJ)))
        cent = lambda s: int(s.replace(",", "")) if s else 0
        ein = sum(cent(r["Betrag"]) for r in rows if r["Art"] == "Einnahme" and not r["Storniert"])
        self.assertEqual(ein, self.f.euer(VJ)["einnahmen_cent"])
        self.assertTrue(all(len(r["Datum"]) == 10 and r["Datum"][2] == "." for r in rows))
        # Kassenbuch unveraendert enthalten, Pruefung ok
        self.assertEqual(z.read("kassenbuch/log.jsonl"), self.bh.log.read_bytes())
        self.assertIn("in Ordnung", z.read("kassenbuch/pruefung.txt").decode())
        # jede Datei, auf die eine Tabelle verweist, liegt im Original bei (Hash stimmt) -- auch aus dem Eingangsjahr
        import hashlib
        verweise = []
        for name, spalte_pf, spalte_sha in (("eingangsbelege.csv", "Datei", "SHA256"), ("ausgangsrechnungen.csv", "Datei", "SHA256")):
            for r in csv.DictReader(io.StringIO(z.read(name).decode("utf-8")), delimiter=";"):
                verweise.append((r[spalte_pf], r[spalte_sha]))
        self.assertGreaterEqual(len(verweise), 6)                                         # 6 Belege im Probejahr
        for pfad, sha in verweise:
            self.assertEqual(hashlib.sha256(z.read(pfad)).hexdigest(), sha, pfad)
        self.assertTrue(z.read(f"EUER_{VJ}.pdf").startswith(b"%PDF"))
        # index.xml ist wohlgeformt und beschreibt jede Tabelle mit ihren Spalten
        doc = minidom.parseString(z.read("index.xml"))
        urls = [t.firstChild.data for t in doc.getElementsByTagName("URL")]
        self.assertEqual(sorted(urls), sorted(ja.TABELLEN))
        kopf = z.read("journal.csv").decode("utf-8").splitlines()[0].split(";")
        tab = next(t for t in doc.getElementsByTagName("Table") if t.getElementsByTagName("URL")[0].firstChild.data == "journal.csv")
        self.assertEqual([c.getElementsByTagName("Name")[0].firstChild.data for c in tab.getElementsByTagName("VariableColumn")], kopf)

    def test_j2_pruefung(self):
        self._probejahr()
        with mock.patch("orchestrator.core.jahresabschluss.jetzt", return_value=jetzt().replace(year=VJ + 1, month=1, day=15)):
            pr = {p["text"][:20]: p for p in ja.abschluss_check(self.bh, self.ks, VJ, heute=jetzt().date().replace(year=VJ + 1, month=1, day=15))}
        self.assertTrue(pr["Kassenbuch unverände"]["ok"])
        self.assertFalse(pr["Alle Monate mit dem "]["ok"])                                 # nichts abgeglichen
        self.assertFalse(pr["Alle Ausgangsrechnun"]["ok"])                                 # r2 teilbezahlt
        self.assertFalse(pr["Alle Ausgangsrechnun"]["pflicht"])
        offen = next(p for p in ja.abschluss_check(self.bh, self.ks, VJ) if p["text"].startswith("Alle Monate"))["detail"]
        self.assertTrue(offen.startswith("offen: 02/"))                                    # ab dem ersten Beleg (Februar)
        for m in range(1, 13):
            self.bh.erfassen(QUITTUNG, {"schluessel": f"monat:{VJ}-{m:02d}"})
        pr = {p["text"][:20]: p for p in ja.abschluss_check(self.bh, self.ks, VJ, heute=jetzt().date().replace(year=VJ + 1, month=1, day=15))}
        self.assertTrue(pr["Alle Monate mit dem "]["ok"])

    def test_j3_kette_manipuliert_wird_gemeldet(self):
        self._probejahr()
        zeilen = self.bh.log.read_text(encoding="utf-8").splitlines()
        e = json.loads(zeilen[3]); e["daten"]["x"] = 1; zeilen[3] = json.dumps(e)
        self.bh.log.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        pr = ja.abschluss_check(self.bh, self.ks, VJ)
        self.assertFalse(pr[0]["ok"])
        self.assertIn("BEFUNDE", self._zip().read("kassenbuch/pruefung.txt").decode())


class TestEuerZeilen(unittest.TestCase):
    def test_z1_zeilen_je_formularjahr(self):
        from orchestrator.core.euer_zeilen import zeile, zeilen_hinweis
        self.assertEqual((zeile(2025, "gwg")["zeile"], zeile(2025, "gwg")["kz"]), ("36", "132"))
        self.assertEqual(zeile(2026, "gwg")["zeile"], "37")                                  # 2026: +1 ab Zeile 27
        self.assertEqual((zeile(2026, "wareneinkauf")["zeile"], zeile(2025, "wareneinkauf")["zeile"]), ("29", "27"))
        self.assertEqual(zeile(2026, "umsatz")["zeile"], "12")
        self.assertEqual(zeile(2027, "gwg")["formularjahr"], 2026)                           # neues Jahr: juengstes Formular
        self.assertIn("abgleichen", zeilen_hinweis(2027))
        self.assertEqual(zeile(2026, "gewinn")["zeile"], "")                                 # Summen: ELSTER rechnet
        from orchestrator.core.eingangsbelege import KATEGORIEN
        for k in KATEGORIEN:                                                                  # jede Kategorie hat eine Zeile
            self.assertTrue(zeile(2026, k)["zeile"], k)
            self.assertTrue(zeile(2025, k)["zeile"], k)


class TestJahresabschlussApi(ApiBasis):
    def test_a1_endpunkte(self):
        d = self.c.get("/api/finanzen/abschluss").json()
        self.assertIn("pruefung", d)
        self.assertIn("zeilen_hinweis", d["euer"])
        r = self.c.get("/api/finanzen/abschluss/export")
        self.assertEqual(r.headers["content-type"], "application/zip")
        self.assertIn("index.xml", zipfile.ZipFile(io.BytesIO(r.content)).namelist())
        self.assertTrue(self.c.get("/api/finanzen/abschluss/euer.pdf").content.startswith(b"%PDF"))
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/finanzen/abschluss/export"), "finanzen")
