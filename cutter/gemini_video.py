"""Cutter (Phase 15) -- OPT-IN Gemini-Video-Verstaendnis fuer die Clip-Reihenfolge.

Standardmaessig **AUS**. Nur aktiv, wenn `CUTTER_VIDEO_KI=1` gesetzt ist UND ein `GEMINI_API_KEY` vorliegt.
Anders als der Text-Pfad (`pipeline._gemini_reihenfolge`, nur Transkript) laedt dieser die Clips als **Video**
zu Gemini hoch (Files-API) und laesst das Modell sie **ansehen** -> visuell begruendete Reihenfolge
(Hook/Highlight). Bei JEDEM Fehler -> `None`, damit der Aufrufer auf Text- bzw. Dateiname-Reihenfolge
zurueckfaellt (robust, nie Absturz).

CEO-Tor: sendet Rohclips an Google -- nur auf **Paid-Tier** datenschutz-vertretbar (Free-Tier trainiert mit).
Kosten ~<1-3 Cent/Lauf (Video = 258 Token/s). Guenstigstes video-faehiges Modell: `gemini-2.5-flash-lite`.
Doku/Preise: siehe `docs/entscheidungs-register.md` (Eintrag 2026-07-03).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

_HOST = "https://generativelanguage.googleapis.com"


class GeminiVideoClient:
    """Duenner REST-Client fuer die Gemini Files-API + generateContent (nur urllib, kein SDK)."""

    def __init__(self, key: str, model: str = "gemini-2.5-flash-lite", *, timeout: int = 180):
        self.key = key
        self.model = model
        self.timeout = timeout

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"x-goog-api-key": self.key}
        if extra:
            h.update(extra)
        return h

    def upload(self, pfad: str, mime: str = "video/mp4") -> dict | None:
        """Resumable-Upload einer Datei -> {uri, name, mime} oder None."""
        daten = Path(pfad).read_bytes()
        start = urllib.request.Request(
            f"{_HOST}/upload/v1beta/files", method="POST",
            data=json.dumps({"file": {"display_name": Path(pfad).name}}).encode("utf-8"),
            headers=self._headers({"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                   "X-Goog-Upload-Header-Content-Length": str(len(daten)),
                                   "X-Goog-Upload-Header-Content-Type": mime,
                                   "Content-Type": "application/json"}))
        with urllib.request.urlopen(start, timeout=self.timeout) as r:
            upload_url = r.headers.get("X-Goog-Upload-URL") or r.headers.get("x-goog-upload-url")
        if not upload_url:
            return None
        fin = urllib.request.Request(
            upload_url, method="POST", data=daten,
            headers={"Content-Length": str(len(daten)), "X-Goog-Upload-Offset": "0",
                     "X-Goog-Upload-Command": "upload, finalize"})
        with urllib.request.urlopen(fin, timeout=self.timeout) as r:
            info = json.loads(r.read().decode("utf-8"))
        f = info.get("file", {})
        if not f.get("uri"):
            return None
        return {"uri": f.get("uri"), "name": f.get("name"), "mime": mime}

    def warte_aktiv(self, name: str, *, intervall: float = 2.0, max_versuche: int = 60) -> bool:
        """Pollt den Datei-Status bis ACTIVE (True) bzw. FAILED/Timeout (False)."""
        for _ in range(max_versuche):
            req = urllib.request.Request(f"{_HOST}/v1beta/{name}", headers=self._headers())
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                state = json.loads(r.read().decode("utf-8")).get("state")
            if state == "ACTIVE":
                return True
            if state == "FAILED":
                return False
            time.sleep(intervall)
        return False

    def generate(self, parts: list) -> str:
        """generateContent mit den gegebenen Parts -> Antworttext."""
        body = {"contents": [{"parts": parts}]}
        req = urllib.request.Request(
            f"{_HOST}/v1beta/models/{self.model}:generateContent", method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers=self._headers({"Content-Type": "application/json"}))
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            daten = json.loads(r.read().decode("utf-8"))
        cands = daten.get("candidates") or []
        if not cands:
            return ""
        teile = cands[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in teile)


def _downsample(pfad: str) -> Path | None:
    """Erzeugt einen kleinen 360p-Proxy (schneller/guenstiger Upload). None -> Original nutzen."""
    try:
        ziel = Path(tempfile.mkdtemp(prefix="cutproxy_")) / "proxy.mp4"
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(pfad), "-vf", "scale=-2:360", "-c:v", "libx264",
             "-crf", "32", "-preset", "veryfast", "-c:a", "aac", "-b:a", "64k", str(ziel)],
            capture_output=True, timeout=120)
        if r.returncode == 0 and ziel.exists() and ziel.stat().st_size > 0:
            return ziel
    except Exception:
        pass
    return None


def _parse_order(txt: str, n: int) -> list | None:
    """Extrahiert eine JSON-Index-Liste; nur gueltige, eindeutige Indizes 0..n-1. None wenn unbrauchbar."""
    i, j = (txt or "").find("["), (txt or "").rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        roh = json.loads(txt[i:j + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(roh, list):
        return None
    sauber: list[int] = []
    for x in roh:
        if isinstance(x, int) and 0 <= x < n and x not in sauber:
            sauber.append(x)
    return sauber or None


def reihenfolge_via_video(auswahlen: list, client, *, downsample: bool = True) -> list | None:
    """Laedt die Clips hoch, laesst Gemini sie ansehen -> Index-Reihenfolge (list[int]) oder None."""
    try:
        n = len(auswahlen)
        parts: list = []
        for i, a in enumerate(auswahlen):
            quelle = a.clip.pfad
            proxy = _downsample(str(quelle)) if downsample else None
            up = client.upload(str(proxy or quelle))
            if not up or not up.get("uri"):
                return None
            if up.get("name") and not client.warte_aktiv(up["name"]):
                return None
            parts.append({"text": f"Clip {i} [{getattr(a, 'typ', '')}]:"})
            parts.append({"file_data": {"mime_type": up.get("mime", "video/mp4"), "file_uri": up["uri"]}})
        parts.append({"text": (
            "Du bist Profi-Video-Cutter fuer Instagram-Reels. Ordne die oben gezeigten "
            f"{n} Clips (Index 0..{n - 1}) zu einer spannenden Reihenfolge -- staerkster visueller Hook "
            "zuerst, dann Aufbau. Antworte NUR mit einer JSON-Liste von Indizes, z. B. [2,0,1].")})
        return _parse_order(client.generate(parts) or "", n)
    except Exception:
        return None
