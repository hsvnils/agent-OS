"""Plattform-Auszahlungen mit Erzielt-Zeitraum (KUNDEN_FINANZEN Etappe 27, CEO 2026-09-30: „die Daten der Einnahmen
und die Zeitraeume auch tracken“).

Facebook (Meta) zahlt die Content-Monetarisierung gesammelt aus; jede Auszahlung besteht aus Posten mit eigenem
**Erzielt-Zeitraum** (meist ein Kalendermonat). Massgeblich ist das „Remittance“-PDF von Meta (die Meta-Oberflaeche
zeigte 2026 vorlaeufige, leicht abweichende Werte). Quellen je Einnahme-Beleg:
  1. von Hand erfasste Posten (Ereignis `eingang_posten`, z. B. wenn nur ein Screenshot vorliegt) -- haben Vorrang,
  2. sonst die Posten aus dem gespeicherten PDF-Text des Belegs (kein Datenwrite noetig).

Reine Information: die EUeR bleibt beim Zuflussprinzip (§ 11 EStG) und zaehlt den Bankeingang am Zahlungstag. Euro je
Posten = anteilig nach Verhaeltnis Bankeingang / Fremdwaehrungs-Summe der Auszahlung.
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta

_MONATE_EN = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                          "dec"), start=1)}
_D_EN = r"(\d{1,2})-([A-Za-z]{3})-(\d{4})"
_ZEILE = re.compile(r"^\s*(\d{8,})\s+" + _D_EN + r"\s*->\s*" + _D_EN + r"\s+(.*?)\s+(-?[\d,]*\d\.\d{2})\s*$", re.M)
_D_DE = r"(\d{1,2})\.(\d{1,2})\.(\d{4})"
_ZEILE_DE = re.compile(r"^\s*" + _D_DE + r"\s*(?:-|–|bis)\s*" + _D_DE + r"\s+(-?[\d.]*\d(?:,\d{1,2})?)\s*(?:\$|usd|eur|€)?\s*(.*)$",
                       re.I | re.M)


def _en(t: str, mon: str, j: str) -> str:
    return date(int(j), _MONATE_EN[mon.lower()], int(t)).isoformat()


def remittance_lesen(text: str) -> dict | None:
    """Meta-„Remittance“-PDF -> {plattform, zahlungs_id, datum, waehrung, betrag_cent, posten[]} oder None.
    Betraege in Cent der Originalwaehrung; die Summe der Posten muss zur Auszahlung passen."""
    t = text or ""
    if not re.search(r"(?i)meta platforms", t) or not re.search(r"(?i)remittance", t):
        return None
    nr = re.search(r"(?i)payment\s+number\s*:?\s*(\d{6,})", t)
    tag = re.search(r"(?i)payment\s+date\s*:?\s*" + _D_EN, t)
    wg = re.search(r"(?i)payment\s+currency\s*:?\s*([A-Z]{3})", t)
    betrag = re.search(r"(?i)payment\s+amount\s*:?\s*([\d,]*\d\.\d{2})", t)
    posten = []
    for m in _ZEILE.finditer(t):
        try:
            posten.append({"referenz": m.group(1), "von": _en(*m.group(2, 3, 4)), "bis": _en(*m.group(5, 6, 7)),
                           "betrag_cent": round(float(m.group(9).replace(",", "")) * 100),
                           "text": re.sub(r"\s+", " ", m.group(8)).strip()[:120]})
        except (KeyError, ValueError):
            continue
    if not posten:
        return None
    summe = round(float(betrag.group(1).replace(",", "")) * 100) if betrag else sum(p["betrag_cent"] for p in posten)
    return {"plattform": "Facebook", "zahlungs_id": nr.group(1) if nr else "",
            "datum": _en(*tag.groups()) if tag else "", "waehrung": wg.group(1).upper() if wg else "USD",
            "betrag_cent": summe, "posten": sorted(posten, key=lambda p: (p["von"], p["referenz"])),
            "stimmig": summe == sum(p["betrag_cent"] for p in posten), "quelle": "pdf"}


def posten_aus_text(zeilen: str) -> list[dict]:
    """Von Hand: je Zeile „01.11.2025-30.11.2025 98,87 [Text]“ -> Posten (Cent der Originalwaehrung)."""
    out = []
    for n, z in enumerate((zeilen or "").splitlines(), start=1):
        if not z.strip():
            continue
        m = _ZEILE_DE.match(z)
        if not m:
            raise ValueError(f"Zeile {n}: bitte „TT.MM.JJJJ-TT.MM.JJJJ Betrag“ (z. B. 01.11.2025-30.11.2025 98,87).")
        try:
            von = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            bis = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        except ValueError:
            raise ValueError(f"Zeile {n}: ungueltiges Datum.") from None
        if bis < von:
            raise ValueError(f"Zeile {n}: Ende liegt vor dem Anfang.")
        betrag = round(float(m.group(7).replace(".", "").replace(",", ".")) * 100)
        if betrag == 0:
            raise ValueError(f"Zeile {n}: Betrag fehlt.")
        out.append({"referenz": "", "von": von.isoformat(), "bis": bis.isoformat(), "betrag_cent": betrag,
                    "text": m.group(8).strip()[:120]})
    if not out:
        raise ValueError("Keine Posten angegeben.")
    return sorted(out, key=lambda p: p["von"])


def auszahlung(beleg: dict) -> dict | None:
    """Plattform-Daten eines Einnahme-Belegs: von Hand erfasste Posten vor PDF-Text."""
    if beleg.get("plattform"):
        return beleg["plattform"]
    return remittance_lesen(beleg.get("text") or "")


def _monatsanteile(von: str, bis: str, betrag: float) -> dict[str, float]:
    """Betrag tagesgenau auf die Kalendermonate des Zeitraums verteilen."""
    a, b = date.fromisoformat(von), date.fromisoformat(bis)
    tage = (b - a).days + 1
    out: dict[str, float] = {}
    d = a
    while d <= b:
        ende = min(b, date(d.year, d.month, monthrange(d.year, d.month)[1]))
        out[f"{d.year}-{d.month:02d}"] = out.get(f"{d.year}-{d.month:02d}", 0) + betrag * ((ende - d).days + 1) / tage
        d = ende + timedelta(days=1)
    return out


def auswertung(belege: list[dict], jahr: int) -> dict:
    """Uebersicht fuer die Finanzen: je Auszahlung (Zufluss) und erzielt je Monat (nach Zeitraum).
    `belege` = gefaltete Eingangsbelege (EingangStore._falte().values())."""
    liste, erzielt = [], {}
    for x in belege:
        f = x.get("felder") or {}
        if x.get("status") != "gebucht" or f.get("art") != "einnahme":
            continue
        a = auszahlung(x)
        if not a or not a.get("posten"):
            continue
        fremd = sum(p["betrag_cent"] for p in a["posten"]) or 1
        eur = f.get("betrag_cent") or 0
        zufluss = x.get("bezahlt_am") or f.get("rechnungsdatum", "")
        posten = []
        for p in a["posten"]:
            p_eur = eur * p["betrag_cent"] / fremd
            posten.append(p | {"eur_cent": round(p_eur)})
            if zufluss[:4] != str(jahr):                      # erzielt zaehlt nur, was in diesem Jahr zufloss
                continue
            for monat, teil in _monatsanteile(p["von"], p["bis"], 1.0).items():
                z = erzielt.setdefault(monat, {"monat": monat, "fremd_cent": 0.0, "eur_cent": 0.0})
                z["fremd_cent"] += p["betrag_cent"] * teil
                z["eur_cent"] += p_eur * teil
        liste.append({"nummer": x["nummer"], "plattform": a.get("plattform", ""), "zahlungs_id": a.get("zahlungs_id", ""),
                      "datum": a.get("datum") or f.get("rechnungsdatum", ""), "zufluss": zufluss,
                      "waehrung": a.get("waehrung", "USD"), "fremd_cent": sum(p["betrag_cent"] for p in a["posten"]),
                      "eur_cent": eur, "posten": posten, "quelle": a.get("quelle", ""),
                      "von": min(p["von"] for p in a["posten"]), "bis": max(p["bis"] for p in a["posten"])})
    liste.sort(key=lambda a: a["zufluss"])
    im_jahr = [a for a in liste if a["zufluss"][:4] == str(jahr)]
    monate = [{"monat": m, "fremd_cent": round(v["fremd_cent"]), "eur_cent": round(v["eur_cent"])}
              for m, v in sorted(erzielt.items())]
    return {"jahr": jahr, "auszahlungen": im_jahr,
            "ausgezahlt_eur_cent": sum(a["eur_cent"] for a in im_jahr),
            "ausgezahlt_fremd_cent": sum(a["fremd_cent"] for a in im_jahr),
            "erzielt": monate,
            "hinweis": "Erzielt-Zeitraum ist Information; die EUeR zaehlt den Bankeingang am Zahlungstag (§ 11 EStG)."}
