"""MAILVERSAND_ALLINKL M2: Kundenantworten im Postfach luna@hanserautisch.de erkennen.

Laeuft im 15-Minuten-Poll des Bots, nur wenn der Kundenversand auf All-Inkl steht. Zuordnung:
1. `In-Reply-To`/`References` enthaelt die Message-ID einer von LUNA gesendeten Mail (`<luna-…@hanserautisch.de>`,
   Kennung steht im Versand-Ereignis des Belegs) -> dieser Beleg;
2. sonst eine Belegnummer im Betreff -- aber nur fuer Belege, die LUNA ueber All-Inkl verschickt hat (keine Zufallstreffer).

Dann: Angebot -> wie bei Gmail als Antwort am Angebot (Verlauf + .eml-Archiv); alle anderen Belege -> Mail in die
Firmenakte mit Bezug (Rechnung/Mahnung: Bezug = Rechnung, erscheint in der Rechnung unter Dokumente). Jede Antwort wird
genau einmal erfasst (Ereignis `mail_antwort`) und per Telegram gemeldet. Das Postfach wird nur gelesen (Gelesen-Status
bleibt), nichts verschoben oder geloescht. Mails ohne Zuordnung bleiben unberuehrt im Postfach.
"""
from __future__ import annotations

import email
import hashlib
import re
from email import policy
from email.utils import parseaddr

KENNUNG = re.compile(r"<(luna-[0-9a-f]{24})@", re.I)
BELEGNR = re.compile(r"\b(?:AN|AB|RE|MA)-\d{4}-\d{4}\b|\bRG-\d{6,8}\b", re.I)
ART = {"AN": "Angebot", "AB": "Auftrag", "RE": "Rechnung", "RG": "Rechnung", "MA": "Mahnung"}


def schluessel(message_id: str, roh: bytes) -> str:
    """Stabile, dateinamen-taugliche ID einer eingehenden Mail (Message-ID, ersatzweise Inhalt)."""
    basis = (message_id or "").strip().encode() or roh
    return "imap-" + hashlib.sha256(basis).hexdigest()[:20]


def gesendete(eintraege: list[dict]) -> tuple[dict, dict]:
    """-> ({kennung: belegnummer}, {mahnung: rechnung}) aus allen Versand-Ereignissen der Kette (alle Belegarten)."""
    zu, mahn_re = {}, {}

    def suche(x, nummer):
        if isinstance(x, dict):
            mid = str(x.get("message_id") or "")
            if mid.startswith("luna-") and nummer:
                zu[mid] = nummer
            for v in x.values():
                suche(v, nummer)
        elif isinstance(x, list):
            for v in x:
                suche(v, nummer)
    for e in eintraege:
        d = e.get("daten") or {}
        nummer = str(d.get("nummer") or d.get("vorgang") or "").upper()
        if e.get("typ", "").startswith("mahnung") and d.get("rechnung") and d.get("nummer"):
            mahn_re[str(d["nummer"]).upper()] = str(d["rechnung"]).upper()
        suche(d, nummer)
    return zu, mahn_re


def erfasste(eintraege: list[dict]) -> set[str]:
    return {e["daten"].get("id") for e in eintraege if e.get("typ") == "mail_antwort"}


def art(nummer: str) -> str:
    return "Mahnung" if re.search(r"-M\d$", nummer) else ART.get(nummer[:2], "Beleg")


def zuordnen(roh: bytes, zu: dict, mahn_re: dict | None = None) -> str:
    m = email.message_from_bytes(roh, policy=policy.default)
    bezug = " ".join(str(m.get(h, "")) for h in ("In-Reply-To", "References"))
    for k in KENNUNG.findall(bezug):
        if k.lower() in zu:
            return zu[k.lower()]
    belege = set(zu.values()) | {(mahn_re or {}).get(n, n) for n in zu.values()}   # Mahnung gesendet -> Rechnung zaehlt
    for nr in BELEGNR.findall(str(m.get("Subject", ""))):
        if nr.upper() in belege:
            return nr.upper()
    return ""


def _vorschau(roh: bytes) -> str:
    from .angebote import mail_lesen
    text = mail_lesen(roh).get("text", "")
    zeilen = []
    for z in text.splitlines():
        if re.match(r"^\s*(>|Am .+schrieb|On .+wrote)", z):
            break                                              # zitierte Original-Mail weglassen
        if z.strip():
            zeilen.append(z.strip())
    return " ".join(zeilen)[:500]


def antworten_pruefen(bh, kunden, postfach, *, eigene: list[str], notify=None, tage: int = 30, von: str = "LUNA-Mail") -> list[dict]:
    """Neue Kundenantworten erfassen, ablegen und melden. Rueckgabe: Liste der neuen Antworten."""
    from .angebote import AngebotStore
    from .firmenakte import Firmenakte
    eintraege = bh.eintraege()
    zu, mahn_re = gesendete(eintraege)
    if not zu:
        return []                                              # noch nichts ueber All-Inkl verschickt
    schon = erfasste(eintraege)
    eigene = [a.strip().lower() for a in eigene if a and "@" in a]
    neu = []
    for x in postfach.posteingang(tage=tage):
        roh = x["roh"]
        m = email.message_from_bytes(roh, policy=policy.default)
        key = schluessel(str(m.get("Message-ID", "")), roh)
        if key in schon:
            continue
        absender = parseaddr(str(m.get("From", "")))[1].lower()
        if not absender or absender in eigene:
            continue
        nummer = zuordnen(roh, zu, mahn_re)
        if not nummer:
            continue
        info = {"id": key, "nummer": nummer, "von": str(m.get("From", ""))[:200], "datum": str(m.get("Date", ""))[:80],
                "betreff": str(m.get("Subject", ""))[:200], "vorschau": _vorschau(roh), "kanal": "allinkl"}
        if nummer.startswith("AN-"):
            st = AngebotStore(bh, kunden)
            st.antwort_erfassen(nummer, {"id": key, "von": info["von"], "datum": info["datum"], "vorschau": info["vorschau"]},
                                von=von)
            st.mail_archivieren(nummer, key, roh, richtung="ein", von=von)
            info["ablage"] = "angebot"
        else:
            bezug = mahn_re.get(nummer, nummer)
            r = Firmenakte(bh, kunden).mail_aufnehmen(roh, key, eigene=eigene, weitergeleitet=False, von=von, bezug=bezug)
            info |= {"ablage": "akte", "akte_id": r["id"], "bezug": bezug}
        bh.erfassen("mail_antwort", info, von=von)
        schon.add(key)
        neu.append(info)
        if notify:
            try:
                a = art(nummer)
                notify(f"✉️ Antwort auf {a} {nummer} von {info['von']}: {info['vorschau'][:160]}",
                       abteilung="CRO", kategorie="crm", quelle="mail_antworten",
                       detail=f"LUNA-OS -> {a} {nummer} (Postfach luna@hanserautisch.de)")
            except Exception:
                pass
    return neu
