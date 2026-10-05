"""Fachagenten-Routing (FACHAGENTEN_ROUTING_ROADMAP.md, CEO 2026-10-05: „An welche Abteilung die Frage geht, muss LUNA
selbst entscheiden“).

- `ZUSTAENDIG`: je Fachagent eine Zeile „wofuer zustaendig“ (abgeleitet aus der Rolle in der Charta, A6-Stand) -- steht
  in der Beschreibung von `delegate`, damit LUNA eine Sachfrage ohne Abteilungsnamen selbst zuordnen kann (R1).
- `WERKZEUG_BEREICH`: jedes Chat-Werkzeug gehoert genau einem Bereich (Fachagent) oder „hoa“ (LUNA selbst) -- damit
  „wer wird gefragt“ auch Antworten ueber Werkzeuge zaehlt (R3).
- `geschaeftsregeln()`: Nur-Lese-Sicht auf Zahlungsbedingungen, Mahnwesen, Leistungskatalog, Projektsaetze und AGB --
  **ohne** Kunden-, Rechnungs- oder Kontodaten (Datenschutz-Entscheidung 2026-09-29) (R2).
"""
from __future__ import annotations

from .subagents import ALL_AGENT_CHARTERS

ZUSTAENDIG: dict[str, str] = {
    "berater": "Strategie, Prozesse",
    "cao": "Fristen, Dienstleister, Versicherungen, Abos",
    "cfo": "Budget, eigene Kosten, Buchhaltung, Steuer, Preise/Margen, Liquiditaet",
    "cro": "Kunden, Angebote, Kooperationen, Nachfassen",
    "ciso": "Sicherheit, Zugaenge, Datenschutz",
    "cbo": "Marke, Markenstimme",
    "cpo": "LUNA-OS-Funktionen, Roadmap",
    "cto": "Technik, Deploy, Fehler",
    "cxo": "Kundenerlebnis: Angebote/Berichte verstaendlich, Bedienbarkeit",
    "cco": "Reels, Skripte, Content-Plan, Konzepte",
    "cdo": "Kennzahlen, Reichweite, Kampagnen-Auswertung",
    "chro": "Freie Mitarbeitende (Kameraleute, Cutter): Tagessaetze, Honorare, Briefing",
    "clo": "Recht, Vertraege, AGB, Werbekennzeichnung, Urheber-/Bild-/Musikrechte",
    "cko": "Wissen, Video-/Clip-Archiv durchsuchen",
    "res": "Web-Recherche",
    "cio": "Investment (Test)",
    "risk": "Investment-Risiko",
    "vid": "Drehpraxis: Shotlist, Kamera, Licht, Ton, Equipment, Drehplan",
}

ROUTING_REGEL = (
    "ROUTING: Der CEO nennt nie eine Abteilung; bestimme selbst, wer zustaendig ist. Datenfragen per Werkzeug "
    "(Budget: 'frage_finance'; Zahlungsbedingungen/Preise/AGB: 'geschaeftsregeln'), Fach-/Rechts-/Bewertungsfragen per "
    "'delegate' an den Zustaendigen (auch Content-Ideen, Marke, Daten -- nicht selbst beantworten); noetige Zahlen vorher "
    "holen und mitgeben. Nenne kurz, wer geantwortet hat."
)


def delegate_beschreibung() -> str:
    teile = "; ".join(f"{k}={v}" for k, v in ZUSTAENDIG.items())
    return f"Fragt den zustaendigen Fachagenten (nur Beratung). an= {teile}."


# Werkzeug -> Bereich (Fachagent-Schluessel) oder "hoa" (LUNA selbst: Kalender, Mail, System, Antraege ...).
_BEREICHE: dict[str, tuple[str, ...]] = {
    "cfo": ("frage_finance", "set_budget", "finance_dashboard", "kosten_optimierung", "kosten_statistik",
            "geschaeftsregeln"),
    "cro": ("crm_dm_abrufen", "crm_dm_backfill", "crm_konversation", "crm_status_setzen", "crm_todo_erledigen",
            "crm_zeigen", "ig_analyse", "ig_postfach_sync"),
    "cdo": ("social_media_analyzer",),
    "cco": ("content_feed_lauf",),
    "cio": ("investment_backfill", "investment_modus", "investment_sammeln", "investment_scorecard",
            "investment_screen", "investment_status", "investment_vorschlaege", "insider_scan",
            "insider_signale_zeigen", "paper_konto", "paper_order", "paper_order_freigabe", "watchlist_hinzufuegen"),
    "res": ("recherche_beauftragen", "recherche_ticket", "recherche_tickets_zeigen"),
    "ciso": ("sicherheits_audit", "skill_pruefen", "sandbox_check"),
    "cto": ("systemcheck", "github_trends", "watch_tick", "antrag_umsetzen", "antrag_mergen", "antrag_pushen",
            "technische_freigabe"),
    "berater": ("innovation_scouting", "selbstentwicklung", "funde_bewerten"),
    "cko": ("brain_suchen", "brain_merken", "erfahrung_abrufen", "erfahrung_merken", "obsidian_export"),
}
WERKZEUG_BEREICH: dict[str, str] = {w: k for k, ws in _BEREICHE.items() for w in ws}


def bereich_von(werkzeug: str) -> str:
    """Bereich eines Werkzeugs; `delegate` wird ueber sein Argument `an` zugeordnet, alles Uebrige ist LUNA ("hoa")."""
    return WERKZEUG_BEREICH.get(werkzeug, "hoa")


def pruefe_vollstaendig() -> list[str]:
    """Fehlerliste (fuer Tests): Karte deckt genau die befragbaren Fachagenten ab, Bereiche sind gueltig."""
    fehler = []
    if set(ZUSTAENDIG) != set(ALL_AGENT_CHARTERS):
        fehler.append(f"ZUSTAENDIG != ALL_AGENT_CHARTERS: {sorted(set(ZUSTAENDIG) ^ set(ALL_AGENT_CHARTERS))}")
    fehler += [f"unbekannter Bereich {k}" for k in _BEREICHE if k not in ALL_AGENT_CHARTERS]
    return fehler


def _eur(cent: int) -> str:
    return f"{cent / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def geschaeftsregeln(bh, thema: str = "") -> dict:
    """Nur-Lese-Sicht auf die Geschaeftsregeln. `thema`: zahlung | mahnung | katalog | agb | "" (alles)."""
    from . import mahnungen, zahlungsbedingungen as zb
    from .katalog import Katalog
    from .projektabrechnung import katalog_saetze
    from .vertraege import VertragStore
    thema = (thema or "").strip().lower()
    out: dict = {"hinweis": "Allgemeine Regeln ohne Kunden-/Rechnungsdaten. Je Angebot koennen Zahlungsziel und "
                            "Vorkasse abweichen; Zahlungsziel je Kunde steht nur in LUNA-OS."}
    if thema in ("", "zahlung"):
        out["zahlungsbedingungen"] = {
            "zahlungsziel_standard_tage": zb.ZIEL_STANDARD,
            "vorkasse": "wird je Angebot entschieden (Prozent oder Euro-Betrag), keine Standard-Vorkasse je Kunde; "
                        "eigene Vorkasse-Rechnung, die Schlussrechnung zieht sie ab",
            "vorkasse_frist_standard_tage": zb.FRIST_STANDARD,
            "steuer": "Kleinunternehmer nach § 19 UStG -- Endpreise, keine Umsatzsteuer",
        }
    if thema in ("", "mahnung", "zahlung"):
        out["mahnwesen"] = {
            "stufen": list(mahnungen.BRIEF.values()), "frist_tage_je_mahnung": mahnungen.FRIST_TAGE,
            "verzugszins_unternehmer": f"Basiszins + {mahnungen.AUFSCHLAG_UNTERNEHMER:g} Prozentpunkte",
            "verzugszins_verbraucher": f"Basiszins + {mahnungen.AUFSCHLAG_VERBRAUCHER:g} Prozentpunkte",
            "basiszins_aktuell": f"{mahnungen.BASISZINS[-1][1]:g} % (ab {mahnungen.BASISZINS[-1][0]})",
            "pauschale_unternehmer": _eur(mahnungen.PAUSCHALE_UNTERNEHMER_CENT),
            "mahnkosten_verbraucher": _eur(mahnungen.KOSTEN_VERBRAUCHER_CENT),
        }
    if thema in ("", "katalog"):
        k = Katalog(bh)
        kat = k.laden()
        s = katalog_saetze(k)
        out["katalog"] = {
            "formate": [{"gruppe": g["name"], "name": it["name"], "preis": _eur(it["preis_cent"]),
                         **({"einheit": it["einheit"]} if it.get("einheit") else {})}
                        for g in kat["gruppen"] for it in g["items"] if it.get("aktiv", True)],
            "zuschlaege": [{"name": z["name"], "prozent": z["prozent"]} for z in kat.get("zuschlaege") or []],
            "rabatt_max_prozent": kat.get("rabatt_max"),
            "projektstunde": _eur(s["satz_cent"]) if s["satz_cent"] else "nicht im Katalog",
            "km_satz": _eur(s["km_satz_cent"]) if s["km_satz_cent"] else "nicht im Katalog",
            "fusszeile": (kat.get("texte") or {}).get("fuss", ""),
        }
    if thema in ("", "agb"):
        try:
            v = VertragStore(bh).in_kraft("agb")
        except KeyError:
            v = None
        if v:
            zahl = [p for p in v["paragraphen"] if any(w in p["titel"].lower() for w in ("zahlung", "verguetung", "preis"))]
            out["agb"] = {"titel": v.get("titel"), "version": v.get("version"), "status": "in Kraft",
                          "zahlungsparagraphen": zahl}
        else:
            out["agb"] = {"status": "keine AGB-Fassung in Kraft (Vertragswerk: Entwurf/Pruefung bei der Anwaeltin)"}
    return out
