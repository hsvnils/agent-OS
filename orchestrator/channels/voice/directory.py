"""Agenten-Verzeichnis: eine Quelle fuer delegate-Routing, Live-Aktivitaetsanzeige und Organigramm.

Anzeigetexte (name/bereich) nutzen Umlaute (Oberflaeche); `key`/`kuerzel` sind kurze Codes.
"""

AGENTS = [
    {"key": "berater", "kuerzel": "Berater", "name": "Unternehmensberater", "bereich": "Strategie, Analyse, Markt"},
    {"key": "cao", "kuerzel": "CAO", "name": "Chief Administrative Officer", "bereich": "Administration, Organisation"},
    {"key": "cfo", "kuerzel": "CFO", "name": "Chief Financial Officer", "bereich": "Finanzen, Budget, Kosten"},
    {"key": "cro", "kuerzel": "CRO", "name": "Chief Revenue Officer", "bereich": "Umsatz, Vertrieb"},
    {"key": "ciso", "kuerzel": "CISO", "name": "Chief Information Security Officer", "bereich": "Sicherheit, Zugriffe"},
    {"key": "cbo", "kuerzel": "CBO", "name": "Chief Brand Officer", "bereich": "Marke, Branding"},
    {"key": "cpo", "kuerzel": "CPO", "name": "Chief Product Officer", "bereich": "Produkt"},
    {"key": "cto", "kuerzel": "CTO", "name": "Chief Technology Officer", "bereich": "Technik, Infrastruktur"},
    {"key": "cxo", "kuerzel": "CXO", "name": "Chief Experience Officer", "bereich": "Nutzererlebnis, UX"},
    {"key": "cco", "kuerzel": "CCO", "name": "Chief Content Officer", "bereich": "Content, Redaktion"},
    {"key": "cdo", "kuerzel": "CDO", "name": "Chief Data Officer", "bereich": "Daten, Analytics"},
    {"key": "chro", "kuerzel": "CHRO", "name": "Chief Human Resources Officer", "bereich": "Personal, Team"},
    {"key": "clo", "kuerzel": "CLO", "name": "Chief Legal Officer", "bereich": "Recht, Verträge"},
    {"key": "cko", "kuerzel": "CKO", "name": "Chief Knowledge Officer", "bereich": "Wissen, Dokumentation"},
]

_BY_KEY = {a["key"]: a for a in AGENTS}


def label(key: str) -> str:
    """Anzeige-Label fuer die Live-Aktivitaet, z. B. 'Chief Financial Officer (CFO)'."""
    a = _BY_KEY.get(key)
    return f"{a['name']} ({a['kuerzel']})" if a else key


def bereich_map() -> dict:
    """key -> Kurzbeschreibung (fuer die delegate-Tool-Beschreibung)."""
    return {a["key"]: a["bereich"] for a in AGENTS}


def organigramm() -> dict:
    """Organigramm-Struktur fuer das Panel."""
    return {
        "type": "organigramm",
        "title": "Organigramm",
        "ceo": "CEO (Nils)",
        "hoa": "Head of Agents",
        "abteilungen": [
            {"key": a["key"], "kuerzel": a["kuerzel"], "name": a["name"], "bereich": a["bereich"]}
            for a in AGENTS
        ],
    }
