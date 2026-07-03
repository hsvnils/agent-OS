"""Phase 26 -- lexikalisches Ranking (BM25), lokal und dependency-frei.

Ersetzt das grobe Set-Overlap-Scoring durch **BM25** (Okapi): beruecksichtigt Term-Haeufigkeit (haeufige
Treffer zaehlen mehr), Seltenheit (IDF -- seltene Woerter wiegen schwerer) und Dokumentlaenge. Deterministisch,
kein LLM, kein externer Dienst, keine Datenausleitung -- passt zu Phase 26 (local-first, token-frugal).

Bewusst KEINE neuronalen Embeddings: die braeuchten eine schwere lokale Bibliothek ODER eine externe/
kostenpflichtige API (Widerspruch zu token-frugal + keine Ausleitung). BM25 ist der beste dependency-freie
Kompromiss und deutlich staerker als reines Term-Overlap.
"""
from __future__ import annotations

import math
import re

_WORT = re.compile(r"[\wäöüß]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Zerlegt Text in Tokens (kleingeschrieben, min. 3 Zeichen)."""
    return [w for w in _WORT.findall((text or "").lower()) if len(w) > 2]


def bm25_ranking(frage: str, dokumente: list[tuple], *, k1: float = 1.5, b: float = 0.75) -> list[tuple]:
    """Rankt Dokumente per BM25 gegen die Frage.

    `dokumente`: Liste von (schluessel, tokens) -- tokens bereits zerlegt (Feld-Gewichtung erfolgt beim
    Aufrufer durch Mehrfachnennung von Tokens). Rueckgabe: [(schluessel, score)] absteigend, nur score > 0.
    """
    q = list(dict.fromkeys(tokenize(frage)))               # eindeutige Frage-Terme
    if not q or not dokumente:
        return []
    n = len(dokumente)
    laengen = [len(toks) for _, toks in dokumente]
    avgdl = (sum(laengen) / n) if n else 0.0
    # Dokumentfrequenz je Term.
    df: dict[str, int] = {}
    for _, toks in dokumente:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    ergebnis: list[tuple] = []
    for i, (schluessel, toks) in enumerate(dokumente):
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in q:
            n_t = df.get(t, 0)
            f = tf.get(t, 0)
            if n_t == 0 or f == 0:
                continue
            # Lucene-Variante der IDF -> stets positiv, auch fuer haeufige Terme.
            idf = math.log(1 + (n - n_t + 0.5) / (n_t + 0.5))
            nenner = f + k1 * (1 - b + b * (laengen[i] / avgdl if avgdl else 0.0))
            score += idf * (f * (k1 + 1)) / nenner
        if score > 0:
            ergebnis.append((schluessel, score))
    ergebnis.sort(key=lambda x: x[1], reverse=True)
    return ergebnis
