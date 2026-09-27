"""Kunden-Stammdaten (KUNDEN_FINANZEN_ROADMAP.md, Etappe 2): Firmen mit Firmenkundennummer `K-00001`, Ansprechpartner
mit eigener Nummer `AP-00001`, Zuordnung bestehender Collab-CRM-Firmen.

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
FIRMA_FELDER = ("name", "typ", "strasse", "plz", "ort", "land", "ustid", "steuernummer", "rechnungsmail", "telefon",
                "website", "zahlungsziel_tage", "notiz", "aktiv")
AP_FELDER = ("vorname", "nachname", "rolle", "mail", "telefon", "notiz", "aktiv")
_MAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
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
                                                            "collab": [], "verlauf": []}
                f["aktiv"] = d.get("aktiv", True) is not False
                f["verlauf"].append(spur | {"felder": {k: v for k, v in d.items() if k != "nummer"}})
                firmen[d["nummer"]] = f
            elif t == "firma_geaendert" and d.get("nummer") in firmen:
                f = firmen[d["nummer"]]
                f.update(d.get("felder", {}))
                f["verlauf"].append(spur | {"felder": d.get("felder", {})})
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
        return firmen, aps

    def _stand(self) -> tuple[dict, dict]:
        return self._falte(self.bh.eintraege())

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
                heu = " ".join(str(x or "") for x in (f["nummer"], f["name"], f["ort"], f["rechnungsmail"],
                                                        " ".join(f["collab"])))
                heu += " " + " ".join(f"{a['nummer']} {a['vorname']} {a['nachname']} {a['mail']}" for a in eigene)
                if q not in _key(heu):
                    continue
            out.append({k: v for k, v in f.items() if k != "verlauf"}
                       | {"ansprechpartner": len([a for a in eigene if a["aktiv"]])})
        return sorted(out, key=lambda f: f["nummer"])

    def firma(self, nummer: str) -> dict | None:
        firmen, aps = self._stand()
        f = firmen.get((nummer or "").strip().upper())
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

        ev = self.bh.mit_nummer("K", "firma_angelegt", d, bezug=d["name"], von=von, pruefe=pruefe)
        return {"nummer": ev["daten"]["nummer"]}

    def firma_aendern(self, nummer: str, aenderungen: dict, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
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
        firma = (firma or "").strip().upper()
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


class KeineAenderung(Exception):
    """Intern: nichts zu schreiben (kein leerer Eintrag in der Kette)."""


class DubletteFehler(ValueError):
    def __init__(self, text: str, nummern: list[str]):
        super().__init__(text)
        self.nummern = nummern
