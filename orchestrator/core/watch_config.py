"""Phase 12 -- Abteilungsrelevante Watch-Themen (Fachbereiche).

Pro Abteilung kuratierte **Suchthemen** (Brave, kostenlos) und **GitHub-Topics**, damit der Scheduler jedem
Fachbereich gezielt relevante Aussenwelt-Signale liefert -- ohne Token zu verbrennen (reine Datenarbeit;
LLM-Synthese nur auf Anfrage). Erweiterbar; die Kuerzel entsprechen `subagents.ALL_AGENT_CHARTERS`.
"""
from __future__ import annotations

# abteilung -> {"suche": [Brave-Suchthemen], "github": [GitHub-Topics]}
DEPARTMENT_WATCH: dict[str, dict[str, list[str]]] = {
    # AGENTEN_AUSBAU A4 (CEO 2026-10-05): Themen auf das Geschaeft von Hanserautisch ausgerichtet (Social-Media-Content
    # und Werbung fuer Unternehmen, Fussball/HSV, Kleinunternehmer) -- weiter token-frugal (Brave, ein Bereich je Takt).
    "berater": {  # Unternehmensberater / Strategie & Innovation
        "suche": ["Content Creator Geschaeftsmodell Agentur", "Influencer Marketing Markt Deutschland 2026",
                  "lokales Influencer Marketing Gastronomie Einzelhandel", "Creator Economy Trends Deutschland"],
        "github": ["ai-agents", "autonomous-agents", "multi-agent"],
    },
    "cto": {  # Technology / IT -- LUNA selbst ist Technik: Agenten-Werkzeuge bleiben, ergaenzt um genutzte Dienste
        "suche": ["Gemini API Aenderungen", "Synology DSM Update Docker", "Instagram Graph API Aenderungen",
                  "Telegram Bot API Update", "MCP model context protocol"],
        "github": ["ai-agents", "llm", "agent-framework", "mcp", "llmops"],
    },
    "cfo": {  # Finance
        "suche": ["Kleinunternehmerregelung Aenderung 2026", "E-Rechnung Pflicht Kleinunternehmer",
                  "GoBD Aenderung BMF-Schreiben", "Einnahmen-Ueberschuss-Rechnung Aenderung Formular",
                  "Steuer Influencer Content Creator Finanzamt"],
        "github": ["cost-optimization"],
    },
    "ciso": {  # Security
        "suche": ["Synology Sicherheitsluecke", "Telegram Bot Sicherheit Token", "Google Workspace Sicherheitswarnung",
                  "Instagram Konto gehackt Creator Schutz", "LLM prompt injection defense"],
        "github": ["llm-security", "prompt-injection", "ai-security"],
    },
    "cdo": {  # Data
        "suche": ["Instagram Reels Reichweite Benchmark 2026", "Engagement Rate Benchmark Instagram Deutschland",
                  "TKP Influencer Marketing Benchmark", "Instagram Insights Kennzahlen Aenderung"],
        "github": ["rag", "vector-database", "embeddings"],
    },
    "cco": {  # Content -- speist auch den Content-Feed (Trends -> Ideen)
        "suche": ["Instagram Reels Trends Fussball", "HSV Fans Social Media", "Reels Hook Ideen Trend",
                  "TikTok Trends Fussball Deutschland", "Gastronomie Reels Ideen"],
        "github": ["text-to-video", "content-generation"],
    },
    "cpo": {  # Product -- LUNA-OS als Produkt (A5)
        "suche": ["Agentur Software Angebote Rechnungen Kleinunternehmer", "Creator Business Tool CRM",
                  "Web App iPhone Safe Area Best Practice"],
        "github": ["ai-product", "copilot"],
    },
    "cro": {  # Revenue
        "suche": ["Influencer Preise Deutschland 2026", "Influencer Kooperation Gastronomie Hamburg",
                  "Mikroinfluencer Honorar Reel", "Sponsoring Fussball Fan Account", "Hamburg Unternehmen Social Media Werbung"],
        "github": ["sales-automation", "marketing-ai"],
    },
    "clo": {  # Legal -- CLO_AUSBAU C3 (CEO 2026-10-05): Influencer-/Werbe-, AGB-, Urheber- und KI-Kennzeichnungsrecht
        "suche": ["Influencer Werbekennzeichnung Urteil", "Medienanstalten Leitfaden Werbekennzeichnung",
                  "BGH Influencer Werbung", "AGB Recht Urteil Werbeagentur", "Urheberrecht Social Media Nutzungsrechte Urteil",
                  "Recht am eigenen Bild Werbung Urteil", "KI-Kennzeichnung AI Act Artikel 50", "Kleinunternehmerregelung Aenderung"],
        "github": ["ai-governance", "compliance"],
    },
    "cxo": {  # Experience -- Bedienbarkeit (iPhone/iPad/Rechner) und Kundendokumente (A5)
        "suche": ["iOS Safari Web App Aenderung", "Kunden Report Vorlage Social Media Agentur",
                  "Angebot gestalten Agentur Kunden Erlebnis"],
        "github": ["voice-assistant", "conversational-ai"],
    },
    "cbo": {  # Brand
        "suche": ["Fan Account Markenaufbau Instagram", "Personal Branding Content Creator Fussball",
                  "HSV Marke Fanprojekte"],
        "github": ["brand", "design-tools"],
    },
    "cko": {  # Knowledge -- Gedaechtnis / Clip-Second-Brain (A5)
        "suche": ["Video Archiv durchsuchbar Creator", "second brain Video Clips Suche", "knowledge management AI"],
        "github": ["knowledge-management", "second-brain", "documentation"],
    },
    "chro": {  # Freie Mitarbeitende (A5)
        "suche": ["Freelancer Kameramann Tagessatz Hamburg", "Videoschnitt Freelancer Honorar",
                  "Scheinselbststaendigkeit Freelancer Kreativbranche"],
        "github": ["hr-tech"],
    },
    "cao": {  # Verwaltung (A5)
        "suche": ["Betriebshaftpflicht Content Creator", "Fristen Kleinunternehmer Steuer Kalender",
                  "Versicherung Kamera Equipment Creator"],
        "github": ["automation", "workflow-automation"],
    },
}

# Firmenweite GitHub-Topics (Kern des KI-Agenten-Unternehmens) -- fuer den allgemeinen Trend-Blick.
FIRMEN_GITHUB_TOPICS = ["ai-agents", "llm", "autonomous-agents", "agent-framework", "rag", "mcp"]


def themen_fuer(abteilung: str) -> dict[str, list[str]]:
    return DEPARTMENT_WATCH.get((abteilung or "").strip().lower(), {"suche": [], "github": []})
