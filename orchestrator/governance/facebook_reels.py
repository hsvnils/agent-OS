"""Facebook-Reels-Upload (Reel-Pipeline Stufe D) -- ein Seiten-Video als Reel veroeffentlichen.

3-Phasen-Upload der Graph Reels-API (`POST /{page_id}/video_reels`): start -> Binaer-Upload -> finish
(`video_state=PUBLISHED`). Nur urllib, keine Dependency. Braucht einen **Seiten-Token mit
`pages_manage_posts`** (+ `pages_read_engagement`). Veroeffentlichung = Oeffentlichkeit = CEO-Tor ->
wird ausschliesslich fuer bereits **freigegebene** Reels aufgerufen. Robust: jeder Fehler -> {ok:false}.

Doku: developers.facebook.com/docs/video-api/guides/reels-publishing
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.facebook.com/v25.0"


def _post(url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, method="POST", data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode("utf-8")
        return json.loads(txt) if txt.strip() else {}


def _form(felder: dict) -> bytes:
    return urllib.parse.urlencode(felder).encode()


def poste_reel(page_id: str, page_token: str, video_pfad: str, beschreibung: str = "") -> dict:
    """Laedt `video_pfad` als Facebook-Reel der Seite hoch und veroeffentlicht es.
    Gibt {ok, video_id} oder {ok:false, fehler}."""
    if not page_id or not page_token:
        return {"ok": False, "fehler": "page_id/Seiten-Token fehlt (Token-Scope pages_manage_posts noetig)."}
    p = Path(video_pfad)
    if not p.exists():
        return {"ok": False, "fehler": f"Video nicht gefunden: {video_pfad}"}
    try:
        daten = p.read_bytes()
        # Phase 1: start -> video_id + upload_url
        start = _post(f"{GRAPH}/{page_id}/video_reels",
                      data=_form({"upload_phase": "start", "access_token": page_token}),
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
        video_id, upload_url = start.get("video_id"), start.get("upload_url")
        if not video_id or not upload_url:
            return {"ok": False, "fehler": f"start fehlgeschlagen: {str(start)[:200]}"}
        # Phase 2: Binaerdaten hochladen (rupload-Host)
        _post(upload_url, data=daten,
              headers={"Authorization": f"OAuth {page_token}", "offset": "0", "file_size": str(len(daten))})
        # Phase 3: finish + veroeffentlichen
        finish = _post(f"{GRAPH}/{page_id}/video_reels",
                       data=_form({"upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
                                   "description": beschreibung or "", "access_token": page_token}),
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
        if finish.get("success") is False:
            return {"ok": False, "fehler": f"finish abgelehnt: {str(finish)[:200]}", "video_id": video_id}
        return {"ok": True, "video_id": video_id}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")[:300]
        except Exception:
            body = ""
        return {"ok": False, "fehler": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "fehler": str(e)[:200]}
