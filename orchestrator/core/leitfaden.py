"""Gespraechsleitfaden am Kunden (KUNDEN_CHECKLISTE C1/C2, CEO 2026-10-26).

Der Fragenkatalog A-J (Unternehmen, Ziel, Zielgruppe, Ton, Marke, Formate, Personen, Dreh, Freigabe, Call to Action) ist
hier die **einzige Quelle**: fuer das leere Dokument (PDF/Word zum Mitnehmen, `scripts/kunden_checkliste_dokument.py` und
Download in LUNA-OS) und fuer den Leitfaden, den der CEO waehrend eines Telefonats/Meetings in LUNA-OS ausfuellt.

- Ein Leitfaden haengt am **Kunden** (Stammdaten-Firma), auch ohne Angebot/Auftrag; mehrere je Kunde moeglich.
- Jede Eingabe wird sofort gespeichert (Ereignisse in der Hash-Kette, nichts geht verloren):
  `leitfaden_angelegt`, `leitfaden_kopf` (Titel, Gespraechspartner, Datum, Notizen), `leitfaden_antwort` (je Frage:
  Text und/oder abgehakt).
- **Abschliessen** erzeugt ein PDF (Kopf wie die Konzept-Vorlage, Fragen mit Antworten) und legt es in der Firmenakte ab
  (Art `leitfaden`); jedes weitere Abschliessen ist eine neue Fassung (`leitfaden_abgeschlossen`).
- **Uebernahme ins Briefing** der Konzept-Mappe eines Vorgangs (AN-/AB- desselben Kunden): Vorschau zeigt alt/neu je
  Feld, geschrieben wird erst nach Bestaetigung (`leitfaden_uebernommen` + `konzept_briefing`).
"""
from __future__ import annotations

import re
import uuid
import zipfile
from html import escape
from io import BytesIO
from pathlib import Path

from .beleg_pdf import DEJAVU, datum_de
from .buchhaltung import jetzt

TITEL = "Kunden-Checkliste – Content-Konzept & Skripte"
TITEL_LEITFADEN = "Gesprächsleitfaden – Content-Konzept & Skripte"
EINLEITUNG = ("Diese Fragen klären wir mit euch, bevor wir Konzept und Skripte schreiben. Mit ★ markierte Blöcke brauchen "
              "wir auf jeden Fall – der Rest hilft, Content zu machen, der wirklich nach euch klingt.")
KOPFFELDER = ["Kunde", "Gesprächspartner", "Datum", "Projekt / Kampagne"]

# (Buchstabe, Titel, Pflicht, [(Frage-ID, Frage, Briefing-Feld oder "")])
BLOECKE = [
    ("A", "Unternehmen & Angebot", False, [
        ("A1", "Was macht ihr – in einem Satz?", ""),
        ("A2", "Welches Produkt oder Angebot steht im Mittelpunkt?", ""),
        ("A3", "Was unterscheidet euch von anderen (warum zu euch und nicht zur Konkurrenz)?", ""),
        ("A4", "Gibt es Aktionen, Termine oder Saisons, die wir treffen müssen?", "")]),
    ("B", "Ziel", True, [
        ("B1", "Was soll der Content erreichen (Bekanntheit, Besucher, Anfragen, Verkauf, Bewerber)?", "ziel"),
        ("B2", "Woran messen wir Erfolg (Reichweite, Klicks, Reservierungen, Anfragen)?", "ziel"),
        ("B3", "Gibt es ein konkretes Ziel bis zu einem bestimmten Datum?", "ziel")]),
    ("C", "Zielgruppe", True, [
        ("C1", "Wen wollt ihr erreichen (Alter, Ort, Interessen)?", "zielgruppe"),
        ("C2", "Wer sind heute eure besten Kunden?", "zielgruppe"),
        ("C3", "Was ist deren größtes Problem oder größter Wunsch?", "zielgruppe")]),
    ("D", "Kernbotschaft & Ton", True, [
        ("D1", "Was soll man nach dem Video über euch denken?", "botschaft"),
        ("D2", "Wie sprecht ihr eure Kunden an (du/Sie, locker/seriös, Humor ja/nein)?", "tonalitaet"),
        ("D3", "Gibt es Wörter oder Themen, die tabu sind?", "donts")]),
    ("E", "Marke & Pflichtangaben", False, [
        ("E1", "Logo, Farben, Schrift, Claim – was müssen wir verwenden?", "dos"),
        ("E2", "Pflichtangaben (z. B. Werbekennzeichnung, Preise, Allergene, Gewinnspielbedingungen)?", "pflicht"),
        ("E3", "Marken oder Partner, die genannt werden müssen – oder nicht genannt werden dürfen?", "pflicht")]),
    ("F", "Inhalte & Formate", False, [
        ("F1", "Auf welchen Plattformen (Instagram, Facebook, TikTok, LinkedIn)?", ""),
        ("F2", "Welche Formate (Reel, Story, Karussell, Foto)?", ""),
        ("F3", "Wie viele Postings, in welchem Zeitraum?", ""),
        ("F4", "Beispiele, die euch gefallen – und welche gar nicht?", "dos"),
        ("F5", "Gibt es vorhandenes Material (Fotos, Videos, Texte)?", "")]),
    ("G", "Personen & Rechte", False, [
        ("G1", "Wer darf oder soll vor die Kamera?", ""),
        ("G2", "Liegen Einwilligungen der Personen vor (sonst holen wir sie ein)?", ""),
        ("G3", "Sind Gäste oder Mitarbeitende im Hintergrund in Ordnung?", ""),
        ("G4", "Musik: eigene Rechte oder Musik der Plattform?", "")]),
    ("H", "Dreh & Organisation", False, [
        ("H1", "Drehorte und gute Zeiten (Öffnungszeiten, ruhige Phasen)?", ""),
        ("H2", "Ansprechpartner vor Ort (Name, Telefon)?", ""),
        ("H3", "Welche Produkte oder Requisiten müssen bereitstehen?", ""),
        ("H4", "Parken, Strom, Zugang – gibt es etwas zu beachten?", "")]),
    ("I", "Freigabe & Zusammenarbeit", True, [
        ("I1", "Wer gibt Skripte und Videos frei (Name, Kontakt)?", "freigabe_an"),
        ("I2", "Wie schnell kommt eine Freigabe (Frist)?", ""),
        ("I3", "Über welchen Kanal (Mail, WhatsApp, Link zum Kundenordner)?", ""),
        ("I4", "Wer postet – wir oder ihr? Auf welchem Konto?", "")]),
    ("J", "Call to Action", True, [
        ("J1", "Was soll der Zuschauer am Ende tun (folgen, reservieren, Link klicken, anrufen, vorbeikommen)?", "botschaft"),
        ("J2", "Gibt es einen Link, Rabattcode oder eine Aktion?", "botschaft")]),
]
FRAGEN = {fid: (b, text, ziel) for b, _, _, fs in BLOECKE for fid, text, ziel in fs}
MAX_ANTWORT, MAX_NOTIZEN = 2000, 6000
KOPF = (("titel", 120), ("gespraechspartner", 200), ("datum", 10), ("notizen", MAX_NOTIZEN))
_ID = re.compile(r"^LF-[0-9a-f]{8}$")


def _t(x, n: int) -> str:
    return str(x or "").strip()[:n]


class LeitfadenStore:
    def __init__(self, bh, kunden):
        self.bh, self.kunden = bh, kunden

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "leitfaden_angelegt":
                out[d["id"]] = {"id": d["id"], "firma": d["firma"], "titel": d.get("titel", ""), "gespraechspartner": "",
                                "datum": d.get("datum", ""), "notizen": "", "antworten": {}, "fassungen": [],
                                "uebernahmen": [], "angelegt": e["ts"], "geaendert": e["ts"], "von": e.get("von", "")}
            elif d.get("id") in out:
                lf = out[d["id"]]
                if t == "leitfaden_kopf":
                    lf.update(d.get("felder") or {})
                elif t == "leitfaden_antwort":
                    a = lf["antworten"].setdefault(d["frage"], {"text": "", "erledigt": False})
                    a.update({k: d[k] for k in ("text", "erledigt") if k in d})
                elif t == "leitfaden_abgeschlossen":
                    lf["fassungen"].append({"fassung": d["fassung"], "akte_id": d["akte_id"], "ts": e["ts"]})
                elif t == "leitfaden_uebernommen":
                    lf["uebernahmen"].append({"vorgang": d["vorgang"], "felder": d.get("felder", []), "ts": e["ts"]})
                lf["geaendert"] = e["ts"]
        return out

    def get(self, lid: str) -> dict | None:
        lf = self._falte(self.bh.eintraege()).get((lid or "").strip())
        return lf and lf | {"offen_pflicht": offene_pflicht(lf), "fortschritt": fortschritt(lf)}

    def liste(self, firma: str) -> list[dict]:
        alle = [lf for lf in self._falte(self.bh.eintraege()).values() if lf["firma"] == firma]
        return sorted(({k: lf[k] for k in ("id", "titel", "datum", "gespraechspartner", "geaendert", "fassungen")}
                       | {"fortschritt": fortschritt(lf), "offen_pflicht": offene_pflicht(lf)} for lf in alle),
                      key=lambda x: x["geaendert"], reverse=True)

    def _vorhanden(self, lid: str) -> dict:
        if not _ID.match(lid or ""):
            raise KeyError(lid)
        lf = self._falte(self.bh.eintraege()).get(lid)
        if not lf:
            raise KeyError(lid)
        return lf

    # -- Schreiben ---------------------------------------------------------------------------------------------------
    def anlegen(self, firma: str, *, titel: str = "", von: str = "") -> dict:
        f = self.kunden.firma(firma)
        if not f:
            raise KeyError(firma)
        lid = "LF-" + uuid.uuid4().hex[:8]
        self.bh.erfassen("leitfaden_angelegt", {"id": lid, "firma": f["nummer"], "titel": _t(titel, 120) or "Erstgespräch",
                                                "datum": jetzt().date().isoformat()}, von=von)
        return {"id": lid}

    def kopf(self, lid: str, felder: dict, *, von: str = "") -> dict:
        self._vorhanden(lid)
        neu = {k: _t(felder[k], n) for k, n in KOPF if k in (felder or {})}
        if "datum" in neu and neu["datum"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", neu["datum"]):
            raise ValueError("Datum bitte als JJJJ-MM-TT.")
        if not neu:
            raise ValueError("Nichts zu speichern.")
        self.bh.erfassen("leitfaden_kopf", {"id": lid, "felder": neu}, von=von)
        return {"id": lid}

    def antwort(self, lid: str, frage: str, *, text: str | None = None, erledigt: bool | None = None, von: str = "") -> dict:
        self._vorhanden(lid)
        if frage not in FRAGEN:
            raise ValueError("Unbekannte Frage.")
        d: dict = {"id": lid, "frage": frage}
        if text is not None:
            d["text"] = _t(text, MAX_ANTWORT)
        if erledigt is not None:
            d["erledigt"] = bool(erledigt)
        if len(d) == 2:
            raise ValueError("Nichts zu speichern.")
        self.bh.erfassen("leitfaden_antwort", d, von=von)
        return {"id": lid, "frage": frage}

    def abschliessen(self, lid: str, *, von: str = "") -> dict:
        """PDF erzeugen und als neue Fassung in der Firmenakte ablegen."""
        from .firmenakte import Firmenakte
        lf = self._vorhanden(lid)
        if not any((a.get("text") or a.get("erledigt")) for a in lf["antworten"].values()) and not lf.get("notizen"):
            raise ValueError("Der Leitfaden ist noch leer.")
        f = self.kunden.firma(lf["firma"]) or {}
        fassung = len(lf["fassungen"]) + 1
        pdf = dokument_pdf(lf, firma_name=f.get("name", ""), logo=self.bh.dir / "logo.jpg")
        titel = f"Gesprächsleitfaden {lf['titel']}" + (f" (Fassung {fassung})" if fassung > 1 else "")
        name = f"Gespraechsleitfaden_{lf['firma']}_{lid}_F{fassung}.pdf"
        offen = offene_pflicht(lf)
        akte = Firmenakte(self.bh, self.kunden).hochladen(
            lf["firma"], pdf, name, titel=titel, art="leitfaden", datum=lf.get("datum") or "",
            notiz=(f"Gespräch mit {lf['gespraechspartner']}. " if lf.get("gespraechspartner") else "")
            + (f"Pflichtblöcke offen: {', '.join(offen)}." if offen else "Alle Pflichtblöcke beantwortet."), von=von)
        self.bh.erfassen("leitfaden_abgeschlossen", {"id": lid, "fassung": fassung, "akte_id": akte["id"]}, von=von)
        return {"id": lid, "fassung": fassung, "akte_id": akte["id"], "offen_pflicht": offen}

    # -- Uebernahme ins Briefing -------------------------------------------------------------------------------------
    def vorgaenge(self, firma: str) -> list[dict]:
        """Angebote und Auftraege des Kunden (Ziel fuer die Uebernahme ins Briefing), neueste zuerst."""
        from .angebote import AngebotStore
        from .beauftragung import AuftragBuch
        e = self.bh.eintraege()
        out = [{"nummer": a["nummer"], "titel": a.get("titel", ""), "art": "Angebot", "status": a.get("status", "")}
               for a in AngebotStore._falte(e).values() if a.get("firma") == firma]
        out += [{"nummer": a["nummer"], "titel": a.get("titel", ""), "art": "Auftrag", "status": a.get("status", "")}
                for a in AuftragBuch._falte(e).values() if a.get("firma") == firma]
        return sorted(out, key=lambda x: x["nummer"].split("-", 1)[1], reverse=True)

    def briefing_werte(self, lf: dict) -> dict[str, str]:
        """Antworten je Briefing-Feld (mehrere Fragen -> Zeilen), nur nicht leere."""
        out: dict[str, list[str]] = {}
        for fid, (_, frage, ziel) in FRAGEN.items():
            text = ((lf["antworten"].get(fid) or {}).get("text") or "").strip()
            if ziel and text:
                out.setdefault(ziel, []).append(text)
        if lf.get("notizen"):
            out.setdefault("notizen", []).append(f"Aus dem Gesprächsleitfaden ({datum_de(lf.get('datum') or '')}): "
                                                 + lf["notizen"].strip())
        return {k: "\n".join(v) for k, v in out.items()}

    def uebernahme_vorschau(self, lid: str, vorgang: str, konzept) -> dict:
        lf = self._vorhanden(lid)
        kontext = konzept.kontext(vorgang)
        if kontext["firma"] != lf["firma"]:
            raise ValueError("Der Vorgang gehört zu einem anderen Kunden.")
        alt = konzept.mappe(kontext["vorgang"])["briefing"]
        from .konzept import BRIEFING
        laengen = {k: n for k, _, n in BRIEFING}
        neu = {k: v[:laengen[k]] for k, v in self.briefing_werte(lf).items() if k in laengen}
        return {"vorgang": kontext["vorgang"], "felder": [{"feld": k, "label": lbl, "alt": alt.get(k, ""), "neu": neu[k]}
                                                          for k, lbl, _ in BRIEFING if k in neu and neu[k] != alt.get(k, "")]}

    def uebernehmen(self, lid: str, vorgang: str, konzept, *, felder: list[str] | None = None, von: str = "") -> dict:
        v = self.uebernahme_vorschau(lid, vorgang, konzept)
        werte = {x["feld"]: x["neu"] for x in v["felder"] if felder is None or x["feld"] in felder}
        if not werte:
            raise ValueError("Keine Änderungen zu übernehmen.")
        konzept.briefing(v["vorgang"], werte, von=von)
        self.bh.erfassen("leitfaden_uebernommen", {"id": lid, "vorgang": v["vorgang"], "felder": sorted(werte)}, von=von)
        return {"vorgang": v["vorgang"], "felder": sorted(werte)}


def offene_pflicht(lf: dict) -> list[str]:
    """Pflichtbloecke ohne eine einzige Antwort (Text)."""
    return [f"{b} {titel}" for b, titel, pflicht, fs in BLOECKE
            if pflicht and not any(((lf["antworten"].get(fid) or {}).get("text") or "").strip() for fid, _, _ in fs)]


def fortschritt(lf: dict) -> dict:
    fertig = sum(1 for _, _, _, fs in BLOECKE
                 if any(((lf["antworten"].get(fid) or {}).get("text") or "").strip() or (lf["antworten"].get(fid) or {}).get("erledigt")
                        for fid, _, _ in fs))
    return {"bloecke": len(BLOECKE), "fertig": fertig}


# -- Dokumente (leer: Checkliste zum Mitnehmen; ausgefuellt: Leitfaden-PDF fuer die Firmenakte) -------------------------
BLAU, ROT, GRAU = (0, 64, 135), (204, 0, 0), (110, 110, 110)
LOGO_B = 50.0
LOGO_H = LOGO_B * 221 / 560


def dokument_pdf(lf: dict | None = None, *, firma_name: str = "", logo: Path | None = None, schrift: Path = DEJAVU) -> bytes:
    """A4 hochkant, nur Kopf (Logo + blau-roter Balken). Ohne `lf`: leere Checkliste mit Antwortzeilen."""
    from fpdf import FPDF

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("DejaVu", size=7)
            self.set_text_color(*GRAU)
            self.cell(0, 4, f"Seite {self.page_no()}/{{nb}}", align="R")

    p = _Pdf(format="A4", orientation="P")
    p.add_font("DejaVu", "", str(schrift / "DejaVuSans.ttf"))
    p.add_font("DejaVu", "B", str(schrift / "DejaVuSans-Bold.ttf"))
    p.set_title(TITEL_LEITFADEN if lf else TITEL)
    p.set_creator("LUNA-OS")
    p.set_margins(18, 14, 18)
    p.set_auto_page_break(True, margin=18)
    p.alias_nb_pages()
    p.add_page()
    B = p.w - 36
    y = 14
    if logo and Path(logo).exists():
        p.image(str(logo), x=(p.w - LOGO_B) / 2, y=14, w=LOGO_B)
        y += LOGO_H + 3
    p.set_fill_color(*BLAU); p.rect(18, y, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT); p.rect(18 + B / 2, y, B / 2, 1.6, style="F")
    p.set_y(y + 7)
    p.set_font("DejaVu", "B", 15); p.set_text_color(0, 0, 0)
    p.multi_cell(0, 7, TITEL_LEITFADEN if lf else TITEL)
    p.ln(1)

    def zeilen(n: int):
        p.set_draw_color(200, 200, 200)
        for _ in range(n):
            yy = p.get_y() + 6.5
            p.line(24, yy, 18 + B, yy)
            p.set_y(yy)

    if lf:
        werte = [firma_name or lf["firma"], lf.get("gespraechspartner") or "–", datum_de(lf.get("datum") or ""),
                 lf.get("titel") or "–"]
        offen = offene_pflicht(lf)
        p.set_font("DejaVu", size=9)
        for feld, wert in zip(KOPFFELDER, werte):
            p.set_text_color(*GRAU); p.cell(38, 5, feld)
            p.set_text_color(0, 0, 0); p.multi_cell(0, 5, str(wert), new_x="LMARGIN", new_y="NEXT")
        if offen:
            p.ln(1); p.set_text_color(*ROT)
            p.multi_cell(0, 5, "Noch offene Pflichtblöcke: " + ", ".join(offen), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(0, 0, 0)
    else:
        p.set_font("DejaVu", size=9); p.set_text_color(*GRAU)
        p.multi_cell(0, 4.6, EINLEITUNG)
        p.ln(3)
        for i in range(0, len(KOPFFELDER), 2):
            yz = p.get_y()
            for j, feld in enumerate(KOPFFELDER[i:i + 2]):
                x = 18 + j * (B / 2 + 2)
                p.set_xy(x, yz); p.set_font("DejaVu", size=8); p.set_text_color(*GRAU)
                p.cell(B / 2 - 2, 4, feld)
                p.set_draw_color(160, 160, 160)
                p.line(x, yz + 11, x + B / 2 - 4, yz + 11)
            p.set_y(yz + 14)
    p.ln(2)

    for buchstabe, titel, pflicht, fragen in BLOECKE:
        if p.get_y() > p.h - 60:
            p.add_page()
        p.ln(3)
        p.set_fill_color(*BLAU); p.rect(18, p.get_y() + 0.8, 1.4, 5.2, style="F")
        p.set_x(22)
        p.set_font("DejaVu", "B", 11); p.set_text_color(*BLAU)
        p.cell(0, 7, f"{buchstabe}. {titel}" + ("   ★ Pflicht" if pflicht else ""), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(0, 0, 0)
        for fid, frage, _ in fragen:
            if p.get_y() > p.h - 36:
                p.add_page()
            a = (lf or {}).get("antworten", {}).get(fid) or {}
            p.set_font("DejaVu", size=9.5)
            yq = p.get_y() + 1.5
            p.set_draw_color(*BLAU)
            p.rect(18.5, yq + 0.6, 3.2, 3.2)
            if a.get("erledigt") or (a.get("text") or "").strip():
                p.set_font("DejaVu", "B", 8); p.set_text_color(*BLAU)
                p.text(19.0, yq + 3.3, "✓")
                p.set_font("DejaVu", size=9.5); p.set_text_color(0, 0, 0)
            p.set_xy(24, yq)
            p.multi_cell(B - 6, 4.6, frage)
            if lf is None:
                zeilen(2)
            else:
                text = (a.get("text") or "").strip()
                p.set_x(24); p.set_font("DejaVu", size=9.5)
                p.set_text_color(*(BLAU if text else GRAU))
                p.multi_cell(B - 6, 4.8, text or "–")
                p.set_text_color(0, 0, 0)
            p.ln(1)

    p.ln(4)
    if p.get_y() > p.h - 40:
        p.add_page()
    p.set_font("DejaVu", "B", 11); p.set_text_color(*BLAU)
    p.cell(0, 7, "Notizen", new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    if lf is None:
        zeilen(5)
    else:
        p.set_font("DejaVu", size=9.5)
        p.multi_cell(0, 4.8, (lf.get("notizen") or "").strip() or "–")
    return bytes(p.output())


def dokument_docx(logo: Path | None = None) -> bytes:
    """Leere Checkliste als Word-Datei (ohne Zusatzbibliothek, gleicher Aufbau wie die Konzept-Vorlage)."""
    TW = lambda mm: round(mm * 56.6929)
    EMU = lambda mm: round(mm * 36000)
    breite = TW(210 - 36)
    halb = breite // 2
    mit_logo = bool(logo and Path(logo).exists())
    ct = ("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="jpg" ContentType="image/jpeg"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>""")
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{escape(TITEL)}</dc:title></cp:coreProperties>"""
    docrels = ("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>"""
               + ('\n<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.jpg"/>' if mit_logo else "")
               + "\n</Relationships>")
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="de-DE"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="60" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Standard"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="berschrift1"><w:name w:val="heading 1"/><w:basedOn w:val="Standard"/><w:next w:val="Standard"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="berschrift2"><w:name w:val="heading 2"/><w:basedOn w:val="Standard"/><w:next w:val="Standard"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="60"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="004087"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="NormaleTabelle"><w:name w:val="Normal Table"/><w:tblPr><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""
    cx, cy = EMU(LOGO_B), EMU(LOGO_H)

    def zelle(w, farbe):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="{farbe}"/></w:tcPr>'
                '<w:p><w:pPr><w:spacing w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p></w:tc>')

    def absatz(text, *, stil="", grau=False, keep=False):
        ppr = (f'<w:pStyle w:val="{stil}"/>' if stil else "") + ("<w:keepNext/>" if keep else "")
        rpr = '<w:color w:val="6E6E6E"/><w:sz w:val="18"/>' if grau else ""
        return f'<w:p><w:pPr>{ppr}</w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    def linie(einzug_mm=6.0):
        return (f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="C8C8C8"/></w:pBdr>'
                f'<w:spacing w:before="160" w:after="0"/><w:ind w:left="{TW(einzug_mm)}"/></w:pPr></w:p>')

    bild = (f"""<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="{TW(3)}"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="Logo"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="1" name="logo.jpg"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>""" if mit_logo else "")
    teile = [bild + f"""<w:tbl><w:tblPr><w:tblW w:w="{breite}" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders></w:tblPr>
<w:tblGrid><w:gridCol w:w="{halb}"/><w:gridCol w:w="{breite - halb}"/></w:tblGrid>
<w:tr><w:trPr><w:trHeight w:val="{TW(1.6)}" w:hRule="exact"/></w:trPr>{zelle(halb, "004087")}{zelle(breite - halb, "CC0000")}</w:tr></w:tbl>""",
             absatz(TITEL, stil="berschrift1"), absatz(EINLEITUNG, grau=True)]
    for feld in KOPFFELDER:
        teile += [absatz(feld, grau=True, keep=True), linie(0)]
    for buchstabe, titel, pflicht, fragen in BLOECKE:
        teile.append(absatz(f"{buchstabe}. {titel}" + ("   ★ Pflicht" if pflicht else ""), stil="berschrift2"))
        for _, frage, _ in fragen:
            teile += [absatz(f"☐  {frage}", keep=True), linie(), linie()]
    teile.append(absatz("Notizen", stil="berschrift2"))
    teile += [linie(0) for _ in range(5)]
    doc = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>
{"".join(teile)}
<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="{TW(14)}" w:right="{TW(18)}" w:bottom="{TW(18)}" w:left="{TW(18)}" w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>
</w:body></w:document>"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", docrels)
        z.writestr("word/styles.xml", styles)
        if mit_logo:
            z.write(logo, "word/media/logo.jpg")
    return buf.getvalue()
