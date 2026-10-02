"""Projektbericht je Auftrag (PROJEKTBERICHT P3, CEO-Entscheidungen 2026-10-02).

Inhalt: Kampagne, Zeitraum, je Posting Link und Kennzahlen, Summen (Reichweite, Interaktionen, Engagement-Rate),
**Plan gegen Ist** mit den festgeschriebenen Konditionen (Gegenwert Ist, Mehrleistung, effektiver TKP, Summe) und --
nur mit Haken -- Stunden und km aus dem Stundenzettel. Das Fazit schlaegt LUNA regelbasiert aus den Zahlen vor; der CEO
passt es an. Versand nur nach CEO-Klick (Aussenkommunikation); das gesendete PDF liegt unveraenderlich in der
Firmenakte (`auftrag_bericht_versendet`), eine Korrektur ergibt einen neuen Bericht (Version 2, 3 ...).
"""
from __future__ import annotations

import re
from pathlib import Path

from .beleg_pdf import BLAU, DEJAVU, GRAU, LINIE, ROT, _latin1, datum_de, eur
from .postings import FELDER, konditionen, vergleich

INTERAKTION = ("likes", "kommentare", "geteilt", "gespeichert", "antworten")
MAX_FAZIT = 3000


def _tsd(n) -> str:
    return "–" if n is None else f"{int(n):,}".replace(",", ".")


def _pz(v) -> str:
    return "–" if v is None else f"{v:.1f} %".replace(".", ",")


def daten(a: dict, postings: list[dict], *, stundenzettel: dict | None = None, mit_stunden: bool = False,
          mit_km: bool = False) -> dict:
    """Alle Zahlen des Berichts (auch fuer die Vorschau in LUNA-OS)."""
    v = vergleich(postings)
    zeilen = []
    for p, z in zip(postings, v["zeilen"]):
        kz = p.get("kennzahlen") or {}
        inter = sum(int(kz.get(k) or 0) for k in INTERAKTION) if kz else None
        rw = kz.get("reichweite")
        zeilen.append(z | {"datum": p.get("datum") or "", "link": p.get("link") or "", "plattform": p["plattform"],
                           "kontakt_label": dict(FELDER[p["format"]])[p["kontakt_feld"]], "reichweite": rw,
                           "interaktionen": inter, "engagement_pct": round(inter / rw * 100, 1) if inter is not None and rw else None,
                           "kennzahlen": kz, "beschreibung": p.get("beschreibung", "")})
    gemessen = [z for z in zeilen if z["kontakte_ist"] is not None]
    rw_sum = sum(z["reichweite"] or 0 for z in gemessen)
    inter_sum = sum(z["interaktionen"] or 0 for z in gemessen)
    tage = sorted(z["datum"] for z in zeilen if z["datum"])
    out = {"auftrag": a["nummer"], "titel": a.get("titel") or "", "firma": a["firma"],
           "zeitraum": [tage[0], tage[-1]] if tage else [a.get("leistung_von") or "", a.get("leistung_bis") or ""],
           "postings": zeilen, "summe": v["summe"] | {"reichweite": rw_sum, "interaktionen": inter_sum,
                                                       "kontakte_ist_alle": sum(z["kontakte_ist"] or 0 for z in gemessen),
                                                       "engagement_pct": round(inter_sum / rw_sum * 100, 1) if rw_sum else None},
           "konditionen": konditionen(a), "fehlen": [z["titel"] for z in zeilen if z["kontakte_ist"] is None]}
    if stundenzettel and (mit_stunden or mit_km):
        sz = stundenzettel
        out["stunden"] = {"mit_stunden": mit_stunden, "mit_km": mit_km,
                          "zeilen": [{k: x[k] for k in ("datum", "von", "bis", "pause_min", "minuten", "taetigkeit", "km")}
                                     for x in sz["eintraege"]],
                          "minuten": sz["summe"]["minuten"], "km": sz["summe"]["km"]}
    return out


def fazit_vorschlag(d: dict) -> str:
    """Regelbasiert aus den Zahlen (kein Sprachmodell): sachlich, positiv, ohne Uebertreibung."""
    s = d["summe"]
    teile = []
    n, m = s["anzahl"], s["gemessen"]
    if not n:
        return "Vielen Dank für die Zusammenarbeit! Gern setzen wir die nächste Kampagne mit Ihnen um."
    teile.append(f"Im Rahmen der Kampagne{' „' + d['titel'] + '“' if d['titel'] else ''} haben wir {n} "
                 f"Posting{'s' if n != 1 else ''} veröffentlicht" + (f", davon {m} mit gemessenen Zahlen." if m < n else "."))
    if s.get("kontakte_ist_alle"):
        teile.append(f"Insgesamt wurden {_tsd(s['kontakte_ist_alle'])} Kontakte erzielt"
                     + (f" bei {_tsd(s['reichweite'])} erreichten Konten" if s.get("reichweite") else "")
                     + (f" und {_tsd(s['interaktionen'])} Interaktionen" if s.get("interaktionen") else "") + ".")
    if s.get("erfuellung_pct") is not None:
        if s["erfuellung_pct"] >= 100:
            teile.append(f"Die vereinbarte Reichweite wurde mit {_pz(s['erfuellung_pct'])} übertroffen – rechnerisch ein "
                         f"Mehrwert von {eur(s['mehrleistung_cent'])} zum vereinbarten TKP.")
        else:
            teile.append(f"Die vereinbarte Reichweite wurde zu {_pz(s['erfuellung_pct'])} erreicht.")
    if s.get("engagement_pct") is not None:
        teile.append(f"Die Engagement-Rate lag bei {_pz(s['engagement_pct'])}.")
    teile.append("Vielen Dank für die Zusammenarbeit – wir freuen uns auf die nächste Kampagne mit Ihnen!")
    return " ".join(teile)


def pdf(d: dict, *, firmendaten: dict, firma_name: str, fazit: str, logo: Path | None = None, version: int = 1,
        schrift_dir: Path | None = None) -> bytes:
    from fpdf import FPDF
    sd = Path(schrift_dir) if schrift_dir else DEJAVU
    uni = (sd / "DejaVuSans.ttf").exists() and (sd / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font(S, size=7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4, T(f"{firmendaten.get('firma', '')} · Projektbericht {d['auftrag']} · Seite {self.page_no()}/{{nb}}"),
                      align="C")

    p = _Pdf(format="A4")
    if uni:
        p.add_font("DejaVu", "", str(sd / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(sd / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    else:
        S = "Helvetica"
    p.set_title(T(f"Projektbericht {d['auftrag']}"))
    p.set_creator("LUNA-OS")
    p.set_margins(18, 14, 18)
    p.set_auto_page_break(True, margin=20)
    p.alias_nb_pages()
    p.add_page()
    B = p.w - 36
    y = 14
    if logo and Path(logo).exists():
        try:
            p.image(str(logo), x=(p.w - 50) / 2, y=y, w=50)
            y += 50 * 221 / 560 + 3
        except Exception:
            pass
    p.set_fill_color(*BLAU)
    p.rect(18, y, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT)
    p.rect(18 + B / 2, y, B / 2, 1.6, style="F")
    p.set_xy(18, y + 6)
    p.set_font(S, "B", 18)
    p.cell(B, 9, T("Projektbericht" + (f" (Version {version})" if version > 1 else "")), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, size=10)
    p.set_text_color(85, 85, 85)
    zr = d["zeitraum"]
    zeitraum = " – ".join(datum_de(x) for x in dict.fromkeys(x for x in zr if x))
    p.multi_cell(B, 5, T(" · ".join(x for x in (firma_name, d["titel"], f"Auftrag {d['auftrag']}",
                                                f"Zeitraum {zeitraum}" if zeitraum else "") if x)),
                 new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    p.ln(4)

    s = d["summe"]
    kacheln = [("Kontakte", _tsd(s.get("kontakte_ist_alle"))), ("Erreichte Konten", _tsd(s.get("reichweite") or None)),
               ("Interaktionen", _tsd(s.get("interaktionen") or None)), ("Engagement-Rate", _pz(s.get("engagement_pct")))]
    if s.get("erfuellung_pct") is not None:
        kacheln[0] = (f"Kontakte · {_pz(s['erfuellung_pct'])} vom Plan", _tsd(s.get("kontakte_ist_alle")))
    w = B / 4
    y0 = p.get_y()
    p.set_fill_color(*GRAU)
    p.rect(18, y0, B, 18, style="F")
    for i, (lbl, wert) in enumerate(kacheln):
        p.set_xy(18 + i * w + 3, y0 + 2.5)
        p.set_font(S, size=7.5)
        p.set_text_color(110, 110, 110)
        p.cell(w - 6, 4, T(lbl))
        p.set_xy(18 + i * w + 3, y0 + 7.5)
        p.set_font(S, "B", 12)
        p.set_text_color(*BLAU)
        p.cell(w - 6, 7, T(wert))
    p.set_text_color(0, 0, 0)
    p.set_y(y0 + 24)

    def kopf(t):
        if p.get_y() > p.h - 50:
            p.add_page()
        p.set_font(S, "B", 12)
        p.cell(B, 7, T(t), new_x="LMARGIN", new_y="NEXT")
        p.set_draw_color(*LINIE)

    kopf("Postings und Zahlen")
    sp = [("Posting", 44), ("Datum", 20), ("Kontakte Plan", 24), ("Kontakte Ist", 24), ("Erfüllung", 18),
          ("Interaktionen", 24), ("Eng.-Rate", 18)]
    p.set_font(S, "B", 8)
    for t, bw in sp:
        p.cell(bw, 6, T(t), border="B", align="L" if t in ("Posting", "Datum") else "R")
    p.ln()
    p.set_font(S, size=8)
    for z in d["postings"]:
        werte = [f"{z['titel']} · {z['plattform']}", datum_de(z["datum"]) if z["datum"] else "–",
                 _tsd(z["kontakte_plan"] or None), _tsd(z["kontakte_ist"]), _pz(z["erfuellung_pct"]),
                 _tsd(z["interaktionen"]), _pz(z["engagement_pct"])]
        for (t, bw), v in zip(sp, werte):
            p.cell(bw, 5.5, T(v)[:34], border="B", align="L" if t in ("Posting", "Datum") else "R",
                   link=z["link"] if t == "Posting" and z["link"] else "")
        p.ln()
    p.set_font(S, size=7)
    p.set_text_color(110, 110, 110)
    p.multi_cell(B, 3.6, T("Kontakte: Reel und Story = Aufrufe, Bild-Post/Karussell = Impressionen. Interaktionen = Likes, "
                            "Kommentare, Geteilt, Gespeichert (Story: Antworten). Engagement-Rate = Interaktionen / "
                            "erreichte Konten. Posting-Titel sind verlinkt."), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    p.ln(3)

    tkp = [z for z in d["postings"] if z["gegenwert_cent"] is not None]
    if tkp:
        kopf(f"Plan gegen Ist (Konditionen festgeschrieben am {datum_de(d['konditionen']['festgeschrieben_am'])})")
        sp2 = [("Posting", 40), ("TKP vereinbart", 26), ("Preis", 24), ("Gegenwert Ist", 26), ("Mehrleistung", 24),
               ("TKP effektiv", 24)]
        p.set_font(S, "B", 8)
        for t, bw in sp2:
            p.cell(bw, 6, T(t), border="B", align="L" if t == "Posting" else "R")
        p.ln()
        p.set_font(S, size=8)
        for z in tkp:
            werte = [z["titel"], eur(z["tkp_cent"]), eur(z["preis_cent"]), eur(z["gegenwert_cent"]),
                     ("+" if z["mehrleistung_cent"] >= 0 else "−") + eur(abs(z["mehrleistung_cent"])),
                     eur(z["tkp_eff_cent"]) if z["tkp_eff_cent"] is not None else "–"]
            for (t, bw), v in zip(sp2, werte):
                p.cell(bw, 5.5, T(v), border="B", align="L" if t == "Posting" else "R")
            p.ln()
        p.set_font(S, "B", 8)
        werte = ["Summe", "", eur(s["preis_cent"]), eur(s["gegenwert_cent"]),
                 ("+" if s["mehrleistung_cent"] >= 0 else "−") + eur(abs(s["mehrleistung_cent"])), ""]
        for (t, bw), v in zip(sp2, werte):
            p.cell(bw, 6, T(v), align="L" if t == "Posting" else "R")
        p.ln()
        if s.get("mehrleistung_pct") is not None:
            p.set_font(S, "B", 9)
            p.set_text_color(*BLAU)
            p.cell(B, 6, T(f"{'Mehrleistung' if s['mehrleistung_cent'] >= 0 else 'Minderleistung'} gesamt: "
                           f"{eur(abs(s['mehrleistung_cent']))} ({_pz(abs(s['mehrleistung_pct']))} "
                           f"{'über' if s['mehrleistung_cent'] >= 0 else 'unter'} dem vereinbarten Preis)"),
                   new_x="LMARGIN", new_y="NEXT")
            p.set_text_color(0, 0, 0)
        p.set_font(S, size=7)
        p.set_text_color(110, 110, 110)
        p.multi_cell(B, 3.6, T("Gegenwert Ist = erreichte Kontakte × vereinbarter TKP / 1.000 + Produktion. Mehrleistung = "
                                "Gegenwert Ist − Preis. TKP effektiv = (Preis − Produktion) / erreichte Kontakte × 1.000."),
                     new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(0, 0, 0)
        p.ln(3)

    st = d.get("stunden")
    if st:
        kopf("Aufwand" if st["mit_stunden"] else "Fahrten")
        p.set_font(S, size=8.5)
        if st["mit_stunden"]:
            for z in st["zeilen"]:
                h = f"{z['minuten'] // 60}:{z['minuten'] % 60:02d} h"
                p.cell(B, 5, T(f"{datum_de(z['datum'])} · {z['von']}–{z['bis']} · {h}"
                               + (f" · {z['taetigkeit']}" if z.get("taetigkeit") else "")
                               + (f" · {z['km']} km" if st["mit_km"] and z.get("km") else "")),
                       new_x="LMARGIN", new_y="NEXT")
        p.set_font(S, "B", 8.5)
        teile = []
        if st["mit_stunden"]:
            teile.append(f"Gesamt {st['minuten'] // 60}:{st['minuten'] % 60:02d} h")
        if st["mit_km"]:
            teile.append(f"{st['km']} km gefahren")
        p.cell(B, 6, T(" · ".join(teile)), new_x="LMARGIN", new_y="NEXT")
        p.ln(3)

    if fazit.strip():
        kopf("Fazit")
        p.set_font(S, size=9.5)
        p.multi_cell(B, 5, T(fazit.strip()), new_x="LMARGIN", new_y="NEXT")
    return bytes(p.output())


def mail_text(d: dict, ap: dict | None, firmendaten: dict, version: int = 1) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Moin {name}," if name else "Moin,"
    betreff = f"Projektbericht {d['auftrag']}" + (f" – {d['titel']}" if d["titel"] else "") + (f" (Version {version})" if version > 1 else "")
    text = (f"{anrede}\n\nanbei unser Projektbericht zur Kampagne{' „' + d['titel'] + '“' if d['titel'] else ''} mit den "
            "erreichten Zahlen je Posting.\n\nBei Fragen melden Sie sich gern.\n\nViele Grüße\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text


def dateiname(nr: str, version: int) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"Projektbericht_{nr}" + (f"_v{version}" if version > 1 else "")) + ".pdf"


def entwurf_speichern(bh, ab, nr: str, *, fazit: str, stunden: bool, km: bool, von: str = "") -> dict:
    a = ab.auftrag(nr)
    if not a:
        raise KeyError(nr)
    if a["status"] == "storniert":
        raise ValueError(f"{a['nummer']} ist storniert.")
    d = {"nummer": a["nummer"], "fazit": str(fazit or "").strip()[:MAX_FAZIT], "stunden": bool(stunden), "km": bool(km)}
    bh.erfassen("auftrag_bericht", d, von=von)
    return {"bericht": d}


def entfaellt(bh, ab, nr: str, grund: str, *, von: str = "") -> dict:
    a = ab.auftrag(nr)
    if not a:
        raise KeyError(nr)
    if not str(grund or "").strip():
        raise ValueError("Bitte kurz begruenden, warum kein Bericht noetig ist.")
    bh.erfassen("auftrag_bericht_entfaellt", {"nummer": a["nummer"], "grund": str(grund).strip()[:300]}, von=von)
    return {"entfaellt": True}
