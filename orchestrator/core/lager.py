"""Lagerbestand fuer physische Ware (KUNDEN_FINANZEN Etappe 21, CEO 2026-09-30: „fuer physische Ware schon mal einen
moeglichen Lagerbestand als Funktion -- haben wir aktuell noch nicht, aber dann ist es fuer die Zukunft drin“).

Ein Katalog-Artikel mit `physisch: true` fuehrt einen Bestand ab seinem `lager_start`:
- **Zugaenge/Korrekturen** erfasst der CEO als Ereignis `lager_bewegung` (Menge +/-, Grund, Datum, optional Beleg `ER-`),
- **Verkaeufe** ergeben sich aus festgeschriebenen Rechnungen mit dieser Katalog-Position (Rechnungsdatum ab Lager-Start);
  eine Stornorechnung bucht die Menge zurueck -- nichts wird doppelt gespeichert, der Bestand folgt immer den Belegen.
Faellt der Bestand unter den Mindestbestand, erscheint ein To-do.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from .buchhaltung import Buchhaltung, jetzt
from .rechnungen import RechnungStore


def _artikel(katalog: dict) -> dict[str, dict]:
    return {it["id"]: it | {"gruppe": g["name"]} for g in katalog["gruppen"] for it in g["items"] if it.get("physisch")}


def bestaende(eintraege: list[dict], katalog: dict) -> dict[str, dict]:
    """-> {artikel_id: {name, bestand, mindestbestand, niedrig, zugang, verkauft, bewegungen: [...]}} (nur physische)."""
    artikel = _artikel(katalog)
    out = {i: {"id": i, "name": a["name"], "gruppe": a["gruppe"], "mindestbestand": a.get("mindestbestand", 0),
               "lager_start": a["lager_start"], "zugang": 0, "verkauft": 0, "bewegungen": []} for i, a in artikel.items()}
    for e in eintraege:
        d = e["daten"]
        if e["typ"] == "lager_bewegung" and d.get("artikel") in out:
            x = out[d["artikel"]]
            x["zugang"] += int(d["menge"])
            x["bewegungen"].append({k: d.get(k) for k in ("datum", "menge", "grund", "beleg")} | {"ts": e["ts"], "art": "manuell"})
    for r in RechnungStore._falte(eintraege)[1].values():
        for p in r.get("positionen") or []:
            x = out.get(p.get("katalog_id") or "")
            if not x or str(r.get("rechnungsdatum", "")) < x["lager_start"]:
                continue
            try:
                m = int(Decimal(str(p.get("menge") or 0)))
            except (InvalidOperation, ValueError):
                continue
            m = m if r.get("art") != "storno" else -m                        # Storno bucht zurueck
            x["verkauft"] += m
            x["bewegungen"].append({"datum": r["rechnungsdatum"], "menge": -m, "grund": f"Rechnung {r['nummer']}",
                                    "beleg": r["nummer"], "art": "rechnung"})
    for x in out.values():
        x["bestand"] = x["zugang"] - x["verkauft"]
        x["niedrig"] = x["bestand"] < x["mindestbestand"] or x["bestand"] < 0
        x["bewegungen"].sort(key=lambda b: (b.get("datum") or "", b.get("ts") or ""))
    return out


class Lager:
    def __init__(self, bh: Buchhaltung, katalog):
        self.bh, self.katalog = bh, katalog

    def uebersicht(self) -> list[dict]:
        return sorted(bestaende(self.bh.eintraege(), self.katalog.laden()).values(), key=lambda x: (x["gruppe"], x["name"]))

    def bewegung(self, artikel: str, menge, *, grund: str, datum: str = "", beleg: str = "", von: str = "") -> dict:
        """Zugang (+) oder Korrektur/Abgang ohne Rechnung (-), z. B. Wareneingang, Inventur, Bruch, Eigenverbrauch."""
        artikel = (artikel or "").strip().lower()
        if artikel not in _artikel(self.katalog.laden()):
            raise ValueError("Diesen Artikel gibt es nicht als physische Ware im Katalog.")
        try:
            m = int(str(menge).strip())
        except (TypeError, ValueError):
            raise ValueError("Menge als ganze Zahl (Zugang positiv, Abgang negativ).") from None
        if not m or abs(m) > 1_000_000:
            raise ValueError("Menge darf nicht 0 sein.")
        grund = str(grund or "").strip()[:200]
        if not grund:
            raise ValueError("Bitte einen Grund angeben (z. B. Wareneingang, Inventur, Bruch).")
        tag = str(datum or "")[:10] or jetzt().date().isoformat()
        try:
            tag = date.fromisoformat(tag).isoformat()
        except ValueError:
            raise ValueError("Datum ungueltig.") from None
        if tag > jetzt().date().isoformat():
            raise ValueError("Datum liegt in der Zukunft.")
        beleg = str(beleg or "").strip().upper()[:20]
        self.bh.erfassen("lager_bewegung", {"artikel": artikel, "menge": m, "grund": grund, "datum": tag, "beleg": beleg},
                         von=von)
        return {"artikel": artikel, "menge": m}
