"""Social-Media-Analyzer (CBO/CCO) -- Insights -> Kennzahlen + Monats-Historie + Media-Kit-Entwurf.

Zieht die Insights des EIGENEN Instagram-Business-/Creator-Kontos ueber die Meta Graph API (v22, 2026),
verdichtet sie zu Kennzahlen, fuehrt eine Monats-Historie (wie die CFO-Kostenstatistik) und erzeugt einen
**Media-Kit-Entwurf** (formatierte Zahlen + Monatstrend). Der Canva-Autofill ist ein spaeterer Aufsatz.

Governance: Der Abruf des EIGENEN Kontos braucht NUR ein vom App-Admin erzeugtes Access-Token mit Insights-
Scope -- NICHT die (zurueckgestellte) Advanced-Access-Review fuer fremde DMs (GATE B). Veroeffentlichen/Posten
bleibt CEO-Tor; dieses Modul liefert nur den Entwurf. Metriken sind konfigurierbar (Meta deprecatet oefter);
HTTP ist injizierbar -> vollstaendig offline testbar.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

_BASE = "https://graph.facebook.com/v22.0"
# Konto-Insights-Metriken (period=days_28). Konfigurierbar, da Meta oefter deprecatet.
_KONTO_METRIKEN = ("reach", "profile_views")


@dataclass
class Snapshot:
    monat: str                       # 'YYYY-MM'
    username: str = ""
    followers: int = 0
    media_count: int = 0
    reach: int = 0
    profile_views: int = 0
    engagement_rate: float = 0.0     # Prozent: Durchschnitt (Likes+Kommentare)/Post / Followers
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    top_posts: list = field(default_factory=list)     # [{likes, comments, ts}]
    erfasst_am: str = ""

    def as_dict(self) -> dict:
        return {"typ": "snapshot", **self.__dict__}


def _num(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


class MetaInsights:
    """Ruft die Insights des eigenen IG-Kontos ab. `http(url, params)->dict` ist injizierbar (Tests/Offline)."""

    def __init__(self, token: str, ig_user_id: str, *, http=None, base: str = _BASE,
                 metriken: tuple = _KONTO_METRIKEN):
        self.token = token
        self.ig_user_id = ig_user_id
        self.http = http or self._urllib_get
        self.base = base
        self.metriken = metriken

    @property
    def verfuegbar(self) -> bool:
        return bool(self.token and self.ig_user_id)

    def _urllib_get(self, url: str, params: dict) -> dict:
        p = dict(params or {}); p["access_token"] = self.token
        voll = f"{url}?{urllib.parse.urlencode(p)}"
        with urllib.request.urlopen(voll, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))

    def hole(self, monat: str | None = None) -> Snapshot | None:
        """Baut einen Monats-Snapshot. None, wenn kein Token/ID oder der Profil-Abruf fehlschlaegt."""
        if not self.verfuegbar:
            return None
        monat = monat or datetime.now().strftime("%Y-%m")
        try:
            prof = self.http(f"{self.base}/{self.ig_user_id}",
                             {"fields": "username,followers_count,media_count"})
        except Exception:
            return None
        if not isinstance(prof, dict) or prof.get("error"):
            return None
        snap = Snapshot(monat=monat, username=str(prof.get("username", "")),
                        followers=_num(prof.get("followers_count")),
                        media_count=_num(prof.get("media_count")),
                        erfasst_am=datetime.now().isoformat(timespec="seconds"))
        # Konto-Insights (best-effort, einzelne Metrik-Fehler ignorieren).
        try:
            ins = self.http(f"{self.base}/{self.ig_user_id}/insights",
                            {"metric": ",".join(self.metriken), "period": "days_28"})
            for eintrag in (ins or {}).get("data", []):
                name = eintrag.get("name")
                werte = eintrag.get("values") or [{}]
                wert = _num(werte[-1].get("value")) if werte else 0
                if name == "reach":
                    snap.reach = wert
                elif name == "profile_views":
                    snap.profile_views = wert
        except Exception:
            pass
        # Engagement aus den letzten Posts.
        try:
            med = self.http(f"{self.base}/{self.ig_user_id}/media",
                            {"fields": "like_count,comments_count,timestamp", "limit": "25"})
            posts = [{"likes": _num(p.get("like_count")), "comments": _num(p.get("comments_count")),
                      "ts": p.get("timestamp", "")} for p in (med or {}).get("data", [])]
            if posts:
                snap.avg_likes = round(sum(p["likes"] for p in posts) / len(posts), 1)
                snap.avg_comments = round(sum(p["comments"] for p in posts) / len(posts), 1)
                if snap.followers > 0:
                    schnitt = sum(p["likes"] + p["comments"] for p in posts) / len(posts)
                    snap.engagement_rate = round(schnitt / snap.followers * 100, 2)
                snap.top_posts = sorted(posts, key=lambda p: p["likes"] + p["comments"], reverse=True)[:3]
        except Exception:
            pass
        return snap


class SocialStore:
    """Monats-Snapshots als event-sourced JSONL (juengster je Monat gewinnt). Leck-geschuetzt."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def speichere(self, snap: Snapshot) -> dict:
        ev = {"ts": datetime.now().isoformat(timespec="seconds"), **snap.as_dict()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(ev, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return ev

    def _snapshots(self) -> dict[str, dict]:
        """Juengster Snapshot je Monat (spaeterer Eintrag ueberschreibt)."""
        je_monat: dict[str, dict] = {}
        if not self.path.exists():
            return je_monat
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("typ") == "snapshot" and e.get("monat"):
                je_monat[e["monat"]] = e
        return je_monat

    def monat(self, ym: str | None = None) -> dict | None:
        je_monat = self._snapshots()
        if not je_monat:
            return None
        ym = ym or max(je_monat)
        return je_monat.get(ym)

    def verlauf(self) -> list[dict]:
        return [je[m] for je in [self._snapshots()] for m in sorted(je)]


def _delta(jetzt: int | float, vor: int | float) -> str:
    if not vor:
        return ""
    diff = jetzt - vor
    proz = round(diff / vor * 100, 1)
    vz = "+" if diff >= 0 else ""
    return f" ({vz}{diff}; {vz}{proz}% ggue. Vormonat)"


def media_kit(snap: dict, vormonat: dict | None = None) -> dict:
    """Erzeugt den Media-Kit-Entwurf (Zahlen + Monatstrend). `snap`/`vormonat` sind Store-Dicts."""
    v = vormonat or {}
    zeilen = [
        f"Media-Kit @{snap.get('username', '?')} -- {snap.get('monat', '?')}",
        f"Follower: {snap.get('followers', 0)}" + _delta(snap.get('followers', 0), v.get('followers', 0)),
        f"Reichweite (28 T.): {snap.get('reach', 0)}" + _delta(snap.get('reach', 0), v.get('reach', 0)),
        f"Profilaufrufe: {snap.get('profile_views', 0)}"
        + _delta(snap.get('profile_views', 0), v.get('profile_views', 0)),
        f"Engagement-Rate: {snap.get('engagement_rate', 0.0)}%"
        + _delta(snap.get('engagement_rate', 0.0), v.get('engagement_rate', 0.0)),
        f"Beitraege gesamt: {snap.get('media_count', 0)}",
        f"Durchschnitt je Post: {snap.get('avg_likes', 0.0)} Likes / {snap.get('avg_comments', 0.0)} Kommentare",
    ]
    return {"monat": snap.get("monat"), "username": snap.get("username"),
            "kennzahlen": {k: snap.get(k) for k in
                           ("followers", "reach", "profile_views", "engagement_rate", "media_count",
                            "avg_likes", "avg_comments")},
            "top_posts": snap.get("top_posts", []),
            "media_kit_text": "\n".join(zeilen),
            "hinweis": "Entwurf -- Canva-Autofill/Posten bleibt CEO-Tor."}
