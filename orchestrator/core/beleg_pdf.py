"""PDF fuer Geschaeftsbelege (Angebot, spaeter Auftragsbestaetigung und Rechnung) -- KUNDEN_FINANZEN Etappe 3.

Layout angelehnt an DIN 5008 (Absenderzeile + Anschriftfeld links, Info-Block rechts, Positionstabelle, Summe,
Kleinunternehmer-Hinweis, Fusszeile mit Anschrift/Bank/Steuernummer). Betraege intern in **Cent** (int), nie float.

Schrift: DejaVu Sans (Paket `fonts-dejavu-core` im Docker-Image) fuer €, Gedankenstriche und Anfuehrungszeichen; fehlt
sie, faellt das Modul auf Helvetica zurueck und ersetzt nicht darstellbare Zeichen (€ -> EUR). `fpdf2` wird erst beim
Erzeugen importiert, damit die Web-App auch ohne neu gebautes Image startet.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
HINWEIS_19 = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."

# -- Geld und Mengen ---------------------------------------------------------------------------------------------


def _dezimal(wert) -> Decimal:
    """'1.234,50' / '1234.50' / '1234,5' / 12 / 12.5 -> Decimal. ValueError bei Unsinn."""
    if isinstance(wert, bool):
        raise ValueError("Ungueltige Zahl.")
    if isinstance(wert, (int, Decimal)):
        return Decimal(wert)
    if isinstance(wert, float):
        return Decimal(str(wert))
    t = str(wert or "").strip().replace("€", "").replace("EUR", "").replace(" ", "")
    if not t:
        raise ValueError("Zahl fehlt.")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        d = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"Ungueltige Zahl: {wert}") from None
    if not d.is_finite():
        raise ValueError(f"Ungueltige Zahl: {wert}")
    return d


def cent(wert) -> int:
    """Betrag in Euro (Text oder Zahl) -> ganze Cent, kaufmaennisch gerundet."""
    return int((_dezimal(wert) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def menge(wert) -> Decimal:
    d = _dezimal(wert)
    if d <= 0:
        raise ValueError("Menge muss groesser als 0 sein.")
    return d.normalize()


def positions_summe(menge_text: str, einzel_cent: int) -> int:
    return int((Decimal(menge_text) * einzel_cent).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def eur(cent_betrag: int) -> str:
    """12345 -> '123,45 €' (deutsches Format, Tausenderpunkte)."""
    neg = cent_betrag < 0
    e, c = divmod(abs(int(cent_betrag)), 100)
    return ("-" if neg else "") + f"{e:,}".replace(",", ".") + f",{c:02d} €"


def menge_text(d) -> str:
    s = format(Decimal(str(d)).normalize(), "f")
    return s.replace(".", ",")


def datum_de(iso: str) -> str:
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return str(iso or "")


# -- PDF ---------------------------------------------------------------------------------------------------------

_ERSATZ = {"€": "EUR", "–": "-", "—": "-", "„": '"', "“": '"', "”": '"', "‚": "'", "‘": "'", "’": "'", "…": "...",
           "•": "-", " ": " "}


def _latin1(text: str) -> str:
    t = "".join(_ERSATZ.get(c, c) for c in str(text or ""))
    return t.encode("latin-1", "replace").decode("latin-1")


def beleg_pdf(*, art: str, nummer: str, firma: dict, empfaenger: list[str], infos: list[tuple[str, str]],
              einleitung: str, positionen: list[dict], summe_cent: int, hinweise: list[str], schluss: str,
              schrift_dir: Path | None = None) -> bytes:
    """Erzeugt das PDF. `positionen`: [{beschreibung, menge (Text), einheit, einzelpreis_cent, gesamt_cent}]."""
    from fpdf import FPDF

    sd = Path(schrift_dir) if schrift_dir else DEJAVU
    unicode_ok = (sd / "DejaVuSans.ttf").exists() and (sd / "DejaVuSans-Bold.ttf").exists()
    T = (lambda s: str(s or "")) if unicode_ok else _latin1
    bank = firma.get("bank") or {}
    fuss = [
        f"{firma.get('firma', '')} · {firma.get('zusatz', '')} · {firma.get('strasse', '')} · "
        f"{firma.get('plz', '')} {firma.get('ort', '')}".replace(" ·  · ", " · "),
        " · ".join(x for x in (
            f"Inhaber: {firma['inhaber']}" if firma.get("inhaber") else "",
            f"Steuernummer: {firma['steuernummer']}" if firma.get("steuernummer") else "",
            f"USt-IdNr.: {firma['ustid']}" if firma.get("ustid") else "") if x),
        " · ".join(x for x in (
            f"Bank: {bank['bank']}" if bank.get("bank") else "",
            f"IBAN: {_iban_lesbar(bank['iban'])}" if bank.get("iban") else "",
            f"BIC: {bank['bic']}" if bank.get("bic") else "",
            f"Kontoinhaber: {bank['kontoinhaber']}" if bank.get("kontoinhaber") else "") if x),
    ]

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-24)
            self.set_font(SCHRIFT, size=7)
            self.set_text_color(90, 90, 90)
            for z in fuss:
                if z.strip(" ·"):
                    self.cell(0, 3.6, T(z), align="C", new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 3.6, T(f"Seite {self.page_no()}/{{nb}}"), align="C")

    pdf = _Pdf(format="A4")
    if unicode_ok:
        pdf.add_font("DejaVu", "", str(sd / "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", str(sd / "DejaVuSans-Bold.ttf"))
        SCHRIFT = "DejaVu"
    else:
        SCHRIFT = "Helvetica"
    pdf.set_title(T(f"{art} {nummer}"))
    pdf.set_author(T(firma.get("firma", "")))
    pdf.set_creator("LUNA-OS")
    pdf.set_margins(20, 15, 20)
    pdf.set_auto_page_break(True, margin=30)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Briefkopf rechts oben
    pdf.set_font(SCHRIFT, "B", 13)
    pdf.cell(0, 6, T(firma.get("firma", "")), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(SCHRIFT, size=8.5)
    for z in (firma.get("zusatz"), firma.get("strasse"), f"{firma.get('plz', '')} {firma.get('ort', '')}".strip()):
        if z:
            pdf.cell(0, 4, T(z), align="R", new_x="LMARGIN", new_y="NEXT")

    # Anschriftfeld (DIN 5008 Form B: ab 45 mm von oben, 20 mm links)
    pdf.set_xy(20, 45)
    pdf.set_font(SCHRIFT, size=7)
    pdf.set_text_color(90, 90, 90)
    absender = " · ".join(x for x in (firma.get("firma"), firma.get("zusatz"), firma.get("strasse"),
                                        f"{firma.get('plz', '')} {firma.get('ort', '')}".strip()) if x)
    pdf.cell(85, 4, T(absender), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(SCHRIFT, size=10)
    pdf.set_y(51)
    for z in empfaenger:
        if z:
            pdf.cell(85, 5, T(z), new_x="LMARGIN", new_y="NEXT")

    # Info-Block rechts
    pdf.set_font(SCHRIFT, size=9)
    y = 51
    for label, wert in infos:
        if not wert:
            continue
        pdf.set_xy(125, y)
        pdf.cell(30, 5, T(label))
        pdf.cell(35, 5, T(wert), align="R")
        y += 5

    # Titel + Einleitung
    pdf.set_xy(20, max(pdf.get_y(), y) + 18)
    pdf.set_font(SCHRIFT, "B", 14)
    pdf.cell(0, 8, T(f"{art} {nummer}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(SCHRIFT, size=10)
    if einleitung:
        pdf.multi_cell(0, 5, T(einleitung), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Positionen
    breiten = (10, 80, 18, 18, 22, 22)
    kopf = ("Pos.", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "Gesamt")

    def tabellenkopf():
        pdf.set_font(SCHRIFT, "B", 9)
        pdf.set_fill_color(235, 239, 245)
        for b, k, a in zip(breiten, kopf, ("L", "L", "R", "L", "R", "R")):
            pdf.cell(b, 7, T(k), border="B", align=a, fill=True)
        pdf.ln()
        pdf.set_font(SCHRIFT, size=9)

    tabellenkopf()
    for i, p in enumerate(positionen, 1):
        zeilen = pdf.multi_cell(breiten[1], 4.6, T(p["beschreibung"]), align="L", dry_run=True, output="LINES")
        hoehe = max(1, len(zeilen)) * 4.6 + 2
        if pdf.get_y() + hoehe > pdf.h - 32:
            pdf.add_page()
            tabellenkopf()                                           # Kopf auf jeder Folgeseite wiederholen
        y0 = pdf.get_y()
        pdf.set_xy(20, y0 + 1)
        pdf.cell(breiten[0], 4.6, str(i))
        pdf.set_xy(20 + breiten[0], y0 + 1)
        pdf.multi_cell(breiten[1], 4.6, T(p["beschreibung"]), align="L")
        x = 20 + breiten[0] + breiten[1]
        for b, w, a in zip(breiten[2:], (menge_text(p["menge"]), p.get("einheit", ""), eur(p["einzelpreis_cent"]),
                                         eur(p["gesamt_cent"])), ("R", "L", "R", "R")):
            pdf.set_xy(x, y0 + 1)
            pdf.cell(b, 4.6, T(w), align=a)
            x += b
        pdf.set_y(y0 + hoehe)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(20, pdf.get_y(), 20 + sum(breiten), pdf.get_y())
    pdf.ln(2)
    pdf.set_font(SCHRIFT, "B", 10)
    pdf.cell(sum(breiten[:4]), 7, T("Gesamtbetrag"), align="R")
    pdf.cell(breiten[4] + breiten[5], 7, T(eur(summe_cent)), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font(SCHRIFT, size=9)
    for h in hinweise:
        if h:
            pdf.multi_cell(0, 4.8, T(h), align="L", new_x="LMARGIN", new_y="NEXT")
    if schluss:
        pdf.ln(3)
        pdf.set_font(SCHRIFT, size=10)
        pdf.multi_cell(0, 5, T(schluss), align="L", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _iban_lesbar(iban: str) -> str:
    t = re.sub(r"\s+", "", iban or "")
    return " ".join(t[i:i + 4] for i in range(0, len(t), 4))
