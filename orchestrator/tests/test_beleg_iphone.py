"""CEO 2026-11-06: Beleg-Formular lag am iPhone ausserhalb des Bildschirms -- iOS-Safari zieht das PDF-iframe auf die
volle PDF-Breite auf. Wachtest: Vorschau steckt in einem begrenzten Rahmen, die Spalten duerfen schrumpfen."""
import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "channels" / "web" / "static"


class TestBelegIphone(unittest.TestCase):
    def test_1_pdf_im_rahmen(self):
        js = (STATIC / "app-v2.js").read_text(encoding="utf-8")
        self.assertIn('<div class="v2-bl-vorschau"><iframe src="${src}" class="v2-bl-pdf"', js)
        self.assertIn('class="v2-bl-gross"', js)                                   # am Telefon gross oeffnen

    def test_2_css_begrenzt(self):
        css = (STATIC / "style-v2.css").read_text(encoding="utf-8")
        self.assertIn(".v2-an-detail > * { min-width: 0; }", css)
        self.assertRegex(css, r"\.v2-an-detail \{ grid-template-columns: minmax\(0, 1fr\); \}")
        self.assertRegex(css, r"\.v2-bl-vorschau \{[^}]*max-width: 100%;[^}]*overflow: auto;")

    def test_3_cache_erneuert(self):
        html = (STATIC / "index-v2.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"style-v2\.css\?v=(\d+)", html).group(1)), 78)


if __name__ == "__main__":
    unittest.main()
