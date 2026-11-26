"""OFC_MITGLIEDER MV0/MV1: eigenes Mitgliederverzeichnis in LUNA (CEO 2026-11-26: „weg vom Google-Formular“).

- MV0 `import_vorschau`: was aus der Google-Tabelle uebernommen wuerde, mit Konflikten (doppelte Nummern, doppelte Namen,
  unklare Mitgliedschaft) -- schreibt nichts.
- MV1 `import_anwenden`: einmaliger Import nach Bestaetigung; doppelte Nummern loest der CEO (wer behaelt sie), die anderen
  bekommen die naechste freie Nummer (E3/E5). Ereignis `ofc_verzeichnis` je Person im Fanclub-Speicher (NAS, Backup).
  Bis zum Umschalten (MV3) lesen alle OFC-Funktionen weiter die Tabelle.
- `abgleich`: Tabelle <-> LUNA je Zeile und Feld, nur Zaehlungen und Feldnamen.
Keine KI; nur der CEO sieht die Daten.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter

FELDER = ("nummer", "anrede", "vorname", "nachname", "email", "handy", "adresse", "geburtstag", "hsv_mitglied", "hsv_nr",
          "anderer_fanclub", "mitgliedschaft", "foerder_betrag", "vorstand", "beitrag", "seit", "naechste_zahlung", "kommentar",
          "anfrage_am")
MITGLIEDSCHAFTEN = {"gold": "Gold", "standard": "Standard", "foerder": "Förder"}
ABGLEICH_FELDER = ("nummer", "vorname", "nachname", "email", "mitgliedschaft")


def mitgliedschaft_aus_text(text: str) -> tuple[str, bool]:
    """Formulartext -> (gold|standard|foerder|'', vorstand). Beide Gold-Schreibweisen = gold (E2)."""
    t = (text or "").lower()
    vorstand = "vorstand" in t
    if "gold" in t:
        return "gold", vorstand
    if "standard" in t or "kostenfrei" in t:
        return "standard", vorstand
    if "förder" in t or "foerder" in t:
        return "foerder", vorstand
    return "", vorstand


def _person(p: dict) -> dict:
    """Zeile aus `ofc_mitglieder.lesen` -> Datensatz des Verzeichnisses (E1: alle Felder, aufgeraeumt)."""
    w = p.get("werte") or {}
    art, vorstand = mitgliedschaft_aus_text(w.get("mitgliedschaft") or p.get("mitgliedschaft", ""))
    d = {"nummer": (p.get("nummer") or "").strip(), "anrede": w.get("anrede", ""), "vorname": p.get("vorname", ""),
         "nachname": p.get("nachname", ""), "email": (w.get("email") or w.get("email_absender") or p.get("email") or "").strip(),
         "handy": w.get("handy", ""), "adresse": w.get("adresse", ""), "geburtstag": w.get("geburtstag", ""),
         "hsv_mitglied": w.get("hsv_mitglied", ""), "hsv_nr": w.get("hsv_nr", ""), "anderer_fanclub": w.get("anderer_fanclub", ""),
         "mitgliedschaft": art, "foerder_betrag": "", "vorstand": vorstand, "beitrag": p.get("beitrag", ""), "seit": p.get("seit", ""),
         "naechste_zahlung": p.get("naechste_zahlung", ""), "kommentar": p.get("kommentar", ""), "anfrage_am": p.get("eingang", "")}
    d["status"] = "mitglied" if d["nummer"] else "anfrage"
    d["zeile"] = p.get("zeile")
    return d


def _schluessel(d: dict) -> str:
    return re.sub(r"\s+", " ", f"{d.get('vorname', '')} {d.get('nachname', '')}".strip().casefold())


def import_vorschau(daten: dict | None, st: dict) -> dict:
    """MV0 Dry-Run: Personen aus der Tabelle, Mitgliedschaften nach E2, Konflikte. Schreibt nichts."""
    if not daten or not daten.get("ok"):
        return {"ok": False, "hinweis": "Mitgliederliste nicht lesbar."}
    personen = [_person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])]
    nrn = Counter(p["nummer"] for p in personen if p["nummer"])
    doppelt = {n: [{"zeile": p["zeile"], "name": f"{p['vorname']} {p['nachname']}".strip(), "email": p["email"]}
                   for p in personen if p["nummer"] == n] for n, c in nrn.items() if c > 1}
    namen = Counter(_schluessel(p) for p in personen)
    return {"ok": True, "schon_importiert": bool(st.get("verzeichnis")),
            "personen": len(personen), "mitglieder": sum(1 for p in personen if p["status"] == "mitglied"),
            "anfragen": sum(1 for p in personen if p["status"] == "anfrage"),
            "mitgliedschaften": dict(Counter(MITGLIEDSCHAFTEN.get(p["mitgliedschaft"], "unklar") for p in personen if p["status"] == "mitglied")),
            "vorstand": sum(1 for p in personen if p["vorstand"]),
            "ohne_email": sum(1 for p in personen if "@" not in p["email"]),
            "doppelte_nummern": doppelt,
            "doppelte_namen": sorted({f"{p['vorname']} {p['nachname']}".strip() for p in personen if namen[_schluessel(p)] > 1}),
            "unklar": [{"zeile": p["zeile"], "name": f"{p['vorname']} {p['nachname']}".strip()} for p in personen
                       if p["status"] == "mitglied" and not p["mitgliedschaft"]],
            "naechste_nummer": naechste_nummer([p["nummer"] for p in personen])}


def naechste_nummer(nummern) -> str:
    """Hoechste numerische Nummer + 1, vierstellig (E5)."""
    zahlen = [int(n) for n in nummern if str(n).strip().isdigit()]
    return str(max(zahlen, default=0) + 1).zfill(4)


def import_anwenden(store, daten: dict | None, behalten: dict | None, *, von: str = "") -> dict:
    """MV1: einmaliger Import. `behalten` = {doppelte Nummer: Zeile, die sie behaelt}. Nie doppelt."""
    st = store.stand()
    v = import_vorschau(daten, st)
    if not v["ok"]:
        return v
    if v["schon_importiert"]:
        return {"ok": False, "hinweis": "Das Verzeichnis ist schon übernommen – Änderungen jetzt direkt in LUNA (MV2)."}
    behalten = {str(k): int(z) for k, z in (behalten or {}).items() if str(z).lstrip("-").isdigit()}
    offen = [n for n, zeilen in v["doppelte_nummern"].items() if behalten.get(n) not in {z["zeile"] for z in zeilen}]
    if offen:
        return {"ok": False, "hinweis": "Bitte für jede doppelte Nummer wählen, wer sie behält: " + ", ".join(offen) + "."}
    personen = [_person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])]
    vergeben = {p["nummer"] for p in personen if p["nummer"]}
    neu_nr = {}
    for p in sorted(personen, key=lambda x: x["zeile"] or 0):
        if p["nummer"] in v["doppelte_nummern"] and behalten[p["nummer"]] != p["zeile"]:
            alt = p["nummer"]
            p["nummer"] = naechste_nummer(vergeben)
            vergeben.add(p["nummer"])
            neu_nr[p["zeile"]] = (alt, p["nummer"])
            p["nummer_alt"] = alt
            p["kommentar"] = (p["kommentar"] + " " if p["kommentar"] else "") + f"[LUNA-Import: Nummer {alt} war doppelt, neu {p['nummer']}]"
    for p in personen:
        store.erfassen("ofc_verzeichnis", {"id": "P-" + uuid.uuid4().hex[:10], **{k: p.get(k, "") for k in FELDER},
                                           "status": p["status"], "zeile": p["zeile"], "nummer_alt": p.get("nummer_alt", ""),
                                           "quelle": "import"}, von=von)
    return {"ok": True, "uebernommen": len(personen), "neue_nummern": [{"zeile": z, "alt": a, "neu": n} for z, (a, n) in neu_nr.items()]}


def abgleich(daten: dict | None, st: dict) -> dict:
    """Tabelle <-> LUNA je Tabellenzeile: Abweichungen je Feld (nur Zaehlungen + Zeilen)."""
    if not daten or not daten.get("ok"):
        return {"ok": False, "hinweis": "Mitgliederliste nicht lesbar."}
    luna = {p.get("zeile"): p for p in (st.get("verzeichnis") or {}).values() if p.get("quelle") == "import"}
    if not luna:
        return {"ok": True, "importiert": False}
    tab = {p["zeile"]: _person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])}
    je_feld: Counter = Counter()
    zeilen = []
    for z in sorted(set(tab) | set(luna), key=lambda x: x or 0):
        a, b = tab.get(z), luna.get(z)
        if not a or not b:
            je_feld["nur in " + ("LUNA" if b else "Tabelle")] += 1
            zeilen.append({"zeile": z, "felder": ["fehlt"]})
            continue
        diff = [f for f in ABGLEICH_FELDER if str(a.get(f) or "").strip() != str(b.get(f) or "").strip()
                and not (f == "nummer" and b.get("nummer_alt") and b["nummer_alt"] == a.get("nummer"))]   # bewusst geloester Konflikt
        if diff:
            je_feld.update(diff)
            zeilen.append({"zeile": z, "felder": diff})
    return {"ok": True, "importiert": True, "abweichungen": len(zeilen), "je_feld": dict(je_feld), "zeilen": zeilen[:50],
            "luna": len(luna), "tabelle": len(tab)}


# -- MV2: Bearbeiten in LUNA-OS (CEO-Go 2026-11-26) ---------------------------------------------------------------------
_RE_MAIL = re.compile(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+")
BEARBEITBAR = tuple(f for f in FELDER if f != "anfrage_am")
STATUS = {"mitglied": "Mitglied", "anfrage": "Anfrage", "archiv": "Gekündigt (Archiv)"}


def eintraege(st: dict) -> list[dict]:
    return list((st.get("verzeichnis") or {}).values())


def gekuendigte_nummern(st: dict) -> set[str]:
    """Nummern im Archiv -- an diese Mitglieder geht keine Nachricht mehr (E4)."""
    return {str(p.get("nummer")) for p in eintraege(st) if p.get("status") == "archiv" and p.get("nummer")}


def uebersicht(st: dict) -> dict:
    ps = eintraege(st)
    mg = [p for p in ps if p.get("status") == "mitglied"]
    return {"ok": True, "importiert": bool(ps), "mitglieder": len(mg), "anfragen": sum(1 for p in ps if p.get("status") == "anfrage"),
            "archiv": sum(1 for p in ps if p.get("status") == "archiv"),
            "je_art": {MITGLIEDSCHAFTEN.get(k, "unklar"): sum(1 for p in mg if (p.get("mitgliedschaft") or "") == k) for k in (*MITGLIEDSCHAFTEN, "")},
            "vorstand": sum(1 for p in mg if p.get("vorstand")),
            "naechste_nummer": naechste_nummer([p.get("nummer") for p in ps]),
            "personen": sorted(ps, key=lambda p: (p.get("status") != "mitglied", str(p.get("nummer") or "").zfill(8),
                                                 p.get("nachname", ""), p.get("vorname", "")))}


def _pruefen(st: dict, pid: str, d: dict) -> str:
    if not (str(d.get("vorname") or "").strip() or str(d.get("nachname") or "").strip()):
        return "Vor- oder Nachname angeben."
    mail = str(d.get("email") or "").strip()
    if mail and not _RE_MAIL.fullmatch(mail):
        return "E-Mail-Adresse ist ungültig."
    nr = str(d.get("nummer") or "").strip()
    if nr and any(str(p.get("nummer")) == nr and p["id"] != pid for p in eintraege(st)):
        return f"Nummer {nr} ist schon vergeben."
    if (d.get("mitgliedschaft") or "") not in ("", *MITGLIEDSCHAFTEN):
        return "Mitgliedschaft: Gold, Standard oder Förder."
    return ""


def speichern(store, pid: str, daten: dict, *, von: str = "") -> dict:
    """Mitglied anlegen (pid leer) oder aendern. Gespeichert werden nur geaenderte Felder (Verlauf)."""
    st = store.stand()
    alt = (st.get("verzeichnis") or {}).get(pid) if pid else None
    if pid and not alt:
        return {"ok": False, "hinweis": "Eintrag nicht gefunden."}
    neu = {k: daten[k] for k in BEARBEITBAR if k in daten}
    for k, v in list(neu.items()):
        neu[k] = bool(v) if k == "vorstand" else str(v if v is not None else "").strip()[:500]
    voll = (alt or {}) | neu
    if not alt:
        voll.setdefault("status", "mitglied")
        if voll["status"] == "mitglied" and not voll.get("nummer"):
            voll["nummer"] = neu["nummer"] = naechste_nummer([p.get("nummer") for p in eintraege(st)])
    fehler = _pruefen(st, pid, voll)
    if fehler:
        return {"ok": False, "hinweis": fehler}
    if alt:
        neu = {k: v for k, v in neu.items() if (alt.get(k) if k != "vorstand" else bool(alt.get(k))) != v}
        if not neu:
            return {"ok": True, "id": pid, "geaendert": []}
        store.erfassen("ofc_verzeichnis", {"id": pid, **neu}, von=von)
        return {"ok": True, "id": pid, "geaendert": sorted(neu)}
    pid = "P-" + uuid.uuid4().hex[:10]
    store.erfassen("ofc_verzeichnis", {"id": pid, **{k: voll.get(k, "" if k != "vorstand" else False) for k in FELDER},
                                       "status": voll["status"], "quelle": "hand"}, von=von)
    return {"ok": True, "id": pid, "nummer": voll.get("nummer", ""), "neu": True}


def aufnehmen(store, pid: str, *, nummer: str = "", mitgliedschaft: str = "", seit: str = "", von: str = "") -> dict:
    """Anfrage -> Mitglied mit Nummer (naechste freie, wenn leer)."""
    from datetime import date
    st = store.stand()
    p = (st.get("verzeichnis") or {}).get(pid)
    if not p or p.get("status") != "anfrage":
        return {"ok": False, "hinweis": "Keine offene Anfrage."}
    nr = (nummer or "").strip() or naechste_nummer([x.get("nummer") for x in eintraege(st)])
    d = {"nummer": nr, "mitgliedschaft": mitgliedschaft or p.get("mitgliedschaft", ""), "vorname": p.get("vorname"),
         "nachname": p.get("nachname"), "email": p.get("email")}
    fehler = _pruefen(st, pid, d)
    if fehler:
        return {"ok": False, "hinweis": fehler}
    store.erfassen("ofc_verzeichnis", {"id": pid, "status": "mitglied", "nummer": nr, "mitgliedschaft": d["mitgliedschaft"],
                                       "seit": seit or date.today().strftime("%d.%m.%Y")}, von=von)
    return {"ok": True, "nummer": nr}


def kuendigen(store, pid: str, *, datum: str = "", notiz: str = "", von: str = "") -> dict:
    """E4: ins Archiv -- keine Nachrichten mehr, kein Beitrags-Soll ab Folgejahr, nichts geloescht."""
    from datetime import date
    p = (store.stand().get("verzeichnis") or {}).get(pid)
    if not p or p.get("status") == "archiv":
        return {"ok": False, "hinweis": "Nicht gefunden oder schon gekündigt."}
    datum = (datum or date.today().isoformat())[:10]
    try:
        date.fromisoformat(datum)
    except ValueError:
        return {"ok": False, "hinweis": "Datum als JJJJ-MM-TT."}
    store.erfassen("ofc_verzeichnis", {"id": pid, "status": "archiv", "status_vorher": p.get("status", "mitglied"),
                                       "gekuendigt_am": datum, "kuendigung_notiz": (notiz or "").strip()[:200]}, von=von)
    return {"ok": True}


def wieder_aufnehmen(store, pid: str, *, von: str = "") -> dict:
    p = (store.stand().get("verzeichnis") or {}).get(pid)
    if not p or p.get("status") != "archiv":
        return {"ok": False, "hinweis": "Nicht im Archiv."}
    store.erfassen("ofc_verzeichnis", {"id": pid, "status": p.get("status_vorher") or "mitglied", "gekuendigt_am": "",
                                       "kuendigung_notiz": ""}, von=von)
    return {"ok": True}


def verlauf(store, pid: str) -> list[dict]:
    """Je Aenderung: Zeitpunkt, wer, welche Felder (ohne Werte)."""
    out = []
    for e in store.eintraege():
        if e.get("typ") == "ofc_verzeichnis" and e["daten"].get("id") == pid:
            felder = sorted(k for k in e["daten"] if k not in ("id",))
            out.append({"ts": e["ts"], "von": e.get("von", ""), "felder": ["übernommen aus der Tabelle"] if e["daten"].get("quelle") == "import"
                        else (["angelegt"] if e["daten"].get("quelle") == "hand" else felder)})
    return out


def export_csv(st: dict, ansicht: str = "mitglied") -> bytes:
    import csv
    import io
    b = io.StringIO()
    w = csv.writer(b, delimiter=";")
    w.writerow(["Nummer", "Status", "Anrede", "Vorname", "Nachname", "E-Mail", "Handy", "Adresse", "Geburtstag", "Mitgliedschaft",
                "Vorstand", "Förderbetrag", "Mitglied seit", "Beitrag", "Nächste Zahlung", "HSV-Mitglied", "HSV-Nr.", "Anderer Fanclub",
                "Gekündigt am", "Kommentar"])
    for p in uebersicht(st)["personen"]:
        if ansicht != "alle" and p.get("status") != ansicht:
            continue
        w.writerow([p.get("nummer", ""), STATUS.get(p.get("status"), ""), p.get("anrede", ""), p.get("vorname", ""), p.get("nachname", ""),
                    p.get("email", ""), p.get("handy", ""), p.get("adresse", ""), p.get("geburtstag", ""),
                    MITGLIEDSCHAFTEN.get(p.get("mitgliedschaft") or "", ""), "ja" if p.get("vorstand") else "", p.get("foerder_betrag", ""),
                    p.get("seit", ""), p.get("beitrag", ""), p.get("naechste_zahlung", ""), p.get("hsv_mitglied", ""), p.get("hsv_nr", ""),
                    p.get("anderer_fanclub", ""), p.get("gekuendigt_am", ""), p.get("kommentar", "")])
    return ("﻿" + b.getvalue()).encode("utf-8")


# -- MV3: LUNA-Verzeichnis als Quelle aller OFC-Funktionen (CEO-Go 2026-11-26) -------------------------------------------
_TEXT_ART = {"gold": "Gold", "standard": "Standard", "foerder": "Förder"}


def als_mitgliederliste(st: dict) -> dict:
    """Verzeichnis in derselben Form wie `ofc_mitglieder.lesen` (Mitglieder + Anfragen), damit Beitraege, Eingangs-Erkennung,
    Zahlungsbitten, Ticketversand und Namenssuche unveraendert weiterlaufen. Gekuendigte stehen mit `gekuendigt_am` in der
    Mitgliederliste (fuer Beitraege bis zum Kuendigungsjahr); Nachrichten an sie sperrt `gekuendigte_nummern`."""
    from datetime import datetime
    ps = eintraege(st)
    if not ps:
        return {"ok": False, "hinweis": "LUNA-Verzeichnis ist leer."}

    def person(p: dict) -> dict:
        art = p.get("mitgliedschaft") or ""
        text = _TEXT_ART.get(art, "Vorstand" if p.get("vorstand") else "")
        beitrag = p.get("beitrag") or (p.get("foerder_betrag") if art == "foerder" else "") or ""
        name = f"{p.get('vorname', '')} {p.get('nachname', '')}".strip()
        felder = [[lbl, str(p.get(k) if k != "vorstand" else ("ja" if p.get("vorstand") else ""))]
                  for k, lbl in (("nummer", "Mitgliedsnummer"), ("anrede", "Anrede"), ("vorname", "Vorname"), ("nachname", "Nachname"),
                                 ("email", "E-Mail"), ("handy", "Handy"), ("adresse", "Adresse"), ("geburtstag", "Geburtstag"),
                                 ("mitgliedschaft", "Mitgliedschaft"), ("vorstand", "Vorstand"), ("seit", "Mitglied seit"),
                                 ("beitrag", "Beitrag"), ("kommentar", "Kommentar")) if p.get(k)]
        return {"id": p["id"], "zeile": p.get("zeile"), "nummer": str(p.get("nummer") or ""),
                "status": "anfrage" if p.get("status") == "anfrage" else "mitglied", "name": name,
                "vorname": p.get("vorname", ""), "nachname": p.get("nachname", ""), "mitgliedschaft": text, "seit": p.get("seit", ""),
                "beitrag": beitrag, "naechste_zahlung": p.get("naechste_zahlung", ""), "kommentar": p.get("kommentar", ""),
                "email": p.get("email", ""), "eingang": p.get("anfrage_am", ""), "felder": felder, "hinweise": [],
                "werte": {k: p.get(k, "") for k in FELDER}, "gekuendigt_am": p.get("gekuendigt_am", "") if p.get("status") == "archiv" else ""}

    mg = sorted((person(p) for p in ps if p.get("status") in ("mitglied", "archiv") and p.get("nummer")),
                key=lambda p: p["nummer"].zfill(8))
    an = sorted((person(p) for p in ps if p.get("status") == "anfrage"), key=lambda p: p["eingang"], reverse=True)
    return {"ok": True, "quelle": "luna", "spalten": [], "erkannt": [], "mitglieder": mg, "anfragen": an, "hinweise": [],
            "summe": {"mitglieder": sum(1 for p in mg if not p["gekuendigt_am"]), "anfragen": len(an), "zeilen": len(mg) + len(an)},
            "blatt": "LUNA-Verzeichnis", "gelesen": datetime.now().isoformat(timespec="seconds")}


def quelle(st: dict, env=None) -> str:
    """`luna` sobald das Verzeichnis existiert (MV3), Rueckweg per `OFC_MITGLIEDER_QUELLE=google`."""
    import os
    wahl = ((env if env is not None else os.environ).get("OFC_MITGLIEDER_QUELLE") or "").strip().lower()
    if wahl == "google":
        return "google"
    return "luna" if (st.get("verzeichnis") or {}) else "google"
