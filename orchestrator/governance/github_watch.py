"""Phase 12 -- GitHub-Watcher: Repos mit vielen Sternen, die schnell wachsen.

Beobachtet themenrelevante GitHub-Repos ueber die **kostenlose** GitHub-Search-API (kein Token noetig;
`GITHUB_TOKEN` aus .env hebt nur das Rate-Limit von 60 auf 5000/h). **Keine LLM-Aufrufe** -- reine
Datenarbeit. „Schnelles Wachstum" wird regelbasiert erkannt:

- **Sterne-Delta** seit dem letzten Lauf (Velocity) -- braucht Historie (wird vom Aufrufer mitgegeben),
- **Neu + viele Sterne** als Proxy fuer Neueinsteiger (created in den letzten N Tagen).

Lazy/stdlib (urllib) -- keine neue Dependency. Mock fuer Offline-Self-Checks.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_API = "https://api.github.com/search/repositories"


@dataclass
class Repo:
    name: str            # owner/repo
    url: str
    sterne: int
    beschreibung: str = ""
    erstellt: str = ""
    topics: list[str] = field(default_factory=list)
    # gefuellt durch flag_fast_growers:
    zuwachs: int = 0     # Sterne-Delta seit letztem Lauf
    neu: bool = False    # juenger als schwelle


class GitHubWatch:
    def __init__(self, env: dict[str, str] | None = None):
        import os
        self._token = (env or os.environ).get("GITHUB_TOKEN", "").strip()

    def trending(self, topic: str, *, min_stars: int = 500, aktiv_seit_tage: int = 30,
                 max_results: int = 15) -> list[Repo]:
        """Repos zu einem Topic mit >= min_stars, in den letzten Tagen aktiv, nach Sternen sortiert."""
        seit = (datetime.now(timezone.utc) - timedelta(days=aktiv_seit_tage)).strftime("%Y-%m-%d")
        q = f"topic:{topic} stars:>={min_stars} pushed:>={seit}"
        params = urllib.parse.urlencode({"q": q, "sort": "stars", "order": "desc",
                                         "per_page": max(1, min(max_results, 50))})
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "luna-github-watch"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(f"{_API}?{params}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            return []
        out = []
        for it in (data or {}).get("items", []):
            out.append(Repo(name=it.get("full_name", ""), url=it.get("html_url", ""),
                            sterne=int(it.get("stargazers_count", 0)),
                            beschreibung=(it.get("description") or "")[:200],
                            erstellt=it.get("created_at", ""), topics=it.get("topics", []) or []))
        return out


def flag_fast_growers(repos: list[Repo], historie: dict[str, int], *, min_zuwachs: int = 50,
                      neu_tage: int = 60) -> list[Repo]:
    """Markiert schnelle Wachser anhand Sterne-Delta (vs. Historie) und Neuheit. Aktualisiert `historie`.

    Rueckgabe: nur die als auffaellig markierten Repos (zuwachs >= min_zuwachs ODER neu mit vielen Sternen).
    """
    schwelle_neu = (datetime.now(timezone.utc) - timedelta(days=neu_tage))
    flagged: list[Repo] = []
    for r in repos:
        vorher = historie.get(r.name)
        r.zuwachs = (r.sterne - vorher) if vorher is not None else 0
        try:
            r.neu = datetime.fromisoformat(r.erstellt.replace("Z", "+00:00")) >= schwelle_neu
        except (ValueError, AttributeError):
            r.neu = False
        historie[r.name] = r.sterne  # Historie fortschreiben
        if r.zuwachs >= min_zuwachs or (r.neu and r.sterne >= min_zuwachs):
            flagged.append(r)
    flagged.sort(key=lambda x: (x.zuwachs, x.sterne), reverse=True)
    return flagged


class MockGitHubWatch:
    """Deterministischer Stub ohne Netz -- fuer Offline-Self-Checks."""

    def __init__(self, repos: dict[str, list[Repo]] | None = None):
        self._repos = repos or {}

    def trending(self, topic, *, min_stars=500, aktiv_seit_tage=30, max_results=15):
        return self._repos.get(topic, [
            Repo(name=f"acme/{topic}-agent", url=f"https://github.com/acme/{topic}-agent",
                 sterne=1200, beschreibung=f"Demo zu {topic}", erstellt="2026-06-01T00:00:00Z",
                 topics=[topic]),
        ])[:max_results]
