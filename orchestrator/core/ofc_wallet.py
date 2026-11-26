"""OFC_TICKETVERSAND TV0: Analyse der HSV-Mails auf Wallet-Links (nur lesend, nichts gespeichert, CEO-Go 2026-11-26).

Ziel: herausfinden, wie die Wallet-Tickets in den HSV-Mails stehen (Link je Ticket oder je Bestellung, Host, Anhang
`.pkpass`, woran Link und Ticket zusammengehoeren), bevor TV1 sie speichert. Der Bericht enthaelt **nie** einen Link, einen
Namen oder einen Mailtext -- nur Zaehlungen, Hosts und maskierte Linktexte (nur Woerter aus einer festen Liste).
Keine KI; Mitgliederdaten bleiben im Code.
"""
from __future__ import annotations

import email
import html
import re
from collections import Counter
from email import policy
from urllib.parse import urlsplit

from . import ofc
from .ofc_post import HSV_DOMAINS, bestellungen_aus_mails

_RE_HREF = re.compile(r"""<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a\s*>""", re.I | re.S)
_RE_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_SPIELTAG = re.compile(r"\b\d{1,2}\.\s*Spieltag\b|\bSpieltag\s*:?\s*\d{1,2}\b|\b\d{1,2}\.\s*Runde\b", re.I)
WALLET_WOERTER = ("wallet", "pkpass", "passbook", "apple", "google", "pass", "gp/v/save")
# Woerter, die im maskierten Linktext stehen bleiben duerfen (alles andere -> „…“, Ziffern -> #)
_ERLAUBT = {"wallet", "apple", "google", "hinzufuegen", "hinzufügen", "zu", "zum", "zur", "in", "add", "to", "ticket", "tickets",
            "karte", "karten", "dein", "deine", "ihr", "ihre", "mobile", "handy", "smartphone", "download", "herunterladen",
            "pay", "jetzt", "hier", "oeffnen", "öffnen", "ansehen", "anzeigen", "pass", "passbook", "app", "fuer", "für"}


def _teile(roh: bytes) -> tuple[list[str], list[str], int]:
    """-> (html-Teile, text-Teile, Zahl der .pkpass-Anhaenge)."""
    m = email.message_from_bytes(roh, policy=policy.default)
    htmls, texte, pk = [], [], 0
    for teil in m.walk():
        ct = teil.get_content_type()
        name = (teil.get_filename() or "").lower()
        if ct == "application/vnd.apple.pkpass" or name.endswith(".pkpass"):
            pk += 1
            continue
        if teil.is_multipart() or teil.get_content_disposition() == "attachment":
            continue
        try:
            inhalt = teil.get_content()
        except Exception:
            continue
        if not isinstance(inhalt, str):
            continue
        (htmls if ct == "text/html" else texte if ct == "text/plain" else []).append(inhalt)
    return htmls, texte, pk


def _pdf(daten: bytes) -> str:
    try:
        return ofc.pdf_bytes_text(daten)
    except Exception:
        return ""


def _links(htmls: list[str], texte: list[str]) -> list[tuple[str, str]]:
    """Alle Links als (url, linktext). HTML-Anker zuerst; im Text nur nackte URLs ohne Linktext."""
    out, gesehen = [], set()
    for h in htmls:
        for url, inner in _RE_HREF.findall(h):
            url = html.unescape(url).strip()
            text = re.sub(r"\s+", " ", html.unescape(_RE_TAG.sub(" ", inner))).strip()
            if not text:                                      # Bild-Knopf: alt-Text nehmen
                alt = re.search(r"""alt\s*=\s*["']([^"']*)["']""", inner, re.I)
                text = alt.group(1).strip() if alt else ""
            out.append((url, text))
            gesehen.add(url)
    for t in texte:
        for url in _RE_URL.findall(t):
            if url not in gesehen:
                out.append((url, ""))
                gesehen.add(url)
    return out


def ist_wallet(url: str, text: str) -> bool:
    u, t = url.lower(), text.lower()
    return any(w in u for w in WALLET_WOERTER) or "wallet" in t


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def maskiert(text: str) -> str:
    """Linktext ohne Namen: nur Woerter aus der festen Liste bleiben, Ziffern -> #, alles andere -> …"""
    woerter = []
    for w in re.findall(r"\S+", text or "")[:12]:
        roh = re.sub(r"[^\wäöüß/]", "", w.lower())
        if roh in _ERLAUBT:
            woerter.append(roh)
        elif re.fullmatch(r"[\d#./:-]+", w):
            woerter.append(re.sub(r"\d", "#", w))
        else:
            woerter.append("…")
    return re.sub(r"(…\s*){2,}", "… ", " ".join(woerter)).strip()


def _pfad_muster(url: str) -> str:
    """Pfad ohne Inhalt: Ziffernfolgen -> #, lange Kennungen -> *, Abfrage-Werte weg (nur Namen der Parameter)."""
    try:
        s = urlsplit(url)
    except ValueError:
        return ""
    teile = []
    for seg in s.path.split("/")[1:6]:
        if re.fullmatch(r"\d+", seg):
            teile.append("#")
        elif len(seg) > 16 or re.search(r"\d{4,}", seg):
            teile.append("*")
        else:
            teile.append(seg.lower())
    q = sorted({p.split("=")[0] for p in s.query.split("&") if p})[:6]
    return "/" + "/".join(teile) + (("?" + "&".join(q)) if q else "")


def analyse(postfach, *, tage: int = 120, mitglieder: list[dict] | None = None, tickets: dict | None = None) -> dict:
    """TV0-Bericht. `tickets` = OfcStore.stand()['tickets'] (fuer die Adress-Abdeckung), `mitglieder` = OM-Liste."""
    mails = postfach.posteingang(tage=tage, nur=HSV_DOMAINS)
    hosts, muster, linktexte, verhaeltnis = Counter(), Counter(), Counter(), Counter()
    je_mail = []
    for x in mails:
        best, n = bestellungen_aus_mails([x])
        if not n:
            continue
        ticketnrn = {t for b in best.values() for t in b["tickets"]}
        htmls, texte, pk = _teile(x["roh"])
        alle = _links(htmls, texte)
        wallet = [(u, t) for u, t in alle if ist_wallet(u, t)]
        for u, t in wallet:
            hosts[_host(u)] += 1
            muster[_host(u) + _pfad_muster(u)] += 1
            linktexte[maskiert(t) or "(ohne Text)"] += 1
        nummern = {tn.replace("-", "") for tn in ticketnrn} | ticketnrn
        mit_nr_url = sum(1 for u, _ in wallet if any(n in u.replace("-", "") for n in nummern))
        mit_nr_text = sum(1 for _, t in wallet if any(n in t.replace("-", "").replace(" ", "") for n in nummern))
        st_rg = st_tk = False                                 # steht die Spieltag-Nummer in Rechnung/Ticket? (E2: Verwendungszweck)
        for b in best.values():
            if b["rechnung"] and _RE_SPIELTAG.search(_pdf(b["rechnung"][1])):
                st_rg = True
            if any(_RE_SPIELTAG.search(_pdf(d)) for _, d in b["tickets"].values()):
                st_tk = True
        distinct = len({u for u, _ in wallet})
        kt = len(ticketnrn)
        verhaeltnis["gleich" if distinct == kt else "weniger" if distinct < kt else "mehr"] += 1
        je_mail.append({"tickets": kt, "pdfs": len(ofc.mail_pdfs(x["roh"])[1]), "links": len(alle), "wallet_links": len(wallet),
                        "wallet_verschieden": distinct, "pkpass_anhaenge": pk, "ticketnr_im_link": mit_nr_url,
                        "ticketnr_im_linktext": mit_nr_text, "rechnung": any(b["rechnung"] for b in best.values()),
                        "spieltag_in_rechnung": st_rg, "spieltag_im_ticket": st_tk})
    return {"ok": True, "tage": tage, "hsv_mails": len(mails), "mails_mit_tickets": len(je_mail),
            "tickets": sum(m["tickets"] for m in je_mail), "wallet_links": sum(m["wallet_links"] for m in je_mail),
            "pkpass_anhaenge": sum(m["pkpass_anhaenge"] for m in je_mail),
            "spieltag_in_rechnung": sum(m["spieltag_in_rechnung"] for m in je_mail),
            "spieltag_im_ticket": sum(m["spieltag_im_ticket"] for m in je_mail),
            "verhaeltnis_wallet_zu_tickets": dict(verhaeltnis), "wallet_hosts": dict(hosts.most_common(10)),
            "link_muster": dict(muster.most_common(10)), "linktexte_maskiert": dict(linktexte.most_common(10)),
            "je_mail": je_mail[:60], "adressen": adressen_abdeckung(tickets or {}, mitglieder)}


def _norm(n: str) -> str:
    return re.sub(r"\s+", " ", (n or "").strip()).casefold()


def adressen_abdeckung(tickets: dict, mitglieder: list[dict] | None) -> dict:
    """Wie viele Ticketnamen haben genau ein Mitglied mit E-Mail-Adresse? Nur Zahlen."""
    namen = {_norm(t.get("name", "")) for t in tickets.values() if (t.get("name") or "").strip()}
    if mitglieder is None:
        return {"ok": False, "namen": len(namen), "hinweis": "Mitgliederliste nicht lesbar."}
    je_name = Counter(_norm(m.get("name", "")) for m in mitglieder)
    mit_mail = {_norm(m.get("name", "")) for m in mitglieder if "@" in (m.get("email") or "")}
    eindeutig = sum(1 for n in namen if je_name[n] == 1 and n in mit_mail)
    mehrdeutig = sum(1 for n in namen if je_name[n] > 1)
    return {"ok": True, "namen": len(namen), "eindeutig_mit_mail": eindeutig, "mehrdeutig": mehrdeutig,
            "ohne_treffer": len(namen) - eindeutig - mehrdeutig - sum(1 for n in namen if je_name[n] == 1 and n not in mit_mail),
            "treffer_ohne_mail": sum(1 for n in namen if je_name[n] == 1 and n not in mit_mail),
            "mitglieder_mit_mail": sum(1 for m in mitglieder if "@" in (m.get("email") or "")), "mitglieder": len(mitglieder)}
