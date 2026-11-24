"""OFC_ROADMAP O5: Zahlungseingaenge der Mitglieder (PayPal „Zahlung erhalten“) den Tickets zuordnen -- regelbasiert, keine KI.

- Quelle: PayPal-Mails im Fanclub-Postfach (nur lesend): Name des Zahlers, Betrag, Mitteilung, Transaktionscode, Datum.
  Rueckzahlungen an Mitglieder (PayPal „Rückzahlung“ an eine Person) zaehlen negativ.
- Zuordnung (E6): eindeutig = automatisch, wenn der Betrag genau zu offenen Tickets passt, die auf den Namen des Zahlers
  (oder einen gelernten Alias) laufen -- bei mehreren Moeglichkeiten entscheidet die Mitteilung (Gegner). Sonst Liste
  „Zuordnen“ mit Vorschlaegen; per Klick auch Teil-, Sammel- oder Ueberzahlung. Ordnet der CEO einen Zahler per Klick
  Tickets mit anderem Namen zu, merkt sich LUNA das als Alias (Ereignis `ofc_alias`).
- Ticketstatus bezahlt/offen und Saldo je Zahler ergeben sich aus den Zuordnungen (Betrag wird der Reihe nach auf die
  Ticketpreise verteilt). Gespeichert als Ereignis `ofc_eingang` in `fanclub/log.jsonl` -- nur fuer den CEO, getrennt
  von der Buchhaltung; LUNA schreibt Mitgliedern nichts.
"""
from __future__ import annotations

import email
import hashlib
import re
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from itertools import combinations

from . import ofc
from .ofc_store import OfcStore
from .ofc_zahlung import PAYPAL_DOMAINS, _BETRAG, _cent, _datum

VERSION = 2                     # Erkennungsstand; automatisch erzeugte Eintraege aelterer Fassung werden neu bewertet
TAGE = 120
_LABELS = ("transaktionscode", "transaktions", "datum", "betrag", "zahlung", "details", "hilfe", "paypal", "sie sind",
           "bitte", "hinweis")


def _norm(s: str) -> str:
    s = s.casefold().replace("ß", "ss")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def _woerter(s: str) -> set[str]:
    return {w for w in _norm(s).split() if len(w) >= 2}


def _mitteilung(text: str) -> str:
    zeilen = [z.strip() for z in text.splitlines()]
    for i, z in enumerate(zeilen):
        if re.match(r"(Mitteilung|Nachricht)\b", z, re.I):
            rest = z.split(":", 1)[1].strip() if ":" in z else ""
            if rest and not re.match(r"^(von|an)\b", rest, re.I):
                return rest[:300]
            teile = []
            for x in zeilen[i + 1:]:
                if not x:
                    if teile:
                        break
                    continue
                if any(x.lower().startswith(l) for l in _LABELS) or re.search(_BETRAG, x):
                    break
                teile.append(x)
                if len(teile) >= 4:
                    break
            return " ".join(teile)[:300]
    return ""


def eingang_lesen(roh: bytes) -> dict | None:
    """PayPal-Mail -> Eingang {id, name, betrag_cent (negativ bei Rueckzahlung), datum, mitteilung, transaktionscode}."""
    m = email.message_from_bytes(roh, policy=policy.default)
    dom = parseaddr(str(m.get("From", "")))[1].lower().rpartition("@")[2]
    if not any(dom == d or dom.endswith("." + d) for d in PAYPAL_DOMAINS):
        return None
    betreff = str(m.get("Subject", ""))
    text = ofc._text(m).replace("\xa0", " ")
    alles = f"{betreff}\n{text}"
    rueck = re.search(r"Rückzahlung|Rueckzahlung", betreff, re.I) and re.search(r"gesendet|an\s", alles, re.I)
    if rueck:
        n = re.search(r"Rückzahlung (?:an|für|fuer)\s+([^\n,]+?)(?:\s+(?:gesendet|über|ueber|von)\b|[\n,.]|$)", alles, re.I)
    else:
        if not re.search(r"(Zahlung|Geld)\s+(erhalten|empfangen)|hat (Ihnen|dir) .{0,40}gesendet", alles, re.I):
            return None
        n = re.search(r"^\s*(.+?)\s+hat (?:Ihnen|dir)\b", text, re.M)
    if not n:
        return None
    name = re.sub(r"\s+", " ", n[1]).strip(" :")[:80]
    if re.search(r"eventim|hamburger sport|paypal", name, re.I):
        return None                                                   # Haendler-Erstattung -> O4
    b = re.search(r"(?:gesendet|Betrag|über|ueber)[^\n]{0,20}?\s*\n?\s*" + _BETRAG, alles) or re.search(_BETRAG, alles)
    if not b:
        return None
    try:
        gesendet = parsedate_to_datetime(str(m.get("Date", ""))).date().isoformat()
    except Exception:
        gesendet = ""
    tc = re.search(r"Transaktions(?:code|-ID|nummer)\s*:?\s*\n?\s*([A-Z0-9]{10,20})", text)
    nach_tc = text[tc.end():] if tc else ""
    betrag = abs(_cent(b[1])) * (-1 if rueck else 1)
    z = {"name": name, "betrag_cent": betrag, "datum": _datum(nach_tc) or gesendet, "mitteilung": _mitteilung(text),
         "transaktionscode": tc[1] if tc else "", "rueckzahlung": bool(rueck), "v": VERSION}
    z["id"] = "e-" + (z["transaktionscode"] or hashlib.sha1(
        f"{name}|{betrag}|{z['datum']}|{m.get('Message-ID', '')}".encode()).hexdigest()[:16])
    return z


def eingaenge_aus_mails(mails: list[dict]) -> list[dict]:
    out, ids = [], set()
    for x in mails:
        try:
            z = eingang_lesen(x["roh"])
        except Exception:
            continue
        if z and z["id"] not in ids:
            ids.add(z["id"])
            out.append(z)
    return sorted(out, key=lambda z: (z["datum"], z["id"]))


# -- Stand: bezahlt/offen je Ticket, Saldo je Zahler ------------------------------------------------------------------
def _aliase(st: dict) -> dict[str, set[str]]:
    return {k: set(v) for k, v in (st.get("aliase") or {}).items()}


def bezahlt_stand(st: dict) -> dict:
    """{tickets: {ticketnr: {bezahlt_cent, bezahlt, zahler}}, saldo: {zahler: cent}} aus allen zugeordneten Eingaengen."""
    tk = {nr: {"bezahlt_cent": 0, "bezahlt": False, "zahler": []} for nr in st["tickets"]}
    saldo: dict = {}
    for e in sorted(st.get("eingaenge", {}).values(), key=lambda e: (e.get("datum") or "", e["id"])):
        if e.get("zuordnung") not in ("auto", "manuell") or not e.get("tickets") or e.get("ersetzt"):
            continue                                                   # nur zugeordnete zaehlen (offene stehen unter „Zuordnen“)
        name = e.get("name") or "?"
        saldo[name] = saldo.get(name, 0) + e["betrag_cent"]
        rest = e["betrag_cent"]
        for nr in e.get("tickets") or []:
            t = st["tickets"].get(nr)
            if not t:
                continue
            x = tk[nr]
            preis = t.get("preis_cent") or 0
            if rest < 0:                                               # Rueckzahlung mindert das Bezahlte
                teil = max(rest, -x["bezahlt_cent"])
            else:
                teil = min(rest, max(preis - x["bezahlt_cent"], 0)) if preis else rest
            x["bezahlt_cent"] += teil
            rest -= teil
            if name not in x["zahler"]:
                x["zahler"].append(name)
    for nr, x in tk.items():
        preis = st["tickets"][nr].get("preis_cent") or 0
        x["bezahlt"] = bool(x["zahler"]) and (x["bezahlt_cent"] >= preis if preis else x["bezahlt_cent"] > 0)
    zugeordnet: dict = {}                                              # Saldo = gezahlt - Preise der zugeordneten Tickets
    for e in st.get("eingaenge", {}).values():
        if e.get("zuordnung") not in ("auto", "manuell") or e.get("ersetzt"):
            continue
        for nr in e.get("tickets") or []:
            zugeordnet.setdefault(nr, e.get("name") or "?")
    for nr, name in zugeordnet.items():
        saldo[name] = saldo.get(name, 0) - (st["tickets"].get(nr, {}).get("preis_cent") or 0)
    return {"tickets": tk, "saldo": saldo}


# -- Vorschlaege ------------------------------------------------------------------------------------------------------
def _name_passt(ticketname: str, zahler: set[str]) -> bool:
    w = _woerter(ticketname)
    return bool(w) and any(w <= z or (len(w) == 1 and next(iter(w)) in z) for z in zahler)


def vorschlag(z: dict, st: dict, offen: dict) -> dict:
    """E6-Entscheidung fuer einen Eingang: {zuordnung: auto|offen, tickets, vorschlaege: [{spiel, tickets, summe, gruende}]}."""
    if z["betrag_cent"] <= 0:
        return {"zuordnung": "offen", "tickets": [], "vorschlaege": []}
    zahler = [_woerter(z["name"])] + [_woerter(a) for a in _aliase(st).get(_norm(z["name"]), set())]
    mt = _woerter(z.get("mitteilung") or "")
    je_spiel: dict = {}
    for nr, t in st["tickets"].items():
        s = st["spiele"].get(t["spiel"]) or {}
        if nr not in offen or s.get("verworfen"):                      # auch abgeschlossene: Zahlungen kommen oft danach
            continue
        if _name_passt(t.get("name") or "", [x for x in zahler if x]):
            je_spiel.setdefault(t["spiel"], []).append(nr)
    moeglich = []
    for sid, nrs in je_spiel.items():
        s = st["spiele"][sid]
        gegner = {w for w in _woerter(s.get("gegner") or sid) if len(w) >= 3 and w not in ("hsv", "vs", "hamburger", "sv", "fc")}
        gruende = ["Name passt"] + (["Gegner in der Mitteilung"] if gegner & mt else [])
        preise = [(offen[nr], nr) for nr in nrs]
        for k in range(len(preise), 0, -1):                            # alle Tickets, sonst Teilmengen gleicher Summe
            for kombi in combinations(preise, k):
                if sum(p for p, _ in kombi) == z["betrag_cent"] and all(p for p, _ in kombi):
                    moeglich.append({"spiel": sid, "tickets": [nr for _, nr in kombi], "summe": z["betrag_cent"],
                                     "gruende": gruende + ["Betrag passt"], "mitteilung": bool(gegner & mt)})
                    break
            else:
                continue
            break
        else:
            moeglich.append({"spiel": sid, "tickets": nrs, "summe": sum(offen[nr] for nr in nrs), "gruende": gruende,
                             "mitteilung": bool(gegner & mt)})
    if len([m for m in moeglich if "Betrag passt" in m["gruende"]]) == 0 and len(je_spiel) > 1:
        alle = [(offen[nr], nr, sid) for sid, nrs in je_spiel.items() for nr in nrs]
        if sum(p for p, _, _ in alle) == z["betrag_cent"] and all(p for p, _, _ in alle):   # Sammelzahlung fuer mehrere Spiele
            moeglich.append({"spiel": "", "tickets": [nr for _, nr, _ in alle], "summe": z["betrag_cent"],
                             "gruende": ["Name passt", "Betrag passt", "mehrere Spiele"], "mitteilung": False})
    treffer = [m for m in moeglich if "Betrag passt" in m["gruende"]]
    if len(treffer) > 1 and sum(1 for m in treffer if m["mitteilung"]) == 1:
        treffer = [m for m in treffer if m["mitteilung"]]
    erwaehnt = {sid for sid, s in st["spiele"].items() if not s.get("verworfen")
                and {w for w in _woerter(s.get("gegner") or sid) if len(w) >= 3 and w not in ("hsv", "vs", "hamburger", "sv", "fc")} & mt}
    if len(treffer) == 1 and erwaehnt and treffer[0]["spiel"] not in erwaehnt and not (
            not treffer[0]["spiel"] and {st["tickets"][nr]["spiel"] for nr in treffer[0]["tickets"]} & erwaehnt):
        treffer = []                                                   # Mitteilung nennt ein anderes Spiel -> per Klick
    moeglich.sort(key=lambda m: ("Betrag passt" not in m["gruende"], not m["mitteilung"], m["spiel"]))
    if len(treffer) == 1:
        return {"zuordnung": "auto", "tickets": treffer[0]["tickets"], "vorschlaege": moeglich[:4]}
    return {"zuordnung": "offen", "tickets": [], "vorschlaege": moeglich[:4]}


def _offen(st: dict) -> dict:
    """Ticketnr -> noch offener Betrag (Preis - bereits bezahlt)."""
    bz = bezahlt_stand(st)["tickets"]
    return {nr: max((t.get("preis_cent") or 0) - bz[nr]["bezahlt_cent"], 0) for nr, t in st["tickets"].items()
            if not bz[nr]["bezahlt"]}


def eingang_plan(store: OfcStore, mails: list[dict]) -> dict:
    """Dry-Run: neue Eingaenge mit Vorschlag/Auto-Zuordnung -- schreibt nichts."""
    st = store.stand()
    alt = {i for i, e in st.get("eingaenge", {}).items() if e.get("v") != VERSION and e.get("zuordnung") in ("auto", "offen")}
    if alt:                                                            # alte automatische Bewertung zaehlt nicht mehr
        st = st | {"eingaenge": {i: e for i, e in st["eingaenge"].items() if i not in alt}}
    bekannt = st.get("eingaenge", {})
    offen = _offen(st)
    neu = []
    for z in eingaenge_aus_mails(mails):
        if z["id"] in bekannt:
            continue
        e = z | vorschlag(z, st, offen)
        for nr in e["tickets"]:                                         # im selben Lauf nicht doppelt vergeben
            offen.pop(nr, None)
        neu.append(e)
    return {"ok": True, "neu": neu, "auto": sum(1 for e in neu if e["zuordnung"] == "auto"),
            "offen": sum(1 for e in neu if e["zuordnung"] == "offen")}


def eingang_anwenden(store: OfcStore, mails: list[dict], *, von: str = "") -> dict:
    plan = eingang_plan(store, mails)
    for e in plan["neu"]:
        store.erfassen("ofc_eingang", {k: v for k, v in e.items() if k != "vorschlaege"}
                       | {"vorschlaege": [{k: v for k, v in m.items() if k != "mitteilung"} for m in e["vorschlaege"]]}, von=von)
    return plan


def eingang_zuordnen(store: OfcStore, eid: str, tickets: list[str], *, ignorieren: bool = False, von: str = "") -> dict:
    """Per Klick: Tickets zuordnen (auch mehrere Spiele, Teil-/Ueberzahlung), loesen (leer) oder ignorieren (kein Ticket)."""
    st = store.stand()
    e = st.get("eingaenge", {}).get(eid)
    if not e:
        return {"ok": False, "hinweis": "Zahlungseingang nicht gefunden."}
    fremd = [nr for nr in tickets if nr not in st["tickets"]]
    if fremd:
        return {"ok": False, "hinweis": f"Ticket nicht gefunden: {fremd[0]}"}
    zu = "ignoriert" if ignorieren else ("manuell" if tickets else "offen")
    store.erfassen("ofc_eingang", {"id": eid, "tickets": [] if ignorieren else list(tickets), "zuordnung": zu}, von=von)
    neu_alias = []
    if zu == "manuell":
        zahler = _woerter(e.get("name") or "")
        for nr in tickets:
            tn = st["tickets"][nr].get("name") or ""
            if tn and not _name_passt(tn, [zahler]) and tn not in neu_alias:
                neu_alias.append(tn)
        for tn in neu_alias:
            store.erfassen("ofc_alias", {"zahler": _norm(e.get("name") or ""), "name": tn}, von=von)
    return {"ok": True, "id": eid, "zuordnung": zu, "tickets": [] if ignorieren else list(tickets), "aliase_neu": neu_alias}


def lauf(store: OfcStore, postfach, *, von: str = "auto") -> dict:
    try:
        if not postfach.verfuegbar():
            return {"ok": False, "hinweis": "Postfach moin@ ist nicht eingerichtet."}
        return eingang_anwenden(store, postfach.posteingang(tage=TAGE, nur=PAYPAL_DOMAINS), von=von)
    except Exception as exc:
        return {"ok": False, "hinweis": f"Postfach-Abruf fehlgeschlagen ({exc.__class__.__name__})."}
