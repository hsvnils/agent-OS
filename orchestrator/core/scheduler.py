"""Phase 12 -- Durable Watch-Store + Scheduler (token-frugal, 24/7).

Leitprinzip (CEO): **Hintergrundarbeit verbrennt keine Token.** Der Scheduler macht ausschliesslich
**kostenlose** Datenarbeit -- GitHub-API (Sterne/Wachstum) und Brave-Gratis-Suche je Fachbereich -- und
flaggt Auffaelliges **regelbasiert**. Teure LLM-Synthese (`innovation_scouting`) bleibt auf Anfrage und ist
hier per Default **aus** (`llm_enabled=False`).

Durable: event-sourced JSONL (`watch/log.jsonl`) mit Sterne-Historie (fuer Velocity), Funden (dedupliziert)
und Lauf-Zeitstempeln (fuer Intervall-Faelligkeit + Resume nach Neustart). Leck-geschuetzt.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.github_watch import GitHubWatch, MockGitHubWatch, flag_fast_growers
from ..governance.leak_guard import redact
from .watch_config import FIRMEN_GITHUB_TOPICS, themen_fuer


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class WatchStore:
    """Append-only JSONL: Sterne-Historie, Funde (dedupliziert nach URL), Lauf-Zeitstempel."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def star_history(self) -> dict[str, int]:
        hist: dict[str, int] = {}
        for e in self._events():
            if e.get("typ") == "stars":
                hist[e["repo"]] = e["sterne"]
        return hist

    def persist_stars(self, history: dict[str, int]) -> None:
        for repo, sterne in history.items():
            self._append({"ts": _now(), "typ": "stars", "repo": repo, "sterne": sterne})

    def seen_urls(self) -> set[str]:
        return {e.get("url", "") for e in self._events() if e.get("typ") == "finding"}

    def add_finding(self, kategorie: str, titel: str, url: str, *, detail: str = "",
                    abteilung: str = "") -> bool:
        if url and url in self.seen_urls():
            return False
        self._append({"ts": _now(), "typ": "finding", "kategorie": kategorie, "titel": titel,
                      "url": url, "detail": detail, "abteilung": abteilung})
        return True

    def findings(self, limit: int = 50, kategorie: str | None = None) -> list[dict]:
        items = [e for e in self._events() if e.get("typ") == "finding"
                 and (kategorie is None or e.get("kategorie") == kategorie)]
        return list(reversed(items))[:limit]

    def set_pause(self, an: bool) -> None:
        """Notbremse: haelt alle autonomen Ablaeufe an / gibt sie frei."""
        self._append({"ts": _now(), "typ": "pause", "an": bool(an)})

    def paused(self) -> bool:
        zustand = [e.get("an") for e in self._events() if e.get("typ") == "pause"]
        return bool(zustand[-1]) if zustand else False

    def last_run(self, job: str) -> str | None:
        runs = [e["ts"] for e in self._events() if e.get("typ") == "run" and e.get("job") == job]
        return runs[-1] if runs else None

    def mark_run(self, job: str) -> None:
        self._append({"ts": _now(), "typ": "run", "job": job})


class WatchScheduler:
    """Faehrt freie Watcher (GitHub + Fachbereichs-Suche) und schreibt Funde in den Store."""

    def __init__(self, store: WatchStore, *, github=None, web=None, research=None, notify=None,
                 google=None, secrets: list[str] | None = None, llm_enabled: bool = False):
        self.store = store
        self.github = github if github is not None else GitHubWatch()
        self.web = web
        self.research = research  # ResearchTickets: Fachbereichs-Suchen laufen ueber den Researcher
        self.notify = notify      # callable(text, *, kategorie, quelle) -> proaktiver Push an den CEO
        self.google = google      # GoogleWorkspace (Mail-/Kalender-Watcher) oder None
        self.secrets = secrets or []
        self.llm_enabled = llm_enabled  # Hintergrund-LLM aus (Token sparen); nur explizit aktivierbar

    def _melde(self, text: str, **kw) -> None:
        if self.notify is not None:
            try:
                self.notify(text, **kw)
            except Exception:
                pass

    def github_tick(self, topics: list[str] | None = None, *, min_stars: int = 500) -> list[dict]:
        """Kostenlos: Repos mit vielen Sternen + schnellem Wachstum flaggen + persistieren."""
        topics = topics or FIRMEN_GITHUB_TOPICS
        hist = self.store.star_history()
        neue: list[dict] = []
        for topic in topics:
            repos = self.github.trending(topic, min_stars=min_stars)
            for r in flag_fast_growers(repos, hist):
                wachstum = f"+{r.zuwachs} Sterne" if r.zuwachs else ("NEU" if r.neu else "")
                detail = f"{r.sterne} Sterne ({wachstum}); {r.beschreibung}".strip()
                if self.store.add_finding("github", r.name, r.url, detail=detail):
                    neue.append({"name": r.name, "url": r.url, "sterne": r.sterne,
                                 "zuwachs": r.zuwachs, "neu": r.neu, "topic": topic,
                                 "beschreibung": (r.beschreibung or "").strip()})
        self.store.persist_stars(hist)
        self.store.mark_run("github")
        if neue:  # Auffaelliges: jedes Repo einzeln auffuehren (eine Meldung je Lauf)
            top = max(neue, key=lambda r: (r["zuwachs"], r["sterne"]))
            liste = "\n".join(
                f"{i}. {(r.get('beschreibung') or 'ohne Beschreibung')[:90]} "
                f"({r['sterne']} Sterne, +{r['zuwachs']}) -- {r['url']} -- {r['name']}"
                for i, r in enumerate(neue, 1))
            text = (f"{len(neue)} neue auffällige Repos. Top: {top['name']} "
                    f"({top['sterne']} Sterne, +{top['zuwachs']}).\n\n{liste}")
            self._melde(text, abteilung="IT/Watcher", kategorie="github", quelle="watcher", detail=liste)
        return neue

    def dept_tick(self, abteilung: str, *, max_pro_thema: int = 3) -> list[dict]:
        """Fachbereichs-Wissensstand pflegen (kostenlos, Brave-Gratis) -- ueber den Researcher (Ticket).

        Je Suchthema des Fachbereichs Top-Treffer als Funde ablegen (dedupliziert) und einen
        Research-Ticket-Eintrag erzeugen (Nachverfolgbarkeit: welche Abteilung, was, Quellen).
        """
        themen = themen_fuer(abteilung).get("suche", [])
        neue: list[dict] = []
        quellen: list[str] = []
        if self.web is None:
            return neue
        for thema in themen:
            erg = self.web.recherchiere(thema)  # Brave-first, kostenlos
            if not getattr(erg, "ok", False):
                continue
            for t in erg.treffer[:max_pro_thema]:
                if t.url and self.store.add_finding("fachbereich", t.titel, t.url,
                                                    detail=t.auszug[:160], abteilung=abteilung):
                    neue.append({"titel": t.titel, "url": t.url, "abteilung": abteilung, "thema": thema})
                    quellen.append(t.url)
        # Researcher dokumentiert den Fachbereichs-Lauf als Ticket (nur wenn es Neues gab).
        if self.research is not None and neue:
            tid = self.research.erstellen(
                f"Fachbereichs-Wissensupdate {abteilung}: {len(neue)} neue Funde", abteilung=abteilung)
            self.research.in_arbeit(tid)
            self.research.erledigen(tid, provider="brave",
                                    befund=f"{len(neue)} neue Einträge im Wissensstand {abteilung}.",
                                    quellen=quellen)
        self.store.mark_run(f"dept:{abteilung}")
        if neue:
            detail = "\n".join(f"- {f['titel']}: {f['url']}" for f in neue)
            self._melde(f"{len(neue)} neue relevante Funde für den Bereich im Wissensstand.",
                        abteilung=f"Researcher/{abteilung}", kategorie="fachbereich",
                        quelle=f"researcher:{abteilung}", detail=detail)
        return neue

    def mail_tick(self) -> list[dict]:
        """Proaktiver Mail-Watcher (kostenlos): neue ungelesene Mails melden (dedupliziert)."""
        if self.google is None or not self.google.verfuegbar():
            return []
        r = self.google.neue_mails()
        if not r.get("ok"):
            return []
        neue = []
        for m in r.get("mails", []):
            if self.store.add_finding("mail", m.get("betreff", ""), f"mail:{m['id']}",
                                      detail=m.get("von", ""), abteilung="Postfach"):
                neue.append(m)
        self.store.mark_run("mail")
        if neue:
            detail = "\n".join(f"- {m.get('von', '')}: {m.get('betreff', '')}" for m in neue)
            self._melde(f"{len(neue)} neue ungelesene Mail(s). Neueste: {neue[0].get('betreff', '')[:50]}",
                        abteilung="Postfach", kategorie="mail", quelle="mail-watcher", detail=detail)
        return neue

    def kalender_tick(self) -> list[dict]:
        """Proaktiver Kalender-Watcher (kostenlos): Termin-Kollisionen melden (dedupliziert)."""
        if self.google is None or not self.google.verfuegbar():
            return []
        r = self.google.kalender_kollisionen()
        if not r.get("ok"):
            return []
        neu = []
        for k in r.get("kollisionen", []):
            key = f"koll:{k.get('a')}|{k.get('b')}|{k.get('ab')}"
            if self.store.add_finding("kollision", f"{k.get('a')} <> {k.get('b')}", key, abteilung="Kalender"):
                neu.append(k)
                self._melde(f"Termin-Kollision: '{k.get('a')}' und '{k.get('b')}' überschneiden sich.",
                            abteilung="Kalender", kategorie="kollision", quelle="kalender-watcher",
                            detail=f"Überschneidung ab {k.get('ab')}")
        self.store.mark_run("kalender")
        return neu

    def briefing(self, abteilung: str | None = None, limit: int = 20) -> list[dict]:
        """Reine Anzeige der gesammelten Funde (kein LLM, keine Kosten)."""
        if abteilung:
            return [f for f in self.store.findings(limit * 3)
                    if f.get("abteilung") == abteilung][:limit]
        return self.store.findings(limit)
