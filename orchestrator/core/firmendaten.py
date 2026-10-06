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
import ipaddress
import re
import socket
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
    m = re.search(r"(?is)(?:USt[.-]?\s?Id(?:ent)?(?:\.?-?Nr\.?)?|Umsatzsteuer-?Identifikations-?nummer|Umsatzsteuer-?ID|VAT\s?(?:ID|No\.?|number))"
                  r".{0,80}?\b(DE\s?(?:\d\s?){9}|(?:AT|BE|DK|ES|FI|FR|IE|IT|LU|NL|PL|SE)\s?[0-9A-Z](?:\s?[0-9A-Z]){7,11})\b",
                  text or "")
    if m:
        out["ustid"] = re.sub(r"\s+", "", m.group(1))
    m = re.search(r"(?i)\b(HR[AB])\s?(\d{2,7}\s?[A-Z]{0,2})\b", text or "")
    if m:
        kein_ort = {"Vorstand", "Aufsichtsrat", "Sitz", "Registergericht", "Handelsregister", "Geschäftsführer", "Geschaeftsfuehrer",
                    "Registernummer", "Vertreten", "Komplementärin", "Inhaber"}
        gericht = next((g for g in re.finditer(r"Amtsgericht(?:es|s)?[:\s]+(?:in\s)?([A-ZÄÖÜ][\wäöüß\-]+(?:\s(?:am|an der|im)\s[\wäöüß\-]+)?)",
                                               text or "") if g.group(1) not in kein_ort), None) \
            or next((g for g in re.finditer(r"(?:Registergericht|\bAG)[:\s]+([A-ZÄÖÜ][\wäöüß\-]+)", text or "")
                     if g.group(1) not in kein_ort), None)
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


class NichtOeffentlich(ValueError):
    """Ziel ist keine oeffentliche Web-Adresse (z. B. NAS, Fritz!Box, localhost) -- wird nie abgerufen."""


def oeffentlich(url: str, *, aufloesen=socket.getaddrinfo) -> str:
    """IMPRESSUM_SUCHE I1: nur http(s) zu oeffentlichen Adressen. Alle aufgeloesten IPs muessen global erreichbar sein
    (keine privaten, lokalen, Link-Local-, Multicast- oder reservierten Netze) -- Schutz vor Abrufen ins Heimnetz."""
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise NichtOeffentlich("Nur http- oder https-Adressen.")
    if u.username or u.password:
        raise NichtOeffentlich("Adressen mit Zugangsdaten werden nicht abgerufen.")
    if u.port not in (None, 80, 443):
        raise NichtOeffentlich("Nur die ueblichen Web-Ports.")
    try:
        ips = {a[4][0] for a in aufloesen(u.hostname, None)}
    except OSError:
        raise NichtOeffentlich("Adresse nicht gefunden.") from None
    for ip in ips:
        a = ipaddress.ip_address(ip.split("%")[0])
        if not a.is_global or a.is_multicast:
            raise NichtOeffentlich("Interne Adresse -- wird nicht abgerufen.")
    return url


class _SichereUmleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        oeffentlich(newurl)                                   # auch Umleitungen ins Heimnetz blockieren
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _abruf(url: str) -> str:
    oeffentlich(url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LUNA Stammdaten-Recherche)",
                                               "Accept": "text/html"})
    with urllib.request.build_opener(_SichereUmleitung()).open(req, timeout=10) as r:
        if "html" not in (r.headers.get("Content-Type") or "text/html"):
            return ""
        return r.read(MAX_BYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")


_RECHTSFORM = re.compile(r"(?i)\b(GmbH\s*&\s*Co\.?\s*KG|GmbH|gGmbH|mbH|UG\s*\(haftungsbeschr(?:ä|ae)nkt\)|UG|AG|KGaA|KG|OHG|"
                         r"e\.\s?K\.|eK|GbR|PartG(?:\s?mbB)?|e\.\s?V\.|SE|Ltd\.?|Limited|S\.à\s?r\.l\.|B\.V\.|Inc\.?)\s*$")
_KEIN_NAME = re.compile(r"(?i)^(vertreten|vertretungsberechtigt|gesch(ä|ae)ftsf(ü|ue)hr|inhaber|registergericht|amtsgericht|"
                        r"sitz|handelsregister|ust|umsatzsteuer|verantwortlich|angaben|impressum|kontakt|tel|e-?mail|copyright|©)")


def name_lesen(text: str) -> str:
    """Firmenname = erste Zeile mit Rechtsform (z. B. „Kiez Alm Gastro GmbH“), nicht „Geschaeftsfuehrer …“ o. Ae."""
    for z in (text or "").splitlines()[:400]:
        z = re.sub(r"\s+", " ", z).strip(" ,;:|")
        if 3 <= len(z) <= 90 and _RECHTSFORM.search(z) and not _KEIN_NAME.match(z) and "@" not in z and "http" not in z.lower():
            return z
    return ""


def _impressum_kandidaten(url: str, abruf) -> list[str]:
    """Eingegebene Seite zuerst (oft schon das Impressum), dann die ueblichen Pfade und Impressums-Links der Startseite."""
    seite = _basis(url)
    out = [url if "://" in url else "https://" + url]
    out += [seite + p for p in ("/impressum", "/imprint", "/legal-notice")]
    try:
        start = abruf(seite)
        for link in re.findall(r'href="([^"#]*(?:impressum|imprint|legal-notice)[^"#]*)"', start or "", flags=re.I)[:3]:
            ziel = urllib.parse.urljoin(seite + "/", link)
            if urllib.parse.urlparse(ziel).netloc == urllib.parse.urlparse(seite).netloc:
                out.append(ziel)
    except Exception:
        pass
    return list(dict.fromkeys(out))


def aus_impressum(url: str, *, abruf=None) -> dict:
    """IMPRESSUM_SUCHE I1: Kundendaten aus dem Impressum einer eingegebenen Website -- nur Vorschlaege, nichts gespeichert.
    -> {vorschlaege: {feld: wert}, quelle}. Regelbasiert (kein LLM)."""
    abruf = abruf or _abruf
    url = (url or "").strip()
    if not url:
        raise ValueError("Bitte die Website oder den Link zum Impressum eingeben.")
    if "://" not in url:
        url = "https://" + url
    oeffentlich(url) if abruf is _abruf else None              # Fehlermeldung frueh und verstaendlich
    for kandidat in _impressum_kandidaten(url, abruf):
        try:
            text = _text(abruf(kandidat))
        except NichtOeffentlich:
            raise
        except Exception:
            continue
        if not re.search(r"(?i)impressum|imprint|angaben gem|legal notice|§\s?5", text):
            continue
        gefunden = impressum_lesen(text)
        name = name_lesen(text)
        if name:
            gefunden["name"] = name
        if gefunden:
            return {"vorschlaege": gefunden | {"website": _basis(url)}, "quelle": kandidat}
    return {"vorschlaege": {}, "quelle": "", "hinweis": "Kein Impressum mit Angaben gefunden -- bitte den direkten Link zum Impressum eintragen."}


def _basis(url: str) -> str:
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    return f"{u.scheme or 'https'}://{u.netloc}" if u.netloc else ""


def _namenswoerter(name: str) -> list[str]:
    return [w for w in re.findall(r"[a-zäöüß0-9]{4,}", (name or "").lower())
            if w not in ("gmbh", "mbh", "gastro", "group", "international", "limited", "deutschland", "germany", "payments",
                         "distribution", "platforms", "ireland", "fernsehen", "trading", "photo", "video")]


def _klar(s: str) -> str:
    return s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def _passt(name: str, url: str, titel: str = "") -> bool:
    """Treffer gehoert zur Firma, wenn ein kennzeichnendes Namenswort in der **Domain** steht (nicht nur im Titel --
    sonst landen Verbraucherportale wie kuendigung.org oder datenanfragen.de als „Firmen-Website“ im Vorschlag)."""
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host or any(p in host for p in PORTALE):
        return False
    return any(w in host or _klar(w) in host for w in _namenswoerter(name))


def _impressum_der_firma(name: str, text: str) -> bool:
    """Das Impressum muss die Firma selbst nennen (kennzeichnendes Namenswort), sonst ist es eine fremde Seite."""
    t = (text or "").lower()
    woerter = _namenswoerter(name) or [w for w in re.findall(r"[a-zäöüß0-9]{3,}", (name or "").lower())]
    return any(w in t or _klar(w) in _klar(t) for w in woerter)


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
                if not _impressum_der_firma(f["name"], text):              # fremdes Impressum (z. B. Portal)
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
