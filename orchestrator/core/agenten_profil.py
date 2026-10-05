"""Agenten-Transparenz (AGENTEN_AUSBAU A1, CEO 2026-10-05).

- **Nutzung messen:** jede Fachagenten-Anfrage von LUNA („delegate“, quelle `delegate`) und jede Antwort ueber ein
  Werkzeug des Bereichs (quelle `werkzeug`, FACHAGENTEN_ROUTING R3) wird ohne Inhalte protokolliert -- Agent, Zeit,
  Dauer, Erfolg, Zahl der geladenen Skills (`agenten_nutzung/log.jsonl`, NAS).
- **Profil je Agent:** Charta (Titel, Status, Modell-Richtwert, Rolle), Skills (skill-card + Gate-Verdikt), Quellen mit
  Stand/Pruefdatum, Watcher-Themen und letzte Funde, Nutzung 30/90 Tage -- fuer die Agenten-Seite in LUNA-OS und den
  Wochenbericht des Leistungs-Agenten.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .subagents import ALL_AGENT_CHARTERS

CHARTEN = {"hoa": "agents/00_head-of-agents.md", **ALL_AGENT_CHARTERS}
ALIAS = {"researcher": "res"}                                     # Organigramm-Schluessel -> Charta-Schluessel


def _zeit(v) -> datetime:
    """Protokoll-Zeitstempel mit Zeitzone. Naive Alt-Eintraege stammen aus dem Container (UTC, BF-32) -- als UTC lesen."""
    d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _grenze(d: datetime) -> datetime:
    """Fenstergrenze: naive Werte kommen von `datetime.now()` des laufenden Rechners -> dessen Ortszeit."""
    return d if d.tzinfo else d.astimezone()


class AgentenNutzung:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def erfassen(self, agent: str, *, ok: bool, dauer_ms: int, skills: int = 0, quelle: str = "delegate") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from .buchhaltung import jetzt                      # deutsche Zeit mit Zeitzone (BF-32/BF-57)
        e = {"ts": jetzt().isoformat(timespec="seconds"), "agent": agent, "ok": bool(ok), "dauer_ms": int(dauer_ms),
             "skills": int(skills), "quelle": quelle}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for z in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(z))
            except ValueError:
                continue
        return out

    def zaehlen(self, seit: datetime, bis: datetime | None = None) -> dict[str, dict]:
        from .buchhaltung import TZ
        s, b = _grenze(seit), _grenze(bis or datetime.now(timezone.utc))
        out: dict[str, dict] = {}
        for e in self._events():
            try:
                t = _zeit(e.get("ts", ""))
            except ValueError:
                continue
            if not (s <= t <= b):
                continue
            x = out.setdefault(e.get("agent", "?"), {"anzahl": 0, "direkt": 0, "werkzeug": 0, "fehler": 0, "zuletzt": "",
                                                     "dauer_ms": []})
            x["anzahl"] += 1
            x["werkzeug" if e.get("quelle") == "werkzeug" else "direkt"] += 1
            x["fehler"] += 0 if e.get("ok") else 1
            x["zuletzt"] = max(x["zuletzt"], t.astimezone(TZ).isoformat(timespec="seconds"))
            x["dauer_ms"].append(int(e.get("dauer_ms") or 0))
        for x in out.values():
            d = sorted(x.pop("dauer_ms"))
            x["median_s"] = round(d[len(d) // 2] / 1000, 1) if d else None
        return out


def _charta(repo: Path, key: str) -> dict:
    t = (repo / CHARTEN[key]).read_text(encoding="utf-8")
    feld = lambda n: (re.search(rf"^{n}:\s*(.+)$", t, re.M) or [None, ""])[1].strip()
    rolle = re.search(r"## Rolle\s*\n(.+?)(?:\n\n|\n## )", t, re.S)
    return {"titel": re.sub(r"^# Agent:\s*", "", t.splitlines()[0]).strip(), "status": feld("Status") or "?",
            "modell": feld("Modell"), "rolle": re.sub(r"\s+", " ", rolle.group(1)).strip() if rolle else "",
            "datei": CHARTEN[key]}


def _skills(repo: Path, key: str) -> list[dict]:
    from . import skill_format
    from .dept_skills import lade_dept_skills
    _, meta = lade_dept_skills(key, repo)
    verdikt = {m["skill"]: m for m in meta}
    out = []
    for d in sorted(p for p in (repo / "skills" / key).iterdir() if p.is_dir()) if (repo / "skills" / key).is_dir() else []:
        md = d / "SKILL.md"
        card = skill_format.parse_skill_card(md.read_text(encoding="utf-8")) if md.exists() else {}
        name = card.get("name") or d.name
        m = verdikt.get(name) or verdikt.get(d.name) or {}
        out.append({"name": name, "beschreibung": card.get("beschreibung", ""), "version": card.get("version", ""),
                    "verdikt": m.get("verdikt", "?"), "geladen": bool(m.get("geladen")), "quellen": (d / "quellen.md").exists()})
    return out


def _funde_alle(watch_log: Path) -> dict[str, list[dict]]:
    """Watcher-Funde je Abteilung (neueste zuerst) -- das Log wird nur einmal gelesen."""
    out: dict[str, list[dict]] = {}
    if not watch_log.exists():
        return out
    for z in watch_log.read_text(encoding="utf-8").splitlines():
        if '"finding"' not in z:
            continue
        try:
            e = json.loads(z)
        except ValueError:
            continue
        if e.get("typ") == "finding" and e.get("abteilung"):
            out.setdefault(e["abteilung"], []).append({k: e.get(k) for k in ("titel", "url", "ts")})
    for v in out.values():
        v.reverse()
    return out


def profil(repo: Path | str, key: str, *, watch_log: Path | str, nutzung: AgentenNutzung, jetzt: datetime | None = None,
           _funde: dict | None = None) -> dict:
    from .rechtsquellen import quellen
    from .watch_config import themen_fuer
    repo, jetzt = Path(repo), jetzt or datetime.now(timezone.utc)
    key = ALIAS.get(key, key)
    if key not in CHARTEN:
        raise KeyError(key)
    funde = (_funde if _funde is not None else _funde_alle(Path(watch_log))).get(key, [])
    n30, n90 = nutzung.zaehlen(jetzt - timedelta(days=30), jetzt).get(key), nutzung.zaehlen(jetzt - timedelta(days=90), jetzt).get(key)
    qs = quellen(repo / "skills" / key) if (repo / "skills" / key).is_dir() else []
    return {"key": key, "charta": _charta(repo, key), "skills": _skills(repo, key),
            "quellen": [{k: q[k] for k in ("skill", "norm", "url", "stand", "pruefen_bis")} for q in qs],
            "watcher": themen_fuer(key).get("suche", []), "funde": funde[:5], "funde_gesamt": len(funde),
            "nutzung": {"tage30": n30 or {"anzahl": 0, "direkt": 0, "werkzeug": 0, "fehler": 0, "zuletzt": "", "median_s": None},
                        "tage90": n90 or {"anzahl": 0, "direkt": 0, "werkzeug": 0, "fehler": 0, "zuletzt": "", "median_s": None}}}


def uebersicht(repo: Path | str, *, watch_log: Path | str, nutzung: AgentenNutzung) -> list[dict]:
    out, funde = [], _funde_alle(Path(watch_log))
    for key in CHARTEN:
        p = profil(repo, key, watch_log=watch_log, nutzung=nutzung, _funde=funde)
        out.append({"key": key, "titel": p["charta"]["titel"], "status": p["charta"]["status"],
                    "skills": len(p["skills"]), "quellen": len(p["quellen"]), "watcher": len(p["watcher"]),
                    "funde": p["funde_gesamt"], "letzter_fund": (p["funde"][0]["ts"] if p["funde"] else ""),
                    "nutzung30": p["nutzung"]["tage30"]["anzahl"]})
    return out
