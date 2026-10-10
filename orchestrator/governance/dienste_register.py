"""Kanonische Liste aller externen Anbieter und Datenquellen (VORSCHLAGSPAUSE_ANBIETER P2, CEO 2026-10-06).

`ANBIETER` ist die **einzige** Stelle, an der steht, mit welchen Diensten LUNA spricht: wofuer, welche Daten
hingehen, welche Zugangs-Schluessel (nur die **Namen**, nie Werte) dazugehoeren, ob er laut Code etwas kosten
kann und ob die Kosten erfasst werden. Daraus entstehen die Seite „🔌 Anbieter & Datenquellen“ in LUNA-OS, die
Kachel „Datenquellen“ in der Investment-App und der CFO-Ueberblick (`register()`, `finance_dashboard`).

`scripts/doku_check.py` prueft, dass jeder Zugangs-Schluessel im Code hier einem Anbieter zugeordnet ist -- ein
neuer Dienst ohne Eintrag macht die Testsuite rot. Ob ein Konto tatsaechlich etwas kostet, steht nicht im Code:
`tarif` beschreibt die Stufe, die wir laut Code/Absprache nutzen; verbindlich ist das jeweilige Anbieter-Konto.
"""
from __future__ import annotations

TARIFE = {
    "gratis": "kostenlos",
    "gratis_stufe": "Gratis-Stufe – darüber kostenpflichtig",
    "nutzung": "kostenpflichtig nach Nutzung",
    "paket": "kostenpflichtig (Paket/Abo)",
}

# schluessel = noetig fuer „eingerichtet“; zugehoerig = weitere Schluessel desselben Anbieters (optional/Varianten);
# lieferant = Namensmuster (klein) der Lieferanten in der Buchhaltung -> Kosten je Anbieter (P3)
ANBIETER = [
    # -- KI --------------------------------------------------------------------------------------------------
    {"id": "anthropic", "lieferant": ["anthropic"], "name": "Anthropic (Claude)", "bereich": "KI", "zweck": "Fachagenten, Rückfall im Chat, Web-Recherche-Eskalation",
     "daten": "Chat-Texte und Aufgaben", "schluessel": ["ANTHROPIC_API_KEY"], "zugehoerig": [], "tarif": "nutzung",
     "kosten_erfasst": True, "konto": "https://console.anthropic.com/settings/billing"},
    {"id": "gemini", "lieferant": ["google cloud"], "name": "Gemini (Google)", "bereich": "KI", "zweck": "Chat (Frontdesk), Video-/Bild-Auswertung, Vorschläge",
     "daten": "Chat-Texte, Bilder/Videos zur Auswertung", "schluessel": ["GEMINI_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": True, "konto": "https://aistudio.google.com/"},
    {"id": "openai", "lieferant": ["openai"], "name": "OpenAI", "bereich": "KI", "zweck": "Rückfall im Chat, Instagram-Analyse",
     "daten": "Chat-Texte, Instagram-Nachrichten zur Analyse", "schluessel": ["OPENAI_API_KEY"], "zugehoerig": ["IG_ANALYSE_KEY", "IG_ANALYSE_BASE_URL"],
     "tarif": "nutzung", "kosten_erfasst": True, "konto": "https://platform.openai.com/settings/organization/billing"},
    {"id": "ollama", "name": "Lokale KI (Ollama auf dem MACO470)", "bereich": "KI", "zweck": "Backoffice-Aufträge, Werkzeugauswahl",
     "daten": "bleibt im Heimnetz", "schluessel": ["LOCAL_LLM_BASE_URL"], "zugehoerig": ["LOCAL_LLM_KEY"], "tarif": "gratis",
     "kosten_erfasst": True, "konto": "", "intern": True},
    # -- Recherche -------------------------------------------------------------------------------------------
    {"id": "brave", "lieferant": ["brave"], "name": "Brave Search", "bereich": "Recherche", "zweck": "Web-Recherche, Watcher, Impressum-Suche",
     "daten": "Suchbegriffe", "schluessel": ["BRAVE_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://api-dashboard.search.brave.com/"},
    # -- Investment ------------------------------------------------------------------------------------------
    {"id": "finnhub", "lieferant": ["finnhub"], "name": "Finnhub", "bereich": "Investment", "zweck": "Aktienkurse, Firmenprofile, News, Insider-Transaktionen",
     "daten": "Börsensymbole", "schluessel": ["FINNHUB_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://finnhub.io/dashboard"},
    {"id": "fmp", "lieferant": ["financial modeling"], "name": "Financial Modeling Prep (FMP)", "bereich": "Investment", "zweck": "Kurshistorie, Top-Gewinner (Markt-Screen)",
     "daten": "Börsensymbole", "schluessel": ["FMP_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://site.financialmodelingprep.com/developer/docs/dashboard"},
    {"id": "alphavantage", "lieferant": ["alpha vantage"], "name": "Alpha Vantage", "bereich": "Investment", "zweck": "Indikatoren (RSI), Tageskurse – ca. 25 Abfragen/Tag",
     "daten": "Börsensymbole", "schluessel": ["ALPHAVANTAGE_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://www.alphavantage.co/premium/"},
    {"id": "coingecko", "lieferant": ["coingecko"], "name": "CoinGecko", "bereich": "Investment", "zweck": "Krypto-Kurse und -Historie",
     "daten": "Krypto-Namen", "schluessel": [], "zugehoerig": ["COINGECKO_API_KEY"], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://www.coingecko.com/en/developers/dashboard"},
    {"id": "sec", "name": "SEC EDGAR (US-Börsenaufsicht)", "bereich": "Investment", "zweck": "Insider-Pflichtmeldungen (Form 4)",
     "daten": "Börsensymbole; Kontaktangabe im Abruf", "schluessel": ["SEC_EDGAR_USER_AGENT"], "zugehoerig": [], "tarif": "gratis",
     "kosten_erfasst": False, "konto": ""},
    {"id": "alpaca", "lieferant": ["alpaca"], "name": "Alpaca (Paper-Depot)", "bereich": "Investment", "zweck": "Spielgeld-Depot: Orders, Konto, Positionen",
     "daten": "Spielgeld-Orders", "schluessel": ["ALPACA_API_KEY", "ALPACA_API_SECRET"], "zugehoerig": [], "tarif": "gratis",
     "kosten_erfasst": False, "konto": "https://app.alpaca.markets/"},
    # -- Kommunikation -----------------------------------------------------------------------------------------
    {"id": "telegram", "name": "Telegram", "bereich": "Kommunikation", "zweck": "LUNA-Bot: Chat, Meldungen, Freigaben",
     "daten": "Chat mit dem CEO", "schluessel": ["TELEGRAM_BOT_TOKEN"], "zugehoerig": [], "tarif": "gratis",
     "kosten_erfasst": False, "konto": ""},
    {"id": "google", "name": "Google Workspace (LUNAs Konto)", "bereich": "Kommunikation", "zweck": "Gmail, Kalender, Drive (Belegkopien)",
     "daten": "Mails, Termine, Beleg-PDFs", "schluessel": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REFRESH_TOKEN"],
     "zugehoerig": [], "tarif": "gratis", "kosten_erfasst": False, "konto": "https://console.cloud.google.com/"},
    {"id": "allinkl", "lieferant": ["all-inkl"], "name": "All-Inkl (Mail luna@hanserautisch.de)", "bereich": "Kommunikation", "zweck": "Kundenmails senden und Antworten lesen",
     "daten": "Kundenmails mit Belegen", "schluessel": ["ALLINKL_MAIL_PASSWORT"], "zugehoerig": [], "tarif": "paket",
     "kosten_erfasst": False, "konto": "https://kas.all-inkl.com/"},
    {"id": "meta", "name": "Meta (Instagram/Facebook)", "bereich": "Kommunikation", "zweck": "Instagram-Kennzahlen, Reels auf Facebook",
     "daten": "Kennzahlen, Videos zum Posten", "schluessel": ["INSTAGRAM_ACCESS_TOKEN"],
     "zugehoerig": ["INSTAGRAM_APP_SECRET", "INSTAGRAM_PAGE_TOKEN", "INSTAGRAM_USER_TOKEN", "INSTAGRAM_INSIGHTS_TOKEN", "INSTAGRAM_VERIFY_TOKEN"],
     "tarif": "gratis", "kosten_erfasst": False, "konto": "https://developers.facebook.com/apps/"},
    # -- Sprache ---------------------------------------------------------------------------------------------
    {"id": "deepgram", "lieferant": ["deepgram"], "name": "Deepgram", "bereich": "Sprache", "zweck": "Spracherkennung im Voice-Kanal",
     "daten": "Sprachaufnahmen", "schluessel": ["DEEPGRAM_API_KEY"], "zugehoerig": [], "tarif": "nutzung",
     "kosten_erfasst": False, "konto": "https://console.deepgram.com/"},
    {"id": "elevenlabs", "lieferant": ["elevenlabs"], "name": "ElevenLabs", "bereich": "Sprache", "zweck": "Sprachausgabe im Voice-Kanal",
     "daten": "Antworttexte", "schluessel": ["ELEVENLABS_API_KEY"], "zugehoerig": [], "tarif": "paket",
     "kosten_erfasst": False, "konto": "https://elevenlabs.io/app/subscription"},
    {"id": "cartesia", "lieferant": ["cartesia"], "name": "Cartesia", "bereich": "Sprache", "zweck": "Sprachausgabe im Voice-Kanal (Alternative)",
     "daten": "Antworttexte", "schluessel": ["CARTESIA_API_KEY"], "zugehoerig": [], "tarif": "nutzung",
     "kosten_erfasst": False, "konto": "https://play.cartesia.ai/"},
    # -- Betrieb ---------------------------------------------------------------------------------------------
    {"id": "github", "lieferant": ["github"], "name": "GitHub", "bereich": "Betrieb", "zweck": "Code-Ablage, Watcher",
     "daten": "Quellcode", "schluessel": ["GITHUB_TOKEN"], "zugehoerig": [], "tarif": "gratis",
     "kosten_erfasst": False, "konto": "https://github.com/settings/billing"},
    {"id": "supabase", "lieferant": ["supabase"], "name": "Supabase", "bereich": "Betrieb", "zweck": "Datenbank-Spiegel (Investment-Lernschleife, LUNA-Tabellen)",
     "daten": "Investment-Prognosen, App-Daten", "schluessel": ["SUPABASE_SERVICE_ROLE_KEY"], "zugehoerig": [], "tarif": "paket",
     "kosten_erfasst": False, "konto": "https://supabase.com/dashboard"},
    {"id": "agentops", "lieferant": ["agentops"], "name": "AgentOps", "bereich": "Betrieb", "zweck": "Beobachtung der Agenten (optional)",
     "daten": "Agenten-Abläufe", "schluessel": ["AGENTOPS_API_KEY"], "zugehoerig": [], "tarif": "gratis_stufe",
     "kosten_erfasst": False, "konto": "https://app.agentops.ai/"},
    # -- Oeffentliche Dienste ohne Zugang (kein Konto, keine Kosten) --------------------------------------------
    {"id": "ezb", "name": "Europäische Zentralbank", "bereich": "Öffentlich", "zweck": "Wechselkurse für Fremdwährungsbelege",
     "daten": "keine", "schluessel": [], "zugehoerig": [], "tarif": "gratis", "kosten_erfasst": False, "konto": ""},
    {"id": "osv", "name": "OSV (Sicherheitsdatenbank)", "bereich": "Öffentlich", "zweck": "Sicherheitslücken in verwendeten Paketen",
     "daten": "Paketnamen/-versionen", "schluessel": [], "zugehoerig": [], "tarif": "gratis", "kosten_erfasst": False, "konto": ""},
    {"id": "osm", "name": "OpenStreetMap (Nominatim/OSRM)", "bereich": "Öffentlich", "zweck": "Adressen finden, Fahrstrecken",
     "daten": "Adressen", "schluessel": [], "zugehoerig": [], "tarif": "gratis", "kosten_erfasst": False, "konto": ""},
    {"id": "gesetze", "name": "Gesetze im Internet", "bereich": "Öffentlich", "zweck": "Rechtstexte für den CLO",
     "daten": "keine", "schluessel": [], "zugehoerig": [], "tarif": "gratis", "kosten_erfasst": False, "konto": ""},
]

# Schluessel im Code, die zu keinem externen Anbieter gehoeren (eigene Zugaenge)
INTERN = {"LUNA_OS_PASSWORD",
          "FRITZBOX_PASSWORD", "DSM_PASSWORD"}   # NETZWERK_WACHE: eigene Geraete (Fritz!Box, NAS), kein externer Anbieter


def alle_schluessel() -> set[str]:
    return {k for a in ANBIETER for k in a["schluessel"] + a["zugehoerig"]} | INTERN


def anbieter(secrets: dict | None = None) -> list[dict]:
    """Liste fuer LUNA-OS: je Anbieter eingerichtet/teilweise/nicht -- **nur Schluesselnamen**, nie Werte."""
    s = secrets or {}
    out = []
    for a in ANBIETER:
        da = [k for k in a["schluessel"] if s.get(k)]
        if not a["schluessel"]:
            stand = "eingerichtet" if any(s.get(k) for k in a["zugehoerig"]) else "ohne Zugang"
        else:
            stand = "eingerichtet" if len(da) == len(a["schluessel"]) else "teilweise" if da else "nicht eingerichtet"
        out.append({k: a[k] for k in ("id", "name", "bereich", "zweck", "daten", "tarif", "kosten_erfasst", "konto")}
                   | {"lieferant": a.get("lieferant", [])}
                   | {"tarif_text": TARIFE[a["tarif"]], "kann_kosten": a["tarif"] != "gratis", "stand": stand,
                      "schluessel": a["schluessel"] + a["zugehoerig"], "intern": bool(a.get("intern"))})
    return out


def register(secrets: dict | None = None) -> dict:
    """CFO-Ueberblick (Tool `finance_dashboard`): Modelle + Dienste, live aus den vorhandenen Schluesseln."""
    modelle = [
        {"name": "Chat (LUNA)", "modell": "claude-haiku-4-5", "provider": "anthropic",
         "fallback": "gemini-2.5-flash -> gpt-4o-mini", "zweck": "Telegram-Dialog",
         "kosten": "per Token", "erfassung": "gemessen"},
        {"name": "Fachagenten (CTO/Berater/...)", "modell": "claude-opus-4-8", "provider": "anthropic (CLI/Abo)",
         "fallback": "-", "zweck": "Konsultation, Innovation, Self-Dev", "kosten": "Abo/per Token",
         "erfassung": "geschaetzt (CLI liefert keine Tokenzahl)"},
        {"name": "Web-Recherche-Eskalation", "modell": "claude-sonnet-4-6", "provider": "anthropic-web",
         "fallback": "Brave", "zweck": "komplexe Recherche", "kosten": "billbar",
         "erfassung": "nicht instrumentiert"},
    ]
    dienste = [{"name": a["name"], "aktiv": a["stand"] == "eingerichtet", "kategorie": a["bereich"],
                "kosten": a["tarif_text"]} for a in anbieter(secrets) if a["bereich"] != "Öffentlich"]
    return {"modelle": modelle, "dienste": dienste}
