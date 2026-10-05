"""CLO-Pruef-Lauf der Vertragsvorlagen (CLO_AUSBAU C4, CEO-Go 2026-10-05).

Der CLO (Charta `agents/13_clo.md` + Skills `skills/clo/*` als System-Prompt, wie bei jeder Fachagenten-Anfrage) prueft
jede Vorlage Paragraph fuer Paragraph mit seinen Rechtsquellen (`skills/clo/*/quellen.md`) und liefert je Paragraph:
Ampel, Fundstelle, Risiko, Vorschlag, offene Frage an die Anwaeltin und eine ueberarbeitete Fassung. Ergebnis:
**Pruefbericht fuer die Anwaeltin** (JSON + PDF) und die ueberarbeiteten Texte als moegliche **Version 2** (Entwurf,
Quelle „CLO-Agent, ungeprueft“), die der CEO per Klick ins Vertragswerk uebernimmt -- erst nachdem er den Bericht
gelesen hat. Datenfluss: nur die Vertragstexte (keine Kundendaten) gehen an das Modell (Gemini).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

AMPELN = ("gruen", "gelb", "rot")
QUELLE_V2 = "CLO-Agent (Gemini), ungeprüft"
BERICHT = Path(__file__).resolve().parents[2] / "docs" / "recht" / "clo-pruefung-vertragsentwuerfe.json"

AUFTRAG = """Du bist der CLO. Pruefe die folgende Vertragsvorlage Paragraph fuer Paragraph mit deinen Skills und den
mitgelieferten Rechtsquellen. Kontext: Hanserautisch ist Kleinunternehmer (§ 19 UStG) und erbringt Social-Media-
Content- und Werbeleistungen fuer Unternehmen (B2B, ganz selten Verbraucher). Platzhalter in geschweiften Klammern
werden spaeter automatisch gefuellt -- nicht ersetzen, nicht bemaengeln, aber in der ueberarbeiteten Fassung beibehalten.

Antworte NUR mit einem JSON-Objekt ohne weiteren Text:
{"gesamt": "2-4 Saetze Gesamteinschaetzung", "paragraphen": [
  {"titel": "§ ... (unveraendert wie in der Vorlage)", "ampel": "gruen|gelb|rot", "fundstelle": "Norm/Absatz oder Urteil",
   "risiko": "ein Satz", "vorschlag": "konkrete Aenderung oder 'keine'", "frage_anwaeltin": "offene Frage oder ''",
   "neuer_text": "ueberarbeitete Fassung des Paragraphen (vollstaendig)"}],
 "fehlend": [{"titel": "§ ... vorgeschlagener neuer Paragraph", "begruendung": "warum", "text": "Formulierung"}]}

Regeln: keine erfundenen Aktenzeichen oder Paragraphen; was du nicht sicher weisst, als Frage an die Anwaeltin;
deutsche Sprache; Ausgabe ist ein Entwurf -- anwaltliche Pruefung erforderlich."""


def quellen_text(skills_dir: Path | str) -> str:
    teile = []
    for q in sorted(Path(skills_dir).glob("*/quellen.md")):
        teile.append(q.read_text(encoding="utf-8"))
    return "\n\n".join(teile)


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("Keine JSON-Antwort vom Modell.")
    return json.loads(m.group(0))


def pruefe_vorlage(art: str, entwurf: dict, *, system: str, quellen: str, client, modell: str) -> dict:
    """Eine Vorlage pruefen -> {art, titel, gesamt, paragraphen: [...], fehlend: [...]} (validiert)."""
    vorlage = "\n\n".join(f"{p['titel']}\n{p['text']}" for p in entwurf["paragraphen"])
    nutzer = (f"{AUFTRAG}\n\n# Rechtsquellen (Wortlaut, Stand siehe Kopf)\n{quellen}\n\n"
              f"# Vorlage: {entwurf['titel']}\n{vorlage}")
    r = client.chat.completions.create(model=modell, messages=[{"role": "system", "content": system},
                                                               {"role": "user", "content": nutzer}], max_tokens=16000)
    d = _json(r.choices[0].message.content or "")
    titel = [p["titel"] for p in entwurf["paragraphen"]]
    pars = []
    for p in d.get("paragraphen") or []:
        if p.get("titel") not in titel:
            continue
        pars.append({"titel": p["titel"], "ampel": p.get("ampel") if p.get("ampel") in AMPELN else "gelb",
                     **{k: str(p.get(k) or "").strip()[:4000] for k in ("fundstelle", "risiko", "vorschlag",
                                                                         "frage_anwaeltin", "neuer_text")}})
    gesehen = {p["titel"] for p in pars}
    pars += [{"titel": t, "ampel": "gelb", "fundstelle": "", "risiko": "vom CLO nicht bewertet", "vorschlag": "",
              "frage_anwaeltin": "Paragraph bitte pruefen (keine Bewertung durch den CLO).", "neuer_text": ""}
             for t in titel if t not in gesehen]
    pars.sort(key=lambda p: titel.index(p["titel"]))
    fehlend = [{k: str(f.get(k) or "").strip()[:3000] for k in ("titel", "begruendung", "text")}
               for f in d.get("fehlend") or [] if f.get("titel") and f.get("text")]
    return {"art": art, "titel": entwurf["titel"], "gesamt": str(d.get("gesamt") or "").strip()[:2000],
            "paragraphen": pars, "fehlend": fehlend}


def version2(pruefung: dict, entwurf: dict) -> list[dict]:
    """Ueberarbeitete Paragraphen (neuer Text, sonst alter) + vom CLO vorgeschlagene neue Paragraphen."""
    neu = {p["titel"]: p["neuer_text"] for p in pruefung["paragraphen"] if p.get("neuer_text")}
    out = [{"titel": p["titel"], "text": neu.get(p["titel"]) or p["text"]} for p in entwurf["paragraphen"]]
    out += [{"titel": f["titel"], "text": f["text"]} for f in pruefung.get("fehlend") or []]
    return out


def bericht_laden(pfad: Path | str = BERICHT) -> dict | None:
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pdf(bericht: dict, *, firmendaten: dict) -> bytes:
    """Pruefbericht fuer die Anwaeltin (alle Vorlagen, je Paragraph Ampel/Fundstelle/Risiko/Vorschlag/Frage)."""
    from fpdf import FPDF
    from .beleg_pdf import BLAU, DEJAVU, GRAU, ROT, _latin1
    uni = (DEJAVU / "DejaVuSans.ttf").exists() and (DEJAVU / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1
    farbe = {"gruen": (31, 143, 87), "gelb": (194, 125, 22), "rot": (208, 52, 77)}

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font(S, size=7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4, T(f"Entwurf – anwaltliche Prüfung erforderlich · CLO-Prüfbericht · Seite {self.page_no()}/{{nb}}"),
                      align="C")

    p = _Pdf(format="A4")
    S = "Helvetica"
    if uni:
        p.add_font("DejaVu", "", str(DEJAVU / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(DEJAVU / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    p.set_margins(18, 14, 18)
    p.set_auto_page_break(True, margin=20)
    p.alias_nb_pages()
    p.add_page()
    B = p.w - 36
    p.set_fill_color(*BLAU)
    p.rect(18, 14, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT)
    p.rect(18 + B / 2, 14, B / 2, 1.6, style="F")
    p.set_xy(18, 20)
    p.set_font(S, "B", 17)
    p.cell(B, 9, T("Prüfbericht Vertragsvorlagen (CLO)"), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, size=9.5)
    p.set_text_color(85, 85, 85)
    p.multi_cell(B, 5, T(f"{firmendaten.get('firma', '')} · erstellt {bericht.get('datum', '')} · Modell {bericht.get('modell', '')} · "
                         "Entwurf, keine Rechtsberatung – zur Prüfung durch die Anwältin."), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    for v in bericht.get("vorlagen") or []:
        p.ln(4)
        p.set_font(S, "B", 13)
        p.set_text_color(*BLAU)
        p.multi_cell(B, 7, T(v["titel"]), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(0, 0, 0)
        p.set_font(S, size=9.5)
        if v.get("gesamt"):
            p.multi_cell(B, 5, T(v["gesamt"]), new_x="LMARGIN", new_y="NEXT")
        for x in v["paragraphen"]:
            if p.get_y() > p.h - 45:
                p.add_page()
            p.ln(2)
            p.set_fill_color(*GRAU)
            p.set_font(S, "B", 10)
            p.set_text_color(*farbe.get(x["ampel"], (0, 0, 0)))
            p.cell(8, 6, T("●"), fill=True)
            p.set_text_color(0, 0, 0)
            p.multi_cell(B - 8, 6, T(f"{x['titel']}  ({x['ampel']})"), fill=True, new_x="LMARGIN", new_y="NEXT")
            p.set_font(S, size=9)
            for label, k in (("Fundstelle", "fundstelle"), ("Risiko", "risiko"), ("Vorschlag", "vorschlag"),
                             ("Frage an die Anwältin", "frage_anwaeltin")):
                if x.get(k) and x[k].lower() != "keine":
                    p.multi_cell(B, 4.6, T(f"{label}: {x[k]}"), new_x="LMARGIN", new_y="NEXT")
        for f in v.get("fehlend") or []:
            p.ln(2)
            p.set_font(S, "B", 10)
            p.multi_cell(B, 6, T(f"Neu vorgeschlagen: {f['titel']}"), new_x="LMARGIN", new_y="NEXT")
            p.set_font(S, size=9)
            p.multi_cell(B, 4.6, T(f"Begründung: {f['begruendung']}"), new_x="LMARGIN", new_y="NEXT")
    return bytes(p.output())
