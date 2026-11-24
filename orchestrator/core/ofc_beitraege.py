"""OFC_KASSE_ROADMAP KA0: Soll-Beitrag je Mitglied aus der Mitgliederliste (OM) ableiten -- nur lesend, keine KI.

CEO-Entscheidungen 2026-11-24:
- E-K1: Beitragsjahr = Kalenderjahr, faellig zum 01.01.
- E-K2: Goldmitgliedschaft kostet 40 € pro Jahr; Quelle ist die Google-Tabelle (Spalten „Beitrag“ + Mitgliedschaft), nur
  lesend. Fehlt der Betrag bei Gold, gelten 40 €. Ein abweichender Betrag in der Tabelle gilt, wird aber als Hinweis gezeigt.
- E-K3: Wer im Beitragsjahr eintritt, zahlt anteilig ab dem Beitrittsmonat (Monat mitgezaehlt), faellig am Beitrittstag.
  (Zurzeit werden keine neuen Goldmitglieder aufgenommen.)
Kostenfrei (Standard) = 0 €; Foerdermitglieder: Betrag aus der Spalte „Beitrag“ (sonst Hinweis, Kommentar nur anzeigen);
Vorstand: Betrag aus der Spalte, sonst 0 €. Nichts wird gespeichert; der Bezahlt-Status folgt in KA1/KA2.
"""
from __future__ import annotations

import re
from datetime import date

GOLD_CENT = 4000
ARTEN = {"gold": "Gold", "standard": "Kostenfrei", "foerder": "Förder", "vorstand": "Vorstand", "unbekannt": "unklar"}


def art(mitgliedschaft: str) -> str:
    """Freitext der Tabelle -> gold|standard|foerder|vorstand|unbekannt (Schreibweisen vereinheitlicht)."""
    t = (mitgliedschaft or "").casefold().replace("ö", "oe")
    if "gold" in t:
        return "gold"
    if "foerder" in t:
        return "foerder"
    if "vorstand" in t:
        return "vorstand"
    if "standard" in t or "kostenfrei" in t:
        return "standard"
    return "unbekannt"


def betrag_cent(text: str) -> int | None:
    """„40,00 €“ / „40 €“ / „1.200,50“ -> Cent; leer oder unlesbar -> None."""
    t = re.sub(r"[^\d,.\-]", "", text or "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return round(float(t) * 100)
    except ValueError:
        return None


def _datum(s: str) -> date | None:
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})", s or "")
    if not m:
        return None
    j = int(m.group(3))
    j += 2000 if j < 100 else 0
    try:
        return date(j, int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _euro(c: int) -> str:
    return f"{c / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def soll(p: dict, jahr: int) -> dict:
    """Ein Mitglied (aus OM) -> Soll im Beitragsjahr mit Faelligkeit und Hinweisen."""
    a = art(p.get("mitgliedschaft", ""))
    b = betrag_cent(p.get("beitrag", ""))
    seit = _datum(p.get("seit", ""))
    h: list[str] = []
    if a == "gold":
        if b is None:
            jahres = GOLD_CENT
            h.append("Gold ohne Beitrag in der Tabelle – 40 € angenommen")
        else:
            jahres = b
            if b != GOLD_CENT:
                h.append(f"Gold mit {_euro(b)} in der Tabelle (statt 40 €)")
    elif a == "standard":
        jahres = 0
        if b:
            h.append(f"Kostenfrei, aber {_euro(b)} in der Tabelle")
    elif a == "foerder":
        jahres = b or 0
        if not b:
            h.append("Förderbetrag fehlt in der Tabelle" + (f" – Kommentar: „{p['kommentar'][:80]}“" if p.get("kommentar") else ""))
    else:
        jahres = b or 0
        if a == "unbekannt":
            h.append("Mitgliedschaft unklar")
    if not seit and a != "standard":
        h.append("„Mitglied seit“ fehlt oder unlesbar")
    out = {"nummer": p.get("nummer", ""), "name": p.get("name", ""), "zeile": p.get("zeile"), "art": a,
           "art_text": ARTEN[a], "mitgliedschaft": p.get("mitgliedschaft", ""), "seit": seit.isoformat() if seit else "",
           "naechste_zahlung": p.get("naechste_zahlung", ""), "jahresbeitrag_cent": jahres, "soll_cent": jahres,
           "faellig": date(jahr, 1, 1).isoformat(), "anteilig": False, "hinweise": list(p.get("hinweise") or []) + h}
    if seit and seit.year > jahr:
        out.update(soll_cent=0, faellig="", hinweise=out["hinweise"] + [f"erst ab {seit.year} Mitglied"])
    elif seit and seit.year == jahr and seit.month > 1 and jahres:
        out.update(soll_cent=round(jahres * (13 - seit.month) / 12), faellig=seit.isoformat(), anteilig=True)
    return out


def beitraege(daten: dict, jahr: int | None = None) -> dict:
    """OM-Daten -> Soll aller Mitglieder im Beitragsjahr, Summen und Hinweise zur Datenqualitaet."""
    if not daten or not daten.get("ok"):
        return {"ok": False, "hinweis": (daten or {}).get("hinweis") or "Mitgliederliste nicht lesbar."}
    jahr = jahr or date.today().year
    liste = [soll(p, jahr) for p in daten.get("mitglieder", [])]
    je_art = {k: sum(1 for x in liste if x["art"] == k) for k in ARTEN}
    hinweise = list(daten.get("hinweise") or [])
    if (n := sum(1 for x in liste if x["hinweise"])):
        hinweise.append(f"{n} Mitglied(er) mit Hinweis – bitte in der Tabelle prüfen")
    gold_ohne = sum(1 for x in liste if x["art"] == "gold" and not x["naechste_zahlung"])
    return {"ok": True, "jahr": jahr, "mitglieder": liste, "hinweise": hinweise,
            "summen": {"mitglieder": len(liste), **je_art, "beitragspflichtig": sum(1 for x in liste if x["soll_cent"]),
                       "soll_cent": sum(x["soll_cent"] for x in liste), "anteilig": sum(1 for x in liste if x["anteilig"]),
                       "gold_ohne_naechste_zahlung": gold_ohne},
            "gelesen": daten.get("gelesen", ""), "blatt": daten.get("blatt", "")}
