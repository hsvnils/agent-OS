"""Bestellbestaetigung -> Eigenbeleg (CEO 2026-10-06: „Ich will nicht jedes Mal die Amazon-Rechnung schicken muessen“).

Weitergeleitete Bestellbestaetigungen (z. B. Amazon) sind keine Rechnung, landen deshalb als Mail in der Firmenakte (bzw.
„keiner Firma“). Hier wird daraus ein **Vorschlag** fuer einen Eigenbeleg: Betrag („Summe 34.99€“), Datum (Original-Mail),
Haendler, Bestellnummer und Zweck (Text des CEO ueber der Weiterleitung). Gebucht wird nur per Klick; die Mail bleibt als
**Nachweis** am Eigenbeleg (`nachweis`). Bestellbestaetigungen ohne Buchung erscheinen im Handlungsbedarf, bis sie gebucht
oder als „keine Firmenausgabe“ abgehakt sind (Ereignis `bestellung_keine_ausgabe`).

Steuerlich (Hinweis, keine Beratung): Als Kleinunternehmer (§ 19 UStG) gibt es keinen Vorsteuerabzug -- fuer die EUeR genuegt
ein nachvollziehbarer Beleg mit Zahlungsnachweis; ein Eigenbeleg ersetzt die Rechnung nur, wenn keine vorliegt. Die
Steuerberatung entscheidet im Zweifel.
"""
from __future__ import annotations

import re

BESTELLUNG = re.compile(r"(?i)\bbestellt\b|bestellbest|ihre bestellung|order confirm|kaufbest|auftragsbest(?:ae|ä)tigung")
_SUMME = re.compile(r"(?i)(?:gesamtsumme|gesamtbetrag|bestellsumme|endbetrag|summe|gesamt|total)\s*(?:\(inkl\.[^)]*\))?\s*[:]?\s*"
                    r"(?:€|EUR)?\s*(\d{1,3}(?:[.\s]\d{3})*[.,]\d{2}|\d+[.,]\d{2})\s*(?:€|EUR)?")
_BESTELLNR = re.compile(r"(?i)bestell(?:nummer|nr\.?)\s*[:#]?\s*\W{0,3}([0-9A-Z][0-9A-Z\-]{5,30})")


def ist_bestellung(titel: str, von: str = "") -> bool:
    return bool(BESTELLUNG.search(f"{titel or ''} {von or ''}"))


def betrag_lesen(text: str) -> str:
    """„Summe 34.99€“ / „Gesamtsumme: 1.234,56 €“ -> „34,99“ / „1234,56“ (deutsch, fuer das Formular)."""
    m = _SUMME.search(text or "")
    if not m:
        return ""
    roh = re.sub(r"\s", "", m.group(1))
    ganz, dez = roh[:-3], roh[-2:]
    return f"{re.sub(r'[.,]', '', ganz)},{dez}"


def vorschlag(roh: bytes, kunden=None) -> dict:
    """Eigenbeleg-Vorschlag aus der (weitergeleiteten) Bestellbestaetigung."""
    import email
    from email import policy
    from .eingangsbelege import _datum_kopf, mail_text, weiterleitung, zweck_aus_mail
    text = mail_text(roh)
    orig, rest, _ = weiterleitung(roh, text)
    m = email.message_from_bytes(roh, policy=policy.default)
    datum = _datum_kopf(orig.get("datum") or "") or _datum_kopf(str(m.get("Date", "")))
    betreff = re.sub(r"(?i)^\s*(?:fwd?|wg|aw|re)\s*:\s*", "", orig.get("betreff") or str(m.get("Subject", ""))).strip()
    produkt = re.sub(r"(?i)^bestellt\s*:\s*", "", betreff).strip(" „“\"")
    von = orig.get("von") or ""
    haendler = (orig.get("von_name") or "").strip() or (von.split("@")[-1] if "@" in von else "")
    firma = ""
    if kunden is not None:
        try:
            firma = kunden.finde(haendler, absender=von)
        except Exception:
            firma = ""
    nr = _BESTELLNR.search(text)
    zweck = zweck_aus_mail(roh)
    return {"art": "ausgabe", "datum": datum, "betrag": betrag_lesen(rest) or betrag_lesen(text),
            "text": (f"Bestellung {haendler}: {produkt}" if haendler else f"Bestellung: {produkt}")[:200]
                    + (f" – {zweck}" if zweck else ""),
            "gegenpartei": haendler, "firma": firma, "referenz": f"Bestellnr. {nr.group(1)}" if nr else "", "zweck": zweck}


def _gebucht(eintraege: list[dict]) -> dict[str, str]:
    """akte_id -> Eigenbeleg-Nummer (nicht storniert)."""
    out, storno = {}, set()
    for e in eintraege:
        d = e["daten"]
        if e["typ"] == "eigenbeleg_angelegt" and (d.get("nachweis") or {}).get("akte_id"):
            out[d["nachweis"]["akte_id"]] = d["nummer"]
        elif e["typ"] == "eigenbeleg_storniert":
            storno.add(d.get("nummer"))
    return {k: v for k, v in out.items() if v not in storno}


def mails(eintraege: list[dict]) -> dict[str, dict]:
    """Alle Mails der Akte (zugeordnet, offen, „keiner Firma“), die wie eine Bestellbestaetigung aussehen."""
    from .firmenakte import _falte, ohne_firma
    docs, offen = _falte(eintraege)
    alle = {**{k: v for k, v in docs.items() if v.get("art") == "mail"}, **offen, **ohne_firma(eintraege)}
    return {k: v for k, v in alle.items() if ist_bestellung(v.get("titel", ""), v.get("mail_von", ""))}


def offene(eintraege: list[dict]) -> list[dict]:
    gebucht = _gebucht(eintraege)
    keine = {e["daten"].get("akte_id") for e in eintraege if e["typ"] == "bestellung_keine_ausgabe"}
    return sorted((m for k, m in mails(eintraege).items() if k not in gebucht and k not in keine),
                  key=lambda m: m.get("datum") or "", reverse=True)


def keine_ausgabe(bh, akte_id: str, *, von: str = "") -> dict:
    if akte_id not in mails(bh.eintraege()):
        raise KeyError(akte_id)
    bh.erfassen("bestellung_keine_ausgabe", {"akte_id": akte_id}, von=von)
    return {"akte_id": akte_id}


_FWD = re.compile(r"(?i)^(?:fwd?|wg)\s*:\s*")


def todos(eintraege: list[dict]) -> list[dict]:
    return [{"id": f"bestellung:{m['id']}", "bereich": "Belege", "icon": "🛒",
             "titel": "Bestellung als Ausgabe buchen: " + _FWD.sub("", m.get("titel", ""))[:60],
             "detail": f"{m.get('mail_von', '')} · Betrag und Zweck aus der Mail vorausgefüllt", "act": "eb-aus-mail",
             "act_id": m["id"], "faellig": "", "dringend": False, "stufe": "woche",
             "erledigen": {"pfad": f"/api/finanzen/bestellung/{m['id']}/keine-ausgabe", "label": "Keine Firmenausgabe"}}
            for m in offene(eintraege)]
