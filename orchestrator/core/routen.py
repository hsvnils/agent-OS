"""Fahrstrecken fuer die Kilometer-Erfassung (KUNDEN_FINANZEN Etappe 25, CEO 2026-09-30: „Adresse des Drehs eintragen,
LUNA findet die Kilometer selbst heraus -- Start ist immer der Arthur-Soltau-Weg“).

Kostenlos und ohne Schluessel ueber OpenStreetMap: Adresse -> Koordinaten mit **Nominatim** (Nutzungsregeln: eigener
User-Agent, hoechstens 1 Anfrage/s, Ergebnisse zwischenspeichern), Strecke mit dem oeffentlichen **OSRM**-Router
(Auto, schnellste Route). Gerechnet wird **Hin- und Rueckweg** ab der Firmenadresse, auf volle km aufgerundet. Ohne Netz
oder ohne Treffer: None -> der CEO traegt die km selbst ein. Google Maps waere kostenpflichtig (CEO-Tor) und ist nicht
angebunden.
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

NOMINATIM = "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=de,at,ch,nl,dk&q={q}"
OSRM = "https://router.project-osrm.org/route/v1/driving/{a};{b}?overview=false"
UA = "LUNA-Hanserautisch/1.0 (Fahrtkosten; nils@hanserautisch.de)"
_LETZTE_ANFRAGE = [0.0]


def _json(url: str) -> dict | list:
    if os.environ.get("LUNA_EZB_OFFLINE") or os.environ.get("LUNA_OFFLINE"):     # Tests: nie ins Netz
        raise OSError("Netz abgeschaltet (Tests)")
    warten = 1.1 - (time.time() - _LETZTE_ANFRAGE[0])                           # Nominatim: max. 1 Anfrage/s
    if warten > 0:
        time.sleep(warten)
    _LETZTE_ANFRAGE[0] = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


class Routen:
    def __init__(self, cache: Path | str, *, http=None):
        self.cache = Path(cache)
        self.http = http or _json

    def _laden(self) -> dict:
        try:
            return json.loads(self.cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def koordinaten(self, adresse: str) -> tuple[float, float] | None:
        a = " ".join((adresse or "").split())
        if len(a) < 5:
            return None
        daten = self._laden()
        if a.lower() in daten:
            return tuple(daten[a.lower()]) if daten[a.lower()] else None
        try:
            r = self.http(NOMINATIM.format(q=urllib.parse.quote(a)))
            ko = (float(r[0]["lat"]), float(r[0]["lon"])) if r else None
        except Exception:
            return None                                                        # Netzfehler: nicht zwischenspeichern
        daten[a.lower()] = list(ko) if ko else None
        try:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache.with_suffix(".tmp")
            tmp.write_text(json.dumps(daten, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            tmp.replace(self.cache)
        except OSError:
            pass
        return ko

    def km_hin_zurueck(self, start: str, ziel: str) -> int | None:
        """Strassen-km Hin + Rueck (aufgerundet) oder None."""
        a, b = self.koordinaten(start), self.koordinaten(ziel)
        if not a or not b:
            return None
        try:
            r = self.http(OSRM.format(a=f"{a[1]},{a[0]}", b=f"{b[1]},{b[0]}"))
            meter = float(r["routes"][0]["distance"])
        except Exception:
            return None
        return math.ceil(2 * meter / 1000)
