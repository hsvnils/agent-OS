"""Zahlungsbedingungen und Vorkasse (KUNDEN_FINANZEN_ROADMAP.md, Etappe 18, CEO 2026-09-30).

Je Angebot einstellbar und in Auftrag und Rechnung uebernommen (eingefroren wie die Positionen):

    {"ziel_tage": 14,                                    # Zahlungsziel der (Schluss-)Rechnung
     "vorkasse": {"art": "prozent", "prozent": 50} | {"art": "euro", "cent": 130000}
                 + {"frist_tage": 7} | {"frist_datum": "JJJJ-MM-TT"},
     "text": "..."}                                      # optionaler Zusatztext

Vorkasse wird pro Angebot entschieden (keine Standard-Vorkasse je Kunde). Die Vorkasse wird als eigene
Vorkasse-Rechnung gestellt; die Schlussrechnung zieht sie ab (`rechnungen.py`).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .beleg_pdf import cent, datum_de, eur, menge_text

ZIEL_STANDARD = 14
FRIST_STANDARD = 7                      # Tage nach Auftragsbestaetigung (CEO 2026-09-30)
ARTEN = ("prozent", "euro")
_MAX_TEXT = 500


def _ganz(v, feld: str, lo: int, hi: int) -> int:
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{feld}: ganze Zahl.") from None
    if not lo <= n <= hi:
        raise ValueError(f"{feld}: {lo} bis {hi}.")
    return n


def pruefen(roh, *, ziel_vorschlag: int | None = None) -> dict:
    """Eingabe pruefen/normalisieren. `None`/leer -> nur Zahlungsziel (Vorschlag aus dem Kunden, sonst 14 Tage)."""
    roh = roh if isinstance(roh, dict) else {}
    ziel = roh.get("ziel_tage")
    out = {"ziel_tage": _ganz(ziel, "Zahlungsziel (Tage)", 0, 120) if ziel not in (None, "")
           else (ziel_vorschlag if ziel_vorschlag is not None else ZIEL_STANDARD)}
    v = roh.get("vorkasse")
    if isinstance(v, dict) and v.get("art") not in (None, "", "keine"):
        if v["art"] not in ARTEN:
            raise ValueError("Vorkasse: Prozent oder Euro.")
        if v["art"] == "prozent":                  # Eingabe `wert` (Editor) oder schon normalisiert `prozent`
            try:
                w = float(str(v.get("prozent", v.get("wert"))).replace(",", "."))
            except (TypeError, ValueError):
                raise ValueError("Vorkasse: Prozentsatz als Zahl.") from None
            if not 0 < w <= 100:
                raise ValueError("Vorkasse: mehr als 0 und hoechstens 100 Prozent.")
            vk = {"art": "prozent", "prozent": round(w, 2)}
        else:                                       # Eingabe `wert` in Euro (Editor) oder schon normalisiert `cent`
            try:
                w = int(v["cent"]) if v.get("cent") not in (None, "") else cent(v.get("wert"))
            except (TypeError, ValueError):
                raise ValueError("Vorkasse: Betrag in Euro.") from None
            if w <= 0:
                raise ValueError("Vorkasse: Betrag muss groesser als 0 sein.")
            vk = {"art": "euro", "cent": w}
        if v.get("frist_datum"):
            try:
                vk["frist_datum"] = date.fromisoformat(str(v["frist_datum"])[:10]).isoformat()
            except ValueError:
                raise ValueError("Vorkasse: Frist-Datum ungueltig (JJJJ-MM-TT).") from None
        else:
            vk["frist_tage"] = (_ganz(v["frist_tage"], "Vorkasse-Frist (Tage)", 0, 90)
                                if v.get("frist_tage") not in (None, "") else FRIST_STANDARD)
        out["vorkasse"] = vk
    t = str(roh.get("text") or "").strip()[:_MAX_TEXT]
    if t:
        out["text"] = t
    return out


def vorkasse_cent(zb: dict | None, summe_cent: int) -> int:
    """Vorkasse-Betrag in Cent (Prozent kaufmaennisch gerundet, nie ueber der Summe)."""
    v = (zb or {}).get("vorkasse")
    if not v or summe_cent <= 0:
        return 0
    if v["art"] == "prozent":
        b = int((Decimal(summe_cent) * Decimal(str(v["prozent"])) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        b = int(v["cent"])
    return max(0, min(b, summe_cent))


def vorkasse_frist(zb: dict | None, ab_datum: date | str) -> str:
    """Faelligkeit der Vorkasse (ISO) ab dem Datum der Auftragsbestaetigung; '' ohne Vorkasse."""
    v = (zb or {}).get("vorkasse")
    if not v:
        return ""
    if v.get("frist_datum"):
        return v["frist_datum"]
    d = ab_datum if isinstance(ab_datum, date) else date.fromisoformat(str(ab_datum)[:10])
    return (d + timedelta(days=int(v.get("frist_tage", FRIST_STANDARD)))).isoformat()


def _ziel_satz(tage: int) -> str:
    return ("zahlbar sofort nach Rechnungsstellung ohne Abzug" if not tage
            else f"zahlbar innerhalb von {tage} Tagen nach Rechnungsstellung ohne Abzug")


def text(zb: dict | None, summe_cent: int, *, ab_datum: str = "") -> str:
    """Satz fuer Angebot/Auftragsbestaetigung. Mit `ab_datum` wird die Vorkasse-Frist als Datum genannt."""
    if not zb:
        return ""
    v = zb.get("vorkasse")
    vk = vorkasse_cent(zb, summe_cent)
    if v and vk:
        anteil = (f"{menge_text(v['prozent'])} % Vorkasse ({eur(vk)})" if v["art"] == "prozent" and vk < summe_cent
                  else f"Vorkasse des Gesamtbetrags ({eur(vk)})" if vk >= summe_cent else f"Vorkasse von {eur(vk)}")
        if v.get("frist_datum") or ab_datum:
            frist = f"bis zum {datum_de(vorkasse_frist(zb, ab_datum or date.today()))}"
        else:
            t = int(v.get("frist_tage", FRIST_STANDARD))
            frist = "sofort nach Auftragsbestätigung" if not t else f"bis {t} Tage nach Auftragsbestätigung"
        satz = f"Zahlungsbedingungen: {anteil}, zahlbar {frist} gegen Vorkasse-Rechnung"
        rest = summe_cent - vk
        satz += (f"; Restbetrag ({eur(rest)}) {_ziel_satz(zb.get('ziel_tage', ZIEL_STANDARD))}." if rest > 0 else ".")
    else:
        satz = f"Zahlungsbedingungen: {_ziel_satz(zb.get('ziel_tage', ZIEL_STANDARD))}."
    return " ".join(x for x in (satz, zb.get("text", "")) if x)


def kurz(zb: dict | None) -> str:
    """Kurzform fuer Listen/Detail in LUNA-OS, z. B. „50 % Vorkasse · 14 Tage“."""
    if not zb:
        return ""
    v = zb.get("vorkasse")
    teile = []
    if v:
        teile.append((f"{menge_text(v['prozent'])} %" if v["art"] == "prozent" else eur(v["cent"])) + " Vorkasse")
    teile.append(f"{zb.get('ziel_tage', ZIEL_STANDARD)} Tage")
    return " · ".join(teile)
