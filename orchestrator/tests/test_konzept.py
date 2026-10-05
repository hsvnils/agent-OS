"""KONZEPT_MAPPE K1-K3: eine Mappe je Vorgang (Angebot -> Auftrag -> Rechnung zeigen denselben Stand), Briefing,
Ideen, Skript je Leistung (wandert von der Angebotsposition zum Posting), Shotlist abhaken, Drehplan, PDF,
Freigabe/Versand nur mit Bestaetigung, Handlungsbedarf."""
import io
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core.angebote import AngebotStore
from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.konzept import KonzeptStore, pdf, todos, vorgang_von
from orchestrator.core.rechnungen import RechnungStore
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_postings import FEED, REEL
from orchestrator.tests.test_rechnungen import FD

HEUTE = jetzt().date()


def _text(b: bytes) -> str:
    from pypdf import PdfReader
    return " ".join(s.extract_text() for s in PdfReader(io.BytesIO(b)).pages)


def _vorgang():
    bh, ks, st, k, ap = _stores()
    an = st.anlegen({"firma": k, "ansprechpartner": ap, "titel": "Herbst", "positionen": [REEL, FEED]})["nummer"]
    return bh, ks, st, an, KonzeptStore(bh, Path(tempfile.mkdtemp()))


class TestKonzept(unittest.TestCase):
    def test_1_eine_mappe_je_vorgang(self):
        bh, ks, st, an, kz = _vorgang()
        kz.briefing(an, {"ziel": "Bekanntheit", "pflicht": "Werbung, Code HSV10", "unbekannt": "x"})
        kz.idee(an, {"titel": "Nachtschicht", "beschreibung": "Drohne"})
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        ab = AuftragBuch(bh, ks, st)
        nr = ab.aus_angebot(an, leistung_von=HEUTE.isoformat())["nummer"]
        rs = RechnungStore(bh, ks)
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"]
        re_nr = rs.festschreiben(eid, FD)["nummer"]
        self.assertEqual({vorgang_von(bh.eintraege(), x) for x in (an, nr, re_nr)}, {an})   # alle Belege -> ein Vorgang
        m = kz.mappe(an)
        self.assertEqual(m["briefing"], {"ziel": "Bekanntheit", "pflicht": "Werbung, Code HSV10"})
        self.assertEqual([i["status"] for i in m["ideen"].values()], ["idee"])
        direkt = ab.anlegen({"firma": st.angebot(an)["firma"], "titel": "Direkt", "positionen": [REEL]})["nummer"]      # ohne Angebot
        self.assertEqual(vorgang_von(bh.eintraege(), direkt), direkt)
        self.assertEqual(kz.mappe(direkt)["briefing"], {})                                   # getrennte Mappen
        with self.assertRaises(KeyError):
            kz.briefing("AN-2099-0001", {"ziel": "x"})

    def test_2_skript_wandert_zum_posting(self):
        bh, ks, st, an, kz = _vorgang()
        slots = kz.kontext(an)["slots"]
        self.assertEqual([(s["position"], s["nr"]) for s in slots], [(1, 1), (1, 2), (2, 1)])   # 2 x Reel + Feed
        kz.skript(an, {"position": 1, "nr": 2, "hook": "Was macht ein Hafen nachts?", "status": "fertig"})
        with self.assertRaisesRegex(ValueError, "gibt es im Vorgang nicht"):
            kz.skript(an, {"position": 1, "nr": 3, "hook": "x"})
        st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
        nr = AuftragBuch(bh, ks, st).aus_angebot(an)["nummer"]
        k = kz.kontext(an)
        self.assertEqual(k["auftrag"], nr)
        self.assertEqual([s["titel"] for s in k["slots"]][:2], ["Reel 1 · Instagram", "Reel 2 · Instagram"])
        self.assertEqual(kz.mappe(an)["skripte"]["S-1-2"]["hook"], "Was macht ein Hafen nachts?")
        self.assertEqual(k["slots"][1]["posting"], f"{nr}-P1-2")

    def test_3_shotlist_dreh_pdf(self):
        bh, ks, st, an, kz = _vorgang()
        a = kz.szene(an, {"titel": "Drohne Totale", "einstellung": "Totale", "dauer": "5 s"})["id"]
        b = kz.szene(an, {"titel": "Interview"})["id"]
        kz.szene_erledigt(an, a, True)
        kz.dreh(an, {"datum": (HEUTE + timedelta(days=1)).isoformat(), "ort": "Burchardkai"})
        m = kz.mappe(an)
        self.assertEqual([(s["titel"], bool(s["erledigt"])) for s in m["szenen_liste"]], [("Drohne Totale", True), ("Interview", False)])
        kz.szene_entfernen(an, b)
        self.assertEqual(len(kz.mappe(an)["szenen_liste"]), 1)
        with self.assertRaisesRegex(ValueError, "JJJJ"):
            kz.dreh(an, {"datum": "morgen"})
        kz.briefing(an, {"ziel": "Bekanntheit in Hamburg"})
        kz.idee(an, {"titel": "Nachtschicht am Terminal", "status": "ausgewaehlt"})
        kz.idee(an, {"titel": "Quiz im Stadion", "status": "verworfen"})
        kz.skript(an, {"position": 1, "nr": 1, "hook": "Hafen bei Nacht"})
        t = _text(pdf(kz.mappe(an), kz.kontext(an), firmendaten=FD, firma_name="Brand X GmbH", art="kunde"))
        self.assertIn("Bekanntheit in Hamburg", t)
        self.assertIn("Nachtschicht am Terminal", t)
        self.assertNotIn("Quiz im Stadion", t)                                  # verworfene Ideen nicht beim Kunden
        self.assertIn("Hafen bei Nacht", t)
        self.assertNotIn("Drohne Totale", t)
        d = _text(pdf(kz.mappe(an), kz.kontext(an), firmendaten=FD, firma_name="Brand X GmbH", art="dreh"))
        self.assertIn("Drohne Totale", d)
        self.assertIn("Burchardkai", d)

    def test_4_freigabe_und_handlungsbedarf(self):
        bh, ks, st, an, kz = _vorgang()
        with self.assertRaisesRegex(ValueError, "Aenderungswunsch"):
            kz.freigabe(an, "aenderung")
        kz.freigabe(an, "beim_kunden", datum=(HEUTE - timedelta(days=3)).isoformat())
        kz.szene(an, {"titel": "Drohne"})
        kz.dreh(an, {"datum": HEUTE.isoformat(), "ort": "Hafen"})
        ids = {t["id"]: t for t in todos(bh.eintraege(), HEUTE)}
        self.assertEqual(ids[f"konzept-freigabe:{an}"]["stufe"], "woche")
        self.assertEqual(ids[f"konzept-dreh:{an}"]["stufe"], "dringend")
        kz.freigabe(an, "freigegeben", datum=HEUTE.isoformat())
        self.assertNotIn(f"konzept-freigabe:{an}", {t["id"] for t in todos(bh.eintraege(), HEUTE)})
        self.assertEqual(kz.mappe(an)["freigabe"]["status"], "freigegeben")

    def test_5_bild(self):
        bh, ks, st, an, kz = _vorgang()
        kz.bild(an, b"\xff\xd8bild", "mood.jpg", idee="I-1")
        self.assertEqual(kz.bild_datei(an, 0).read_bytes(), b"\xff\xd8bild")
        with self.assertRaisesRegex(ValueError, "Bild"):
            kz.bild(an, b"x", "a.exe")


class TestApi(ApiBasis):
    def test_a1_endpunkte_und_versand(self):
        an = self._neu()
        d = self.c.get(f"/api/crm/konzept/{an}").json()
        self.assertEqual(d["kontext"]["vorgang"], an)
        self.assertTrue(self.c.post(f"/api/crm/konzept/{an}/briefing", json={"felder": {"ziel": "Test"}}).json()["ok"])
        self.assertTrue(self.c.post(f"/api/crm/konzept/{an}/idee", json={"titel": "Idee 1", "status": "ausgewaehlt"}).json()["ok"])
        self.assertFalse(self.c.post(f"/api/crm/konzept/{an}/unsinn", json={}).status_code == 200)
        p = self.c.get(f"/api/crm/konzept-pdf/{an}?art=kunde")
        self.assertEqual(p.headers["content-type"], "application/pdf")
        v = self.c.get(f"/api/crm/konzept-versand/{an}").json()
        self.assertEqual(v["an"], "anna@brandx.de")
        ohne = self.c.post(f"/api/crm/konzept-versand/{an}", json={"an": v["an"], "betreff": v["betreff"], "text": v["text"]}).json()
        self.assertFalse(ohne["ok"])
        self.assertEqual(self.g.gesendet, [])
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(self.w, "ROOT", tmp):
            r = self.c.post(f"/api/crm/konzept-versand/{an}", json={"an": v["an"], "betreff": v["betreff"], "text": v["text"],
                                                                     "bestaetigt": True}).json()
        self.assertTrue(r["ok"], r)
        m = self.c.get(f"/api/crm/konzept/{an}").json()["mappe"]
        self.assertEqual((m["freigabe"]["status"], len(m["freigabe"]["versionen"])), ("beim_kunden", 1))
        self.assertIn("Test", _text(self.c.get(f"/api/crm/konzept-pdf/{an}?archiv=1").content))
        akte = self.c.get(f"/api/crm/kunden/{self.k}/akte").json()
        self.assertEqual([x["art"] for x in akte["dokumente"] if x["art"] == "konzept"], ["konzept"])


if __name__ == "__main__":
    unittest.main()
