"""Verwerfen zuruecknehmen (CEO 2026-10-07: Meta Verified gehoert doch in die Buchhaltung)."""
import unittest

from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_mail_belege import _store


class TestReaktivieren(unittest.TestCase):
    def test_1_zuruecknehmen_und_buchen(self):
        st = _store()
        nr = st.aufnehmen(_pdf("Apple Rechnung Meta Verified 16,99 EUR"), "apple.pdf")["nummer"]
        with self.assertRaises(ValueError):
            st.reaktivieren(nr, "doch gebraucht")                                     # nicht verworfen
        st.verwerfen(nr, "privat")
        with self.assertRaises(ValueError):
            st.reaktivieren(nr, " ")                                                  # Grund Pflicht
        self.assertEqual(st.reaktivieren(nr, "CEO: gehoert doch rein")["status"], "zu_pruefen")
        x = st.get(nr)
        self.assertEqual((x["status"], x["grund"]), ("zu_pruefen", ""))
        self.assertEqual([v["typ"] for v in x["verlauf"]][-2:], ["eingang_verworfen", "eingang_reaktiviert"])
        st.buchen(nr, {"lieferant": "Apple", "rechnungsdatum": "2026-06-19", "betrag": "16,99", "kategorie": "software"})
        self.assertEqual(st.get(nr)["status"], "gebucht")
        self.assertEqual(st.bh.pruefe_kette(), [])


if __name__ == "__main__":
    unittest.main()
