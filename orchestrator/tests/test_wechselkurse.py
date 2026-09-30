"""KUNDEN_FINANZEN Etappe 20: Euro-Betrag fuer Fremdwaehrungs-Belege zum EZB-Referenzkurs des Rechnungstags
(Wochenende: letzter Kurs davor), zwischengespeichert, ohne Netz keine Aenderung, nie automatisch gebucht."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.eingangsbelege import datei_importieren, fremdwaehrung_erinnern
from orchestrator.core.wechselkurse import EzbKurse, euro_vorschlag, kurse_ergaenzen
from orchestrator.tests.test_eingangsbelege import _pdf, _store

CSV = ("KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
       "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-06-18,1.1502\n"
       "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-06-19,1.1467\n"
       "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-06-22,1.1456\n"
       "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-07-21,1.1418\n")
SUPABASE = "Supabase Pte. Ltd.\nInvoice number WAOFNM-00003\nInvoice date Jun 21, 2026\nCurrency: USD\nAmount due $25.00"


class _Http:
    def __init__(self, antwort=CSV, fehler=False):
        self.antwort, self.fehler, self.aufrufe = antwort, fehler, []

    def __call__(self, url):
        self.aufrufe.append(url)
        if self.fehler:
            raise OSError("offline")
        return self.antwort


def _kurse(http):
    return EzbKurse(Path(tempfile.mkdtemp()) / "wechselkurse.json", http=http)


class TestKurse(unittest.TestCase):
    def test_1_wochenende_und_cache(self):
        h = _Http()
        k = _kurse(h)
        self.assertEqual(k.kurs("usd", "2026-06-21"), ("2026-06-19", 1.1467))        # Sonntag -> Freitag
        self.assertEqual(k.kurs("USD", "2026-06-22"), ("2026-06-22", 1.1456))
        self.assertIn("D.USD.EUR.SP00.A", h.aufrufe[0])
        n = len(h.aufrufe)
        self.assertEqual(k.kurs("USD", "2026-06-22"), ("2026-06-22", 1.1456))        # aus dem Zwischenspeicher
        self.assertEqual(k.kurs("USD", "2026-06-20"), ("2026-06-19", 1.1467))        # Samstag: Luecke ist gesichert
        self.assertEqual(len(h.aufrufe), n)
        self.assertIsNone(k.kurs("EUR", "2026-06-22"))
        self.assertIsNone(_kurse(_Http(fehler=True)).kurs("USD", "2026-06-22"))       # offline: kein Kurs, kein Fehler

    def test_2_vorschlag(self):
        k = _kurse(_Http())
        v = euro_vorschlag({"waehrung": "USD", "betrag_fremd": "25,00", "rechnungsdatum": "2026-06-21", "betrag": ""}, k)
        self.assertEqual(v["betrag"], "21,80")                                           # 25 / 1,1467
        self.assertEqual(v["kurs"], {"waehrung": "USD", "tag": "2026-06-19", "kurs": 1.1467, "quelle": "EZB"})
        self.assertIn("EZB-Referenzkurs vom 2026-06-19", v["kurs_notiz"])
        self.assertEqual(euro_vorschlag({"waehrung": "USD", "betrag_fremd": "33,76", "rechnungsdatum": "2026-07-21"},
                                        k)["betrag"], "29,57")                          # 29,567 -> kaufmaennisch 29,57
        self.assertEqual(euro_vorschlag({"waehrung": "USD", "betrag_fremd": "25,00", "rechnungsdatum": "2026-06-21",
                                         "betrag": "20,00"}, k), {})                     # Euro schon da: nichts
        self.assertEqual(euro_vorschlag({"waehrung": "EUR", "betrag_fremd": "25,00", "rechnungsdatum": "2026-06-21"}, k), {})

    def test_3_beleg_ergaenzen_und_keine_erinnerung(self):
        st = _store()
        nr = datei_importieren(st, _pdf(SUPABASE), "Invoice.pdf")[0]["nummer"]
        self.assertEqual((st.get(nr)["vorschlag"]["waehrung"], st.get(nr)["vorschlag"]["betrag"]), ("USD", ""))
        self.assertEqual(kurse_ergaenzen(st, _kurse(_Http(fehler=True))), [])           # offline: bleibt offen
        self.assertEqual(kurse_ergaenzen(st, _kurse(_Http())), [nr])
        v = st.get(nr)["vorschlag"]
        self.assertEqual((v["betrag"], v["kurs"]["tag"]), ("21,80", "2026-06-19"))
        self.assertEqual(st.get(nr)["status"], "zu_pruefen")                             # nie automatisch gebucht
        self.assertEqual(kurse_ergaenzen(st, _kurse(_Http())), [])                      # nur einmal

        class G:
            termine = []
            def verfuegbar(self): return True
            def termin_anlegen(self, *a, **k):
                self.termine.append(a); return {"ok": True, "termin_id": "e1"}
        g = G()
        self.assertEqual(fremdwaehrung_erinnern(st, g), [])                              # Kurs da: kein Termin


if __name__ == "__main__":
    unittest.main()
