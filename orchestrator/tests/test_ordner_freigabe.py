"""KUNDENORDNER_FREIGABE F2 (Weg A, CEO 2026-10-19): Freigabe-Link /teilen/<schluessel> -- ohne Anmeldung nur genau dieser
Ordner, mit Ablauf, optional Passwort, widerrufbar, Abrufe protokolliert, Bremse gegen Durchprobieren."""
import io
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core import ordner_freigabe as of
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.sitzungen import Sitzungen
from orchestrator.tests.test_angebote import ApiBasis

ORIGIN = "https://os.test"


class FreigabeBasis(ApiBasis):
    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient
        w = self.w
        self._alt = (w._PW, w._USER, w._sitzungen, dict(w._TEILEN_TAKT), dict(w._TEILEN_OK), dict(w._TEILEN_GESEHEN))
        w._TEILEN_TAKT.clear(); w._TEILEN_OK.clear(); w._TEILEN_GESEHEN.clear()
        self.tmp = Path(tempfile.mkdtemp())
        w._PW, w._USER = "richtig-geheim", "ceo"
        w._sitzungen = Sitzungen(self.tmp / "sitzungen.json")
        self._root = mock.patch.object(w, "ROOT", self.tmp)
        self._root.start()
        self.c = TestClient(w.app, base_url=ORIGIN, follow_redirects=False)       # ohne Anmeldung (wie ein Kunde)
        self.a = ("ceo", "richtig-geheim")                                          # CEO
        o = self.c.post(f"/api/crm/kunden/{self.k}/ordner", json={"name": "Herbst"}, auth=self.a).json()
        self.oid = o["id"]
        ko = w._kundenordner()
        ko.datei_ablegen(self.oid, b"%PDF-1.4 Plan", "Plan.pdf")
        ko.datei_ablegen(self.oid, b"\x00\x00\x00\x18ftypmp42" + b"v" * 100, "Reel final.mp4")
        a = ko.anlegen(self.k, "Anderer Ordner")
        ko.datei_ablegen(a["id"], b"%PDF geheim", "Geheim.pdf")

    def tearDown(self):
        self._root.stop()
        w = self.w
        w._PW, w._USER, w._sitzungen = self._alt[:3]
        for d, alt in zip((w._TEILEN_TAKT, w._TEILEN_OK, w._TEILEN_GESEHEN), self._alt[3:]):
            d.clear(); d.update(alt)
        super().tearDown()

    def freigeben(self, **kw):
        r = self.c.post(f"/api/crm/kundenordner/{self.oid}/freigaben", json=kw, auth=self.a).json()
        self.assertTrue(r["ok"], r)
        return r


class TestFreigabe(FreigabeBasis):
    def test_1_link_nur_dieser_ordner(self):
        self.assertEqual(self.c.get(f"/api/crm/kunden/{self.k}/ordner").status_code, 401)   # Rest bleibt gesperrt
        r = self.freigeben()
        self.assertTrue(r["link"].startswith("/teilen/") and len(r["link"]) > 40)
        self.assertEqual(r["ablauf"], (jetzt().date() + timedelta(days=30)).isoformat())
        s = self.c.get(r["link"])
        self.assertEqual(s.status_code, 200)
        self.assertIn("Plan.pdf", s.text)
        self.assertIn("Reel final.mp4", s.text)
        self.assertNotIn("Geheim.pdf", s.text)
        for k in ("content-security-policy", "x-robots-tag", "referrer-policy"):
            self.assertIn(k, s.headers)
        d = self.c.get(r["link"] + "/datei/0")
        self.assertEqual((d.status_code, d.content), (200, b"%PDF-1.4 Plan"))
        self.assertIn("attachment", d.headers["content-disposition"])
        self.assertEqual(self.c.get(r["link"] + "/datei/2").status_code, 404)       # Datei eines anderen Ordners: nein
        for trick in ("/datei/-1", "/datei/0/../../api/crm/kunden", "/../api/crm/kunden/" + self.k + "/ordner"):
            self.assertIn(self.c.get(r["link"] + trick).status_code, (401, 404, 422))
        z = zipfile.ZipFile(io.BytesIO(self.c.get(r["link"] + "/zip").content))
        self.assertEqual(sorted(z.namelist()), ["Plan.pdf", "Reel final.mp4"])
        self.assertEqual(z.read("Plan.pdf"), b"%PDF-1.4 Plan")
        liste = self.c.get(f"/api/crm/kundenordner/{self.oid}/freigaben", auth=self.a).json()["freigaben"]
        self.assertEqual([a["art"] for a in liste[0]["abrufe"]], ["zip", "datei", "seite"])
        self.assertTrue(liste[0]["abrufe"][0]["ip"].endswith(".0") or liste[0]["abrufe"][0]["ip"] == "testclient")
        self.assertNotIn("schluessel_hash", liste[0])
        self.assertEqual(liste[0]["link"], r["link"])

    def test_2_ablauf_und_widerruf(self):
        r = self.freigeben(tage=7)
        with self.assertRaisesRegex(ValueError, "Ablauf"):
            self.w._freigaben().anlegen(self.oid, tage=3650)
        with mock.patch.object(of, "jetzt", return_value=jetzt() + timedelta(days=8)):
            s = self.c.get(r["link"])
        self.assertEqual(s.status_code, 404)
        self.assertIn("ungültig, abgelaufen", s.text)
        r = self.freigeben()
        self.assertEqual(self.c.get(r["link"]).status_code, 200)
        self.assertTrue(self.c.post(f"/api/crm/freigaben/{r['fid']}/widerrufen", auth=self.a).json()["ok"])
        self.assertEqual(self.c.get(r["link"]).status_code, 404)
        self.assertEqual(self.c.get(r["link"] + "/datei/0").status_code, 404)

    def test_3_passwort(self):
        self.assertFalse(self.c.post(f"/api/crm/kundenordner/{self.oid}/freigaben", json={"passwort": "123"}, auth=self.a).json()["ok"])
        r = self.freigeben(passwort="kiez-2026")
        s = self.c.get(r["link"])
        self.assertIn('type="password"', s.text)
        self.assertNotIn("Plan.pdf", s.text)
        self.assertEqual(self.c.get(r["link"] + "/datei/0").status_code, 403)
        f = self.c.post(r["link"], data={"passwort": "falsch"})
        self.assertEqual(f.headers["location"], r["link"] + "?fehler=1")
        ok = self.c.post(r["link"], data={"passwort": "kiez-2026"})
        self.assertEqual(ok.status_code, 303)
        self.assertIn("Plan.pdf", self.c.get(r["link"]).text)                       # Cookie gilt
        self.assertEqual(self.c.get(r["link"] + "/datei/0").status_code, 200)
        r2 = self.freigeben(passwort="anderes-pw")
        self.assertNotIn("Plan.pdf", self.c.get(r2["link"]).text)                   # Cookie gilt nur fuer diese Freigabe
        self.assertNotIn("kiez-2026", (self.tmp / "orchestrator" / "state" / "freigabe_links.json").read_text())

    def test_4_bremse(self):
        for _ in range(5):
            self.assertEqual(self.c.get("/teilen/" + "x" * 43).status_code, 404)    # Durchprobieren
        r = self.freigeben()
        self.assertEqual(self.c.get(r["link"]).status_code, 429)                    # danach auch gueltige Links gesperrt
        self.w._sitzungen = Sitzungen(self.tmp / "s2.json")
        with mock.patch.object(self.w, "TEILEN_PRO_MINUTE", 3):
            codes = [self.c.get(r["link"] + "/datei/0").status_code for _ in range(5)]
        self.assertEqual(codes[-1], 429)


class TestMail(FreigabeBasis):
    """F3: Link per Mail -- Vorlage „Dateifreigabe“, Link + Ablauf im Text, nie das Passwort, nur mit Bestaetigung."""

    def test_5_vorschau_und_senden(self):
        r = self.freigeben(passwort="Kiez#Alm2026")
        v = self.c.get(f"/api/crm/freigaben/{r['fid']}/versandvorschau", auth=self.a).json()
        self.assertTrue(v["ok"], v)
        voll = "https://os.hanserautisch.synology.me" + r["link"]
        self.assertIn(voll, v["text"])                                              # nie die LAN-Adresse
        self.assertIn(".".join(reversed(r["ablauf"].split("-"))), v["text"])
        self.assertIn("Passwort erhalten Sie separat", v["text"])
        self.assertNotIn("Kiez#Alm2026", v["text"] + v["betreff"])
        self.assertEqual(v["art"], "dateifreigabe")
        url = f"/api/crm/freigaben/{r['fid']}/senden"
        self.assertIn("Bestaetigung", self.c.post(url, json={"an": "kunde@example.com"}, auth=self.a).json()["hinweis"])
        self.assertIn("Link fehlt", self.c.post(url, json={"an": "kunde@example.com", "text": "Hallo", "bestaetigt": True},
                                                auth=self.a).json()["hinweis"])
        mit_pw = v["text"].replace("Bei Fragen", "Passwort: Kiez#Alm2026. Bei Fragen")
        self.assertIn("Passwort steht im Text", self.c.post(url, json={"an": "kunde@example.com", "text": mit_pw, "bestaetigt": True},
                                                           auth=self.a).json()["hinweis"])
        self.assertEqual(self.g.gesendet, [])                                       # bis hier nichts raus
        ok = self.c.post(url, json={"an": "kunde@example.com", "cc": "chef@example.com", "text": v["text"] + "\n\nPS: Gruss vom Kiez",
                                    "betreff": v["betreff"], "bestaetigt": True}, auth=self.a).json()
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(len(self.g.gesendet), 1)
        self.assertIn(voll, self.g.gesendet[0]["text"])
        self.assertIn("CC: chef@example.com", self.g.gesendet[0]["an"])
        f = self.c.get(f"/api/crm/kundenordner/{self.oid}/freigaben", auth=self.a).json()["freigaben"][0]
        self.assertEqual(f["versendet"][0]["an"], ok["an"])
        akte = self.c.get(f"/api/crm/kunden/{self.k}/akte", auth=self.a).json()["dokumente"]
        self.assertTrue(any(d.get("art") == "mail" for d in akte))                   # Mail liegt in der Firmenakte

    def test_6_nur_ceo_und_nur_aktiv(self):
        r = self.freigeben()
        with mock.patch.object(self.w, "hat_modul", side_effect=lambda u, m: m != "finanzen"):   # Team ohne Finanzen
            self.assertIn("nur der CEO", self.c.post(f"/api/crm/freigaben/{r['fid']}/senden", json={"bestaetigt": True},
                                                     auth=self.a).json()["hinweis"])
        self.c.post(f"/api/crm/freigaben/{r['fid']}/widerrufen", auth=self.a)
        self.assertIn("zurueckgezogen", self.c.get(f"/api/crm/freigaben/{r['fid']}/versandvorschau", auth=self.a).json()["hinweis"])

    def test_7_chat_vorschau_dann_senden(self):
        from orchestrator.core.hoa_tools import ToolContext, run_tool
        ctx = ToolContext(core=None, antraege=None, engine=None, finance_dir=None, repo_root=self.tmp, leak_secrets=[],
                          google=self.g, secret_dict={})
        bh = self.w.kunden_store.bh
        with mock.patch("orchestrator.core.buchhaltung.Buchhaltung", return_value=bh):
            v = run_tool("kundenordner_link", {"firma": self.k, "ordner": "herbst"}, ctx)
            self.assertTrue(v["vorschau"], v)
            self.assertEqual(self.g.gesendet, [])
            r = run_tool("kundenordner_link", {"firma": self.k, "ordner": "herbst", "an": "kunde@example.com", "bestaetigt": True}, ctx)
            self.assertTrue(r["ok"], r)
            self.assertIn("/teilen/", self.g.gesendet[0]["text"])
            v = run_tool("kundenordner_link", {"firma": self.k, "ordner": "herbst"}, ctx)
            self.assertIn("https://os.hanserautisch.synology.me/teilen/", v["text"])  # gleicher Link, kein zweiter
        self.assertEqual(len([f for f in self.w._freigaben().fuer_ordner(self.oid) if f["aktiv"]]), 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
