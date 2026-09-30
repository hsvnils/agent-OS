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
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):                 # „1.600“ = eintausendsechshundert (deutsch)
        t = t.replace(".", "")
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
              schrift_dir: Path | None = None, summen_zeilen: list[tuple[str, int]] | None = None) -> bytes:
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
        for b, w, a in zip(breiten[2:], (menge_text(p["menge"]), p.get("einheit", ""),
                                         p.get("einzel_text") or eur(p["einzelpreis_cent"]),
                                         p.get("gesamt_text") or eur(p["gesamt_cent"])), ("R", "L", "R", "R")):
            pdf.set_xy(x, y0 + 1)
            pdf.cell(b, 4.6, T(w), align=a)
            x += b
        pdf.set_y(y0 + hoehe)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(20, pdf.get_y(), 20 + sum(breiten), pdf.get_y())
    pdf.ln(2)
    pdf.set_font(SCHRIFT, size=9)
    for label, betrag in summen_zeilen or []:                          # Zuschlaege/Rabatt (Etappe 3b)
        pdf.cell(sum(breiten[:4]), 5.5, T(label), align="R")
        pdf.cell(breiten[4] + breiten[5], 5.5, T(eur(betrag)), align="R", new_x="LMARGIN", new_y="NEXT")
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


# -- Hanserautisch-Layout (Etappe 3b, aus dem Preislisten-Generator des CEO) -------------------------------------

BLAU = (0, 64, 135)
ROT = (204, 0, 0)
LINIE = (221, 221, 221)
GRAU = (242, 242, 242)


def _md(text: str) -> str:
    """Nutzertext fuer fpdf2-Markdown entschaerfen (nur unser eigenes **fett** soll wirken)."""
    return str(text or "").replace("**", "*​*").replace("__", "_​_").replace("--", "-​-")


def hanserautisch_pdf(*, art: str, nummer: str | None, firma: dict, logo: Path | None, empfaenger: list[str],
                      infos: list[str], untertitel: str, anrede: str, einleitung: str, texte: dict,
                      zeige_kalkulation: bool, zeige_kennzahlen: bool, gruppen: list[tuple],
                      summen: dict | None, zuschlag_liste: list[dict] | None, fuss_zusatz: str = "",
                      schrift_dir: Path | None = None) -> bytes:
    """Angebot oder Preisliste im Hanserautisch-Look.

    `gruppen`: [(name, farbe 'blau'|'rot', [{name, detail, menge|None, einheit, betrag_cent}])];
    `summen` (nur Angebot): {formate_cent, zuschlaege: [(name, prozent, cent)], rabatt: (prozent, cent)|None, gesamt_cent}.
    """
    from fpdf import FPDF

    sd = Path(schrift_dir) if schrift_dir else DEJAVU
    unicode_ok = (sd / "DejaVuSans.ttf").exists() and (sd / "DejaVuSans-Bold.ttf").exists()
    T = (lambda s: str(s or "")) if unicode_ok else _latin1
    bank = firma.get("bank") or {}
    fusszeilen = [" · ".join(x for x in (
        f"Steuernummer: {firma['steuernummer']}" if firma.get("steuernummer") else "",
        f"Bank: {bank['bank']}" if bank.get("bank") else "",
        f"IBAN: {_iban_lesbar(bank['iban'])}" if bank.get("iban") else "",
        f"BIC: {bank['bic']}" if bank.get("bic") else "",
        f"Kontoinhaber: {bank['kontoinhaber']}" if bank.get("kontoinhaber") else "") if x)]

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font(S, size=7)
            self.set_text_color(120, 120, 120)
            for z in fusszeilen:
                if z:
                    self.cell(0, 3.5, T(z), align="C", new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 3.5, T(f"Seite {self.page_no()}/{{nb}}"), align="C")

    pdf = _Pdf(format="A4")
    if unicode_ok:
        pdf.add_font("DejaVu", "", str(sd / "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", str(sd / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    else:
        S = "Helvetica"
    pdf.set_title(T(f"{art} {nummer or ''}".strip()))
    pdf.set_author(T(firma.get("firma", "")))
    pdf.set_creator("LUNA-OS")
    pdf.set_margins(20, 14, 20)
    pdf.set_auto_page_break(True, margin=22)
    pdf.alias_nb_pages()
    pdf.add_page()
    B = pdf.w - 40                                                    # Nutzbreite

    def farbe(rgb):
        pdf.set_text_color(*rgb)

    def platz(h):
        if pdf.get_y() + h > pdf.h - 24:
            pdf.add_page()

    # Logo + Farbbalken
    y = 14
    if logo and Path(logo).exists():
        try:
            pdf.image(str(logo), x=(pdf.w - 55) / 2, y=y, w=55)
            y += 55 * 221 / 560 + 3                                   # Seitenverhaeltnis des Logos
        except Exception:
            pass
    pdf.set_fill_color(*BLAU)
    pdf.rect(20, y, B / 2, 1.6, style="F")
    pdf.set_fill_color(*ROT)
    pdf.rect(20 + B / 2, y, B / 2, 1.6, style="F")
    y += 9

    # Anschrift links, Titel + Meta rechts
    pdf.set_xy(20, y)
    pdf.set_font(S, size=6.8)
    farbe((136, 136, 136))
    pdf.cell(95, 3.2, T(firma.get("firma", "")), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 3.2, T(" · ".join(x for x in (firma.get("inhaber"), firma.get("zusatz"), firma.get("strasse"),
                                                 f"{firma.get('plz', '')} {firma.get('ort', '')}".strip()) if x)),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINIE)
    pdf.line(20, pdf.get_y() + 1, 115, pdf.get_y() + 1)
    pdf.set_y(pdf.get_y() + 3)
    farbe((0, 0, 0))
    for i, z in enumerate(x for x in empfaenger if x):
        pdf.set_font(S, "B" if i == 0 else "", 9.5)
        pdf.cell(95, 5, T(z), new_x="LMARGIN", new_y="NEXT")
    y_links = pdf.get_y()
    pdf.set_xy(120, y)
    groesse = 20.0
    pdf.set_font(S, "B", groesse)
    while groesse > 12 and pdf.get_string_width(T(art)) > B - 100:     # z. B. „Auftragsbestätigung“ passt nicht in 20 pt
        groesse -= 1
        pdf.set_font(S, "B", groesse)
    pdf.cell(B - 100, 9, T(art), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(S, size=9.5)
    farbe((85, 85, 85))
    if untertitel:
        pdf.set_x(120)
        pdf.cell(B - 100, 5, T(untertitel), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_font(S, size=8.5)
    farbe((119, 119, 119))
    for z in infos:
        if z:
            pdf.set_x(110)
            pdf.cell(B - 90, 4.4, T(z), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(max(y_links, pdf.get_y()) + 7)
    farbe((0, 0, 0))

    # Anrede + Einleitung
    pdf.set_font(S, "B", 10)
    pdf.multi_cell(0, 5.2, T(anrede), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(S, size=10)
    if einleitung:
        pdf.multi_cell(0, 5.2, T(einleitung), align="L", new_x="LMARGIN", new_y="NEXT")

    # So kalkulieren wir
    absaetze = texte.get("kalkulation") or []
    if zeige_kalkulation and absaetze:
        def fett_vorn(t):
            k, _, rest = t.partition(":")
            return f"**{_md(k)}:**{_md(rest)}" if rest and len(k) < 40 else _md(t)
        pdf.set_font(S, size=9.3)
        h = 6 + sum(pdf.multi_cell(B - 10, 4.8, T(fett_vorn(a)), markdown=True, dry_run=True, output="HEIGHT") + 2
                    for a in absaetze)
        if texte.get("kalkulation_beispiel"):
            h += 4 + pdf.multi_cell(B - 10, 4.8, T(texte["kalkulation_beispiel"]), dry_run=True, output="HEIGHT")
        link = texte.get("kalkulation_link") or []                    # Etappe 16: [Text, URL] -- z. B. OMR-Quelle
        if len(link) == 2:
            h += 6
        pdf.ln(5)
        platz(h + 8)
        y0 = pdf.get_y()
        pdf.set_fill_color(*GRAU)
        pdf.rect(20, y0, B, h + 6, style="F")
        pdf.set_fill_color(*BLAU)
        pdf.rect(20, y0, 1.4, h + 6, style="F")
        pdf.set_xy(25, y0 + 3)
        pdf.set_font(S, "B", 11)
        pdf.cell(B - 10, 6, T(texte.get("kalkulation_titel", "")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(S, size=9.3)
        for a in absaetze:
            pdf.set_x(25)
            pdf.multi_cell(B - 10, 4.8, T(fett_vorn(a)), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        if texte.get("kalkulation_beispiel"):
            pdf.set_draw_color(*LINIE)
            pdf.line(25, pdf.get_y() + 1, 20 + B - 5, pdf.get_y() + 1)
            pdf.set_xy(25, pdf.get_y() + 3)
            pdf.multi_cell(B - 10, 4.8, T(texte["kalkulation_beispiel"]), align="L", new_x="LMARGIN", new_y="NEXT")
        if len(link) == 2:
            pdf.set_xy(25, pdf.get_y() + 1.5)
            pdf.set_font(S, "U", 8.5)
            farbe(BLAU)
            seite = re.sub(r"^https?://(www\.)?", "", link[1]).split("/")[0]       # kurz halten, Link bleibt klickbar
            pdf.cell(B - 10, 4.5, T(f"{link[0]} · {seite}"), link=link[1], new_x="LMARGIN", new_y="NEXT")
            farbe((0, 0, 0))
            pdf.set_font(S, size=9.3)
        pdf.set_y(y0 + h + 6)

    # Kennzahlen
    kz = texte.get("kennzahlen") or []
    if zeige_kennzahlen and kz:
        pdf.ln(5)
        platz(26)
        n, abstand = len(kz), 3
        bb = (B - abstand * (n - 1)) / n
        y0 = pdf.get_y()
        pdf.set_draw_color(*LINIE)
        for i, (wert, label) in enumerate(kz):
            x = 20 + i * (bb + abstand)
            pdf.rect(x, y0, bb, 15)
            pdf.set_xy(x, y0 + 2)
            pdf.set_font(S, "B", 13)
            farbe(BLAU)
            pdf.cell(bb, 6, T(wert), align="C")
            pdf.set_xy(x, y0 + 8.5)
            pdf.set_font(S, size=7.5)
            farbe((102, 102, 102))
            pdf.cell(bb, 4, T(label), align="C")
        pdf.set_y(y0 + 17)
        if texte.get("kennzahlen_quelle"):
            pdf.set_font(S, size=7.8)
            farbe((136, 136, 136))
            pdf.multi_cell(0, 3.8, T(texte["kennzahlen_quelle"]), align="L", new_x="LMARGIN", new_y="NEXT")
        farbe((0, 0, 0))

    # Positionen je Gruppe
    pdf.ln(6)
    platz(20)
    pdf.set_font(S, "B", 14)
    pdf.cell(0, 7, T("Ihre Positionen" if summen is not None else "Formate & Preise"), new_x="LMARGIN", new_y="NEXT")
    for gname, gfarbe, posten in gruppen:
        if not posten:
            continue
        platz(18)
        pdf.ln(3)
        pdf.set_font(S, "B", 9.5)
        farbe(ROT if gfarbe == "rot" else BLAU)
        pdf.cell(0, 5.5, T(gname), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 20 + B, pdf.get_y())
        pdf.set_line_width(0.2)
        farbe((0, 0, 0))
        for p in posten:
            breite_txt = B - 50
            pdf.set_font(S, size=8.3)
            h_detail = pdf.multi_cell(breite_txt, 4, T(p.get("detail", "")), dry_run=True, output="HEIGHT") if p.get("detail") else 0
            h = 5.2 + h_detail + 3
            platz(h)
            y0 = pdf.get_y() + 1.5
            pdf.set_xy(20, y0)
            pdf.set_font(S, "B", 9.5)
            pdf.cell(breite_txt, 5.2, T(p["name"]))
            if p.get("detail"):
                pdf.set_xy(20, y0 + 5.2)
                pdf.set_font(S, size=8.3)
                farbe((102, 102, 102))
                pdf.multi_cell(breite_txt, 4, T(p["detail"]), align="L")
                farbe((0, 0, 0))
            if p.get("menge") is not None:
                pdf.set_xy(20 + breite_txt, y0)
                pdf.set_font(S, "B", 9.5)
                pdf.cell(14, 5.2, T(f"{menge_text(p['menge'])} ×"), align="R")
            pdf.set_xy(20 + B - 34, y0)
            pdf.set_font(S, "B", 9.5)
            pdf.cell(34, 5.2, T(p.get("betrag_text") or eur(p["betrag_cent"])), align="R")
            if p.get("einheit"):
                pdf.set_xy(20 + B - 34, y0 + 5)
                pdf.set_font(S, size=7.5)
                farbe((119, 119, 119))
                pdf.cell(34, 4, T(f"/ {p['einheit']}"), align="R")
                farbe((0, 0, 0))
            pdf.set_y(y0 - 1.5 + h)
            pdf.set_draw_color(*LINIE)
            pdf.line(20, pdf.get_y(), 20 + B, pdf.get_y())

    # Summen (Angebot)
    if summen is not None:
        pdf.ln(5)
        zeilen = (1 + len(summen.get("zuschlaege") or []) + (1 if summen.get("rabatt") else 0) + ("provision_cent" in summen)
                  + (1 + len(summen["abzuege"]) if summen.get("abzuege") else 0))
        platz(zeilen * 5.5 + 16)
        x0, bs = 20 + B - 115, 115
        pdf.set_font(S, size=9.5)

        def zeile(links, rechts, rgb=(0, 0, 0), fett=False):
            farbe(rgb)
            pdf.set_x(x0)
            pdf.set_font(S, "B" if fett else "", 9.5)
            pdf.cell(bs - 32, 5.5, T(links))
            pdf.cell(32, 5.5, T(rechts), align="R", new_x="LMARGIN", new_y="NEXT")

        zeile("Summe Formate", eur(summen["formate_cent"]), fett=True)
        for name, prozent, c in summen.get("zuschlaege") or []:
            zeile(f"{name} (+{menge_text(prozent)} %)", eur(c), (51, 51, 51))
        if summen.get("rabatt"):
            pr, c = summen["rabatt"]
            zeile(f"Paketrabatt ({menge_text(pr)} %)", eur(-c), ROT)
        if "provision_cent" in summen:                     # Etappe 23: Provision (Affiliate)
            zeile("Provision",
                  "nach Abrechnung" if summen.get("provision_offen") and not summen["provision_cent"] else eur(summen["provision_cent"]))
        if summen.get("abzuege"):                          # Schlussrechnung: Vorkasse abziehen (Etappe 18)
            zeile("Auftragssumme", eur(summen["vor_abzug_cent"]), fett=True)
            for name, c in summen["abzuege"]:
                zeile(name, eur(-c), ROT)
        pdf.set_x(x0)
        pdf.set_fill_color(0, 0, 0)
        farbe((255, 255, 255))
        pdf.set_font(S, "B", 10)
        pdf.cell(bs - 32, 7, T("  Gesamtbetrag"), fill=True)
        pdf.cell(32, 7, T(eur(summen["gesamt_cent"]) + "  "), align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
        farbe((102, 102, 102))
        pdf.set_x(x0)
        pdf.set_font(S, size=8.3)
        pdf.cell(bs, 5, T(HINWEIS_19), new_x="LMARGIN", new_y="NEXT")
        farbe((0, 0, 0))

    # Zusaetzliche Leistungen (Preisliste)
    if zuschlag_liste:
        pdf.ln(6)
        platz(30)
        pdf.set_font(S, "B", 12.5)
        pdf.cell(0, 7, T("Zusätzliche Leistungen"), new_x="LMARGIN", new_y="NEXT")
        if texte.get("zuschlaege_info"):
            pdf.set_font(S, size=8.5)
            farbe((102, 102, 102))
            pdf.multi_cell(0, 4.2, T(texte["zuschlaege_info"]), align="L", new_x="LMARGIN", new_y="NEXT")
            farbe((0, 0, 0))
        pdf.ln(1)
        for z in zuschlag_liste:
            platz(10)
            y0 = pdf.get_y()
            pdf.set_font(S, size=8.5)
            txt = f"**{_md(z['name'])}**" + (f" – {_md(z['info'])}" if z.get("info") else "")
            pdf.set_x(20)
            pdf.multi_cell(B - 25, 4.3, T(txt), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
            y1 = pdf.get_y()
            pdf.set_xy(20 + B - 25, y0)
            pdf.set_font(S, "B", 9)
            farbe(ROT)
            pdf.cell(25, 4.3, T(f"+{menge_text(z['prozent'])} %"), align="R")
            farbe((0, 0, 0))
            pdf.set_y(y1 + 1)
            pdf.set_draw_color(*LINIE)
            pdf.line(20, pdf.get_y(), 20 + B, pdf.get_y())
            pdf.ln(1)

    # Fusstext
    pdf.ln(6)
    platz(25)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 20 + B, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(3)
    pdf.set_font(S, size=8.3)
    farbe((102, 102, 102))
    pdf.multi_cell(0, 4.2, T(" ".join(x for x in (texte.get("fuss", ""), fuss_zusatz) if x)), align="L",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    farbe((0, 0, 0))
    pdf.set_font(S, "B", 8.5)
    pdf.cell(0, 4.5, T(" · ".join(x for x in (firma.get("firma"), firma.get("zusatz"), texte.get("kontakt")) if x)),
             new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
