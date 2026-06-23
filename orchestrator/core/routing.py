"""Autonomie-/Eskalations-Routing und CEO-Tor-Erkennung (deterministisch)."""
from __future__ import annotations

# CEO-Tor-Kategorien (AGENTS.md 5.4). Schluesselphrasen bewusst spezifisch.
CEO_TOR_KEYWORDS: dict[str, list[str]] = {
    "geld": ["kosten", "kostenpflichtig", "bezahlen", "zahlung", "budget", "abo", "preis", "rechnung"],
    "recht": ["vertrag", "vertraege", "lizenz", "agb", "nda"],
    "oeffentlichkeit": ["veroeffentlich", "posten", "pressemitteilung", "publizieren", "tweet"],
    "tools": ["neues tool", "neues modell", "externer zugang", "account anlegen", "api-key", "neuer dienst"],
    "mandat": ["charta", "mandat aendern"],
    "daten": ["loeschen", "loeschung"],
}

_TECH = ["technik", "technisch", "server", "deploy", "infrastruktur", "integration",
         "build", "bug", "mcp", "pipeline", "machbar", "backend", "frontend", "devops"]
_STRAT = ["strategie", "markt", "analyse", "benchmark", "prozess", "effizienz",
          "wettbewerb", "szenario", "berater"]


def detect_ceo_tor(text: str) -> str | None:
    t = text.lower()
    for cat, kws in CEO_TOR_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return cat
    return None


def decide_delegation(text: str) -> list[str]:
    """Welche Subagenten bekommen die Aufgabe? (Berater = Strategie, CTO = Technik)."""
    t = text.lower()
    agents: list[str] = []
    if any(k in t for k in _STRAT):
        agents.append("berater")
    if any(k in t for k in _TECH):
        agents.append("cto")
    if not agents:
        agents.append("berater")  # Default
    return agents
