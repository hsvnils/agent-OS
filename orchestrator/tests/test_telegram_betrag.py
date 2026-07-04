import unittest

from orchestrator.channels.telegram.bot import _parse_betrag


class TestParseBetrag(unittest.TestCase):
    def test_zahl(self):
        self.assertEqual(_parse_betrag("50"), 50.0)

    def test_mit_einheit(self):
        self.assertEqual(_parse_betrag("50 USD"), 50.0)

    def test_komma(self):
        self.assertEqual(_parse_betrag("12,5"), 12.5)

    def test_keine_zahl(self):
        self.assertEqual(_parse_betrag("keine ahnung"), 0.0)


if __name__ == "__main__":
    unittest.main()
