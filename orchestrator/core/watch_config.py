"""Phase 12 -- Abteilungsrelevante Watch-Themen (Fachbereiche).

Pro Abteilung kuratierte **Suchthemen** (Brave, kostenlos) und **GitHub-Topics**, damit der Scheduler jedem
Fachbereich gezielt relevante Aussenwelt-Signale liefert -- ohne Token zu verbrennen (reine Datenarbeit;
LLM-Synthese nur auf Anfrage). Erweiterbar; die Kuerzel entsprechen `subagents.ALL_AGENT_CHARTERS`.
"""
from __future__ import annotations

# abteilung -> {"suche": [Brave-Suchthemen], "github": [GitHub-Topics]}
DEPARTMENT_WATCH: dict[str, dict[str, list[str]]] = {
    "berater": {  # Unternehmensberater / Strategie & Innovation
        "suche": ["KI-Agenten Markttrends", "AI agent startups funding", "agentic AI business models"],
        "github": ["ai-agents", "autonomous-agents", "multi-agent"],
    },
    "cto": {  # Technology / IT
        "suche": ["AI agent frameworks vergleich", "LLM orchestration tools", "MCP model context protocol"],
        "github": ["ai-agents", "llm", "agent-framework", "mcp", "llmops"],
    },
    "cfo": {  # Finance
        "suche": ["LLM API pricing changes", "AI token cost optimization", "inference cost reduction"],
        "github": ["llm-inference", "cost-optimization"],
    },
    "ciso": {  # Security
        "suche": ["LLM prompt injection defense", "AI agent security", "OWASP LLM top 10"],
        "github": ["llm-security", "prompt-injection", "ai-security"],
    },
    "cdo": {  # Data
        "suche": ["RAG techniques 2026", "vector database benchmark", "AI data pipelines"],
        "github": ["rag", "vector-database", "embeddings"],
    },
    "cco": {  # Content
        "suche": ["AI video generation tools", "AI content creation trends", "social media automation AI"],
        "github": ["text-to-video", "generative-ai", "content-generation"],
    },
    "cpo": {  # Product
        "suche": ["AI agent product launches", "agent UX patterns", "AI product onboarding"],
        "github": ["ai-product", "copilot"],
    },
    "cro": {  # Revenue
        "suche": ["AI sales automation", "AI marketing agents", "lead generation AI"],
        "github": ["sales-automation", "marketing-ai"],
    },
    "clo": {  # Legal
        "suche": ["EU AI Act updates", "AI copyright ruling", "LLM compliance datenschutz"],
        "github": ["ai-governance", "compliance"],
    },
    "cxo": {  # Experience
        "suche": ["conversational AI UX", "voice agent design", "realtime voice AI"],
        "github": ["voice-assistant", "conversational-ai", "speech-to-text"],
    },
    "cbo": {  # Brand
        "suche": ["AI branding tools", "AI generated brand design", "fan brand engagement AI"],
        "github": ["brand", "design-tools"],
    },
    "cko": {  # Knowledge
        "suche": ["knowledge management AI", "AI documentation tools", "second brain AI"],
        "github": ["knowledge-management", "second-brain", "documentation"],
    },
    "chro": {  # HR
        "suche": ["AI recruiting tools", "AI workforce productivity"],
        "github": ["hr-tech"],
    },
    "cao": {  # Admin
        "suche": ["AI office automation", "AI scheduling assistant"],
        "github": ["automation", "workflow-automation"],
    },
}

# Firmenweite GitHub-Topics (Kern des KI-Agenten-Unternehmens) -- fuer den allgemeinen Trend-Blick.
FIRMEN_GITHUB_TOPICS = ["ai-agents", "llm", "autonomous-agents", "agent-framework", "rag", "mcp"]


def themen_fuer(abteilung: str) -> dict[str, list[str]]:
    return DEPARTMENT_WATCH.get((abteilung or "").strip().lower(), {"suche": [], "github": []})
