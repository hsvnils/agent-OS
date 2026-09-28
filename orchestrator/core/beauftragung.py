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

from .angebote import AngebotStore, _bloecke, _empfaenger, anrede_moin, inhalt_hash, summen
from .beleg_pdf import HINWEIS_19, beleg_pdf, datum_de, eur, hanserautisch_pdf
from .buchhaltung import Buchhaltung, jetzt
from .kunden import KundenStore

STATUS = ("beauftragt", "erledigt", "storniert")
_UEBERNAHME = ("firma", "ansprechpartner", "titel", "positionen", "zuschlaege", "rabatt_prozent", "layout", "bloecke")


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
            elif t == "auftrag_status":
                a = out[d["nummer"]]
                if d["status"] in STATUS:
                    a["status"] = d["status"]
                    a[d["status"] + "_am"] = e["ts"]
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
        return a | {"positionen": pos, "summen": sm, "summe_cent": sm["gesamt_cent"], "inhalt": inhalt_hash(a)}

    # -- Lesen ---------------------------------------------------------------------------------------------------

    def liste(self) -> list[dict]:
        firmen = {f["nummer"]: f["name"] for f in self.kunden.firmen()}
        out = []
        for a in self._falte(self.bh.eintraege()).values():
            r = self._anreichern(a)
            out.append({k: r.get(k) for k in ("nummer", "angebot", "firma", "titel", "datum", "leistung_von",
                                               "leistung_bis", "status", "summe_cent")} | {"firma_name": firmen.get(a["firma"], "")})
        return sorted(out, key=lambda x: x["nummer"], reverse=True)

    def auftrag(self, nummer: str) -> dict | None:
        a = self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())
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
            return {k: a.get(k) for k in _UEBERNAHME} | {"angebot": angebot_nr, "datum": heute.isoformat(),
                                                         "leistung_von": lv, "leistung_bis": lb,
                                                         "notiz": str(notiz or "").strip()[:2000]}

        ev = self.bh.mit_nummer("AB", "auftrag_angelegt", daten, jahr=heute.year, bezug=angebot_nr, von=von,
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
                      von: str = "") -> dict:
        """erledigt / storniert (nur aus „beauftragt"); `status="gesendet"` protokolliert nur den Mailversand."""
        nummer = (nummer or "").strip().upper()
        if status not in ("erledigt", "storniert", "gesendet"):
            raise ValueError("Status muss erledigt, storniert oder gesendet sein.")

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if status != "gesendet" and a["status"] != "beauftragt":
                raise ValueError(f"{nummer}: von „{a['status']}“ nicht nach „{status}“ moeglich.")
        daten = {"nummer": nummer, "status": status}
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
        einleitung = (f"vielen Dank für Ihren Auftrag. Hiermit bestätigen wir die Beauftragung auf Grundlage unseres "
                      f"Angebots {a['angebot']}" + (f" für den Leistungszeitraum {zeitraum}" if zeitraum else "") + ".")
        hinweise = [HINWEIS_19] + ([f"Anmerkung: {a['notiz']}"] if a.get("notiz") else [])
        if a.get("layout") == "hanserautisch":
            b = a.get("bloecke") or _bloecke({})
            gruppen: dict[str, tuple] = {}
            for p in a["positionen"]:
                g = gruppen.setdefault(p.get("gruppe") or "Leistungen",
                                       (p.get("gruppe") or "Leistungen", p.get("gruppe_farbe", "blau"), []))
                g[2].append({"name": p["beschreibung"], "detail": p.get("detail", ""), "menge": p["menge"],
                             "einheit": p.get("einheit", "") if p.get("einheit", "").lower() == "monat" else "",
                             "betrag_cent": p["gesamt_cent"]})
            return hanserautisch_pdf(
                art="Auftragsbestätigung", nummer=a["nummer"], firma=firmendaten, logo=self.bh.dir / "logo.jpg",
                empfaenger=_empfaenger(f, ap), untertitel=a.get("titel") or b.get("untertitel", ""),
                infos=[f"Tangstedt, den {datum_de(a['datum'])}", f"Auftrag: {a['nummer']}", f"Angebot: {a['angebot']}",
                       f"Kundennummer: {a['firma']}"] + ([f"Leistung: {zeitraum}"] if zeitraum else []),
                anrede=anrede_moin(ap, f.get("name", "")), einleitung=einleitung, texte=b | {"fuss": b.get("fuss", "")},
                zeige_kalkulation=False, zeige_kennzahlen=False, gruppen=list(gruppen.values()), summen=a["summen"],
                zuschlag_liste=None, fuss_zusatz=" ".join(hinweise[1:]))
        return beleg_pdf(
            art="Auftragsbestätigung", nummer=a["nummer"], firma=firmendaten, empfaenger=_empfaenger(f, ap),
            infos=[("Datum", datum_de(a["datum"])), ("Angebot", a["angebot"]), ("Kundennummer", a["firma"]),
                   ("Leistung", zeitraum)],
            einleitung=anrede_moin(ap, f.get("name", "")) + "\n\n" + einleitung, positionen=a["positionen"],
            summe_cent=a["summe_cent"], hinweise=hinweise, schluss="")

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


def auftrag_mail_text(a: dict, ap: dict | None, firmendaten: dict) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,"
    betreff = f"Auftragsbestätigung {a['nummer']}" + (f" – {a['titel']}" if a.get("titel") else "")
    text = (f"{anrede}\n\nvielen Dank für Ihren Auftrag. Anbei erhalten Sie unsere Auftragsbestätigung {a['nummer']} "
            f"zu unserem Angebot {a['angebot']} über {eur(a['summe_cent'])}.\n\n"
            "Bei Fragen melden Sie sich gerne.\n\nMit freundlichen Grüßen\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text
