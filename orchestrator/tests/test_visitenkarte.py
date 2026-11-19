"""KONTAKTE K1: Visitenkarte per Telegram -> Vorschau -> nach Knopf Firma + Ansprechpartner + Foto in der Akte.
Gate: neue Firma, bekannte Firma, bekannter Kontakt; Gegenproben: ohne Knopf nichts angelegt, kein Bild-Modell -> OCR,
keine Visitenkarte -> Kennzahlen-Weg wie bisher, wartendes Posting -> Visitenkarte wird gar nicht gefragt."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.core import visitenkarte as vk
from orchestrator.core.firmenakte import Firmenakte
from orchestrator.tests.test_angebote import _stores

KARTE = {"art": "visitenkarte", "firma": "Alta Seta GmbH", "vorname": "Patrick", "nachname": "Muster", "rolle": "Vertrieb",
         "mail": "patrick@alta-seta.de", "telefon": "+49 171 1234567", "website": "alta-seta.de", "ort": "Neustadt"}


class _Antwort:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


class _Client:
    def __init__(self, text=None, fehler=False):
        self.text, self.fehler, self.anfragen = text, fehler, []
        self.chat = type("Ch", (), {"completions": self})()

    def create(self, **kw):
        self.anfragen.append(kw)
        if self.fehler:
            raise RuntimeError("down")
        return _Antwort(self.text)


class TestLesen(unittest.TestCase):
    def test_1_modell_streng(self):
        roh = json.dumps(KARTE | {"mail": "Mail: Patrick@Alta-Seta.de", "website": "https://www.alta-seta.de/", "iban": "DE00",
                                  "plz": "abc", "telefon": "12"})
        r = vk.lesen(b"\xff\xd8", "k.jpg", client=_Client(f"Hier: {roh}"), modell="m")
        self.assertEqual((r["mail"], r["website"], r["quelle"]), ("patrick@alta-seta.de", "https://www.alta-seta.de", "modell"))
        self.assertNotIn("iban", r)
        self.assertNotIn("plz", r)                                                       # Unsinn verworfen
        self.assertNotIn("telefon", r)
        self.assertEqual(vk.lesen(b"x", "k.jpg", client=_Client('{"art": "anderes"}'))["art"], "anderes")
        self.assertEqual(vk.aus_antwort("kein json")["art"], "anderes")

    def test_2_rueckfall_ocr(self):
        ocr = lambda d, n: "Patrick Muster\nVertrieb\nT +49 171 1234567\npatrick@alta-seta.de\nwww.alta-seta.de"
        r = vk.lesen(b"x", "k.jpg", client=_Client(fehler=True), ocr=ocr)
        self.assertEqual((r["quelle"], r["mail"], r["telefon"], r["firma"]),
                         ("ocr", "patrick@alta-seta.de", "+49 171 1234567", "Alta Seta"))
        self.assertEqual(vk.lesen(b"x", "k.jpg", ocr=lambda d, n: "Nur ein Foto vom Stadion")["art"], "anderes")
        self.assertNotIn("firma", vk.aus_text("max@gmail.com"))                          # Freemail ist keine Firma


class TestAnlegen(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, _st, self.k, _ap = _stores()
        self.akte = Firmenakte(self.bh, self.ks)

    def test_1_neue_firma_mit_kontakt_und_foto(self):
        v = vk.vorschlag(KARTE, self.ks)
        self.assertEqual((v["firma"], v["ansprechpartner"], v["firma_name"]), ("", "", "Alta Seta GmbH"))
        self.assertIn("Als was anlegen?", vk.text(v))
        self.assertEqual([b["callback_data"][-5:] for b in vk.knoepfe(v, "abc")[0]], ["kunde", "erant", "rtner"])
        with self.assertRaises(ValueError):
            vk.anlegen(v, "ap", self.ks, self.akte, b"bild", "k.jpg")                     # Typ fehlt
        n = len(self.ks.firmen())
        r = vk.anlegen(v, "lieferant", self.ks, self.akte, b"\xff\xd8bild", "k.jpg")
        f = self.ks.firma(r["firma"])
        self.assertEqual((f["name"], f["typ"], f["website"], r["neu_firma"], r["neu_ap"]),
                         ("Alta Seta GmbH", "lieferant", "https://alta-seta.de", True, True))
        self.assertEqual(len(self.ks.firmen()), n + 1)
        a = f["ansprechpartner_liste"][0]
        self.assertEqual((a["vorname"], a["mail"], a["rolle"]), ("Patrick", "patrick@alta-seta.de", "Vertrieb"))
        self.assertEqual([d["titel"] for d in self.akte.akte(r["firma"])], ["Visitenkarte Patrick Muster"])
        # zweite Karte derselben Person: Firma und Kontakt erkannt, nichts doppelt
        v2 = vk.vorschlag(KARTE, self.ks)
        self.assertEqual((v2["firma"], v2["ansprechpartner"]), (r["firma"], a["nummer"]))
        self.assertIn("nichts doppelt", vk.text(v2))
        r2 = vk.anlegen(v2, "foto", self.ks, self.akte, b"\xff\xd8bild2", "k2.jpg")
        self.assertFalse(r2["neu_firma"] or r2["neu_ap"])
        self.assertEqual(len(self.ks.firma(r["firma"])["ansprechpartner_liste"]), 1)

    def test_2_bekannte_firma_neuer_kontakt(self):
        v = vk.vorschlag(KARTE | {"firma": "Brand X", "mail": "neu@brandx.de", "vorname": "Ben"}, self.ks)   # Domain der Firma
        self.assertEqual((v["firma"], v["ansprechpartner"]), (self.k, ""))
        self.assertEqual(vk.knoepfe(v, "s")[0][0]["callback_data"], "vkn:s:ap")
        vor = len(self.ks.firmen())
        r = vk.anlegen(v, "ap", self.ks, self.akte, b"\xff\xd8", "k.jpg")
        self.assertEqual((r["firma"], r["neu_firma"], r["neu_ap"], len(self.ks.firmen())), (self.k, False, True, vor))


class TestBot(unittest.TestCase):
    def setUp(self):
        from orchestrator.channels.telegram import bot
        self.bot = bot
        bot._VK_WARTET.clear()
        self.bh, self.ks, _st, self.k, _ap = _stores()
        self.root = Path(tempfile.mkdtemp())
        (self.root / "buchhaltung").symlink_to(self.bh.dir)
        (self.root / "finance").mkdir()
        self.gesendet = []
        self.ps = [mock.patch.object(bot, "ROOT", self.root),
                   mock.patch.object(bot, "_api", side_effect=lambda t, m, p, **k: self.gesendet.append((m, p)) or {"ok": True}),
                   mock.patch.object(bot, "_download_voice", return_value=b"\xff\xd8karte")]
        for p in self.ps:
            p.start()

    def tearDown(self):
        for p in self.ps:
            p.stop()

    def _foto(self, antwort):
        with mock.patch("orchestrator.core.claude_api.cloud_client", return_value=(_Client(antwort), "claude")):
            return self.bot._vk_foto("T", 1, {"file_id": "f"}, "k.jpg", "", {"ANTHROPIC_API_KEY": "x"})

    def test_1_vorschau_dann_knopf(self):
        vor = len(self.ks.firmen())
        self.assertTrue(self._foto(json.dumps(KARTE)))
        self.assertEqual(len(self.ks.firmen()), vor)                                     # Vorschau schreibt nichts
        kb = json.loads(self.gesendet[-1][1]["reply_markup"])["inline_keyboard"]
        daten = kb[0][1]["callback_data"]
        self.assertTrue(daten.startswith("vkn:") and len(daten.encode()) <= 64)
        res = self.bot._vk_knopf(daten)
        self.assertIn("✅ Visitenkarte übernommen", res)
        self.assertEqual(len(self.ks.firmen()), vor + 1)
        self.assertIn("nicht mehr offen", self.bot._vk_knopf(daten))                       # Knopf nur einmal

    def test_2_gegenproben(self):
        self.assertFalse(self._foto('{"art": "anderes"}'))                                  # Screenshot -> alter Weg
        self.assertTrue(self._foto(json.dumps(KARTE)))
        kb = json.loads(self.gesendet[-1][1]["reply_markup"])["inline_keyboard"]
        vor = len(self.ks.firmen())
        self.assertIn("verworfen", self.bot._vk_knopf(kb[1][0]["callback_data"]))
        self.assertEqual(len(self.ks.firmen()), vor)
        self.assertFalse(vk.an({"VISITENKARTE": "0"}))
        self.assertTrue(vk.an({}))

    def test_3_wartendes_posting_hat_vorrang(self):
        quelle = Path(self.bot.__file__).read_text(encoding="utf-8")
        i = quelle.index("KONTAKTE K1: Visitenkarte, wenn kein Posting")
        self.assertIn("not _PO_FOTO_WARTET.get(str(chat_id))", quelle[i:i + 400])
        self.assertLess(i, quelle.index("_po_foto(token, chat_id, _foto"))


if __name__ == "__main__":
    unittest.main()
