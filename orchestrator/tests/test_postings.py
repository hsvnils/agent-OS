"""PROJEKTBERICHT P1: Postings je Position (Menge), veroeffentlicht am/Link, Kennzahlen als Zahlen, festgeschriebene
Konditionen und TKP-Vergleich; Katalog-Aenderungen wirken nie auf bestehende Auftraege/Belege."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from datetime import timedelta

from orchestrator.core.beauftragung import AuftragBuch
from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.katalog import Katalog
from orchestrator.core.postings import Postings, format_von, postings_aus, vergleich
from orchestrator.tests.test_angebote import ApiBasis, _stores

HEUTE = jetzt().date()
REEL = {"beschreibung": "Reel, Standalone", "menge": "2", "einheit": "Stück", "katalog_id": "reel_solo",
        "kontakte": 37000, "tkp_cent": 3000, "produktion_cent": 49000, "einzelpreis": "0"}          # 37.000 x 30 / 1.000 + 490 = 1.600 EUR
FEED = {"beschreibung": "Feed-Post oder Karussell", "menge": "1", "katalog_id": "feed",
        "kontakte": 52000, "tkp_cent": 2500, "produktion_cent": 26000, "einzelpreis": "0"}          # 1.300 + 260 = 1.560 EUR
PAUSCHAL = [{"beschreibung": "WhatsApp-Kanal", "menge": "1", "katalog_id": "wa", "einzelpreis": "100"},
            {"beschreibung": "Story-Paket", "menge": "1", "einzelpreis": "300"}]


def _auftrag(pos=None):
    bh, ks, st, k, ap = _stores()
    an = st.anlegen({"firma": k, "positionen": pos or [REEL, FEED] + PAUSCHAL})["nummer"]
    st.status_setzen(an, "versendet"); st.status_setzen(an, "angenommen")
    ab = AuftragBuch(bh, ks, st)
    nr = ab.aus_angebot(an)["nummer"]
    return bh, ab, nr, Postings(bh, ab, bh.dir.parent / "lieferungen")


class TestPostings(unittest.TestCase):
    def test_1_aus_menge_und_format(self):
        bh, ab, nr, ps = _auftrag()
        p = ps.liste(nr)
        self.assertEqual([(x["id"], x["titel"], x["format"], x["kontakt_feld"]) for x in p],
                         [(f"{nr}-P1-1", "Reel 1", "reel", "aufrufe"), (f"{nr}-P1-2", "Reel 2", "reel", "aufrufe"),
                          (f"{nr}-P2-1", "Bild-Post", "feed", "impressionen"), (f"{nr}-P4-1", "Story", "story", "aufrufe")])
        self.assertEqual(p[0]["plan"], {"kontakte": 37000, "tkp_cent": 3000, "produktion_cent": 49000, "preis_cent": 160000})
        self.assertIsNone(format_von({"beschreibung": "Spieltags-Paket", "katalog_id": "pk_match"}))
        self.assertEqual(format_von({"beschreibung": "TikTok-Video"}), ("reel", "TikTok"))

    def test_2_veroeffentlicht_pruefungen(self):
        bh, ab, nr, ps = _auftrag()
        pid = f"{nr}-P1-2"
        with self.assertRaisesRegex(ValueError, "Zukunft"):
            ps.veroeffentlichen(pid, datum=(HEUTE + timedelta(days=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "Link"):
            ps.veroeffentlichen(pid, datum=HEUTE.isoformat(), link="instagram reel")
        with self.assertRaises(KeyError):
            ps.veroeffentlichen(f"{nr}-P3-1", datum=HEUTE.isoformat())             # WhatsApp ist kein Posting
        ps.veroeffentlichen(pid, datum=(HEUTE - timedelta(days=7)).isoformat(), link="https://www.instagram.com/reel/abc/")
        x = ps.get(pid)
        self.assertEqual((x["datum"], x["plattform"], x["kennzahl_faellig"]), ((HEUTE - timedelta(days=7)).isoformat(), "Instagram", True))
        self.assertEqual([p["id"] for p in ps.faellige()], [pid])
        self.assertEqual(ps.faellige(heute=HEUTE - timedelta(days=1)), [])   # erst am 7. Tag

    def test_3_kennzahlen_als_zahlen_mit_verlauf(self):
        bh, ab, nr, ps = _auftrag()
        pid = f"{nr}-P2-1"
        with self.assertRaisesRegex(ValueError, "Impressionen fehlt"):
            ps.kennzahlen_setzen(pid, {"aufrufe": 5})                               # Feed zaehlt Impressionen
        ps.kennzahlen_setzen(pid, {"impressionen": "61.250", "likes": 900, "unbekannt": 3})
        ps.kennzahlen_setzen(pid, {"impressionen": 61300, "likes": 905}, quelle="screenshot")
        x = ps.get(pid)
        self.assertEqual(x["kennzahlen"], {"impressionen": 61300, "likes": 905})
        self.assertEqual(x["kennzahlen_quelle"], "screenshot")
        self.assertEqual([v["typ"] for v in x["verlauf"]], ["posting_kennzahlen"] * 2)

    def test_4_tkp_vergleich(self):
        bh, ab, nr, ps = _auftrag()
        ps.kennzahlen_setzen(f"{nr}-P1-1", {"aufrufe": 50000})
        ps.kennzahlen_setzen(f"{nr}-P1-2", {"aufrufe": 30000})
        ps.kennzahlen_setzen(f"{nr}-P4-1", {"aufrufe": 8000})                     # Pauschale: nur Reichweite
        v = vergleich(ps.liste(nr))
        z = {r["id"]: r for r in v["zeilen"]}
        r1 = z[f"{nr}-P1-1"]
        self.assertEqual((r1["gegenwert_cent"], r1["mehrleistung_cent"], r1["erfuellung_pct"]), (199000, 39000, 135.1))
        self.assertEqual(r1["tkp_eff_cent"], round((160000 - 49000) / 50000 * 1000))   # 22,20 EUR statt 30 EUR
        self.assertEqual(z[f"{nr}-P1-2"]["mehrleistung_cent"], 139000 - 160000)
        self.assertIsNone(z[f"{nr}-P4-1"]["gegenwert_cent"])
        s = v["summe"]
        self.assertEqual((s["kontakte_plan"], s["kontakte_ist"], s["preis_cent"], s["mehrleistung_cent"], s["gemessen"]),
                         (74000, 80000, 320000, 18000, 3))
        self.assertEqual(s["mehrleistung_pct"], 5.6)

    def test_5_katalog_aenderung_wirkt_nicht_zurueck(self):
        bh, ab, nr, ps = _auftrag()
        vorher = (ab.auftrag(nr)["positionen"], ab.auftrag(nr)["summe_cent"], ps.liste(nr)[0]["plan"])
        kat = Katalog(bh)
        k = kat.laden()
        for g in k["gruppen"]:
            for it in g["items"]:
                if it["id"] == "reel_solo":
                    it |= {"kontakte": 10000, "produktion_cent": 99000, "tkp_min_cent": 5000, "tkp_max_cent": 6000}
        self.assertTrue(kat.speichern(k)["geaendert"])
        nachher = (ab.auftrag(nr)["positionen"], ab.auftrag(nr)["summe_cent"], ps.liste(nr)[0]["plan"])
        self.assertEqual(vorher, nachher)


class _Antwort:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


class _Gemini:
    """OpenAI-kompatibler Test-Client: merkt sich die Anfrage, antwortet mit festem Text."""
    def __init__(self, text):
        self.text, self.anfragen = text, []
        self.chat = type("Ch", (), {"completions": self})()

    def create(self, **kw):
        self.anfragen.append(kw)
        return _Antwort(self.text)


class TestKennzahlenP2(unittest.TestCase):
    def setUp(self):
        from orchestrator.channels.telegram import bot
        self.bot = bot
        for d in (bot._PO_FOTO_WARTET, bot._PO_FOTO_OFFEN, bot._PO_AUSLESEN, bot._PO_VORSCHLAG):
            d.clear()
        self.bh, self.ab, self.nr, self.ps = _auftrag()
        self.pid = f"{self.nr}-P1-1"
        self.ps.veroeffentlichen(self.pid, datum=(HEUTE - timedelta(days=7)).isoformat())
        self.ps.veroeffentlichen(f"{self.nr}-P2-1", datum=(HEUTE - timedelta(days=6)).isoformat())
        self.gesendet = []
        self.p1 = mock.patch.object(bot, "_postings", return_value=self.ps)
        self.p2 = mock.patch.object(bot, "_api", side_effect=lambda t, m, p, **k: self.gesendet.append((m, p)) or {"ok": True})
        self.p1.start(); self.p2.start()

    def tearDown(self):
        self.p1.stop(); self.p2.stop()

    def test_1_erinnerung_genau_einmal_ab_tag_7(self):
        self.assertEqual(self.bot._kennzahlen_erinnern("T", "1", heute=HEUTE - timedelta(days=1)), 0)
        self.assertEqual(self.bot._kennzahlen_erinnern("T", "1"), 1)                 # nur Reel 1 (Tag 7), nicht Bild-Post (Tag 6)
        kb = json.loads(self.gesendet[0][1]["reply_markup"])["inline_keyboard"]
        self.assertEqual(kb[0][0]["callback_data"], f"pkz:{self.pid}")
        self.assertLessEqual(len(kb[0][0]["callback_data"].encode()), 64)
        self.assertEqual(self.bot._kennzahlen_erinnern("T", "1"), 0)                 # eine je Posting
        self.assertEqual(self.bot._kennzahlen_erinnern("T", "1", heute=HEUTE + timedelta(days=1)), 1)   # Bild-Post am 7. Tag

    def test_2_nicht_zugestellt_bleibt_offen(self):
        with mock.patch.object(self.bot, "_api", return_value={"ok": False}):
            self.assertEqual(self.bot._kennzahlen_erinnern("T", "1"), 0)
        self.assertEqual(self.bot._kennzahlen_erinnern("T", "1"), 1)

    def test_3_foto_zuordnen_auslesen_bestaetigen(self):
        from orchestrator.core import kennzahlen_lesen
        with mock.patch.object(self.bot, "_download_voice", return_value=b"\xff\xd8bild1"):
            self.bot._po_foto("T", "1", {"file_id": "f1"}, "a.jpg")                  # ohne Wahl: fragt nach dem Posting
            self.bot._po_foto("T", "1", {"file_id": "f2"}, "b.jpg")                  # Album: nur einmal fragen
        frage = [p for m, p in self.gesendet if "reply_markup" in p]
        self.assertEqual(len(frage), 1)
        self.assertIn(f"pkz:{self.pid}", frage[0]["reply_markup"])
        self.assertIn("📷 2 Screenshot(s)", self.bot._po_knopf("1", f"pkz:{self.pid}"))
        self.assertEqual(len(self.ps.get(self.pid)["bilder"]), 2)
        g = _Gemini('Hier: {"aufrufe": "51.234", "likes": 2100, "unsinn": 5, "reichweite": -3}')
        echt = kennzahlen_lesen.lesen
        with mock.patch.object(kennzahlen_lesen, "lesen", side_effect=lambda *a, **k: echt(*a, **(k | {"client": g}))):
            self.bot._po_auslesen("T", {"GEMINI_API_KEY": "x"})
        self.assertEqual(len([c for c in g.anfragen[0]["messages"][0]["content"] if c["type"] == "image_url"]), 2)
        self.assertEqual(self.bot._PO_VORSCHLAG[self.pid], {"aufrufe": 51234, "likes": 2100})
        self.assertIsNone(self.ps.get(self.pid).get("kennzahlen"))                   # erst nach ✅ gespeichert
        self.assertIn("✅", self.bot._po_knopf("1", f"pkj:{self.pid}"))
        x = self.ps.get(self.pid)
        self.assertEqual((x["kennzahlen"], x["kennzahlen_quelle"]), ({"aufrufe": 51234, "likes": 2100}, "screenshot"))
        self.assertNotIn(self.pid, [p["id"] for p in self.ps.faellige()])

    def test_4_korrigieren_speichert_nichts(self):
        self.bot._PO_VORSCHLAG[self.pid] = {"aufrufe": 5}
        self.assertIn("LUNA-OS", self.bot._po_knopf("1", f"pkk:{self.pid}"))
        self.assertIsNone(self.ps.get(self.pid).get("kennzahlen"))
        self.assertIn("⚠️", self.bot._po_knopf("1", f"pkj:{self.pid}"))

    def test_5_handlungsbedarf(self):
        from orchestrator.core.kunden import KundenStore
        from orchestrator.core.todos import geschaefts_todos
        t = [x for x in geschaefts_todos(self.bh, KundenStore(self.bh)) if x["id"].startswith("po-kennzahlen:")]
        self.assertEqual([(x["id"], x["stufe"], x["act_id"]) for x in t], [(f"po-kennzahlen:{self.pid}", "woche", self.nr)])
        self.ps.kennzahlen_setzen(self.pid, {"aufrufe": 1})
        self.assertFalse([x for x in geschaefts_todos(self.bh, KundenStore(self.bh)) if x["id"].startswith("po-kennzahlen:")])


class TestApi(ApiBasis):
    def test_a1_endpunkte_und_rechnung_festgeschrieben(self):
        r = self.c.post("/api/crm/angebote", json={"angebot": {"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst",
                                                               "positionen": [REEL]}}).json()
        an = r["nummer"]
        self.c.post(f"/api/crm/angebote/{an}/versendet")
        nr = self.c.post(f"/api/crm/angebote/{an}/auftrag", json={"annehmen": True}).json()["nummer"]
        d = self.c.get(f"/api/crm/auftraege/{nr}/postings").json()
        self.assertEqual(len(d["postings"]), 2)
        self.assertEqual(d["konditionen"]["positionen"][0]["tkp_cent"], 3000)
        self.assertEqual(d["konditionen"]["festgeschrieben_am"], HEUTE.isoformat())
        pid = d["postings"][0]["id"]
        self.assertTrue(self.c.post(f"/api/crm/postings/{pid}/veroeffentlicht", json={"datum": HEUTE.isoformat()}).json()["ok"])
        k = self.c.post(f"/api/crm/postings/{pid}/kennzahlen", json={"werte": {"aufrufe": "40000"}}).json()
        self.assertTrue(k["ok"], k)
        self.assertEqual(self.c.get(f"/api/crm/auftraege/{nr}/postings").json()["vergleich"]["summe"]["kontakte_ist"], 40000)
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(self.w, "_google_secrets", return_value={}), mock.patch.object(self.w, "ROOT", tmp):
            b = self.c.post(f"/api/crm/postings/{pid}/bild", content=b"\xff\xd8bild", headers={"X-Dateiname": "ins%20ights.png"}).json()
            self.assertEqual(self.c.get(f"/api/crm/postings/{pid}/bild/0").content, b"\xff\xd8bild")
            self.assertFalse(self.c.post(f"/api/crm/postings/{pid}/bild", content=b"x", headers={"X-Dateiname": "a.exe"}).json()["ok"])
        self.assertTrue(b["ok"], b)
        self.assertEqual((b["vorschlag"], b["bild"]["name"][-4:]), ({}, ".png"))
        self.assertIn("von Hand", b["hinweis"])
        self.assertTrue((tmp / "lieferungen" / nr / "kennzahlen").is_dir())
        kat = Katalog(self.w.kunden_store.bh)
        kk = kat.laden()
        for g in kk["gruppen"]:
            for it in g["items"]:
                if it["id"] == "reel_solo":
                    it |= {"tkp_min_cent": 5000, "tkp_max_cent": 6000}
        kat.speichern(kk)
        re_ = self.c.post(f"/api/finanzen/rechnungen/aus-auftrag/{nr}", json={}).json()
        self.assertTrue(re_["ok"], re_)
        pos = self.w._rechnungen().get(re_["entwurf_id"])["positionen"][0]
        self.assertEqual((pos["tkp_cent"], pos["einzelpreis_cent"]), (3000, 160000))


if __name__ == "__main__":
    unittest.main()
