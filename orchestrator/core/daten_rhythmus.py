"""Wiederkehrende Erinnerungen fuer die Datenlieferungen der Menschen (MONETARISIERUNG_ROADMAP.md, Etappe M6).

Quelle des Rhythmus: Skill `skills/cmo/marketing-daten-rhythmus/SKILL.md` und Monetarisierungsplan Abschnitt 11.
- **Vorlagen** werden nie automatisch angelegt: der CEO waehlt in LUNA-OS aus, welche als wiederkehrendes To-do entstehen
  (Quelle `Vorlage:<id>`, je Vorlage hoechstens eine offene Serie).
- **Teilzeit-Antrag** (Plan, Brueckenjob-Gates): Sobald eine „in Folge“-Regel eines Brueckenjob-Gates zur Haelfte erfuellt
  ist (z. B. 3 von 6 Monaten), legt der Tageslauf genau ein To-do „Teilzeit-Antrag stellen“ an -- der Antrag braucht
  3 Monate Vorlauf (Textform, § 8 / § 9a TzBfG).
"""
from __future__ import annotations

import math
from datetime import date, timedelta

VORLAGEN = [
    {"id": "reichweite", "titel": "Reichweiten der Woche sichern (Facebook, TikTok, YouTube)", "wiederholung": "woechentlich",
     "wann": "montags",
     "notiz": "Instagram holt LUNA montags selbst. Facebook: Business Suite → Insights → Exportieren (CSV); TikTok Studio "
              "und YouTube Studio: Export (CSV). In LUNA-OS → Content & Collabs → Reichweiten → „CSV importieren“ "
              "oder Werte von Hand eintragen."},
    {"id": "abrechnungen", "titel": "Auszahlungen und Abrechnungen des Vormonats erfassen", "wiederholung": "monatlich",
     "wann": "am 5. jedes Monats",
     "notiz": "Facebook, YouTube, TikTok, Affiliates (Hands of God, Fantastic Frames), App Store Connect und Google Play "
              "Console: PDF/CSV in LUNA-OS als Beleg hochladen und der Säule zuordnen."},
    {"id": "stunden", "titel": "Stunden je Säule für den Vormonat eintragen", "wiederholung": "monatlich",
     "wann": "am 3. jedes Monats",
     "notiz": "LUNA-OS → Finanzen → Säulen → „Stunden ohne Auftrag“: geschätzte Stunden je Person und Säule "
              "(eigene Kanäle, App, Merch). Zeiten an Kundenaufträgen zählen automatisch."},
    {"id": "quartal", "titel": "Quartals-Check: Zielgruppe, Rücklage, Preisliste, Plan-Werte", "wiederholung": "quartalsweise",
     "wann": "am 5. Januar, April, Juli, Oktober",
     "notiz": "Zielgruppen-Demografie je Plattform, Media-Kit-Werte, Rücklage, Ersatzbedarf E und Netto-Lücke L "
              "(Finanzen → Plan bearbeiten), Preisliste prüfen."},
]


def erster_termin(vid: str, heute: date) -> date:
    """Erste Faelligkeit einer Vorlage ab heute (heute zaehlt mit)."""
    if vid == "reichweite":                                  # naechster Montag
        return heute + timedelta(days=(7 - heute.weekday()) % 7)
    tag = {"abrechnungen": 5, "stunden": 3, "quartal": 5}[vid]
    j, m = heute.year, heute.month
    while True:
        if (vid != "quartal" or m in (1, 4, 7, 10)) and date(j, m, tag) >= heute:
            return date(j, m, tag)
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def vorlagen(store) -> list[dict]:
    """Vorlagen mit Stand: `aktiv` = es gibt eine offene Serie aus dieser Vorlage."""
    offen = {a.get("quelle") for g, liste in store.liste(mit_erledigt=False).items() for a in liste}
    return [v | {"aktiv": f"Vorlage:{v['id']}" in offen} for v in VORLAGEN]


def vorlagen_anlegen(store, ids: list[str], heute: date, *, von: str = "") -> list[dict]:
    """Gewaehlte Vorlagen als wiederkehrende To-dos anlegen (bereits aktive werden uebersprungen)."""
    stand = {v["id"]: v for v in vorlagen(store)}
    unbekannt = [i for i in ids if i not in stand]
    if unbekannt or not ids:
        raise ValueError("Bitte mindestens eine bekannte Vorlage wählen.")
    neu = []
    for i in ids:
        v = stand[i]
        if v["aktiv"]:
            continue
        neu.append(store.anlegen(v["titel"], faellig=erster_termin(i, heute).isoformat(), notiz=v["notiz"],
                                 quelle=f"Vorlage:{i}", von=von, wiederholung=v["wiederholung"]))
    return neu


def teilzeit_vorlauf(auswertung: dict) -> list[dict]:
    """Brueckenjob-Gates, deren „in Folge“-Regel mindestens zur Haelfte steht (und noch nicht erfuellt ist)."""
    out = []
    for g in auswertung.get("gates") or []:
        if g.get("erreicht") or "brückenjob" not in (g.get("name") or "").lower():
            continue
        for r in g.get("regeln_stand") or []:
            n = r["regel"]["monate"]
            if r["regel"]["art"] == "in_folge" and not r["erfuellt"] and r["ist"] >= math.ceil(n / 2):
                out.append({"gate": g["code"], "name": g["name"], "stand": r["ist"], "von": n})
                break
    return out


def teilzeit_erinnern(store, auswertung: dict, heute: date, *, von: str = "LUNA") -> list[dict]:
    """Je Brueckenjob-Gate genau einmal ein To-do „Teilzeit-Antrag stellen“ (Quelle `Plan:<Gate>:teilzeit`)."""
    schon = {a.get("quelle") for liste in store.liste().values() for a in liste}
    neu = []
    for v in teilzeit_vorlauf(auswertung):
        q = f"Plan:{v['gate']}:teilzeit"
        if q in schon:
            continue
        neu.append(store.anlegen(
            f"Teilzeit-Antrag vorbereiten ({v['gate']} {v['name']})", faellig=(heute + timedelta(days=7)).isoformat(),
            notiz=(f"{v['gate']} ist {v['stand']} von {v['von']} Monaten auf Kurs. Der Antrag auf Teilzeit bzw. "
                   "Brückenteilzeit muss spätestens 3 Monate vor Beginn in Textform beim Arbeitgeber sein (§ 8 / § 9a "
                   "TzBfG). Vorher: Arbeitsvertrag (Nebentätigkeit, Wettbewerbsverbot) prüfen, Krankenkasse informieren."),
            quelle=q, von=von))
    return neu
