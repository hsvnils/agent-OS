"""Mehrere Empfaenger beim Versand (EMPFAENGER_MEHRERE M1/M2, CEO 2026-10-13): An, CC und BCC.

Die Versanddialoge schicken `an`, `cc`, `bcc` (je Text mit Komma/Semikolon/Zeilen oder Liste). Fuer Kette und Verlauf
wird daraus **ein** Anzeigetext gebaut („a@x.de, b@y.de · CC: c@z.de · BCC: d@w.de“) -- die Belege speichern weiter
nur `an` als Text, und der Versandweg zerlegt ihn wieder (`zerlegen`). So bleiben alle bisherigen Ablaeufe unveraendert.
"""
from __future__ import annotations

import re

MAX = 10
_MAIL = re.compile(r"^[^@\s,;<>()\"']+@[^@\s,;<>()\"']+\.[A-Za-z]{2,}$")
_TEIL = re.compile(r"\s*·\s*(CC|BCC):\s*", re.I)


def _liste(wert) -> list[str]:
    if isinstance(wert, (list, tuple)):
        teile = [str(x) for x in wert]
    else:
        teile = re.split(r"[,;\n]+", str(wert or ""))
    out = []
    for t in teile:
        m = re.search(r"<([^<>]+@[^<>]+)>", t)                 # „Name <a@b.de>“ -> a@b.de
        t = (m.group(1) if m else t).strip().strip("<>").strip()
        if t:
            out.append(t)
    return out


def pruefen(an, cc=None, bcc=None) -> dict:
    """-> {an: [...], cc: [...], bcc: [...]} -- jede Adresse geprueft, Doppelte entfernt (An vor CC vor BCC), hoechstens
    `MAX` insgesamt, mindestens ein An. Fehler nennen die falsche Adresse."""
    gesehen: set[str] = set()
    out: dict[str, list[str]] = {"an": [], "cc": [], "bcc": []}
    for feld, wert in (("an", an), ("cc", cc), ("bcc", bcc)):
        for a in _liste(wert):
            if not _MAIL.match(a):
                raise ValueError(f"Mailadresse ungueltig: „{a}“.")
            if a.lower() in gesehen:
                continue
            gesehen.add(a.lower())
            out[feld].append(a)
    if not out["an"]:
        raise ValueError("Bitte mindestens eine Empfaenger-Adresse (An) angeben.")
    if len(gesehen) > MAX:
        raise ValueError(f"Hoechstens {MAX} Empfaenger insgesamt (An, CC und BCC).")
    return out


def anzeige(e: dict) -> str:
    """Anzeigetext fuer Kette/Verlauf und zugleich Transportformat bis zum Versandweg."""
    t = ", ".join(e["an"])
    if e.get("cc"):
        t += " · CC: " + ", ".join(e["cc"])
    if e.get("bcc"):
        t += " · BCC: " + ", ".join(e["bcc"])
    return t


def zerlegen(text: str) -> dict:
    """Umkehrung von `anzeige` (auch fuer alte Einzel-Adressen) -> geprueftes {an, cc, bcc}."""
    teile = _TEIL.split(str(text or ""))
    werte = {"an": teile[0], "cc": "", "bcc": ""}
    for art, wert in zip(teile[1::2], teile[2::2]):
        werte[art.lower()] = (werte[art.lower()] + "," if werte[art.lower()] else "") + wert
    return pruefen(werte["an"], werte["cc"], werte["bcc"])


def aus_body(body: dict) -> str:
    """Dialog-Werte (`an`, `cc`, `bcc`) -> Anzeigetext; wirft ValueError mit der falschen Adresse."""
    b = body or {}
    if not (b.get("cc") or b.get("bcc")) and _TEIL.search(str(b.get("an") or "")):
        return anzeige(zerlegen(b.get("an")))                     # schon zusammengesetzt (z. B. erneut senden)
    return anzeige(pruefen(b.get("an"), b.get("cc"), b.get("bcc")))


def erste(text: str) -> str:
    """Erste An-Adresse (z. B. fuer Dubletten-Pruefung oder neuen Ansprechpartner)."""
    try:
        return zerlegen(text)["an"][0]
    except ValueError:
        return str(text or "").strip()


def vorschlaege(kunden, firma: str) -> list[dict]:
    """Alle Mailadressen einer Firma zum Anhaken: aktive Ansprechpartner mit Mail, dann die Rechnungs-Mail."""
    f = kunden.firma(firma) if (kunden and firma) else None
    if not f:
        return []
    out, gesehen = [], set()
    for ap in f.get("ansprechpartner_liste") or []:
        m = str(ap.get("mail") or "").strip()
        if ap.get("aktiv", True) and m and m.lower() not in gesehen:
            gesehen.add(m.lower())
            out.append({"mail": m, "name": " ".join(x for x in (ap.get("vorname"), ap.get("nachname")) if x),
                        "rolle": ap.get("rolle") or "Ansprechpartner"})
    rm = str(f.get("rechnungsmail") or "").strip()
    if rm and rm.lower() not in gesehen:
        out.append({"mail": rm, "name": "", "rolle": "Rechnungs-Mail"})
    return out


def kopf(text: str) -> tuple[str, str, list[str], list[str]]:
    """Fuer den Versandweg: (To, Cc, Bcc-Liste, alle Empfaenger). Eine einzelne alte Adresse bleibt unveraendert."""
    t = str(text or "").strip()
    if not re.search(r"[,;]|·\s*(CC|BCC):", t, re.I):
        return t, "", [], [t]
    e = zerlegen(t)
    return ", ".join(e["an"]), ", ".join(e["cc"]), list(e["bcc"]), e["an"] + e["cc"] + e["bcc"]
