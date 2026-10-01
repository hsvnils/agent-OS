"""KUNDEN_FINANZEN Etappe 30: Auftrag „geliefert“ (Lieferdatum, wieder oeffnen), Zeitsperre, Lieferungen mit Dateien
(Upload in Stuecken) und Links. Etappe 29 nutzt dieselbe Zeit-API (Start nur fuer beauftragte Auftraege)."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core import lieferungen as lf_mod
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.lieferungen import Lieferungen
from orchestrator.core.zeiterfassung import offene_auftraege
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_zeiterfassung import _setup

HEUTE = jetzt().date()


def _lf(bh, ab):
    return Lieferungen(bh, Path(tempfile.mkdtemp()) / "lieferungen", ab)


class TestGeliefert(unittest.TestCase):
    def test_1_status_und_zeitsperre(self):
        bh, ks, k, ab, nr, z = _setup()
        with self.assertRaisesRegex(ValueError, "Zukunft"):
            ab.status_setzen(nr, "erledigt", datum=(HEUTE + timedelta(days=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "nicht nach"):
            ab.status_setzen(nr, "beauftragt", grund="x")                         # nur aus „geliefert“
        ab.status_setzen(nr, "erledigt", datum=(HEUTE - timedelta(days=2)).isoformat())
        self.assertEqual(ab.auftrag(nr)["geliefert_am"], (HEUTE - timedelta(days=2)).isoformat())
        for tun in (lambda: z.starten(auftrag=nr), lambda: z.eintragen(auftrag=nr, datum=HEUTE.isoformat(), minuten=30)):
            with self.assertRaisesRegex(ValueError, "geliefert"):
                tun()
        self.assertEqual(offene_auftraege(ab, k), [])                              # Telegram bietet ihn nicht an
        with self.assertRaisesRegex(ValueError, "begruenden"):
            ab.status_setzen(nr, "beauftragt")
        ab.status_setzen(nr, "beauftragt", grund="Nachlieferung Hochformat")
        a = ab.auftrag(nr)
        self.assertEqual((a["status"], a["geliefert_am"]), ("beauftragt", ""))
        self.assertEqual(a["verlauf"][-1]["grund"], "Nachlieferung Hochformat")
        self.assertTrue(z.starten(auftrag=nr)["id"])                                 # wieder buchbar


class TestLieferungen(unittest.TestCase):
    def test_1_anlegen_links_und_stuecke(self):
        bh, ks, k, ab, nr, z = _setup()
        lf = _lf(bh, ab)
        with self.assertRaisesRegex(ValueError, "Link"):
            lf.anlegen(nr, titel="X", links=["kein link"])
        with self.assertRaisesRegex(ValueError, "Titel"):
            lf.anlegen(nr, titel="")
        x = lf.anlegen(nr, titel="Reel final", links=["https://www.instagram.com/p/abc/"])
        with mock.patch.object(lf_mod, "STUECK", 4):
            self.assertEqual(lf.stueck("upload12345", 0, b"abcd"), {"bytes": 4})
            self.assertEqual(lf.stueck("upload12345", 0, b"abcd"), {"bytes": 4})      # Wiederholung ist ok
            with self.assertRaisesRegex(ValueError, "passt nicht"):
                lf.stueck("upload12345", 3, b"zzzz")                                    # Luecke
            lf.stueck("upload12345", 1, b"ef")
            with self.assertRaisesRegex(ValueError, "unvollstaendig"):
                lf.fertig(x["id"], "upload12345", "clip.mp4", groesse=99)
            lf.stueck("upload67890", 0, b"abcd")
            with self.assertRaisesRegex(ValueError, "Dateityp"):
                lf.fertig(x["id"], "upload67890", "virus.exe", groesse=4)
            lf.stueck("uploadABCDE", 0, b"abcd"); lf.stueck("uploadABCDE", 1, b"ef")
            d = lf.fertig(x["id"], "uploadABCDE", "../../clip final.mp4", groesse=6)
        self.assertTrue(d["pfad"].startswith(f"{nr}/"))
        self.assertTrue((lf.ordner / d["pfad"]).is_file())
        self.assertNotIn("belege", d["pfad"])
        pfad, info = lf.datei(x["id"], 0)
        self.assertEqual((pfad.read_bytes(), info["mime"]), (b"abcdef", "video/mp4"))
        self.assertIsNone(lf.datei(x["id"], 5))
        liste = lf.fuer_auftrag(nr)
        self.assertEqual((len(liste), liste[0]["links"], len(liste[0]["dateien"])), (1, ["https://www.instagram.com/p/abc/"], 1))
        lf.entfernen(x["id"], "falscher Auftrag")
        self.assertFalse(pfad.exists())
        self.assertEqual(lf.fuer_auftrag(nr), [])

    def test_2_storniert_gesperrt(self):
        bh, ks, k, ab, nr, z = _setup()
        ab.status_setzen(nr, "storniert", grund="abgesagt")
        with self.assertRaisesRegex(ValueError, "storniert"):
            _lf(bh, ab).anlegen(nr, titel="X")


class TestApi(ApiBasis):
    def test_a1_ablauf(self):
        an = self._neu()
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        self.c.post("/api/finanzen/zeit/einstellungen", json={"monatsbrutto": "5061,21", "wochenstunden": "40"})
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(self.w, "ROOT", tmp), mock.patch.object(lf_mod, "STUECK", 4):
            x = self.c.post(f"/api/crm/auftraege/{nr}/lieferungen", json={"titel": "Fotos", "links": "https://drive.example.com/x\n"}).json()
            self.assertTrue(x["ok"], x)
            for i, teil in enumerate((b"\xff\xd8\xff\xe0", b"jpg")):
                self.assertTrue(self.c.put(f"/api/crm/lieferungen/upload/abcdefgh12/{i}", content=teil).json()["ok"])
            f = self.c.post(f"/api/crm/lieferungen/{x['id']}/fertig", json={"upload_id": "abcdefgh12", "name": "foto.jpg", "groesse": 7}).json()
            self.assertTrue(f["ok"], f)
            self.assertEqual(self.c.get(f"/api/crm/lieferungen/{x['id']}/datei/0").content, b"\xff\xd8\xff\xe0jpg")
            akte = self.c.get(f"/api/crm/kunden/{self.k}/akte").json()
            self.assertEqual([l["titel"] for l in akte["lieferungen"]], ["Fotos"])
        r = self.c.post(f"/api/crm/auftraege/{nr}/status", json={"status": "erledigt", "datum": HEUTE.isoformat()}).json()
        self.assertTrue(r["ok"], r)
        self.assertFalse(self.c.post("/api/finanzen/zeit/start", json={"auftrag": nr}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/crm/auftraege/{nr}/status", json={"status": "beauftragt", "grund": "Nachlieferung"}).json()["ok"])
        st = self.c.post("/api/finanzen/zeit/start", json={"auftrag": nr}).json()
        self.assertTrue(st["ok"], st)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        self.assertEqual(st["start_ms"], int(datetime.fromisoformat(st["start"]).replace(tzinfo=ZoneInfo("Europe/Berlin")).timestamp() * 1000))
        self.assertEqual(self.c.get("/api/finanzen/zeit").json()["laufend"]["start_ms"], st["start_ms"])   # Etappe 29


if __name__ == "__main__":
    unittest.main()
