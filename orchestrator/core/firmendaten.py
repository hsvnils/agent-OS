"""Firmendaten recherchieren und auf Knopfdruck uebernehmen (KUNDEN_FINANZEN Etappe 22, CEO 2026-09-30: „Mach das“).

Fuer Kunden, Lieferanten und Partner mit Luecken in den Stammdaten sucht LUNA **oeffentliche** Pflichtangaben:
Firmen-Website (hinterlegt oder per Brave-Suche „<Name> Impressum“), dort das **Impressum** (Pflichtangaben nach § 5 DDG)
-> Strasse, PLZ, Ort, USt-ID, Handelsregister, Telefon, Rechnungs-Mail. Vorschlaege gibt es nur fuer **fehlende** Felder,
jeweils mit Quelle; **uebernommen wird nie automatisch**, nur per Klick (einzeln oder alle). Privatpersonen
(`verbraucher`) werden nie recherchiert. Regelbasiert, kein LLM: Seiteninhalte werden nur per Muster gelesen.

Ereignisse in der Hash-Kette: `firma_recherche` (Vorschlaege + Quellen), `firma_vorschlag_erledigt` (uebernommen/verworfen).
Der Bot prueft einmal pro Woche bis zu `JE_LAUF` Firmen mit Luecken (letzte Recherche aelter als `PAUSE_TAGE`).
"""
from __future__ import annotations

import html as _html
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from .buchhaltung import jetzt

FELDER = ("strasse", "plz", "ort", "ustid", "handelsregister", "telefon", "rechnungsmail", "website")
NAMEN = {"strasse": "Straße", "plz": "PLZ", "ort": "Ort", "ustid": "USt-ID", "handelsregister": "Handelsregister",
         "telefon": "Telefon", "rechnungsmail": "Rechnungs-Mail", "website": "Website"}
JE_LAUF = 8
PAUSE_TAGE = 30
MAX_BYTES = 800_000
PORTALE = ("northdata", "linkedin", "facebook", "instagram", "xing", "wikipedia", "kununu", "firmenwissen", "dnb.com",
           "handelsregister", "unternehmensregister", "creditreform", "gelbeseiten", "11880", "dasoertliche", "youtube",
           "twitter", "x.com", "tiktok", "trustpilot", "google.", "bing.", "yelp", "amazon.", "ebay.")
_RECHNUNGS_MAIL = re.compile(r"(?i)^(rechnung|rechnungen|invoice|invoices|billing|buchhaltung|accounting|finance|finanz)")
_STRASSE = re.compile(r"(?i)^[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß.\-' ]{2,50}?\s\d{1,4}\s?[a-zA-Z]?(?:\s?[-/]\s?(?:\d{1,4}[a-zA-Z]?|[a-zA-Z]))?$")
_PLZ_ORT = re.compile(r"^(?:D-)?(\d{5})\s+([A-ZÄÖÜ][\wÄÖÜäöüß .\-/()]{1,40})$")


def luecken(f: dict) -> list[str]:
    return [k for k in FELDER if not str(f.get(k) or "").strip()]


def _text(roh: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", roh or "")
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|address|section|span)>", "\n", t)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t))
    return "\n".join(z for z in (re.sub(r"[ \t\xa0]+", " ", z).strip() for z in t.splitlines()) if z)


def impressum_lesen(text: str) -> dict:
    """Pflichtangaben aus Impressums-Text (bereits ohne HTML) per Muster lesen -> {feld: wert}."""
    out: dict = {}
    zeilen = [z.strip(" ,;") for z in (text or "").splitlines() if z.strip()]
    for i, z in enumerate(zeilen):                               # „Musterweg 1“ + „20095 Hamburg“ (auch in einer Zeile)
        teile = [x.strip() for x in re.split(r",\s*|\s[|·•]\s", z)]
        for j, t in enumerate(teile):
            m = _PLZ_ORT.match(t)
            if not m:
                continue
            davor = [teile[j - 1]] if j else [zeilen[k] for k in (i - 1, i - 2) if k >= 0]   # auch „Aufgang D“ dazwischen
            strasse = next((s for s in davor if _STRASSE.match(s or "")), "")
            if strasse:
                out |= {"strasse": strasse, "plz": m.group(1), "ort": m.group(2).strip()}
                break
        if "plz" in out:
            break
    m = re.search(r"(?is)(?:USt[.-]?\s?Id(?:ent)?(?:\.?-?Nr\.?)?|Umsatzsteuer-?Identifikations-?nummer|VAT\s?(?:ID|No\.?|number))"
                  r".{0,80}?\b(DE\s?(?:\d\s?){9}|(?:AT|BE|DK|ES|FI|FR|IE|IT|LU|NL|PL|SE)\s?[0-9A-Z](?:\s?[0-9A-Z]){7,11})\b",
                  text or "")
    if m:
        out["ustid"] = re.sub(r"\s+", "", m.group(1))
    m = re.search(r"(?i)\b(HR[AB])\s?(\d{2,7}\s?[A-Z]{0,2})\b", text or "")
    if m:
        gericht = (re.search(r"Amtsgericht[:\s]+([A-ZÄÖÜ][\wäöüß\-]+(?:\s(?:am|an der|im)\s[\wäöüß\-]+)?)", text or "")
                   or re.search(r"(?:Registergericht|AG)[:\s]+([A-ZÄÖÜ][\wäöüß\-]+)", text or ""))
        out["handelsregister"] = " ".join(x for x in ((f"Amtsgericht {gericht.group(1)}" if gericht else ""),
                                                       f"{m.group(1).upper()} {m.group(2).strip()}") if x)
    m = re.search(r"(?i)(?:Tel(?:efon)?\.?|Phone|Fon)\s*[:.]?\s*(\+?\d[\d\s/()\-]{6,20}\d)", text or "")
    if m:
        out["telefon"] = re.sub(r"\s+", " ", m.group(1)).strip()
    mails = re.findall(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", (text or "").replace("[at]", "@").replace("(at)", "@"))
    rm = next((x for x in mails if _RECHNUNGS_MAIL.match(x)), "")
    if rm:
        out["rechnungsmail"] = rm.lower()
    return out


def _abruf(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LUNA Stammdaten-Recherche)",
                                               "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=10) as r:
        if "html" not in (r.headers.get("Content-Type") or "text/html"):
            return ""
        return r.read(MAX_BYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")


def _basis(url: str) -> str:
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    return f"{u.scheme or 'https'}://{u.netloc}" if u.netloc else ""


def _passt(name: str, url: str, titel: str = "") -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host or any(p in host for p in PORTALE):
        return False
    woerter = [w for w in re.findall(r"[a-zäöüß0-9]{4,}", name.lower())
               if w not in ("gmbh", "mbh", "gastro", "group", "international", "limited", "deutschland", "germany")]
    klar = lambda s: s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")  # noqa: E731
    return any(w in host or klar(w) in host or w in titel.lower() for w in woerter)


class FirmenRecherche:
    def __init__(self, kunden, *, suche=None, abruf=None):
        """`suche(query) -> [(titel, url)]` (Brave), `abruf(url) -> html` -- beide austauschbar (Tests ohne Netz)."""
        self.kunden, self.suche, self.abruf = kunden, suche, abruf or _abruf

    def _website(self, f: dict) -> str:
        if f.get("website"):
            return _basis(f["website"])
        if self.suche is None:
            return ""
        for titel, url in self.suche(f"{f['name']} Impressum") or []:
            if _passt(f["name"], url, titel):
                return _basis(url)
        return ""

    def _kandidaten(self, seite: str):
        """Uebliche Impressums-Pfade, danach der Impressums-Link der Startseite (z. B. /de-de/g-about/impressum)."""
        yield from (seite + p for p in ("/impressum", "/imprint", "/legal-notice"))
        try:
            start = self.abruf(seite)
        except Exception:
            return
        links = re.findall(r'href="([^"#]*(?:impressum|imprint|legal-notice)[^"#]*)"', start or "", flags=re.I)
        for link in sorted(dict.fromkeys(links), key=lambda l: "impressum" not in l.lower())[:3]:
            ziel = urllib.parse.urljoin(seite + "/", link)
            if urllib.parse.urlparse(ziel).netloc == urllib.parse.urlparse(seite).netloc:   # nur dieselbe Website
                yield ziel
        yield seite

    def recherchieren(self, nummer: str, *, von: str = "LUNA") -> dict:
        f = self.kunden.firma(nummer)
        if not f:
            raise KeyError(nummer)
        if f.get("verbraucher"):
            raise ValueError("Privatpersonen werden nicht recherchiert.")
        offen = luecken(f)
        if not offen:
            return {"nummer": f["nummer"], "vorschlaege": {}, "hinweis": "Keine Luecken."}
        seite = self._website(f)
        vorschlaege, quelle = {}, ""
        if seite:
            for url in self._kandidaten(seite):
                try:
                    text = _text(self.abruf(url))
                except Exception:
                    continue
                if not re.search(r"(?i)impressum|imprint|angaben gem|legal notice|§\s?5", text):
                    continue
                gefunden = impressum_lesen(text)
                if gefunden:
                    vorschlaege, quelle = gefunden, url
                    break
            if "website" in offen:
                vorschlaege["website"] = seite
                quelle = quelle or seite
        vorschlaege = {k: v for k, v in vorschlaege.items() if k in offen and v}
        self.kunden.bh.erfassen("firma_recherche", {"nummer": f["nummer"], "vorschlaege": vorschlaege, "quelle": quelle,
                                                    "gesucht": offen}, von=von)
        return {"nummer": f["nummer"], "vorschlaege": vorschlaege, "quelle": quelle,
                "hinweis": "" if vorschlaege else "Nichts Passendes gefunden."}


def offene_vorschlaege(eintraege: list[dict]) -> dict[str, dict]:
    """-> {nummer: {vorschlaege: {feld: wert}, quelle, ts}} -- letzte Recherche je Firma ohne Erledigt-Vermerk je Feld."""
    out: dict[str, dict] = {}
    for e in eintraege:
        d = e["daten"]
        if e["typ"] == "firma_recherche":
            out[d["nummer"]] = {"vorschlaege": dict(d.get("vorschlaege") or {}), "quelle": d.get("quelle", ""), "ts": e["ts"]}
        elif e["typ"] == "firma_vorschlag_erledigt" and d.get("nummer") in out:
            for k in d.get("felder") or []:
                out[d["nummer"]]["vorschlaege"].pop(k, None)
    return out


def uebernehmen(kunden, nummer: str, felder: list[str] | None, *, verwerfen: bool = False, von: str = "") -> dict:
    """Vorschlaege (alle oder `felder`) in die Stammdaten uebernehmen bzw. verwerfen -- nur, was noch leer ist."""
    nummer = (nummer or "").strip().upper()
    v = offene_vorschlaege(kunden.bh.eintraege()).get(nummer)
    if not v or not v["vorschlaege"]:
        raise ValueError("Keine offenen Vorschlaege.")
    felder = [k for k in (felder or list(v["vorschlaege"])) if k in v["vorschlaege"]]
    if not felder:
        raise ValueError("Diese Vorschlaege gibt es nicht (mehr).")
    f = kunden.firma(nummer) or {}
    neu = {k: v["vorschlaege"][k] for k in felder if not str(f.get(k) or "").strip()}
    if neu and not verwerfen:
        kunden.firma_aendern(nummer, neu, von=von)
    kunden.bh.erfassen("firma_vorschlag_erledigt", {"nummer": nummer, "felder": felder,
                                                    "wie": "verworfen" if verwerfen else "uebernommen"}, von=von)
    return {"nummer": nummer, "uebernommen": {} if verwerfen else neu, "felder": felder}


def wochenlauf(kunden, recherche: FirmenRecherche, *, heute: datetime | None = None, je_lauf: int = JE_LAUF) -> list[str]:
    """Bis zu `je_lauf` Firmen mit Luecken recherchieren, die zuletzt vor mehr als PAUSE_TAGE geprueft wurden."""
    heute = heute or jetzt()
    zuletzt = {e["daten"]["nummer"]: e["ts"] for e in kunden.bh.eintraege() if e["typ"] == "firma_recherche"}
    grenze = (heute - timedelta(days=PAUSE_TAGE)).isoformat()
    kandidaten = [f for f in kunden.firmen() if f.get("aktiv", True) and not f.get("verbraucher") and luecken(f)
                  and str(zuletzt.get(f["nummer"], "")) < grenze and f["nummer"] != kunden_eigene(kunden)]
    erledigt = []
    for f in kandidaten[:je_lauf]:
        try:
            if recherche.recherchieren(f["nummer"], von="LUNA-Firmendaten")["vorschlaege"]:
                erledigt.append(f["nummer"])
        except (KeyError, ValueError):
            continue
    return erledigt


def kunden_eigene(kunden) -> str:
    """Eigene Firma (Krueger Onlinehandel) nie recherchieren -- Nummer ueber den Namen."""
    return next((f["nummer"] for f in kunden.firmen() if "krüger onlinehandel" in f["name"].lower()
                 or "kruger onlinehandel" in f["name"].lower()), "")
