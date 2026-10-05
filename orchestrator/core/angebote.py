"""Angebote (KUNDEN_FINANZEN_ROADMAP.md, Etappe 3): Angebot `AN-JJJJ-NNNN` zu Firma `K-` und Ansprechpartner `AP-`,
Positionen in Cent, Status, PDF-Ablage.

Ereignisse in der Buchhaltungs-Kette (`core/buchhaltung.py`), nichts wird ueberschrieben:
- `angebot_angelegt` / `angebot_geaendert` -- nur im Status **entwurf** aenderbar;
- `angebot_pdf_abgelegt` -- das PDF, das als Mail-Entwurf rausgeht, wird als Geschaeftsbrief (6 Jahre) abgelegt,
  mit Hash des Inhalts, damit spaeter klar ist, welcher Stand verschickt wurde;
- `angebot_status` -- versendet (friert den Inhalt ein), angenommen, abgelehnt. „abgelaufen" wird nicht gespeichert,
  sondern aus `gueltig_bis` abgeleitet.
Senden bleibt beim CEO (Oeffentlichkeit): LUNA-OS legt nur einen Gmail-**Entwurf** an.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

from pathlib import Path

from .beleg_pdf import (HINWEIS_19, beleg_pdf, cent, datum_de, eur, hanserautisch_pdf, menge, menge_text,
                        positions_summe)
from .buchhaltung import Buchhaltung, jetzt
from .katalog import OMR, kalkulation_texte, tkp_preis
from .kunden import KundenStore
from . import zahlungsbedingungen as zb

STATUS = ("entwurf", "versendet", "angenommen", "abgelehnt")
KOPF_FELDER = ("firma", "ansprechpartner", "titel", "datum", "gueltig_bis", "einleitung", "schluss", "nachfassen_tage",
               "zuschlaege", "rabatt_prozent", "layout", "bloecke", "ware",   # 3b; „ware“ = Barter (Etappe 12)
               "zahlung",                                                     # Zahlungsbedingungen/Vorkasse (Etappe 18)
               "praesentation")                                               # Canva-Link DE/EN (ANGEBOT_PRAESENTATION)
PRAES_SPRACHEN = ("de", "en", "")
LAYOUTS = ("hanserautisch", "standard")
SCHALTER = ("zeige_kalkulation", "zeige_kennzahlen", "tkp_zeigen", "omr_zeigen")
GUELTIG_TAGE = 14                                                           # CEO 2026-09-27 (wie im Generator)
ORT = "Tangstedt"
MAX_POSITIONEN = 60
_MAX = 4000


def _iso(d, feld: str) -> str:
    try:
        return date.fromisoformat(str(d)[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{feld}: ungueltiges Datum (JJJJ-MM-TT).") from None


def _positionen(roh) -> list[dict]:
    if not isinstance(roh, list) or not roh:
        raise ValueError("Mindestens eine Position noetig.")
    if len(roh) > MAX_POSITIONEN:
        raise ValueError(f"Hoechstens {MAX_POSITIONEN} Positionen.")
    out = []
    for i, p in enumerate(roh, 1):
        if not isinstance(p, dict):
            raise ValueError(f"Position {i}: ungueltig.")
        text = str(p.get("beschreibung") or "").strip()[:_MAX]
        if not text:
            raise ValueError(f"Position {i}: Beschreibung fehlt.")
        try:
            m = menge(p.get("menge", 1))
            ep = (int(p["einzelpreis_cent"]) if "einzelpreis_cent" in p
                  else cent(p.get("einzelpreis") or ("0" if p.get("provision") else "")))
        except ValueError as exc:
            raise ValueError(f"Position {i}: {exc}") from None
        if ep < 0:
            raise ValueError(f"Position {i}: negativer Preis.")
        pos = {"beschreibung": text, "menge": format(m, "f"), "einheit": str(p.get("einheit") or "").strip()[:30],
               "einzelpreis_cent": ep}
        if p.get("kontakte") not in (None, "", 0, "0") and (p.get("tkp_cent") or p.get("tkp")):   # Etappe 16: TKP
            try:
                kontakte = int(p["kontakte"])
                tkp = int(p["tkp_cent"]) if p.get("tkp_cent") else cent(p.get("tkp"))
                prod = int(p.get("produktion_cent") or 0)
            except (TypeError, ValueError):
                raise ValueError(f"Position {i}: Kontakte/TKP ungueltig.") from None
            if not (0 < kontakte <= 100_000_000 and 100 <= tkp <= 50_000 and 0 <= prod <= 10_000_000):
                raise ValueError(f"Position {i}: TKP zwischen 1 und 500 €, Kontakte/Produktion im Rahmen.")
            pos |= {"kontakte": kontakte, "tkp_cent": tkp, "produktion_cent": prod,
                    "einzelpreis_cent": tkp_preis(kontakte, tkp, prod)}               # Preis folgt immer dem TKP
            for k in ("tkp_min_cent", "tkp_max_cent"):
                if str(p.get(k) or "").isdigit():
                    pos[k] = int(p[k])
            if str(p.get("omr") or "") in OMR["werte"]:
                pos["omr"] = p["omr"]
        if p.get("provision"):                                     # Etappe 23: Provisionsmodell (Affiliate)
            pos |= _provision(p["provision"], i)
        for k, n in (("detail", 600), ("katalog_id", 30), ("gruppe", 60)):   # Etappe 3b: aus dem Leistungskatalog
            if str(p.get(k) or "").strip():
                pos[k] = str(p[k]).strip()[:n]
        if p.get("gruppe_farbe") == "rot":
            pos["gruppe_farbe"] = "rot"
        out.append(pos)
    return out


PROVISION_ARTEN = ("stueck", "prozent")


def _provision(roh, i: int) -> dict:
    """Etappe 23: Provision statt Festpreis -- „5,00 EUR je verkauftem Artikel“ oder „10 % vom vermittelten Umsatz“.
    Ohne Abrechnung (Angebot, Auftrag) ist der Betrag 0 und zaehlt nicht zur Summe; mit Abrechnung (verkaufte Stueck
    bzw. Umsatz) rechnet LUNA den Euro-Betrag aus. Nimmt Eingaben (`wert`, `abrechnung`) und gespeicherte Felder an."""
    if not isinstance(roh, dict) or roh.get("art") not in PROVISION_ARTEN:
        raise ValueError(f"Position {i}: Provision je Stueck oder in Prozent.")
    out = {"art": roh["art"]}
    try:
        if roh["art"] == "stueck":
            out["satz_cent"] = int(roh["satz_cent"]) if roh.get("satz_cent") not in (None, "") else cent(roh.get("wert"))
            if not 0 < out["satz_cent"] <= 10_000_000:
                raise ValueError
        else:
            out["prozent"] = round(float(str(roh.get("prozent", roh.get("wert"))).replace(",", ".")), 2)
            if not 0 < out["prozent"] <= 100:
                raise ValueError
    except (TypeError, ValueError):
        raise ValueError(f"Position {i}: Provisionssatz ungueltig (Euro je Stueck > 0 bzw. 0-100 %).") from None
    ab = roh.get("stueck" if roh["art"] == "stueck" else "basis_cent")
    if ab in (None, ""):
        ab = roh.get("abrechnung")
        if ab not in (None, "") and roh["art"] == "prozent":
            try:
                ab = cent(ab)
            except ValueError:
                raise ValueError(f"Position {i}: Umsatz fuer die Provision ungueltig.") from None
    if ab in (None, ""):
        return {"menge": "1", "einzelpreis_cent": 0, "provision": out}           # noch nicht abgerechnet
    try:
        ab = int(str(ab).replace(".", "")) if roh["art"] == "stueck" else int(ab)
    except (TypeError, ValueError):
        raise ValueError(f"Position {i}: verkaufte Stueck als ganze Zahl.") from None
    if ab < 0:
        raise ValueError(f"Position {i}: Abrechnung darf nicht negativ sein.")
    if roh["art"] == "stueck":
        out["stueck"] = ab
        return {"menge": str(ab) if ab else "1", "einzelpreis_cent": out["satz_cent"] if ab else 0, "provision": out}
    from decimal import ROUND_HALF_UP, Decimal
    out["basis_cent"] = ab
    betrag = int((Decimal(ab) * Decimal(str(out["prozent"])) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {"menge": "1", "einzelpreis_cent": betrag, "provision": out}


def provision_abgerechnet(p: dict) -> bool:
    pr = p.get("provision") or {}
    return bool(pr) and ("stueck" in pr or "basis_cent" in pr)


def provision_text(pr: dict) -> str:
    """„5,00 € je verkauftem Artikel“ / „10 % vom vermittelten Umsatz“ -- mit Abrechnung die Rechnung dazu."""
    if not pr:
        return ""
    if pr["art"] == "stueck":
        satz = f"{eur(pr['satz_cent'])} je verkauftem Artikel"
        return satz + (f" · abgerechnet: {pr['stueck']} verkaufte Artikel × {eur(pr['satz_cent'])}" if "stueck" in pr else "")
    satz = f"{menge_text(pr['prozent'])} % vom vermittelten Umsatz"
    return satz + (f" · abgerechnet: {menge_text(pr['prozent'])} % von {eur(pr['basis_cent'])} Umsatz" if "basis_cent" in pr else "")


def pdf_posten(p: dict) -> dict:
    """Zusatzfelder fuer die PDF-Zeile einer Provisionsposition (Betragstext statt 0,00 EUR, Modell im Detail)."""
    pr = p.get("provision")
    if not pr:
        return {}
    detail = " · ".join(x for x in (p.get("detail"), provision_text(pr)) if x)
    if provision_abgerechnet(p):
        return {"detail": detail}
    kurz = f"{eur(pr['satz_cent'])}/Stk." if pr["art"] == "stueck" else f"{menge_text(pr['prozent'])} %"
    return {"detail": detail, "betrag_text": "nach Abrechnung", "einzel_text": kurz, "gesamt_text": "nach Abr.",
            "menge": None}


def pdf_posten_standard(p: dict) -> dict:
    """Wie `pdf_posten`, fuer das schlichte Layout (Modell in der Beschreibung, Texte in den Betragsspalten)."""
    pr = p.get("provision")
    if not pr:
        return {}
    extra = {"beschreibung": f"{p['beschreibung']} – {provision_text(pr)}"}
    if not provision_abgerechnet(p):
        extra |= {k: v for k, v in pdf_posten(p).items() if k in ("einzel_text", "gesamt_text")}
    return extra


def _kopf(daten: dict) -> dict:
    out = {}
    for k in KOPF_FELDER:
        if k not in daten:
            continue
        v = daten[k]
        if k in ("datum", "gueltig_bis"):
            out[k] = _iso(v, "Datum" if k == "datum" else "Gueltig bis")
        elif k == "zuschlaege":
            out[k] = _zuschlaege(v)
        elif k == "rabatt_prozent":
            try:
                r = float(str(v or 0).replace(",", "."))
            except ValueError:
                raise ValueError("Rabatt: Zahl in Prozent.") from None
            if not 0 <= r <= 90:
                raise ValueError("Rabatt: 0 bis 90 Prozent.")
            out[k] = round(r, 2)
        elif k == "layout":
            if v not in LAYOUTS:
                raise ValueError(f"Layout muss einer von {', '.join(LAYOUTS)} sein.")
            out[k] = v
        elif k == "bloecke":
            out[k] = _bloecke(v)
        elif k == "ware":
            out[k] = _ware(v)
        elif k == "zahlung":
            out[k] = zb.pruefen(v)
        elif k == "praesentation":
            sprache = (v.get("sprache") if isinstance(v, dict) else v) or ""
            if sprache not in PRAES_SPRACHEN:
                raise ValueError("Praesentation: de, en oder leer.")
            out[k] = sprache                                   # wird im Store zum Link aufgeloest (_praesentation)
        elif k == "nachfassen_tage":
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise ValueError("Nachfassen: ganze Zahl (Tage).") from None
            if not 1 <= n <= 90:
                raise ValueError("Nachfassen: 1 bis 90 Tage.")
            out[k] = n
        else:
            out[k] = str(v or "").strip()[:_MAX]
    if "firma" in out:
        out["firma"] = out["firma"].upper()
    if "ansprechpartner" in out:
        out["ansprechpartner"] = out["ansprechpartner"].upper()
    return out


def _ware(roh) -> dict:
    """Barter (Etappe 12): Teil der Gegenleistung in Ware -- {text, wert_cent}; leer = reines Geldgeschaeft."""
    if not roh:
        return {}
    if not isinstance(roh, dict):
        raise ValueError("Gegenleistung in Ware ungueltig.")
    try:
        w = int(roh["wert_cent"]) if "wert_cent" in roh and roh.get("wert") in (None, "") else cent(roh.get("wert") or 0)
    except (ValueError, TypeError):
        raise ValueError("Warenwert ungueltig.") from None
    if w < 0:
        raise ValueError("Warenwert darf nicht negativ sein.")
    if not w:
        return {}
    text = str(roh.get("text") or "").strip()[:300]
    if not text:
        raise ValueError("Welche Ware? Bitte die Gegenleistung in Ware beschreiben.")
    return {"text": text, "wert_cent": w}


def ware_geld(summe_cent: int, ware: dict | None) -> tuple[int, int]:
    """-> (Warenanteil, Geldanteil) in Cent; der Warenwert darf die Summe nicht uebersteigen."""
    w = int((ware or {}).get("wert_cent") or 0)
    if w > summe_cent:
        raise ValueError(f"Warenwert {eur(w)} ist hoeher als die Gesamtsumme {eur(summe_cent)}.")
    return w, summe_cent - w


def ware_hinweis(summe_cent: int, ware: dict | None, *, rechnung: bool = False) -> list[str]:
    """PDF-Text zur Gegenleistung in Ware (Angebot/Auftrag bzw. Rechnung mit beziffertem Entgelt, § 34a UStDV)."""
    w, g = ware_geld(summe_cent, ware)
    if not w:
        return []
    if rechnung:
        return [f"Entgelt {eur(summe_cent)}, davon Sachleistung (tauschähnlicher Umsatz): {ware['text']} im Wert von "
                f"{eur(w)}" + (f"; in Geld zu zahlen: {eur(g)}." if g else "; kein Geldbetrag zu zahlen – das Entgelt wird "
                               "durch die Lieferung der Ware ausgeglichen.")]
    return [f"Gegenleistung: {eur(w)} in Ware ({ware['text']})" + (f" und {eur(g)} in Geld." if g else
                                                                   " – vollständig in Ware (Barter).")]


def _zuschlaege(roh) -> list[dict]:
    if not isinstance(roh, list):
        raise ValueError("Zuschlaege: Liste erwartet.")
    out, ids = [], set()
    for z in roh[:12]:
        if not isinstance(z, dict):
            raise ValueError("Zuschlag ungueltig.")
        try:
            pr = float(str(z.get("prozent")).replace(",", "."))
        except ValueError:
            raise ValueError("Zuschlag: Prozent fehlt.") from None
        name = str(z.get("name") or "").strip()[:120]
        if not name or not 0 < pr <= 200:
            raise ValueError("Zuschlag: Name und 0-200 Prozent noetig.")
        zid = str(z.get("id") or name).strip()[:30]
        if zid in ids:
            continue
        ids.add(zid)
        out.append({"id": zid, "name": name, "prozent": round(pr, 2)})
    return out


def _bloecke(roh) -> dict:
    """Textbausteine des Hanserautisch-Layouts -- beim Anlegen aus dem Katalog kopiert (eingefroren)."""
    if not isinstance(roh, dict):
        raise ValueError("Textbausteine ungueltig.")
    t = lambda x, n=2000: str(x if x is not None else "").strip()[:n]
    return {"untertitel": t(roh.get("untertitel"), 80), "intro": t(roh.get("intro")),
            "kalkulation_titel": t(roh.get("kalkulation_titel"), 120),
            "kalkulation": [t(x, 1500) for x in (roh.get("kalkulation") or []) if t(x)][:6],
            "kalkulation_beispiel": t(roh.get("kalkulation_beispiel"), 400),
            "kennzahlen": [[t(a, 20), t(b, 60)] for a, b in (roh.get("kennzahlen") or []) if t(a)][:6],
            "kennzahlen_quelle": t(roh.get("kennzahlen_quelle"), 800), "fuss": t(roh.get("fuss")),
            "kontakt": t(roh.get("kontakt"), 120),
            "zeige_kalkulation": roh.get("zeige_kalkulation", True) is not False,
            "zeige_kennzahlen": roh.get("zeige_kennzahlen", True) is not False,
            # Etappe 16: Rechnung Kontakte x TKP und OMR-Vergleich (mit Link) je Angebot an-/abwaehlbar
            "tkp_zeigen": roh.get("tkp_zeigen", True) is not False,
            "omr_zeigen": roh.get("omr_zeigen", False) is True}


def summen(positionen: list[dict], zuschlaege: list[dict], rabatt_prozent: float) -> dict:
    """Summe Formate + Zuschlaege (Prozent auf die Summe aller Formate, wie im Generator) - Paketrabatt, in Cent."""
    from decimal import ROUND_HALF_UP, Decimal
    rund = lambda d: int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    formate = sum(positions_summe(p["menge"], p["einzelpreis_cent"]) for p in positionen if not p.get("provision"))
    zu = [(z["name"], z["prozent"], rund(Decimal(formate) * Decimal(str(z["prozent"])) / 100)) for z in zuschlaege]
    zwischen = formate + sum(c for _, _, c in zu)
    rabatt = (rabatt_prozent, rund(Decimal(zwischen) * Decimal(str(rabatt_prozent)) / 100)) if rabatt_prozent else None
    out = {"formate_cent": formate, "zuschlaege": zu, "rabatt": rabatt, "gesamt_cent": zwischen - (rabatt[1] if rabatt else 0)}
    prov = [p for p in positionen if p.get("provision")]          # Etappe 23: Provision ohne Zuschlag/Rabatt, danach
    if prov:
        out["provision_cent"] = sum(positions_summe(p["menge"], p["einzelpreis_cent"]) for p in prov)
        out["provision_offen"] = any(not provision_abgerechnet(p) for p in prov)
        out["gesamt_cent"] += out["provision_cent"]
    return out


def anrede_moin(ap: dict | None, firma_name: str) -> str:
    """Wie im Generator: „Moin Anna,“ bzw. „Moin Herr Muster,“ oder „Moin liebes Team von …,“."""
    vor, nach = ((ap or {}).get("vorname") or "").strip(), ((ap or {}).get("nachname") or "").strip()
    if vor and not vor.lower().rstrip(".") in ("herr", "frau", "dr", "prof"):
        return f"Moin {vor.split()[0]},"
    if vor or nach:
        return f"Moin {' '.join(x for x in (vor, nach) if x)},"
    return f"Moin liebes Team von {firma_name}," if firma_name else "Moin,"


def inhalt_hash(a: dict) -> str:
    """Hash des druckrelevanten Inhalts (welcher Stand ging raus?)."""
    teil = {k: a.get(k) for k in KOPF_FELDER                      # leeres „ware“ zaehlt nicht (alte Staende gleich)
            if k != "nachfassen_tage" and (k != "ware" or a.get("ware"))} | {"positionen": a.get("positionen")}
    return hashlib.sha256(json.dumps(teil, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class AngebotStore:
    def __init__(self, bh: Buchhaltung, kunden: KundenStore, katalog=None):
        self.bh = bh
        self.kunden = kunden
        self.katalog = katalog                                  # Etappe 3b: Textbausteine fuer neue Angebote

    # -- Faltung -------------------------------------------------------------------------------------------------

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t}
            if t == "angebot_angelegt":
                out[d["nummer"]] = {**{k: d.get(k) for k in KOPF_FELDER}, "nummer": d["nummer"],
                                    "positionen": d["positionen"], "status": "entwurf", "angelegt": e["ts"],
                                    "pdfs": [], "verlauf": [spur]}
            elif t == "auftrag_angelegt" and d.get("angebot") in out:     # Verknuepfung Angebot -> Auftrag (AB-)
                out[d["angebot"]]["auftrag"] = d["nummer"]
                out[d["angebot"]]["verlauf"].append(spur | {"auftrag": d["nummer"]})
            elif d.get("nummer") not in out:
                continue
            elif t == "angebot_geaendert":
                a = out[d["nummer"]]
                a.update(d.get("felder", {}))
                a["verlauf"].append(spur | {"felder": sorted(d.get("felder", {}))})
            elif t == "angebot_pdf_abgelegt":
                a = out[d["nummer"]]
                a["pdfs"].append({k: d.get(k) for k in ("pfad", "sha256", "inhalt", "entwurf_id", "an")} | {"ts": e["ts"]})
                a["verlauf"].append(spur | {"an": d.get("an", "")})
            elif t == "angebot_antwort":                     # Kundenantwort im Mailverlauf (Etappe 4 Google-Konto)
                a = out[d["nummer"]]
                a.setdefault("antworten", []).append({k: d.get(k) for k in ("message_id", "von", "datum", "vorschau")}
                                                     | {"ts": e["ts"]})
                a["verlauf"].append(spur | {"mail_id": d.get("message_id", ""), "richtung": "ein",
                                            "mail_von": d.get("von", ""), "vorschau": d.get("vorschau", "")})
            elif t == "angebot_mail_archiviert":             # Original-Mail (.eml) als Geschaeftsbrief abgelegt
                out[d["nummer"]].setdefault("mail_archiv", {})[d["message_id"]] = {k: d.get(k) for k in ("pfad", "richtung")}
            elif t == "angebot_nachgefasst":                 # CEO hat nachgefasst (Hauptseite) -> Nachfass-Termin weg
                a = out[d["nummer"]]
                a["nachgefasst_am"] = e["ts"]
                a["verlauf"].append(spur | {"grund": d.get("notiz", "")})
            elif t == "angebot_erinnerungen":                # nachgeholte Kalender-Erinnerungen (BF-33)
                a = out[d["nummer"]]
                a["versendet_termine"] = a.get("versendet_termine", []) + d.get("termine", [])
                a["verlauf"].append(spur)
            elif t == "angebot_status":
                a = out[d["nummer"]]
                a["status"] = d["status"]
                a[d["status"] + "_am"] = e["ts"]
                for k in ("termine", "grund", "pdf", "mail"):
                    if d.get(k):
                        a[f"{d['status']}_{k}"] = d[k]
                m = d.get("mail") or {}
                a["verlauf"].append(spur | {"status": d["status"], "grund": d.get("grund", "")}
                                    | ({"mail_id": m.get("message_id", ""), "richtung": "aus", "mail_an": m.get("an", ""),
                                        "betreff": m.get("betreff", "")} if m.get("message_id") else {}))
        return out

    @staticmethod
    def _anreichern(a: dict, heute: date | None = None) -> dict:
        heute = heute or jetzt().date()
        pos = [p | {"gesamt_cent": positions_summe(p["menge"], p["einzelpreis_cent"])} for p in a["positionen"]]
        sm = summen(a["positionen"], a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0)
        anzeige = a["status"]
        if anzeige == "versendet" and a.get("gueltig_bis") and date.fromisoformat(a["gueltig_bis"]) < heute:
            anzeige = "abgelaufen"
        w = min(int((a.get("ware") or {}).get("wert_cent") or 0), sm["gesamt_cent"])
        return a | {"positionen": pos, "summe_cent": sm["gesamt_cent"], "summen": sm, "anzeige_status": anzeige,
                    "ware_cent": w, "geld_cent": sm["gesamt_cent"] - w,
                    "layout": a.get("layout") or "standard", "inhalt": inhalt_hash(a)}

    # -- Lesen ---------------------------------------------------------------------------------------------------

    def liste(self, *, firma: str = "") -> list[dict]:
        firmen = {f["nummer"]: f["name"] for f in self.kunden.firmen()}
        out = []
        for a in self._falte(self.bh.eintraege()).values():
            if firma and a["firma"] != firma.upper():
                continue
            r = self._anreichern(a)
            out.append({k: r[k] for k in ("nummer", "firma", "ansprechpartner", "titel", "datum", "gueltig_bis",
                                          "status", "anzeige_status", "summe_cent")} | {"firma_name": firmen.get(a["firma"], "")})
        return sorted(out, key=lambda x: x["nummer"], reverse=True)

    def angebot(self, nummer: str) -> dict | None:
        a = self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())
        return self._anreichern(a) if a else None

    # -- Schreiben -----------------------------------------------------------------------------------------------

    def _pruefe_bezug(self, eintraege, kopf: dict):
        firmen, aps = KundenStore._falte(eintraege)
        if kopf.get("firma") not in firmen:
            raise KeyError(kopf.get("firma") or "Firma")
        ap = kopf.get("ansprechpartner")
        if ap and (ap not in aps or aps[ap]["firma"] != kopf["firma"]):
            raise ValueError(f"Ansprechpartner {ap} gehoert nicht zu {kopf['firma']}.")

    def anlegen(self, daten: dict, *, von: str = "") -> dict:
        if not isinstance(daten, dict):
            raise ValueError("Ungueltige Eingabe.")
        heute = jetzt().date()
        kopf = {"datum": heute.isoformat(), "gueltig_bis": (heute + timedelta(days=GUELTIG_TAGE)).isoformat(),
                "nachfassen_tage": 7, "ansprechpartner": "", "titel": "", "einleitung": "", "schluss": "",
                "zuschlaege": [], "rabatt_prozent": 0, "layout": "hanserautisch" if self.katalog else "standard"}
        kopf.update(_kopf(daten))
        self._ziel_vorschlag(kopf, daten.get("zahlung"), kopf.get("firma") or "")
        kopf["praesentation"] = self._praesentation(kopf.get("praesentation", "de"))
        if kopf["layout"] == "hanserautisch" and "bloecke" not in kopf:
            kopf["bloecke"] = _bloecke(self.katalog.laden()["texte"] if self.katalog else {})
        _schalter(kopf, daten)
        if kopf["gueltig_bis"] < kopf["datum"]:
            raise ValueError("Gueltig bis liegt vor dem Angebotsdatum.")
        pos = _positionen(daten.get("positionen"))
        jahr = int(kopf["datum"][:4])
        ev = self.bh.mit_nummer("AN", "angebot_angelegt", kopf | {"positionen": pos}, jahr=jahr,
                                bezug=kopf["firma"], von=von, pruefe=lambda e: self._pruefe_bezug(e, kopf))
        return {"nummer": ev["daten"]["nummer"]}

    def _praesentation(self, sprache: str) -> dict:
        """Sprache -> eingefrorener Link {sprache, url, text} aus dem Katalog (spaetere Katalogaenderung aendert nichts)."""
        if not sprache:
            return {}
        from .katalog import STANDARD
        t = self.katalog.laden()["texte"] if self.katalog else STANDARD["texte"]
        url = t.get(f"praesentation_{sprache}") or ""
        return {"sprache": sprache, "url": url, "text": t.get(f"praesentation_text_{sprache}") or url} if url else {}

    def _ziel_vorschlag(self, kopf: dict, roh, firma: str) -> None:
        """Etappe 18: kein/leeres Zahlungsziel -> aus den Kundendaten (sonst 14 Tage)."""
        if "zahlung" in kopf and str((roh or {}).get("ziel_tage") if isinstance(roh, dict) else "").strip():
            return
        ziel = (self.kunden.firma(firma) or {}).get("zahlungsziel_tage")
        kopf["zahlung"] = zb.pruefen(roh, ziel_vorschlag=ziel)

    def aendern(self, nummer: str, daten: dict, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        if not isinstance(daten, dict):
            raise ValueError("Ungueltige Eingabe.")
        neu = _kopf(daten)
        if "praesentation" in neu:
            neu["praesentation"] = self._praesentation(neu["praesentation"])
        if "zahlung" in neu:
            firma = neu.get("firma") or (self.angebot(nummer) or {}).get("firma") or ""
            self._ziel_vorschlag(neu, daten.get("zahlung"), firma)
        schalter = {k: daten[k] for k in SCHALTER if k in daten}
        if "positionen" in daten:
            neu["positionen"] = _positionen(daten["positionen"])
        diff: dict = {}

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] != "entwurf":
                raise ValueError(f"{nummer} ist {a['status']} und kann nicht mehr geaendert werden.")
            if schalter or (neu.get("layout") == "hanserautisch" and not a.get("bloecke") and "bloecke" not in neu):
                basis = {"bloecke": neu.get("bloecke") or a.get("bloecke")
                         or _bloecke(self.katalog.laden()["texte"] if self.katalog else {})}
                _schalter(basis, schalter)
                neu["bloecke"] = basis["bloecke"]
            diff.update({k: v for k, v in neu.items() if a.get(k) != v})
            rest = a | diff
            if rest["gueltig_bis"] < rest["datum"]:
                raise ValueError("Gueltig bis liegt vor dem Angebotsdatum.")
            if {"firma", "ansprechpartner"} & set(diff):
                self._pruefe_bezug(eintraege, rest)
            if not diff:
                raise _Nichts()

        try:
            self.bh.erfassen_geprueft("angebot_geaendert", {"nummer": nummer, "felder": diff}, von=von, pruefe=pruefe)
        except _Nichts:
            return {"geaendert": []}
        return {"geaendert": sorted(diff)}

    def teile(self, a: dict, firmendaten: dict) -> dict:
        """Texte und Kopfdaten fuer PDF und Belegblatt (DIGITALER_BELEG D2) -- je Layout wie im PDF."""
        f = self.kunden.firma(a["firma"]) or {}
        ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
        hinweise = ([HINWEIS_19] + ware_hinweis(a["summe_cent"], a.get("ware"))
                    + [x for x in [zb.text(a.get("zahlung"), a["geld_cent"])] if x]
                    + [f"Dieses Angebot ist gültig bis {datum_de(a['gueltig_bis'])}."])
        infos = [("Datum", datum_de(a["datum"])), ("Angebot", a["nummer"]), ("Gültig bis", datum_de(a["gueltig_bis"])),
                 ("Kundennummer", a["firma"])]
        if a["layout"] == "hanserautisch":
            b = a.get("bloecke") or _bloecke({})
            texte = kalkulation_texte(b, formate=a["positionen"], tkp_zeigen=b.get("tkp_zeigen", True),
                                      omr_zeigen=b.get("omr_zeigen", False))
            zeigen = b.get("zeige_kalkulation", True) or b.get("omr_zeigen", False)
            return {"firma": f, "ap": ap, "anrede": anrede_moin(ap, f.get("name", "")), "praesentation": a.get("praesentation") or {},
                    "einleitung": a.get("einleitung") or b.get("intro", ""), "hinweise": hinweise, "infos": infos,
                    "untertitel": a.get("titel") or b.get("untertitel", ""), "schluss": "",
                    "kalkulation": ({"titel": texte.get("kalkulation_titel", ""), "absaetze": texte.get("kalkulation") or [],
                                     "beispiel": texte.get("kalkulation_beispiel", "")} if zeigen and texte.get("kalkulation") else None)}
        ap_name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
        anrede = f"Guten Tag {ap_name}," if ap_name else "Sehr geehrte Damen und Herren,"
        einleitung = a.get("einleitung") or (f"{anrede}\n\nvielen Dank für Ihr Interesse. Gerne unterbreiten wir "
                                             "Ihnen folgendes Angebot" + (f" zu „{a['titel']}“" if a.get("titel") else "") + ":")
        schluss = a.get("schluss") or ("Wir freuen uns auf Ihre Rückmeldung.\n\nMit freundlichen Grüßen\n"
                                       + (firmendaten.get("inhaber") or firmendaten.get("firma") or ""))
        return {"firma": f, "ap": ap, "anrede": "", "einleitung": einleitung, "hinweise": hinweise, "infos": infos,
                "untertitel": a.get("titel") or "", "schluss": schluss, "kalkulation": None,
                "praesentation": a.get("praesentation") or {}}

    def pdf(self, nummer: str, firmendaten: dict) -> bytes:
        a = self.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        f = self.kunden.firma(a["firma"]) or {}
        ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
        if a["layout"] == "hanserautisch":
            return self._pdf_hanserautisch(a, f, ap, firmendaten)
        ap_name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
        empfaenger = [f.get("name", ""), f"z. Hd. {ap_name}" if ap_name else "", f.get("strasse", ""),
                      f"{f.get('plz') or ''} {f.get('ort') or ''}".strip(),
                      f.get("land", "") if (f.get("land") or "").lower() not in ("", "deutschland", "de") else ""]
        anrede = f"Guten Tag {ap_name}," if ap_name else "Sehr geehrte Damen und Herren,"
        einleitung = a.get("einleitung") or (f"{anrede}\n\nvielen Dank für Ihr Interesse. Gerne unterbreiten wir "
                                             "Ihnen folgendes Angebot" + (f" zu „{a['titel']}“" if a.get("titel") else "") + ":")
        schluss = a.get("schluss") or ("Wir freuen uns auf Ihre Rückmeldung.\n\nMit freundlichen Grüßen\n"
                                       + (firmendaten.get("inhaber") or firmendaten.get("firma") or ""))
        return beleg_pdf(
            art="Angebot", nummer=a["nummer"], firma=firmendaten, empfaenger=empfaenger,
            infos=[("Datum", datum_de(a["datum"])), ("Gültig bis", datum_de(a["gueltig_bis"])),
                   ("Kundennummer", a["firma"]), ("Ansprechpartner", a.get("ansprechpartner", ""))],
            einleitung=einleitung, positionen=[x | pdf_posten_standard(x) for x in a["positionen"]], summe_cent=a["summe_cent"],
            summen_zeilen=_summen_zeilen(a["summen"]),
            hinweise=[HINWEIS_19] + ware_hinweis(a["summe_cent"], a.get("ware"))
            + [zb.text(a.get("zahlung"), a["geld_cent"]), f"Dieses Angebot ist gültig bis {datum_de(a['gueltig_bis'])}."],
            schluss=schluss, link=_link(a))

    def _pdf_hanserautisch(self, a: dict, f: dict, ap: dict | None, firmendaten: dict) -> bytes:
        b = a.get("bloecke") or _bloecke({})
        gruppen: dict[str, tuple] = {}
        for p in a["positionen"]:
            g = gruppen.setdefault(p.get("gruppe") or "Leistungen", (p.get("gruppe") or "Leistungen",
                                                                      p.get("gruppe_farbe", "blau"), []))
            g[2].append({"name": p["beschreibung"], "detail": p.get("detail", ""), "menge": p["menge"],
                         "einheit": p.get("einheit", "") if p.get("einheit", "").lower() == "monat" else "",
                         "betrag_cent": p["gesamt_cent"]} | pdf_posten(p))
        return hanserautisch_pdf(
            art="Angebot", nummer=a["nummer"], firma=firmendaten, logo=self.bh.dir / "logo.jpg",
            empfaenger=_empfaenger(f, ap), untertitel=a.get("titel") or b.get("untertitel", ""),
            infos=[f"{ORT}, den {datum_de(a['datum'])}", f"Gültig bis: {datum_de(a['gueltig_bis'])}",
                   f"Angebot: {a['nummer']}", f"Kundennummer: {a['firma']}"],
            anrede=anrede_moin(ap, f.get("name", "")), einleitung=a.get("einleitung") or b.get("intro", ""),
            texte=kalkulation_texte(b, formate=a["positionen"], tkp_zeigen=b.get("tkp_zeigen", True),
                                    omr_zeigen=b.get("omr_zeigen", False)),
            zeige_kalkulation=b.get("zeige_kalkulation", True) or b.get("omr_zeigen", False),
            zeige_kennzahlen=b.get("zeige_kennzahlen", True),
            gruppen=list(gruppen.values()), summen=a["summen"], zuschlag_liste=None,
            fuss_zusatz=" ".join(x for x in ware_hinweis(a["summe_cent"], a.get("ware"))
                                 + [zb.text(a.get("zahlung"), a["geld_cent"]),
                                    f"Dieses Angebot ist gültig bis {datum_de(a['gueltig_bis'])}."] if x),
            praesentation=_link(a))

    def pdf_ablegen(self, nummer: str, pdf: bytes, *, an: str = "", entwurf_id: str = "", von: str = "") -> dict:
        a = self.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        ev = self.bh.beleg_ablegen(pdf, f"Angebot_{a['nummer']}.pdf", jahr=int(a["datum"][:4]), art="geschaeftsbrief",
                                   bezug=a["nummer"], von=von)
        d = ev["daten"]
        self.bh.erfassen("angebot_pdf_abgelegt", {"nummer": a["nummer"], "pfad": d["pfad"], "sha256": d["sha256"],
                                                   "inhalt": a["inhalt"], "an": an, "entwurf_id": entwurf_id}, von=von)
        return {"pfad": d["pfad"], "sha256": d["sha256"]}

    def erinnerungen_ergaenzen(self, nummer: str, termine: list[dict], *, von: str = "") -> None:
        """Nachgeholte Kalender-Erinnerungen protokollieren (nur fuer versendete Angebote)."""
        nummer = (nummer or "").strip().upper()

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] != "versendet":
                raise ValueError(f"{nummer} ist {a['status']} -- Erinnerungen nur fuer versendete Angebote.")
        self.bh.erfassen_geprueft("angebot_erinnerungen", {"nummer": nummer, "termine": termine}, von=von, pruefe=pruefe)

    def mail_archivieren(self, nummer: str, message_id: str, roh: bytes, *, richtung: str,
                         von: str = "LUNA-Mail") -> bool:
        """Original-Mail unveraendert als .eml ablegen (Geschaeftsbrief, 6 Jahre) und dem Angebot zuordnen. True = neu."""
        a = self.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if message_id in (a.get("mail_archiv") or {}):
            return False
        ev = self.bh.beleg_ablegen(roh, f"Mail_{a['nummer']}_{richtung}_{message_id}.eml", jahr=int(a["datum"][:4]),
                                   art="geschaeftsbrief", bezug=a["nummer"], von=von)
        self.bh.erfassen("angebot_mail_archiviert", {"nummer": a["nummer"], "message_id": message_id,
                                                     "richtung": richtung, "pfad": ev["daten"]["pfad"],
                                                     "sha256": ev["daten"]["sha256"]}, von=von)
        return True

    def antwort_erfassen(self, nummer: str, nachricht: dict, *, von: str = "LUNA-Mail") -> bool:
        """Kundenantwort einmalig protokollieren (Dedup ueber die Gmail-Message-ID). True = neu."""
        nummer = (nummer or "").strip().upper()
        mid = str(nachricht.get("id") or "")

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if any(x.get("message_id") == mid for x in a.get("antworten", [])):
                raise _Nichts()
        try:
            self.bh.erfassen_geprueft("angebot_antwort", {"nummer": nummer, "message_id": mid,
                                                          "von": str(nachricht.get("von") or "")[:200],
                                                          "datum": str(nachricht.get("datum") or "")[:80],
                                                          "vorschau": str(nachricht.get("vorschau") or "")[:500]},
                                      von=von, pruefe=pruefe)
        except _Nichts:
            return False
        return True

    def nachgefasst(self, nummer: str, *, notiz: str = "", von: str = "") -> dict:
        """Nachfassen erledigt (To-do auf der Hauptseite) -- der Nachfass-Termin wird danach aus dem Kalender geloescht."""
        nummer = (nummer or "").strip().upper()

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] != "versendet":
                raise ValueError(f"{nummer} ist {a['status']} -- nachfassen nur bei versendeten Angeboten.")
            if a.get("nachgefasst_am"):
                raise ValueError(f"{nummer} ist schon als nachgefasst markiert.")
        self.bh.erfassen_geprueft("angebot_nachgefasst", {"nummer": nummer, "notiz": str(notiz or "").strip()[:300]},
                                  von=von, pruefe=pruefe)
        return {"nachgefasst": nummer}

    def status_setzen(self, nummer: str, status: str, *, grund: str = "", termine: list | None = None,
                      pdf: str = "", mail: dict | None = None, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        erlaubt = {"entwurf": ("versendet",), "versendet": ("angenommen", "abgelehnt"),
                   "angenommen": (), "abgelehnt": ()}

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if status not in erlaubt.get(a["status"], ()):
                raise ValueError(f"{nummer}: von „{a['status']}“ nicht nach „{status}“ moeglich.")

        daten = {"nummer": nummer, "status": status}
        if grund:
            daten["grund"] = str(grund).strip()[:500]
        if termine:
            daten["termine"] = termine
        if pdf:
            daten["pdf"] = pdf
        if mail:
            daten["mail"] = mail                                 # {an, message_id, thread_id} beim Versand aus LUNA-OS
        self.bh.erfassen_geprueft("angebot_status", daten, von=von, pruefe=pruefe)
        return {"status": status}


class _Nichts(Exception):
    pass


def _schalter(kopf: dict, daten: dict) -> None:
    """„So kalkulieren wir“/Kennzahlen im Hanserautisch-Layout ein- oder ausblenden."""
    if kopf.get("bloecke") is None:
        return
    for k in SCHALTER:
        if k in daten:
            kopf["bloecke"] = {**kopf["bloecke"], k: bool(daten[k])}


def _summen_zeilen(sm: dict) -> list[tuple[str, int]] | None:
    """Zwischenzeilen fuer das Standard-PDF, nur wenn es Zuschlaege oder Rabatt gibt."""
    if not (sm["zuschlaege"] or sm["rabatt"] or sm.get("abzuege") or "provision_cent" in sm):
        return None
    zeilen = [("Summe Formate", sm["formate_cent"])]
    zeilen += [(f"{n} (+{menge_text(pr)} %)", c) for n, pr, c in sm["zuschlaege"]]
    if sm["rabatt"]:
        zeilen.append((f"Paketrabatt ({menge_text(sm['rabatt'][0])} %)", -sm["rabatt"][1]))
    if "provision_cent" in sm:                             # Etappe 23: Provision nach Rabatt, ohne Zuschlag
        zeilen.append(("Provision" + (" (Rest nach Abrechnung)" if sm.get("provision_offen") else ""), sm["provision_cent"]))
    if sm.get("abzuege"):                                  # Schlussrechnung (Etappe 18)
        zeilen.append(("Auftragssumme", sm["vor_abzug_cent"]))
        zeilen += [(n, -c) for n, c in sm["abzuege"]]
    return zeilen


def _empfaenger(f: dict, ap: dict | None) -> list[str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    land = f.get("land", "") if (f.get("land") or "").lower() not in ("", "deutschland", "de") else ""
    return [f.get("name", ""), name, f.get("strasse", ""), f"{f.get('plz') or ''} {f.get('ort') or ''}".strip(), land]


def preisliste_pdf(katalog: dict, firmendaten: dict, *, logo: Path | None, ids: list[str] | None = None,
                   firma: dict | None = None, ap: dict | None = None) -> bytes:
    """Preisliste aus dem Katalog (ohne Nummer, ohne Buchhaltungseintrag). `ids` = Auswahl, sonst alle aktiven."""
    t = katalog["texte"]
    gruppen = []
    for g in katalog["gruppen"]:
        posten = [{"name": it["name"], "detail": " · ".join(x for x in (it["basis"], it["hinweis"]) if x), "menge": None,
                   "einheit": it["einheit"], "betrag_cent": it["preis_cent"]}
                  | ({"betrag_text": (f"{eur(it['provision_wert'])} / Stk." if it["provision_art"] == "stueck"
                                      else f"{menge_text(it['provision_wert'])} % Provision"), "einheit": ""}
                     if it.get("provision_art") else {})
                  for it in g["items"] if it["aktiv"] and (ids is None or it["id"] in ids)]
        gruppen.append((g["name"], g["farbe"], posten))
    if not any(p for _, _, p in gruppen):
        raise ValueError("Keine Formate ausgewaehlt.")
    heute = jetzt().date()
    return hanserautisch_pdf(
        art="Preisliste", nummer=None, firma=firmendaten, logo=logo,
        empfaenger=_empfaenger(firma, ap) if firma else [], untertitel=t.get("untertitel", ""),
        infos=[f"{ORT}, den {datum_de(heute.isoformat())}"],
        anrede=anrede_moin(ap, (firma or {}).get("name", "")) if firma else "Moin,", einleitung=t.get("intro", ""),
        texte=kalkulation_texte(t, formate=[it for g in katalog["gruppen"] for it in g["items"]
                                            if it["aktiv"] and (ids is None or it["id"] in ids)],
                                omr_zeigen=True, spanne=True),
        zeige_kalkulation=True, zeige_kennzahlen=True, gruppen=gruppen, summen=None,
        zuschlag_liste=katalog["zuschlaege"], fuss_zusatz="Preisliste freibleibend, Angebote individuell.")


def antworten_pruefen(st: "AngebotStore", google, *, eigene_adresse: str = "", notify=None, tage: int = 60) -> int:
    """Mailverlaeufe gesendeter Angebote auf Kundenantworten pruefen, neue protokollieren und dem CEO melden.
    Laeuft im 15-Minuten-Poll des Bots. Rueckgabe: Anzahl neuer Antworten."""
    from datetime import timedelta
    grenze = (jetzt() - timedelta(days=tage)).isoformat()
    eigen = (eigene_adresse or "").strip().lower()
    neu = 0
    def archiviere(a, mid, richtung):
        if not mid or mid in (a.get("mail_archiv") or {}):
            return
        r = google.mail_roh(mid)
        if r.get("ok") and r.get("roh"):
            st.mail_archivieren(a["nummer"], mid, r["roh"], richtung=richtung)

    for a in st._falte(st.bh.eintraege()).values():
        mail = a.get("versendet_mail") or {}
        if not mail.get("thread_id"):
            continue
        # Archiv nachholen (gesendete Mail + bereits erfasste Antworten), unabhaengig vom Alter
        archiviere(a, mail.get("message_id"), "aus")
        for x in a.get("antworten", []):
            archiviere(a, x.get("message_id"), "ein")
        if a["status"] not in ("versendet", "angenommen") or str(a.get("versendet_am") or "") < grenze:
            continue
        r = google.thread_lesen(mail["thread_id"])
        if not r.get("ok"):
            continue
        for m in r.get("nachrichten", []):
            if m.get("gesendet") or (eigen and eigen in str(m.get("von") or "").lower()):
                continue
            if st.antwort_erfassen(a["nummer"], m):
                archiviere(st.angebot(a["nummer"]), m.get("id"), "ein")
                neu += 1
                if notify:
                    try:
                        notify(f"✉️ Antwort auf Angebot {a['nummer']} von {m.get('von', '')}: "
                               f"{str(m.get('vorschau') or '')[:160]}", abteilung="CRO", kategorie="crm",
                               quelle="angebote", detail=f"LUNA-OS -> Angebote -> {a['nummer']}")
                    except Exception:
                        pass
    return neu


def mail_lesen(roh: bytes) -> dict:
    """Archivierte .eml fuer die Anzeige: Kopfdaten, Text (Klartext bevorzugt, sonst HTML ohne Tags), Anhangnamen."""
    import email
    import html as _html
    import re as _re
    from email import policy
    m = email.message_from_bytes(roh, policy=policy.default)
    teil = m.get_body(preferencelist=("plain", "html"))
    text = ""
    if teil is not None:
        text = teil.get_content()
        if teil.get_content_type() == "text/html":
            text = _html.unescape(_re.sub(r"<[^>]+>", " ", _re.sub(r"(?is)<(script|style).*?</\1>", "", text)))
            text = _re.sub(r"[ \t]+", " ", _re.sub(r"\n\s*\n+", "\n\n", text))
    anhaenge = [p.get_filename() for p in m.iter_attachments() if p.get_filename()]
    return {"von": str(m.get("From", "")), "an": str(m.get("To", "")), "datum": str(m.get("Date", "")),
            "betreff": str(m.get("Subject", "")), "text": text.strip()[:20000], "anhaenge": anhaenge}


def _link(a: dict) -> tuple[str, str] | None:
    p = a.get("praesentation") or {}
    return (p.get("text") or p["url"], p["url"]) if p.get("url") else None


def mail_text(a: dict, firma: dict, ap: dict | None, firmendaten: dict, *, vorlage: dict | None = None,
              signatur: str = "") -> tuple[str, str]:
    """Betreff + Text fuer den Versand (Textbausteine: Standard = frueherer Text; der CEO passt ihn vor dem Senden an)."""
    from .textbausteine import anrede_werte, rendern
    t = a.get("titel") or ""
    w = anrede_werte(ap) | {"kunde": (firma or {}).get("name", ""), "nummer": a["nummer"], "titel": t,
                            "titel_zusatz": f" – {t}" if t else "", "zu_titel": f" zu „{t}“" if t else "",
                            "betrag": eur(a["summe_cent"]), "gueltig_bis": datum_de(a["gueltig_bis"]),
                            "praesentation": f"{_link(a)[0]}: {_link(a)[1]}" if _link(a) else ""}
    return rendern("angebot", w, firmendaten, vorlage=vorlage, signatur=signatur)
