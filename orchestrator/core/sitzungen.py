"""Login-Sitzungen fuer LUNA-OS (LUNA_OS_UI_ROADMAP Etappe 2, CEO 2026-09-30: „auf iPhone/iPad als WebApp muss ich mich
immer neu einloggen, der Schluesselbund schlaegt nichts vor“).

Menschen melden sich ueber ein echtes Login-Formular an (der Schluesselbund fuellt es per Face ID aus) und bekommen ein
Sitzungs-Cookie mit 30 Tagen Laufzeit, die sich bei Nutzung verlaengert. Gespeichert wird nur der **SHA-256 des
Tokens** (Datei auf der NAS unter `orchestrator/state/`, nicht im Git, nicht gesynct) -- wer die Datei liest, kann
sich damit nicht anmelden. Jede Sitzung ist einzeln oder gesammelt widerrufbar („Alle Geraete abmelden“).
Maschinen-Zugaenge (Waechter, Cutter-Bruecke) nutzen weiter HTTP-Basic und sind hiervon nicht betroffen.

Fehlversuch-Bremse: 5 Fehlversuche je Nutzername und Adresse in 15 Minuten -> 10 Minuten gesperrt (im Speicher, ein
Neustart setzt sie zurueck).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def _jetzt() -> datetime:
    """Deutsche Zeit ohne Zonenangabe (der Container laeuft in UTC; vgl. BF-32/BF-48)."""
    return datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)

LAUFZEIT_TAGE = 30
COOKIE = "luna_sitzung"
FEHLVERSUCHE_MAX = 5
FEHLVERSUCHE_FENSTER_S = 15 * 60
SPERRE_S = 10 * 60
_VERLAENGERN_AB_S = 6 * 3600          # "zuletzt" hoechstens alle 6 h schreiben (weniger Schreibzugriffe)


def _hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def geraet_aus(user_agent: str) -> str:
    """Grobe, lesbare Geraete-Bezeichnung fuer die Liste in den Einstellungen."""
    ua = user_agent or ""
    if "iPad" in ua:
        g = "iPad"
    elif "iPhone" in ua:
        g = "iPhone"
    elif "Android" in ua:
        g = "Android"
    elif "Macintosh" in ua:
        g = "Mac"
    elif "Windows" in ua:
        g = "Windows"
    else:
        g = "Geraet"
    b = "Safari" if "Safari" in ua and "Chrome" not in ua and "CriOS" not in ua else \
        "Chrome" if "Chrome" in ua or "CriOS" in ua else "Firefox" if "Firefox" in ua else ""
    return f"{g} · {b}" if b else g


class Sitzungen:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()
        self._fehl: dict[str, list[float]] = {}
        self._gesperrt: dict[str, float] = {}

    # -- Speicher ------------------------------------------------------------
    def _laden(self) -> dict:
        try:
            return json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _speichern(self, daten: dict) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
        tmp.replace(self.pfad)

    @staticmethod
    def _abgelaufen(s: dict, jetzt: datetime) -> bool:
        try:
            return datetime.fromisoformat(s["ablauf"]) <= jetzt
        except (KeyError, ValueError):
            return True

    # -- Sitzungen -----------------------------------------------------------
    def anlegen(self, username: str, *, art: str, geraet: str = "") -> str:
        """Neue Sitzung -> Klartext-Token (nur fuers Cookie; gespeichert wird der Hash)."""
        token = secrets.token_urlsafe(32)
        jetzt = _jetzt()
        with self._lock:
            d = {h: s for h, s in self._laden().items() if not self._abgelaufen(s, jetzt)}
            d[_hash(token)] = {"id": secrets.token_hex(6), "username": username, "art": art, "geraet": geraet[:60],
                               "erstellt": jetzt.isoformat(timespec="seconds"),
                               "zuletzt": jetzt.isoformat(timespec="seconds"),
                               "ablauf": (jetzt + timedelta(days=LAUFZEIT_TAGE)).isoformat(timespec="seconds")}
            self._speichern(d)
        return token

    def pruefen(self, token: str) -> dict | None:
        """Gueltige Sitzung -> {username, art, id}; verlaengert die Laufzeit gleitend."""
        if not token:
            return None
        h = _hash(token)
        jetzt = _jetzt()
        with self._lock:
            d = self._laden()
            s = d.get(h)
            if not s or self._abgelaufen(s, jetzt):
                return None
            try:
                alt = (jetzt - datetime.fromisoformat(s["zuletzt"])).total_seconds()
            except (KeyError, ValueError):
                alt = _VERLAENGERN_AB_S
            if alt >= _VERLAENGERN_AB_S:
                s["zuletzt"] = jetzt.isoformat(timespec="seconds")
                s["ablauf"] = (jetzt + timedelta(days=LAUFZEIT_TAGE)).isoformat(timespec="seconds")
                self._speichern(d)
        return {"username": s["username"], "art": s.get("art", ""), "id": s["id"]}

    def beenden(self, token: str) -> None:
        with self._lock:
            d = self._laden()
            if d.pop(_hash(token), None) is not None:
                self._speichern(d)

    def liste(self, username: str) -> list[dict]:
        jetzt = _jetzt()
        return sorted(({k: s.get(k) for k in ("id", "geraet", "erstellt", "zuletzt", "ablauf")}
                       for s in self._laden().values()
                       if s.get("username") == username and not self._abgelaufen(s, jetzt)),
                      key=lambda s: s["zuletzt"] or "", reverse=True)

    def widerrufen(self, username: str, sitzung_id: str | None = None, *, ausser_id: str | None = None) -> int:
        """Eine Sitzung (id) oder alle des Nutzers widerrufen (optional ausser der aktuellen). -> Anzahl."""
        with self._lock:
            d = self._laden()
            weg = [h for h, s in d.items() if s.get("username") == username
                   and (sitzung_id is None or s.get("id") == sitzung_id)
                   and (ausser_id is None or s.get("id") != ausser_id)]
            for h in weg:
                del d[h]
            if weg:
                self._speichern(d)
        return len(weg)

    # -- Fehlversuch-Bremse --------------------------------------------------
    def gesperrt_s(self, schluessel: str) -> int:
        """Restsekunden der Sperre (0 = frei)."""
        bis = self._gesperrt.get(schluessel, 0)
        rest = int(bis - time.time())
        return rest if rest > 0 else 0

    def fehlversuch(self, schluessel: str) -> None:
        jetzt = time.time()
        liste = [t for t in self._fehl.get(schluessel, []) if jetzt - t < FEHLVERSUCHE_FENSTER_S] + [jetzt]
        self._fehl[schluessel] = liste
        if len(liste) >= FEHLVERSUCHE_MAX:
            self._gesperrt[schluessel] = jetzt + SPERRE_S
            self._fehl[schluessel] = []

    def erfolg(self, schluessel: str) -> None:
        self._fehl.pop(schluessel, None)
        self._gesperrt.pop(schluessel, None)
