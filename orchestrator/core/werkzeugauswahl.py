"""Werkzeugauswahl (WERKZEUGAUSWAHL_ROADMAP.md) -- nur passende Werkzeuge je Nachricht, ohne LLM-Aufruf.

Statt aller ~97 Werkzeuge (~12.000 Token) sieht das Modell ein kleines KERN-Set plus die Themengruppen, deren
Stichwoerter in der CEO-Nachricht vorkommen (bzw. die im Gespraech schon genutzt wurden). Die Auswahl betrifft nur,
was das Modell SIEHT -- ausgefuehrt wird weiter jedes Werkzeug ueber `run_tool`, mit unveraenderten Rechten/CEO-Toren.

Pflege: Jedes Werkzeug aus `hoa_tools.tool_specs()` gehoert GENAU EINER Gruppe (oder dem Kern) an. Ein neues Werkzeug
ohne Gruppe laesst `test_werkzeugauswahl` rot werden. Stichwoerter werden am Wortanfang gesucht (\\b<stichwort>),
nach Normalisierung (klein, ae/oe/ue/ss).
"""
from __future__ import annotations

import json
import re

# Immer dabei: Ueberblick, Delegation, Meldungen, Gedaechtnis, Recherche-Auftrag, Antrags-Grundfunktionen.
KERN = [
    "lagebild", "delegate", "melde_an_ceo", "meldung_details", "brain_suchen", "brain_merken",
    "recherche_beauftragen", "offene_tickets", "antraege_zeigen", "antrag_details", "antrag_stellen",
    "notiz_hinzufuegen", "werkzeuge_laden",
]

GRUPPEN: dict[str, dict[str, list[str]]] = {
    "antraege": {
        "werkzeuge": ["antrag_ablehnen", "antrag_freigeben", "antrag_mergen", "antrag_pushen", "antrag_revidieren",
                      "antrag_umsetzen", "antraege_neu_formatieren", "technische_freigabe", "abteilung_tickets",
                      "selbstentwicklung"],
        "stichwoerter": ["antrag", "antraeg", "freigeb", "freigab", "genehmig", "ablehn", "merg", "push", "umsetz",
                         "revid", "ueberarbeit", "formatier", "selbstentwickl", "verbesserungsvorschlag", "archiv",
                         "geschlossen", "ticket", "technische freigabe", "branch", "pull request"],
    },
    "investment": {
        "werkzeuge": ["investment_backfill", "investment_modus", "investment_sammeln", "investment_scorecard",
                      "investment_screen", "investment_status", "investment_vorschlaege", "insider_scan",
                      "insider_signale_zeigen", "paper_konto", "paper_order", "paper_order_freigabe",
                      "watchlist_hinzufuegen"],
        "stichwoerter": ["invest", "aktie", "depot", "kurs", "krypto", "bitcoin", "btc", "ethereum", "etf", "boerse",
                         "trade", "trading", "kauf", "verkauf", "order", "paper", "alpaca", "watchlist", "insider",
                         "sec", "prognose", "scorecard", "trefferquote", "screen", "portfolio", "position", "backtest",
                         "backfill", "cio", "rendite", "apple", "aapl", "nvidia", "tesla", "usd", "dollar"],
    },
    "crm_social": {
        "werkzeuge": ["crm_dm_abrufen", "crm_dm_backfill", "crm_konversation", "crm_status_setzen",
                      "crm_todo_erledigen", "crm_zeigen", "ig_analyse", "ig_postfach_sync", "social_media_analyzer",
                      "content_feed_lauf"],
        "stichwoerter": ["crm", "collab", "kooperation", "instagram", "insta", "ig", "dm", "direktnachricht",
                         "social", "follower", "reichweite", "insights", "content", "reel", "hashtag", "caption",
                         "firma", "firmen", "pipeline", "marke", "partner", "sponsor", "radar", "influencer",
                         "beitrag", "beitraege", "posting", "to-do", "todo"],
    },
    "mail": {
        "werkzeuge": ["mail_entwurf", "mail_lesen", "mail_markieren", "mail_senden", "mail_suchen", "posteingang"],
        "stichwoerter": ["mail", "e-mail", "email", "posteingang", "postfach", "gmail", "entwurf", "ungelesen",
                         "gelesen", "absender", "anschreiben", "schreib", "antworte", "nachricht von", "newsletter"],
    },
    "kalender": {
        "werkzeuge": ["kalender_agenda", "kalender_kollisionen", "termin_aendern", "termin_anlegen", "termin_loeschen",
                      "agenda_zeigen", "briefing_jetzt"],
        "stichwoerter": ["kalender", "termin", "meeting", "besprechung", "agenda", "heute", "morgen", "uebermorgen",
                         "woche", "uhr", "verschieb", "absag", "einlad", "kollision", "ueberschneid", "briefing",
                         "tagesplan", "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
                         "wann", "call", "telefonat"],
    },
    "dokumente": {
        "werkzeuge": ["drive_anlegen", "drive_lesen", "drive_suchen", "tabelle_lesen", "tabelle_schreiben",
                      "obsidian_export", "xmind_lesen", "xmind_bearbeiten", "visualisiere"],
        "stichwoerter": ["drive", "dokument", "datei", "doc", "sheet", "tabelle", "excel", "xmind", "mindmap",
                         "obsidian", "vault", "organigramm", "diagramm", "grafik", "chart", "visualis", "zeichne",
                         "schaubild", "balken", "ablage", "ordner"],
    },
    "recherche": {
        "werkzeuge": ["recherche_ticket", "recherche_tickets_zeigen", "watch_digest", "watch_tick", "github_trends",
                      "innovation_scouting", "funde_bewerten", "dept_briefing", "wissensstand"],
        "stichwoerter": ["recherch", "research", "web", "internet", "news", "neuigkeit", "trend", "github", "repo",
                         "open source", "open-source", "tool", "innovation", "idee", "funde", "fund", "wissensstand",
                         "watch", "beobacht", "konkurrenz", "wettbewerb", "studie", "quelle", "fachbereich",
                         "was gibt es neues", "ki-agent"],
    },
    "rechner": {
        "werkzeuge": ["rechner_aktion", "rechner_ziel", "bildschirm_sehen", "apps_kennen", "steuerung_modus"],
        "stichwoerter": ["rechner", "computer", "pc", "mac", "bildschirm", "app", "apps", "programm", "oeffne",
                         "starte", "klick", "fenster", "steuerungsmodus", "iron", "orb", "maus", "tastatur",
                         "installiert", "browser", "spotify", "finder"],
    },
    "system": {
        "werkzeuge": ["systemcheck", "sicherheits_audit", "skill_pruefen", "skills_der_abteilung", "sandbox_check",
                      "autonomie_pausieren", "autonomie_status", "aktivitaet_protokoll", "benachrichtigungen_zeigen"],
        "stichwoerter": ["system", "laeuft", "sicherheit", "security", "audit", "ciso", "skill", "sandbox",
                         "autonomie", "autonom", "pausier", "notbremse", "stopp", "aktivitaet", "protokoll", "log",
                         "benachrichtigung", "outbox", "fehler", "kaputt", "funktioniert", "check", "gesund",
                         "watcher", "hintergrund", "wer hat", "was hast du", "was habt ihr"],
    },
    "finanzen": {
        "werkzeuge": ["finance_dashboard", "frage_finance", "kosten_optimierung", "kosten_statistik", "set_budget"],
        "stichwoerter": ["budget", "kosten", "geld", "euro", "eur", "ausgabe", "rechnung", "abo", "cfo", "finanz",
                         "token", "sparen", "guenstig", "preis", "teuer", "dienstleister", "modelle", "provider"],
    },
    "gedaechtnis": {
        "werkzeuge": ["erfahrung_abrufen", "erfahrung_merken"],
        "stichwoerter": ["erfahrung", "wie haben wir", "frueher", "letztes mal", "bewaehrt", "gelernt", "lernen",
                         "trajektor", "wie sind wir", "schon mal"],
    },
}

_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})
_MUSTER = {g: re.compile("|".join(r"\b" + re.escape(s) for s in d["stichwoerter"])) for g, d in GRUPPEN.items()}


def normalisiere(text: str) -> str:
    return (text or "").translate(_UMLAUTE).lower()


def gruppen_fuer(text: str) -> set[str]:
    """Themengruppen, deren Stichwoerter in `text` vorkommen."""
    t = normalisiere(text)
    return {g for g, muster in _MUSTER.items() if muster.search(t)}


def gruppe_von(werkzeug: str) -> str | None:
    if werkzeug in KERN:
        return "kern"
    return next((g for g, d in GRUPPEN.items() if werkzeug in d["werkzeuge"]), None)


def auswahl(text: str, bisherige_gruppen: set[str] | frozenset = frozenset()) -> tuple[list[str], set[str]]:
    """(Werkzeugnamen, Gruppen) fuer eine CEO-Nachricht. Bereits genutzte Gruppen bleiben geladen."""
    gruppen = gruppen_fuer(text) | set(bisherige_gruppen)
    namen = list(KERN)
    for g in sorted(gruppen):
        namen += [w for w in GRUPPEN[g]["werkzeuge"] if w not in namen]
    return namen, gruppen


def filtere(specs: list[dict], namen: list[str]) -> list[dict]:
    """Werkzeug-Definitionen auf `namen` einschraenken (Reihenfolge wie in `specs`)."""
    erlaubt = set(namen)
    return [s for s in specs if s["name"] in erlaubt]


def token_schaetzung(specs: list[dict]) -> int:
    return int(len(json.dumps(specs, ensure_ascii=False)) / 3.5)
