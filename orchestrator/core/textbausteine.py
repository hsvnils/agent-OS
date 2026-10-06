"""Textbausteine und Signatur fuer den Belegversand (TEXTBAUSTEINE_MAILVERSAND T1, CEO 2026-10-05).

Je Belegart mehrere Vorlagen (Name, Betreff, Text mit Platzhaltern), eine davon Standard; dazu **eine** Signatur, die
unter jeden Text gesetzt wird. Der Mailtext entsteht erst beim Versand aus der aktuellen Vorlage -- Aenderungen gelten fuer
jede Mail ab dann; versendete Mails bleiben unveraendert in der Firmenakte. Die Standardvorlagen ergeben **ohne Signatur
genau die bisherigen Texte** (frueherer Gruss „Mit freundlichen Gruessen …“ bzw. „Viele Gruesse …“); ist eine Signatur
hinterlegt, ersetzt sie diesen Gruss.

Ablage nur auf der NAS (`buchhaltung/textbausteine.json`, wie Firmendaten -- die Signatur enthaelt eine Telefonnummer),
jede Aenderung als Ereignis `textbausteine_geaendert` in der Buchhaltungs-Kette (welche Belegarten, ob Signatur -- ohne
Texte).
"""
from __future__ import annotations

import copy
import json
import os
import re
import uuid

ARTEN = {"angebot": "Angebot", "auftrag": "Auftragsbestätigung", "rechnung": "Rechnung", "storno": "Stornorechnung",
         "mahnung": "Mahnung", "bericht": "Projektbericht", "konzept": "Konzept",
         "vorstellung": "Vorstellung", "vorstellung_nachfassen": "Vorstellung – Nachfassen"}   # SERIEN_UND_VORSTELLUNG V1/V2

_GEMEINSAM = {"anrede": "„Guten Tag Vorname Nachname,“ bzw. „Sehr geehrte Damen und Herren,“",
              "anrede_moin": "„Moin Vorname Nachname,“ bzw. „Moin,“", "vorname": "Vorname des Ansprechpartners",
              "nachname": "Nachname des Ansprechpartners", "kunde": "Firmenname des Kunden", "nummer": "Belegnummer",
              "titel": "Titel/Kampagne (kann leer sein)", "titel_zusatz": "„ – Titel“ (leer ohne Titel)"}
PLATZHALTER: dict[str, dict[str, str]] = {
    "angebot": _GEMEINSAM | {"zu_titel": "„ zu „Titel““ (leer ohne Titel)", "betrag": "Angebotssumme",
                             "gueltig_bis": "Gültig bis (Datum)", "praesentation": "Canva-Link-Zeile (leer, wenn keine)"},
    "auftrag": _GEMEINSAM | {"betrag": "Auftragssumme", "zu_angebot": "„zu unserem Angebot AN-…“ (leer ohne Angebot)",
                             "angebot": "Angebotsnummer"},
    "rechnung": _GEMEINSAM | {"betrag": "Rechnungsbetrag", "faellig": "Zahlbar bis (Datum)",
                              "rechnungsart": "Rechnung / Vorkasse-Rechnung / Schlussrechnung"},
    "storno": _GEMEINSAM | {"bezug": "Nummer der stornierten Rechnung", "betrag": "Betrag"},
    "mahnung": _GEMEINSAM | {"rechnung": "Rechnungsnummer", "faellig": "ursprüngliche Fälligkeit",
                             "stufe": "„1. Mahnung“ / „2. Mahnung“ / „3. Mahnung“",
                             "mahnung_im_text": "„1. Mahnung“, „2. Mahnung“ bzw. „letzte Mahnung“", "betrag": "Gesamtbetrag",
                             "frist": "Zahlungsfrist (Datum)"},
    "bericht": _GEMEINSAM | {"titel_quote": "„ „Titel““ (leer ohne Titel)", "version_zusatz": "„ (Version 2)“ ab der 2. Fassung"},
    "vorstellung": {k: v for k, v in _GEMEINSAM.items() if k not in ("nummer", "titel", "titel_zusatz")}
                   | {"praesentation": "Präsentations-Zeile mit Canva-Link (aus dem Katalog)"},
    "vorstellung_nachfassen": {k: v for k, v in _GEMEINSAM.items() if k not in ("nummer", "titel", "titel_zusatz")}
                              | {"praesentation": "Präsentations-Zeile mit Canva-Link (aus dem Katalog)",
                                 "gesendet_am": "Datum der ersten Mail"},
    "konzept": _GEMEINSAM | {"zu_titel": "„ zu „Titel““ (leer ohne Titel)", "titel_oder_vorgang": "Titel, sonst Vorgangsnummer",
                             "version_zusatz": "„ (Version 2)“ ab der 2. Fassung"},
}
# frueherer fester Gruss (gilt, solange keine Signatur hinterlegt ist)
GRUSS = {"bericht": "Viele Grüße", "konzept": "Viele Grüße"}

STANDARD: dict[str, dict] = {
    "angebot": {"betreff": "Angebot {nummer}{titel_zusatz}",
                "text": "{anrede}\n\nanbei erhalten Sie unser Angebot {nummer}{zu_titel} über {betrag}. Es ist gültig bis "
                        "{gueltig_bis}.\n\n{praesentation}\n\nBei Fragen melden Sie sich gerne."},
    "auftrag": {"betreff": "Auftragsbestätigung {nummer}{titel_zusatz}",
                "text": "{anrede}\n\nvielen Dank für Ihren Auftrag. Anbei erhalten Sie unsere Auftragsbestätigung {nummer} "
                        "{zu_angebot} über {betrag}.\n\nBei Fragen melden Sie sich gerne."},
    "rechnung": {"betreff": "{rechnungsart} {nummer}{titel_zusatz}",
                 "text": "{anrede}\n\nanbei erhalten Sie unsere {rechnungsart} {nummer} über {betrag}, zahlbar bis "
                         "{faellig}.\n\nBei Fragen melden Sie sich gerne."},
    "storno": {"betreff": "Stornorechnung {nummer} zu {bezug}",
               "text": "{anrede}\n\nanbei erhalten Sie die Stornorechnung {nummer} zur Rechnung {bezug}.\n\n"
                       "Bei Fragen melden Sie sich gerne."},
    "mahnung": {"betreff": "{stufe} zu Rechnung {rechnung}",
                "text": "{anrede}\n\nunsere Rechnung {rechnung} war am {faellig} fällig und ist noch offen. Anbei erhalten "
                        "Sie unsere {mahnung_im_text} ({nummer}). Bitte überweisen Sie den Gesamtbetrag von {betrag} bis "
                        "zum {frist}.\n\nSollte sich Ihre Zahlung mit dieser Nachricht überschnitten haben, betrachten "
                        "Sie sie bitte als gegenstandslos."},
    "bericht": {"betreff": "Projektbericht {nummer}{titel_zusatz}{version_zusatz}",
                "text": "{anrede_moin}\n\nanbei unser Projektbericht zur Kampagne{titel_quote} mit den erreichten Zahlen "
                        "je Posting.\n\nBei Fragen melden Sie sich gern."},
    "vorstellung": {"betreff": "Hanserautisch × {kunde} – kurze Vorstellung",
                    "text": "{anrede_moin}\n\nich möchte Ihnen Hanserautisch kurz vorstellen: Wir machen Content rund um den HSV "
                            "und Hamburg für unsere Community auf Social Media.\n\nIch könnte mir gut vorstellen, dass {kunde} "
                            "und unsere Community zusammenpassen – gerne zeige ich Ihnen, wie eine Zusammenarbeit aussehen "
                            "kann.\n\n{praesentation}\n\nHätten Sie Lust auf ein kurzes Gespräch?"},
    "vorstellung_nachfassen": {"betreff": "Kurze Nachfrage – Hanserautisch × {kunde}",
                               "text": "{anrede_moin}\n\nich wollte kurz nachhaken, ob Sie meine Nachricht vom {gesendet_am} "
                                       "gesehen haben. Gerne erzähle ich Ihnen in einem kurzen Gespräch mehr.\n\n{praesentation}"},
    "konzept": {"betreff": "Konzept zur Freigabe – {titel_oder_vorgang}{version_zusatz}",
                "text": "{anrede_moin}\n\nanbei unser Konzept{zu_titel} mit Briefing, Ideen und Skripten. Bitte schauen Sie "
                        "es sich an und geben Sie uns kurz Ihre Freigabe oder Ihre Änderungswünsche."},
}
_PH = re.compile(r"\{([^{}]*)\}")
MAX_VORLAGEN, MAX_TEXT, MAX_SIGNATUR = 10, 4000, 1500


def anrede_werte(ap: dict | None) -> dict:
    vn, nn = ((ap or {}).get("vorname") or "").strip(), ((ap or {}).get("nachname") or "").strip()
    name = " ".join(x for x in (vn, nn) if x)
    return {"vorname": vn, "nachname": nn, "anrede": f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,",
            "anrede_moin": f"Moin {name}," if name else "Moin,"}


def _pruefe_text(art: str, text: str, feld: str) -> str:
    erlaubt = set(PLATZHALTER[art])
    fremd = sorted({p for p in _PH.findall(text) if p not in erlaubt})
    if fremd:
        raise ValueError(f"{ARTEN[art]}, {feld}: unbekannte Platzhalter {', '.join('{' + p + '}' for p in fremd)}.")
    if text.count("{") != text.count("}"):
        raise ValueError(f"{ARTEN[art]}, {feld}: geschweifte Klammern nur für Platzhalter.")
    return text


def _fuellen(vorlage: str, werte: dict) -> str:
    return _PH.sub(lambda m: str(werte.get(m.group(1), "")), vorlage)


def rendern(art: str, werte: dict, firmendaten: dict, *, vorlage: dict | None = None, signatur: str = "") -> tuple[str, str]:
    """-> (betreff, text). Ohne Vorlage gilt der Standard; ohne Signatur der fruehere Gruss mit Inhaber/Firma."""
    v = vorlage or STANDARD[art]
    betreff = re.sub(r"[ \t]{2,}", " ", _fuellen(v["betreff"], werte)).strip()
    text = _fuellen(v["text"], werte)
    text = re.sub(r"[ \t]{2,}", " ", text)                       # leere Platzhalter mitten im Satz
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    gruss = (signatur or "").strip() or (GRUSS.get(art, "Mit freundlichen Grüßen") + "\n" + "\n".join(
        x for x in ((firmendaten or {}).get("inhaber"), (firmendaten or {}).get("firma")) if x))
    return betreff, f"{text}\n\n{gruss}"


class TextbausteinStore:
    def __init__(self, bh):
        self.bh = bh
        self.pfad = bh.dir / "textbausteine.json"

    @staticmethod
    def _standard() -> dict:
        return {"signatur": "", "vorlagen": {a: [{"id": "standard", "name": "Standard", "standard": True,
                                                  **copy.deepcopy(STANDARD[a])}] for a in ARTEN}}

    def laden(self) -> dict:
        try:
            roh = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return self._standard()
        out = self._standard()
        out["signatur"] = str(roh.get("signatur") or "")
        for a in ARTEN:
            if (roh.get("vorlagen") or {}).get(a):
                out["vorlagen"][a] = roh["vorlagen"][a]
        return out

    def vorlage(self, art: str, vid: str = "") -> dict:
        liste = self.laden()["vorlagen"][art]
        return next((v for v in liste if vid and v["id"] == vid), None) or next(v for v in liste if v.get("standard"))

    def auswahl(self, art: str) -> list[dict]:
        return [{"id": v["id"], "name": v["name"], "standard": bool(v.get("standard"))} for v in self.laden()["vorlagen"][art]]

    @staticmethod
    def pruefe(neu: dict) -> dict:
        if not isinstance(neu, dict):
            raise ValueError("Ungueltige Eingabe.")
        sig = str(neu.get("signatur") or "").replace("\r\n", "\n").strip()
        if len(sig) > MAX_SIGNATUR:
            raise ValueError(f"Signatur: höchstens {MAX_SIGNATUR} Zeichen.")
        vorlagen = {}
        for a in ARTEN:
            liste = (neu.get("vorlagen") or {}).get(a) or []
            if not liste:
                vorlagen[a] = TextbausteinStore._standard()["vorlagen"][a]
                continue
            if len(liste) > MAX_VORLAGEN:
                raise ValueError(f"{ARTEN[a]}: höchstens {MAX_VORLAGEN} Vorlagen.")
            aus, ids = [], set()
            for v in liste:
                name = str(v.get("name") or "").strip()[:80]
                betreff = str(v.get("betreff") or "").strip()[:300]
                text = str(v.get("text") or "").replace("\r\n", "\n").strip()[:MAX_TEXT]
                if not name or not betreff or not text:
                    raise ValueError(f"{ARTEN[a]}: Name, Betreff und Text sind Pflicht.")
                vid = re.sub(r"[^a-z0-9-]", "", str(v.get("id") or "").lower())[:20] or uuid.uuid4().hex[:8]
                if vid in ids:
                    vid = uuid.uuid4().hex[:8]
                ids.add(vid)
                aus.append({"id": vid, "name": name, "betreff": _pruefe_text(a, betreff, "Betreff"),
                            "text": _pruefe_text(a, text, "Text"), "standard": bool(v.get("standard"))})
            if sum(v["standard"] for v in aus) != 1:                 # genau eine Standardvorlage
                for i, v in enumerate(aus):
                    v["standard"] = i == next((j for j, x in enumerate(aus) if x["standard"]), 0)
            vorlagen[a] = aus
        return {"signatur": sig, "vorlagen": vorlagen}

    def speichern(self, neu: dict, *, von: str = "") -> dict:
        alt = self.laden()
        k = self.pruefe(neu)
        arten = [a for a in ARTEN if k["vorlagen"][a] != alt["vorlagen"][a]]
        sig = k["signatur"] != alt["signatur"]
        if not arten and not sig and self.pfad.exists():
            return {"geaendert": False}
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.pfad)
        self.bh.erfassen("textbausteine_geaendert", {"arten": arten, "signatur": sig}, von=von)
        return {"geaendert": True, "arten": arten, "signatur": sig}


def eml(an: str, betreff: str, text: str, anhang: tuple[str, bytes]) -> bytes:
    """Mail-Entwurf fuer das eigene Mail-Programm (TEXTBAUSTEINE T3): Kennung „ungesendet“ (X-Unsent), damit Outlook die
    Datei als neue Mail zum Bearbeiten oeffnet; Absender setzt das Mail-Programm selbst. PDF als Anhang."""
    from email.message import EmailMessage
    from email.utils import formatdate
    m = EmailMessage()
    if an:
        m["To"] = an
    m["Subject"] = betreff
    m["Date"] = formatdate(localtime=True)
    m["X-Unsent"] = "1"
    m.set_content(text, charset="utf-8")
    m.add_attachment(anhang[1], maintype="application", subtype="pdf", filename=anhang[0])
    return m.as_bytes()
