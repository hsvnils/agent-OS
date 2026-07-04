"""Screen-Universum fuer Modell v4 (Insider-Discovery).

Bewusst GETRENNT von `universe.CORE_UNIVERSE` (Mega-Caps fuer v2/v3). Empirisch geprueft (2026-07-04): bei
Mega-Caps kommen Offenmarkt-KAEUFE (Form-4-Code P) praktisch nie vor -- Insider kaufen dort fast nie am Markt.
Der dokumentierte Insider-Edge (Cohen/Malloy, "opportunistic" insider buys) liegt bei Small/Mid-Caps,
Financials/Regionalbanken und abgestraften Growth-Werten. Diese Liste ist daher gezielt auf Werte gerichtet,
bei denen Insider-Kaeufe real vorkommen -- so kann das Insider-Signal ueberhaupt feuern und ein Edge messbar
werden.

Nur `aktie` -- ETFs und Krypto haben keine SEC-Form-4-Insider. Frei erweiterbar: je mehr liquide, insider-aktive
Werte, desto groesser die Stichprobe (n) fuer den Edge-Test. Keine Trades -- reine Beobachtungsliste.
"""
from __future__ import annotations

INSIDER_SCREEN_UNIVERSE: list[dict] = [
    # Fintech / abgestrafte Growth (sehen regelmaessig Insider-Kaeufe)
    {"symbol": "SOFI", "asset": "aktie"}, {"symbol": "RIVN", "asset": "aktie"},
    {"symbol": "LCID", "asset": "aktie"}, {"symbol": "AFRM", "asset": "aktie"},
    {"symbol": "UPST", "asset": "aktie"}, {"symbol": "HOOD", "asset": "aktie"},
    {"symbol": "OPEN", "asset": "aktie"}, {"symbol": "CHPT", "asset": "aktie"},
    {"symbol": "PLUG", "asset": "aktie"}, {"symbol": "DKNG", "asset": "aktie"},
    # Value / Industrie / Auto (Insider-Kaeufe bei Schwaeche)
    {"symbol": "F", "asset": "aktie"}, {"symbol": "GM", "asset": "aktie"},
    {"symbol": "T", "asset": "aktie"}, {"symbol": "INTC", "asset": "aktie"},
    {"symbol": "PARA", "asset": "aktie"}, {"symbol": "WBD", "asset": "aktie"},
    {"symbol": "CCL", "asset": "aktie"}, {"symbol": "NCLH", "asset": "aktie"},
    # Regionalbanken / Financials (klassische Insider-Kaeufer bei Kursdruck)
    {"symbol": "KEY", "asset": "aktie"}, {"symbol": "CFG", "asset": "aktie"},
    {"symbol": "RF", "asset": "aktie"}, {"symbol": "HBAN", "asset": "aktie"},
    {"symbol": "FITB", "asset": "aktie"}, {"symbol": "ZION", "asset": "aktie"},
    {"symbol": "CMA", "asset": "aktie"}, {"symbol": "ALLY", "asset": "aktie"},
    # REITs / Energie / Healthcare (breitere Streuung)
    {"symbol": "KMI", "asset": "aktie"}, {"symbol": "DVN", "asset": "aktie"},
    {"symbol": "MPW", "asset": "aktie"}, {"symbol": "VTRS", "asset": "aktie"},
    {"symbol": "PFE", "asset": "aktie"}, {"symbol": "WBA", "asset": "aktie"},
]
