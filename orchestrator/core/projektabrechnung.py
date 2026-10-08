"""Projektzeiten optional in der Rechnung (PROJEKTZEITEN Z2, CEO-Entscheidungen 2026-10-02).

- Je Rechnungsentwurf aus einem Auftrag waehlbar: welche Zeiteintraege (und Fahrten) berechnet werden, Darstellung
  **zusammengefasst** (Standard: eine Position „Projektzeit 12,5 h“ + Stundenzettel als PDF-Anlage) oder **einzeln**
  (je Eintrag eine Position mit Datum und Uhrzeit).
- Preis = **Verkaufs-Stundensatz** (Katalog-Artikel „Projektstunde“, je Auftrag aenderbar) bzw. Verkaufs-km-Satz
  (Katalog-Artikel „Fahrt-km“). Der kalkulatorische Stundensatz (Etappe 25) bleibt davon getrennt.
- Die Auswahl steht als Momentaufnahme (`projektzeiten.zeilen`) am Entwurf und wird beim Festschreiben mit der
  Rechnung eingefroren. **Abgerechnet** ist eine Zeit, sobald sie auf einer festgeschriebenen Rechnung steht
  (`zeiterfassung.falte_zeiten` leitet das aus der Kette ab); eine Stornorechnung gibt sie wieder frei.
"""
from __future__ import annotations

import io
import re
from decimal import ROUND_HALF_UP, Decimal

from .angebote import _positionen
from .beleg_pdf import _latin1, cent, datum_de, eur
from .zeiterfassung import falte_zeiten

ZEIT_ID, KM_ID = "projektstunde", "projekt_km"
GRUPPE = "Projektzeiten"
DARSTELLUNGEN = ("zusammen", "einzeln")


def _stunden(minuten: int) -> str:
    return str((Decimal(minuten) / 60).quantize(Decimal("0.01"), ROUND_HALF_UP).normalize())


def _std_text(minuten: int) -> str:
    return _stunden(minuten).replace(".", ",") + " h"


def katalog_saetze(katalog) -> dict:
    """Verkaufs-Saetze aus dem Katalog: Artikel-ID oder Name „Projektstunde“ bzw. „Fahrt-km“/„Kilometer“."""
    out = {"satz_cent": 0, "km_satz_cent": 0}
    if katalog is None:
        return out
    for g in katalog.laden().get("gruppen") or []:
        for it in g.get("items") or []:
            name = str(it.get("name") or "").lower()
            if not out["satz_cent"] and (it.get("id") == ZEIT_ID or "projektstunde" in name):
                out["satz_cent"] = int(it.get("preis_cent") or 0)
            elif not out["km_satz_cent"] and (it.get("id") == KM_ID or re.search(r"\bkm\b|kilometer", name)):
                out["km_satz_cent"] = int(it.get("preis_cent") or 0)
    return out


def saetze(auftrag: dict, katalog) -> dict:
    """Je Auftrag gemerkter Satz vor dem Katalog-Satz."""
    k = katalog_saetze(katalog)
    return {"satz_cent": int(auftrag.get("verkauf_satz_cent") or k["satz_cent"] or 0),
            "km_satz_cent": int(auftrag.get("verkauf_km_cent") or k["km_satz_cent"] or 0),
            "quelle": "auftrag" if auftrag.get("verkauf_satz_cent") else "katalog" if k["satz_cent"] else ""}


def positionen(zeilen: list[dict], km_zeilen: list[dict], darstellung: str, satz: int, km_satz: int) -> list[dict]:
    pos = []
    basis = {"gruppe": GRUPPE}
    if zeilen:
        if darstellung == "einzeln":
            for z in zeilen:
                pos.append(basis | {"beschreibung": f"Arbeitszeit {datum_de(z['datum'])}, {z['von']}–{z['bis']} Uhr"
                                                    + (f" – {z['taetigkeit']}" if z.get("taetigkeit") else ""),
                                    "menge": _stunden(z["minuten"]), "einheit": "Std.", "einzelpreis_cent": satz,
                                    "katalog_id": ZEIT_ID})
        else:
            m = sum(z["minuten"] for z in zeilen)
            tage = sorted({z["datum"] for z in zeilen})
            zr = datum_de(tage[0]) + (f" – {datum_de(tage[-1])}" if len(tage) > 1 else "")
            pos.append(basis | {"beschreibung": f"Projektzeit {_std_text(m)}", "detail": f"{zr} · Stundenzettel siehe Anlage",
                                "menge": _stunden(m), "einheit": "Std.", "einzelpreis_cent": satz, "katalog_id": ZEIT_ID})
    if km_zeilen:
        if darstellung == "einzeln":
            for z in km_zeilen:
                pos.append(basis | {"beschreibung": f"Fahrtkosten {datum_de(z['datum'])} ({z['km']} km)", "menge": str(z["km"]),
                                    "einheit": "km", "einzelpreis_cent": km_satz, "katalog_id": KM_ID})
        else:
            km = sum(z["km"] for z in km_zeilen)
            pos.append(basis | {"beschreibung": f"Fahrtkosten ({km} km)", "menge": str(km), "einheit": "km",
                                "einzelpreis_cent": km_satz, "katalog_id": KM_ID})
    return pos


def setzen(rs, zeit, eid: str, *, zeiten: list, km: list, darstellung: str = "zusammen", satz="", km_satz="",
           von: str = "") -> dict:
    """Auswahl uebernehmen: ersetzt die Projektzeit-Positionen des Entwurfs; leere Auswahl entfernt sie wieder."""
    x = rs.get(eid)
    if not x or x.get("status") != "entwurf":
        raise KeyError(eid)
    if not x.get("auftrag") or x.get("art") == "anzahlung":
        raise ValueError("Projektzeiten gibt es nur auf der Rechnung zu einem Auftrag (nicht auf der Vorkasse-Rechnung).")
    if darstellung not in DARSTELLUNGEN:
        raise ValueError("Darstellung: zusammen oder einzeln.")
    sz = {z["id"]: z for z in zeit.stundenzettel(x["auftrag"])["eintraege"]}
    zeiten, km = [str(i) for i in zeiten or []], [str(i) for i in km or []]
    for i in zeiten + km:
        if i not in sz:
            raise ValueError(f"Zeiteintrag {i} gehoert nicht zu {x['auftrag']}.")
    doppelt = [sz[i]["abgerechnet"] for i in zeiten if sz[i]["abgerechnet"]] \
        + [sz[i]["km_abgerechnet"] for i in km if sz[i].get("km_abgerechnet")]
    if doppelt:
        raise ValueError(f"Schon abgerechnet auf {doppelt[0]} -- keine Doppelabrechnung.")
    if any(not sz[i]["km"] for i in km):
        raise ValueError("Fahrt ohne Kilometer gewaehlt.")
    s = cent(satz) if str(satz).strip() else 0
    ks = cent(km_satz) if str(km_satz).strip() else 0
    if zeiten and s <= 0:
        raise ValueError("Verkaufs-Stundensatz fehlt (Katalog-Artikel „Projektstunde“ oder hier eintragen).")
    if km and ks <= 0:
        raise ValueError("Verkaufs-km-Satz fehlt (Katalog-Artikel „Fahrt-km“ oder hier eintragen).")
    zeilen = [_zeile(sz[i]) for i in sorted(set(zeiten), key=lambda i: (sz[i]["datum"], sz[i]["von"]))]
    km_zeilen = [_zeile(sz[i]) for i in sorted(set(km), key=lambda i: (sz[i]["datum"], sz[i]["von"]))]
    rest = [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in x["positionen"]
            if p.get("katalog_id") not in (ZEIT_ID, KM_ID)]
    neu = rest + positionen(zeilen, km_zeilen, darstellung, s, ks)
    if not neu:
        raise ValueError("Ohne Positionen geht es nicht.")
    pz = ({"zeiten": [z["id"] for z in zeilen], "km": [z["id"] for z in km_zeilen], "darstellung": darstellung,
           "satz_cent": s, "km_satz_cent": ks, "zeilen": zeilen, "km_zeilen": km_zeilen} if zeilen or km_zeilen else {})

    def pruefe(eintraege):
        if eid not in rs._falte(eintraege)[0]:
            raise KeyError(eid)
    rs.bh.erfassen_geprueft("rechnung_entwurf_geaendert", {"entwurf_id": eid, "felder": {"positionen": _positionen(neu),
                                                                                         "projektzeiten": pz}},
                            von=von, pruefe=pruefe)
    a = _auftrag(rs.bh.eintraege(), x["auftrag"]) or {}
    merken = {k: v for k, v in (("verkauf_satz_cent", s), ("verkauf_km_cent", ks)) if v and a.get(k) != v}
    if merken:                                              # Satz je Auftrag merken (CEO: „je Auftrag aenderbar“)
        rs.bh.erfassen("auftrag_geaendert", {"nummer": x["auftrag"], "felder": merken}, von=von)
    return {"projektzeiten": pz, "positionen": len(neu)}


def _auftrag(eintraege: list[dict], nr: str) -> dict | None:
    from .beauftragung import AuftragBuch
    return AuftragBuch._falte(eintraege).get(nr)


def _zeile(z: dict) -> dict:
    return {k: z.get(k) for k in ("id", "datum", "von", "bis", "pause_min", "minuten", "taetigkeit", "km")}


def pruefe_festschreiben(x: dict, eintraege: list[dict]) -> None:
    """Unter der Sperre: nichts doppelt, und die Zeiten sind seit der Uebernahme nicht korrigiert worden."""
    pz = x.get("projektzeiten") or {}
    if not pz:
        return
    ids = {p.get("katalog_id") for p in x.get("positionen") or []}
    if (pz.get("zeilen") and ZEIT_ID not in ids) or (pz.get("km_zeilen") and KM_ID not in ids):
        raise ValueError("Projektzeiten sind gewaehlt, die Position fehlt aber -- Projektzeiten neu uebernehmen oder abwaehlen.")
    alle = falte_zeiten(eintraege)
    for z in pz.get("zeilen") or []:
        a = alle.get(z["id"])
        if not a or a["storniert"]:
            raise ValueError(f"Zeiteintrag vom {datum_de(z['datum'])} gibt es nicht mehr -- Projektzeiten neu uebernehmen.")
        if a.get("abgerechnet"):
            raise ValueError(f"Zeit vom {datum_de(z['datum'])} ist schon auf {a['abgerechnet']} abgerechnet.")
        if a.get("minuten") != z["minuten"]:
            raise ValueError(f"Zeit vom {datum_de(z['datum'])} wurde seit der Uebernahme geaendert -- Projektzeiten neu "
                             "uebernehmen.")
    for z in pz.get("km_zeilen") or []:
        a = alle.get(z["id"])
        if not a or a.get("km_abgerechnet"):
            raise ValueError(f"Fahrt vom {datum_de(z['datum'])} ist schon abgerechnet oder entfernt.")
        if sum(f.get("km") or 0 for f in a["fahrten"]) != z["km"]:
            raise ValueError(f"Fahrt vom {datum_de(z['datum'])} wurde geaendert -- Projektzeiten neu uebernehmen.")


def stundenzettel_pdf(r: dict, firmendaten: dict, logo=None) -> bytes:
    """Anlage „Stundenzettel“ zur Rechnung (nur Darstellung zusammengefasst): Zeilen der eingefrorenen Auswahl."""
    from fpdf import FPDF
    pz = r.get("projektzeiten") or {}
    from .beleg_pdf import DEJAVU, absender_zeile, hanserautisch_kopf
    uni = (DEJAVU / "DejaVuSans.ttf").exists() and (DEJAVU / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1
    pdf = FPDF(format="A4")
    S = "Helvetica"
    if uni:
        pdf.add_font("DejaVu", "", str(DEJAVU / "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", str(DEJAVU / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    pdf.set_margins(18, 14, 18)                                       # Tabelle 174 mm = Balkenbreite
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()
    y = hanserautisch_kopf(pdf, logo=logo, x=18, y=12, logo_breite=45)   # gleicher Kopf wie die Rechnung
    pdf.set_xy(pdf.l_margin, y + 4)
    pdf.set_font(S, "", 6.8)
    pdf.set_text_color(136, 136, 136)
    pdf.cell(0, 3.2, T(absender_zeile(firmendaten)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font(S, "B", 14)
    pdf.cell(0, 8, T(f"Anlage: Stundenzettel zu {r.get('nummer') or 'ENTWURF'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(S, "", 9)
    pdf.cell(0, 6, T(f"{firmendaten.get('firma') or firmendaten.get('name') or ''} · Auftrag {r.get('auftrag', '')}"
                           + (f" · {r['titel']}" if r.get("titel") else "")), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    spalten = [("Datum", 24), ("Ein", 14), ("Aus", 14), ("Pause", 16), ("Dauer", 18), ("Tätigkeit", 74), ("km", 14)]
    pdf.set_font(S, "B", 9)
    for t, w in spalten:
        pdf.cell(w, 7, T(t), border="B")
    pdf.ln()
    pdf.set_font(S, "", 9)
    km_ids = set(pz.get("km") or [])
    zeilen = pz.get("zeilen") or []
    for z in zeilen:
        werte = [datum_de(z["datum"]), z["von"], z["bis"], f"{z['pause_min']} min" if z.get("pause_min") else "",
                 _std_text(z["minuten"]), (z.get("taetigkeit") or "")[:48], str(z["km"]) if z["id"] in km_ids and z["km"] else ""]
        for (t, w), v in zip(spalten, werte):
            pdf.cell(w, 6, T(v), border="B")
        pdf.ln()
    pdf.set_font(S, "B", 9)
    m = sum(z["minuten"] for z in zeilen)
    km = sum(z["km"] for z in pz.get("km_zeilen") or [])
    pdf.cell(68, 7, "Summe")                                          # bis zur Spalte „Dauer“
    pdf.cell(18, 7, T(_std_text(m)))
    pdf.cell(74, 7, T(f"x {eur(pz.get('satz_cent') or 0)} = {eur(round(m * (pz.get('satz_cent') or 0) / 60))}"
                            if m else ""))
    pdf.cell(14, 7, str(km) if km else "")
    pdf.ln(10)
    pdf.set_font(S, "", 8)
    pdf.multi_cell(0, 4, T("Dauer = Aus - Ein - Pause. Berechnet wird die Summe laut Rechnung (auf 0,01 h gerundet)."))
    return bytes(pdf.output())


def mit_anlage(rechnung_pdf: bytes, r: dict, firmendaten: dict, logo=None) -> bytes:
    """Stundenzettel als Anlage an das Rechnungs-PDF haengen (nur zusammengefasst mit Zeiten)."""
    pz = r.get("projektzeiten") or {}
    if pz.get("darstellung") != "zusammen" or not pz.get("zeilen"):
        return rechnung_pdf
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for teil in (rechnung_pdf, stundenzettel_pdf(r, firmendaten, logo)):
        w.append(PdfReader(io.BytesIO(teil)))
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
