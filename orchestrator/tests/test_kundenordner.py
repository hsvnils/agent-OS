"""KUNDENORDNER_FREIGABE F1 (CEO 2026-10-19): Ordner je Firma + Projekt auf der NAS, Upload in Stuecken, Pfade nur innerhalb
des Ordners, Lieferungen per Klick uebernehmen, Datei loeschen."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core import lieferungen as lf_mod
from orchestrator.core.kundenordner import Kundenordner, _slug
from orchestrator.core.lieferungen import Lieferungen
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_zeiterfassung import _setup


def _ko():
    bh, ks, k, ab, nr, z = _setup()
    tmp = Path(tempfile.mkdtemp())
    lf = Lieferungen(bh, tmp / "lieferungen", ab)
    return Kundenordner(bh, tmp / "kundenordner", ks, lf), lf, k, nr


class TestKundenordner(unittest.TestCase):
    def test_1_anlegen_und_hochladen(self):
        ko, lf, k, nr = _ko()
        with self.assertRaises(KeyError):
            ko.anlegen("K-09999", "X")
        with self.assertRaisesRegex(ValueError, "Name"):
            ko.anlegen(k, "  ")
        o = ko.anlegen(k, "Herbstkampagne Größe/../2026")
        self.assertEqual((o["slug"], o["pfad"]), ("herbstkampagne-groesse-2026", f"{k}/herbstkampagne-groesse-2026"))
        self.assertTrue((ko.ordner / o["pfad"]).is_dir())
        with self.assertRaisesRegex(ValueError, "schon einen Ordner"):
            ko.anlegen(k, "herbstkampagne GROESSE 2026")
        with mock.patch.object(lf_mod, "STUECK", 4):
            ko.stueck("uploadKO123", 0, b"abcd"); ko.stueck("uploadKO123", 1, b"ef")
            d = ko.fertig(o["id"], "uploadKO123", "../../../etc/passwd final.mp4", groesse=6)
            ko.stueck("uploadKO999", 0, b"MZ")
            with self.assertRaisesRegex(ValueError, "Dateityp"):
                ko.fertig(o["id"], "uploadKO999", "tool.exe", groesse=2)
            self.assertFalse(ko._upload._tmp("uploadKO999").exists())              # abgelehnter Upload aufgeraeumt
        self.assertTrue(d["pfad"].startswith(o["pfad"] + "/"))
        self.assertNotIn("..", d["pfad"])
        ko.datei_ablegen(o["id"], b"Hallo", "Briefing.docx")
        x = ko.fuer_firma(k)[0]
        self.assertEqual([f["name"] for f in x["dateien"]], ["passwd final.mp4", "Briefing.docx"])
        pfad, info = ko.datei(o["id"], 0)
        self.assertEqual((pfad.read_bytes(), info["mime"]), (b"abcdef", "video/mp4"))
        self.assertIsNone(ko.datei(o["id"], 9))
        with self.assertRaisesRegex(ValueError, "schon in diesem Ordner"):
            ko.datei_ablegen(o["id"], b"Hallo", "Briefing.docx")

    def test_2_datei_ausserhalb_nie(self):
        ko, lf, k, nr = _ko()
        o = ko.anlegen(k, "A")
        ko.bh.erfassen("kundenordner_datei", {"id": o["id"], "name": "x", "pfad": "../lieferungen/geheim.pdf", "groesse": 1,
                                              "sha256": "0", "mime": "application/pdf"})
        geheim = ko.ordner.parent / "lieferungen" / "geheim.pdf"
        geheim.parent.mkdir(parents=True, exist_ok=True)
        geheim.write_bytes(b"x")
        self.assertIsNone(ko.datei(o["id"], 0))                                      # manipulierter Pfad -> kein Zugriff
        b = ko.anlegen(k, "B")
        ko.datei_ablegen(b["id"], b"%PDF", "b.pdf")
        ko.bh.erfassen("kundenordner_datei", {"id": o["id"], "name": "b", "pfad": ko.fuer_firma(k)[0]["dateien"][0]["pfad"],
                                              "groesse": 1, "sha256": "1", "mime": "application/pdf"})
        self.assertIsNone(ko.datei(o["id"], 1))                                      # Datei eines anderen Ordners -> nein

    def test_3_lieferung_uebernehmen_und_loeschen(self):
        ko, lf, k, nr = _ko()
        x = lf.anlegen(nr, titel="Reel final")
        lf.datei_ablegen(x["id"], b"video", "reel.mp4")
        o = ko.anlegen(k, "Herbst", auftrag=nr)
        r = ko.lieferung_uebernehmen(o["id"], x["id"])
        self.assertEqual((r["uebernommen"], r["schon_da"]), (1, 0))
        self.assertEqual(ko.lieferung_uebernehmen(o["id"], x["id"])["schon_da"], 1)    # zweimal -> nicht doppelt
        d = ko.get(o["id"])["dateien"][0]
        self.assertEqual((d["name"], d["quelle"]), ("reel.mp4", x["id"]))
        andere = ko.anlegen(k, "Andere")
        ko.kunden.firma_anlegen({"name": "Zweite GmbH", "typ": "kunde"}, trotz_dublette=True)
        fremd = ko.anlegen(ko.kunden.firmen()[-1]["nummer"], "Fremd")
        with self.assertRaisesRegex(ValueError, "gehoert zu"):
            ko.lieferung_uebernehmen(fremd["id"], x["id"])
        self.assertEqual(ko.lieferung_uebernehmen(andere["id"], x["id"])["uebernommen"], 1)
        pfad, _ = ko.datei(o["id"], 0)
        ko.datei_entfernen(o["id"], 0)
        self.assertFalse(pfad.exists())
        self.assertEqual(ko.get(o["id"])["dateien"], [])
        self.assertTrue(lf.datei(x["id"], 0)[0].is_file())                           # Lieferung bleibt
        self.assertEqual(_slug("!!!"), "ordner")


class TestChat(unittest.TestCase):
    def test_4_luna_legt_ordner_an(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        from orchestrator.tests.test_zeiterfassung import _stores
        root = Path(tempfile.mkdtemp())
        bh, ks, st, k, ap = _stores()
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=None, repo_root=root, leak_secrets=[])
        with mock.patch("orchestrator.core.buchhaltung.Buchhaltung", return_value=bh):
            r = run_tool("kundenordner_anlegen", {"firma": "Brand X GmbH", "name": "Herbstkampagne"}, ctx)
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["ordner"], "Herbstkampagne")
            self.assertTrue((root / "kundenordner" / k / "herbstkampagne").is_dir())
            self.assertFalse(run_tool("kundenordner_anlegen", {"firma": "Gibt es nicht AG", "name": "X"}, ctx)["ok"])
            self.assertIn("schon", run_tool("kundenordner_anlegen", {"firma": k, "name": "Herbstkampagne"}, ctx)["hinweis"])


class TestApi(ApiBasis):
    def test_a1_ablauf(self):
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(self.w, "ROOT", tmp), mock.patch.object(lf_mod, "STUECK", 4):
            o = self.c.post(f"/api/crm/kunden/{self.k}/ordner", json={"name": "Herbst"}).json()
            self.assertTrue(o["ok"], o)
            self.assertFalse(self.c.post(f"/api/crm/kunden/{self.k}/ordner", json={"name": "Herbst"}).json()["ok"])
            for i, teil in enumerate((b"%PDF", b"-1.4")):
                self.assertTrue(self.c.put(f"/api/crm/kundenordner/upload/abcdefgh12/{i}", content=teil).json()["ok"])
            f = self.c.post(f"/api/crm/kundenordner/{o['id']}/fertig", json={"upload_id": "abcdefgh12", "name": "Plan.pdf", "groesse": 8}).json()
            self.assertTrue(f["ok"], f)
            self.assertEqual(self.c.get(f"/api/crm/kundenordner/{o['id']}/datei/0").content, b"%PDF-1.4")
            self.assertEqual(self.c.get(f"/api/crm/kundenordner/{o['id']}/datei/7").status_code, 404)
            liste = self.c.get(f"/api/crm/kunden/{self.k}/ordner").json()["ordner"]
            self.assertEqual([(x["name"], len(x["dateien"])) for x in liste], [("Herbst", 1)])
            self.assertTrue((tmp / "kundenordner" / self.k / "herbst").is_dir())
            r = self.c.post(f"/api/crm/kundenordner/{o['id']}/datei/0/entfernen").json()
            self.assertEqual((r["ok"], r["entfernt"]), (True, "Plan.pdf"))


if __name__ == "__main__":
    unittest.main()
