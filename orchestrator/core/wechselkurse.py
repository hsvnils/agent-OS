"""EZB-Referenzkurse fuer Fremdwaehrungs-Belege (KUNDEN_FINANZEN Etappe 20, CEO 2026-09-30: „EZB-Kurs bei Dollar nehmen“).

Belege in Fremdwaehrung (USD usw.) bekommen den Euro-Betrag zum EZB-Referenzkurs des Rechnungstags vorgeschlagen;
an Wochenenden/Feiertagen gilt der letzte veroeffentlichte Kurs davor. Quelle: EZB Data Portal (Serie EXR, taeglich,
`D.<WAEHRUNG>.EUR.SP00.A` = Einheiten Fremdwaehrung je 1 EUR). Kurse werden in `buchhaltung/wechselkurse.json`
zwischengespeichert (veroeffentlichte Kurse aendern sich nicht). Ohne Netz bleibt alles wie vorher -- der CEO traegt den
Euro-Betrag dann selbst ein (Kalender-Erinnerung). Gebucht wird nie automatisch, nur vorgeschlagen.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .beleg_pdf import cent, eur

EZB_URL = ("https://data-api.ecb.europa.eu/service/data/EXR/D.{w}.EUR.SP00.A"
           "?startPeriod={von}&endPeriod={bis}&format=csvdata")
RUECKBLICK_TAGE = 10                      # laengste Luecke ohne Kurs (Ostern/Weihnachten) sicher abdecken


def _http_csv(url: str) -> str:
    if os.environ.get("LUNA_EZB_OFFLINE"):                 # Tests: nie ins Netz (orchestrator/tests/conftest.py)
        raise OSError("EZB-Abruf abgeschaltet (LUNA_EZB_OFFLINE)")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "text/csv"}), timeout=8) as r:
        return r.read().decode("utf-8", "replace")


def _csv_kurse(csv: str) -> dict[str, float]:
    zeilen = [z.split(",") for z in csv.strip().splitlines()]
    if not zeilen:
        return {}
    kopf = zeilen[0]
    try:
        i_t, i_w = kopf.index("TIME_PERIOD"), kopf.index("OBS_VALUE")
    except ValueError:
        return {}
    out = {}
    for z in zeilen[1:]:
        try:
            out[z[i_t]] = float(z[i_w])
        except (IndexError, ValueError):
            continue
    return out


class EzbKurse:
    def __init__(self, cache: Path | str, *, http=None):
        self.cache = Path(cache)
        self.http = http or _http_csv

    def _laden(self) -> dict:
        try:
            return json.loads(self.cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def kurs(self, waehrung: str, tag: str) -> tuple[str, float] | None:
        """-> (Kurstag, Einheiten Fremdwaehrung je 1 EUR) fuer den Tag oder den letzten Kurstag davor; None ohne Kurs."""
        w = (waehrung or "").upper()
        if not re.fullmatch(r"[A-Z]{3}", w) or w == "EUR":
            return None
        d = date.fromisoformat(tag[:10])
        daten = self._laden()
        bekannt = daten.get(w, {})
        treffer = sorted(t for t in bekannt if t <= d.isoformat() and t >= (d - timedelta(days=RUECKBLICK_TAGE)).isoformat())
        gesichert = any(t > d.isoformat() for t in bekannt)       # spaeterer Kurs bekannt -> Luecke ist echt (Wochenende)
        if not treffer or (treffer[-1] != d.isoformat() and not gesichert):
            try:
                neu = _csv_kurse(self.http(EZB_URL.format(w=w, von=(d - timedelta(days=RUECKBLICK_TAGE)).isoformat(),
                                                          bis=d.isoformat())))
            except Exception:
                neu = {}
            if neu:
                bekannt = bekannt | neu
                daten[w] = bekannt
                try:
                    self.cache.parent.mkdir(parents=True, exist_ok=True)
                    tmp = self.cache.with_suffix(".tmp")
                    tmp.write_text(json.dumps(daten, sort_keys=True), encoding="utf-8")
                    tmp.replace(self.cache)
                except OSError:
                    pass
                treffer = sorted(t for t in bekannt
                                 if (d - timedelta(days=RUECKBLICK_TAGE)).isoformat() <= t <= d.isoformat())
        return (treffer[-1], bekannt[treffer[-1]]) if treffer else None


def euro_vorschlag(v: dict, kurse: EzbKurse) -> dict:
    """Vorschlag in Fremdwaehrung -> Ergaenzung {betrag, kurs, kurs_notiz} oder {} (kein Kurs/kein Fremdbetrag)."""
    w, fremd, tag = (v.get("waehrung") or "").upper(), v.get("betrag_fremd"), v.get("rechnungsdatum")
    if not w or w == "EUR" or not fremd or not tag or v.get("betrag"):
        return {}
    try:
        k = kurse.kurs(w, tag)
        betrag_fremd = cent(fremd)
    except ValueError:
        return {}
    if not k:
        return {}
    kurstag, satz = k
    euro = int((Decimal(betrag_fremd) / Decimal(str(satz))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    betrag = eur(euro).replace(" €", "")
    return {"betrag": betrag, "kurs": {"waehrung": w, "tag": kurstag, "kurs": satz, "quelle": "EZB"},
            "kurs_notiz": f"{fremd} {w} umgerechnet mit EZB-Referenzkurs vom {kurstag} (1 EUR = {satz} {w}) = {betrag} EUR"}


def kurse_ergaenzen(st, kurse: EzbKurse) -> list[str]:
    """Offene Belege in Fremdwaehrung ohne Euro-Betrag: EZB-Vorschlag ergaenzen. Rueckgabe: Belegnummern."""
    neu = []
    for x in st._falte(st.bh.eintraege()).values():
        v = x.get("vorschlag") or {}
        if x["status"] != "zu_pruefen":
            continue
        if (erg := euro_vorschlag(v, kurse)):
            st.vorschlag_ergaenzen(x["nummer"], erg)
            neu.append(x["nummer"])
    return neu
