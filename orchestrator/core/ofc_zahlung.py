"""OFC_ROADMAP O4: Eigene PayPal-Zahlungen (an Eventim/HSV) den Spielen zuordnen -- regelbasiert, keine KI.

- Quelle: PayPal-Mails im Fanclub-Postfach (nur `paypal.de`/`paypal.com`, nur lesend). Erkannt werden Belege „Zahlung
  gesendet“, „Später bezahlen“ (Kauf jetzt, Abbuchung nach 30 Tagen), Abbuchung erfolgreich/fehlgeschlagen und Erstattungen.
  Zahlungseingaenge der Mitglieder (O5) und Zahlungen an andere Haendler werden hier ignoriert.
- Zuordnung: Rechnungs-/Auftrags-/Bestellnummer im Mailtext (sicher), Betrag = Rechnungssumme, Zeitfenster zur Rechnung,
  Gegner im Text, Kauf vor dem Spieltag. Eindeutig -> automatisch; sonst Vorschlag -> „Zuordnen“ per Klick.
- Gespeichert wird nur das Ergebnis (Betrag, Datum, Haendler, Bestellnr, Transaktionscode, Spiel) als Ereignis
  `ofc_zahlung` in `fanclub/log.jsonl` -- kein Mailtext. Getrennt von der Buchhaltung.
"""
from __future__ import annotations

import email
import hashlib
import re
from datetime import date, timedelta
from email import policy
from email.utils import parseaddr, parsedate_to_datetime

from . import ofc
from .ofc_store import OfcStore

PAYPAL_DOMAINS = ("paypal.de", "paypal.com")
TAGE = 120
FRIST_SPAETER = 30
VERSION = 3                       # Erkennungsstand; automatisch erzeugte Eintraege aelterer Fassung werden neu bewertet
_HAENDLER_OK = re.compile(r"eventim|hamburger\s*s(port|v)|\bhsv\b|fu(ss|ß)ball\s*ag", re.I)
_MONATE = {m: i + 1 for i, m in enumerate(("januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
                                           "september", "oktober", "november", "dezember"))}
_MONATE |= {"maerz": 3, "jan": 1, "feb": 2, "mär": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
            "okt": 10, "nov": 11, "dez": 12}
_BETRAG = r"(-?[\d.]*\d,\d\d)\s*(?:€|EUR)"


def _cent(s: str) -> int:
    return int(round(float(s.replace(".", "").replace(",", ".")) * 100))


def _datum(text: str) -> str:
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text)
    if m:
        try:
            return date(int(m[3]), int(m[2]), int(m[1])).isoformat()
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})\.?\s+([A-Za-zÄÖÜäöü]+)\.?\s+(\d{4})\b", text)
    if m and m[2].lower() in _MONATE:
        try:
            return date(int(m[3]), _MONATE[m[2].lower()], int(m[1])).isoformat()
        except ValueError:
            pass
    return ""


def _nach(label: str, text: str) -> str:
    """Erste nicht leere Zeile nach einer Zeile, die mit `label` beginnt."""
    zeilen = [z.strip() for z in text.splitlines()]
    for i, z in enumerate(zeilen):
        if z.lower().startswith(label.lower()):
            rest = z[len(label):].strip(" :")
            if rest:
                return rest
            return next((x for x in zeilen[i + 1:] if x), "")
    return ""


def art_der_mail(betreff: str, text: str) -> str:
    a = f"{betreff}\n{text}"
    if re.search(r"(Zahlung|Geld)\s+(erhalten|empfangen)|hat Ihnen .{0,40}gesendet|You.ve got money", a, re.I) and \
            not re.search(r"Rückzahlung|Rueckzahlung|Erstattung", betreff, re.I):
        return ""                                                    # Eingang (Mitglied) -> O5, nicht hier
    if re.search(r"Sie bezahlen in \d+ Tagen|Später bezahlen|Spaeter bezahlen|nach \d+ Tagen", a, re.I) and \
            re.search(r"Kauf|Einkauf|bezahlen in", a, re.I) and not re.search(r"wird in .{0,20}abgebucht|eingezogen|erfolgreich", betreff, re.I):
        return "spaeter"
    if re.search(r"konnte nicht eingezogen|abgelehnt|fehlgeschlagen", betreff, re.I):
        return "abbuchung_fehler"
    if re.search(r"Zahlung mit PayPal war erfolgreich|wurde abgebucht|erfolgreich eingezogen", betreff, re.I):
        return "abbuchung_ok"
    if re.search(r"wird in .{0,20}abgebucht", betreff, re.I):
        return "abbuchung_hinweis"
    if re.search(r"Rückzahlung|Rueckzahlung|Erstattung|erstattet|Gutschrift", betreff, re.I):
        return "erstattung"
    if re.search(r"(Zahlung|Geld).{0,60}(gesendet|an )|Beleg f\S*r Ihre Zahlung|Sie haben .{0,40} an .{0,80} gezahlt", a, re.I):
        return "gesendet"
    return ""


def paypal_lesen(roh: bytes) -> dict | None:
    """Eine PayPal-Mail -> Zahlung (ohne Mailtext) oder None (kein eigener Ticketkauf)."""
    m = email.message_from_bytes(roh, policy=policy.default)
    dom = parseaddr(str(m.get("From", "")))[1].lower().rpartition("@")[2]
    if not any(dom == d or dom.endswith("." + d) for d in PAYPAL_DOMAINS):
        return None
    betreff = str(m.get("Subject", ""))
    text = ofc._text(m).replace("\xa0", " ")
    art = art_der_mail(betreff, text)
    if not art:
        return None
    alles = f"{betreff}\n{text}"
    h = re.search(r"an\s+(.+?)(?:\.\.\.|…)?\s+gezahlt", alles) or re.search(r"Zahlung an\s+(.+?)(?:\.\.\.|…|\n|$)", alles) \
        or re.search(r"\bbei\s+(.+?)(?:\.\.\.|…)?\s*(?:–|-|\n|\.|$)", alles)
    haendler = (h[1].strip() if h else "") or _nach("Händler", text) or _nach("Haendler", text)
    haendler = re.sub(r"\s+", " ", haendler.rstrip(". …"))[:80]
    b = re.search(r"(?:Sie haben|über|ueber)\s+" + _BETRAG, alles) or re.search(r"Gesamtbetrag\s*\n?\s*" + _BETRAG, text) \
        or re.search(_BETRAG, alles)
    if not b:
        return None
    try:
        gesendet = parsedate_to_datetime(str(m.get("Date", ""))).date().isoformat()
    except Exception:
        gesendet = ""
    tc = re.search(r"Transaktions(?:code|-ID|nummer)\s*:?\s*([A-Z0-9]{10,20})", text)
    bnr = _nach("Bestellnummer", text)
    bnr = bnr if re.fullmatch(r"[\w-]{4,30}", bnr or "") else ""
    lab = re.search(r"Datum de[rs]\s+([A-Za-zÄÖÜäöüß]+)", text)
    datum = _datum(_nach("Datum des", text) or "") or _datum(text) or gesendet
    faellig = ""
    if art == "spaeter" and datum:
        # Zwei Mails je Kauf (Probelauf 2026-11-24): Kaufmail („… nach 30 Tagen“, Datum = Kauf) und Erinnerung vor der
        # Abbuchung („Sie bezahlen in N Tagen“, Datum = Einzug). Erinnerung -> Kaufdatum = Einzug - 30 Tage.
        n = re.search(r"Sie bezahlen in (\d+) Tag", betreff, re.I)
        if n:
            einzug = datum if not (lab and re.search(r"kauf|bestell", lab[1], re.I)) else ""
            if not einzug and gesendet:
                einzug = (date.fromisoformat(gesendet) + timedelta(days=int(n[1]))).isoformat()
            faellig = einzug or datum
            datum = (date.fromisoformat(faellig) - timedelta(days=FRIST_SPAETER)).isoformat()
        else:
            faellig = (date.fromisoformat(datum) + timedelta(days=FRIST_SPAETER)).isoformat()
    z = {"art": art, "betrag_cent": abs(_cent(b[1])), "datum": datum or gesendet, "mail_datum": gesendet,
         "haendler": haendler, "bestellnr": bnr, "transaktionscode": tc[1] if tc else "", "v": VERSION,
         "nummern": sorted(set(re.findall(r"\b\d{6,14}\b", alles)))}
    if faellig:
        z["faellig"] = faellig
    schluessel = f"{art}|{z['betrag_cent']}|{z['datum']}" if art == "spaeter" else \
        f"{art}|{z['betrag_cent']}|{z['datum']}|{haendler.lower()}|{bnr}|{m.get('Message-ID', '')}"
    z["id"] = z["transaktionscode"] or "z-" + hashlib.sha1(schluessel.encode()).hexdigest()[:16]
    z["_text"] = alles.lower()                                       # nur fuer die Zuordnung, wird nie gespeichert
    if art in ("gesendet", "spaeter", "erstattung") and not _HAENDLER_OK.search(haendler):
        return None                                                  # andere Haendler (z. B. Dropbox) -> nicht OFC
    return z


# -- Zuordnung -------------------------------------------------------------------------------------------------------
def kandidaten(z: dict, st: dict, belegt: set | None = None) -> list[tuple[int, str, list[str]]]:
    """Punkte je Spiel: (punkte, spiel_id, gruende), absteigend. `belegt`: (spiel, betrag) schon bezahlt -> kein Betrags-Treffer."""
    belegt = belegt or set()
    out = []
    nummern = set(z.get("nummern") or []) | ({z["bestellnr"]} if z.get("bestellnr") else set())
    text = z.get("_text", "")
    je_rg: dict = {}
    for t in st["tickets"].values():
        je_rg.setdefault((t["spiel"], t.get("rechnungsnr")), 0)
        je_rg[(t["spiel"], t.get("rechnungsnr"))] += t.get("preis_cent") or 0
    for sid, s in st["spiele"].items():
        if s.get("verworfen"):
            continue
        p, g = 0, []
        rg = s.get("rechnungen") or []
        refs = {str(r.get(k)) for r in rg for k in ("rechnungsnr", "auftragsnr") if r.get(k)}    # Kunden-Nr ist bei allen gleich
        refs |= {t.get("rechnungsnr") for t in st["tickets"].values() if t["spiel"] == sid and t.get("rechnungsnr")}
        if nummern & refs:
            p += 100; g.append("Nummer passt")
        summen = {r.get("summe_cent") for r in rg if r.get("summe_cent")} | {v for (sp, _), v in je_rg.items() if sp == sid and v}
        if z["betrag_cent"] in summen and (sid, z["betrag_cent"]) not in belegt:
            p += 50; g.append("Betrag = Rechnung")
        tage = [r.get("datum") for r in rg if r.get("datum")]
        if z.get("datum") and any(-3 <= (date.fromisoformat(z["datum"]) - date.fromisoformat(d)).days <= 14 for d in tage):
            p += 20; g.append("Datum nahe Rechnung")
        gegner = [w for w in re.split(r"[\s-]+", (s.get("gegner") or "").lower()) if len(w) >= 4 and w not in ("hamburger", "fc", "verein")]
        if gegner and any(w in text for w in gegner):
            p += 25; g.append("Gegner im Beleg")
        if z.get("datum") and s.get("spieltag") and z["datum"] <= s["spieltag"]:
            p += 5
        if p > 5:
            out.append((p, sid, g))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def _entscheiden(z: dict, st: dict, belegt: set | None = None) -> dict:
    if z["art"] not in ("gesendet", "spaeter", "erstattung"):
        return {"spiel": "", "zuordnung": "info", "vorschlaege": []}
    k = kandidaten(z, st, belegt)
    vs = [{"spiel": sid, "punkte": p, "gruende": g} for p, sid, g in k[:3]]
    if k and k[0][0] >= 70 and (len(k) == 1 or k[1][0] < k[0][0]):
        return {"spiel": k[0][1], "zuordnung": "auto", "vorschlaege": vs}
    return {"spiel": "", "zuordnung": "offen", "vorschlaege": vs}


def _gleicher_kauf(a: dict, b: dict) -> bool:
    """„Später bezahlen“: Kauf- und Erinnerungsmail desselben Kaufs (gleicher Betrag, Kaufdatum +-3 Tage)."""
    return a["art"] == b["art"] == "spaeter" and a["betrag_cent"] == b["betrag_cent"] and \
        abs((date.fromisoformat(a["datum"]) - date.fromisoformat(b["datum"])).days) <= 3


def zahlungen_aus_mails(mails: list[dict]) -> list[dict]:
    out, ids = [], set()
    for x in mails:
        try:
            z = paypal_lesen(x["roh"])
        except Exception:
            continue
        if z and z["id"] not in ids and not any(_gleicher_kauf(z, o) for o in out):
            ids.add(z["id"])
            out.append(z)
    return sorted(out, key=lambda z: (z["datum"], z["id"]))


def zahl_plan(store: OfcStore, mails: list[dict]) -> dict:
    """Dry-Run: neue Zahlungen und ihre Zuordnung. Per Klick gesetzte (manuell/ignoriert) bleiben, wie sie sind;
    automatisch erzeugte Eintraege aelterer Erkennung (`v` < VERSION) werden neu bewertet bzw. als ersetzt markiert."""
    st = store.stand()
    alle = {i: z for i, z in st.get("zahlungen", {}).items() if not z.get("ersetzt")}
    alt = {i for i, z in alle.items() if z.get("v") != VERSION and z.get("zuordnung") in ("auto", "offen", "info")}
    bekannt = {i: z for i, z in alle.items() if i not in alt}
    belegt = {(z["spiel"], z.get("betrag_cent")) for z in bekannt.values() if z.get("spiel")}
    neu, gesehen = [], set()
    for z in zahlungen_aus_mails(mails):
        gesehen.add(z["id"])
        if z["id"] in bekannt or any(_gleicher_kauf(z, b) for b in bekannt.values() if b.get("datum")):
            continue
        e = {k: v for k, v in z.items() if k != "_text"} | _entscheiden(z, st, belegt)
        if e["spiel"]:
            belegt.add((e["spiel"], e["betrag_cent"]))
        neu.append(e)
    ersetzt = sorted(alt - gesehen)
    return {"ok": True, "neu": neu, "ersetzt": ersetzt, "auto": sum(1 for z in neu if z["zuordnung"] == "auto"),
            "offen": sum(1 for z in neu if z["zuordnung"] == "offen")}


def zahl_anwenden(store: OfcStore, mails: list[dict], *, von: str = "") -> dict:
    plan = zahl_plan(store, mails)
    for zid in plan["ersetzt"]:
        store.erfassen("ofc_zahlung", {"id": zid, "ersetzt": True}, von=von)
    for z in plan["neu"]:
        store.erfassen("ofc_zahlung", {k: v for k, v in z.items() if k not in ("nummern",)}, von=von)
    return plan


def zuordnen(store: OfcStore, zid: str, spiel: str, *, ignorieren: bool = False, von: str = "") -> dict:
    st = store.stand()
    if zid not in st.get("zahlungen", {}):
        return {"ok": False, "hinweis": "Zahlung nicht gefunden."}
    if spiel and spiel not in st["spiele"]:
        return {"ok": False, "hinweis": "Spiel nicht gefunden."}
    zu = "ignoriert" if ignorieren else ("manuell" if spiel else "offen")
    store.erfassen("ofc_zahlung", {"id": zid, "spiel": "" if ignorieren else spiel, "zuordnung": zu}, von=von)
    return {"ok": True, "id": zid, "spiel": "" if ignorieren else spiel, "zuordnung": zu}


def zahlungs_status(st: dict, heute: date | None = None) -> list[dict]:
    """Alle eigenen Zahlungen mit Status; „Später bezahlen“ mit Faelligkeit und Abbuchung (gleicher Betrag, 45 Tage)."""
    heute = heute or date.today()
    zs = sorted((z for z in st.get("zahlungen", {}).values() if not z.get("ersetzt")), key=lambda z: (z.get("datum") or "", z["id"]))
    info = [z for z in zs if z.get("art") in ("abbuchung_ok", "abbuchung_fehler", "abbuchung_hinweis")]
    out = []
    for z in zs:
        if z.get("zuordnung") == "info":
            continue
        z = dict(z)
        if z.get("art") == "spaeter" and z.get("spiel"):
            rg = [r for r in (st["spiele"].get(z["spiel"]) or {}).get("rechnungen") or []
                  if r.get("summe_cent") == z["betrag_cent"] and r.get("datum")]
            if rg:
                z["datum"] = rg[0]["datum"]
                z["faellig"] = (date.fromisoformat(rg[0]["datum"]) + timedelta(days=FRIST_SPAETER)).isoformat()
        if z.get("art") == "spaeter" and z.get("datum"):
            faellig = date.fromisoformat(z.get("faellig") or (date.fromisoformat(z["datum"]) + timedelta(days=FRIST_SPAETER)).isoformat())
            z["faellig"] = faellig.isoformat()
            passt = [i for i in info if i.get("betrag_cent") == z["betrag_cent"] and i.get("datum")
                     and 0 <= (date.fromisoformat(i["datum"]) - date.fromisoformat(z["datum"])).days <= 45]
            if any(i["art"] == "abbuchung_fehler" for i in passt):
                z["abbuchung"] = "fehlgeschlagen"
            elif any(i["art"] == "abbuchung_ok" for i in passt) or faellig < heute - timedelta(days=5):
                z["abbuchung"] = "abgebucht"
            else:
                z["abbuchung"] = "offen"
        out.append(z)
    return out


def oeffentlich(plan: dict) -> dict:
    return {k: v for k, v in plan.items() if not k.startswith("_")}


def lauf(store: OfcStore, postfach, *, von: str = "auto") -> dict:
    try:
        if not postfach.verfuegbar():
            return {"ok": False, "hinweis": "Postfach moin@ ist nicht eingerichtet."}
        return oeffentlich(zahl_anwenden(store, postfach.posteingang(tage=TAGE, nur=PAYPAL_DOMAINS), von=von))
    except Exception as exc:
        return {"ok": False, "hinweis": f"Postfach-Abruf fehlgeschlagen ({exc.__class__.__name__})."}
