"""KONTAKTE K4: freie Mail aus LUNA-OS an einen Ansprechpartner (bzw. an die Firma), Absender luna@hanserautisch.de.

- **CEO-Tor Oeffentlichkeit:** gesendet wird nur mit `bestaetigt=True` (Klick „Jetzt senden“ im Dialog). LUNA formuliert
  auf Wunsch einen Entwurf (`entwurf`), sendet aber nie selbst.
- **Absender:** vorerst nur `luna` (All-Inkl); `nils` ist bis K5 gesperrt (eigener Zugang mit CISO-Freigabe).
- **Nach dem Versand:** Kopie (.eml + PDF-Ansicht) in die Firmenakte -- mit Ansprechpartner --, und das Ereignis
  `kontakt_mail_gesendet` (K3), damit der 15-min-Poll die Antwort ueber die Kennung zuordnet.
- **Anhaenge:** nur Dokumente aus der Akte derselben Firma (erste Datei = PDF-Ansicht bzw. Upload), zusammen hoechstens
  `MAX_ANHANG` Bytes.
- **Datenschutz Entwurf:** an das Modell gehen nur die Stichworte des CEO -- keine Namen, Adressen oder Firmendaten;
  Anrede und Signatur setzt LUNA lokal davor bzw. dahinter.
"""
from __future__ import annotations

import os
from pathlib import Path

ABSENDER = {"luna": "luna@hanserautisch.de", "nils": "nils@hanserautisch.de"}
GESPERRT = {"nils": "Absender nils@ wird erst mit Etappe K5 freigeschaltet (eigener Zugang, CISO-Freigabe)."}
MAX_ANHANG = 15 * 1024 * 1024
_MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".eml": "message/rfc822", ".txt": "text/plain"}


def aktiv() -> bool:
    """Schalter `KONTAKT_MAIL=0` blendet den Knopf aus und sperrt den Versand (Rueckweg K4)."""
    return os.environ.get("KONTAKT_MAIL", "1").strip().lower() not in ("0", "false", "no", "off")


def _ap(kunden, firma: str, ap_nr: str) -> tuple[dict, dict | None]:
    f = kunden.firma(firma)
    if not f:
        raise KeyError(firma)
    ap_nr = str(ap_nr or "").strip().upper()
    ap = None
    if ap_nr:
        ap = next((a for a in f.get("ansprechpartner_liste") or [] if a["nummer"] == ap_nr), None)
        if not ap:
            raise ValueError(f"Ansprechpartner {ap_nr} gehoert nicht zu {f['nummer']}.")
    return f, ap


def vorschlag(kunden, firma: str, ap_nr: str = "", *, signatur: str = "") -> dict:
    """Vorbelegung des Dialogs: Empfaenger = Mail des Ansprechpartners (sonst Rechnungsmail), Text = Anrede + Signatur."""
    from .textbausteine import anrede_werte
    f, ap = _ap(kunden, firma, ap_nr)
    an = (ap or {}).get("mail") or ("" if ap else f.get("rechnungsmail") or "")
    gruss = (signatur or "").strip() or "Viele Grüße"
    return {"firma": {k: f.get(k) for k in ("nummer", "name", "typ")},
            "ansprechpartner": {k: ap.get(k, "") for k in ("nummer", "vorname", "nachname", "mail", "rolle")} if ap else None,
            "an": an, "anrede": anrede_werte(ap)["anrede"], "text": f"{anrede_werte(ap)['anrede']}\n\n\n\n{gruss}",
            "gruss": gruss}


def _anhaenge(akte, firma: str, ids: list) -> list[tuple[str, bytes, str]]:
    out, summe = [], 0
    for did in ids or []:
        d = akte.dokument(str(did))
        if not d or d.get("firma") != firma or not d.get("dateien"):
            raise ValueError(f"Anhang {did} liegt nicht in der Akte dieser Firma.")
        datei = d["dateien"][0]
        daten = (akte.bh.dir / datei["pfad"]).read_bytes()
        summe += len(daten)
        if summe > MAX_ANHANG:
            raise ValueError("Anhaenge zusammen groesser als 15 MB.")
        name = datei.get("name") or Path(datei["pfad"]).name
        out.append((name, daten, _MIME.get(Path(name).suffix.lower(), "application/octet-stream")))
    return out


def senden(bh, kunden, versand, daten: dict, *, absender_name: str, eigene: list[str], von: str = "") -> dict:
    """Senden nach CEO-Klick. Reihenfolge: pruefen -> senden -> Akte -> Ereignis (Antwort-Erkennung K3)."""
    from .empfaenger import aus_body
    from .firmenakte import Firmenakte
    from .mail_antworten import kontakt_mail_vermerken
    d = daten or {}
    if not aktiv():
        raise ValueError("Mail an Ansprechpartner ist ausgeschaltet (KONTAKT_MAIL=0).")
    if d.get("bestaetigt") is not True:
        raise ValueError("Senden braucht die ausdrueckliche Bestaetigung.")
    absender = str(d.get("absender") or "luna").strip().lower()
    if absender in GESPERRT:
        raise ValueError(GESPERRT[absender])
    if absender not in ABSENDER:
        raise ValueError("Unbekannter Absender.")
    if getattr(versand, "kanal", "") != "allinkl":
        raise ValueError("Mails an Ansprechpartner gehen nur ueber luna@ (All-Inkl) -- Kundenversand steht auf einem anderen Weg.")
    f, ap = _ap(kunden, str(d.get("firma") or ""), str(d.get("ansprechpartner") or ""))
    betreff, text = str(d.get("betreff") or "").strip(), str(d.get("text") or "").strip()
    if not str(d.get("an") or "").strip() or not betreff or not text:
        raise ValueError("Empfaenger (gueltige Mailadresse), Betreff und Text sind Pflicht.")
    an = aus_body(d)
    akte = Firmenakte(bh, kunden)
    anhaenge = _anhaenge(akte, f["nummer"], d.get("anhaenge") or [])
    s = versand.mail_senden(an, betreff[:200], text, bestaetigt=True, anhaenge=anhaenge, absender_name=absender_name)
    if not s.get("ok"):
        raise ValueError(s.get("hinweis") or "Senden fehlgeschlagen.")
    ap_nr = (ap or {}).get("nummer", "")
    akte_id = ""
    roh = versand.mail_roh(s["id"]) if s.get("id") and hasattr(versand, "mail_roh") else {}
    if roh.get("ok"):
        akte_id = akte.mail_aufnehmen(roh["roh"], s["id"], eigene=eigene, weitergeleitet=False, von=von,
                                      firma=f["nummer"], ansprechpartner=ap_nr)["id"]
    kontakt_mail_vermerken(bh, firma=f["nummer"], ansprechpartner=ap_nr, message_id=s["id"], betreff=betreff, an=an,
                           kanal=s.get("kanal", "allinkl"), akte_id=akte_id, von=von)
    return {"firma": f["nummer"], "ansprechpartner": ap_nr, "an": an, "akte_id": akte_id, "kennung": s["id"],
            "anhaenge": [a[0] for a in anhaenge], "gesendet_ordner": s.get("gesendet_ordner", "")}


def verlauf(akte, firma: str, ap_nr: str) -> list[dict]:
    """Mails/Dokumente der Akte, die an diesem Ansprechpartner haengen (gesendet + Antworten), neueste zuerst."""
    ap_nr = str(ap_nr or "").strip().upper()
    return [{k: x.get(k, "") for k in ("id", "titel", "datum", "art", "mail_von", "quelle")}
            for x in akte.akte(firma) if x.get("ansprechpartner") == ap_nr]


ENTWURF_AUFTRAG = ("Schreibe den Hauptteil einer kurzen, freundlichen geschaeftlichen E-Mail auf Deutsch (Du- oder Sie-Form "
                   "wie in den Stichworten, sonst Sie). Nur der Text zwischen Anrede und Gruss -- KEINE Anrede, KEIN Gruss, "
                   "keine Signatur, keine Platzhalter in eckigen Klammern, kein Betreff. Hoechstens 120 Woerter.\n\n"
                   "Stichworte des Absenders:\n")


def entwurf(stichworte: str, *, client, modell: str) -> str:
    """Nur die Stichworte gehen an das Modell (keine Namen/Adressen aus den Stammdaten)."""
    st = str(stichworte or "").strip()
    if not st:
        raise ValueError("Bitte zuerst ein paar Stichworte eingeben, worum es gehen soll.")
    r = client.chat.completions.create(model=modell, max_tokens=800,
                                       messages=[{"role": "user", "content": ENTWURF_AUFTRAG + st[:2000]}])
    text = (r.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("Kein Entwurf erhalten -- bitte erneut versuchen.")
    return text
