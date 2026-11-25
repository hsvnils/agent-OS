"""OFC_KASSE_ROADMAP KA3: Kassenbuch des Fanclubs -- ein Konto PayPal (E-K5), getrennt von der Buchhaltung, keine KI.

Buchungen kommen aus vorhandenen Quellen (nichts doppelt erfasst):
- PayPal-Eingaenge der Mitglieder (O5/KA1, `ofc_eingang`): Kategorie nach Art (Ticket, Beitrag, Merch, Spende, Sonstiges);
  Rueckzahlung an ein Mitglied und Auszahlung aufs Bankkonto sind Abgaenge; noch nicht zugeordnete Eingaenge zaehlen im
  Kassenstand mit (Kategorie „noch nicht zugeordnet“).
- Eigene Zahlungen an Eventim/HSV (O4, `ofc_zahlung`): Abgang Tickets; Erstattung = Zugang; „Spaeter bezahlen“ zaehlt erst
  am Faelligkeitstag und nur, wenn die Abbuchung nicht fehlgeschlagen ist -- sonst „vorgemerkt“.
- Handbuchungen (`ofc_kasse`, z. B. Gebuehren, Auslagen, Korrekturen) mit optionalem Beleg in `fanclub/belege/`
  (nur neu anlegen, nie ueberschreiben); Korrektur per Storno (Buchung bleibt sichtbar), nie loeschen.
- Anfangsbestand (`ofc_kasse_start`, Historie; der letzte gilt) = Stand zu Beginn des Stichtags; Kassenstand = Anfangsbestand
  + alle gebuchten Bewegungen ab dem Stichtag. Kategorie je Buchung per Klick aenderbar (`ofc_kasse_kat`).
"""
from __future__ import annotations

import re
import secrets
from datetime import date
from pathlib import Path

from .ofc_store import OfcStore

KATEGORIEN = {"tickets": "Tickets", "beitraege": "Beiträge", "merch": "Merch/Trikot", "spenden": "Spenden",
              "gebuehren": "Gebühren", "auslagen": "Auslagen", "auszahlung": "Auszahlung", "einzahlung": "Einzahlung (Bank)",
              "sonstiges": "Sonstiges",
              "offen": "noch nicht zugeordnet"}
_ART_KAT = {"ticket": "tickets", "beitrag": "beitraege", "merch": "merch", "spende": "spenden", "sonstiges": "sonstiges",
            "auszahlung": "auszahlung"}
BELEG_ENDUNGEN = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".webp"}
BELEG_MAX = 10 * 1024 * 1024


def _eur(c: int) -> str:
    neg = c < 0
    e, r = divmod(abs(int(c)), 100)
    return ("-" if neg else "") + f"{e:,}".replace(",", ".") + f",{r:02d} €"


def _kat_eingang(e: dict) -> str:
    if e.get("art") in _ART_KAT and e.get("zuordnung") in ("auto", "manuell", "info"):
        return _ART_KAT[e["art"]]
    if e.get("zuordnung") == "ignoriert":
        return "sonstiges"
    if e.get("tickets") and e.get("zuordnung") in ("auto", "manuell"):
        return "tickets"
    if e.get("rueckzahlung"):
        return "tickets"
    return "offen"


def buchungen(st: dict, heute: date | None = None) -> list[dict]:
    """Alle Bewegungen der Kasse (neueste zuerst) mit Quelle, Kategorie und Status gebucht/vorgemerkt/storniert."""
    from .ofc_zahlung import zahlungs_status
    heute = heute or date.today()
    kat = st.get("kasse_kat") or {}
    out = []
    for e in st.get("eingaenge", {}).values():
        if e.get("ersetzt") or not e.get("betrag_cent"):
            continue
        q = f"eingang:{e['id']}"
        text = ("Rückzahlung an " if e.get("rueckzahlung") and e["betrag_cent"] < 0 else "") + (e.get("name") or "PayPal")
        if e.get("mitteilung"):
            text += f" – „{e['mitteilung'][:60]}“"
        out.append({"id": q, "quelle": "eingang", "datum": e.get("datum") or "", "betrag_cent": int(e["betrag_cent"]),
                    "kategorie": kat.get(q) or _kat_eingang(e), "text": text, "status": "gebucht",
                    "herkunft": "PayPal-Eingang", "transaktionscode": e.get("transaktionscode") or ""})
    for z in zahlungs_status(st, heute):
        if z.get("art") not in ("gesendet", "spaeter", "erstattung"):
            continue
        q = f"zahlung:{z['id']}"
        vz = 1 if z["art"] == "erstattung" else -1
        datum, status = z.get("datum") or "", "gebucht"
        if z["art"] == "spaeter":
            datum = z.get("faellig") or datum
            if z.get("abbuchung") != "abgebucht":
                status = "vorgemerkt"
        spiel = (st["spiele"].get(z.get("spiel") or "") or {}).get("spiel") or z.get("spiel") or ""
        text = {"gesendet": "Zahlung an ", "spaeter": "Später bezahlen an ", "erstattung": "Erstattung von "}[z["art"]] \
            + (z.get("haendler") or "Eventim/HSV") + (f" – {spiel}" if spiel else "")
        if z["art"] == "spaeter" and z.get("abbuchung") == "fehlgeschlagen":
            text += " (Abbuchung fehlgeschlagen)"
        out.append({"id": q, "quelle": "zahlung", "datum": datum, "betrag_cent": vz * int(z.get("betrag_cent") or 0),
                    "kategorie": kat.get(q) or ("sonstiges" if z.get("zuordnung") == "ignoriert" else "tickets"),
                    "text": text, "status": status, "herkunft": "Eigene Zahlung",
                    "transaktionscode": z.get("transaktionscode") or ""})
    for b in (st.get("kasse") or {}).values():
        q = f"kasse:{b['id']}"
        out.append({"id": q, "quelle": "import" if b.get("import_id") else "hand", "datum": b.get("datum") or "",
                    "betrag_cent": int(b.get("betrag_cent") or 0), "kategorie": kat.get(q) or b.get("kategorie") or "sonstiges",
                    "text": b.get("text") or "", "status": "storniert" if b.get("storniert") else "gebucht",
                    "herkunft": "CSV-Import" if b.get("import_id") else "Handbuchung", "beleg": bool(b.get("beleg")),
                    "import_id": b.get("import_id") or "", "transaktionscode": b.get("transaktionscode") or ""})
    return sorted(out, key=lambda x: (x["datum"], x["id"]), reverse=True)


def anfangsbestand(st: dict) -> dict | None:
    s = st.get("kasse_start") or []
    return s[-1] if s else None


def kassenbuch(st: dict, *, jahr: int | None = None, heute: date | None = None) -> dict:
    """Buchungen (optional nur ein Jahr), Kassenstand, Einnahmen/Ausgaben je Kategorie, Vorgemerktes."""
    heute = heute or date.today()
    alle = buchungen(st, heute)
    start = anfangsbestand(st)
    gebucht = [b for b in alle if b["status"] == "gebucht"]
    stand = None
    if start:
        stand = int(start["betrag_cent"]) + sum(b["betrag_cent"] for b in gebucht if b["datum"] >= start["datum"])
    liste = [b for b in alle if not jahr or b["datum"][:4] == str(jahr)]
    je_kat: dict = {}
    for b in liste:
        if b["status"] != "gebucht":
            continue
        k = je_kat.setdefault(b["kategorie"], {"kategorie": b["kategorie"], "text": KATEGORIEN.get(b["kategorie"], b["kategorie"]),
                                               "einnahmen_cent": 0, "ausgaben_cent": 0})
        k["einnahmen_cent" if b["betrag_cent"] > 0 else "ausgaben_cent"] += b["betrag_cent"]
    for b in liste:
        b["vor_stichtag"] = bool(start and b["datum"] < start["datum"])
    return {"ok": True, "jahr": jahr, "buchungen": liste, "anfangsbestand": start, "kassenstand_cent": stand,
            "einnahmen_cent": sum(k["einnahmen_cent"] for k in je_kat.values()),
            "ausgaben_cent": sum(k["ausgaben_cent"] for k in je_kat.values()),
            "je_kategorie": sorted(je_kat.values(), key=lambda k: list(KATEGORIEN).index(k["kategorie"]) if k["kategorie"] in KATEGORIEN else 99),
            "vorgemerkt_cent": sum(b["betrag_cent"] for b in alle if b["status"] == "vorgemerkt"),
            "nicht_zugeordnet": sum(1 for b in alle if b["kategorie"] == "offen" and b["status"] == "gebucht"),
            "kategorien": KATEGORIEN}


def _datum_ok(d: str) -> bool:
    try:
        date.fromisoformat(d)
        return True
    except (TypeError, ValueError):
        return False


def buchung_anlegen(store: OfcStore, *, datum: str, betrag_cent: int, kategorie: str, text: str,
                    beleg: bytes = b"", beleg_name: str = "", von: str = "", import_id: str = "",
                    transaktionscode: str = "") -> dict:
    """Handbuchung (+ Zugang / - Abgang); Beleg wird nur neu angelegt (`fanclub/belege/<id><endung>`)."""
    if not _datum_ok(datum):
        return {"ok": False, "hinweis": "Datum ungültig."}
    if kategorie not in KATEGORIEN or kategorie == "offen":
        return {"ok": False, "hinweis": "Kategorie unbekannt."}
    if not isinstance(betrag_cent, int) or not betrag_cent or abs(betrag_cent) > 10_000_000:
        return {"ok": False, "hinweis": "Betrag ungültig."}
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:200]
    if not text:
        return {"ok": False, "hinweis": "Bitte einen Text angeben."}
    bid = "k-" + secrets.token_hex(6)
    datei = ""
    if beleg:
        endung = Path(beleg_name or "").suffix.lower()
        if endung not in BELEG_ENDUNGEN:
            return {"ok": False, "hinweis": "Beleg: nur PDF oder Bild."}
        if len(beleg) > BELEG_MAX:
            return {"ok": False, "hinweis": "Beleg ist größer als 10 MB."}
        ordner = store.dir / "belege"
        ordner.mkdir(parents=True, exist_ok=True)
        ziel = ordner / f"{bid}{endung}"
        with open(ziel, "xb") as f:                                      # nur neu anlegen, nie ueberschreiben
            f.write(beleg)
        datei = ziel.name
    d = {"id": bid, "datum": datum, "betrag_cent": betrag_cent, "kategorie": kategorie, "text": text, "beleg": datei}
    if import_id:
        d["import_id"] = import_id
    if transaktionscode:
        d["transaktionscode"] = transaktionscode
    store.erfassen("ofc_kasse", d, von=von)
    return {"ok": True, "id": bid, "buchung": d}


def storno(store: OfcStore, bid: str, *, zurueck: bool = False, von: str = "") -> dict:
    """Handbuchung stornieren (bleibt sichtbar) oder Storno aufheben. Buchungen aus Mails aendert man ueber die Zuordnung."""
    b = (store.stand().get("kasse") or {}).get(bid)
    if not b:
        return {"ok": False, "hinweis": "Buchung nicht gefunden (nur Handbuchungen und Importe sind stornierbar)."}
    store.erfassen("ofc_kasse", {"id": bid, "storniert": not zurueck}, von=von)
    return {"ok": True, "id": bid, "storniert": not zurueck}


def kategorie_setzen(store: OfcStore, quelle: str, kategorie: str, *, von: str = "") -> dict:
    if kategorie not in KATEGORIEN:
        return {"ok": False, "hinweis": "Kategorie unbekannt."}
    if quelle not in {b["id"] for b in buchungen(store.stand())}:
        return {"ok": False, "hinweis": "Buchung nicht gefunden."}
    store.erfassen("ofc_kasse_kat", {"quelle": quelle, "kategorie": kategorie}, von=von)
    return {"ok": True, "quelle": quelle, "kategorie": kategorie}


def anfangsbestand_setzen(store: OfcStore, datum: str, betrag_cent: int, *, von: str = "") -> dict:
    if not _datum_ok(datum):
        return {"ok": False, "hinweis": "Datum ungültig."}
    if not isinstance(betrag_cent, int) or abs(betrag_cent) > 100_000_000:
        return {"ok": False, "hinweis": "Betrag ungültig."}
    store.erfassen("ofc_kasse_start", {"datum": datum, "betrag_cent": betrag_cent}, von=von)
    return {"ok": True, "datum": datum, "betrag_cent": betrag_cent}


def beleg_pfad(store: OfcStore, bid: str) -> Path | None:
    b = (store.stand().get("kasse") or {}).get(bid)
    if not b or not b.get("beleg"):
        return None
    p = store.dir / "belege" / b["beleg"]
    return p if p.is_file() and p.parent == store.dir / "belege" else None
