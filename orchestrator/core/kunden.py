"""Kunden-Stammdaten (KUNDEN_FINANZEN_ROADMAP.md, Etappe 2): Firmen mit Firmenkundennummer `K-00001`, Ansprechpartner
mit eigener Nummer `AP-00001`, Zuordnung bestehender Collab-CRM-Firmen.

Etappe 14 (CEO 2026-09-29): eigene Nummernkreise je Rolle -- Kunden `K-`, Lieferanten/Dienstleister `L-`, Partner `P-`.
Eine Firma behaelt ihre erste Nummer als festen Schluessel; bekommt sie eine andere Rolle (z. B. die schon als `K-00003`
angelegten Lieferanten), vergibt `rollennummer_sichern` zusaetzlich die Nummer des passenden Kreises
(`firma_nummer_ergaenzt`). Beide Nummern finden die Firma; angezeigt wird die Rollennummer (`anzeige`).

Liegt als Ereignisse in der Hash-Kette der Buchhaltung (`core/buchhaltung.py`): Anlegen und jede Aenderung sind eigene
Eintraege mit Akteur und Zeit -> vollstaendiger Verlauf, nichts wird ueberschrieben. Der aktuelle Stand entsteht durch
Faltung. Loeschen gibt es nicht (Aufbewahrung, GoBD); stattdessen `aktiv = False`.

Das Collab-CRM (`core/crm.py`, Schluessel = Anzeigename) bleibt unveraendert; eine Collab-Firma wird hier per Name
genau einer Firmenkundennummer zugeordnet.
"""
from __future__ import annotations

import re

from .buchhaltung import Buchhaltung
from .crm import _key as _crm_key   # gleicher Schluessel wie im Collab-CRM

TYPEN = ("kunde", "lieferant", "partner")
KREIS = {"kunde": "K", "lieferant": "L", "partner": "P"}
FIRMA_FELDER = ("name", "typ", "strasse", "plz", "ort", "land", "ustid", "steuernummer", "rechnungsmail", "telefon",
                "website", "zahlungsziel_tage", "notiz", "aktiv", "verbraucher",
                # Etappe 14: unsere Kundennummer dort, Zahlungsweg, Rechnungs-Absender (Mail/Domain), Vertraege/Abos
                "kundennummer_bei", "zahlungsweg", "rechnungs_absender", "vertraege",
                "handelsregister")                                     # Etappe 22: aus dem Impressum
VERTRAG_FELDER = ("bezeichnung", "nummer", "notiz")
AP_FELDER = ("vorname", "nachname", "rolle", "mail", "telefon", "notiz", "aktiv")
_MAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# Zahlungsdienste versenden Belege fuer viele Haendler -> nie als Rechnungs-Absender einer Firma lernen/zuordnen
ZAHLDIENSTE = re.compile(r"(?i)@(?:[\w-]+\.)*(?:paypal|stripe|klarna|sumup|mollie|adyen|braintreegateway)\.")
_MAX = 500


def _key(name: str) -> str:
    return " ".join((name or "").split()).lower()


def _bereinige(daten: dict, felder: tuple[str, ...]) -> dict:
    """Nur bekannte Felder, Text getrimmt und gekuerzt, Typen geprueft. ValueError bei ungueltigen Werten."""
    if not isinstance(daten, dict):
        raise ValueError("Ungueltige Eingabe.")
    out = {}
    for k, v in daten.items():
        if k not in felder:
            continue
        if k == "aktiv":
            out[k] = bool(v)
        elif k == "vertraege":                            # [{bezeichnung, nummer, notiz}] -- Vertrags-/Abo-/Policen-Nr.
            if v in (None, ""):
                out[k] = []
                continue
            if not isinstance(v, list) or len(v) > 30:
                raise ValueError("Vertraege: Liste mit hoechstens 30 Eintraegen erwartet.")
            out[k] = [z for z in ({f: str((x or {}).get(f) or "").strip()[:200] for f in VERTRAG_FELDER}
                                  for x in v if isinstance(x, dict)) if z["bezeichnung"] or z["nummer"]]
        elif k == "verbraucher":                          # Privatperson (§ 13 BGB) -> Mahnung: 5 statt 9 Punkte, keine 40 €
            out[k] = v is True or str(v).strip().lower() in ("1", "true", "ja", "on")
        elif k == "zahlungsziel_tage":
            if v in (None, ""):
                out[k] = None
                continue
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise ValueError("Zahlungsziel muss eine ganze Zahl (Tage) sein.") from None
            if not 0 <= n <= 365:
                raise ValueError("Zahlungsziel muss zwischen 0 und 365 Tagen liegen.")
            out[k] = n
        else:
            out[k] = str(v if v is not None else "").strip()[:_MAX]
    if "typ" in out and out["typ"] not in TYPEN:
        raise ValueError(f"Typ muss einer von {', '.join(TYPEN)} sein.")
    for mk in ("rechnungsmail", "mail"):
        if out.get(mk) and not _MAIL.fullmatch(out[mk]):
            raise ValueError(f"Ungueltige Mail-Adresse: {out[mk]}")
    return out


class KundenStore:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh

    # -- Faltung -------------------------------------------------------------------------------------------------

    @staticmethod
    def _falte(eintraege: list[dict]) -> tuple[dict, dict]:
        firmen: dict[str, dict] = {}
        aps: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t, "seq": e["seq"]}
            if t == "firma_angelegt":
                f = {k: d.get(k) for k in FIRMA_FELDER} | {"nummer": d["nummer"], "angelegt": e["ts"],
                                                            "collab": [], "verlauf": [], "nummern": [d["nummer"]]}
                f["aktiv"] = d.get("aktiv", True) is not False
                f["verlauf"].append(spur | {"felder": {k: v for k, v in d.items() if k != "nummer"}})
                firmen[d["nummer"]] = f
            elif t == "firma_geaendert" and d.get("nummer") in firmen:
                f = firmen[d["nummer"]]
                f.update(d.get("felder", {}))
                f["verlauf"].append(spur | {"felder": d.get("felder", {})})
            elif t == "firma_nummer_ergaenzt" and d.get("firma") in firmen:     # Etappe 14: Rollennummer (L-/P-/K-)
                firmen[d["firma"]]["nummern"].append(d["nummer"])
                firmen[d["firma"]]["verlauf"].append(spur | {"felder": {"nummer_ergaenzt": d["nummer"]}})
            elif t == "collab_zugeordnet":
                for f in firmen.values():                      # eine Collab-Firma gehoert genau einer Nummer
                    if d["collab"] in f["collab"]:
                        f["collab"].remove(d["collab"])
                if d.get("nummer") in firmen:
                    firmen[d["nummer"]]["collab"].append(d["collab"])
                    firmen[d["nummer"]]["verlauf"].append(spur | {"felder": {"collab": d.get("name", d["collab"])}})
            elif t == "collab_geloest" and d.get("nummer") in firmen:
                f = firmen[d["nummer"]]
                if d["collab"] in f["collab"]:
                    f["collab"].remove(d["collab"])
                f["verlauf"].append(spur | {"felder": {"collab_entfernt": d.get("name", d["collab"])}})
            elif t == "ansprechpartner_angelegt":
                a = {k: d.get(k) for k in AP_FELDER} | {"nummer": d["nummer"], "firma": d.get("firma"),
                                                         "angelegt": e["ts"], "verlauf": []}
                a["aktiv"] = d.get("aktiv", True) is not False
                a["verlauf"].append(spur | {"felder": {k: v for k, v in d.items() if k != "nummer"}})
                aps[d["nummer"]] = a
            elif t == "ansprechpartner_geaendert" and d.get("nummer") in aps:
                a = aps[d["nummer"]]
                a.update(d.get("felder", {}))
                a["verlauf"].append(spur | {"felder": d.get("felder", {})})
        for f in firmen.values():
            f["anzeige"] = anzeige_nummer(f)
            f["luecken"] = luecken(f)
            f["vertraege"] = f.get("vertraege") or []
        return firmen, aps

    def _stand(self) -> tuple[dict, dict]:
        return self._falte(self.bh.eintraege())

    @staticmethod
    def haupt(firmen: dict, nummer: str) -> str:
        """Fester Schluessel einer Firma zu jeder ihrer Nummern (K-/L-/P-), sonst ''."""
        nummer = (nummer or "").strip().upper()
        if nummer in firmen:
            return nummer
        return next((f["nummer"] for f in firmen.values() if nummer in f.get("nummern", [])), "")

    # -- Lesen ---------------------------------------------------------------------------------------------------

    def firmen(self, *, suche: str = "", nur_aktive: bool = False) -> list[dict]:
        firmen, aps = self._stand()
        q = _key(suche)
        out = []
        for f in firmen.values():
            eigene = [a for a in aps.values() if a["firma"] == f["nummer"]]
            if nur_aktive and not f["aktiv"]:
                continue
            if q:
                heu = " ".join(str(x or "") for x in (" ".join(f["nummern"]), f["name"], f["ort"], f["rechnungsmail"],
                                                        " ".join(f["collab"]), f.get("kundennummer_bei"),
                                                        " ".join(v["nummer"] for v in f["vertraege"])))
                heu += " " + " ".join(f"{a['nummer']} {a['vorname']} {a['nachname']} {a['mail']}" for a in eigene)
                if q not in _key(heu):
                    continue
            out.append({k: v for k, v in f.items() if k != "verlauf"}
                       | {"ansprechpartner": len([a for a in eigene if a["aktiv"]])})
        return sorted(out, key=lambda f: f["nummer"])

    def firma(self, nummer: str) -> dict | None:
        firmen, aps = self._stand()
        f = firmen.get(self.haupt(firmen, nummer))
        if not f:
            return None
        eigene = sorted((a for a in aps.values() if a["firma"] == f["nummer"]), key=lambda a: a["nummer"])
        return f | {"ansprechpartner_liste": eigene}

    def collab_zuordnung(self) -> dict[str, str]:
        """Collab-Schluessel -> Firmenkundennummer."""
        firmen, _ = self._stand()
        return {c: f["nummer"] for f in firmen.values() for c in f["collab"]}

    # -- Schreiben -----------------------------------------------------------------------------------------------

    def firma_anlegen(self, daten: dict, *, von: str = "", trotz_dublette: bool = False) -> dict:
        d = _bereinige(daten, FIRMA_FELDER)
        if not d.get("name"):
            raise ValueError("Firmenname fehlt.")
        d.setdefault("typ", "kunde")
        d["aktiv"] = True

        def pruefe(eintraege):
            if trotz_dublette:
                return
            firmen, _ = self._falte(eintraege)
            gleich = [f["nummer"] for f in firmen.values() if _key(f["name"]) == _key(d["name"])]
            if gleich:
                raise DubletteFehler(f"Es gibt schon eine Firma mit diesem Namen ({', '.join(gleich)}).", gleich)

        ev = self.bh.mit_nummer(KREIS[d["typ"]], "firma_angelegt", d, bezug=d["name"], von=von, pruefe=pruefe)
        return {"nummer": ev["daten"]["nummer"]}

    def rollennummer_sichern(self, nummer: str, *, von: str = "") -> str:
        """Hat die Firma noch keine Nummer im Kreis ihrer Rolle (Lieferant -> L-, Partner -> P-, Kunde -> K-), wird sie
        vergeben (atomar, protokolliert). Rueckgabe: die Rollennummer."""
        ergebnis = {}

        def daten(eintraege):
            firmen, _ = self._falte(eintraege)
            h = self.haupt(firmen, nummer)
            if not h:
                raise KeyError(nummer)
            f = firmen[h]
            kreis = KREIS.get(f.get("typ") or "kunde", "K")
            vorhanden = [n for n in f["nummern"] if n.startswith(kreis + "-")]
            if vorhanden:
                ergebnis["nummer"] = vorhanden[-1]
                raise KeineAenderung()
            ergebnis["kreis"] = kreis
            return {"firma": h}
        try:
            ev = self.bh.mit_nummer(lambda: ergebnis["kreis"], "firma_nummer_ergaenzt", daten, bezug=nummer, von=von)
        except KeineAenderung:
            return ergebnis["nummer"]
        return ev["daten"]["nummer"]

    def finde(self, name: str = "", absender: str = "", *, firmen: dict | None = None) -> str:
        """Passende Firma zu einem Beleg: Rechnungs-Absender (Adresse oder Domain) > gleicher Name > gleiches erstes
        Namenswort (mind. 4 Zeichen, z. B. „Apple“ -> „Apple Distribution International“). Nur Vorschlag."""
        firmen = firmen if firmen is not None else self._stand()[0]
        aktiv = [f for f in firmen.values() if f["aktiv"]]
        a = (absender or "").strip().lower()
        if a and "@" in a and not ZAHLDIENSTE.search(a):
            dom = a.rsplit("@", 1)[1]
            for f in aktiv:
                eintraege = [x.strip().lower().lstrip("@") for x in re.split(r"[,;\s]+", f.get("rechnungs_absender") or "") if x.strip()]
                if a in eintraege or any(dom == x or dom.endswith("." + x) for x in eintraege if "@" not in x):
                    return f["nummer"]
        k = _key(name)
        if not k:
            return ""
        gleich = [f["nummer"] for f in aktiv if _key(f["name"]) == k]
        if gleich:
            return gleich[0]
        wort = re.split(r"[\s,.(]+", k)[0]
        if len(wort) >= 4:
            treffer = [f["nummer"] for f in aktiv if re.split(r"[\s,.(]+", _key(f["name"]))[0] == wort]
            if len(treffer) == 1:
                return treffer[0]
        return ""

    def zuordnen(self, name: str, *, art: str = "ausgabe", absender: str = "", von: str = "") -> str:
        """Firma zu einem Beleg finden oder anlegen (Lieferant bei Ausgaben, Partner bei Einnahmen/Gutschriften);
        sorgt fuer die Rollennummer und merkt sich den Rechnungs-Absender. Rueckgabe: fester Schluessel."""
        name = " ".join(str(name or "").split())[:200]
        nr = self.finde(name, absender)
        if not nr:
            if not name:
                raise ValueError("Lieferant/Gegenpartei fehlt -- jeder Beleg braucht eine Stammdaten-Nummer.")
            nr = self.firma_anlegen({"name": name, "typ": "partner" if art == "einnahme" else "lieferant"},
                                    von=von, trotz_dublette=True)["nummer"]
        f = self.firma(nr)
        if f and f.get("typ") == "kunde" and art != "einnahme":
            pass                                              # Kunde, der auch liefert: Rolle bleibt, keine L-Nummer
        elif f:
            self.rollennummer_sichern(nr, von=von)
        self.absender_lernen(nr, absender, von=von)
        return nr

    def absender_lernen(self, nummer: str, absender: str, *, von: str = "") -> None:
        """Rechnungs-Absender einer Beleg-Mail an der Firma merken (fuer die Zuordnung kuenftiger Mails)."""
        a = (absender or "").strip().lower()
        f = self.firma(nummer)
        if f and a and "@" in a and not ZAHLDIENSTE.search(a) and not self.finde("", a):
            alt = (f.get("rechnungs_absender") or "").strip()
            self.firma_aendern(f["nummer"], {"rechnungs_absender": f"{alt}, {a}" if alt else a}, von=von)

    def firma_aendern(self, nummer: str, aenderungen: dict, *, von: str = "") -> dict:
        nummer = self.haupt(self._stand()[0], nummer) or (nummer or "").strip().upper()
        neu = _bereinige(aenderungen, FIRMA_FELDER)
        if "name" in neu and not neu["name"]:
            raise ValueError("Firmenname darf nicht leer sein.")
        diff: dict = {}

        def pruefe(eintraege):
            firmen, _ = self._falte(eintraege)
            if nummer not in firmen:
                raise KeyError(nummer)
            diff.update({k: v for k, v in neu.items() if firmen[nummer].get(k) != v})
            if not diff:
                raise KeineAenderung()

        try:
            self.bh.erfassen_geprueft("firma_geaendert", {"nummer": nummer, "felder": diff}, von=von, pruefe=pruefe)
        except KeineAenderung:
            return {"geaendert": {}}
        return {"geaendert": diff}

    def ansprechpartner_anlegen(self, firma: str, daten: dict, *, von: str = "") -> dict:
        firma = self.haupt(self._stand()[0], firma) or (firma or "").strip().upper()
        d = _bereinige(daten, AP_FELDER)
        if not (d.get("vorname") or d.get("nachname")):
            raise ValueError("Name des Ansprechpartners fehlt.")
        d["aktiv"] = True

        def pruefe(eintraege):
            if firma not in self._falte(eintraege)[0]:
                raise KeyError(firma)

        name = f"{d.get('vorname', '')} {d.get('nachname', '')}".strip()
        ev = self.bh.mit_nummer("AP", "ansprechpartner_angelegt", d | {"firma": firma}, bezug=f"{firma} {name}",
                                von=von, pruefe=pruefe)
        return {"nummer": ev["daten"]["nummer"]}

    def ansprechpartner_aendern(self, nummer: str, aenderungen: dict, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        neu = _bereinige(aenderungen, AP_FELDER)
        diff: dict = {}

        def pruefe(eintraege):
            _, aps = self._falte(eintraege)
            if nummer not in aps:
                raise KeyError(nummer)
            diff.update({k: v for k, v in neu.items() if aps[nummer].get(k) != v})
            if not diff:
                raise KeineAenderung()
            rest = {**aps[nummer], **diff}
            if not (rest.get("vorname") or rest.get("nachname")):
                raise ValueError("Name des Ansprechpartners darf nicht leer sein.")

        try:
            self.bh.erfassen_geprueft("ansprechpartner_geaendert", {"nummer": nummer, "felder": diff}, von=von,
                                      pruefe=pruefe)
        except KeineAenderung:
            return {"geaendert": {}}
        return {"geaendert": diff}

    def collab_zuordnen(self, nummer: str, collab_name: str, *, von: str = "") -> dict:
        nummer, k = (nummer or "").strip().upper(), _crm_key(collab_name)
        if not k:
            raise ValueError("Collab-Firma fehlt.")

        def pruefe(eintraege):
            firmen, _ = self._falte(eintraege)
            if nummer not in firmen:
                raise KeyError(nummer)
            if k in firmen[nummer]["collab"]:
                raise KeineAenderung()

        try:
            self.bh.erfassen_geprueft("collab_zugeordnet", {"nummer": nummer, "collab": k, "name": collab_name.strip()},
                                      von=von, pruefe=pruefe)
        except KeineAenderung:
            pass
        return {"nummer": nummer, "collab": k}

    def collab_loesen(self, nummer: str, collab_name: str, *, von: str = "") -> dict:
        nummer, k = (nummer or "").strip().upper(), _crm_key(collab_name)

        def pruefe(eintraege):
            firmen, _ = self._falte(eintraege)
            if nummer not in firmen:
                raise KeyError(nummer)
            if k not in firmen[nummer]["collab"]:
                raise KeineAenderung()

        try:
            self.bh.erfassen_geprueft("collab_geloest", {"nummer": nummer, "collab": k, "name": collab_name.strip()},
                                      von=von, pruefe=pruefe)
        except KeineAenderung:
            pass
        return {"nummer": nummer, "collab": k}


def anzeige_nummer(f: dict) -> str:
    """Die Nummer, unter der die Firma in ihrer Rolle gefuehrt wird (L- fuer Lieferanten, P- fuer Partner, K- sonst)."""
    kreis = KREIS.get(f.get("typ") or "kunde", "K")
    passend = [n for n in f.get("nummern") or [f["nummer"]] if n.startswith(kreis + "-")]
    return passend[-1] if passend else f["nummer"]


def luecken(f: dict) -> list[str]:
    """Fehlende Stammdaten (werden angezeigt, nicht erfunden)."""
    out = []
    inland = (f.get("land") or "deutschland").strip().lower() in ("deutschland", "de", "germany")
    if not (f.get("strasse") and f.get("ort") and (f.get("plz") or not inland)):   # Ausland: PLZ nicht immer vorhanden
        out.append("Adresse")
    if not f.get("land"):
        out.append("Land")
    if f.get("typ") in ("lieferant", "partner") and not (f.get("ustid") or f.get("steuernummer")):
        out.append("USt-IdNr./Steuernummer")
    return out


class KeineAenderung(Exception):
    """Intern: nichts zu schreiben (kein leerer Eintrag in der Kette)."""


class DubletteFehler(ValueError):
    def __init__(self, text: str, nummern: list[str]):
        super().__init__(text)
        self.nummern = nummern
