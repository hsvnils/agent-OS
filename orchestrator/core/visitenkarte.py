"""Visitenkarte per Telegram (KONTAKTE_ROADMAP.md, Etappe K1, CEO 2026-11-19).

Der CEO schickt LUNA ein Foto einer Visitenkarte. LUNA liest es (E1: Claude Haiku wie die Kennzahlen-Screenshots, Rueckfall
lokal `tesseract` + Regeln), gleicht mit den Stammdaten ab und zeigt eine **Vorschau**. Angelegt wird erst nach dem Knopf
des CEO: neue Firma (Typ per Knopf) + Ansprechpartner, bei bekannter Firma nur der Ansprechpartner, bei bekanntem Kontakt
nichts doppelt. Das Foto kommt in die Firmenakte (E3). Datenschutz: `docs/datenschutz-ki-nutzung.md` (Nachtrag K1).

Erkennung (E2): Wartet ein Posting auf einen Kennzahlen-Screenshot, bleibt alles wie bisher (der Bot fragt dieses Modul gar
nicht). Sonst entscheidet das Modell „visitenkarte“ oder „anderes“; Schalter `VISITENKARTE=0` schaltet den Weg ab.
"""
from __future__ import annotations

import base64
import json
import re

FELDER = ("firma", "vorname", "nachname", "rolle", "mail", "telefon", "website", "strasse", "plz", "ort")
_MAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
_TEL = re.compile(r"(?:\+|00)?\d[\d ()/.-]{6,}\d")
_WEB = re.compile(r"(?i)\b(?:https?://)?(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:de|com|net|org|eu|info|io|shop|hamburg|"
                  r"football|at|ch|nl|dk|uk|co\.uk)\b(?:/\S*)?")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic"}


def an(secrets: dict) -> bool:
    return str((secrets or {}).get("VISITENKARTE", "1")).strip().lower() not in ("0", "aus", "false", "nein", "off")


def _prompt() -> str:
    return ("Ist das Bild eine Visitenkarte (Geschaeftskarte einer Person oder Firma)? Antworte NUR mit einem JSON-Objekt. "
            'Ist es KEINE Visitenkarte: {"art": "anderes"}. Ist es eine: {"art": "visitenkarte", "firma": ..., "vorname": ..., '
            '"nachname": ..., "rolle": ..., "mail": ..., "telefon": ..., "website": ..., "strasse": ..., "plz": ..., '
            '"ort": ...} -- nur was auf der Karte steht, nichts erfinden, fehlende Schluessel weglassen; bei mehreren '
            "Telefonnummern die Mobilnummer; Rolle = Position/Titel der Person.")


def _sauber(k: str, v) -> str:
    if not isinstance(v, str):
        return ""
    v = " ".join(v.split())[:120].strip(" ,;")
    if k == "mail":
        m = _MAIL.search(v)
        return m.group(0).lower() if m else ""
    if k == "website":
        v = re.sub(r"(?i)^https?://", "", v).strip("/")
        return f"https://{v}" if v and "." in v and " " not in v else ""
    if k == "telefon":
        return v if len(re.sub(r"\D", "", v)) >= 6 else ""
    if k == "plz":
        return v if re.fullmatch(r"[A-Z]{0,2}-?\d{4,5}", v) else ""
    return v


def aus_antwort(text: str) -> dict:
    """Modell-Antwort -> {art, felder...} streng: nur bekannte Schluessel, nur Text, Mail/Website/Telefon geprueft."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        roh = json.loads(m.group(0)) if m else {}
    except ValueError:
        roh = {}
    if not isinstance(roh, dict) or roh.get("art") != "visitenkarte":
        return {"art": "anderes"}
    out = {"art": "visitenkarte"}
    for k in FELDER:
        if (w := _sauber(k, roh.get(k))):
            out[k] = w
    return out


def aus_text(text: str) -> dict:
    """Rueckfall ohne Modell (OCR-Text): Mail, Telefon, Website per Regel; Firma aus der Domain. Name bleibt offen."""
    t = text or ""
    out = {"art": "visitenkarte"}
    if (m := _MAIL.search(t)):
        out["mail"] = m.group(0).lower()
    if (m := _TEL.search(t)):
        out["telefon"] = " ".join(m.group(0).split())
    if (m := _WEB.search(re.sub(_MAIL, " ", t))):
        out["website"] = _sauber("website", m.group(0))
    dom = (out.get("mail", "").rsplit("@", 1)[-1] if "mail" in out else "") or out.get("website", "")
    dom = re.sub(r"(?i)^https?://(?:www\.)?", "", dom).split("/")[0]
    if dom and dom.split(".")[0] not in ("gmail", "googlemail", "web", "gmx", "icloud", "outlook", "hotmail", "t-online"):
        out["firma"] = dom.split(".")[0].replace("-", " ").title()
    return out if len(out) > 1 else {"art": "anderes"}


def lesen(daten: bytes, name: str, *, client=None, modell: str = "", ocr=None) -> dict:
    """Bild -> {art, felder}. Erst das Modell (OpenAI-kompatibler Client aus `claude_api.cloud_client`), bei Fehler oder
    ohne Client der lokale OCR-Rueckfall (`ocr(daten, name) -> text`)."""
    if client is not None:
        try:
            endung = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ".jpg"
            url = f"data:{MIME.get(endung, 'image/jpeg')};base64,{base64.b64encode(daten).decode()}"
            r = client.chat.completions.create(model=modell, max_tokens=600, messages=[{"role": "user", "content": [
                {"type": "text", "text": _prompt()}, {"type": "image_url", "image_url": {"url": url}}]}])
            return aus_antwort(r.choices[0].message.content or "") | {"quelle": "modell"}
        except Exception:
            pass
    if ocr is not None:
        try:
            return aus_text(ocr(daten, name)) | {"quelle": "ocr"}
        except Exception:
            pass
    return {"art": "anderes", "quelle": ""}


def ocr_lokal(daten: bytes, name: str) -> str:
    from .eingangsbelege import auslesen
    return auslesen(daten, name or "karte.jpg").get("text") or ""


def vorschlag(karte: dict, ks) -> dict:
    """Abgleich mit den Stammdaten: bekannte Firma (Mail/Domain, sonst Name) und bekannter Kontakt (gleiche Mail oder
    gleicher Vor- + Nachname an dieser Firma)."""
    from .firmenakte import firma_zu_adresse
    karte = {k: w for k in FELDER if (w := _sauber(k, karte.get(k)))}
    firmen = [ks.firma(f["nummer"]) or f for f in ks.firmen()]
    nr = ""
    if karte.get("mail"):
        nr = firma_zu_adresse(firmen, karte["mail"])
    if not nr and karte.get("website"):
        nr = firma_zu_adresse(firmen, "info@" + re.sub(r"(?i)^https?://(?:www\.)?", "", karte["website"]).split("/")[0])
    if not nr and karte.get("firma"):
        nr = ks.finde(karte["firma"])
    f = ks.firma(nr) if nr else None
    ap = ""
    if f:
        name = (karte.get("vorname", "").lower(), karte.get("nachname", "").lower())
        for a in f.get("ansprechpartner_liste") or []:
            if (karte.get("mail") and (a.get("mail") or "").lower() == karte["mail"]) or \
                    (all(name) and ((a.get("vorname") or "").lower(), (a.get("nachname") or "").lower()) == name):
                ap = a["nummer"]
                break
    return {"karte": karte, "firma": f["nummer"] if f else "",
            "firma_name": f["name"] if f else karte.get("firma", ""), "ansprechpartner": ap}


def text(v: dict) -> str:
    """Vorschau fuer Telegram."""
    k = v["karte"]
    person = " ".join(x for x in (k.get("vorname"), k.get("nachname")) if x) or "(kein Name erkannt)"
    zeilen = [f"🪪 Visitenkarte: {person}" + (f" – {k['rolle']}" if k.get("rolle") else "")]
    zeilen.append(f"🏢 {v['firma_name'] or '(keine Firma erkannt)'}" +
                  (f" – schon da ({v['firma']})" if v["firma"] else " – neu"))
    for lbl, f in (("✉️", "mail"), ("📞", "telefon"), ("🌐", "website")):
        if k.get(f):
            zeilen.append(f"{lbl} {k[f]}")
    ort = " ".join(x for x in (k.get("strasse"), k.get("plz"), k.get("ort")) if x)
    if ort:
        zeilen.append(f"📍 {ort}")
    if v["ansprechpartner"]:
        zeilen.append(f"ℹ️ Den Kontakt gibt es schon ({v['ansprechpartner']}) – es wird nichts doppelt angelegt.")
    elif v["firma"]:
        zeilen.append("Anlegen = neuer Ansprechpartner bei dieser Firma.")
    else:
        zeilen.append("Als was anlegen?")
    return "\n".join(zeilen)


def knoepfe(v: dict, schluessel: str) -> list[list[dict]]:
    if v["ansprechpartner"]:
        aktion = [{"text": "📎 Nur Foto ablegen", "callback_data": f"vkn:{schluessel}:foto"}]
    elif v["firma"]:
        aktion = [{"text": "✅ Kontakt anlegen", "callback_data": f"vkn:{schluessel}:ap"}]
    else:
        aktion = [{"text": "✅ Kunde", "callback_data": f"vkn:{schluessel}:kunde"},
                  {"text": "✅ Lieferant", "callback_data": f"vkn:{schluessel}:lieferant"},
                  {"text": "✅ Partner", "callback_data": f"vkn:{schluessel}:partner"}]
    return [aktion, [{"text": "❌ Verwerfen", "callback_data": f"vkn:{schluessel}:nein"}]]


def anlegen(v: dict, wahl: str, ks, akte, bild: bytes, bildname: str, *, von: str = "Telegram:CEO") -> dict:
    """Nach dem Knopf: Firma (falls neu, Typ = Wahl) + Ansprechpartner (falls neu) + Foto in die Akte.
    -> {firma, name, ansprechpartner, neu_firma, neu_ap}."""
    from .kunden import DubletteFehler
    k = v["karte"]
    nr, neu_firma, neu_ap = v["firma"], False, False
    if not nr:
        if wahl not in ("kunde", "lieferant", "partner"):
            raise ValueError("Bitte Kunde, Lieferant oder Partner waehlen.")
        if not (v.get("firma_name") or "").strip():
            raise ValueError("Keine Firma auf der Karte erkannt -- bitte in LUNA-OS anlegen.")
        daten = {"name": v["firma_name"], "typ": wahl} | {f: k[f] for f in ("website", "strasse", "plz", "ort") if k.get(f)}
        try:
            nr = ks.firma_anlegen(daten, von=von)["nummer"]
            neu_firma = True
        except DubletteFehler as exc:
            nr = exc.nummern[0] if getattr(exc, "nummern", None) else ""
            if not nr:
                raise
    ap = v["ansprechpartner"]
    if not ap and (k.get("vorname") or k.get("nachname")) and wahl != "foto":
        ap = ks.ansprechpartner_anlegen(nr, {f: k[f] for f in ("vorname", "nachname", "rolle", "mail", "telefon")
                                             if k.get(f)}, von=von)["nummer"]
        neu_ap = True
    person = " ".join(x for x in (k.get("vorname"), k.get("nachname")) if x) or "Kontakt"
    if bild:
        akte.hochladen(nr, bild, bildname or "visitenkarte.jpg", titel=f"Visitenkarte {person}", art="sonstiges", von=von)
    return {"firma": nr, "name": (ks.firma(nr) or {}).get("name", nr), "ansprechpartner": ap, "neu_firma": neu_firma,
            "neu_ap": neu_ap}
