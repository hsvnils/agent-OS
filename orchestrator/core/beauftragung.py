"""Beauftragung / Auftragsbestaetigung (KUNDEN_FINANZEN_ROADMAP.md, Etappe 4): aus einem angenommenen Angebot `AN-`
wird ein Auftrag `AB-JJJJ-NNNN` -- Bruecke zur Rechnung (Etappe 5).

Ereignisse in der Buchhaltungs-Kette:
- `auftrag_angelegt` -- uebernimmt Firma, Ansprechpartner, Titel, Positionen, Zuschlaege, Rabatt und Textbausteine aus dem
  Angebot (eingefroren) plus Leistungszeitraum/Notiz; genau **ein** Auftrag je Angebot;
- `auftrag_geaendert` -- nur Leistungszeitraum und Notiz, nur solange „beauftragt";
- `auftrag_pdf_abgelegt` / `auftrag_status` (erledigt, storniert; gesendet = Mail-Daten) -- wie bei Angeboten.
Positionen aendern sich im Auftrag nicht mehr; Abweichungen regelt spaeter die Rechnung (Etappe 5).
"""
from __future__ import annotations

from datetime import date

from .angebote import (AngebotStore, _bloecke, _empfaenger, _summen_zeilen, anrede_moin, inhalt_hash, pdf_posten, pdf_posten_standard,
                       summen, ware_hinweis)
from .beleg_pdf import HINWEIS_19, beleg_pdf, datum_de, eur, hanserautisch_pdf
from .buchhaltung import Buchhaltung, jetzt
from .kunden import KundenStore
from . import zahlungsbedingungen as zb

STATUS = ("beauftragt", "erledigt", "storniert")
_UEBERNAHME = ("firma", "ansprechpartner", "titel", "positionen", "zuschlaege", "rabatt_prozent", "layout", "bloecke", "ware",
               "zahlung")


def _datum(v, feld: str) -> str:
    if v in (None, ""):
        return ""
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{feld}: ungueltiges Datum (JJJJ-MM-TT).") from None


class AuftragBuch:
    def __init__(self, bh: Buchhaltung, kunden: KundenStore, angebote: AngebotStore):
        self.bh, self.kunden, self.angebote = bh, kunden, angebote

    # -- Faltung -------------------------------------------------------------------------------------------------

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t}
            if t == "auftrag_angelegt":
                out[d["nummer"]] = dict(d) | {"status": "beauftragt", "angelegt": e["ts"], "pdfs": [], "verlauf": [spur]}
            elif not str(t).startswith("auftrag_") or d.get("nummer") not in out:
                continue
            elif t == "auftrag_geaendert":
                a = out[d["nummer"]]
                a.update(d.get("felder", {}))
                a["verlauf"].append(spur | {"felder": sorted(d.get("felder", {}))})
            elif t == "auftrag_pdf_abgelegt":
                a = out[d["nummer"]]
                a["pdfs"].append({k: d.get(k) for k in ("pfad", "sha256", "an")} | {"ts": e["ts"]})
                a["verlauf"].append(spur | {"an": d.get("an", "")})
            elif t == "auftrag_bericht":                  # PROJEKTBERICHT P3: Entwurf (Fazit, Haken Stunden/km)
                a = out[d["nummer"]]
                a["bericht"] = {k: d.get(k) for k in ("fazit", "stunden", "km")} | {"geaendert": e["ts"]}
            elif t == "auftrag_bericht_versendet":        # P3: eingefrorenes PDF in der Firmenakte
                a = out[d["nummer"]]
                a.setdefault("berichte", []).append({k: d.get(k) for k in ("akte_id", "sha256", "an", "betreff", "version")}
                                                    | {"ts": e["ts"]})
                a["verlauf"].append(spur | {"an": d.get("an", "")})
            elif t == "auftrag_bericht_entfaellt":        # P3: bewusst kein Bericht (z. B. reiner Dreh ohne Postings)
                a = out[d["nummer"]]
                a["bericht_entfaellt"] = d.get("grund", "")
                a["verlauf"].append(spur | {"grund": d.get("grund", "")})
            elif t == "auftrag_status":
                a = out[d["nummer"]]
                if d["status"] in STATUS:
                    a["status"] = d["status"]
                    a[d["status"] + "_am"] = e["ts"]
                    if d["status"] == "erledigt":                # Etappe 30: „Geliefert“ mit Lieferdatum
                        a["geliefert_am"] = d.get("datum") or e["ts"][:10]
                    elif d["status"] == "beauftragt":            # wieder geoeffnet (Nachlieferung)
                        a["geliefert_am"] = ""
                if d.get("mail"):
                    a["gesendet_mail"] = d["mail"]
                    a["gesendet_am"] = e["ts"]
                a["verlauf"].append(spur | {"status": d["status"], "grund": d.get("grund", "")}
                                    | ({"mail_an": d["mail"].get("an", ""), "betreff": d["mail"].get("betreff", "")}
                                       if d.get("mail") else {}))
        return out

    def _anreichern(self, a: dict) -> dict:
        from .beleg_pdf import positions_summe
        pos = [p | {"gesamt_cent": positions_summe(p["menge"], p["einzelpreis_cent"])} for p in a["positionen"]]
        sm = summen(a["positionen"], a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0)
        w = min(int((a.get("ware") or {}).get("wert_cent") or 0), sm["gesamt_cent"])
        return a | {"positionen": pos, "summen": sm, "summe_cent": sm["gesamt_cent"], "inhalt": inhalt_hash(a),
                    "ware_cent": w, "geld_cent": sm["gesamt_cent"] - w}

    # -- Lesen ---------------------------------------------------------------------------------------------------

    def liste(self) -> list[dict]:
        firmen = {f["nummer"]: f["name"] for f in self.kunden.firmen()}
        e = self.bh.eintraege()
        out = []
        for a in abschluss(self._falte(e), e).values():
            r = self._anreichern(a)
            out.append({k: r.get(k) for k in ("nummer", "angebot", "firma", "titel", "datum", "leistung_von",
                                               "leistung_bis", "status", "summe_cent", "abgeschlossen")}
                       | {"firma_name": firmen.get(a["firma"], "")})
        return sorted(out, key=lambda x: x["nummer"], reverse=True)

    def auftrag(self, nummer: str) -> dict | None:
        e = self.bh.eintraege()
        a = abschluss(self._falte(e), e).get((nummer or "").strip().upper())
        return self._anreichern(a) if a else None

    # -- Schreiben -----------------------------------------------------------------------------------------------

    def aus_angebot(self, angebot_nr: str, *, leistung_von: str = "", leistung_bis: str = "", notiz: str = "",
                    von: str = "") -> dict:
        """Auftrag aus einem **angenommenen** Angebot anlegen (genau einer je Angebot)."""
        angebot_nr = (angebot_nr or "").strip().upper()
        lv, lb = _datum(leistung_von, "Leistung von"), _datum(leistung_bis, "Leistung bis")
        if lv and lb and lb < lv:
            raise ValueError("Leistungszeitraum: Ende liegt vor dem Beginn.")
        heute = jetzt().date()

        def pruefe(eintraege):
            a = AngebotStore._falte(eintraege).get(angebot_nr)
            if not a:
                raise KeyError(angebot_nr)
            if a["status"] != "angenommen":
                raise ValueError(f"{angebot_nr} ist {a['status']} -- ein Auftrag entsteht nur aus einem angenommenen Angebot.")
            if a.get("auftrag"):
                raise ValueError(f"Zu {angebot_nr} gibt es schon den Auftrag {a['auftrag']}.")

        def daten(eintraege):                                 # unter der Sperre: Stand des Angebots uebernehmen
            a = AngebotStore._falte(eintraege)[angebot_nr]
            d = {k: a.get(k) for k in _UEBERNAHME} | {"angebot": angebot_nr, "datum": heute.isoformat(),
                                                      "leistung_von": lv, "leistung_bis": lb,
                                                      "notiz": str(notiz or "").strip()[:2000]}
            vk = zb.vorkasse_cent(a.get("zahlung"), AngebotStore._anreichern(a, heute)["geld_cent"])
            if vk:                                            # Etappe 18: Vorkasse-Betrag und -Frist einfrieren
                d |= {"vorkasse_cent": vk, "vorkasse_faellig": zb.vorkasse_frist(a["zahlung"], heute)}
            return d

        ev = self.bh.mit_nummer("AB", "auftrag_angelegt", daten, jahr=heute.year, bezug=angebot_nr, von=von,
                                pruefe=pruefe)
        return {"nummer": ev["daten"]["nummer"]}

    def anlegen(self, daten: dict, *, leistung_von: str = "", leistung_bis: str = "", notiz: str = "",
                von: str = "") -> dict:
        """Etappe 31 (CEO 2026-10-02: „Nicht jeder Auftrag braucht ein Angebot“): Auftrag direkt anlegen -- gleiche
        Felder und Pruefregeln wie ein Angebot (Firma, Ansprechpartner, Titel, Positionen, Zuschlaege/Rabatt, Layout,
        Ware, Zahlungsbedingungen inkl. Vorkasse), Feld „angebot“ bleibt leer."""
        from .angebote import _kopf, _positionen, _schalter
        if not isinstance(daten, dict):
            raise ValueError("Ungueltige Eingabe.")
        lv, lb = _datum(leistung_von, "Leistung von"), _datum(leistung_bis, "Leistung bis")
        if lv and lb and lb < lv:
            raise ValueError("Leistungszeitraum: Ende liegt vor dem Beginn.")
        heute = jetzt().date()
        katalog = getattr(self.angebote, "katalog", None)
        kopf = {"ansprechpartner": "", "titel": "", "zuschlaege": [], "rabatt_prozent": 0,
                "layout": "hanserautisch" if katalog else "standard"}
        kopf.update({k: v for k, v in _kopf(daten).items() if k in _UEBERNAHME})
        if not str(kopf.get("titel") or "").strip():
            raise ValueError("Bitte einen Titel angeben (z. B. „Social-Media-Kampagne Herbst“).")
        self.angebote._ziel_vorschlag(kopf, daten.get("zahlung"), kopf.get("firma") or "")
        if kopf["layout"] == "hanserautisch" and "bloecke" not in kopf:
            from .angebote import _bloecke
            kopf["bloecke"] = _bloecke(katalog.laden()["texte"] if katalog else {})
        _schalter(kopf, daten)
        pos = _positionen(daten.get("positionen"))
        sm = summen(pos, kopf.get("zuschlaege") or [], kopf.get("rabatt_prozent") or 0)
        geld = sm["gesamt_cent"] - min(int((kopf.get("ware") or {}).get("wert_cent") or 0), sm["gesamt_cent"])

        def pruefe(eintraege):
            self.angebote._pruefe_bezug(eintraege, kopf)

        def bauen(eintraege):
            d = {k: kopf.get(k) for k in _UEBERNAHME if k in kopf} | {
                "positionen": pos, "angebot": "", "datum": heute.isoformat(), "leistung_von": lv, "leistung_bis": lb,
                "notiz": str(notiz or "").strip()[:2000]}
            vk = zb.vorkasse_cent(kopf.get("zahlung"), geld)
            if vk:
                d |= {"vorkasse_cent": vk, "vorkasse_faellig": zb.vorkasse_frist(kopf["zahlung"], heute)}
            return d

        ev = self.bh.mit_nummer("AB", "auftrag_angelegt", bauen, jahr=heute.year, bezug=kopf["firma"], von=von,
                                pruefe=pruefe)
        return {"nummer": ev["daten"]["nummer"]}

    def aendern(self, nummer: str, felder: dict, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        neu = {}
        if "leistung_von" in felder:
            neu["leistung_von"] = _datum(felder["leistung_von"], "Leistung von")
        if "leistung_bis" in felder:
            neu["leistung_bis"] = _datum(felder["leistung_bis"], "Leistung bis")
        if "notiz" in felder:
            neu["notiz"] = str(felder["notiz"] or "").strip()[:2000]
        diff: dict = {}

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] != "beauftragt":
                raise ValueError(f"{nummer} ist {a['status']} und kann nicht mehr geaendert werden.")
            diff.update({k: v for k, v in neu.items() if a.get(k) != v})
            rest = a | diff
            if rest.get("leistung_von") and rest.get("leistung_bis") and rest["leistung_bis"] < rest["leistung_von"]:
                raise ValueError("Leistungszeitraum: Ende liegt vor dem Beginn.")
            if not diff:
                raise _Nichts()
        try:
            self.bh.erfassen_geprueft("auftrag_geaendert", {"nummer": nummer, "felder": diff}, von=von, pruefe=pruefe)
        except _Nichts:
            return {"geaendert": []}
        return {"geaendert": sorted(diff)}

    def status_setzen(self, nummer: str, status: str, *, grund: str = "", mail: dict | None = None,
                      von: str = "", datum: str = "") -> dict:
        """erledigt (= „Geliefert“, Etappe 30, mit Lieferdatum) / storniert (nur aus „beauftragt“); `beauftragt` =
        wieder oeffnen (nur aus „erledigt“, mit Grund); `status="gesendet"` protokolliert nur den Mailversand."""
        nummer = (nummer or "").strip().upper()
        if status not in ("erledigt", "storniert", "gesendet", "beauftragt"):
            raise ValueError("Status muss geliefert, storniert, wieder offen oder gesendet sein.")
        if status == "beauftragt" and not str(grund or "").strip():
            raise ValueError("Bitte kurz begruenden, warum der Auftrag wieder geoeffnet wird.")
        if status == "erledigt" and datum:
            try:
                datum = date.fromisoformat(str(datum)[:10]).isoformat()
            except ValueError:
                raise ValueError("Lieferdatum ungueltig.") from None
            if datum > jetzt().date().isoformat():
                raise ValueError("Das Lieferdatum liegt in der Zukunft.")

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            noetig = "erledigt" if status == "beauftragt" else "beauftragt"
            if status != "gesendet" and a["status"] != noetig:
                raise ValueError(f"{nummer}: von „{a['status']}“ nicht nach „{status}“ moeglich.")
        daten = {"nummer": nummer, "status": status} | ({"datum": datum} if status == "erledigt" and datum else {})
        if grund:
            daten["grund"] = str(grund).strip()[:500]
        if mail:
            daten["mail"] = mail
        self.bh.erfassen_geprueft("auftrag_status", daten, von=von, pruefe=pruefe)
        return {"status": status}

    def pdf(self, nummer: str, firmendaten: dict) -> bytes:
        a = self.auftrag(nummer)
        if not a:
            raise KeyError(nummer)
        f = self.kunden.firma(a["firma"]) or {}
        ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
        lv, lb = a.get("leistung_von"), a.get("leistung_bis")
        zeitraum = (f"{datum_de(lv)} – {datum_de(lb)}" if lv and lb else f"ab {datum_de(lv)}" if lv
                    else f"bis {datum_de(lb)}" if lb else "")
        einleitung = ("vielen Dank für Ihren Auftrag. Hiermit bestätigen wir die Beauftragung"
                      + (f" auf Grundlage unseres Angebots {a['angebot']}" if a.get("angebot") else "")   # Etappe 31
                      + (f" für den Leistungszeitraum {zeitraum}" if zeitraum else "") + ".")
        hinweise = ([HINWEIS_19] + ware_hinweis(a["summe_cent"], a.get("ware"))
                    + [x for x in [zb.text(a.get("zahlung"), a["geld_cent"], ab_datum=a["datum"])] if x]
                    + ([f"Anmerkung: {a['notiz']}"] if a.get("notiz") else []))
        if a.get("layout") == "hanserautisch":
            b = a.get("bloecke") or _bloecke({})
            gruppen: dict[str, tuple] = {}
            for p in a["positionen"]:
                g = gruppen.setdefault(p.get("gruppe") or "Leistungen",
                                       (p.get("gruppe") or "Leistungen", p.get("gruppe_farbe", "blau"), []))
                g[2].append({"name": p["beschreibung"], "detail": p.get("detail", ""), "menge": p["menge"],
                             "einheit": p.get("einheit", "") if p.get("einheit", "").lower() == "monat" else "",
                             "betrag_cent": p["gesamt_cent"]} | pdf_posten(p))
            return hanserautisch_pdf(
                art="Auftragsbestätigung", nummer=a["nummer"], firma=firmendaten, logo=self.bh.dir / "logo.jpg",
                empfaenger=_empfaenger(f, ap), untertitel=a.get("titel") or b.get("untertitel", ""),
                infos=[f"Tangstedt, den {datum_de(a['datum'])}", f"Auftrag: {a['nummer']}"] + ([f"Angebot: {a['angebot']}"] if a.get("angebot") else [])
                      + [f"Kundennummer: {a['firma']}"] + ([f"Leistung: {zeitraum}"] if zeitraum else []),
                anrede=anrede_moin(ap, f.get("name", "")), einleitung=einleitung, texte=b | {"fuss": b.get("fuss", "")},
                zeige_kalkulation=False, zeige_kennzahlen=False, gruppen=list(gruppen.values()), summen=a["summen"],
                zuschlag_liste=None, fuss_zusatz=" ".join(hinweise[1:]))
        return beleg_pdf(
            art="Auftragsbestätigung", nummer=a["nummer"], firma=firmendaten, empfaenger=_empfaenger(f, ap),
            infos=[("Datum", datum_de(a["datum"]))] + ([("Angebot", a["angebot"])] if a.get("angebot") else []) + [("Kundennummer", a["firma"]),
                   ("Leistung", zeitraum)],
            einleitung=anrede_moin(ap, f.get("name", "")) + "\n\n" + einleitung, positionen=[x | pdf_posten_standard(x) for x in a["positionen"]],
            summe_cent=a["summe_cent"], hinweise=hinweise, schluss="", summen_zeilen=_summen_zeilen(a["summen"]))

    def pdf_ablegen(self, nummer: str, pdf: bytes, *, an: str = "", von: str = "") -> dict:
        a = self.auftrag(nummer)
        if not a:
            raise KeyError(nummer)
        ev = self.bh.beleg_ablegen(pdf, f"Auftragsbestaetigung_{a['nummer']}.pdf", jahr=int(a["datum"][:4]),
                                   art="geschaeftsbrief", bezug=a["nummer"], von=von)
        d = ev["daten"]
        self.bh.erfassen("auftrag_pdf_abgelegt", {"nummer": a["nummer"], "pfad": d["pfad"], "sha256": d["sha256"],
                                                  "an": an}, von=von)
        return {"pfad": d["pfad"]}


class _Nichts(Exception):
    pass


def abschluss(auftraege: dict[str, dict], eintraege: list[dict]) -> dict[str, dict]:
    """PROJEKTBERICHT P3 (CEO 2026-10-02): **abgeschlossen** = geliefert, Bericht versendet (oder bewusst entfallen) und
    alle Rechnungen zum Auftrag bezahlt. Der Status bleibt „erledigt“ (Geliefert); `abgeschlossen` kommt dazu."""
    from .rechnungen import RechnungStore
    re_je: dict[str, list] = {}
    for r in RechnungStore._falte(eintraege)[1].values():
        if r.get("auftrag") and r["status"] != "storniert" and r.get("art") != "storno":
            re_je.setdefault(r["auftrag"], []).append(r)
    for a in auftraege.values():
        rs = re_je.get(a["nummer"], [])
        bezahlt = any(r.get("art", "rechnung") == "rechnung" for r in rs) and all(r["status"] == "bezahlt" for r in rs)
        bericht = "versendet" if a.get("berichte") else "entfaellt" if a.get("bericht_entfaellt") else ""
        a["abschluss"] = {"geliefert": a["status"] == "erledigt", "bericht": bericht, "bezahlt": bezahlt}
        a["abgeschlossen"] = a["status"] == "erledigt" and bool(bericht) and bezahlt
    return auftraege


def auftrag_mail_text(a: dict, ap: dict | None, firmendaten: dict) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,"
    betreff = f"Auftragsbestätigung {a['nummer']}" + (f" – {a['titel']}" if a.get("titel") else "")
    text = (f"{anrede}\n\nvielen Dank für Ihren Auftrag. Anbei erhalten Sie unsere Auftragsbestätigung {a['nummer']} "
            + (f"zu unserem Angebot {a['angebot']} " if a.get("angebot") else "") + f"über {eur(a['summe_cent'])}.\n\n"
            "Bei Fragen melden Sie sich gerne.\n\nMit freundlichen Grüßen\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text
