"""Etappe 6 LUNA-Google-Konto: Belege ausser Haus in LUNAs Drive -- idempotent, gegengeprueft, Tagesstand."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core.beleg_sicherung import belege_sichern, stand_sichern
from orchestrator.core.buchhaltung import Buchhaltung
from orchestrator.governance.google_workspace import MockGoogleWorkspace


def _bh():
    bh = Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")
    bh.beleg_ablegen(b"%PDF angebot", "Angebot_AN-2026-0001.pdf", jahr=2026, art="geschaeftsbrief")
    bh.beleg_ablegen(b"From: x\n\nHallo", "Mail_AN-2026-0001_ein_m1.eml", jahr=2026, art="geschaeftsbrief")
    return bh


class TestBelegSicherung(unittest.TestCase):
    def test_1_kopiert_einmal_mit_pruefsumme(self):
        bh, g = _bh(), MockGoogleWorkspace()
        r = belege_sichern(bh, g)
        self.assertEqual((r["kopiert"], r["fehler"]), (2, []))
        self.assertEqual(set(g.drive["ordner"]), {"LUNA-Buchhaltung/Belege/2026"})
        eintraege = bh.eintraege("beleg_extern_kopiert")
        self.assertEqual(len(eintraege), 2)
        self.assertTrue(eintraege[0]["daten"]["ziel"].startswith("LUNA-Buchhaltung/Belege/2026/"))
        self.assertEqual(belege_sichern(bh, g)["kopiert"], 0)                          # idempotent
        self.assertEqual(len(g.drive["dateien"]), 2)
        bh.beleg_ablegen(b"%PDF neu", "Angebot_AN-2026-0002.pdf", jahr=2026)
        self.assertEqual(belege_sichern(bh, g)["kopiert"], 1)                          # neuer Beleg kommt dazu
        self.assertEqual(bh.pruefe_kette(), [])

    def test_2_manipulierte_oder_fehlende_datei_wird_nicht_kopiert(self):
        bh, g = _bh(), MockGoogleWorkspace()
        belege = [e["daten"]["pfad"] for e in bh.eintraege("beleg")]
        (bh.dir / belege[0]).write_bytes(b"gefaelscht")
        (bh.dir / belege[1]).unlink()
        meldungen = []
        r = belege_sichern(bh, g, notify=lambda t, **k: meldungen.append((t, k.get("detail"))))
        self.assertEqual(r["kopiert"], 0)
        self.assertEqual(len(r["fehler"]), 2)
        self.assertIn("Pruefsumme", r["fehler"][0])
        self.assertEqual(len(meldungen), 1)
        self.assertEqual(getattr(g, "drive", {"dateien": {}})["dateien"], {})

    def test_3_upload_fehler_und_nachholen(self):
        bh, g = _bh(), MockGoogleWorkspace()
        with mock.patch.object(g, "drive_datei_hochladen", return_value={"ok": False, "hinweis": "Kontingent"}):
            r = belege_sichern(bh, g)
        self.assertEqual((r["kopiert"], len(r["fehler"])), (0, 2))
        self.assertEqual(bh.eintraege("beleg_extern_kopiert"), [])
        self.assertEqual(belege_sichern(bh, g)["kopiert"], 2)                          # naechster Lauf holt nach

    def test_4_vorhandene_drive_datei_wird_uebernommen(self):
        bh, g = _bh(), MockGoogleWorkspace()
        belege_sichern(bh, g)
        # gleiche Belege in einer frischen Kette (Kopier-Eintraege fehlen, Dateien liegen schon in Drive)
        bh2 = Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung")
        for e in bh.eintraege("beleg"):
            d = e["daten"]
            bh2.beleg_ablegen((bh.dir / d["pfad"]).read_bytes(), d["name"], jahr=2026, art=d["art"])
        r = belege_sichern(bh2, g)
        self.assertEqual((r["kopiert"], r["uebernommen"]), (0, 2))                     # kein Doppel-Upload
        self.assertEqual(len(g.drive["dateien"]), 2)

    def test_5_tagesstand(self):
        bh, g = _bh(), MockGoogleWorkspace()
        (bh.dir / "katalog.json").write_text("{}", encoding="utf-8")
        r = stand_sichern(bh, g, heute="2026-09-28")
        self.assertEqual((r["ok"], r["hochgeladen"]), (True, ["log.jsonl", "katalog.json"]))
        self.assertEqual(stand_sichern(bh, g, heute="2026-09-28")["hochgeladen"], [])   # heute schon gesichert
        self.assertIn("LUNA-Buchhaltung/Stand/2026-09-28", g.drive["ordner"])

    def test_6_ohne_google(self):
        self.assertEqual(belege_sichern(_bh(), None)["fehler"], ["Google nicht verbunden"])


if __name__ == "__main__":
    unittest.main()
