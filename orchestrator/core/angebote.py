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

from .beleg_pdf import HINWEIS_19, beleg_pdf, cent, datum_de, eur, menge, positions_summe
from .buchhaltung import Buchhaltung, jetzt
from .kunden import KundenStore

STATUS = ("entwurf", "versendet", "angenommen", "abgelehnt")
KOPF_FELDER = ("firma", "ansprechpartner", "titel", "datum", "gueltig_bis", "einleitung", "schluss", "nachfassen_tage")
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
            ep = int(p["einzelpreis_cent"]) if "einzelpreis_cent" in p else cent(p.get("einzelpreis", ""))
        except ValueError as exc:
            raise ValueError(f"Position {i}: {exc}") from None
        if ep < 0:
            raise ValueError(f"Position {i}: negativer Preis.")
        out.append({"beschreibung": text, "menge": format(m, "f"), "einheit": str(p.get("einheit") or "").strip()[:30],
                    "einzelpreis_cent": ep})
    return out


def _kopf(daten: dict) -> dict:
    out = {}
    for k in KOPF_FELDER:
        if k not in daten:
            continue
        v = daten[k]
        if k in ("datum", "gueltig_bis"):
            out[k] = _iso(v, "Datum" if k == "datum" else "Gueltig bis")
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


def inhalt_hash(a: dict) -> str:
    """Hash des druckrelevanten Inhalts (welcher Stand ging raus?)."""
    teil = {k: a.get(k) for k in KOPF_FELDER if k != "nachfassen_tage"} | {"positionen": a.get("positionen")}
    return hashlib.sha256(json.dumps(teil, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class AngebotStore:
    def __init__(self, bh: Buchhaltung, kunden: KundenStore):
        self.bh = bh
        self.kunden = kunden

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
            elif t == "angebot_status":
                a = out[d["nummer"]]
                a["status"] = d["status"]
                a[d["status"] + "_am"] = e["ts"]
                for k in ("termine", "grund", "pdf"):
                    if d.get(k):
                        a[f"{d['status']}_{k}"] = d[k]
                a["verlauf"].append(spur | {"status": d["status"], "grund": d.get("grund", "")})
        return out

    @staticmethod
    def _anreichern(a: dict, heute: date | None = None) -> dict:
        heute = heute or jetzt().date()
        pos = [p | {"gesamt_cent": positions_summe(p["menge"], p["einzelpreis_cent"])} for p in a["positionen"]]
        anzeige = a["status"]
        if anzeige == "versendet" and a.get("gueltig_bis") and date.fromisoformat(a["gueltig_bis"]) < heute:
            anzeige = "abgelaufen"
        return a | {"positionen": pos, "summe_cent": sum(p["gesamt_cent"] for p in pos), "anzeige_status": anzeige,
                    "inhalt": inhalt_hash(a)}

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
        kopf = {"datum": heute.isoformat(), "gueltig_bis": (heute + timedelta(days=30)).isoformat(),
                "nachfassen_tage": 7, "ansprechpartner": "", "titel": "", "einleitung": "", "schluss": ""}
        kopf.update(_kopf(daten))
        if kopf["gueltig_bis"] < kopf["datum"]:
            raise ValueError("Gueltig bis liegt vor dem Angebotsdatum.")
        pos = _positionen(daten.get("positionen"))
        jahr = int(kopf["datum"][:4])
        ev = self.bh.mit_nummer("AN", "angebot_angelegt", kopf | {"positionen": pos}, jahr=jahr,
                                bezug=kopf["firma"], von=von, pruefe=lambda e: self._pruefe_bezug(e, kopf))
        return {"nummer": ev["daten"]["nummer"]}

    def aendern(self, nummer: str, daten: dict, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        if not isinstance(daten, dict):
            raise ValueError("Ungueltige Eingabe.")
        neu = _kopf(daten)
        if "positionen" in daten:
            neu["positionen"] = _positionen(daten["positionen"])
        diff: dict = {}

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] != "entwurf":
                raise ValueError(f"{nummer} ist {a['status']} und kann nicht mehr geaendert werden.")
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

    def pdf(self, nummer: str, firmendaten: dict) -> bytes:
        a = self.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        f = self.kunden.firma(a["firma"]) or {}
        ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
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
            einleitung=einleitung, positionen=a["positionen"], summe_cent=a["summe_cent"],
            hinweise=[HINWEIS_19, f"Dieses Angebot ist gültig bis {datum_de(a['gueltig_bis'])}."], schluss=schluss)

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

    def status_setzen(self, nummer: str, status: str, *, grund: str = "", termine: list | None = None,
                      pdf: str = "", von: str = "") -> dict:
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
        self.bh.erfassen_geprueft("angebot_status", daten, von=von, pruefe=pruefe)
        return {"status": status}


class _Nichts(Exception):
    pass


def mail_text(a: dict, firma: dict, ap: dict | None, firmendaten: dict) -> tuple[str, str]:
    """Betreff + Text fuer den Gmail-Entwurf (der CEO passt ihn vor dem Senden in Gmail an)."""
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,"
    betreff = f"Angebot {a['nummer']}" + (f" – {a['titel']}" if a.get("titel") else "")
    text = (f"{anrede}\n\nanbei erhalten Sie unser Angebot {a['nummer']}"
            + (f" zu „{a['titel']}“" if a.get("titel") else "")
            + f" über {eur(a['summe_cent'])}. Es ist gültig bis {datum_de(a['gueltig_bis'])}.\n\n"
            "Bei Fragen melden Sie sich gerne.\n\nMit freundlichen Grüßen\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text
