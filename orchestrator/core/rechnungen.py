"""Ausgangsrechnungen (KUNDEN_FINANZEN_ROADMAP.md, Etappe 5) -- Kleinunternehmer § 19 UStG, Pflichtangaben § 34a UStDV.

Ablauf: **Entwurf** (frei oder aus Auftrag `AB-`, beliebig aenderbar/verwerfbar, **ohne Nummer**) -> **Festschreiben**
(Nummer `RE-JJJJ-NNNN` + PDF + Eintrag in EINEM gesperrten Schritt, `Buchhaltung.festschreiben`; danach unveraenderlich)
-> versendet / bezahlt. Fehler werden nie ueberschrieben, sondern **storniert**: eine Stornorechnung mit eigener Nummer
(negative Betraege, Bezug auf das Original), optional mit neuem Korrektur-Entwurf.

Schutz: kein Umsatzsteuer-Feld (§ 14c), Pflicht Steuernummer + Leistungsdatum, **Kleinunternehmer-Waechter**: Festschreiben
wird blockiert, wenn der Jahresumsatz 100.000 EUR ueberschreiten wuerde (ab dieser Rechnung waere Umsatzsteuer faellig)
oder der Vorjahresumsatz ueber 25.000 EUR lag; ab 80 % Warnung. Umsatz = Summe festgeschriebener Rechnungen des
Kalenderjahres abzueglich Stornos (vereinfachte Sicht; Zahlungseingang/EUeR folgt in Etappe 7).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from .angebote import _bloecke, _empfaenger, _kopf, _positionen, anrede_moin, summen, ware_geld, ware_hinweis
from .beleg_pdf import HINWEIS_19, beleg_pdf, cent, datum_de, eur, hanserautisch_pdf, positions_summe
from .buchhaltung import Buchhaltung, jetzt
from .eigenbelege import einnahmen_cent, zuordnung_pruefen
from .kunden import KundenStore

GRENZE_LAUFEND = 100_000_00     # Cent, § 19 Abs. 1 UStG (ab 2025): Ueberschreiten beendet den Status sofort
GRENZE_VORJAHR = 25_000_00
WARNSCHWELLE = 0.8
FELDER = ("firma", "ansprechpartner", "titel", "leistung_von", "leistung_bis", "zahlungsziel_tage", "einleitung",
          "layout", "bloecke", "zuschlaege", "rabatt_prozent", "ware")
VERWENDUNG = ("content", "privat", "leihgabe")         # Barter-Ware: betrieblich fuer Content (Standard) / privat / zurueck


def _datum(v, feld):
    if v in (None, ""):
        return ""
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{feld}: ungueltiges Datum (JJJJ-MM-TT).") from None


def _entwurf_felder(daten: dict) -> dict:
    """Pruefen/normalisieren -- nutzt die Angebots-Regeln fuer Firma, Zuschlaege, Rabatt, Layout, Bloecke."""
    if not isinstance(daten, dict):
        raise ValueError("Ungueltige Eingabe.")
    out = _kopf({k: v for k, v in daten.items() if k in ("firma", "ansprechpartner", "titel", "einleitung", "layout",
                                                          "bloecke", "zuschlaege", "rabatt_prozent", "ware")})
    for k, f in (("leistung_von", "Leistung von"), ("leistung_bis", "Leistung bis")):
        if k in daten:
            out[k] = _datum(daten[k], f)
    if "zahlungsziel_tage" in daten:
        try:
            n = int(daten["zahlungsziel_tage"])
        except (TypeError, ValueError):
            raise ValueError("Zahlungsziel: ganze Zahl (Tage).") from None
        if not 0 <= n <= 120:
            raise ValueError("Zahlungsziel: 0 bis 120 Tage.")
        out["zahlungsziel_tage"] = n
    if "positionen" in daten:
        out["positionen"] = _positionen(daten["positionen"])
    return out


class RechnungStore:
    def __init__(self, bh: Buchhaltung, kunden: KundenStore, katalog=None):
        self.bh, self.kunden, self.katalog = bh, kunden, katalog

    # -- Faltung -------------------------------------------------------------------------------------------------

    @staticmethod
    def _falte(eintraege: list[dict]) -> tuple[dict, dict]:
        entwuerfe: dict[str, dict] = {}
        rechnungen: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t}
            if t == "rechnung_entwurf":
                entwuerfe[d["entwurf_id"]] = dict(d) | {"status": "entwurf", "angelegt": e["ts"], "verlauf": [spur]}
            elif t == "rechnung_entwurf_geaendert" and d.get("entwurf_id") in entwuerfe:
                x = entwuerfe[d["entwurf_id"]]
                x.update(d.get("felder", {}))
                x["verlauf"].append(spur | {"felder": sorted(d.get("felder", {}))})
            elif t == "rechnung_entwurf_verworfen":
                entwuerfe.pop(d.get("entwurf_id"), None)
            elif t == "rechnung_festgeschrieben":
                entwuerfe.pop(d.get("entwurf_id"), None)
                w = max(0, min(int((d.get("ware") or {}).get("wert_cent") or 0), int(d.get("summe_cent") or 0)))
                r = dict(d) | {"status": "storno" if d.get("art") == "storno" else "offen", "bezahlt_cent": 0,
                               "zahlungen": [], "festgeschrieben_am": e["ts"], "verlauf": [spur],
                               "ware_cent": w, "geld_cent": int(d.get("summe_cent") or 0) - w, "ware_vorgaenge": []}
                rechnungen[d["nummer"]] = r
                if d.get("art") == "storno" and d.get("bezug") in rechnungen:
                    o = rechnungen[d["bezug"]]
                    o["status"], o["storniert_durch"] = "storniert", d["nummer"]
                    o["verlauf"].append(spur | {"storno": d["nummer"], "grund": d.get("grund", "")})
            elif d.get("nummer") not in rechnungen:
                continue
            elif t == "rechnung_versendet":
                r = rechnungen[d["nummer"]]
                r["versendet_mail"], r["versendet_am"] = d.get("mail"), e["ts"]
                r["verlauf"].append(spur | {"mail_an": (d.get("mail") or {}).get("an", "")})
            elif t == "rechnung_bezahlt":
                r = rechnungen[d["nummer"]]
                r["zahlungen"].append({k: d.get(k) for k in ("datum", "betrag_cent", "notiz", "zuordnung_jahr",
                                                             "nebenforderung_cent")})
                r["bezahlt_cent"] += int(d.get("betrag_cent") or 0)
                r["verlauf"].append(spur | {"betrag_cent": d.get("betrag_cent"), "datum": d.get("datum")})
            elif t == "rechnung_zahlung_storniert":          # Etappe 7: falsch erfasste Zahlung, Korrektur sichtbar
                r = rechnungen[d["nummer"]]
                z = r["zahlungen"][d["index"]]
                z |= {"storniert": True, "storno_grund": d.get("grund", ""), "storniert_am": e["ts"]}
                r["bezahlt_cent"] -= int(z.get("betrag_cent") or 0)
                r["verlauf"].append(spur | {"betrag_cent": -int(z.get("betrag_cent") or 0), "grund": d.get("grund", "")})
            elif t == "rechnung_ware_erhalten":              # Etappe 12: Barter-Ware ist da (Einnahme)
                r = rechnungen[d["nummer"]]
                r["ware_vorgaenge"].append(dict(d) | {"ts": e["ts"], "storniert": False})
                r["verlauf"].append(spur | {"betrag_cent": d.get("wert_cent"), "datum": d.get("datum")})
            elif t == "rechnung_ware_storniert":
                r = rechnungen[d["nummer"]]
                for v in r["ware_vorgaenge"]:
                    if not v["storniert"]:
                        v |= {"storniert": True, "storno_grund": d.get("grund", ""), "storniert_am": e["ts"]}
                r["verlauf"].append(spur | {"grund": d.get("grund", "")})
            elif t == "rechnung_erinnerung":
                rechnungen[d["nummer"]]["erinnerung"] = d.get("termin")
        for r in rechnungen.values():                        # bezahlt = Geldteil gezahlt UND Ware erhalten (Barter)
            r.setdefault("ware_cent", 0)
            r.setdefault("geld_cent", r.get("summe_cent", 0))
            r.setdefault("ware_vorgaenge", [])
            r["ware_erhalten"] = next((v for v in r["ware_vorgaenge"] if not v["storniert"]), None)
            if r["status"] in ("offen", "bezahlt"):
                r["status"] = ("bezahlt" if r["bezahlt_cent"] >= r["geld_cent"] and (not r["ware_cent"] or r["ware_erhalten"])
                               else "offen")
        return entwuerfe, rechnungen

    @staticmethod
    def _summen(x: dict) -> dict:
        pos = [p | {"gesamt_cent": positions_summe(p["menge"], p["einzelpreis_cent"])} for p in x.get("positionen", [])]
        sm = summen(x.get("positionen", []), x.get("zuschlaege") or [], x.get("rabatt_prozent") or 0)
        return x | {"positionen": pos, "summen": sm, "summe_cent": sm["gesamt_cent"]}

    def _stand(self):
        return self._falte(self.bh.eintraege())

    # -- Lesen ---------------------------------------------------------------------------------------------------

    def umsatz(self, jahr: int, rechnungen: dict | None = None, eintraege: list | None = None) -> int:
        """Umsatz fuer § 19 UStG: Rechnungen nach Rechnungsdatum + Einnahmen aus Eigenbelegen (z. B. Plattform-
        Auszahlungen ohne eigene Rechnung, Etappe 7). Ohne Argumente wird das Kassenbuch gelesen."""
        if rechnungen is None:
            eintraege = self.bh.eintraege() if eintraege is None else eintraege
            rechnungen = self._falte(eintraege)[1]
        sonst = einnahmen_cent(eintraege, jahr) if eintraege is not None else 0
        return sonst + sum(r["summe_cent"] for r in rechnungen.values() if str(r.get("rechnungsdatum", ""))[:4] == str(jahr))

    def waechter(self, zusatz_cent: int = 0, jahr: int | None = None, rechnungen: dict | None = None,
                 eintraege: list | None = None) -> dict:
        jahr = jahr or jetzt().year
        lauf = self.umsatz(jahr, rechnungen, eintraege) + zusatz_cent
        vor = self.umsatz(jahr - 1, rechnungen, eintraege)
        return {"jahr": jahr, "umsatz_cent": lauf, "vorjahr_cent": vor, "grenze_cent": GRENZE_LAUFEND,
                "anteil": round(lauf / GRENZE_LAUFEND, 4), "warnung": lauf >= GRENZE_LAUFEND * WARNSCHWELLE,
                "ueberschritten": lauf > GRENZE_LAUFEND, "vorjahr_ueberschritten": vor > GRENZE_VORJAHR}

    def uebersicht(self, jahr: int | None = None) -> dict:
        eintraege = self.bh.eintraege()
        entwuerfe, rechnungen = self._falte(eintraege)
        firmen = {f["nummer"]: f["name"] for f in self.kunden.firmen()}
        heute = jetzt().date().isoformat()
        liste = []
        for r in rechnungen.values():
            if jahr and str(r.get("rechnungsdatum", ""))[:4] != str(jahr):
                continue
            ueber = r["status"] == "offen" and r.get("faellig_am", "9") < heute
            liste.append({k: r.get(k) for k in ("nummer", "art", "bezug", "firma", "titel", "rechnungsdatum", "faellig_am",
                                                 "summe_cent", "bezahlt_cent", "status", "auftrag")}
                         | {"firma_name": firmen.get(r["firma"], ""), "ueberfaellig": ueber,
                            "versendet": bool(r.get("versendet_mail"))})
        ents = [self._summen(x) for x in entwuerfe.values()]
        return {"rechnungen": sorted(liste, key=lambda x: x["nummer"], reverse=True),
                "entwuerfe": [{k: x.get(k) for k in ("entwurf_id", "firma", "titel", "auftrag", "summe_cent", "angelegt")}
                              | {"firma_name": firmen.get(x["firma"], "")} for x in ents],
                "waechter": self.waechter(rechnungen=rechnungen, eintraege=eintraege)}

    def get(self, kennung: str) -> dict | None:
        k = (kennung or "").strip()
        entwuerfe, rechnungen = self._stand()
        if k.upper() in rechnungen:
            r = self._summen(rechnungen[k.upper()])
            return r | {"ueberfaellig": r["status"] == "offen" and r.get("faellig_am", "9") < jetzt().date().isoformat()}
        return self._summen(entwuerfe[k]) if k in entwuerfe else None

    # -- Entwuerfe -----------------------------------------------------------------------------------------------

    def entwurf_anlegen(self, daten: dict, *, von: str = "") -> dict:
        d = _entwurf_felder(daten)
        if not d.get("firma"):
            raise ValueError("Firma fehlt.")
        if "positionen" not in d:
            raise ValueError("Mindestens eine Position noetig.")
        firma = self.kunden.firma(d["firma"])
        if not firma:
            raise KeyError(d["firma"])
        ap = d.get("ansprechpartner")
        if ap and ap not in {x["nummer"] for x in firma.get("ansprechpartner_liste", [])}:
            raise ValueError(f"Ansprechpartner {ap} gehoert nicht zu {d['firma']}.")
        d.setdefault("zahlungsziel_tage", firma.get("zahlungsziel_tage") if firma.get("zahlungsziel_tage") is not None else 14)
        d.setdefault("layout", "hanserautisch" if self.katalog else "standard")
        if d["layout"] == "hanserautisch" and "bloecke" not in d:
            d["bloecke"] = _bloecke(self.katalog.laden()["texte"] if self.katalog else {})
        for k in ("ansprechpartner", "titel", "leistung_von", "leistung_bis", "einleitung"):
            d.setdefault(k, "")
        d.setdefault("zuschlaege", [])
        d.setdefault("rabatt_prozent", 0)
        for k in ("auftrag", "angebot"):
            if daten.get(k):
                d[k] = str(daten[k]).upper()[:20]
        eid = "E-" + uuid.uuid4().hex[:8]
        self.bh.erfassen("rechnung_entwurf", d | {"entwurf_id": eid}, von=von)
        return {"entwurf_id": eid}

    def entwurf_aus_auftrag(self, auftrag: dict, *, von: str = "") -> dict:
        _, rechnungen = self._stand()
        entwuerfe = self._stand()[0]
        aktiv = [r["nummer"] for r in rechnungen.values() if r.get("auftrag") == auftrag["nummer"] and r["status"] != "storniert"
                 and r.get("art") != "storno"]
        if aktiv:
            raise ValueError(f"Zu {auftrag['nummer']} gibt es schon die Rechnung {aktiv[0]}.")
        offen = [e for e, x in entwuerfe.items() if x.get("auftrag") == auftrag["nummer"]]
        if offen:
            return {"entwurf_id": offen[0], "vorhanden": True}
        if auftrag.get("status") == "storniert":
            raise ValueError(f"{auftrag['nummer']} ist storniert.")
        daten = {k: auftrag.get(k) for k in ("firma", "ansprechpartner", "titel", "zuschlaege", "rabatt_prozent", "layout",
                                              "bloecke", "leistung_von", "leistung_bis", "ware")}
        daten["positionen"] = [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in auftrag["positionen"]]
        daten |= {"auftrag": auftrag["nummer"], "angebot": auftrag.get("angebot", "")}
        return self.entwurf_anlegen({k: v for k, v in daten.items() if v not in (None,)}, von=von)

    def entwurf_aendern(self, eid: str, daten: dict, *, von: str = "") -> dict:
        neu = _entwurf_felder(daten)
        diff: dict = {}

        def pruefe(eintraege):
            x = self._falte(eintraege)[0].get(eid)
            if not x:
                raise KeyError(eid)
            diff.update({k: v for k, v in neu.items() if x.get(k) != v})
            if not diff:
                raise _Nichts()
        try:
            self.bh.erfassen_geprueft("rechnung_entwurf_geaendert", {"entwurf_id": eid, "felder": diff}, von=von,
                                      pruefe=pruefe)
        except _Nichts:
            return {"geaendert": []}
        return {"geaendert": sorted(diff)}

    def entwurf_verwerfen(self, eid: str, *, von: str = "") -> dict:
        def pruefe(eintraege):
            if eid not in self._falte(eintraege)[0]:
                raise KeyError(eid)
        self.bh.erfassen_geprueft("rechnung_entwurf_verworfen", {"entwurf_id": eid}, von=von, pruefe=pruefe)
        return {"verworfen": eid}

    # -- Festschreiben -------------------------------------------------------------------------------------------

    def festschreiben(self, eid: str, firmendaten: dict, *, von: str = "") -> dict:
        """Nummer + PDF + unveraenderlicher Eintrag. ValueError, wenn Pflichtangaben fehlen oder der Waechter blockiert."""
        if not (firmendaten.get("steuernummer") or firmendaten.get("ustid")):
            raise ValueError("Steuernummer fehlt in den Firmendaten -- Pflichtangabe auf Rechnungen (§ 34a UStDV).")
        heute = jetzt().date()
        info: dict = {}

        def erzeuge(nummer, eintraege):
            entwuerfe, rechnungen = self._falte(eintraege)
            x = entwuerfe.get(eid)
            if not x:
                raise KeyError(eid)
            x = self._summen(x)
            if not x.get("leistung_von") and not x.get("leistung_bis"):
                raise ValueError("Leistungsdatum fehlt (Pflichtangabe).")
            if x["summe_cent"] <= 0:
                raise ValueError("Rechnungsbetrag muss groesser als 0 sein.")
            ware_geld(x["summe_cent"], x.get("ware"))                  # Warenwert nicht ueber der Summe
            w = self.waechter(x["summe_cent"], heute.year, rechnungen, eintraege)
            if w["vorjahr_ueberschritten"]:
                raise ValueError(f"Vorjahresumsatz {eur(w['vorjahr_cent'])} liegt ueber 25.000 € -- Kleinunternehmer-"
                                 "Regelung gilt dieses Jahr nicht. Nicht festgeschrieben; bitte klaeren.")
            if w["ueberschritten"]:
                raise ValueError(f"Mit dieser Rechnung laege der Jahresumsatz bei {eur(w['umsatz_cent'])} -- ueber "
                                 "100.000 €. Ab dieser Rechnung waere Umsatzsteuer faellig; nicht festgeschrieben.")
            info["warnung"] = w["warnung"]
            info["waechter"] = w
            faellig = heute + timedelta(days=int(x.get("zahlungsziel_tage") or 0))
            kopf = {k: x.get(k) for k in FELDER} | {"positionen": [{k: v for k, v in p.items() if k != "gesamt_cent"}
                                                                   for p in x["positionen"]],
                                                    "entwurf_id": eid, "art": "rechnung",
                                                    "auftrag": x.get("auftrag", ""), "angebot": x.get("angebot", ""),
                                                    "rechnungsdatum": heute.isoformat(), "faellig_am": faellig.isoformat(),
                                                    "summe_cent": x["summe_cent"]}
            pdf = self._pdf(kopf | {"nummer": nummer}, firmendaten)
            return kopf, [(pdf, f"Rechnung_{nummer}.pdf", "beleg")]

        ev = self.bh.festschreiben("RE", "rechnung_festgeschrieben", erzeuge, jahr=heute.year, bezug=eid, von=von)
        return {"nummer": ev["daten"]["nummer"], "faellig_am": ev["daten"]["faellig_am"], "warnung": info.get("warnung"),
                "waechter": info.get("waechter")}

    def stornieren(self, nummer: str, firmendaten: dict, *, grund: str = "", korrektur: bool = False,
                   von: str = "") -> dict:
        """Stornorechnung (eigene Nummer, negative Betraege) zur Rechnung `nummer`; optional Korrektur-Entwurf."""
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:500]
        if not grund:
            raise ValueError("Bitte einen Grund fuer das Storno angeben.")
        heute = jetzt().date()
        original: dict = {}

        def erzeuge(neu_nr, eintraege):
            _, rechnungen = self._falte(eintraege)
            o = rechnungen.get(nummer)
            if not o:
                raise KeyError(nummer)
            if o.get("art") == "storno" or o["status"] == "storniert":
                raise ValueError(f"{nummer} ist bereits {'eine Stornorechnung' if o.get('art') == 'storno' else 'storniert'}.")
            if o.get("bezahlt_cent"):
                raise ValueError(f"{nummer} ist (teil)bezahlt -- erst die Zahlung klaeren (Rueckzahlung), dann stornieren.")
            if o.get("ware_erhalten"):
                raise ValueError(f"Zu {nummer} ist Ware als erhalten gebucht -- erst den Ware-Eingang stornieren.")
            original.update(o)
            pos = [p | {"einzelpreis_cent": -int(p["einzelpreis_cent"])} for p in o["positionen"]]
            kopf = {k: o.get(k) for k in FELDER} | {"positionen": pos, "art": "storno", "bezug": nummer, "grund": grund,
                                                    "auftrag": o.get("auftrag", ""), "angebot": o.get("angebot", ""),
                                                    "rechnungsdatum": heute.isoformat(), "faellig_am": heute.isoformat(),
                                                    "leistung_von": o.get("leistung_von", ""),
                                                    "leistung_bis": o.get("leistung_bis", "")}
            kopf["summe_cent"] = self._summen(kopf)["summe_cent"]
            pdf = self._pdf(kopf | {"nummer": neu_nr}, firmendaten)
            return kopf, [(pdf, f"Stornorechnung_{neu_nr}.pdf", "beleg")]

        ev = self.bh.festschreiben("RE", "rechnung_festgeschrieben", erzeuge, jahr=heute.year, bezug=nummer, von=von)
        out = {"storno": ev["daten"]["nummer"]}
        if korrektur:
            d = {k: original.get(k) for k in FELDER if original.get(k) not in (None,)}
            d["positionen"] = [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in original["positionen"]]
            for k in ("auftrag", "angebot"):
                if original.get(k):
                    d[k] = original[k]
            out["korrektur_entwurf"] = self.entwurf_anlegen(d, von=von)["entwurf_id"]
        return out

    def versendet(self, nummer: str, mail: dict, *, von: str = "") -> None:
        def pruefe(eintraege):
            if nummer not in self._falte(eintraege)[1]:
                raise KeyError(nummer)
        self.bh.erfassen_geprueft("rechnung_versendet", {"nummer": nummer, "mail": mail}, von=von, pruefe=pruefe)

    def bezahlt(self, nummer: str, *, datum: str, betrag: str | int | None = None, notiz: str = "",
                zuordnung_jahr=None, nebenforderung=None, von: str = "") -> dict:
        """Zahlungseingang von Hand (CEO-Entscheidung 3). Ohne Betrag = offener Rest. `zuordnung_jahr` = 10-Tage-Regel.
        `nebenforderung` (Etappe 10): zusaetzlich gezahlte Verzugszinsen/Mahnkosten -- nur bei gemahnten Rechnungen."""
        nummer = (nummer or "").strip().upper()
        tag = _datum(datum, "Zahlungsdatum") or jetzt().date().isoformat()
        if tag > jetzt().date().isoformat():
            raise ValueError("Zahlungsdatum liegt in der Zukunft.")
        zuordnung = zuordnung_pruefen(tag, zuordnung_jahr)
        try:
            neben = cent(nebenforderung) if nebenforderung not in (None, "", 0, "0") else 0
        except ValueError:
            raise ValueError("Betrag Zinsen/Mahnkosten ungueltig.") from None
        if neben < 0:
            raise ValueError("Betrag Zinsen/Mahnkosten darf nicht negativ sein.")
        rest: dict = {}

        def pruefe(eintraege):
            r = self._falte(eintraege)[1].get(nummer)
            if not r:
                raise KeyError(nummer)
            if r["status"] != "offen" or r.get("art") == "storno":
                raise ValueError(f"{nummer} ist {r['status']} -- keine Zahlung erfassbar.")
            rest["cent"] = r["geld_cent"] - r["bezahlt_cent"]
            if rest["cent"] <= 0:
                raise ValueError(f"Der Geldteil von {nummer} ist bezahlt -- offen ist nur die Ware (\u201eWare erhalten\u201c erfassen).")

        # Betrag erst nach der Pruefung festlegen (offener Rest), deshalb zweistufig unter derselben Sperre
        with self.bh._gesperrt():
            pruefe(self.bh._eintraege())
            if neben and not any(e["typ"] == "mahnung_erstellt" and e["daten"].get("rechnung") == nummer
                                 for e in self.bh._eintraege()):
                raise ValueError("Zinsen/Mahnkosten gibt es nur bei gemahnten Rechnungen.")
            b = rest["cent"] if betrag in (None, "") else cent(betrag)
            if b <= 0 or b > rest["cent"]:
                raise ValueError(f"Betrag muss zwischen 0,01 € und dem offenen Rest {eur(rest['cent'])} liegen.")
            self.bh._anhaengen("rechnung_bezahlt", {"nummer": nummer, "datum": tag, "betrag_cent": b,
                                                     "notiz": str(notiz or "").strip()[:300]}
                               | ({"zuordnung_jahr": zuordnung} if zuordnung else {})
                               | ({"nebenforderung_cent": neben} if neben else {}), von=von)
        return {"betrag_cent": b, "rest_cent": rest["cent"] - b, "nebenforderung_cent": neben}

    def ware_erhalten(self, nummer: str, *, datum: str = "", text: str = "", wert_marke=None, wert_nachweis=None,
                      verwendung: str = "content", kategorie: str = "", nutzungsdauer_jahre=None,
                      nachweise: list[tuple[bytes, str]] | None = None, von: str = "") -> dict:
        """Etappe 12 (Barter): Ware als Gegenleistung erhalten -> Einnahme zum ueblichen Endpreis (§ 8 Abs. 2 EStG).
        Wert = eigener Nachweis (Shop-Preis), sonst Preisangabe der Marke (CEO: beides erfassen). Verwendung
        „content“ (Standard) bucht die Ware zugleich als Anschaffung (GWG/Anlage/Verbrauch), „privat“ nur die Einnahme,
        „leihgabe“ (geht zurueck) gar nichts -- dokumentiert wird immer."""
        from .eingangsbelege import KATEGORIEN, _teil_pruefen
        nummer = (nummer or "").strip().upper()
        tag = _datum(datum, "Eingangsdatum") or jetzt().date().isoformat()
        if tag > jetzt().date().isoformat():
            raise ValueError("Eingangsdatum liegt in der Zukunft.")
        if verwendung not in VERWENDUNG:
            raise ValueError("Verwendung muss Content, privat oder Leihgabe sein.")
        r = self._stand()[1].get(nummer)
        if not r:
            raise KeyError(nummer)
        if r.get("art") == "storno" or r["status"] == "storniert":
            raise ValueError(f"{nummer} ist storniert.")
        if not r.get("ware_cent"):
            raise ValueError(f"{nummer} hat keine Gegenleistung in Ware.")
        if r.get("ware_erhalten"):
            raise ValueError(f"Ware zu {nummer} ist bereits erfasst -- bei Fehlern erst stornieren.")
        try:
            marke = cent(wert_marke) if wert_marke not in (None, "") else r["ware_cent"]
            nachweis = cent(wert_nachweis) if wert_nachweis not in (None, "") else 0
        except ValueError:
            raise ValueError("Warenwert ungueltig.") from None
        wert = nachweis or marke
        if wert <= 0:
            raise ValueError("Warenwert muss groesser als 0 sein.")
        d = {"nummer": nummer, "datum": tag, "text": str(text or (r.get("ware") or {}).get("text") or "").strip()[:300],
             "wert_cent": wert, "wert_marke_cent": marke, "wert_nachweis_cent": nachweis, "verwendung": verwendung}
        if verwendung == "content":
            k = kategorie or ("gwg" if wert <= 80000 else "anlage")
            if k not in KATEGORIEN:
                raise ValueError("Bitte eine Kategorie fuer die Ware waehlen.")
            t = _teil_pruefen({"text": d["text"], "betrag": eur(wert).replace(" €", ""), "kategorie": k,
                               "nutzungsdauer_jahre": nutzungsdauer_jahre})
            d["kategorie"] = k
            if t.get("nutzungsdauer_jahre"):
                d["nutzungsdauer_jahre"] = t["nutzungsdauer_jahre"]
        d["nachweise"] = [{k: b["daten"][k] for k in ("pfad", "sha256")}
                          for b in (self.bh.beleg_ablegen(inhalt, name, art="beleg", bezug=nummer, von=von)
                                    for inhalt, name in (nachweise or []) if inhalt)]
        self.bh.erfassen("rechnung_ware_erhalten", d, von=von)
        return {"wert_cent": wert, "verwendung": verwendung, "kategorie": d.get("kategorie", "")}

    def ware_stornieren(self, nummer: str, grund: str, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund angeben.")

        def pruefe(eintraege):
            r = self._falte(eintraege)[1].get(nummer)
            if not r:
                raise KeyError(nummer)
            if not r.get("ware_erhalten"):
                raise ValueError("Es ist kein Ware-Eingang erfasst.")
        self.bh.erfassen_geprueft("rechnung_ware_storniert", {"nummer": nummer, "grund": grund}, von=von, pruefe=pruefe)
        return {"storniert": True}

    def zahlung_stornieren(self, nummer: str, index: int, grund: str, *, von: str = "") -> dict:
        """Falsch erfasste Zahlung zuruecknehmen (Eintrag bleibt, Storno mit Grund daneben -- GoBD)."""
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund angeben.")

        def pruefe(eintraege):
            r = self._falte(eintraege)[1].get(nummer)
            if not r:
                raise KeyError(nummer)
            if not isinstance(index, int) or not 0 <= index < len(r["zahlungen"]):
                raise ValueError("Diese Zahlung gibt es nicht.")
            if r["zahlungen"][index].get("storniert"):
                raise ValueError("Diese Zahlung ist bereits storniert.")
            if r["status"] == "storniert":
                raise ValueError(f"{nummer} ist storniert.")
        self.bh.erfassen_geprueft("rechnung_zahlung_storniert", {"nummer": nummer, "index": index, "grund": grund},
                                  von=von, pruefe=pruefe)
        return {"storniert": index}

    def erinnerung_merken(self, nummer: str, termin: dict, *, von: str = "") -> None:
        self.bh.erfassen("rechnung_erinnerung", {"nummer": nummer, "termin": termin}, von=von)

    # -- PDF -----------------------------------------------------------------------------------------------------

    def vorschau_pdf(self, eid: str, firmendaten: dict) -> bytes:
        x = self.get(eid)
        if not x or x.get("status") != "entwurf":
            raise KeyError(eid)
        heute = jetzt().date()
        return self._pdf(x | {"nummer": "ENTWURF", "rechnungsdatum": heute.isoformat(),
                              "faellig_am": (heute + timedelta(days=int(x.get("zahlungsziel_tage") or 0))).isoformat()},
                         firmendaten)

    def _pdf(self, r: dict, firmendaten: dict) -> bytes:
        r = self._summen(r)
        f = self.kunden.firma(r["firma"]) or {}
        ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == r.get("ansprechpartner")), None)
        storno = r.get("art") == "storno"
        art = "Stornorechnung" if storno else "Rechnung"
        lv, lb = r.get("leistung_von"), r.get("leistung_bis")
        leistung = (f"{datum_de(lv)} – {datum_de(lb)}" if lv and lb else datum_de(lv or lb))
        infos = [f"Rechnungsdatum: {datum_de(r['rechnungsdatum'])}", f"{art}: {r['nummer']}",
                 f"Kundennummer: {r['firma']}", f"Leistung: {leistung}" if leistung else ""]
        if storno:
            infos.append(f"Storno zu: {r['bezug']}")
        elif r.get("auftrag"):
            infos.append(f"Auftrag: {r['auftrag']}")
        einleitung = (f"hiermit stornieren wir die Rechnung {r['bezug']}. Grund: {r.get('grund', '')}" if storno else
                      r.get("einleitung") or "vielen Dank für Ihren Auftrag. Wir berechnen Ihnen folgende Leistungen:")
        w, g = ware_geld(r["summe_cent"], r.get("ware")) if not storno else (0, r["summe_cent"])
        zahlung = ("" if storno or not g else f"Bitte überweisen Sie {'den Geldanteil' if w else 'den Rechnungsbetrag'} von "
                   f"{eur(g)} bis zum {datum_de(r['faellig_am'])} unter Angabe der Rechnungsnummer {r['nummer']} auf das "
                   "unten genannte Konto.")
        if not storno and w:
            zahlung = " ".join(ware_hinweis(r["summe_cent"], r.get("ware"), rechnung=True) + ([zahlung] if zahlung else []))
        if r.get("layout") == "hanserautisch":
            b = r.get("bloecke") or _bloecke({})
            gruppen: dict[str, tuple] = {}
            for p in r["positionen"]:
                g = gruppen.setdefault(p.get("gruppe") or "Leistungen",
                                       (p.get("gruppe") or "Leistungen", p.get("gruppe_farbe", "blau"), []))
                g[2].append({"name": p["beschreibung"], "detail": p.get("detail", ""), "menge": p["menge"],
                             "einheit": p.get("einheit", "") if p.get("einheit", "").lower() == "monat" else "",
                             "betrag_cent": p["gesamt_cent"]})
            return hanserautisch_pdf(
                art=art, nummer=r["nummer"], firma=firmendaten, logo=self.bh.dir / "logo.jpg",
                empfaenger=_empfaenger(f, ap), untertitel=r.get("titel") or "", infos=[i for i in infos if i],
                anrede=anrede_moin(ap, f.get("name", "")), einleitung=einleitung,
                texte={"kontakt": b.get("kontakt", ""), "fuss": ""}, zeige_kalkulation=False, zeige_kennzahlen=False,
                gruppen=list(gruppen.values()), summen=r["summen"], zuschlag_liste=None, fuss_zusatz=zahlung)
        return beleg_pdf(
            art=art, nummer=r["nummer"], firma=firmendaten, empfaenger=_empfaenger(f, ap),
            infos=[(i.split(": ", 1)[0], i.split(": ", 1)[1]) for i in infos if i],
            einleitung=anrede_moin(ap, f.get("name", "")) + "\n\n" + einleitung, positionen=r["positionen"],
            summe_cent=r["summe_cent"], hinweise=[HINWEIS_19, zahlung], schluss="")


class _Nichts(Exception):
    pass


def rechnung_mail_text(r: dict, ap: dict | None, firmendaten: dict) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,"
    storno = r.get("art") == "storno"
    betreff = (f"Stornorechnung {r['nummer']} zu {r.get('bezug')}" if storno else f"Rechnung {r['nummer']}"
               + (f" – {r['titel']}" if r.get("titel") else ""))
    text = (f"{anrede}\n\nanbei erhalten Sie " + (f"die Stornorechnung {r['nummer']} zur Rechnung {r.get('bezug')}."
                                                  if storno else
                                                  f"unsere Rechnung {r['nummer']} über {eur(r['summe_cent'])}, zahlbar bis "
                                                  f"{datum_de(r['faellig_am'])}.")
            + "\n\nBei Fragen melden Sie sich gerne.\n\nMit freundlichen Grüßen\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text


def ueberfaellige(store: RechnungStore) -> list[dict]:
    heute = jetzt().date().isoformat()
    _, rechnungen = store._stand()
    return [r for r in rechnungen.values() if r["status"] == "offen" and r.get("art") != "storno"
            and r.get("faellig_am", "9") < heute]
