import unittest

from orchestrator.core import ranking


class TestRanking(unittest.TestCase):
    def test_tokenize_min_laenge_und_lower(self):
        self.assertEqual(ranking.tokenize("Ab CDE fghij"), ["cde", "fghij"])   # 'ab' zu kurz

    def test_leere_frage_oder_docs(self):
        self.assertEqual(ranking.bm25_ranking("", [("a", ["hallo"])]), [])
        self.assertEqual(ranking.bm25_ranking("hallo", []), [])

    def test_kein_treffer_leer(self):
        docs = [("a", ranking.tokenize("aepfel und birnen"))]
        self.assertEqual(ranking.bm25_ranking("voellig anderes thema", docs), [])

    def test_relevantestes_dokument_zuerst(self):
        docs = [
            ("a", ranking.tokenize("hotel oetztal kooperation reels marketing")),
            ("b", ranking.tokenize("steuerberater termin juli vorbereiten")),
        ]
        rang = ranking.bm25_ranking("hotel oetztal kooperation", docs)
        self.assertEqual(rang[0][0], "a")

    def test_idf_seltener_term_gewinnt(self):
        # 'zebra' ist selten (nur in b), 'auto' haeufig (in allen) -> b sollte bei Frage 'auto zebra' vorne sein.
        docs = [
            ("a", ranking.tokenize("auto auto auto strasse")),
            ("b", ranking.tokenize("auto zebra")),
            ("c", ranking.tokenize("auto haus")),
        ]
        rang = dict(ranking.bm25_ranking("auto zebra", docs))
        self.assertGreater(rang["b"], rang["a"])

    def test_term_frequenz_zaehlt(self):
        docs = [
            ("viel", ranking.tokenize("budget budget budget budget")),
            ("wenig", ranking.tokenize("budget einmal erwaehnt hier")),
        ]
        rang = ranking.bm25_ranking("budget", docs)
        self.assertEqual(rang[0][0], "viel")


if __name__ == "__main__":
    unittest.main()
