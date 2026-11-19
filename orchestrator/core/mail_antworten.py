"""MAILVERSAND_ALLINKL M2: Kundenantworten im Postfach luna@hanserautisch.de erkennen.

Laeuft im 15-Minuten-Poll des Bots, nur wenn der Kundenversand auf All-Inkl steht. Zuordnung:
1. `In-Reply-To`/`References` enthaelt die Message-ID einer von LUNA gesendeten Mail (`<luna-…@hanserautisch.de>`,
   Kennung steht im Versand-Ereignis des Belegs) -> dieser Beleg;
2. sonst eine Belegnummer im Betreff -- aber nur fuer Belege, die LUNA ueber All-Inkl verschickt hat (keine Zufallstreffer).

Dann: Angebot -> wie bei Gmail als Antwort am Angebot (Verlauf + .eml-Archiv); alle anderen Belege -> Mail in die
Firmenakte mit Bezug (Rechnung/Mahnung: Bezug = Rechnung, erscheint in der Rechnung unter Dokumente). Jede Antwort wird
genau einmal erfasst (Ereignis `mail_antwort`) und per Telegram gemeldet. Das Postfach wird nur gelesen (Gelesen-Status
bleibt), nichts verschoben oder geloescht. Mails ohne Zuordnung bleiben unberuehrt im Postfach.

KONTAKTE K3: freie Mails an einen Ansprechpartner (Ereignis `kontakt_mail_gesendet`, ab K4 aus LUNA-OS) werden **nur**
ueber die Kennung (`In-Reply-To`/`References`) zugeordnet, nie ueber den Betreff: Antwort -> Firmenakte mit Firma und
Ansprechpartner, Meldung „Antwort von <Name> (<Firma>)“. Bei allen Antworten wird der Ansprechpartner zusaetzlich ueber
die Absenderadresse erkannt, wenn sie bei der Firma hinterlegt ist. `trocken=True` = nur auflisten, nichts schreiben.
"""
from __future__ import annotations

import email
import hashlib
import re
from email import policy
from email.utils import parseaddr

KENNUNG = re.compile(r"<(luna-[0-9a-f]{24})@", re.I)
BELEGNR = re.compile(r"\b(?:AN|AB|RE|MA|ZE)-\d{4}-\d{4}\b|\bRG-\d{6,8}\b", re.I)
TESTMAIL = "TESTMAIL"                                          # Testmail aus LUNA-OS (Gate M2): nur melden, nichts ablegen
KONTAKT_GESENDET = "kontakt_mail_gesendet"                     # K3/K4: freie Mail an einen Ansprechpartner
ART = {"AN": "Angebot", "AB": "Auftrag", "RE": "Rechnung", "RG": "Rechnung", "MA": "Mahnung", "ZE": "Zahlungserinnerung"}


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


def kontakt_mail_vermerken(bh, *, firma: str, ansprechpartner: str, message_id: str, betreff: str = "", an=None,
                           kanal: str = "allinkl", akte_id: str = "", von: str = "") -> dict:
    """K4 ruft das nach erfolgreichem Versand: ab dann erkennt der Poll Antworten auf diese Mail (Kennung)."""
    mid = str(message_id or "").strip().strip("<>")
    kennung = (KENNUNG.findall(f"<{mid if '@' in mid else mid + '@'}>") or [""])[0].lower()   # auch nackte Kennung (Versand-id)
    if not kennung or not firma:
        raise ValueError("Kennung der gesendeten Mail und Firma sind Pflicht.")
    return bh.erfassen(KONTAKT_GESENDET, {"firma": str(firma).upper(), "ansprechpartner": str(ansprechpartner or "").upper(),
                                          "message_id": kennung, "betreff": str(betreff or "")[:200], "an": an or [],
                                          "kanal": kanal, "akte_id": akte_id}, von=von)


def kontakt_mails(eintraege: list[dict]) -> dict:
    """-> {kennung: {firma, ansprechpartner, betreff}} aller freien Mails an Ansprechpartner."""
    return {str(e["daten"].get("message_id") or "").lower(): e["daten"] for e in eintraege
            if e.get("typ") == KONTAKT_GESENDET and str(e["daten"].get("message_id") or "").startswith("luna-")}


def kontakt_zuordnen(roh: bytes, km: dict) -> dict | None:
    """Antwort auf eine freie Mail? Nur ueber die Kennung -- ein Betreff wie „Re: Hallo“ beweist nichts."""
    m = email.message_from_bytes(roh, policy=policy.default)
    for k in KENNUNG.findall(" ".join(str(m.get(h, "")) for h in ("In-Reply-To", "References"))):
        if k.lower() in km:
            return km[k.lower()]
    return None


def ap_zu_adresse(kunden, firma: str, adresse: str) -> dict | None:
    """Ansprechpartner der Firma mit genau dieser Mailadresse (sonst None)."""
    adresse = (adresse or "").strip().lower()
    f = kunden.firma(firma) if firma and adresse else None
    for a in (f or {}).get("ansprechpartner_liste") or []:
        if str(a.get("mail") or "").strip().lower() == adresse:
            return a
    return None


def _name(ap: dict | None) -> str:
    return " ".join(x for x in ((ap or {}).get("vorname", ""), (ap or {}).get("nachname", "")) if x).strip()


def erfasste(eintraege: list[dict]) -> set[str]:
    return {e["daten"].get("id") for e in eintraege if e.get("typ") == "mail_antwort"}


def art(nummer: str) -> str:
    if nummer.startswith("K-"):
        return "Vorstellung an"                                # V1: Vorstellungs-Mail an eine Firma
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


def _beleg_firma(bh, kunden, nummer: str) -> str:
    """Firma eines Belegs (fuer die Ansprechpartner-Erkennung ueber die Absenderadresse); leer, wenn unbekannt."""
    if not nummer or nummer == TESTMAIL:
        return ""
    from .firmenakte import Firmenakte
    try:
        return Firmenakte(bh, kunden)._beleg_firma(nummer)[1]
    except Exception:
        return ""


def antworten_pruefen(bh, kunden, postfach, *, eigene: list[str], notify=None, tage: int = 30, von: str = "LUNA-Mail",
                      trocken: bool = False) -> list[dict]:
    """Neue Kundenantworten erfassen, ablegen und melden. Rueckgabe: Liste der neuen Antworten.
    `trocken=True`: nur zeigen, was zugeordnet wuerde -- nichts erfassen, ablegen oder melden."""
    from .angebote import AngebotStore
    from .firmenakte import Firmenakte
    eintraege = bh.eintraege()
    zu, mahn_re = gesendete(eintraege)
    km = kontakt_mails(eintraege)
    if not zu and not km:
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
        kontakt = kontakt_zuordnen(roh, km)
        nummer = kontakt["firma"] if kontakt else zuordnen(roh, zu, mahn_re)
        if not absender or not nummer or (absender in eigene and nummer != TESTMAIL):
            continue                                           # CEO/LUNA zaehlen nie als Kunde -- ausser beim Testlauf
        info = {"id": key, "nummer": nummer, "von": str(m.get("From", ""))[:200], "datum": str(m.get("Date", ""))[:80],
                "betreff": str(m.get("Subject", ""))[:200], "vorschau": _vorschau(roh), "kanal": "allinkl"}
        firma_nr = nummer if (kontakt or nummer.startswith("K-")) else ""
        ap = ap_zu_adresse(kunden, firma_nr or _beleg_firma(bh, kunden, mahn_re.get(nummer, nummer)), absender)
        ap_nr = (ap or {}).get("nummer") or (kontakt or {}).get("ansprechpartner", "")
        if kontakt:
            info["art"] = "kontakt"
        if ap_nr:
            info["ansprechpartner"] = ap_nr
        if trocken:
            neu.append(info | {"ablage": "trocken"})
            continue
        if nummer == TESTMAIL:
            info["ablage"] = "keine"
        elif nummer.startswith("AN-"):
            st = AngebotStore(bh, kunden)
            st.antwort_erfassen(nummer, {"id": key, "von": info["von"], "datum": info["datum"], "vorschau": info["vorschau"]},
                                von=von)
            st.mail_archivieren(nummer, key, roh, richtung="ein", von=von)
            info["ablage"] = "angebot"
        else:
            bezug = mahn_re.get(nummer, nummer)
            r = Firmenakte(bh, kunden).mail_aufnehmen(roh, key, eigene=eigene, weitergeleitet=False, von=von,
                                                      bezug="" if firma_nr else bezug, firma=firma_nr,
                                                      ansprechpartner=ap_nr)
            info |= {"ablage": "akte", "akte_id": r["id"], "bezug": bezug}
        bh.erfassen("mail_antwort", info, von=von)
        schon.add(key)
        neu.append(info)
        if notify:
            try:
                if nummer == TESTMAIL:
                    notify(f"✉️ Antwort auf die LUNA-Testmail von {info['von']} erkannt – die Antwort-Erkennung ueber "
                           f"luna@hanserautisch.de funktioniert. „{info['vorschau'][:120]}“", abteilung="CRO", kategorie="crm",
                           quelle="mail_antworten")
                    continue
                if kontakt:
                    f = kunden.firma(nummer) or {}
                    person = _name(ap) or _name(next((a for a in f.get("ansprechpartner_liste") or []
                                                      if a.get("nummer") == ap_nr), None)) or info["von"]
                    notify(f"✉️ Antwort von {person} ({f.get('name', nummer)}): {info['vorschau'][:160]}",
                           abteilung="CRO", kategorie="crm", quelle="mail_antworten",
                           detail=f"LUNA-OS -> Firma {f.get('name', '')} ({nummer}) -> Akte (Postfach luna@hanserautisch.de)")
                    continue
                a = art(nummer)
                wer = f"{(kunden.firma(nummer) or {}).get('name', '')} ({nummer})" if nummer.startswith("K-") else nummer
                notify(f"✉️ Antwort auf {a} {wer} von {info['von']}: {info['vorschau'][:160]}",
                       abteilung="CRO", kategorie="crm", quelle="mail_antworten",
                       detail=f"LUNA-OS -> {a} {wer} (Postfach luna@hanserautisch.de)")
            except Exception:
                pass
    return neu
