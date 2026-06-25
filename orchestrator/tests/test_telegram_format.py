"""Self-Check: Telegram-Anzeige-Filter -- Markdown raus, Abteilungs-Kuerzel gross."""
import unittest

from orchestrator.core.telegram_format import fuer_telegram


class TestTelegramFormat(unittest.TestCase):
    def test_1_fett_marker_weg(self):
        self.assertEqual(fuer_telegram("**Genauigkeit & Konsistenz**: Weniger Fehler"),
                         "Genauigkeit & Konsistenz: Weniger Fehler")
        self.assertEqual(fuer_telegram("*Fuer die Nacht steht an:*"), "Fuer die Nacht steht an:")

    def test_2_header_und_bullet(self):
        self.assertEqual(fuer_telegram("## Kosten"), "Kosten")
        self.assertEqual(fuer_telegram("* Punkt eins"), "• Punkt eins")

    def test_3_codes_gross(self):
        self.assertEqual(fuer_telegram("Researcher/cto: 15 neue Funde"), "Researcher/CTO: 15 neue Funde")
        self.assertEqual(fuer_telegram("cfo (Selbst-Entwicklung)"), "CFO (Selbst-Entwicklung)")
        self.assertIn("CISO", fuer_telegram("Briefing fuer ciso"))

    def test_4_normaler_text_unveraendert(self):
        self.assertEqual(fuer_telegram("Hallo Nils, alles klar."), "Hallo Nils, alles klar.")
        # einzelner Stern ohne Paar bleibt stehen (kein Crash)
        self.assertEqual(fuer_telegram("3 * 4 = 12"), "3 * 4 = 12")

    def test_5_leer(self):
        self.assertEqual(fuer_telegram(""), "")
        self.assertEqual(fuer_telegram(None), "")


if __name__ == "__main__":
    unittest.main()
