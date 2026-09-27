"""Self-Checks Buchhaltungs-Speicher (KUNDEN_FINANZEN_ROADMAP.md, Etappe 1): Hash-Kette, Nummernkreise, Belege, Modul."""
import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path

from orchestrator.core.buchhaltung import Buchhaltung, aufbewahren_bis, tagespruefung


def _bh():
    return Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")


def _zeilen(bh):
    return bh.log.read_text(encoding="utf-8").splitlines()


def _schreibe(bh, zeilen):
    bh.log.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


class TestKette(unittest.TestCase):
    def test_1_kette_intakt(self):
        bh = _bh()
        self.assertEqual(bh.pruefe_kette(), [])                               # leer = intakt
        bh.erfassen("notiz", {"text": "Ä ö ü ß €"})
        bh.vergebe_nummer("K")
        bh.erfassen("notiz", {"betrag": 12.5})
        self.assertEqual(bh.pruefe_kette(), [])
        self.assertEqual([e["seq"] for e in bh.eintraege()], [1, 2, 3])
        self.assertIsNone(tagespruefung(bh))

    def test_2_veraenderung_erkannt(self):
        bh = _bh()
        bh.erfassen("notiz", {"betrag": 100})
        bh.erfassen("notiz", {"betrag": 200})
        z = _zeilen(bh)
        _schreibe(bh, [z[0].replace('"betrag":100', '"betrag":900'), z[1]])
        befunde = bh.pruefe_kette()
        self.assertTrue(any("Zeile 1" in b and "veraendert" in b for b in befunde), befunde)
        self.assertIn("Integritaetspruefung fehlgeschlagen", tagespruefung(bh))

    def test_3_loeschen_und_einfuegen_erkannt(self):
        bh = _bh()
        for i in range(3):
            bh.erfassen("notiz", {"i": i})
        z = _zeilen(bh)
        _schreibe(bh, [z[0], z[2]])                                           # mittlere Zeile geloescht
        self.assertTrue(bh.pruefe_kette())
        _schreibe(bh, z[:-1])                                                 # letzte Zeile weg: Kette bleibt formal intakt
        self.assertEqual(bh.pruefe_kette(), [])                               # -> deshalb Backup-Schrumpf-Check
        _schreibe(bh, [z[0], z[0], z[1], z[2]])                               # Duplikat eingefuegt
        self.assertTrue(bh.pruefe_kette())

    def test_4_neu_gerechnete_zeile_bricht_nachfolger(self):
        # Wer eine Zeile inkl. eigenem Hash neu berechnet, bricht den prev-Verweis der naechsten Zeile.
        from orchestrator.core.buchhaltung import _hash
        bh = _bh()
        bh.erfassen("notiz", {"betrag": 1})
        bh.erfassen("notiz", {"betrag": 2})
        z = _zeilen(bh)
        e = json.loads(z[0]); e["daten"]["betrag"] = 999
        e["hash"] = _hash(e["prev"], {k: v for k, v in e.items() if k != "hash"})
        _schreibe(bh, [json.dumps(e), z[1]])
        befunde = bh.pruefe_kette()
        self.assertTrue(any("Zeile 2" in b and "Vorgaenger" in b for b in befunde), befunde)

    def test_5_ungueltiger_typ(self):
        with self.assertRaises(ValueError):
            _bh().erfassen("Böse Typ", {})


class TestNummern(unittest.TestCase):
    def test_1_formate(self):
        bh = _bh()
        self.assertEqual(bh.vergebe_nummer("K"), "K-00001")
        self.assertEqual(bh.vergebe_nummer("k"), "K-00002")
        self.assertEqual(bh.vergebe_nummer("AP"), "AP-00001")
        self.assertEqual(bh.vergebe_nummer("RE", jahr=2026), "RE-2026-0001")
        self.assertEqual(bh.vergebe_nummer("RE", jahr=2026), "RE-2026-0002")
        self.assertEqual(bh.vergebe_nummer("RE", jahr=2027), "RE-2027-0001")    # je Jahr neu
        self.assertEqual(bh.vergebe_nummer("AN", jahr=2026), "AN-2026-0001")    # Kreise unabhaengig
        with self.assertRaises(ValueError):
            bh.vergebe_nummer("XX")

    def test_2_parallel_lueckenlos_ohne_doppelte(self):
        bh = _bh()
        ergebnisse, fehler = [], []

        def arbeite():
            try:
                for _ in range(10):
                    ergebnisse.append(Buchhaltung(bh.dir).vergebe_nummer("RE", jahr=2026))  # eigene Instanz je Thread
            except Exception as exc:                                                        # pragma: no cover
                fehler.append(exc)

        threads = [threading.Thread(target=arbeite) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(fehler, [])
        self.assertEqual(sorted(ergebnisse), [f"RE-2026-{i:04d}" for i in range(1, 81)])
        self.assertEqual(bh.pruefe_kette(), [])


class TestBelege(unittest.TestCase):
    def test_1_ablegen_und_pruefen(self):
        bh = _bh()
        ev = bh.beleg_ablegen(b"%PDF-1.4 test", "Rechnung Mai/2026.pdf", jahr=2026, bezug="ER-2026-0001")
        d = ev["daten"]
        self.assertTrue(d["pfad"].startswith("belege/2026/"))
        self.assertNotIn("/", d["pfad"].split("/", 2)[2])                   # Dateiname ohne Pfadanteile
        self.assertEqual(d["aufbewahren_bis"], "2034-12-31")
        self.assertEqual((bh.dir / d["pfad"]).read_bytes(), b"%PDF-1.4 test")
        self.assertEqual(bh.pruefe_belege(), [])

    def test_2_manipulation_und_verlust_erkannt(self):
        bh = _bh()
        p = bh.dir / bh.beleg_ablegen(b"original", "a.pdf", jahr=2026)["daten"]["pfad"]
        q = bh.dir / bh.beleg_ablegen(b"zweiter", "b.pdf", jahr=2026)["daten"]["pfad"]
        p.write_bytes(b"gefaelscht")
        q.unlink()
        befunde = bh.pruefe_belege()
        self.assertTrue(any("veraendert" in b for b in befunde) and any("fehlt" in b for b in befunde), befunde)
        self.assertIn("Beleg", tagespruefung(bh))

    def test_3_pfad_ausbruch_verhindert(self):
        bh = _bh()
        d = bh.beleg_ablegen(b"x", "../../etc/passwd", jahr=2026)["daten"]
        self.assertTrue((bh.dir / d["pfad"]).resolve().is_relative_to(bh.dir.resolve()))

    def test_4_aufbewahrung(self):
        self.assertEqual(aufbewahren_bis("beleg", 2026), date(2034, 12, 31))
        self.assertEqual(aufbewahren_bis("aufzeichnung", 2026), date(2036, 12, 31))
        self.assertEqual(aufbewahren_bis("geschaeftsbrief", 2026), date(2032, 12, 31))
        with self.assertRaises(ValueError):
            _bh().beleg_ablegen(b"x", "a.pdf", art="quatsch")


class TestZeitzone(unittest.TestCase):
    """BF-32: Container laufen in UTC -- Zeitstempel und Nummern-Jahr muessen deutsche Zeit sein."""

    def test_1_silvester_nach_mitternacht_neues_jahr(self):
        from datetime import datetime as echt, timezone
        from unittest import mock
        utc = echt(2026, 12, 31, 23, 30, tzinfo=timezone.utc)                   # = 01.01.2027 00:30 in Deutschland
        with mock.patch("orchestrator.core.buchhaltung.datetime") as dt:
            dt.now.side_effect = lambda tz=None: utc.astimezone(tz) if tz else utc.replace(tzinfo=None)
            bh = _bh()
            self.assertEqual(bh.vergebe_nummer("RE"), "RE-2027-0001")
            ev = bh.beleg_ablegen(b"x", "a.pdf")
        self.assertEqual(ev["daten"]["jahr"], 2027)
        self.assertEqual(ev["ts"], "2027-01-01T00:30:00+01:00")

    def test_2_zeitstempel_mit_zeitzone(self):
        ts = _bh().erfassen("notiz", {})["ts"]
        self.assertRegex(ts, r"\+0[12]:00$")


class TestModulFinanzen(unittest.TestCase):
    def test_1_nur_owner_oder_zugeteilt(self):
        from orchestrator.core.team_auth import hat_modul, modul_fuer_pfad, module_fuer_rolle
        self.assertEqual(modul_fuer_pfad("GET", "/api/buchhaltung/kette"), "finanzen")
        self.assertEqual(modul_fuer_pfad("POST", "/api/finanzen/x"), "finanzen")
        self.assertNotIn("finanzen", module_fuer_rolle("admin"))
        self.assertNotIn("finanzen", module_fuer_rolle("team"))
        self.assertIn("finanzen", module_fuer_rolle("owner"))
        self.assertTrue(hat_modul({"role": "owner", "allowed_modules": []}, "finanzen"))
        self.assertFalse(hat_modul({"role": "admin", "allowed_modules": module_fuer_rolle("admin")}, "finanzen"))
        self.assertTrue(hat_modul({"role": "admin", "allowed_modules": ["finanzen"]}, "finanzen"))


if __name__ == "__main__":
    unittest.main()
