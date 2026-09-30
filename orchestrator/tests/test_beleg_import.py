"""Beleg-Import (CEO 2026-09-30): gespeicherte Mails (.eml/.mbox) hochladen -- gleiche Erkennung wie Mails an LUNA,
idempotent, Dubletten erkannt. Dazu Lesefehler aus dem echten Jahresordner: Datum TT/MM/JJJJ (DAZN), „Post:“-Absender
und Rufnummern-Positionen (Klarmobil), Firma nur im Fuss (Canva). Nachbauten echter Belege (anonymisiert)."""
import base64
import mailbox
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.eingangsbelege import datei_importieren, vorschlag_regeln
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import TEXT, _pdf, _store
from orchestrator.tests.test_mail_belege import _mail

PAYPAL = """Hallo Nils!
Sie haben 55,70 € EUR an Grover Group GmbH gezahlt
Händler Grover Group GmbH
Transaktionsdatum 24.09.2026
Transaktionscode: 8CB50D0CB141B652
Gesamtbetrag 55,70 € EUR"""

KLARMOBIL = """Post: klarmobil GmbH • Postfach 0661 • 24752 Rendsburg
Nils Krüger
Ihre klarmobil Rechnung Seite 1von 2
Rechnungsbetrag netto 20,3412 €
USt.-Betrag (19%) 3,86 €
Rechnungsbetrag gesamt 24,20 €
1 Grundgebühr 01.09.2026 - 30.09.2026 21,0000 €
1 Rabatt Tarif 11,- EUR dauerhaft 01.09.2026 - 30.09.2026 -9,2437 €
Nettobetrag für Rufnummer 01514 / 2085715 11,7563 €
Rechnungsdatum: 16.09.2026
Rechnungsnr.: F26028317717
1 Grundgebühr 01.09.2026 - 30.09.2026 16,7983 €
Summe Rabatte 31,08 €
Nettobetrag für Rufnummer 0173 / 7428375 8,5849 €"""

DAZN = """Invoice Date : 30/04/2026
Invoice# : INV354025859
DAZN Limited
12 Hammersmith Grove
Unit Total: EUR 29.40
VAT: EUR 5.59
Total: EUR 34.99"""

CANVA = """Rechnung
Rechnungsdatum
23. Januar 2026
Rechnungsnr .
04770-22783405
An
Nils Krüger
Rechnungsadresse
Deutschland
Abonnements
Canva Pro 12,00 €
iAG_OO-QpBc
23. Januar 2026
Gesamtbetrag 12,00 €
Einschl. anfallender Steuern 1,92 €
Bitte für deine Unterlagen aufbewahren.
Canva Pty. Ltd. ABN 80 158 929 938, VAT EU372042198
Copyright © 2026 Canva Pty. Ltd.. Alle Rechte vorbehalten."""


class TestRegeln(unittest.TestCase):
    def test_1_klarmobil_rufnummern(self):
        v = vorschlag_regeln(KLARMOBIL)
        self.assertEqual((v["lieferant"], v["betrag"], v["rechnungsdatum"]), ("klarmobil GmbH", "24,20", "2026-09-16"))
        self.assertEqual(v["positionen"], [{"text": "Rufnummer 01514 / 2085715", "betrag": "13,99"},
                                           {"text": "Rufnummer 0173 / 7428375", "betrag": "10,21"}])   # Summe = 24,20

    def test_2_dazn_datum_mit_schraegstrich(self):
        v = vorschlag_regeln(DAZN)
        self.assertEqual((v["lieferant"], v["rechnungsdatum"], v["betrag"]), ("DAZN Limited", "2026-04-30", "34,99"))

    def test_3_canva_firma_aus_dem_fuss(self):
        v = vorschlag_regeln(CANVA)
        self.assertEqual((v["lieferant"], v["rechnungsdatum"], v["betrag"]), ("Canva Pty. Ltd", "2026-01-23", "12,00"))


class TestImport(unittest.TestCase):
    def test_1_eml_mit_rechnung_im_text_und_idempotent(self):
        st = _store()
        roh = _mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an Grover Group GmbH", text=PAYPAL,
                    koepfe={"Message-ID": "<abc@paypal.de>"})
        r = datei_importieren(st, roh, "Beleg.eml", von="LUNA-OS:ceo")
        self.assertEqual(len(r), 1)
        b = st.get(r[0]["nummer"])
        self.assertEqual((b["quelle"], b["mail_id"], b["vorschlag"]["betrag"]), ("upload", "eml:abc@paypal.de", "55,70"))
        self.assertEqual([x["pfad"][-4:] for x in b["belege"]], [".pdf", ".eml"])            # PDF-Ansicht + Original
        self.assertEqual(datei_importieren(st, roh, "Beleg 2.eml"), [{"nummer": r[0]["nummer"], "doppelt": True}])
        st.verwerfen(r[0]["nummer"], "Test: privat")                                         # verworfen bleibt verworfen
        self.assertEqual(datei_importieren(st, roh, "Beleg 2.eml"), [{"nummer": r[0]["nummer"], "doppelt": True}])
        anders = roh.replace(b"abc@paypal.de", b"xyz@paypal.de")                            # gleiche Rechnung, neue Mail
        self.assertTrue(datei_importieren(st, anders, "Beleg 3.eml")[0].get("doppelt"))

    def test_2_eml_mit_pdf_anhang_und_mbox(self):
        st = _store()
        roh = _mail("Druckerei <rechnung@druckerei-nord.de>", "Ihre Rechnung", text="Anbei die Rechnung.",
                    anhaenge=[("Rechnung.pdf", _pdf(TEXT))], koepfe={"Message-ID": "<r1@nord>"})
        r = datei_importieren(st, roh, "Rechnung.eml")
        self.assertEqual(st.get(r[0]["nummer"])["vorschlag"]["betrag"], "1.190,00")
        with tempfile.TemporaryDirectory() as d:
            box = mailbox.mbox(str(Path(d) / "x.mbox"))
            box.add(_mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an Grover Group GmbH", text=PAYPAL,
                          koepfe={"Message-ID": "<m1@paypal.de>"}))
            box.add(roh)                                                                  # schon importiert
            box.add(_mail("Freund <a@b.de>", "Grillen am Samstag?", text="Hast du Zeit?"))  # keine Rechnung
            box.flush()
            r = datei_importieren(st, (Path(d) / "x.mbox").read_bytes(), "Postfach.mbox")
        self.assertEqual([bool(x.get("doppelt")) for x in r], [False, True])
        self.assertEqual(len(st._falte(st.bh.eintraege())), 2)


class TestApi(ApiBasis):
    def test_a1_upload_eml(self):
        roh = _mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an Grover Group GmbH", text=PAYPAL,
                    koepfe={"Message-ID": "<api@paypal.de>"})
        r = self.c.post("/api/finanzen/belege/hochladen",
                        json={"dateien": [{"name": "Grover.eml", "daten": base64.b64encode(roh).decode()},
                                          {"name": "Privat.eml", "daten": base64.b64encode(
                                              _mail("Freund <a@b.de>", "Hallo", text="Na?")).decode()}]}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual([e["ok"] for e in r["ergebnisse"]], [True, False])
        self.assertIn("Keine Rechnung", r["ergebnisse"][1]["hinweis"])


if __name__ == "__main__":
    unittest.main()
