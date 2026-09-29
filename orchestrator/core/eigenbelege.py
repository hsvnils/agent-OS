"""KUNDEN_FINANZEN Etappe 7: Eigenbelege -- Zahlungen ohne eigene Rechnung/Eingangsrechnung.

Beispiele: Auszahlung einer Plattform (Meta, YouTube), Kontogebuehren, Porto bar. Jede Buchung bekommt eine Nummer
`EB-JJJJ-NNNN` (lueckenlos, atomar) und steht unveraenderlich in der Hash-Kette; Korrektur nur per Storno mit Grund
(GoBD: Korrektur erkennbar). Datum = **Zahlungsdatum** (Zufluss-/Abflussprinzip der EUeR).

Hier liegt auch die **10-Tage-Regel** (§ 11 EStG): regelmaessig wiederkehrende Zahlungen, die kurz vor/nach dem
Jahreswechsel (22.12. bis 10.01.) fliessen, gehoeren in das Jahr, zu dem sie wirtschaftlich gehoeren. Der CEO setzt
dafuer bei der Zahlung ein abweichendes Zuordnungsjahr; LUNA prueft nur, dass es zulaessig ist.
"""
from __future__ import annotations

from datetime import date

from .beleg_pdf import cent
from .buchhaltung import Buchhaltung, jetzt
from .eingangsbelege import EINNAHME_KATEGORIEN, KATEGORIEN, EingangStore

ARTEN = ("einnahme", "ausgabe")


def datum_pruefen(s: str, name: str = "Zahlungsdatum", *, zukunft: bool = False) -> str:
    s = str(s or "").strip()[:10] or jetzt().date().isoformat()
    try:
        tag = date.fromisoformat(s).isoformat()
    except ValueError:
        raise ValueError(f"{name}: ungueltiges Datum.") from None
    if not zukunft and tag > jetzt().date().isoformat():
        raise ValueError(f"{name} liegt in der Zukunft.")
    return tag


def zuordnung_pruefen(tag: str, jahr) -> int | None:
    """10-Tage-Regel: abweichendes Zuordnungsjahr nur fuer Zahlungen vom 22.12. bis 10.01. und nur ins Nachbarjahr.
    Rueckgabe: das abweichende Jahr oder None (= Jahr des Zahlungsdatums)."""
    if jahr in (None, "", 0, "0"):
        return None
    try:
        jahr = int(jahr)
    except (TypeError, ValueError):
        raise ValueError("Zuordnungsjahr ungueltig.") from None
    d = date.fromisoformat(tag)
    if jahr == d.year:
        return None
    im_fenster = (d.month == 12 and d.day >= 22) or (d.month == 1 and d.day <= 10)
    nachbar = d.year + 1 if d.month == 12 else d.year - 1
    if not im_fenster or jahr != nachbar:
        raise ValueError("Abweichendes Zuordnungsjahr nur fuer regelmaessig wiederkehrende Zahlungen vom 22.12. bis 10.01. "
                         f"(10-Tage-Regel) -- hier nur {nachbar} moeglich." if im_fenster else
                         "Abweichendes Zuordnungsjahr nur fuer Zahlungen vom 22.12. bis 10.01. (10-Tage-Regel).")
    return jahr


class EigenbelegStore:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "eigenbeleg_angelegt":
                out[d["nummer"]] = dict(d) | {"status": "gebucht", "angelegt": e["ts"], "von": e.get("von", "")}
            elif t == "eigenbeleg_firma_verknuepft" and d.get("nummer") in out:     # Etappe 14: Altbeleg -> Nummer
                out[d["nummer"]]["firma"] = d["firma"]
            elif t == "eigenbeleg_storniert" and d.get("nummer") in out:
                out[d["nummer"]] |= {"status": "storniert", "storno_grund": d.get("grund", ""), "storniert_am": e["ts"]}
        return out

    def liste(self) -> list[dict]:
        return sorted(self._falte(self.bh.eintraege()).values(), key=lambda x: x["nummer"], reverse=True)

    def get(self, nummer: str) -> dict | None:
        return self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())

    def anlegen(self, daten: dict, *, von: str = "") -> dict:
        d = self.pruefen(daten)
        ev = self.bh.mit_nummer("EB", "eigenbeleg_angelegt", d, jahr=int(d["datum"][:4]), bezug=d["text"][:60], von=von)
        return {"nummer": ev["daten"]["nummer"]}

    @staticmethod
    def pruefen(daten: dict) -> dict:
        """Eingaben pruefen und bereinigen, ohne zu schreiben (ValueError mit Grund)."""
        art = str(daten.get("art") or "").strip()
        if art not in ARTEN:
            raise ValueError("Art muss Einnahme oder Ausgabe sein.")
        tag = datum_pruefen(daten.get("datum"))
        try:
            betrag = cent(daten.get("betrag"))
        except ValueError:
            raise ValueError("Betrag fehlt oder ist ungueltig.") from None
        if betrag <= 0:
            raise ValueError("Betrag muss groesser als 0 sein (Rueckzahlung = Buchung der Gegenart).")
        kat = str(daten.get("kategorie") or ("umsatz" if art == "einnahme" else "")).strip()
        erlaubt = EINNAHME_KATEGORIEN if art == "einnahme" else {k: v for k, v in KATEGORIEN.items() if k != "anlage"}
        if kat not in erlaubt:
            raise ValueError("Anlagegueter bitte als Beleg hochladen (Abschreibung)." if kat == "anlage"
                             else "Bitte eine Kategorie waehlen.")
        text = str(daten.get("text") or "").strip()[:300]
        if len(text) < 3:
            raise ValueError("Bitte beschreiben, wofuer die Zahlung war (Eigenbeleg).")
        d = {"art": art, "datum": tag, "betrag_cent": betrag, "kategorie": kat, "text": text,
             "gegenpartei": str(daten.get("gegenpartei") or "").strip()[:200],
             "referenz": str(daten.get("referenz") or "").strip()[:120]}
        if daten.get("firma"):                               # Etappe 14: Stammdaten-Nummer der Gegenpartei
            d["firma"] = str(daten["firma"]).strip().upper()[:20]
        if (z := zuordnung_pruefen(tag, daten.get("zuordnung_jahr"))):
            d["zuordnung_jahr"] = z
        return d

    def firma_verknuepfen(self, nummer: str, firma: str, *, von: str = "") -> dict:
        nummer, firma = (nummer or "").strip().upper(), (firma or "").strip().upper()

        def pruefe(eintraege):
            x = self._falte(eintraege).get(nummer)
            if not x:
                raise KeyError(nummer)
            if x.get("firma") == firma:
                raise ValueError(f"{nummer} haengt schon an {firma}.")
        self.bh.erfassen_geprueft("eigenbeleg_firma_verknuepft", {"nummer": nummer, "firma": firma}, von=von, pruefe=pruefe)
        return {"nummer": nummer, "firma": firma}

    def stornieren(self, nummer: str, grund: str, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund fuer das Storno angeben.")

        def pruefe(eintraege):
            x = self._falte(eintraege).get(nummer)
            if not x:
                raise KeyError(nummer)
            if x["status"] == "storniert":
                raise ValueError(f"{nummer} ist bereits storniert.")
        self.bh.erfassen_geprueft("eigenbeleg_storniert", {"nummer": nummer, "grund": grund}, von=von, pruefe=pruefe)
        return {"status": "storniert"}


def einnahmen_cent(eintraege: list[dict], jahr: int) -> int:
    """Umsatz ausserhalb eigener Rechnungen (fuer den Kleinunternehmer-Waechter): Eigenbeleg-Einnahmen nach Datum +
    gebuchte Gutschriften (z. B. Facebook-Monetarisierung) nach Gutschriftsdatum."""
    eigen = sum(x["betrag_cent"] for x in EigenbelegStore._falte(eintraege).values()
                if x["art"] == "einnahme" and x["status"] == "gebucht" and x["datum"][:4] == str(jahr)
                and x.get("kategorie") != "anlage_abgang")          # Anlagevermoegen zaehlt nicht (§ 19 Abs. 2 UStG)
    gutschriften = sum(f["betrag_cent"] for f in (x.get("felder") or {} for x in EingangStore._falte(eintraege).values()
                                                   if x["status"] == "gebucht")
                       if f.get("art") == "einnahme" and str(f.get("rechnungsdatum", ""))[:4] == str(jahr)
                       and f.get("kategorie") != "anlage_abgang")
    return eigen + gutschriften
