"""OFC_ROADMAP OM: Mitgliederliste des Fanclubs HSVInside aus der Google-Forms-Antworttabelle -- NUR LESEND.

CEO-Entscheidung 2026-11-24: Quelle ist das Blatt „Formularantworten 1“ der Tabelle „Mitgliedschaftsanfrage“
(mit LUNAs Google-Konto nur lesend geteilt). Mitglied = Zeile mit HSVInside-Mitgliedsnummer, sonst Anfrage. Alle Spalten
werden angezeigt (nur CEO).

Regeln: keine KI fuer Mitgliederdaten; nichts wird auf der NAS gespeichert (nur kurz im Speicher des Prozesses);
es werden ausschliesslich Lese-Aufrufe benutzt (Drive `files.list`, Sheets `values.get`) -- nie schreiben.
"""
from __future__ import annotations

import os
import re
import time
from collections import Counter
from datetime import datetime

TABELLE_NAME = "Mitgliedschaftsanfrage"
BLATT_STANDARD = "Formularantworten 1"
CACHE_SEKUNDEN = 300

# Schluessel -> erkennender Text im Spaltenkopf (klein geschrieben, „enthaelt“). Reihenfolge = Vorrang.
SPALTEN = [
    ("zeitstempel", "zeitstempel"),
    ("nummer", "hsvinside-mitglied"),
    ("hsv_nr", "hsv-mitgliedsnummer"),
    ("seit", "mitglied seit"),
    ("beitrag", "beitrag"),
    ("naechste_zahlung", "chste zahlung"),
    ("anrede", "ansprechen"),
    ("vorname", "vorname"),
    ("nachname", "nachname"),
    ("mitgliedschaft", "welche mitgliedschaft"),
    ("geburtstag", "geburtstag"),
    ("email", "e-mailadresse"),
    ("hsv_mitglied", "mitglied beim hsv"),
    ("anderer_fanclub", "anderen fanclub"),
    ("handy", "handynummer"),
    ("adresse", "hausnummer"),
    ("email_absender", "e-mail-adresse"),
    ("kommentar", "teile uns"),
]

_CACHE: dict = {}


def spalten_erkennen(kopf: list[str]) -> dict[str, int]:
    """Spaltenkopf -> {schluessel: index}. Jede Spalte wird hoechstens einem Schluessel zugeordnet."""
    out: dict[str, int] = {}
    belegt: set[int] = set()
    for key, muster in SPALTEN:
        for i, k in enumerate(kopf):
            if i not in belegt and muster in (k or "").strip().lower():
                out[key] = i
                belegt.add(i)
                break
    return out


def _datum(s: str) -> str:
    """„24.09.2026 18:03:11“ / „24.09.2026“ -> ISO-Datum fuer Sortierung; sonst ''."""
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    if not m:
        return ""
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
    except ValueError:
        return ""


def _schluessel_name(vor: str, nach: str) -> str:
    return re.sub(r"\s+", " ", f"{vor} {nach}".strip().lower())


def auswerten(werte: list[list]) -> dict:
    """Rohwerte des Blatts (erste Zeile = Kopf) -> Mitglieder, Anfragen, Hinweise. Reine Funktion, kein Netz."""
    if not werte:
        return {"ok": False, "hinweis": "Die Tabelle ist leer."}
    kopf = [str(k or "").strip() for k in werte[0]]
    sp = spalten_erkennen(kopf)
    fehlend = [k for k in ("nummer", "vorname", "nachname") if k not in sp]
    if fehlend:
        return {"ok": False, "hinweis": "Spalten nicht erkannt: " + ", ".join(fehlend) + ".", "spalten": kopf}
    personen = []
    for zi, roh in enumerate(werte[1:], start=2):
        z = [str(x if x is not None else "").strip() for x in roh] + [""] * (len(kopf) - len(roh))
        if not any(z):
            continue
        g = {k: z[i] for k, i in sp.items()}
        vor, nach = g.get("vorname", ""), g.get("nachname", "")
        nr = g.get("nummer", "")
        personen.append({
            "zeile": zi, "nummer": nr, "status": "mitglied" if nr else "anfrage",
            "name": re.sub(r"\s+", " ", f"{vor} {nach}").strip(), "vorname": vor, "nachname": nach,
            "mitgliedschaft": g.get("mitgliedschaft", ""), "seit": g.get("seit", ""),
            "beitrag": g.get("beitrag", ""), "naechste_zahlung": g.get("naechste_zahlung", ""),
            "kommentar": g.get("kommentar", ""),
            "email": g.get("email", "") or g.get("email_absender", ""),
            "eingang": _datum(g.get("zeitstempel", "")),
            "felder": [[kopf[i], z[i]] for i in range(len(kopf)) if kopf[i] and z[i]],
            "hinweise": [],
        })
    nrn = Counter(p["nummer"] for p in personen if p["nummer"])
    namen = Counter(_schluessel_name(p["vorname"], p["nachname"]) for p in personen)
    for p in personen:
        if p["nummer"] and nrn[p["nummer"]] > 1:
            p["hinweise"].append(f"Nummer {p['nummer']} mehrfach")
        if namen[_schluessel_name(p["vorname"], p["nachname"])] > 1:
            p["hinweise"].append("Name mehrfach")
    mitglieder = sorted((p for p in personen if p["status"] == "mitglied"),
                        key=lambda p: (p["nummer"].zfill(8), p["zeile"]))
    anfragen = sorted((p for p in personen if p["status"] == "anfrage"), key=lambda p: (p["eingang"], p["zeile"]), reverse=True)
    hinweise = []
    if (d := sum(1 for c in nrn.values() if c > 1)):
        hinweise.append(f"{d} Mitgliedsnummer(n) mehrfach vergeben")
    if (d := sum(1 for c in namen.values() if c > 1)):
        hinweise.append(f"{d} Name(n) mehrfach eingetragen")
    return {"ok": True, "spalten": kopf, "erkannt": sorted(sp), "mitglieder": mitglieder, "anfragen": anfragen,
            "hinweise": hinweise, "summe": {"mitglieder": len(mitglieder), "anfragen": len(anfragen),
                                             "zeilen": len(personen)}}


def namen_fuer_vorschlag(daten: dict) -> list[dict]:
    """Fuer O2: Mitglieder als Namensvorschlaege (Name + Nummer)."""
    return [{"name": p["name"], "nummer": p["nummer"]} for p in daten.get("mitglieder", []) if p["name"]]


def _tabelle_finden(auth) -> str:
    """ID aus `OFC_MITGLIEDER_TABELLE` oder per Drive-Suche nach der geteilten Tabelle (nur `files.list`)."""
    if (tid := os.environ.get("OFC_MITGLIEDER_TABELLE", "").strip()):
        return tid
    q = (f"name = '{TABELLE_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false")
    files = auth.service("drive", "v3").files().list(q=q, fields="files(id,name)", pageSize=5).execute().get("files", [])
    return files[0]["id"] if files else ""


def lesen(auth, *, neu: bool = False, jetzt: float | None = None) -> dict:
    """Blatt nur lesend holen und auswerten. 5 Minuten im Speicher (nichts auf Platte)."""
    jetzt = time.time() if jetzt is None else jetzt
    if not neu and _CACHE.get("t") and jetzt - _CACHE["t"] < CACHE_SEKUNDEN:
        return _CACHE["daten"]
    if not auth or not auth.verfuegbar():
        return {"ok": False, "hinweis": "Google-Zugang von LUNA ist nicht eingerichtet."}
    tid = _tabelle_finden(auth)
    if not tid:
        return {"ok": False, "hinweis": f"Tabelle „{TABELLE_NAME}“ nicht gefunden – ist sie mit LUNAs Google-Konto geteilt?"}
    blatt = os.environ.get("OFC_MITGLIEDER_BLATT", "").strip() or BLATT_STANDARD
    werte = auth.service("sheets", "v4").spreadsheets().values().get(
        spreadsheetId=tid, range=f"'{blatt}'!A1:AZ").execute().get("values", [])
    daten = auswerten(werte) | {"blatt": blatt, "gelesen": datetime.now().astimezone().isoformat(timespec="seconds")}
    if daten.get("ok"):
        _CACHE.update(t=jetzt, daten=daten)
    return daten
