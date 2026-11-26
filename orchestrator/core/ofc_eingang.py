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
import unicodedata
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from itertools import combinations

from . import ofc
from .ofc_store import OfcStore
from .ofc_zahlung import PAYPAL_DOMAINS, _BETRAG, _cent, _datum

VERSION = 4                     # Erkennungsstand; automatisch erzeugte Eintraege aelterer Fassung werden neu bewertet
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
        hb = st["tickets"][nr].get("hand_bezahlt") or {}
        if hb.get("bezahlt"):                                          # OFC_TICKETVERSAND TV3c: vom CEO als bezahlt markiert
            x.update(bezahlt=True, bezahlt_cent=max(x["bezahlt_cent"], preis), hand=hb)
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
_FREI = {"", "frei", "offen", "unbekannt"}
_KEIN_NAME = {"hsv", "vs", "hamburger", "sv", "fc", "tsg", "fsv", "1", "05", "04", "borussia", "eintracht", "tickets",
              "ticket", "dfb", "pokal", "heim", "auswaerts", "spiel", "gegen", "und", "the"}
# Spitznamen/Staedte -> Kuerzel (gilt in beide Richtungen ueber die Merkmale eines Spiels)
_SYNONYME = {"bmg": {"gladbach", "moenchengladbach", "fohlen"}, "vfb": {"stuttgart"}, "fcb": {"bayern", "muenchen"},
             "sge": {"frankfurt"}, "svw": {"bremen", "werder"}, "s04": {"schalke"}, "bvb": {"dortmund"},
             "koeln": {"effzeh", "koelle"}, "m05": {"mainz"}, "hajduk": {"split"}, "kopenhagen": {"copenhagen", "koebenhavn"}}
_PHRASEN = ((r"nord\s*sued|sued\s*nord", "fcb"), (r"nordderby|nord\s+derby", "svw"))
_MERCH = re.compile(r"trikot|schal|merch|aufkleber|shirt|hoodie|cap\b|sticker|fahne", re.I)
_SPENDE = re.compile(r"spende", re.I)
ARTEN = ("ticket", "beitrag", "merch", "spende", "sonstiges")
_BANK = re.compile(r"sparkasse|\bbank\b|volksbank|commerzbank|\bing\b|••|\*\*\d", re.I)
RUNDUNG_CENT = 500                                                    # „aufgerundet“: bis 5 € ueber dem Kartenpreis


def _falten(s: str) -> str:
    s = s.replace("ß", "ss")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue")):
        s = s.replace(a, b)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _ticket_woerter(name: str) -> set[str]:
    """Ticketname -> Namenswoerter: „28B-ReneSchnettler“ -> {rene, schnettler}, „Johannes1“ -> {johannes}."""
    s = _falten(name)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=\d)(?=[A-Za-z]{3})", " ", s)
    s = re.sub(r"(?<=[A-Za-z])\d+\b", "", s)
    return {w for w in _norm(s).split() if len(w) >= 2 and not re.fullmatch(r"\d+[a-z]?", w) and w not in _FREI}


def _frei(name: str) -> bool:
    return not _ticket_woerter(name)


def _name_passt(ticketname: str, zahler: list[set[str]]) -> bool:
    w = _ticket_woerter(ticketname)
    return bool(w) and any(z and (w <= z or (len(w) == 1 and next(iter(w)) in z)) for z in zahler)


def _merkmale(sid: str, s: dict) -> set[str]:
    """Woerter, an denen man ein Spiel in einer Mitteilung erkennt (Gegner, Kuerzel aus dem Ordner, Spitznamen)."""
    roh = _norm(_falten(re.sub(r"(?i)hsv|vs", " ", sid))) + " " + _norm(_falten(s.get("gegner") or ""))
    w = {x for x in roh.split() if len(x) >= 3 and x not in _KEIN_NAME} | {x for x in roh.split() if x in ("s04", "m05")}
    for k, v in _SYNONYME.items():
        if k in w or v & w:
            w |= v | {k}
    if "pokal" in _norm(sid + " " + (s.get("wettbewerb") or "")):
        w |= {"pokal", "dfb"}
    return w


def _heim(sid: str) -> bool:
    return _norm(sid).replace(" ", "").startswith("hsv")


def _erwaehnt(st: dict, mitteilung: str) -> tuple[set[str], bool]:
    """Spiele, die die Mitteilung nennt -> ({sid}, Ort-Konflikt). Pokal/Heim/Auswaerts trennen gleiche Gegner."""
    t = _norm(_falten(mitteilung or ""))
    if not t:
        return set(), False
    mt = set(t.split())
    for muster, k in _PHRASEN:
        if re.search(muster, t):
            mt.add(k)
    treffer = {}
    for sid, s in st["spiele"].items():
        if s.get("verworfen"):
            continue
        m = _merkmale(sid, s) & mt
        if m:
            treffer[sid] = m
    if not treffer:
        return set(), False
    woerter = t.split()
    ort = ""
    if mt & {"in", "bei", "auswaerts", "away"}:
        ort = "aus"
    elif "heim" in mt:
        ort = "heim"
    elif "hsv" in woerter:
        i = woerter.index("hsv")
        alle = set().union(*treffer.values())
        pos = [j for j, x in enumerate(woerter) if x in alle]
        if pos:
            ort = "heim" if i < min(pos) else "aus"
    menge = set(treffer)
    if mt & {"pokal", "dfb"}:
        p = {sid for sid in menge if "pokal" in _norm(sid + " " + (st["spiele"][sid].get("wettbewerb") or ""))}
        menge = p or menge
    if ort:
        o = {sid for sid in menge if _heim(sid) == (ort == "heim")}
        if not o:
            return menge, True                                         # „Köln vs HSV“, aber nur das Heimspiel im Bestand
        menge = o
    return menge, False


def _beste_kombi(pool: list[tuple[int, str, bool]], betrag: int, rundung: bool = False):
    """pool [(offen_cent, ticketnr, ist_zahler)] -> beste Teilmenge mit Summe == Betrag (oder bis RUNDUNG_CENT darunter).
    Bevorzugt Tickets auf den Namen des Zahlers, dann die Reihenfolge."""
    beste = None
    for k in range(1, min(len(pool), 10) + 1):
        for kombi in combinations(pool, k):
            summe = sum(p for p, _, _ in kombi)
            rest = betrag - summe
            if not (rest == 0 or (rundung and 0 < rest <= RUNDUNG_CENT and rest < min(p for p, _, _ in pool))):
                continue
            wert = (rest == 0, summe, sum(1 for *_, z in kombi if z))
            if beste is None or wert > beste[0]:
                beste = (wert, [nr for _, nr, _ in kombi], summe)
    return (beste[1], beste[2]) if beste else None


def vorschlag(z: dict, st: dict, offen: dict) -> dict:
    """E6-Entscheidung fuer einen Eingang: {zuordnung: auto|offen|info, tickets, vorschlaege, wahl?, grund?}.

    1. Nennt die Mitteilung ein Spiel, zaehlen nur dessen Tickets: Name + Betrag, sonst freie Karten (ohne Namen/„Frei“)
       mit passendem Betrag (auch aufgerundet bis 5 €) -> automatisch. Passt der Betrag nur mit Karten anderer Namen ->
       „Tickets wählen“ mit vorgewaehltem Spiel.
    2. Ohne Spiel in der Mitteilung: genau eine Kombination aus Tickets auf den Namen des Zahlers mit genau dem Betrag.
    Ueberweisungen aufs Bankkonto -> info; Mitteilung „Trikot/Beitrag …“ ohne passendes Ticket -> info."""
    if _BANK.search(z.get("name") or ""):
        return {"zuordnung": "info", "tickets": [], "vorschlaege": [], "grund": "Überweisung auf das Bankkonto", "art": "auszahlung"}
    if z["betrag_cent"] <= 0:
        return {"zuordnung": "offen", "tickets": [], "vorschlaege": []}
    zahler = [x for x in [_woerter(_falten(z["name"]))] + [_ticket_woerter(a) for a in _aliase(st).get(_norm(z["name"]), set())] if x]
    erw, ort_konflikt = _erwaehnt(st, z.get("mitteilung") or "")
    je_spiel: dict = {}
    for nr, t in st["tickets"].items():
        s = st["spiele"].get(t["spiel"]) or {}
        if nr not in offen or s.get("verworfen"):                      # auch abgeschlossene: Zahlungen kommen oft danach
            continue
        je_spiel.setdefault(t["spiel"], []).append((nr, _name_passt(t.get("name") or "", zahler), _frei(t.get("name") or "")))
    moeglich = []
    for sid, nrs in je_spiel.items():
        eigene = [nr for nr, n, _ in nrs if n]
        if not eigene:
            continue
        gruende = ["Name passt"] + (["Spiel in der Mitteilung"] if sid in erw else [])
        mit_preis = [(offen[nr], nr, True) for nr in eigene if offen[nr]]
        k = _beste_kombi(mit_preis, z["betrag_cent"]) if mit_preis else None
        if k:
            moeglich.append({"spiel": sid, "tickets": k[0], "summe": k[1], "gruende": gruende + ["Betrag passt"]})
        elif not mit_preis and len(eigene) == 1:                       # Preis unbekannt (keine Rechnung)
            moeglich.append({"spiel": sid, "tickets": eigene, "summe": z["betrag_cent"], "gruende": gruende + ["Preis unbekannt"]})
        else:
            moeglich.append({"spiel": sid, "tickets": eigene, "summe": sum(offen[nr] for nr in eigene), "gruende": gruende})
    treffer = [m for m in moeglich if "Betrag passt" in m["gruende"]]
    if not treffer and len(je_spiel) > 1:                              # Sammelzahlung fuer mehrere Spiele
        alle = [(offen[nr], nr, sid) for sid, nrs in je_spiel.items() for nr, n, _ in nrs if n]
        if len(alle) > 1 and sum(p for p, _, _ in alle) == z["betrag_cent"] and all(p for p, _, _ in alle) \
                and len({sid for *_, sid in alle}) > 1 and (not erw or {sid for *_, sid in alle} <= erw):
            m = {"spiel": "", "tickets": [nr for _, nr, _ in alle], "summe": z["betrag_cent"],
                 "gruende": ["Name passt", "Betrag passt", "mehrere Spiele"]}
            moeglich.append(m)
            treffer = [m]
    wahl = None
    if erw:                                                            # 1. die Mitteilung nennt das Spiel
        treffer = [m for m in treffer if m["spiel"] in erw or (not m["spiel"] and {st["tickets"][nr]["spiel"] for nr in m["tickets"]} <= erw)]
        unbekannt = [m for m in moeglich if m["spiel"] in erw and "Preis unbekannt" in m["gruende"]]
        if not treffer and len(unbekannt) == 1:
            treffer = unbekannt
        if not treffer:
            frei_treffer, fremd = [], []
            for sid in sorted(erw):
                nrs = je_spiel.get(sid, [])
                pool = [(offen[nr], nr, n) for nr, n, f in nrs if (n or f) and offen[nr]]
                k = _beste_kombi(pool, z["betrag_cent"], rundung=True) if pool else None
                if k:
                    g = ["Spiel in der Mitteilung"] + (["Name passt"] if any(n for nr, n, _ in nrs if nr in k[0]) else []) \
                        + (["freie Karte"] if any(f for nr, _, f in nrs if nr in k[0]) else []) \
                        + (["Betrag passt"] if k[1] == z["betrag_cent"] else [f"aufgerundet (+{(z['betrag_cent'] - k[1]) / 100:.2f} €)".replace(".", ",")])
                    frei_treffer.append({"spiel": sid, "tickets": k[0], "summe": k[1], "gruende": g})
                    continue
                preise = sorted({offen[nr] for nr, _, _ in nrs if offen[nr]})
                for p in preise:
                    if p and z["betrag_cent"] % p == 0 and z["betrag_cent"] // p <= len(nrs):
                        fremd.append({"spiel": sid, "karten": z["betrag_cent"] // p, "preis_cent": p,
                                      "tickets": [nr for nr, n, _ in nrs if n]})
                        break
            moeglich = frei_treffer + moeglich
            treffer = frei_treffer
            if not frei_treffer and len(fremd) == 1:
                wahl = fremd[0]
        if ort_konflikt:
            treffer = []                                               # Mitteilung nennt ein Spiel, das so nicht im Bestand ist
    seen, liste = set(), []
    for m in sorted(moeglich, key=lambda m: ("Betrag passt" not in m["gruende"] and not any(g.startswith("aufgerundet") for g in m["gruende"]),
                                            m["spiel"] not in erw, "Preis unbekannt" not in m["gruende"], m["spiel"])):
        key = (m["spiel"], tuple(m["tickets"]))
        if key not in seen:
            seen.add(key)
            liste.append(m)
    out = {"zuordnung": "offen", "tickets": [], "vorschlaege": liste[:4]}
    if wahl:
        out["wahl"] = wahl
    if len(treffer) == 1:
        out.update(zuordnung="auto", tickets=treffer[0]["tickets"])
    elif not treffer and not erw and (m := _MERCH.search(z.get("mitteilung") or "") or _SPENDE.search(z.get("mitteilung") or "")):
        spende = bool(_SPENDE.search(m.group(0)))
        out.update(zuordnung="info", grund="Spende laut Mitteilung" if spende else "Merch laut Mitteilung (kein Ticket)",
                   art="spende" if spende else "merch")
    return out


def _offen(st: dict) -> dict:
    """Ticketnr -> noch offener Betrag (Preis - bereits bezahlt)."""
    bz = bezahlt_stand(st)["tickets"]
    return {nr: max((t.get("preis_cent") or 0) - bz[nr]["bezahlt_cent"], 0) for nr, t in st["tickets"].items()
            if not bz[nr]["bezahlt"]}


def _neu_bewerten(e: dict) -> bool:
    """Automatisch entschiedene/offene Eintraege ohne Klick des CEO werden bei jedem Lauf neu bewertet."""
    if e.get("von_hand") or e.get("zuordnung") in ("manuell", "ignoriert"):
        return False
    return e.get("zuordnung") == "offen" or (e.get("v") != VERSION and e.get("zuordnung") in ("auto", "info"))


def _gleich(a: dict, b: dict) -> bool:
    keys = ("zuordnung", "tickets", "wahl", "grund", "art", "beitrag")
    if [(tuple((x["nummer"], x["jahr"]) for x in m["beitrag"])) for m in a.get("beitrag_vorschlaege") or []] != \
            [(tuple((x["nummer"], x["jahr"]) for x in m["beitrag"])) for m in b.get("beitrag_vorschlaege") or []]:
        return False
    return all(a.get(k) == b.get(k) for k in keys) and [(m["spiel"], m["tickets"]) for m in a.get("vorschlaege") or []] \
        == [(m["spiel"], m["tickets"]) for m in b.get("vorschlaege") or []] and a.get("v") == b.get("v")


def eingang_plan(store: OfcStore, mails: list[dict], mitglieder: dict | None = None) -> dict:
    """Dry-Run: neue (und neu bewertete) Eingaenge mit Vorschlag/Auto-Zuordnung -- schreibt nichts.
    Mit Mitgliederliste (OFC-Kasse KA1) werden auch Beitragszahlungen erkannt."""
    from . import ofc_beitraege as ob
    st = store.stand()
    alt = {i: e for i, e in st.get("eingaenge", {}).items() if _neu_bewerten(e)}
    if alt:                                                            # ohne Klick: Bewertung zaehlt nicht, wird neu gemacht
        st = st | {"eingaenge": {i: e for i, e in st["eingaenge"].items() if i not in alt}}
    bekannt = st.get("eingaenge", {})
    offen = _offen(st)
    from datetime import date as _d
    offen_b = ob.offene_beitraege(st, mitglieder, _d.today().year + 2) if mitglieder else {}
    neu = []
    for z in eingaenge_aus_mails(mails):
        if z["id"] in bekannt:
            continue
        e = z | vorschlag(z, st, offen)
        bv = ob.beitrag_vorschlag(z, st, mitglieder, offen_b) if mitglieder else None
        wort = bool(ob.BEITRAG_WORT.search(z.get("mitteilung") or ""))
        if bv:
            e["beitrag_vorschlaege"] = bv["vorschlaege"]
            if bv["auto"] and (wort or e["zuordnung"] != "auto"):
                e.update(zuordnung="auto", tickets=[], art="beitrag", beitrag=bv["auto"], grund=ob.beitrag_text(bv["auto"]))
                for b in bv["auto"]:
                    offen_b.pop(f"{b['nummer']}|{b['jahr']}", None)
        if wort and e["zuordnung"] == "info" and e.get("art") in ("merch", "spende"):
            e.update(zuordnung="offen", art=None, grund=None)            # „Beitrag“ in der Mitteilung -> per Klick
        if e["zuordnung"] == "auto" and e.get("art") != "beitrag":
            e["art"] = "ticket"
        for nr in e["tickets"]:                                         # im selben Lauf nicht doppelt vergeben
            offen.pop(nr, None)
        e.setdefault("art", None)
        e.setdefault("beitrag", [])
        e.setdefault("grund", None)
        e.setdefault("beitrag_vorschlaege", [])
        neu.append(e)
    _teilzahlungen(neu, st, offen)
    neu = [e for e in neu if not (e["id"] in alt and _gleich(alt[e["id"]], e))]
    return {"ok": True, "neu": neu, "auto": sum(1 for e in neu if e["zuordnung"] == "auto"),
            "offen": sum(1 for e in neu if e["zuordnung"] == "offen"),
            "neu_bewertet": sum(1 for e in neu if e["id"] in alt)}


def _teilzahlungen(neu: list[dict], st: dict, offen: dict) -> None:
    """Gleicher Zahler, mehrere offene Betraege binnen 3 Tagen, die zusammen genau passen (z. B. 81 € + 1 €)."""
    from datetime import date as _d
    gruppen: dict = {}
    for e in neu:
        if e["zuordnung"] == "offen" and e["betrag_cent"] > 0:
            gruppen.setdefault(_norm(e["name"]), []).append(e)
    for es in gruppen.values():
        if len(es) < 2:
            continue
        for k in range(min(len(es), 3), 1, -1):
            for kombi in combinations(es, k):
                try:
                    tage = [_d.fromisoformat(e["datum"]) for e in kombi]
                except ValueError:
                    continue
                if (max(tage) - min(tage)).days > 3 or any(e["zuordnung"] != "offen" for e in kombi):
                    continue
                summe = {"name": kombi[0]["name"], "betrag_cent": sum(e["betrag_cent"] for e in kombi),
                         "mitteilung": " ".join(e.get("mitteilung") or "" for e in kombi)}
                v = vorschlag(summe, st, offen)
                if v["zuordnung"] != "auto":
                    continue
                for e in kombi:
                    e.update(zuordnung="auto", tickets=list(v["tickets"]), grund="Teilzahlungen zusammen", art="ticket")
                for nr in v["tickets"]:
                    offen.pop(nr, None)


def eingang_anwenden(store: OfcStore, mails: list[dict], *, von: str = "", mitglieder: dict | None = None) -> dict:
    plan = eingang_plan(store, mails, mitglieder)
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
    store.erfassen("ofc_eingang", {"id": eid, "tickets": [] if ignorieren else list(tickets), "zuordnung": zu, "von_hand": True,
                                   "art": "sonstiges" if ignorieren else ("ticket" if tickets else None), "beitrag": []},
                   von=von)                                            # Klick des CEO -> wird nie automatisch neu bewertet
    neu_alias = []
    if zu == "manuell":
        zahler = _woerter(_falten(e.get("name") or ""))
        for nr in tickets:
            tn = st["tickets"][nr].get("name") or ""
            if tn and not _name_passt(tn, [zahler]) and tn not in neu_alias:
                neu_alias.append(tn)
        for tn in neu_alias:
            store.erfassen("ofc_alias", {"zahler": _norm(e.get("name") or ""), "name": tn}, von=von)
    return {"ok": True, "id": eid, "zuordnung": zu, "tickets": [] if ignorieren else list(tickets), "aliase_neu": neu_alias}


def eingang_art(store: OfcStore, eid: str, art: str, *, beitrag: list[dict] | None = None, mitglieder: dict | None = None,
               von: str = "") -> dict:
    """OFC-Kasse KA1: Art eines Eingangs per Klick setzen -- Beitrag (Mitglied + Jahr), Merch, Spende, Sonstiges.
    Bei „Beitrag“ wird der Betrag der Reihe nach auf die offenen Beitraege verteilt; ein Zahler mit anderem Namen
    als das Mitglied wird als Alias gelernt (Familie zahlt mit)."""
    from . import ofc_beitraege as ob
    st = store.stand()
    e = st.get("eingaenge", {}).get(eid)
    if not e:
        return {"ok": False, "hinweis": "Zahlungseingang nicht gefunden."}
    if art not in ARTEN or art == "ticket":
        return {"ok": False, "hinweis": "Art unbekannt."}
    items, neu_alias = [], []
    if art == "beitrag":
        ms = {p["nummer"]: p for p in ob._mitglieder(mitglieder) if p.get("nummer")}
        if not beitrag or not ms:
            return {"ok": False, "hinweis": "Mitglied und Jahr wählen (Mitgliederliste nötig)."}
        offen_b = ob.offene_beitraege(st, mitglieder, max(int(b.get("jahr") or 0) for b in beitrag))
        rest = e.get("betrag_cent", 0)
        for i, b in enumerate(beitrag):
            nr, j = str(b.get("nummer") or ""), int(b.get("jahr") or 0)
            if nr not in ms or not 2000 <= j <= 2100:
                return {"ok": False, "hinweis": f"Mitglied {nr} / Jahr {j} unbekannt."}
            soll = offen_b.get(f"{nr}|{j}", ob.soll(ms[nr], j)["soll_cent"])
            teil = rest if i == len(beitrag) - 1 else min(rest, soll)
            items.append({"nummer": nr, "name": ms[nr].get("name", ""), "jahr": j, "cent": max(teil, 0)})
            rest -= max(teil, 0)
        zahler = _woerter(_falten(e.get("name") or ""))
        for b in items:
            if not ob._name_passt_mitglied(ms[b["nummer"]], zahler) and b["nummer"] not in neu_alias:
                neu_alias.append(b["nummer"])
    store.erfassen("ofc_eingang", {"id": eid, "tickets": [], "zuordnung": "manuell", "von_hand": True, "art": art,
                                   "beitrag": items, "grund": ob.beitrag_text(items) if items else None}, von=von)
    for nr in neu_alias:
        store.erfassen("ofc_beitrag_alias", {"zahler": _norm(e.get("name") or ""), "nummer": nr}, von=von)
    return {"ok": True, "id": eid, "art": art, "beitrag": items, "aliase_neu": neu_alias}


def lauf(store: OfcStore, postfach, *, von: str = "auto", mitglieder: dict | None = None) -> dict:
    try:
        if not postfach.verfuegbar():
            return {"ok": False, "hinweis": "Postfach moin@ ist nicht eingerichtet."}
        return eingang_anwenden(store, postfach.posteingang(tage=TAGE, nur=PAYPAL_DOMAINS), von=von, mitglieder=mitglieder)
    except Exception as exc:
        return {"ok": False, "hinweis": f"Postfach-Abruf fehlgeschlagen ({exc.__class__.__name__})."}
