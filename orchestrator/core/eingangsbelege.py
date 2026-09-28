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
    "buero": ("Bürobedarf / Porto", ("büro", "buero", "papier", "porto", "briefmarke", "paketmarke", "deutsche post")),
    "reise": ("Reisekosten", ("bahn", "db fernverkehr", "hotel", "flug", "übernachtung", "ticket", "reise")),
    "fahrzeug": ("Fahrzeugkosten", ("tank", "kraftstoff", "benzin", "diesel", "parken", "werkstatt", "kfz")),
    "bewirtung": ("Bewirtung (70 % absetzbar)", ("restaurant", "bewirtung", "gastronomie", "café", "cafe")),
    "fortbildung": ("Fortbildung / Fachliteratur", ("seminar", "kurs", "fortbildung", "buch", "schulung", "konferenz")),
    "gwg": ("Geringwertiges Wirtschaftsgut (bis 800 € netto)", ("kamera", "mikrofon", "objektiv", "stativ", "monitor", "tastatur", "cage", "gimbal", "akku", "speicherkarte", "smallrig", "rode", "sony alpha")),
    "anlage": ("Anlagegut > 800 € (Abschreibung)", ("laptop", "macbook", "computer", "pc ", "iphone", "server", "nas")),
    "gebuehren": ("Gebühren, Beiträge, Versicherungen", ("gebühr", "gebuehr", "beitrag", "versicherung", "ihk", "kontoführung")),
    "sonstiges": ("Sonstiges", ()),
}
STATUS = ("zu_pruefen", "gebucht", "verworfen")
GWG_GRENZE_CENT = 80000        # 800 €; beim Kleinunternehmer zaehlt der Bruttobetrag (kein Vorsteuerabzug)


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
                "leistung": _text(root, "InvoiceLine", "Item", "Name")}
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
                "leistung": _text(tx, "IncludedSupplyChainTradeLineItem", "SpecifiedTradeProduct", "Name") if tx is not None else ""}
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


def vorschlag_regeln(text: str, e_rechnung: dict | None = None) -> dict:
    """Schneller Vorschlag ohne KI. E-Rechnungs-Felder haben Vorrang (exakt)."""
    t = text or ""
    v = {"lieferant": "", "rechnungsnummer": "", "rechnungsdatum": "", "betrag": "", "faellig_am": "", "leistung": "",
         "kategorie": kategorie_raten(t), "quelle": "regeln"}
    zeilen = [z.strip() for z in t.splitlines() if z.strip()]
    m = re.search(r"(?i)(?:rechnungs?[- ]?(?:nummer|nr\.?)|rechnung\s+nr\.?|invoice\s+(?:no\.?|number)|beleg[- ]?(?:nummer|nr\.?))"
                  r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_.]{2,30})", t)
    if m:
        v["rechnungsnummer"] = m.group(1).rstrip(".")
    m = (re.search(r"(?i)(?:rechnungsdatum|invoice\s+date|belegdatum|leistungsdatum)\s*[:]?\s*" + _DATUM, t)
         or re.search(r"(?i)(?<![a-zäöü])datum\s*[:]?\s*" + _DATUM, t) or re.search(_DATUM, t))
    if m:
        v["rechnungsdatum"] = _iso(t, *m.groups()[-3:])
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
    if zeilen:
        v["lieferant"] = re.split(r"\s+[·|•]\s+", zeilen[0])[0][:120]      # Absenderzeile "Firma · Strasse · Ort"
    if e_rechnung:
        v.update({k: e_rechnung[k] for k in ("lieferant", "rechnungsnummer", "rechnungsdatum", "betrag", "faellig_am", "leistung")
                  if e_rechnung.get(k)})
        v["quelle"] = "e-rechnung"
    return v


LLM_SYSTEM = (
    "Du liest den Text einer Eingangsrechnung und antwortest NUR mit einem JSON-Objekt, ohne Erklaerung, mit genau diesen "
    'Feldern: {"lieferant": "", "rechnungsnummer": "", "rechnungsdatum": "JJJJ-MM-TT", "betrag": "123,45", '
    '"faellig_am": "JJJJ-MM-TT", "leistung": "kurz, was gekauft wurde", "kategorie": ""}. '
    "betrag = Endbetrag, den wir zahlen muessen (brutto, deutsches Format). kategorie ist genau einer von: "
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
    k = str(roh.get("kategorie") or "").strip().lower()
    v["kategorie"] = k if k in KATEGORIEN else ""
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
                        "bezahlt_cent": x.get("bezahlt_cent", 0), "faellig_am": f.get("faellig_am", ""),
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
        k = str(felder.get("kategorie") or "").strip()
        if k not in KATEGORIEN:
            raise ValueError("Bitte eine Kategorie waehlen.")
        f["kategorie"] = k
        if k == "gwg" and abs(f["betrag_cent"]) > GWG_GRENZE_CENT:
            raise ValueError("Ueber 800 € ist es kein geringwertiges Wirtschaftsgut -- bitte als Anlagegut buchen "
                             "(Abschreibung ueber die Nutzungsdauer).")
        if k == "anlage":
            try:
                f["nutzungsdauer_jahre"] = int(felder.get("nutzungsdauer_jahre") or 0)
            except (TypeError, ValueError):
                f["nutzungsdauer_jahre"] = 0
            if not 1 <= f["nutzungsdauer_jahre"] <= 50:
                raise ValueError("Nutzungsdauer in Jahren angeben (Computer/Software: 1, Foto/Video-Technik: 7).")
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


def mail_eingang_pruefen(st: EingangStore, google, *, absender: list[str], backoffice=None, notify=None,
                         gesehen: set | None = None, tage: int = 30) -> list[str]:
    """Belege, die der CEO an LUNAs Adresse weiterleitet, automatisch aufnehmen -- **nur von den eigenen Absendern**
    (Schutz vor Phishing/Fremd-Anhaengen). Idempotent ueber die Mail-ID. Rueckgabe: neue ER-Nummern."""
    absender = [a.strip().lower() for a in absender if a and "@" in a]
    if not absender or google is None or not google.verfuegbar():
        return []
    q = f"has:attachment newer_than:{tage}d from:({' OR '.join(absender)})"
    r = google.mail_suchen(q, max_results=20)
    if not r.get("ok"):
        return []
    bekannt = {x.get("mail_id") for x in st._falte(st.bh.eintraege()).values() if x.get("mail_id")}
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
        for name, daten in anhaenge(roh["roh"]):
            try:
                res = st.aufnehmen(daten, name, quelle="mail", mail_id=mid, von="LUNA-Mail")
            except ValueError:
                continue
            if res.get("doppelt"):
                continue
            neu.append(res["nummer"])
            llm_beauftragen(st, backoffice, res["nummer"])
    if neu and notify:
        try:
            notify(f"📥 {len(neu)} Beleg(e) aus deiner Mail an LUNA übernommen: {', '.join(neu)} -- in LUNA-OS prüfen "
                   "und buchen.", abteilung="CFO", kategorie="finanzen", quelle="belege", detail="LUNA-OS -> Belege")
        except Exception:
            pass
    return neu
