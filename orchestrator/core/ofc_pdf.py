"""OFC-Kasse: einfacher Bericht als PDF (A4 hochkant) im Stil des Saisonberichts (O6) -- Titel, Kennzahlen, Tabellen."""
from __future__ import annotations

from datetime import date
from pathlib import Path


def bericht_pdf(titel: str, kacheln: list[tuple[str, str]], abschnitte: list[tuple[str, list[tuple[str, float]], list[list[str]]]],
                *, text: str = "", fuss: str = "", schrift_dir: Path | None = None) -> bytes:
    """abschnitte: [(Ueberschrift, [(Spalte, Breite in mm; 0 = Rest)], Zeilen)]."""
    from fpdf import FPDF
    from .beleg_pdf import BLAU, DEJAVU, GRAU, LINIE, ROT, _latin1
    sd = Path(schrift_dir) if schrift_dir else DEJAVU
    uni = (sd / "DejaVuSans.ttf").exists() and (sd / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1
    p = FPDF(format="A4", orientation="P")
    if uni:
        p.add_font("DejaVu", "", str(sd / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(sd / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    else:
        S = "Helvetica"
    p.set_title(T(titel)); p.set_creator("LUNA-OS")
    p.set_margins(16, 14, 16); p.set_auto_page_break(True, margin=16)
    p.add_page()
    B = p.w - 32
    p.set_fill_color(*BLAU); p.rect(16, 14, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT); p.rect(16 + B / 2, 14, B / 2, 1.6, style="F")
    p.set_xy(16, 20); p.set_font(S, "B", 17)
    p.cell(B, 9, T(titel), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, size=9); p.set_text_color(90, 90, 90)
    p.cell(B, 5, T(f"Stand {date.today().strftime('%d.%m.%Y')} · erstellt von LUNA"), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0); p.ln(3)
    if kacheln:
        w = B / len(kacheln)
        y0 = p.get_y()
        p.set_fill_color(*GRAU); p.rect(16, y0, B, 17, style="F")
        for i, (l, v) in enumerate(kacheln):
            p.set_xy(16 + i * w + 3, y0 + 2.5); p.set_font(S, size=7.5); p.set_text_color(110, 110, 110); p.cell(w - 6, 4, T(l))
            p.set_xy(16 + i * w + 3, y0 + 7.5); p.set_font(S, "B", 11.5); p.set_text_color(*BLAU); p.cell(w - 6, 7, T(v))
        p.set_text_color(0, 0, 0); p.set_y(y0 + 21)
    if text:
        p.set_font(S, size=8.5); p.multi_cell(B, 4.5, T(text), new_x="LMARGIN", new_y="NEXT"); p.ln(2)
    for ueberschrift, spalten, zeilen in abschnitte:
        if p.get_y() > p.h - 40:
            p.add_page()
        p.set_font(S, "B", 12); p.cell(B, 7, T(ueberschrift), new_x="LMARGIN", new_y="NEXT"); p.set_draw_color(*LINIE)
        fest = sum(b for _, b in spalten if b)
        sp = [(k, b or max(B - fest, 10)) for k, b in spalten]
        p.set_font(S, "B", 8)
        for k, b in sp:
            p.cell(b, 6, T(k), border="B")
        p.ln(6); p.set_font(S, size=8)
        for z in zeilen or [["–"] + [""] * (len(sp) - 1)]:
            if p.get_y() > p.h - 22:
                p.add_page()
            for (_, b), v in zip(sp, z):
                txt = T(v)
                while p.get_string_width(txt) > b - 1.5 and len(txt) > 3:
                    txt = txt[:-2] + ("…" if uni else ".")
                p.cell(b, 5.5, txt, border="B")
            p.ln(5.5)
        p.ln(3)
    if fuss:
        p.set_font(S, size=7.5); p.set_text_color(110, 110, 110); p.multi_cell(B, 4, T(fuss)); p.set_text_color(0, 0, 0)
    return bytes(p.output())
