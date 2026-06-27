"""LUNA-OS -- Web-Arbeitsoberflaeche (Phase 16) als Desktop-aehnliches Browser-OS.

FastAPI-Backend ueber den bestehenden Stores. Aktionen laufen ueber dieselben Store-Methoden wie
LUNA selbst (freigeben/ablehnen/...), also mit Changelog + CEO-Tor -- die UI ist nur der bequeme Weg.
Live-Updates per Server-Sent-Events (Datei-mtime-Erkennung). Keine Veroeffentlichung/kein Auto-Merge.

Start lokal:  python -m orchestrator.channels.web   (-> http://127.0.0.1:8765)
"""
import asyncio
import json
import os
import secrets
import time
from functools import partial
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from ...core.antraege import Antraege
from ...core.briefing import Agenda
from ...core.notifications import Notifications
from ...core.research_tickets import ResearchTickets
from ...governance.changelog_tool import append_changelog

ROOT = Path(__file__).resolve().parents[3]
STATIC = Path(__file__).resolve().parent / "static"

_changelog = partial(append_changelog, ROOT / "projekt_changelog.md")
antraege = Antraege(ROOT / "antraege" / "log.jsonl", changelog=_changelog)
notifications = Notifications(ROOT / "notifications" / "log.jsonl")
research = ResearchTickets(ROOT / "research" / "log.jsonl", changelog=_changelog)
agenda = Agenda(ROOT / "agenda" / "log.jsonl")

OFFEN = ("eingereicht", "freigegeben", "in_umsetzung")
_RANG = {"eingereicht": 0, "freigegeben": 1, "in_umsetzung": 2}

# Login-Schutz: nur aktiv, wenn LUNA_OS_PASSWORD gesetzt ist (auf dem NAS via .env). Lokal ohne Passwort offen.
_USER = os.environ.get("LUNA_OS_USER", "ceo")
_PW = os.environ.get("LUNA_OS_PASSWORD", "")
_security = HTTPBasic(auto_error=False)


def auth(cred: HTTPBasicCredentials = Depends(_security)):
    if not _PW:
        return
    ok = cred and secrets.compare_digest(cred.username, _USER) and secrets.compare_digest(cred.password, _PW)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login noetig",
                            headers={"WWW-Authenticate": "Basic"})


app = FastAPI(title="LUNA-OS", dependencies=[Depends(auth)])


def _antrag_dto(a):
    return {
        "id": a.get("antrag_id"),
        "titel": (a.get("titel") or "(ohne Titel)").lstrip("*").strip()[:120],
        "beschreibung": (a.get("beschreibung") or "").strip(),
        "von": a.get("von", ""),
        "kategorie": a.get("kategorie", ""),
        "status": a.get("status", ""),
        "schritte": len(a.get("verlauf", [])),
    }


def _offene_antraege():
    offen = [a for a in antraege.list() if a.get("status") in OFFEN]
    offen.sort(key=lambda a: (_RANG.get(a.get("status"), 9), -len(a.get("verlauf", []))))
    return [_antrag_dto(a) for a in offen]


def _budget():
    p = ROOT / "finance" / "budget.md"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "Monatsbudget" in line and ":" in line:
                return line.split(":", 1)[1].strip().strip("*").strip("`").strip()
    return "unbekannt"


def _state():
    return {
        "antraege": _offene_antraege(),
        "meldungen": [{"id": n["id"], "abteilung": n.get("abteilung", ""),
                       "text": n.get("text", ""), "ts": n.get("ts", "")}
                      for n in list(reversed(notifications.pending()))[:25]],
        "aktivitaet": [{"akteur": e.get("akteur", ""), "aktion": e.get("aktion", ""),
                        "ts": e.get("ts", "")} for e in _aktivitaet_letzte(25)],
        "research": [{"id": t.get("ticket_id"), "frage": (t.get("frage") or "")[:80],
                      "status": t.get("status"), "abteilung": t.get("abteilung", "")}
                     for t in research.list() if t.get("status") in ("offen", "in_arbeit")][:25],
        "finance": {"monatsbudget": _budget()},
        "ts": time.time(),
    }


def _aktivitaet_letzte(n):
    p = ROOT / "aktivitaet" / "log.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(out))[:n]


def _mtimes():
    s = 0.0
    for sub in ("antraege", "notifications", "aktivitaet", "research", "agenda"):
        f = ROOT / sub / "log.jsonl"
        if f.exists():
            s += f.stat().st_mtime
    return s


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def state():
    return _state()


@app.post("/api/antraege/{antrag_id}/freigeben")
async def freigeben(antrag_id: str):
    ok = antraege.freigeben(antrag_id)
    return JSONResponse({"ok": ok, "state": _state()})


@app.post("/api/antraege/{antrag_id}/ablehnen")
async def ablehnen(antrag_id: str, request: Request):
    body = await _json(request)
    ok = antraege.ablehnen(antrag_id, grund=body.get("grund", "Per Oberflaeche abgelehnt"))
    return JSONResponse({"ok": ok, "state": _state()})


@app.post("/api/antraege/{antrag_id}/loeschen")
async def loeschen(antrag_id: str):
    ok = antraege.status_setzen(antrag_id, "geloescht", akteur="CEO", grund="Per Oberflaeche geloescht")
    return JSONResponse({"ok": ok, "state": _state()})


@app.post("/api/antraege/{antrag_id}/mehr-info")
async def mehr_info(antrag_id: str):
    a = antraege.get(antrag_id) or {}
    frage = f"Mehr Infos/Bewertung zum Antrag: {(a.get('titel') or antrag_id)[:80]}"
    tid = research.erstellen(frage, abteilung="Head of Agents")
    notifications.enqueue(f"Recherche zum Antrag beauftragt (Ticket {tid}).",
                          abteilung="LUNA-OS", kategorie="research")
    return JSONResponse({"ok": True, "ticket": tid, "state": _state()})


@app.get("/api/events")
async def events(request: Request):
    async def gen():
        letzte = None
        while True:
            if await request.is_disconnected():
                break
            jetzt = _mtimes()
            if jetzt != letzte:
                letzte = jetzt
                yield "event: update\ndata: {}\n\n"
            else:
                yield ": ping\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(gen(), media_type="text/event-stream")


async def _json(request: Request):
    try:
        return await request.json()
    except Exception:
        return {}


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
