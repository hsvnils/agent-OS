"""DIGITALER_BELEG D1-D3: das Belegblatt zeigt dieselben Inhalte wie das PDF (Anschrift, Nummer, Kopfdaten, Texte,
Positionen, Summe) und keine internen Felder; Stempel je Status; Mahnung (auch vor LUNA) als eigenes Blatt."""
import io
import json
import re
import unittest
from datetime import timedelta

from orchestrator.core import belegblatt
from orchestrator.core.beleg_pdf import eur
from orchestrator.core.mahnungen import MahnStore
from orchestrator.tests.test_altrechnungen import PDF, _rs
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mahnverfahren import _drei_mahnungen
from orchestrator.tests.test_rechnungen import FD
from orchestrator.tests.test_zahlungsbedingungen import HEUTE, _ablauf


def _text(b: bytes) -> str:
    from pypdf import PdfReader
    return re.sub(r"\s+", " ", " ".join(s.extract_text() for s in PdfReader(io.BytesIO(b)).pages))


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def _wie_pdf(test, blatt: dict, pdf: bytes, *, texte=True):
    t = _text(pdf)
    for zeile in blatt["empfaenger"]:
        test.assertIn(_norm(zeile), t)
    if blatt["nummer"]:
        test.assertIn(blatt["nummer"], t)
    test.assertIn(eur(blatt["gesamt"]["cent"]).replace(" ", " "), t.replace(" ", " "))
    for g in blatt["gruppen"]:
        for p in g["posten"]:
            test.assertIn(_norm(p["beschreibung"])[:30], t)
    if texte:
        for h in blatt["hinweise"]:
            test.assertIn(_norm(h)[:60], t)
        test.assertIn(_norm(blatt["einleitung"])[:50], t)
    for a, b in blatt["infos"]:
        if b != "wird beim Festschreiben vergeben":
            test.assertIn(b, t)


INTERN = ("kosten", "stundensatz", "nachkalkulation", "satz_cent", "verkauf_satz", "kennzahlen", "notiz_intern")


class TestBlatt(unittest.TestCase):
    def test_1_rechnung_wie_pdf_und_stempel(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 10})
        eid = rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"]
        b = belegblatt.rechnung(rs, rs.get(eid), FD)
        self.assertEqual((b["stempel"]["text"], b["nummer"]), ("ENTWURF", ""))
        _wie_pdf(self, b, rs.vorschau_pdf(eid, FD))
        re_nr = rs.festschreiben(eid, FD)["nummer"]
        r = rs.get(re_nr)
        b = belegblatt.rechnung(rs, r, FD)
        _wie_pdf(self, b, rs._pdf(r, FD))
        self.assertEqual(b["stempel"]["text"], "OFFEN")
        self.assertTrue(any("überweisen" in h for h in b["hinweise"]))                # Zahlungshinweis wie im PDF
        self.assertEqual([p["nr"] for g in b["gruppen"] for p in g["posten"]], list(range(1, len(r["positionen"]) + 1)))
        self.assertIn(["Fällig am", (HEUTE() + timedelta(days=10)).strftime("%d.%m.%Y")], b["infos"])
        self.assertEqual(b["absender"].split(" · ")[0], FD["firma"])
        self.assertTrue(any("IBAN" in x for x in b["fuss"]))
        dump = json.dumps(b).lower()
        self.assertFalse([w for w in INTERN if w in dump])
        rs.bezahlt(re_nr, datum=HEUTE().isoformat())
        self.assertEqual(belegblatt.rechnung(rs, rs.get(re_nr), FD)["stempel"]["text"], "BEZAHLT")

    def test_2_storno_und_ueberfaellig(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 0})
        re_nr = rs.festschreiben(rs.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"], FD)["nummer"]
        x = rs.stornieren(re_nr, FD, grund="Adresse falsch")
        self.assertEqual(belegblatt.rechnung(rs, rs.get(re_nr), FD)["stempel"],
                         {"art": "rot", "text": "STORNIERT", "unter": f"durch {x['storno']}"})
        s = belegblatt.rechnung(rs, rs.get(x["storno"]), FD)
        self.assertEqual((s["stempel"]["text"], s["art"]), ("STORNO", "Stornorechnung"))
        _wie_pdf(self, s, rs._pdf(rs.get(x["storno"]), FD), texte=False)
        self.assertIn("Adresse falsch", s["einleitung"])

    def test_3_angebot_und_auftrag(self):
        bh, ks, st, ab, rs, an, nr = _ablauf({"ziel_tage": 14, "vorkasse": {"art": "prozent", "wert": 50}})
        a = st.angebot(an)
        b = belegblatt.angebot(st, a, FD)
        _wie_pdf(self, b, st.pdf(an, FD))
        self.assertEqual(b["stempel"]["text"], "ANGENOMMEN")
        self.assertTrue(any("Vorkasse" in h for h in b["hinweise"]))
        c = belegblatt.auftrag(ab, ab.auftrag(nr), FD)
        _wie_pdf(self, c, ab.pdf(nr, FD))
        self.assertIsNone(c["stempel"])
        self.assertIn(["Angebot", an], c["infos"])

    def test_4_mahnung_und_altmahnung(self):
        bh, ks, rs, k = _rs()
        ms = _drei_mahnungen(bh, ks, rs, k)
        self.assertEqual(belegblatt.rechnung(rs, rs.get("RG-11052026"), FD)["stempel"]["text"], "ÜBERFÄLLIG")
        ms.mahnverfahren_setzen("RG-11052026", datum=HEUTE().isoformat(), durch="Anwältin")
        self.assertEqual(belegblatt.rechnung(rs, rs.get("RG-11052026"), FD)["stempel"],
                         {"art": "rot", "text": "IM MAHNVERFAHREN", "unter": f"seit {HEUTE().strftime('%d.%m.%Y')}"})
        alt = belegblatt.mahnung(ms, ms.get("RG-11052026-M2"), FD)
        self.assertEqual((alt["art"], alt["titel"], alt["gesamt"]["cent"]), ("2. Mahnung", "vor LUNA verschickt", 400000))
        bh2, ks2, st, ab, rs2, an, nr = _ablauf({"ziel_tage": 0})
        re_nr = rs2.festschreiben(rs2.entwurf_aus_auftrag(ab.auftrag(nr))["entwurf_id"], FD)["nummer"]
        ms2 = MahnStore(bh2, ks2)
        m = ms2.berechnen(re_nr, stichtag=(HEUTE() + timedelta(days=20)).isoformat()) | {"nummer": "MA-2026-0001"}
        b = belegblatt.mahnung(ms2, m, FD)
        self.assertEqual(sum(p["gesamt_cent"] for g in b["gruppen"] for p in g["posten"]), m["summe_cent"])
        _wie_pdf(self, b, ms2.pdf(m, FD))


class TestApi(ApiBasis):
    def test_a1_detail_mit_blatt(self):
        an = self._neu()
        self.assertEqual(self.c.get(f"/api/crm/angebote/{an}").json()["blatt"]["art"], "Angebot")
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        b = self.c.get(f"/api/crm/auftraege/{nr}").json()["blatt"]
        self.assertEqual((b["art"], b["empfaenger"][0]), ("Auftragsbestätigung", "Brand X GmbH"))
        eid = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()["entwurf_id"]
        self.assertEqual(self.c.get(f"/api/finanzen/rechnungen/{eid}").json()["blatt"]["stempel"]["text"], "ENTWURF")
        self.assertEqual(self.c.get("/api/finanzen/mahnungen/MA-2099-0001").status_code, 404)


if __name__ == "__main__":
    unittest.main()
