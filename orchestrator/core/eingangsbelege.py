"""Eingangsrechnungen und Belege (KUNDEN_FINANZEN_ROADMAP.md, Etappe 6) -- hochladen/weiterleiten -> digitalisieren ->
ablegen -> verarbeiten (Vorschlag) -> CEO bestaetigt (bucht).

Grundsaetze:
- **Original zuerst, unveraenderlich:** jede Datei wird beim Eingang mit interner Belegnummer `ER-JJJJ-NNNN` als Beleg
  (8 Jahre) archiviert -- in EINEM Schritt mit dem Eintrag (`Buchhaltung.festschreiben`). Doppelte Dateien (gleiche
  Pruefsumme) werden erkannt, nie doppelt abgelegt. Loeschen gibt es nicht; Fehlupload -> „verworfen" (Datei bleibt).
- **Auslesen lokal:** E-Rechnung (XRechnung UBL/CII, ZUGFeRD/Factur-X-XML im PDF) exakt per XML; PDF-Text per `pypdf`;
  Fotos/Scans per OCR (`tesseract`, `pdftoppm` im NAS-Image). Daraus ein **Sofort-Vorschlag nach Regeln**; das lokale
  Backoffice-Modell (MACO470) liefert spaeter einen genaueren Vorschlag nach. Keine Cloud.
- **Vorschlag ist kein Buchungssatz:** Werte (Lieferant, Rechnungsnummer, Datum, Betrag, Kategorie) bestaetigt der CEO
  mit „Buchen"; Korrekturen sind neue Eintraege (Verlauf). Kleinunternehmer: Brutto = Aufwand (kein Vorsteuerabzug).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .beleg_pdf import cent, eur
from .buchhaltung import Buchhaltung, jetzt

MAX_BYTES = 15 * 1024 * 1024
ENDUNGEN = {".pdf": "application/pdf", ".xml": "application/xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".heic": "image/heic", ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff"}

# EUeR-orientierte Kategorien (Zuordnung zu den ELSTER-Zeilen folgt in Etappe 7/9)
KATEGORIEN = {
    "wareneinkauf": ("Wareneinkauf / Material", ("ware", "material", "einkauf", "druck", "merch", "textil", "shirt")),
    "fremdleistungen": ("Fremdleistungen (Freelancer, Subunternehmer)", ("freelancer", "honorar", "dienstleistung", "schnitt", "fotograf", "videoproduktion")),
    "software": ("Software, Abos, Hosting", ("software", "abo", "subscription", "lizenz", "hosting", "cloud", "adobe", "canva", "google", "apple", "microsoft", "openai", "anthropic", "domain")),
    "werbung": ("Werbung / Marketing", ("werbung", "anzeige", "ads", "marketing", "kampagne", "promotion", "sponsor")),
    "telekommunikation": ("Telefon / Internet", ("telefon", "mobilfunk", "internet", "telekom", "vodafone", "o2", "1&1")),
    "buero": ("Arbeitsmittel & Zubehör (Kabel, Speicherkarten, Büro, Versand, Requisiten)",
              ("büro", "buero", "papier", "porto", "briefmarke", "paketmarke", "deutsche post", "kabel", "adapter",
               "speicherkarte", "sd-karte", "versandbeutel", "versandtasche", "panzerglas", "schutzfolie")),
    "reise": ("Reisekosten", ("bahn", "db fernverkehr", "hotel", "flug", "übernachtung", "ticket", "reise")),
    "fahrzeug": ("Fahrzeugkosten", ("tank", "kraftstoff", "benzin", "diesel", "parken", "werkstatt", "kfz")),
    "bewirtung": ("Bewirtung (70 % absetzbar)", ("restaurant", "bewirtung", "gastronomie", "café", "cafe")),
    "fortbildung": ("Fortbildung / Fachliteratur", ("seminar", "kurs", "fortbildung", "buch", "schulung", "konferenz")),
    "gwg": ("Technik & Equipment bis 800 € (Kamera, Licht, Ton, Streaming – GWG)",
            ("kamera", "mikrofon", "objektiv", "stativ", "monitor", "tastatur", "cage", "gimbal", "akku", "smallrig", "rode",
             "sony alpha", "key light", "stream deck", "elgato", "capture", "streambox", "headset", "softbox", "ringlicht")),
    "anlage": ("Technik & Geräte über 800 € (Abschreibung)", ("laptop", "macbook", "computer", "pc ", "iphone", "server", "nas")),
    "gebuehren": ("Gebühren, Beiträge, Versicherungen", ("gebühr", "gebuehr", "beitrag", "versicherung", "ihk", "kontoführung")),
    "sonstiges": ("Sonstiges", ()),
}
# Gutschriften (z. B. Facebook-Monetarisierung: Meta stellt die Rechnung in unserem Namen aus) sind EINNAHMEN.
EINNAHME_KATEGORIEN = {"umsatz": "Betriebseinnahmen (Kleinunternehmer)",
                       "anlage_abgang": "Verkauf oder private Weiternutzung eines Geräts/GWG (Erlös bzw. Teilwert)"}
ARTEN = ("ausgabe", "einnahme")
_GUTSCHRIFT = re.compile(r"(?i)gutschrift|self[- ]?billing|selbstfakturierung|credit\s+note|auszahlung|payout|monetarisierung|"
                         r"remittance|zahlungsavis|"
                         r"werbeeinnahmen|in\s+ihrem\s+namen|on\s+your\s+behalf")
STATUS = ("zu_pruefen", "gebucht", "verworfen")
GWG_GRENZE_CENT = 80000        # 800 €; beim Kleinunternehmer zaehlt der Bruttobetrag (kein Vorsteuerabzug)
PRIVAT = "privat"              # Etappe 11: Position einer gemischten Rechnung, die nicht fuer die Firma war (§ 12 EStG)


def _teil_pruefen(p: dict) -> dict:
    """Eine Position der Aufteilung pruefen: Betrag, Kategorie (oder „privat“), GWG-Grenze, Nutzungsdauer bei Anlagen."""
    try:
        c = cent(p.get("betrag"))
    except ValueError:
        raise ValueError(f"Position „{p.get('text', '')}“: Betrag ungueltig.") from None
    k = str(p.get("kategorie") or "").strip()
    if k != PRIVAT and k not in KATEGORIEN:
        raise ValueError(f"Position „{p.get('text', '')}“: bitte Kategorie oder „privat“ waehlen.")
    t = {"text": str(p.get("text") or "").strip()[:200], "betrag_cent": c, "kategorie": k}
    if k == "gwg" and abs(c) > GWG_GRENZE_CENT:
        raise ValueError(f"{t['text'] or 'Position'}: ueber 800 € ist es kein geringwertiges Wirtschaftsgut -- bitte als "
                         "Anlagegut buchen (Abschreibung ueber die Nutzungsdauer).")
    if k == "anlage":
        try:
            t["nutzungsdauer_jahre"] = int(p.get("nutzungsdauer_jahre") or 0)
        except (TypeError, ValueError):
            t["nutzungsdauer_jahre"] = 0
        if not 1 <= t["nutzungsdauer_jahre"] <= 50:
            raise ValueError("Nutzungsdauer in Jahren angeben (Computer/Software: 1, Foto/Video-Technik: 7).")
    return t


def teile(f: dict) -> list[dict]:
    """Positionen einer Buchung: die Aufteilung oder -- ohne Aufteilung -- der ganze Beleg als eine Position."""
    if f.get("aufteilung"):
        return f["aufteilung"]
    return [{"text": f.get("leistung", ""), "betrag_cent": f.get("betrag_cent", 0), "kategorie": f.get("kategorie", "sonstiges"),
             **({"nutzungsdauer_jahre": f["nutzungsdauer_jahre"]} if f.get("nutzungsdauer_jahre") else {})}]


def anteile(betrag_cent: int, teile_: list[dict]) -> list[int]:
    """Zahlung anteilig auf die Positionen verteilen (Rest-Cent auf die groesste Position) -- Summe bleibt exakt."""
    gesamt = sum(t["betrag_cent"] for t in teile_)
    if not gesamt:
        return [0] * len(teile_)
    roh = [betrag_cent * t["betrag_cent"] / gesamt for t in teile_]
    out = [int(round(x)) for x in roh]
    diff = betrag_cent - sum(out)
    if diff:
        i = max(range(len(teile_)), key=lambda j: abs(teile_[j]["betrag_cent"]))
        out[i] += diff
    return out


# -- Auslesen -------------------------------------------------------------------------------------------------------

def _lokal(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _finde(el, *pfad):
    """Erstes Element entlang lokaler Namen (Namensraeume egal)."""
    kandidaten = [el]
    for name in pfad:
        naechste = []
        for k in kandidaten:
            naechste += [c for c in k if _lokal(c.tag) == name]
        if not naechste:
            return None
        kandidaten = naechste
    return kandidaten[0]


def _text(el, *pfad) -> str:
    x = _finde(el, *pfad)
    return (x.text or "").strip() if x is not None and x.text else ""


def _alle(el, name: str) -> list:
    return [x for x in el.iter() if _lokal(x.tag) == name] if el is not None else []


def _brutto(netto: str, prozent: str) -> str:
    """E-Rechnungs-Positionen sind netto -- fuer den Kleinunternehmer zaehlt brutto (kein Vorsteuerabzug)."""
    try:
        c = cent(netto.replace(".", ","))
        p = float((prozent or "0").replace(",", "."))
    except ValueError:
        return ""
    return eur(round(c * (1 + p / 100))).replace(" €", "")


def _e_positionen(root, art: str) -> list[dict]:
    out = []
    if art in ("Invoice", "CreditNote"):
        for z in _alle(root, "InvoiceLine") + _alle(root, "CreditNoteLine"):
            out.append({"text": _text(z, "Item", "Name"),
                        "betrag": _brutto(_text(z, "LineExtensionAmount"), _text(z, "Item", "ClassifiedTaxCategory", "Percent"))})
    else:
        for z in _alle(root, "IncludedSupplyChainTradeLineItem"):
            s = _finde(z, "SpecifiedLineTradeSettlement")
            out.append({"text": _text(z, "SpecifiedTradeProduct", "Name"),
                        "betrag": _brutto(_text(s, "SpecifiedTradeSettlementLineMonetarySummation", "LineTotalAmount"),
                                          _text(s, "ApplicableTradeTax", "RateApplicablePercent")) if s is not None else ""})
    return [p for p in out if p["text"] and p["betrag"]]


def e_rechnung_lesen(xml: bytes) -> dict | None:
    """XRechnung/ZUGFeRD (UBL oder CII) -> Felder. None, wenn keine E-Rechnung."""
    try:
        from defusedxml import ElementTree as ET        # sicher gegen XML-Bomben/Entitaeten
        root = ET.fromstring(xml)
    except Exception:
        return None
    art = _lokal(root.tag)
    if art in ("Invoice", "CreditNote"):                 # UBL (XRechnung)
        lieferant = (_text(root, "AccountingSupplierParty", "Party", "PartyLegalEntity", "RegistrationName")
                     or _text(root, "AccountingSupplierParty", "Party", "PartyName", "Name"))
        betrag = _text(root, "LegalMonetaryTotal", "PayableAmount") or _text(root, "LegalMonetaryTotal", "TaxInclusiveAmount")
        waehrung = (_finde(root, "LegalMonetaryTotal", "PayableAmount").get("currencyID", "EUR")
                    if _finde(root, "LegalMonetaryTotal", "PayableAmount") is not None else "EUR")
        return {"format": "XRechnung (UBL)", "lieferant": lieferant, "rechnungsnummer": _text(root, "ID"),
                "rechnungsdatum": _text(root, "IssueDate"), "faellig_am": _text(root, "DueDate"),
                "betrag": betrag.replace(".", ",") if betrag else "", "waehrung": waehrung,
                "leistung": _text(root, "InvoiceLine", "Item", "Name"), "positionen": _e_positionen(root, art)}
    if art == "CrossIndustryInvoice":                    # CII (ZUGFeRD/Factur-X/XRechnung-CII)
        def d(s):
            s = (s or "").strip()
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", s) else s
        tx = _finde(root, "SupplyChainTradeTransaction")
        summe = _finde(tx, "ApplicableHeaderTradeSettlement", "SpecifiedTradeSettlementHeaderMonetarySummation") if tx is not None else None
        betrag = (_text(summe, "DuePayableAmount") or _text(summe, "GrandTotalAmount")) if summe is not None else ""
        return {"format": "ZUGFeRD / Factur-X (CII)",
                "lieferant": _text(tx, "ApplicableHeaderTradeAgreement", "SellerTradeParty", "Name") if tx is not None else "",
                "rechnungsnummer": _text(root, "ExchangedDocument", "ID"),
                "rechnungsdatum": d(_text(root, "ExchangedDocument", "IssueDateTime", "DateTimeString")),
                "faellig_am": d(_text(tx, "ApplicableHeaderTradeSettlement", "SpecifiedTradePaymentTerms", "DueDateDateTime",
                                      "DateTimeString")) if tx is not None else "",
                "betrag": betrag.replace(".", ",") if betrag else "",
                "waehrung": _text(tx, "ApplicableHeaderTradeSettlement", "InvoiceCurrencyCode") if tx is not None else "EUR",
                "leistung": _text(tx, "IncludedSupplyChainTradeLineItem", "SpecifiedTradeProduct", "Name") if tx is not None else "",
                "positionen": _e_positionen(root, art)}
    return None


def _ocr_bild(pfad: Path) -> str:
    if not shutil.which("tesseract"):
        return ""
    try:
        r = subprocess.run(["tesseract", str(pfad), "stdout", "-l", "deu+eng"], capture_output=True, text=True, timeout=120)
        return r.stdout
    except Exception:
        return ""


def _ocr_pdf(daten: bytes, seiten: int = 3) -> str:
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        quelle = Path(tmp) / "in.pdf"
        quelle.write_bytes(daten)
        try:
            subprocess.run(["pdftoppm", "-r", "300", "-l", str(seiten), "-png", str(quelle), str(Path(tmp) / "s")],
                           capture_output=True, timeout=180, check=True)
        except Exception:
            return ""
        return "\n".join(_ocr_bild(p) for p in sorted(Path(tmp).glob("s*.png")))


def auslesen(daten: bytes, dateiname: str) -> dict:
    """-> {text, text_quelle, e_rechnung (Felder oder None)}. Bevorzugt: E-Rechnung > PDF-Text > OCR."""
    endung = Path(dateiname).suffix.lower()
    if endung == ".xml":
        er = e_rechnung_lesen(daten)
        return {"text": daten.decode("utf-8", "replace")[:15000], "text_quelle": "xml", "e_rechnung": er}
    if endung == ".pdf" or daten[:5] == b"%PDF-":
        text, er = "", None
        try:
            from pypdf import PdfReader
            leser = PdfReader(io.BytesIO(daten))
            for name, inhalte in (leser.attachments or {}).items():       # ZUGFeRD/Factur-X: XML im PDF
                if name.lower().endswith(".xml"):
                    er = e_rechnung_lesen(inhalte[0]) or er
            text = "\n".join((s.extract_text() or "") for s in leser.pages[:6])
        except Exception:
            pass
        if len(text.strip()) >= 40:
            return {"text": text[:15000], "text_quelle": "pdf-text", "e_rechnung": er}
        ocr = _ocr_pdf(daten)
        return {"text": (ocr or text)[:15000], "text_quelle": "ocr" if ocr else ("pdf-text" if text else "leer"),
                "e_rechnung": er}
    if endung in ENDUNGEN:
        with tempfile.NamedTemporaryFile(suffix=endung) as f:
            f.write(daten)
            f.flush()
            ocr = _ocr_bild(Path(f.name))
        return {"text": ocr[:15000], "text_quelle": "ocr" if ocr.strip() else "leer", "e_rechnung": None}
    return {"text": "", "text_quelle": "leer", "e_rechnung": None}


_BETRAG = r"(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}|-?\d+\.\d{2})"
_DATUM = r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})"
_MONATE_EN = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}
_DATUM_EN = r"(\d{1,2})[-\s]([A-Za-z]{3})[a-z]*[-\s,]+(\d{4})"                 # 25-Sep-2026 (Meta, englische Belege)


def _iso(t: str, tag: str, monat: str, jahr: str) -> str:
    j = int(jahr) + (2000 if len(jahr) == 2 else 0)
    try:
        return date(j, int(monat), int(tag)).isoformat()
    except ValueError:
        return ""


def kategorie_raten(text: str) -> str:
    t = (text or "").lower()
    treffer = [(sum(t.count(w) for w in woerter), k) for k, (_, woerter) in KATEGORIEN.items() if woerter]
    beste = max(treffer, default=(0, "sonstiges"))
    return beste[1] if beste[0] > 0 else "sonstiges"


_POS_BETRAG = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")
_POS_NICHT = re.compile(r"(?i)summe|gesamt|zwischensumme|netto|brutto|mwst|ust\b|umsatzsteuer|steuer|rechnungsbetrag|"
                        r"zu zahlen|zahlbar|total|bezahlt|zahlung|betrag|saldo|guthaben|iban|konto|seite \d")


def positionen_regeln(text: str) -> list[dict]:
    """Positionszeilen aus PDF-/OCR-Text: Zeile mit Artikeltext und Betrag; der letzte Betrag der Zeile ist der
    Zeilenbetrag (brutto, wie auf Verbraucher-/Shop-Rechnungen). Summen-, Steuer- und Zahlungszeilen fallen raus."""
    out, puffer = [], []
    for z in (text or "").replace("\xa0", " ").splitlines():
        z = z.strip()
        b = _POS_BETRAG.findall(z)
        if re.match(r"(?i)^(asin|sku)\b", z):                 # Artikelnummer unter dem Text (Amazon) -- Text behalten
            continue
        if _POS_NICHT.search(z) or re.match(r"(?i)^(beschreibung|menge|pos\.?|artikel|\(?(ohne|inkl)\.)", z) or ":" in z:
            puffer = []                                      # Kopf-, Summen-, Adress- oder Feldzeile: kein Artikeltext
            continue
        if not b:
            if len(re.findall(r"[A-Za-zÄÖÜäöüß]", z)) >= 3:
                puffer = puffer if len(puffer) >= 3 else puffer + [z]   # mehrzeiliger Artikeltext: Anfang = Produktname
            continue
        if len(re.findall(r"[A-Za-zÄÖÜäöüß]", z[:z.find(b[0])])) < 3 and puffer:   # reine Zahlenzeile unter dem Text
            t = re.sub(r"\s*\|\s*B0\w+\s*$", "", " ".join(puffer)).strip()
            puffer = []
            try:
                c = cent(b[-1])
            except ValueError:
                continue
            if c:
                out.append({"text": t[:200], "betrag": eur(c).replace(" €", "")})
            continue
        puffer = []
        vorne = z[:z.find(b[0])]
        t = re.sub(r"^\d{1,3}[.)]?\s+", "", vorne).strip()                        # Positionsnummer
        for _ in range(3):                                                         # Menge, Einheit, Steuersatz hinten
            t = re.sub(r"\s+(\d{1,3}([.,]\d+)?\s*(Stk\.?|St\.?|x|%|€|EUR)?)$", "", t, flags=re.I).strip()
        if len(re.findall(r"[A-Za-zÄÖÜäöüß]", t)) < 3:
            continue
        try:
            c = cent(b[-1])
        except ValueError:
            continue
        if c:
            out.append({"text": t[:200], "betrag": eur(c).replace(" €", "")})
    return out[:40]


def vorschlag_regeln(text: str, e_rechnung: dict | None = None) -> dict:
    """Schneller Vorschlag ohne KI. E-Rechnungs-Felder haben Vorrang (exakt)."""
    t = text or ""
    gutschrift = bool(_GUTSCHRIFT.search(t))
    v = {"lieferant": "", "rechnungsnummer": "", "rechnungsdatum": "", "betrag": "", "faellig_am": "", "leistung": "",
         "art": "einnahme" if gutschrift else "ausgabe", "kategorie": "umsatz" if gutschrift else kategorie_raten(t),
         "quelle": "regeln"}
    zeilen = [z.strip() for z in t.splitlines() if z.strip()]
    m = re.search(r"(?i)(?:rechnungs?[- ]?(?:nummer|nr\.?)|rechnung\s+nr\.?|invoice\s+(?:no\.?|number)|payment\s+(?:no\.?|number)|"
                  r"beleg[- ]?(?:nummer|nr\.?))"
                  r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_.]{2,30})", t)
    if m:
        v["rechnungsnummer"] = m.group(1).rstrip(".")
    m = (re.search(r"(?i)(?:rechnungsdatum|invoice\s+date|belegdatum|leistungsdatum)\s*[:]?\s*" + _DATUM, t)
         or re.search(r"(?i)(?<![a-zäöü])datum\s*[:]?\s*" + _DATUM, t) or re.search(_DATUM, t))
    if m:
        v["rechnungsdatum"] = _iso(t, *m.groups()[-3:])
    else:
        m = (re.search(r"(?i)(?:payment|invoice|remittance)\s+date\s*:?\s*" + _DATUM_EN, t) or re.search(_DATUM_EN, t))
        if m and m.group(2).lower()[:3] in _MONATE_EN:
            v["rechnungsdatum"] = _iso(t, m.group(1), str(_MONATE_EN[m.group(2).lower()[:3]]), m.group(3))
    betraege = []
    for z in zeilen:
        if re.search(r"(?i)(gesamt|rechnungsbetrag|zu zahlen|endbetrag|summe|total|brutto|zahlbetrag)", z):
            betraege += re.findall(_BETRAG, z)
    if not betraege:
        betraege = re.findall(_BETRAG + r"\s*(?:€|EUR)", t)
    if betraege:
        werte = []
        for b in betraege:
            try:
                werte.append((abs(cent(b)), b))
            except ValueError:
                continue
        if werte:
            v["betrag"] = eur(max(werte)[0]).replace(" €", "")
    w = re.search(r"(?i)(?:currency|w[aä]hrung)\s*:?\s*([A-Z]{3})\b", t)
    waehrung = w.group(1).upper() if w else ("USD" if re.search(r"\$\s?\d|\bUSD\b", t) and "€" not in t and "EUR" not in t else "")
    if waehrung and waehrung != "EUR":                       # EUeR zaehlt den Euro-Betrag, der aufs Konto kam
        v |= {"waehrung": waehrung, "betrag_fremd": v["betrag"], "betrag": ""}
        if v["betrag_fremd"]:
            v["leistung"] = f"{'Auszahlung' if gutschrift else 'Kauf'} {v['betrag_fremd']} {waehrung}"
    if zeilen:
        v["lieferant"] = re.split(r"\s+[·|•]\s+", zeilen[0])[0][:120]      # Absenderzeile "Firma · Strasse · Ort"
    if not v.get("waehrung"):                                   # Fremdwaehrung: Euro-Betrag kommt vom Konto
        v["positionen"] = positionen_regeln(t)
    # Sammel-PDF mit mehreren Rechnungen (Amazon: eine je Verkaeufer): Zahlbetraege aller Rechnungen addieren
    zahl = []
    for teil in re.split(r"Rechnungsdetails", t.replace("\xa0", " "))[1:]:
        m = re.search(r"Zahlbetrag\s*(-?\d{1,3}(?:\.\d{3})*,\d{2})", teil)
        if m:
            zahl.append(cent(m.group(1)))
    if len(zahl) >= 2 and not v.get("waehrung"):
        v["betrag"] = eur(sum(zahl)).replace(" €", "")
    if e_rechnung:
        v.update({k: e_rechnung[k] for k in ("lieferant", "rechnungsnummer", "rechnungsdatum", "betrag", "faellig_am", "leistung",
                                              "positionen") if e_rechnung.get(k)})
        v["quelle"] = "e-rechnung"
    return v


LLM_SYSTEM = (
    "Du liest den Text einer Rechnung oder Gutschrift und antwortest NUR mit einem JSON-Objekt, ohne Erklaerung, mit genau "
    'diesen Feldern: {"art": "ausgabe", "lieferant": "", "rechnungsnummer": "", "rechnungsdatum": "JJJJ-MM-TT", '
    '"betrag": "123,45", "faellig_am": "JJJJ-MM-TT", "leistung": "kurz, worum es geht", "kategorie": "", '
    '"positionen": [{"text": "Artikel", "betrag": "12,34", "kategorie": ""}]}. '
    "positionen = jede einzelne Rechnungsposition mit ihrem Gesamtbetrag BRUTTO (inkl. Umsatzsteuer), Versandkosten "
    "als eigene Position, Rabatte negativ, je Position die passende kategorie (wie unten); keine Summen- oder Steuerzeilen. "
    "art = \"einnahme\", wenn WIR Geld bekommen (Gutschrift, Auszahlung, Monetarisierung, Vergütung, die der Aussteller in "
    "unserem Namen abrechnet), sonst \"ausgabe\". lieferant = das Unternehmen, das die Rechnung/Gutschrift ausgestellt hat. "
    "betrag = Endbetrag brutto im deutschen Format, NUR wenn er in Euro angegeben ist; bei anderer Waehrung betrag leer lassen "
    "und stattdessen \"waehrung\" (z. B. USD) und \"betrag_fremd\" (z. B. 282,37) angeben. kategorie: bei einnahme immer \"umsatz\", bei ausgabe genau einer von: "
    + ", ".join(KATEGORIEN) + ". Steht ein Wert nicht im Text, leerer String. Nichts erfinden, nichts schaetzen.")


def vorschlag_llm(antwort: str) -> dict | None:
    """Antwort des Backoffice-Modells -> geprueftes Vorschlags-Dict (tolerant gegenueber Text um das JSON)."""
    m = re.search(r"\{.*\}", antwort or "", re.S)
    if not m:
        return None
    try:
        roh = json.loads(m.group(0))
    except ValueError:
        return None
    v = {"quelle": "backoffice"}
    for k in ("lieferant", "rechnungsnummer", "leistung"):
        v[k] = str(roh.get(k) or "").strip()[:200]
    for k in ("rechnungsdatum", "faellig_am"):
        s = str(roh.get(k) or "").strip()[:10]
        try:
            v[k] = date.fromisoformat(s).isoformat() if s else ""
        except ValueError:
            v[k] = ""
    try:
        v["betrag"] = eur(abs(cent(roh.get("betrag")))).replace(" €", "") if str(roh.get("betrag") or "").strip() else ""
    except ValueError:
        v["betrag"] = ""
    wg = str(roh.get("waehrung") or "").strip().upper()[:3]
    if wg and wg != "EUR":
        v |= {"waehrung": wg, "betrag_fremd": str(roh.get("betrag_fremd") or roh.get("betrag") or "").strip()[:20], "betrag": ""}
    art = str(roh.get("art") or "").strip().lower()
    v["art"] = art if art in ARTEN else "ausgabe"
    pos = []
    for p in roh.get("positionen") or []:
        if isinstance(p, dict) and str(p.get("text") or "").strip():
            try:
                k = str(p.get("kategorie") or "").strip().lower()
                pos.append({"text": str(p["text"]).strip()[:200], "betrag": eur(cent(p.get("betrag"))).replace(" €", "")}
                           | ({"kategorie": k} if k in KATEGORIEN else {}))
            except (ValueError, TypeError):
                continue
    if pos and not v.get("waehrung"):
        v["positionen"] = pos[:40]
    k = str(roh.get("kategorie") or "").strip().lower()
    v["kategorie"] = "umsatz" if v["art"] == "einnahme" else (k if k in KATEGORIEN else "")
    return v


# -- Speicher -------------------------------------------------------------------------------------------------------

class EingangStore:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t}
            if t == "eingang_angelegt":
                out[d["nummer"]] = dict(d) | {"status": "zu_pruefen", "eingegangen": e["ts"], "felder": {}, "verlauf": [spur]}
            elif not str(t).startswith("eingang_") or d.get("nummer") not in out:
                continue
            elif t == "eingang_vorschlag":
                x = out[d["nummer"]]
                x["vorschlag"] = (x.get("vorschlag") or {}) | {k: v for k, v in d["vorschlag"].items() if v}
                x["verlauf"].append(spur | {"quelle": d["vorschlag"].get("quelle", "")})
            elif t == "eingang_llm_auftrag":
                out[d["nummer"]]["llm_auftrag"] = d["auftrag_id"]
            elif t == "eingang_erinnerung":                  # Kalender: Euro-Betrag nachtragen (Fremdwaehrung)
                out[d["nummer"]]["erinnerung"] = d["termin"]
            elif t == "eingang_gebucht":
                x = out[d["nummer"]]
                x["felder"], x["status"] = d["felder"], "gebucht"
                x["gebucht_am"] = e["ts"]
                x["verlauf"].append(spur | {"felder": sorted(d["felder"])})
            elif t == "eingang_bezahlt":                     # betrag_cent fehlt bei Alt-Eintraegen = voller Betrag
                x = out[d["nummer"]]
                x.setdefault("zahlungen", []).append({k: d.get(k) for k in ("datum", "betrag_cent", "zuordnung_jahr", "notiz")})
                x["verlauf"].append(spur | {"datum": d["datum"], "betrag_cent": d.get("betrag_cent")})
            elif t == "eingang_zahlung_storniert":
                x = out[d["nummer"]]
                x["zahlungen"][d["index"]] |= {"storniert": True, "storno_grund": d.get("grund", ""), "storniert_am": e["ts"]}
                x["verlauf"].append(spur | {"grund": d.get("grund", "")})
            elif t == "eingang_verworfen":
                x = out[d["nummer"]]
                x["status"], x["grund"] = "verworfen", d.get("grund", "")
                x["verlauf"].append(spur | {"grund": d.get("grund", "")})
        for x in out.values():                               # Zahlstand aus Buchung + Zahlungen (Etappe 7)
            gesamt = (x.get("felder") or {}).get("betrag_cent")
            zs = x.setdefault("zahlungen", [])
            for z in zs:
                if z.get("betrag_cent") is None:
                    z["betrag_cent"] = gesamt or 0
            gueltig = [z for z in zs if not z.get("storniert")]
            x["bezahlt_cent"] = sum(z["betrag_cent"] for z in gueltig)
            x["bezahlt_am"] = gueltig[-1]["datum"] if gesamt and gueltig and abs(x["bezahlt_cent"]) >= abs(gesamt) else ""
        return out

    def liste(self) -> list[dict]:
        out = []
        for x in self._falte(self.bh.eintraege()).values():
            f, v = x.get("felder") or {}, x.get("vorschlag") or {}
            out.append({"nummer": x["nummer"], "dateiname": x.get("dateiname"), "eingegangen": x["eingegangen"],
                        "status": x["status"], "quelle": x.get("quelle"), "text_quelle": x.get("text_quelle"),
                        "lieferant": f.get("lieferant") or v.get("lieferant", ""),
                        "rechnungsdatum": f.get("rechnungsdatum") or v.get("rechnungsdatum", ""),
                        "betrag_cent": f.get("betrag_cent") if f else (_cent_oder_none(v.get("betrag"))),
                        "kategorie": f.get("kategorie") or v.get("kategorie", ""), "bezahlt_am": x.get("bezahlt_am", ""),
                        "art": f.get("art") or v.get("art") or "ausgabe",
                        "bezahlt_cent": x.get("bezahlt_cent", 0), "faellig_am": f.get("faellig_am", ""),
                        "aufgeteilt": len(f.get("aufteilung") or []),
                        "teils_privat": any(t["kategorie"] == PRIVAT for t in f.get("aufteilung") or []),
                        "e_rechnung": bool(x.get("e_rechnung"))})
        return sorted(out, key=lambda x: x["nummer"], reverse=True)

    def get(self, nummer: str) -> dict | None:
        return self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())

    def vorhanden(self, sha: str) -> str:
        for x in self._falte(self.bh.eintraege()).values():
            if any(b.get("sha256") == sha for b in x.get("belege", [])):
                return x["nummer"]
        return ""

    def aufnehmen(self, daten: bytes, dateiname: str, *, quelle: str = "upload", mail_id: str = "",
                  von: str = "") -> dict:
        """Beleg aufnehmen: auslesen (ausserhalb der Sperre, OCR dauert), dann Nummer + Datei + Eintrag atomar."""
        name = re.sub(r"[\\\\/:*?\"<>|]+", "_", Path(dateiname or "beleg").name)[:120] or "beleg"
        if not daten:
            raise ValueError(f"{name}: leere Datei.")
        if len(daten) > MAX_BYTES:
            raise ValueError(f"{name}: groesser als 15 MB.")
        if Path(name).suffix.lower() not in ENDUNGEN:
            raise ValueError(f"{name}: Dateityp nicht unterstuetzt (PDF, XML, JPG, PNG, HEIC, WEBP, TIFF).")
        sha = hashlib.sha256(daten).hexdigest()
        if (alt := self.vorhanden(sha)):
            return {"nummer": alt, "doppelt": True}
        a = auslesen(daten, name)
        vorschlag = vorschlag_regeln(a["text"], a["e_rechnung"])
        heute = jetzt().date()

        def pruefe(eintraege):
            for x in self._falte(eintraege).values():            # zweiter Blick unter der Sperre (paralleler Upload)
                if any(b.get("sha256") == sha for b in x.get("belege", [])):
                    raise _Doppelt(x["nummer"])

        def erzeuge(nummer, eintraege):
            return ({"dateiname": name, "mime": ENDUNGEN[Path(name).suffix.lower()], "quelle": quelle,
                     "mail_id": mail_id, "text_quelle": a["text_quelle"], "text": a["text"],
                     "e_rechnung": a["e_rechnung"], "vorschlag": vorschlag}, [(daten, name, "beleg")])
        try:
            ev = self.bh.festschreiben("ER", "eingang_angelegt", erzeuge, jahr=heute.year, bezug=name, von=von,
                                       pruefe=pruefe)
        except _Doppelt as d:
            return {"nummer": d.args[0], "doppelt": True}
        return {"nummer": ev["daten"]["nummer"], "text_quelle": a["text_quelle"], "vorschlag": vorschlag}

    def llm_auftrag_merken(self, nummer: str, auftrag_id: str) -> None:
        self.bh.erfassen("eingang_llm_auftrag", {"nummer": nummer, "auftrag_id": auftrag_id}, von="LUNA-Belege")

    def erinnerung_merken(self, nummer: str, termin: dict) -> None:
        self.bh.erfassen("eingang_erinnerung", {"nummer": nummer, "termin": termin}, von="LUNA-Belege")

    def vorschlag_ergaenzen(self, nummer: str, vorschlag: dict) -> None:
        self.bh.erfassen("eingang_vorschlag", {"nummer": nummer, "vorschlag": vorschlag}, von="LUNA-Belege")

    def buchen(self, nummer: str, felder: dict, *, von: str = "") -> dict:
        """CEO bestaetigt die Werte (auch erneut = Korrektur mit Verlauf)."""
        nummer = (nummer or "").strip().upper()
        f = {"lieferant": str(felder.get("lieferant") or "").strip()[:200],
             "lieferant_firma": str(felder.get("lieferant_firma") or "").strip().upper()[:20],
             "rechnungsnummer": str(felder.get("rechnungsnummer") or "").strip()[:60],
             "leistung": str(felder.get("leistung") or "").strip()[:300],
             "notiz": str(felder.get("notiz") or "").strip()[:500]}
        if not f["lieferant"]:
            raise ValueError("Lieferant fehlt.")
        for k, name in (("rechnungsdatum", "Rechnungsdatum"), ("faellig_am", "Faellig am")):
            s = str(felder.get(k) or "").strip()
            try:
                f[k] = date.fromisoformat(s[:10]).isoformat() if s else ""
            except ValueError:
                raise ValueError(f"{name}: ungueltiges Datum.") from None
        if not f["rechnungsdatum"]:
            raise ValueError("Rechnungsdatum fehlt.")
        try:
            f["betrag_cent"] = cent(felder.get("betrag"))
        except ValueError:
            raise ValueError("Betrag fehlt oder ist ungueltig.") from None
        if f["betrag_cent"] == 0:
            raise ValueError("Betrag darf nicht 0 sein.")
        f["art"] = str(felder.get("art") or "ausgabe").strip()
        if f["art"] not in ARTEN:
            raise ValueError("Art muss Ausgabe oder Einnahme (Gutschrift) sein.")
        aufteilung = felder.get("aufteilung") or []
        if aufteilung and f["art"] == "einnahme":
            raise ValueError("Gutschriften werden nicht aufgeteilt.")
        if aufteilung:                                           # Etappe 11: Positionen, auch „privat“
            teile_ = [_teil_pruefen(p) for p in aufteilung]
            summe = sum(t["betrag_cent"] for t in teile_)
            if summe != f["betrag_cent"]:
                raise ValueError(f"Summe der Positionen {eur(summe)} passt nicht zum Rechnungsbetrag {eur(f['betrag_cent'])} "
                                 "-- Versand/Rabatt als eigene Position ergaenzen.")
            betrieb = [t for t in teile_ if t["kategorie"] != PRIVAT]
            if not betrieb:
                raise ValueError("Alles privat -- das ist kein Betriebsbeleg: bitte „Kein Beleg / verwerfen“.")
            if len(teile_) == 1:                                   # eine Position = ganz normale Buchung
                felder = felder | {"kategorie": teile_[0]["kategorie"],
                                   "nutzungsdauer_jahre": teile_[0].get("nutzungsdauer_jahre")}
            else:
                f["aufteilung"] = teile_
                felder = felder | {"kategorie": max(betrieb, key=lambda t: abs(t["betrag_cent"]))["kategorie"]}
        k = str(felder.get("kategorie") or ("umsatz" if f["art"] == "einnahme" else "")).strip()
        if k not in (EINNAHME_KATEGORIEN if f["art"] == "einnahme" else KATEGORIEN):
            raise ValueError("Bitte eine Kategorie waehlen.")
        f["kategorie"] = k
        if "aufteilung" not in f and f["art"] == "ausgabe":
            ganz = _teil_pruefen({"text": f["leistung"], "betrag": eur(f["betrag_cent"]).replace(" €", ""), "kategorie": k,
                                  "nutzungsdauer_jahre": felder.get("nutzungsdauer_jahre")})
            if ganz.get("nutzungsdauer_jahre"):
                f["nutzungsdauer_jahre"] = ganz["nutzungsdauer_jahre"]
        doppelt: list = []

        def pruefe(eintraege):
            alle = self._falte(eintraege)
            if nummer not in alle:
                raise KeyError(nummer)
            if alle[nummer]["status"] == "verworfen":
                raise ValueError(f"{nummer} ist verworfen.")
            if f["rechnungsnummer"] and not felder.get("trotz_doppelt"):
                for x in alle.values():
                    g = x.get("felder") or {}
                    if x["nummer"] != nummer and x["status"] == "gebucht" and g.get("rechnungsnummer") == f["rechnungsnummer"] \
                            and g.get("lieferant", "").lower() == f["lieferant"].lower():
                        doppelt.append(x["nummer"])
            if doppelt:
                raise ValueError(f"Rechnung {f['rechnungsnummer']} von {f['lieferant']} ist schon als {doppelt[0]} gebucht.")
        self.bh.erfassen_geprueft("eingang_gebucht", {"nummer": nummer, "felder": f}, von=von, pruefe=pruefe)
        return {"nummer": nummer, "felder": f}

    def bezahlt(self, nummer: str, datum: str, *, betrag=None, zuordnung_jahr=None, notiz: str = "",
                von: str = "") -> dict:
        """Zahlung (Abfluss) erfassen; ohne Betrag = offener Rest, sonst Teilzahlung. `zuordnung_jahr` = 10-Tage-Regel."""
        from .eigenbelege import datum_pruefen, zuordnung_pruefen
        nummer = (nummer or "").strip().upper()
        tag = datum_pruefen(datum)
        zuordnung = zuordnung_pruefen(tag, zuordnung_jahr)
        with self.bh._gesperrt():
            x = self._falte(self.bh._eintraege()).get(nummer)
            if not x:
                raise KeyError(nummer)
            if x["status"] != "gebucht":
                raise ValueError("Erst buchen, dann als bezahlt markieren.")
            gesamt = x["felder"]["betrag_cent"]
            rest = gesamt - x["bezahlt_cent"]
            if rest == 0:
                raise ValueError(f"{nummer} ist bereits vollstaendig bezahlt.")
            b = rest if betrag in (None, "") else cent(betrag) * (1 if gesamt > 0 else -1)
            if not 0 < b / (1 if gesamt > 0 else -1) <= abs(rest):
                raise ValueError(f"Betrag muss zwischen 0,01 € und dem offenen Rest {eur(abs(rest))} liegen.")
            self.bh._anhaengen("eingang_bezahlt", {"nummer": nummer, "datum": tag, "betrag_cent": b,
                                                    "notiz": str(notiz or "").strip()[:300]}
                               | ({"zuordnung_jahr": zuordnung} if zuordnung else {}), von=von)
        return {"bezahlt_am": tag if b == rest else "", "betrag_cent": b, "rest_cent": rest - b}

    def zahlung_stornieren(self, nummer: str, index: int, grund: str, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund angeben.")

        def pruefe(eintraege):
            x = self._falte(eintraege).get(nummer)
            if not x:
                raise KeyError(nummer)
            if not isinstance(index, int) or not 0 <= index < len(x["zahlungen"]):
                raise ValueError("Diese Zahlung gibt es nicht.")
            if x["zahlungen"][index].get("storniert"):
                raise ValueError("Diese Zahlung ist bereits storniert.")
        self.bh.erfassen_geprueft("eingang_zahlung_storniert", {"nummer": nummer, "index": index, "grund": grund},
                                  von=von, pruefe=pruefe)
        return {"storniert": index}

    def verwerfen(self, nummer: str, grund: str, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund angeben (z. B. „kein Beleg, versehentlich hochgeladen“).")

        def pruefe(eintraege):
            x = self._falte(eintraege).get(nummer)
            if not x:
                raise KeyError(nummer)
            if x["status"] == "gebucht":
                raise ValueError("Gebuchte Belege werden nicht verworfen -- Buchung korrigieren.")
        self.bh.erfassen_geprueft("eingang_verworfen", {"nummer": nummer, "grund": grund}, von=von, pruefe=pruefe)
        return {"status": "verworfen"}


class _Doppelt(Exception):
    pass


def _cent_oder_none(b):
    try:
        return cent(b) if str(b or "").strip() else None
    except ValueError:
        return None


# -- Anbindungen ----------------------------------------------------------------------------------------------------

def llm_beauftragen(st: EingangStore, backoffice, nummer: str) -> str:
    """Genaueren Vorschlag beim lokalen Backoffice-Modell anfordern (stumm: keine Meldung, Ergebnis holt LUNA-OS)."""
    x = st.get(nummer)
    if backoffice is None or not x or len((x.get("text") or "").strip()) < 20:
        return ""
    aid = backoffice.anlegen("Text der Eingangsrechnung:\n\n" + x["text"][:6000], art="roh", system=LLM_SYSTEM,
                             zweck=f"beleg:{nummer}", stumm=True, von="LUNA-Belege")
    st.llm_auftrag_merken(nummer, aid)
    return aid


def llm_ergebnisse_uebernehmen(st: EingangStore, backoffice) -> int:
    """Fertige Backoffice-Auftraege in die Vorschlaege uebernehmen (beim Lesen in LUNA-OS aufgerufen)."""
    if backoffice is None:
        return 0
    n = 0
    for x in st._falte(st.bh.eintraege()).values():
        if x["status"] != "zu_pruefen" or not x.get("llm_auftrag") or (x.get("vorschlag") or {}).get("quelle") == "backoffice":
            continue
        a = backoffice.get(x["llm_auftrag"])
        if not a or a.get("status") != "fertig":
            continue
        v = vorschlag_llm(a.get("ergebnis") or "")
        if v:
            if (x.get("vorschlag") or {}).get("quelle") == "e-rechnung":      # E-Rechnung ist exakt -> nur Luecken fuellen
                v = {k: w for k, w in v.items() if not (x["vorschlag"].get(k)) or k == "quelle"}
            st.vorschlag_ergaenzen(x["nummer"], v)
            n += 1
    return n


def anhaenge(roh: bytes) -> list[tuple[str, bytes]]:
    """Anhaenge einer Mail (RFC 822) mit erlaubter Endung -- auch **inline** und verschachtelt (Apple Mail leitet
    PDFs als `inline`-Teil in `multipart/alternative` weiter; `iter_attachments()` sieht die nicht, BF-36).
    Eingebettete Bilder aus dem HTML (Logos, Signaturen: Content-ID oder < 20 KB) werden uebersprungen."""
    import email
    from email import policy
    m = email.message_from_bytes(roh, policy=policy.default)
    out = []
    for teil in m.walk():
        if teil.is_multipart():
            continue
        name = teil.get_filename() or ""
        endung = Path(name).suffix.lower()
        if endung not in ENDUNGEN:
            continue
        daten = teil.get_payload(decode=True) or b""
        if not daten:
            continue
        if (ENDUNGEN[endung].startswith("image/") and teil.get_content_disposition() != "attachment"
                and (teil.get("Content-ID") or len(daten) < 20_000)):
            continue
        out.append((name, daten))
    return out


FREMDWAEHRUNG_TAGE = 7          # CEO 2026-09-28: bis dahin ist der Euro-Betrag auf dem Konto


def fremdwaehrung_erinnern(st: EingangStore, google, heute: date | None = None) -> list[str]:
    """Belege in Fremdwaehrung (z. B. Meta-Auszahlung in USD) brauchen den Euro-Betrag vom Kontoauszug: LUNA legt dafuer
    einmalig einen Termin in ihrem Kalender an (Rechnungsdatum + 7 Tage, 09:00; liegt das zurueck: morgen). Geloescht
    wird er von `erinnerungen.erledigte_entfernen`, sobald der Beleg gebucht oder verworfen ist. Rueckgabe: Belegnummern."""
    from datetime import timedelta
    if google is None or not google.verfuegbar():
        return []
    heute = heute or jetzt().date()
    neu = []
    for x in st._falte(st.bh.eintraege()).values():
        v = x.get("vorschlag") or {}
        if x["status"] != "zu_pruefen" or x.get("erinnerung") or not v.get("waehrung") or v["waehrung"] == "EUR":
            continue
        try:
            basis = date.fromisoformat(v.get("rechnungsdatum") or x["eingegangen"][:10])
        except ValueError:
            basis = heute
        tag = basis + timedelta(days=FREMDWAEHRUNG_TAGE)
        if tag <= heute:
            tag = heute + timedelta(days=1)
        wer = v.get("lieferant") or x.get("dateiname", "")
        titel = f"💶 Euro-Betrag eintragen: {x['nummer']} {wer} ({v.get('betrag_fremd', '?')} {v['waehrung']})"
        r = google.termin_anlegen(titel, f"{tag.isoformat()}T09:00:00", f"{tag.isoformat()}T09:15:00",
                                  beschreibung=f"Betrag laut Beleg: {v.get('betrag_fremd', '?')} {v['waehrung']}. Den auf dem "
                                               "Konto eingegangenen bzw. abgebuchten Euro-Betrag (Kontoauszug) eintragen und "
                                               "buchen.\nLUNA-OS -> Belege -> " + x["nummer"], bestaetigt=True)
        if r.get("ok"):
            st.erinnerung_merken(x["nummer"], {"datum": tag.isoformat(), "id": r.get("termin_id", ""), "titel": titel})
            neu.append(x["nummer"])
    return neu


# -- Euro-Betrag per Telegram (CEO 2026-09-28) -----------------------------------------------------------------------
# „Facebook 241,80“ / „ER-2026-0002 241,80 € am 26.09.“ -> Vorschau mit Knoepfen -> bei ✅ buchen + Geldeingang erfassen.
# Regelbasiert (kein Raten durch ein Modell); gebucht wird erst nach dem Klick des CEO.

_ALIASE = {"meta": ("meta", "facebook", "fb", "instagram", "insta")}


def offene_fremdwaehrung(st: EingangStore) -> list[dict]:
    return [x for x in st._falte(st.bh.eintraege()).values()
            if x["status"] == "zu_pruefen" and (x.get("vorschlag") or {}).get("waehrung") not in (None, "", "EUR")]


def euro_zuordnen(text: str, offene: list[dict], heute: date | None = None) -> dict | None:
    """Nachricht -> {nummer, betrag_cent, datum, beleg} oder None (dann normaler Chat)."""
    if not offene or not text:
        return None
    heute = heute or jetzt().date()
    t = text.strip()
    if "?" in t:                                                 # Fragen sind nie ein Buchungsauftrag
        return None
    nr = re.search(r"(?i)\bER-\d{4}-\d{4}\b", t)
    rest = re.sub(r"(?i)\bER-\d{4}-\d{4}\b", " ", t)
    datum = ""
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})?", rest)
    if m:
        jahr = m.group(3) or str(heute.year)
        datum = _iso("", m.group(1), m.group(2), jahr)
        if datum and datum > heute.isoformat() and not m.group(3):
            datum = _iso("", m.group(1), m.group(2), str(heute.year - 1))
        rest = rest[:m.start()] + " " + rest[m.end():]
    betraege = re.findall(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})*,\d{1,2}|\d+(?:[.,]\d{1,2})?)(?![\w.,])\s*(€|eur\b|euro\b)?",
                          rest, re.I)
    mit_euro = [b for b, w in betraege if w]
    kandidaten = mit_euro or [b for b, _ in betraege if re.search(r"[.,]\d{1,2}$", b)]   # 2026 ist kein Betrag
    if len(kandidaten) != 1:
        return None
    try:
        betrag = cent(kandidaten[0])
    except ValueError:
        return None
    if betrag <= 0:
        return None
    beleg = None
    if nr:
        beleg = next((x for x in offene if x["nummer"] == nr.group(0).upper()), None)
    else:
        klein, treffer = rest.lower(), []
        for x in offene:
            name = str((x.get("vorschlag") or {}).get("lieferant") or "").lower()
            woerter = {w for w in re.findall(r"[a-zäöüß]{4,}", name)} - {"ireland", "limited", "gmbh", "platforms"}
            for k, al in _ALIASE.items():
                if k in name:
                    woerter |= set(al)
            if any(re.search(rf"\b{re.escape(w)}\b", klein) for w in woerter):
                treffer.append(x)
        if len(treffer) > 1:
            return None                                          # mehrdeutig -> Belegnummer noetig
        beleg = treffer[0] if treffer else None
        if beleg is None and len(offene) == 1 and (mit_euro or re.search(r"(?i)konto|eingegangen|gutgeschrieben", rest)):
            beleg = offene[0]
    if beleg is None:
        return None
    return {"nummer": beleg["nummer"], "betrag_cent": betrag, "datum": datum or heute.isoformat(), "beleg": beleg,
            "datum_angegeben": bool(datum)}


def euro_vorschau(z: dict) -> str:
    v = z["beleg"].get("vorschlag") or {}
    ein = v.get("art") == "einnahme"
    return (f"💶 {z['nummer']} · {v.get('lieferant') or z['beleg'].get('dateiname', '')}\n"
            f"{v.get('betrag_fremd', '?')} {v.get('waehrung', '')} → {eur(z['betrag_cent'])}\n"
            f"Als {'Einnahme' if ein else 'Ausgabe'} buchen und {'Geldeingang' if ein else 'Zahlung'} am "
            f"{date.fromisoformat(z['datum']).strftime('%d.%m.%Y')} erfassen?"
            + ("" if z["datum_angegeben"] else "\n(Anderes Datum? Schick z. B. „241,80 am 26.09.“)"))


def euro_buchen(st: EingangStore, nummer: str, betrag_cent: int, datum: str, *, von: str = "Telegram:CEO") -> dict:
    """Nach ✅ des CEO: Beleg mit den erkannten Feldern + Euro-Betrag buchen und die Zahlung erfassen."""
    x = st.get(nummer)
    if not x or x["status"] != "zu_pruefen":
        raise ValueError(f"{nummer} ist nicht mehr offen -- schon gebucht oder verworfen.")
    v = x.get("vorschlag") or {}
    ein = v.get("art") == "einnahme"
    kat = "umsatz" if ein else v.get("kategorie")
    if not kat or not v.get("lieferant"):
        raise ValueError(f"{nummer}: Lieferant/Kategorie nicht erkannt -- bitte in LUNA-OS buchen.")
    st.buchen(nummer, {"art": "einnahme" if ein else "ausgabe", "lieferant": v["lieferant"],
                       "rechnungsnummer": v.get("rechnungsnummer", ""), "rechnungsdatum": v.get("rechnungsdatum") or datum,
                       "betrag": eur(betrag_cent).replace(" €", ""), "kategorie": kat,
                       "leistung": v.get("leistung", ""),
                       "notiz": f"{v.get('betrag_fremd', '?')} {v.get('waehrung', '')} laut Beleg; Euro-Betrag per Telegram"},
              von=von)
    st.bezahlt(nummer, datum, von=von)
    return {"nummer": nummer, "betrag_cent": betrag_cent, "datum": datum, "art": "einnahme" if ein else "ausgabe"}


def absender_echt(roh: bytes, absender: list[str]) -> bool:
    """Absender ist einer der eigenen UND von Gmail bestaetigt: im obersten `Authentication-Results`-Kopf (den setzt
    mx.google.com beim Empfang) besteht DMARC oder DKIM fuer genau die Domain der Absenderadresse. Faelschungen des
    From-Kopfes (Phishing mit Anhang) fallen so durch -- auch wenn Gmail sie in den Spam gelegt hat."""
    import email
    from email import policy
    from email.utils import parseaddr
    m = email.message_from_bytes(roh, policy=policy.default)
    von = parseaddr(str(m.get("From", "")))[1].lower()
    if von not in absender:
        return False
    dom = re.escape(von.rsplit("@", 1)[-1])
    kopf = (m.get_all("Authentication-Results") or [""])[0]
    kopf = re.sub(r"\s+", " ", str(kopf).lower())
    if not kopf.startswith("mx.google.com"):
        return False
    return bool(re.search(rf"dmarc=pass [^;]*header\.from={dom}(?![\w.-])", kopf)
                or re.search(rf"dkim=pass [^;]*header\.i=@(?:[\w-]+\.)*{dom}(?![\w.-])", kopf))


MAIL_ABGELEGT = "eingang_mail_abgelegt"
MAIL_ORDNER = "LUNA"


def _ordner(art: str, jahr: str | int) -> str:
    return f"{MAIL_ORDNER}/{art}/{jahr}"


def mail_ordner(beleg: dict) -> str:
    """Zielordner einer erledigten Beleg-Mail: Gutschriften (Einnahmen) und Rechnungen getrennt, je Jahr.
    Jahr = Rechnungsdatum (gebucht, sonst Vorschlag), ersatzweise Eingangsdatum."""
    f, v = beleg.get("felder") or {}, beleg.get("vorschlag") or {}
    art = f.get("art") or v.get("art") or "ausgabe"
    jahr = str(f.get("rechnungsdatum") or v.get("rechnungsdatum") or "")[:4]
    if not re.fullmatch(r"20\d\d", jahr):
        jahr = str(beleg.get("eingegangen") or jetzt().isoformat())[:4]
    return _ordner("Gutschriften" if art == "einnahme" else "Rechnungen", jahr)


def _abgelegt(eintraege: list[dict]) -> set[str]:
    return {e["daten"].get("mail_id") for e in eintraege if e["typ"] == MAIL_ABGELEGT}


def _ablegen(st: EingangStore, google, mid: str, ordner: str, nummern: list[str]) -> bool:
    """Mail verschieben + gelesen; nur bei Erfolg protokollieren (sonst naechster Lauf erneut)."""
    if not hasattr(google, "mail_ablegen"):
        return False
    try:
        r = google.mail_ablegen(mid, ordner)
    except Exception:
        return False
    if not r.get("ok"):
        return False
    st.bh.erfassen(MAIL_ABGELEGT, {"mail_id": mid, "ordner": ordner, "belege": nummern}, von="LUNA-Mail")
    return True


def mails_ablegen(st: EingangStore, google) -> list[dict]:
    """Beleg-Mails, deren Anhang sicher im Kassenbuch liegt, aus dem Posteingang in `LUNA/<Art>/<Jahr>` verschieben
    (CEO 2026-09-29). Nachholend und idempotent: jede Mail genau einmal, protokolliert (`eingang_mail_abgelegt`).
    Verworfene Belege bleiben im Posteingang (kein erledigter Beleg)."""
    if google is None or not google.verfuegbar():
        return []
    eintraege = st.bh.eintraege()
    fertig, je_mail = _abgelegt(eintraege), {}
    for x in sorted(st._falte(eintraege).values(), key=lambda b: b["nummer"]):
        mid = x.get("mail_id")
        if mid and mid not in fertig and x.get("status") != "verworfen":
            je_mail.setdefault(mid, []).append(x)
    out = []
    for mid, belege in je_mail.items():
        ordner = mail_ordner(belege[0])
        if _ablegen(st, google, mid, ordner, [b["nummer"] for b in belege]):
            out.append({"mail_id": mid, "ordner": ordner})
    return out


def mail_eingang_pruefen(st: EingangStore, google, *, absender: list[str], backoffice=None, notify=None,
                         gesehen: set | None = None, tage: int = 30) -> list[str]:
    """Belege, die der CEO an LUNAs Adresse weiterleitet, automatisch aufnehmen -- **nur von den eigenen Absendern**
    (Schutz vor Phishing/Fremd-Anhaengen). Idempotent ueber die Mail-ID. Rueckgabe: neue ER-Nummern."""
    absender = [a.strip().lower() for a in absender if a and "@" in a]
    if not absender or google is None or not google.verfuegbar():
        return []
    q = f"in:anywhere -in:trash has:attachment newer_than:{tage}d from:({' OR '.join(absender)})"   # auch Spam (BF-37)
    r = google.mail_suchen(q, max_results=20)
    if not r.get("ok"):
        return []
    eintraege = st.bh.eintraege()
    bekannt = {x.get("mail_id") for x in st._falte(eintraege).values() if x.get("mail_id")} | _abgelegt(eintraege)
    gesehen = gesehen if gesehen is not None else set()
    neu = []
    for m in r.get("mails", []):
        mid = m.get("id", "")
        if not mid or mid in bekannt or mid in gesehen:
            continue
        gesehen.add(mid)
        if not any(a in str(m.get("von", "")).lower() for a in absender):              # zweite Pruefung des Absenders
            continue
        roh = google.mail_roh(mid)
        if not roh.get("ok"):
            gesehen.discard(mid)
            continue
        if not absender_echt(roh["roh"], absender):             # gefaelschter Absender -> nie uebernehmen
            continue
        vorher, doppelt = len(neu), []
        for name, daten in anhaenge(roh["roh"]):
            try:
                res = st.aufnehmen(daten, name, quelle="mail", mail_id=mid, von="LUNA-Mail")
            except ValueError:
                continue
            if res.get("doppelt"):
                doppelt.append(res["nummer"])
                continue
            neu.append(res["nummer"])
            llm_beauftragen(st, backoffice, res["nummer"])
        if len(neu) == vorher and doppelt:                  # nur schon bekannte Belege -> erledigt, ab nach „Doppelt“
            if not _ablegen(st, google, mid, _ordner("Doppelt", jetzt().year), doppelt):
                gesehen.discard(mid)
        elif len(neu) > vorher and not hasattr(google, "mail_ablegen") and hasattr(google, "mail_aus_spam"):
            try:                                            # ohne Ablage: Gmail lernt, eigene Beleg-Mails sind kein Spam
                google.mail_aus_spam(mid)
            except Exception:
                pass
    mails_ablegen(st, google)                               # neue + frueher nicht abgelegte Beleg-Mails (CEO 2026-09-29)
    if neu and notify:
        try:
            notify(f"📥 {len(neu)} Beleg(e) aus deiner Mail an LUNA übernommen: {', '.join(neu)} -- in LUNA-OS prüfen "
                   "und buchen.", abteilung="CFO", kategorie="finanzen", quelle="belege", detail="LUNA-OS -> Belege")
        except Exception:
            pass
    return neu
