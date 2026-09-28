"""Kalender-Erinnerungen aufraeumen, die sich erledigt haben (CEO 2026-09-28).

LUNA legt beim Versand Erinnerungen in ihrem Kalender an: Angebot nachfassen / laeuft ab, Rechnung faellig.
Sobald der Vorgang erledigt ist, loescht LUNA die **noch kommenden** davon selbststaendig:

- Angebot angenommen (Auftrag) oder abgelehnt -> Nachfass- und Ablauf-Termine weg,
- Rechnung bezahlt oder storniert -> Faelligkeits-Termin weg,
- Angebot als „nachgefasst“ markiert (Hauptseite) -> Nachfass-Termin weg (auch wenn er heute/vorbei ist),
- Beleg in Fremdwaehrung gebucht (Euro-Betrag eingetragen) oder verworfen -> „Euro-Betrag eintragen“ weg.

Geloescht werden **nur Termine, die LUNA selbst angelegt und im Kassenbuch mit ID protokolliert hat** -- nie fremde
Eintraege. Vergangene Termine bleiben als Historie stehen. Jede Loeschung wird protokolliert
(`kalender_erinnerung_entfernt`); ein bereits von Hand geloeschter Termin (404/410) gilt als erledigt.
Laeuft sofort beim Statuswechsel (LUNA-OS) und als Nachholer im 15-Minuten-Abruf des Bots.
"""
from __future__ import annotations

from .angebote import AngebotStore
from .buchhaltung import Buchhaltung, jetzt
from .eingangsbelege import EingangStore
from .rechnungen import RechnungStore

TYP = "kalender_erinnerung_entfernt"
ANGEBOT_ERLEDIGT = ("angenommen", "abgelehnt")
RECHNUNG_ERLEDIGT = ("bezahlt", "storniert")


def faellige_loeschungen(eintraege: list[dict], heute: str | None = None) -> list[dict]:
    """-> [{bezug, id, datum, titel, grund}] -- kommende LUNA-Termine zu erledigten Vorgaengen, noch nicht entfernt."""
    heute = heute or jetzt().date().isoformat()
    weg = {e["daten"].get("id") for e in eintraege if e["typ"] == TYP}
    out = []
    for a in AngebotStore._falte(eintraege).values():
        if a.get("status") == "versendet" and a.get("nachgefasst_am"):   # Hauptseite: nachgefasst -> auch heute/vergangen
            for t in a.get("versendet_termine") or []:
                if "nachfassen" in str(t.get("titel", "")):
                    out.append({"bezug": a["nummer"], "id": t.get("id", ""), "datum": t.get("datum", ""),
                                "titel": t.get("titel", ""), "grund": "nachgefasst", "auch_vergangen": True})
        if a.get("status") in ANGEBOT_ERLEDIGT:
            for t in a.get("versendet_termine") or []:
                out.append({"bezug": a["nummer"], "id": t.get("id", ""), "datum": t.get("datum", ""),
                            "titel": t.get("titel", ""), "grund": f"Angebot {a['status']}"})
    for r in RechnungStore._falte(eintraege)[1].values():
        t = r.get("erinnerung") or {}
        if r.get("status") in RECHNUNG_ERLEDIGT and t:
            out.append({"bezug": r["nummer"], "id": t.get("id", ""), "datum": t.get("datum", ""),
                        "titel": f"Rechnung {r['nummer']} fällig", "grund": f"Rechnung {r['status']}"})
    for b in EingangStore._falte(eintraege).values():               # Fremdwaehrung: Euro-Betrag ist eingetragen
        t = b.get("erinnerung") or {}
        if t and b.get("status") != "zu_pruefen":
            out.append({"bezug": b["nummer"], "id": t.get("id", ""), "datum": t.get("datum", ""),
                        "titel": t.get("titel", ""), "grund": f"Beleg {b['status']}"})
    return [{k: v for k, v in x.items() if k != "auch_vergangen"} for x in out
            if x["id"] and x["id"] not in weg and (x.get("auch_vergangen") or str(x["datum"]) >= heute)]


def erledigte_entfernen(bh: Buchhaltung, google, *, von: str = "LUNA") -> list[dict]:
    """Kommende Erinnerungen erledigter Vorgaenge aus LUNAs Kalender loeschen. Rueckgabe: entfernte Termine."""
    if google is None or not google.verfuegbar():
        return []
    entfernt = []
    for x in faellige_loeschungen(bh.eintraege()):
        r = google.termin_loeschen(x["id"], bestaetigt=True)          # eigener, protokollierter LUNA-Termin (CEO-Auftrag)
        schon_weg = any(c in str(r.get("hinweis") or "") for c in ("404", "410", "deleted", "Not Found"))
        if not (r.get("ok") or schon_weg):
            continue                                                  # naechster Abruf versucht es erneut
        bh.erfassen(TYP, {k: x[k] for k in ("bezug", "id", "datum", "titel", "grund")}
                    | {"schon_geloescht": bool(schon_weg and not r.get("ok"))}, von=von)
        entfernt.append(x)
    return entfernt
