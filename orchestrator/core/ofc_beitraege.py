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
            h.append("Gold ohne Beitrag in den Mitgliederdaten – 40 € angenommen")
        else:
            jahres = b
            if b != GOLD_CENT:
                h.append(f"Gold mit {_euro(b)} in den Mitgliederdaten (statt 40 €)")
    elif a == "standard":
        jahres = 0
        if b:
            h.append(f"Kostenfrei, aber {_euro(b)} in den Mitgliederdaten")
    elif a == "foerder":
        jahres = b or 0
        if not b:
            h.append("Förderbetrag fehlt in den Mitgliederdaten" + (f" – Kommentar: „{p['kommentar'][:80]}“" if p.get("kommentar") else ""))
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
    liste = [soll(p, jahr) for p in daten.get("mitglieder", [])        # OFC_MITGLIEDER E4: kein Soll nach dem Kuendigungsjahr
             if not (str(p.get("gekuendigt_am") or "")[:4].isdigit() and int(str(p["gekuendigt_am"])[:4]) < jahr)]
    je_art = {k: sum(1 for x in liste if x["art"] == k) for k in ARTEN}
    hinweise = list(daten.get("hinweise") or [])
    if (n := sum(1 for x in liste if x["hinweise"])):
        hinweise.append(f"{n} Mitglied(er) mit Hinweis – bitte beim Mitglied prüfen")
    gold_ohne = sum(1 for x in liste if x["art"] == "gold" and not x["naechste_zahlung"])
    return {"ok": True, "jahr": jahr, "mitglieder": liste, "hinweise": hinweise,
            "summen": {"mitglieder": len(liste), **je_art, "beitragspflichtig": sum(1 for x in liste if x["soll_cent"]),
                       "soll_cent": sum(x["soll_cent"] for x in liste), "anteilig": sum(1 for x in liste if x["anteilig"]),
                       "gold_ohne_naechste_zahlung": gold_ohne},
            "gelesen": daten.get("gelesen", ""), "blatt": daten.get("blatt", "")}


# -- KA1: Beitragszahlungen erkennen ----------------------------------------------------------------------------------
# E-K4 (CEO 2026-11-24, wie empfohlen): automatisch, wenn der Name des Zahlers zu einem Mitglied passt (oder ein gelernter
# Alias, z. B. Familie) und der Betrag genau den offenen Beitraegen entspricht (ein oder mehrere Jahre, mehrere Mitglieder)
# -- und kein Ticket passt oder die Mitteilung den Beitrag nennt. Sonst Vorschlag; per Klick Mitglied/Jahr waehlen.
START_STANDARD = 2027               # erstes erfasstes Beitragsjahr (aeltere Beitraege liefen vor LUNA)
MAX_JAHRE = 3
BEITRAG_WORT = re.compile(r"beitrag|mitglied|gold|jahresbeitrag", re.I)


def start_jahr(st: dict) -> int:
    import os
    w = (st.get("einstellungen") or {}).get("beitrag_ab") or os.environ.get("OFC_BEITRAG_AB") or START_STANDARD
    try:
        return int(w)
    except (TypeError, ValueError):
        return START_STANDARD


def _mitglieder(daten: dict | None) -> list[dict]:
    return list((daten or {}).get("mitglieder") or []) if (daten or {}).get("ok") else []


def bezahlt_je_jahr(st: dict) -> dict[str, dict]:
    """"nummer|jahr" -> {cent, zahlungen: [{id, datum, name, cent}]} aus zugeordneten Beitrags-Eingaengen."""
    out: dict = {}
    for e in st.get("eingaenge", {}).values():
        if e.get("art") != "beitrag" or e.get("zuordnung") not in ("auto", "manuell") or e.get("ersetzt"):
            continue
        for b in e.get("beitrag") or []:
            x = out.setdefault(f"{b['nummer']}|{b['jahr']}", {"cent": 0, "zahlungen": []})
            x["cent"] += int(b.get("cent") or 0)
            x["zahlungen"].append({"id": e["id"], "datum": e.get("datum", ""), "name": e.get("name", ""), "cent": int(b.get("cent") or 0)})
    return out


def offene_beitraege(st: dict, daten: dict | None, bis_jahr: int) -> dict[str, int]:
    """"nummer|jahr" -> offener Betrag fuer alle erfassten Jahre (ab Startjahr) bis `bis_jahr`."""
    bz = bezahlt_je_jahr(st)
    status = st.get("beitrag_status") or {}
    out: dict = {}
    for p in _mitglieder(daten):
        if not p.get("nummer"):
            continue
        for j in range(start_jahr(st), bis_jahr + 1):
            k = f"{p['nummer']}|{j}"
            if (status.get(k) or {}).get("status") in ("bezahlt", "erlassen"):
                continue
            s = soll(p, j)["soll_cent"]
            rest = s - (bz.get(k) or {}).get("cent", 0)
            if rest > 0:
                out[k] = rest
    return out


def _name_passt_mitglied(p: dict, zahler: set[str]) -> bool:
    from .ofc_eingang import _falten, _woerter
    w = _woerter(_falten(p.get("name") or ""))
    return len(w) >= 2 and w <= zahler


def beitrag_vorschlag(z: dict, st: dict, daten: dict | None, offen_b: dict[str, int]) -> dict | None:
    """Eingang -> {auto: [{nummer, name, jahr, cent}] | None, vorschlaege: [...]} oder None (kein Mitglied erkennbar)."""
    from .ofc_eingang import _falten, _norm, _woerter
    ms = _mitglieder(daten)
    if not ms or z.get("betrag_cent", 0) <= 0:
        return None
    zahler = _woerter(_falten(z.get("name") or ""))
    alias = set((st.get("beitrag_aliase") or {}).get(_norm(z.get("name") or ""), []))
    kand = [p for p in ms if p.get("nummer") and (_name_passt_mitglied(p, zahler) or p["nummer"] in alias)]
    seen, kandidaten = set(), []
    for p in kand:
        if p["nummer"] not in seen:
            seen.add(p["nummer"])
            kandidaten.append(p)
    if not kandidaten:
        return None
    wort = bool(BEITRAG_WORT.search(z.get("mitteilung") or ""))

    def offen_jahre(p):
        return sorted((int(k.split("|")[1]), c) for k, c in offen_b.items() if k.split("|")[0] == p["nummer"])

    treffer = []
    for p in kandidaten:                                         # ein Mitglied, ein oder mehrere Jahre (aelteste zuerst)
        js = offen_jahre(p)[:MAX_JAHRE]
        for n in range(1, len(js) + 1):
            if sum(c for _, c in js[:n]) == z["betrag_cent"]:
                treffer.append([{"nummer": p["nummer"], "name": p.get("name", ""), "jahr": j, "cent": c} for j, c in js[:n]])
                break
    if len(kandidaten) > 1:                                      # Familie: je Mitglied das aelteste offene Jahr
        ersten = [(p, offen_jahre(p)[0]) for p in kandidaten if offen_jahre(p)]
        if len(ersten) > 1 and sum(c for _, (_, c) in ersten) == z["betrag_cent"]:
            treffer.append([{"nummer": p["nummer"], "name": p.get("name", ""), "jahr": j, "cent": c} for p, (j, c) in ersten])
    namen_doppelt = len({_norm(p.get("name") or "") for p in kandidaten}) < len(kandidaten) and not alias
    gruende = ["Name passt"] + (["Mitteilung nennt Beitrag"] if wort else [])
    vorschlaege = [{"art": "beitrag", "beitrag": t, "summe": sum(b["cent"] for b in t), "gruende": gruende + ["Betrag passt"]}
                   for t in treffer]
    if not treffer:
        for p in kandidaten:
            js = offen_jahre(p)
            if js:
                vorschlaege.append({"art": "beitrag", "beitrag": [{"nummer": p["nummer"], "name": p.get("name", ""),
                                                                   "jahr": js[0][0], "cent": min(js[0][1], z["betrag_cent"])}],
                                    "summe": min(js[0][1], z["betrag_cent"]), "gruende": gruende})
    auto = treffer[0] if len(treffer) == 1 and not namen_doppelt else None
    return {"auto": auto, "vorschlaege": vorschlaege[:4], "wort": wort}


def beitrag_text(items: list[dict]) -> str:
    jahre = sorted({b["jahr"] for b in items})
    return "Beitrag " + ", ".join(str(j) for j in jahre) + (f" ({len({b['nummer'] for b in items})} Mitglieder)" if len({b["nummer"] for b in items}) > 1 else "")


# -- KA2: Beitragsuebersicht, offene Beitraege, Klick-Aktionen, Export ------------------------------------------------
UEBERFAELLIG_TAGE = 28              # Hinweis im Reiter ab 4 Wochen nach Faelligkeit
STATUS = ("bezahlt", "erlassen", "offen")


def jahr_stand(st: dict, daten: dict | None, jahr: int, heute: date | None = None) -> dict:
    """Soll / bezahlt / offen je Mitglied im Beitragsjahr, mit Zahlungen, Status, Hinweis „ueberfaellig“ und Text zum
    Kopieren. Jahre vor dem Startjahr gelten als „nicht erfasst“ (liefen vor LUNA)."""
    heute = heute or date.today()
    basis = beitraege(daten, jahr)
    if not basis.get("ok"):
        return basis
    erfasst = jahr >= start_jahr(st)
    bz = bezahlt_je_jahr(st)
    status = st.get("beitrag_status") or {}
    s = {"soll_cent": 0, "bezahlt_cent": 0, "offen_cent": 0, "offen": 0, "bezahlt": 0, "teilweise": 0, "erlassen": 0,
         "ueberfaellig": 0}
    for m in basis["mitglieder"]:
        k = f"{m['nummer']}|{jahr}"
        x = bz.get(k) or {"cent": 0, "zahlungen": []}
        st_hand = (status.get(k) or {}).get("status", "")
        m.update(bezahlt_cent=x["cent"], zahlungen=x["zahlungen"], status_hand=st_hand)
        if not m["soll_cent"]:
            m.update(status="frei", offen_cent=0)
        elif not erfasst:
            m.update(status="nicht_erfasst", offen_cent=0)
        elif st_hand == "erlassen":
            m.update(status="erlassen", offen_cent=0)
        elif st_hand == "bezahlt" or x["cent"] >= m["soll_cent"]:
            m.update(status="bezahlt", offen_cent=0)
        else:
            m.update(status="teilweise" if x["cent"] else "offen", offen_cent=m["soll_cent"] - x["cent"])
        f = date.fromisoformat(m["faellig"]) if m.get("faellig") else None
        m["ueberfaellig"] = bool(m["offen_cent"] and f and (heute - f).days > UEBERFAELLIG_TAGE)
        m["text"] = _erinnerung(m, jahr) if m["offen_cent"] else ""
        if m["soll_cent"] and erfasst:
            s["soll_cent"] += 0 if m["status"] == "erlassen" else m["soll_cent"]
            s["bezahlt_cent"] += m["soll_cent"] if m["status"] == "bezahlt" else (x["cent"] if m["status"] != "erlassen" else 0)
            s["offen_cent"] += m["offen_cent"]
            s[m["status"]] = s.get(m["status"], 0) + 1
            s["ueberfaellig"] += m["ueberfaellig"]
    s["quote"] = round(100 * s["bezahlt"] / max(s["bezahlt"] + s["offen"] + s["teilweise"], 1))
    return basis | {"erfasst": erfasst, "start_jahr": start_jahr(st), "stand": s}


def _erinnerung(m: dict, jahr: int) -> str:
    vor = (m.get("name") or "").split(" ")[0] or "zusammen"
    return (f"Hallo {vor}, kleine Erinnerung: Dein HSVInside-Beitrag {jahr} ({ARTEN.get(m['art'], '')}-Mitgliedschaft) über "
            f"{_euro(m['offen_cent'])} ist noch offen. Magst du ihn wie gewohnt per PayPal schicken? Danke dir und nur der HSV!")


def beitrag_setzen(store, nummer: str, jahr: int, status: str, *, daten: dict | None = None, von: str = "") -> dict:
    """Per Klick: „bezahlt“ (z. B. vor der Erfassung oder ausserhalb von PayPal), „erlassen“ oder zuruecksetzen („offen“)."""
    if status not in STATUS:
        return {"ok": False, "hinweis": "Status unbekannt."}
    if not 2000 <= int(jahr or 0) <= 2100:
        return {"ok": False, "hinweis": "Jahr ungültig."}
    if daten is not None and nummer not in {p.get("nummer") for p in _mitglieder(daten)}:
        return {"ok": False, "hinweis": "Mitglied nicht gefunden."}
    store.erfassen("ofc_beitrag", {"nummer": str(nummer), "jahr": int(jahr), "status": status}, von=von)
    return {"ok": True, "nummer": str(nummer), "jahr": int(jahr), "status": status}


def beitrag_hinweis(st: dict, daten: dict | None, heute: date | None = None) -> dict:
    """Fuer den Reiter: ueberfaellige Beitraege des laufenden Jahres (E8: nur Hinweis, keine Nachricht)."""
    heute = heute or date.today()
    j = jahr_stand(st, daten, heute.year, heute)
    if not j.get("ok") or not j["erfasst"]:
        return {"ok": bool(j.get("ok")), "jahr": heute.year, "ueberfaellig": 0, "offen_cent": 0}
    return {"ok": True, "jahr": heute.year, "ueberfaellig": j["stand"]["ueberfaellig"], "offen_cent": j["stand"]["offen_cent"]}


_STATUS_TEXT = {"bezahlt": "bezahlt", "teilweise": "teilweise", "offen": "offen", "erlassen": "erlassen", "frei": "kostenfrei",
                "nicht_erfasst": "nicht erfasst"}


def export_csv(j: dict) -> bytes:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Jahr", "Nummer", "Name", "Mitgliedschaft", "Mitglied seit", "Faellig", "Soll", "Bezahlt", "Offen", "Status",
                "Zahlungen", "Hinweise"])
    for m in j.get("mitglieder", []):
        w.writerow([j["jahr"], m["nummer"], m["name"], m["art_text"], m["seit"], m["faellig"], _euro(m["soll_cent"]),
                    _euro(m.get("bezahlt_cent", 0)), _euro(m.get("offen_cent", 0)), _STATUS_TEXT.get(m.get("status"), ""),
                    ", ".join(f"{z['datum']} {_euro(z['cent'])}" for z in m.get("zahlungen") or []), " | ".join(m["hinweise"])])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def export_pdf(j: dict) -> bytes:
    from .ofc_pdf import bericht_pdf
    s = j["stand"]
    pflichtig = [m for m in j["mitglieder"] if m["soll_cent"]]
    return bericht_pdf(
        f"HSVInside – Beiträge {j['jahr']}",
        [("Soll", _euro(s["soll_cent"])), ("Bezahlt", _euro(s["bezahlt_cent"])), ("Offen", _euro(s["offen_cent"])),
         ("Quote", f"{s['quote']} %")],
        [("Offene Beiträge", [("Nr.", 14), ("Name", 0), ("Fällig", 22), ("Soll", 22), ("Offen", 22)],
          [[m["nummer"], m["name"], _tag(m["faellig"]), _euro(m["soll_cent"]), _euro(m["offen_cent"])]
           for m in pflichtig if m.get("offen_cent")]),
         ("Alle beitragspflichtigen Mitglieder", [("Nr.", 14), ("Name", 0), ("Art", 20), ("Soll", 22), ("Bezahlt", 22), ("Status", 24)],
          [[m["nummer"], m["name"], m["art_text"], _euro(m["soll_cent"]), _euro(m.get("bezahlt_cent", 0)),
            _STATUS_TEXT.get(m.get("status"), "")] for m in pflichtig])],
        text=(f"{len(pflichtig)} beitragspflichtige Mitglieder · bezahlt {s['bezahlt']} · teilweise {s['teilweise']} · offen "
              f"{s['offen']} · erlassen {s['erlassen']}" + ("" if j["erfasst"] else " · Jahr vor der Erfassung durch LUNA")),
        fuss="Quelle: Mitgliederliste (nur lesend) und PayPal-Eingänge im Fanclub-Postfach. Kein Steuer- oder Rechtsdokument.")


def _tag(iso: str) -> str:
    try:
        return date.fromisoformat(iso[:10]).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return ""
