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
import uuid
from datetime import datetime
from functools import partial
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from ...core.antraege import Antraege
from ...core.auftraege import ARTEN as AUFTRAG_ARTEN, AuftragStore, kurz_id
from ...core.entwicklungs_roadmap import EntwicklungsRoadmap
from ...core.brain import Brain
from ...core.crm import CrmStore
from ...core.buchhaltung import Buchhaltung
from ...core.kunden import DubletteFehler, KundenStore
from ...core.angebote import AngebotStore, mail_lesen, mail_text as angebot_mail_text, preisliste_pdf
from ...core.katalog import Katalog
from ...core.beauftragung import AuftragBuch, auftrag_mail_text
from ...core.rechnungen import RechnungStore, rechnung_mail_text
from ...core import eingangsbelege as _eb
from ...core.eigenbelege import EigenbelegStore
from ...core.finanzen import KATEGORIE_NAMEN, Finanzen, journal_csv
from ...core.ig_inbox import IgInboxStore
from ...core.content_store import (AIINTEL_FELDER, AIINTEL_RECS, ContentStore, CUTTER_FELDER, CUTTER_STATUSES,
                                   DRAFT_FELDER, DRAFT_STATUSES, IDEA_FELDER, IDEA_STATUSES, SOURCE_FELDER,
                                   TREND_FELDER, TREND_STATUSES)
from ...core.briefing import Agenda
from ...core.insights import Insights
from ...core.notifications import Notifications
from ...core.reel_store import ReelStore
from ...core.research_tickets import ResearchTickets
from ...core.team_auth import MODULE, MODUL_LABELS, TeamAuth, erlaubte_apps, hat_modul, modul_fuer_pfad
from ...governance.changelog_tool import append_changelog

ROOT = Path(__file__).resolve().parents[3]
STATIC = Path(__file__).resolve().parent / "static"

_changelog = partial(append_changelog, ROOT / "projekt_changelog.md")
entwicklungs_roadmap = EntwicklungsRoadmap(ROOT / "entwicklung" / "roadmap.jsonl", changelog=_changelog)
antraege = Antraege(ROOT / "antraege" / "log.jsonl", changelog=_changelog,
                    on_freigabe=entwicklungs_roadmap.aufnehmen)
notifications = Notifications(ROOT / "notifications" / "log.jsonl")
research = ResearchTickets(ROOT / "research" / "log.jsonl", changelog=_changelog)
agenda = Agenda(ROOT / "agenda" / "log.jsonl")
backoffice = AuftragStore(ROOT / "backoffice" / "log.jsonl")   # FRONTDESK_BACKOFFICE_ROADMAP.md
brain = Brain(ROOT / "brain" / "log.jsonl")


def _crm_projektor():
    """Write-Through-Projektor nach Supabase, sobald SUPABASE_URL + SERVICE_ROLE_KEY da sind (sonst None ->
    rein lokal). Liest die Keys aus orchestrator/.env (bzw. os.environ als Fallback)."""
    try:
        from ...core.crm_projection import SupabaseCrmProjection
        from ...governance.supabase import SupabaseAuth, SupabaseClient
        try:
            from ..telegram.bot import _load_secrets
            sec = _load_secrets()
        except Exception:
            sec = dict(os.environ)
        auth = SupabaseAuth.from_env(sec)
        return SupabaseCrmProjection(SupabaseClient(auth)) if auth.verfuegbar() else None
    except Exception:
        return None


crm_store = CrmStore(ROOT / "crm" / "log.jsonl", changelog=_changelog, projektor=_crm_projektor(),
                     notify=notifications.enqueue)   # Phase 23<->21: Injection im DM-Webhook meldet an CISO
buchhaltung = Buchhaltung((ROOT / "buchhaltung" / "log.jsonl").parent)   # Hash-Kette (KUNDEN_FINANZEN Etappe 1)
kunden_store = KundenStore(buchhaltung)                                     # Firmen K-/Ansprechpartner AP- (Etappe 2)
_GOOGLE = None


def _google_secrets() -> dict:
    try:
        from ..telegram.bot import _load_secrets
        return _load_secrets()
    except Exception:
        return dict(os.environ)


def _google():
    """Google Workspace fuer Angebote (Gmail-Entwurf mit Anhang, Kalender-Erinnerung) -- lazy, wie im Bot."""
    global _GOOGLE
    if _GOOGLE is None:
        from ...governance.google_workspace import GoogleAuth, GoogleWorkspace
        try:
            from ..telegram.bot import _load_secrets
            sec = _load_secrets()
        except Exception:
            sec = dict(os.environ)
        _GOOGLE = GoogleWorkspace(GoogleAuth.from_env(env=sec),
                                  standard_einladung=sec.get("GOOGLE_CALENDAR_DEFAULT_ATTENDEE", ""),
                                  zeitzone=sec.get("GOOGLE_CALENDAR_TIMEZONE", "Europe/Berlin"),
                                  kalender_id=sec.get("GOOGLE_CALENDAR_ID", ""),
                                  lese_kalender=sec.get("GOOGLE_CALENDAR_LESEN", ""))
        _GOOGLE.konto_adresse = sec.get("GOOGLE_ACCOUNT_EMAIL", "")
    return _GOOGLE


def _firmendaten() -> dict:
    """Eigene Firma (Briefkopf, Bank) -- liegt nur auf der NAS in buchhaltung/firmendaten.json (nie im Git)."""
    try:
        return json.loads((kunden_store.bh.dir / "firmendaten.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
ig_inbox_store = IgInboxStore(ROOT / "ig_inbox" / "log.jsonl")   # Collab-Radar: Voll-Postfach-Archiv + KI-Analyse
REEL_DIR = ROOT / "reel_freigabe"                                # Stufe C: eingereichte Reels (Video + Log)
reel_store = ReelStore(REEL_DIR / "log.jsonl")


def _supabase_client():
    """SupabaseClient aus der .env (service_role). None nur bei Import-Fehler; ohne Keys -> Fall-B im Client."""
    try:
        from ...governance.supabase import SupabaseAuth, SupabaseClient
        try:
            from ..telegram.bot import _load_secrets
            sec = _load_secrets()
        except Exception:
            sec = dict(os.environ)
        return SupabaseClient(SupabaseAuth.from_env(sec))
    except Exception:
        return None


# content_ops (K1/K2): Supabase = DB, lokaler Cache-Fallback. Ein ContentStore je Tabelle.
_sb = _supabase_client()
trends_store = ContentStore(_sb, "trend_signals", TREND_FELDER, ROOT / "content_ops" / "trends_cache.jsonl",
                            statuses=TREND_STATUSES)
ideas_store = ContentStore(_sb, "ideas", IDEA_FELDER, ROOT / "content_ops" / "ideas_cache.jsonl",
                           statuses=IDEA_STATUSES)
drafts_store = ContentStore(_sb, "content_drafts", DRAFT_FELDER, ROOT / "content_ops" / "drafts_cache.jsonl",
                            statuses=DRAFT_STATUSES)
sources_store = ContentStore(_sb, "sources", SOURCE_FELDER, ROOT / "content_ops" / "sources_cache.jsonl")
aiinbox_store = ContentStore(_sb, "ai_intel_items", AIINTEL_FELDER, ROOT / "content_ops" / "aiinbox_cache.jsonl",
                             statuses=AIINTEL_RECS, status_feld="recommendation")
# K5: Cutter-Jobs (geteilt Mac<->LUNA-OS). Generischer ContentStore reicht (list/add/patch).
# Eigene Tabelle `luna_cutter_jobs` -- NICHT das alte HCC `cutter_jobs` (anderes Schema, wird in K6 gedroppt).
cutter_store = ContentStore(_sb, "luna_cutter_jobs", CUTTER_FELDER, ROOT / "cutter_ops" / "jobs_cache.jsonl",
                            statuses=CUTTER_STATUSES)
# Internes Lagebild (ohne Google); fuer das volle Lagebild (Termine/Mails) nutzt der Endpunkt die LUNA-ctx.
insights_intern = Insights(antraege=antraege, research=research, agenda=agenda)
# Investment (Phase 2, advisory): Engine + Store. MarketData wird lazy aus den .env-Keys gebaut.
from ...investment.store import InvestmentStore
inv_store = InvestmentStore(ROOT / "investment" / "log.jsonl")
# Walk-Forward-Lern-Loop: read-only auf dieselbe Datei, die der Bot schreibt (geteiltes Volume).
from ...investment.loop_store import LoopStore
loop_store = LoopStore(ROOT / "investment" / "features.jsonl")

OFFEN = ("eingereicht", "freigegeben", "in_umsetzung")
_RANG = {"eingereicht": 0, "freigegeben": 1, "in_umsetzung": 2}

# K4 -- Team-Auth + Rollen: CEO ist Superuser via env (LUNA_OS_USER/PASSWORD, auf dem NAS in .env), zusaetzlich
# Team-Nutzer aus der Supabase-Tabelle luna_os_users (Rollen + allowed_modules). Ohne Passwort UND ohne
# Nutzer-Tabelle bleibt LUNA-OS lokal offen (Dev). Sensible Module/Aktionen werden pro Pfad gated.
_USER = os.environ.get("LUNA_OS_USER", "ceo")
_PW = os.environ.get("LUNA_OS_PASSWORD", "")
_security = HTTPBasic(auto_error=False)
_team_auth = TeamAuth(_sb, changelog=_changelog)


def _ceo_user() -> dict:
    """Der env-CEO = Superuser (Rolle owner -> alle Module)."""
    return {"username": _USER, "display_name": "CEO", "role": "owner",
            "allowed_modules": list(MODULE), "is_active": True}


def _login_erforderlich() -> bool:
    return bool(_PW) or _team_auth.verfuegbar()


def _resolve_user(cred: HTTPBasicCredentials | None) -> dict | None:
    if cred and _PW and secrets.compare_digest(cred.username, _USER) \
            and secrets.compare_digest(cred.password, _PW):
        return _ceo_user()
    if cred and _team_auth.verfuegbar():
        u = _team_auth.verify(cred.username, cred.password)
        if u:
            return u
    return None


def auth(request: Request, cred: HTTPBasicCredentials = Depends(_security)):
    # Webhook-Endpunkte (Instagram/Meta) sind von der Basic-Auth ausgenommen: Meta kann sich nicht per Login
    # authentifizieren. Sie sichern sich selbst -- GET ueber den Verify-Token, POST ueber die HMAC-Signatur.
    if request.url.path.startswith("/api/webhook/"):
        return
    user = _resolve_user(cred)
    if user is None:
        if not _login_erforderlich():
            request.state.user = _ceo_user()   # lokaler Dev ohne Passwort/Tabelle: offener Owner
            return
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login nötig",
                            headers={"WWW-Authenticate": "Basic"})
    request.state.user = user
    # Modul-Gating: sensible App-Endpunkte/Aktionen brauchen das passende Modul (Owner sieht alles).
    modul = modul_fuer_pfad(request.method, request.url.path)
    if modul and not hat_modul(user, modul):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"Kein Zugriff auf Modul '{modul}'")


app = FastAPI(title="LUNA-OS", dependencies=[Depends(auth)])


def _md_strip(s: str) -> str:
    """Entfernt Markdown-Schmuck (**, *, #, __) und wandelt Tabellen in lesbaren Text -- fuer LUNA-OS."""
    import re as _re
    out = []
    for line in (s or "").splitlines():
        if _re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line) and "-" in line:  # Tabellen-Trennzeile
            continue
        line = _re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = _re.sub(r"__(.+?)__", r"\1", line)
        line = _re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", line)
        line = _re.sub(r"^\s{0,3}#{1,6}\s*", "", line).replace("**", "").replace("__", "")
        if line.strip().startswith("|") or " | " in line:               # Tabellen-Zeile -> 'a · b · c'
            line = _re.sub(r"\s*\|\s*", " · ", line.strip().strip("|")).strip(" ·")
        out.append(line)
    return "\n".join(out).strip()


def _antrag_dto(a):
    return {
        "id": a.get("antrag_id"),
        "titel": (_md_strip(a.get("titel") or "") or "(ohne Titel)")[:120],
        "beschreibung": _md_strip(a.get("beschreibung") or ""),
        "von": a.get("von", ""),
        "kategorie": a.get("kategorie", ""),
        "status": a.get("status", ""),
        "schritte": len(a.get("verlauf", [])),
    }


def _antrag_detail_dto(a):
    """Vollansicht eines Antrags inkl. Verlauf (Evidenz fuer eine schnelle Entscheidung)."""
    d = _antrag_dto(a)
    d["betroffen"] = (a.get("betroffen") or "").strip()
    d["verlauf"] = [{"ts": s.get("ts", ""), "event": s.get("event", ""),
                     "akteur": s.get("akteur", ""), "grund": s.get("grund", "")}
                    for s in a.get("verlauf", [])]
    return d


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
def index(request: Request):
    """LUNA-OS (V2 ist seit 2026-09-29 das einzige Design; alte `?ui=v1`-Lesezeichen landen ebenfalls hier)."""
    return FileResponse(STATIC / "index-v2.html")


@app.get("/api/state")
def state():
    return _state()


@app.get("/api/me")
def me(request: Request):
    """K4: der eingeloggte Nutzer + seine sichtbaren Apps (SSOT fuers Frontend-Gating)."""
    u = getattr(request.state, "user", None) or _ceo_user()
    # Feature-Flag fuer das 3D-Hologramm (Umschalter Orb<->Hologramm). Default an; per env LUNA_AVATAR=0 global aus.
    avatar_enabled = os.environ.get("LUNA_AVATAR", "1").strip().lower() not in ("0", "false", "no", "off")
    return {"username": u.get("username"), "display_name": u.get("display_name"),
            "role": u.get("role"), "allowed_modules": u.get("allowed_modules") or [],
            "apps": erlaubte_apps(u), "avatar_enabled": avatar_enabled}


# -- K4: Team-Verwaltung (nur Modul 'administration' -> owner/admin; Gating in auth) ------------------

@app.get("/api/team")
def team_liste():
    return {"verfuegbar": _team_auth.verfuegbar(), "users": _team_auth.liste(),
            "module": [{"id": m, "label": MODUL_LABELS.get(m, m)} for m in MODULE],
            "rollen": ["owner", "admin", "team", "content", "viewer"]}


@app.post("/api/team")
async def team_anlegen(request: Request):
    d = await request.json()
    r = _team_auth.anlegen((d.get("username") or "").strip(), d.get("passwort") or "",
                           role=(d.get("role") or "content"),
                           allowed_modules=d.get("allowed_modules"),
                           display_name=(d.get("display_name") or "").strip())
    return JSONResponse({**r, "users": _team_auth.liste()})


@app.post("/api/team/{username}/aktiv")
async def team_aktiv(username: str, request: Request):
    d = await request.json()
    r = _team_auth.setzen_aktiv(username, bool(d.get("aktiv", True)))
    return JSONResponse({**r, "users": _team_auth.liste()})


# -- K5: Cutter-Jobs (Modul content_ops). Mac-Cutter meldet ueber /report, holt offene Jobs ueber /queue. ----

_CUTTER_REPORT_FELDER = ("status", "clips_verwendet", "dauer_sek", "untertitel", "reel_datei",
                         "groesse_mb", "fehler")


@app.get("/api/cutter")
def cutter_liste():
    return {"verfuegbar": _sb is not None and _sb.verfuegbar(),
            "jobs": cutter_store.list(limit=100), "statuses": list(CUTTER_STATUSES)}


@app.post("/api/cutter/job")
async def cutter_job(request: Request):
    """Aus LUNA-OS einen Reel-Job anstossen -> Status `queued`; der Mac-Watcher holt ihn per /queue ab."""
    d = await request.json()
    projekt = (d.get("projekt") or "").strip()
    if not projekt:
        return JSONResponse({"ok": False, "hinweis": "Projekt-/Ordnername noetig."})
    r = cutter_store.add({"id": uuid.uuid4().hex, "projekt": projekt[:200],
                          "note": ((d.get("note") or "").strip()[:500] or None),
                          "status": "queued", "quelle": "luna-os"})
    return JSONResponse({**r, "jobs": cutter_store.list(limit=100)})


def _reel_job_einreihen(*, thema: str = "", spiel: str = "", alle_spiele: bool = False,
                        min_dauer: float = 15.0, max_dauer: float = 45.0) -> dict:
    """Legt einen manuellen Themen-Reel-Job in die Queue. **Der Web-Prozess baut NICHT selbst** — das macht
    der Cutter-Worker (MACO470). Parameter stecken als JSON im `note`-Feld (Job-Schema bleibt unangetastet).
    Mindestlaenge nie unter 15 s (globale Regel)."""
    min_d = max(15.0, float(min_dauer or 15))
    max_d = max(min_d, float(max_dauer or 45))
    ziel = "alle Spiele" if alle_spiele else (spiel or "?")
    note = json.dumps({"typ": "reel", "thema": (thema or None),
                       "spiel": (None if alle_spiele else (spiel or None)), "alle_spiele": bool(alle_spiele),
                       "min_dauer": min_d, "max_dauer": max_d}, ensure_ascii=False)
    return cutter_store.add({"id": uuid.uuid4().hex, "projekt": f"🎬 Reel · {thema or 'Auto'} · {ziel}"[:200],
                             "note": note[:500], "status": "queued", "quelle": "luna-os"})


@app.post("/api/cutter/reel")
async def cutter_reel(request: Request):
    """Manuellen Themen-Reel anfordern (Thema, Einzelspiel/alle Spiele, Min-/Max-Laenge) -> Job in die Queue."""
    d = await _json(request)
    thema = (d.get("thema") or "").strip()
    alle = bool(d.get("alle_spiele"))
    spiel = (d.get("spiel") or "").strip()
    if not alle and not spiel:
        return JSONResponse({"ok": False, "hinweis": "Spielordner-Namen angeben oder 'alle Spiele' waehlen."})
    r = _reel_job_einreihen(thema=thema, spiel=spiel, alle_spiele=alle,
                            min_dauer=_inum(d.get("min_dauer")) or 15,
                            max_dauer=_inum(d.get("max_dauer")) or 45)
    if r.get("ok"):
        _changelog("Cutter", f"Manueller Reel-Auftrag: {thema or 'Auto'} ({'alle Spiele' if alle else spiel})",
                   "CEO ueber LUNA-OS", "cutter")
    return JSONResponse({**r, "jobs": cutter_store.list(limit=100)})


WORKER_HERZ = ROOT / "cutter_ops" / "worker_herzschlag.json"


def _herzschlag(user: str) -> None:
    """Lebenszeichen des Cutter-Workers festhalten. Nur dieser Endpunkt wird vom Worker gepollt (die
    Weboberflaeche nutzt `/api/cutter`) -- der Zeitstempel ist damit ein echter Herzschlag und nicht bloss
    „irgendwer hat die Seite offen". Die Betriebs-Wacht schlaegt Alarm, wenn er veraltet."""
    try:
        WORKER_HERZ.parent.mkdir(parents=True, exist_ok=True)
        WORKER_HERZ.write_text(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                           "user": user or ""}), "utf-8")
    except OSError:
        pass                                    # ein fehlender Herzschlag darf den Worker nie ausbremsen


@app.get("/api/cutter/queue")
def cutter_queue(request: Request):
    """Vom Cutter-Worker (MACO470) gepollt: offene (queued) Jobs."""
    _herzschlag(_pref_user(request))
    return {"jobs": [j for j in cutter_store.list(limit=100) if j.get("status") == "queued"]}


def _performance_agent():
    from ...core.aktivitaet import Aktivitaet
    from ...core.kosten import KostenStore
    from ...core.nutzung import NutzungStore
    from ...core.performance_agent import PerformanceAgent
    return PerformanceAgent(reels=reel_store, antraege=antraege, cutter=cutter_store,
                            aktivitaet=Aktivitaet(ROOT / "aktivitaet" / "log.jsonl"),
                            kosten=KostenStore(ROOT / "finance" / "kosten-log.jsonl"),
                            nutzung=NutzungStore(ROOT / "nutzung" / "log.jsonl"))


@app.get("/api/performance")
def performance(wochen: int = 8):
    """Woechentlicher Leistungsbericht (CDO, regelbasiert, kein LLM): Freigabequoten, Pipeline-Erfolg,
    Durchsatz, Kosten, Reaktionszeiten, Nutzung/Feature-Friedhof -- Woche vs. Vorwoche + Wochen-Historie."""
    agent = _performance_agent()
    b = agent.bericht()
    b["historie"] = agent.historie(wochen=max(2, min(26, int(wochen))))
    return JSONResponse(b)


@app.post("/api/nutzung")
async def nutzung_log(request: Request):
    """App-Oeffnung protokollieren (Feature-Friedhof; nur ts+app+user, CEO-gewollt 2026-07-10)."""
    from ...core.nutzung import NutzungStore
    body = await _json(request)
    NutzungStore(ROOT / "nutzung" / "log.jsonl").log((body or {}).get("app") or "",
                                                     user=_pref_user(request) or "")
    return JSONResponse({"ok": True})


@app.post("/api/cutter/report")
async def cutter_report(request: Request):
    """Der Mac-Cutter meldet Job-Status. Mit job_id -> vorhandene Zeile (aus /queue) aktualisieren;
    ohne job_id -> neue Zeile (auto-verarbeiteter Ordner)."""
    d = await request.json()
    felder = {k: d[k] for k in _CUTTER_REPORT_FELDER if k in d}
    jid = (d.get("job_id") or "").strip()
    if jid:
        r = cutter_store.patch(jid, felder)
    else:
        r = cutter_store.add({"id": uuid.uuid4().hex, "projekt": (d.get("projekt") or "")[:200],
                              "quelle": "mac", **felder})
    return JSONResponse(r)


# -- Backoffice (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 2): Warteschlange fuer das lokale LLM auf dem MACO470. ----
# Der Backoffice-Worker holt Auftraege per /naechster und meldet per /ergebnis. Meldung an den CEO: tagsueber einzeln
# (Outbox -> Telegram, voller Text per „zeig #xxxx"), zwischen 01 und 06 Uhr nur im Morgen-Briefing (CEO 2026-09-26).
BACKOFFICE_NACHT = (1, 6)


def _backoffice_nacht(jetzt: datetime | None = None) -> bool:
    if jetzt is None:
        try:
            from zoneinfo import ZoneInfo
            jetzt = datetime.now(ZoneInfo("Europe/Berlin"))
        except Exception:
            jetzt = datetime.now()
    return BACKOFFICE_NACHT[0] <= jetzt.hour < BACKOFFICE_NACHT[1]


@app.get("/api/backoffice")
def backoffice_liste():
    return {"auftraege": backoffice.list()[:100], "arten": list(AUFTRAG_ARTEN)}


@app.post("/api/backoffice/auftrag")
async def backoffice_auftrag(request: Request):
    d = await _json(request)
    try:
        aid = backoffice.anlegen(d.get("aufgabe") or "", art=d.get("art") or "sonstiges",
                                 von=_pref_user(request) or "CEO")
    except ValueError as exc:
        return JSONResponse({"ok": False, "hinweis": str(exc)})
    return JSONResponse({"ok": True, "id": aid, "kurz": kurz_id(aid)})


@app.get("/api/backoffice/naechster")
def backoffice_naechster():
    """Vom Backoffice-Worker gepollt: aeltesten offenen Auftrag holen (wird dabei in_arbeit)."""
    backoffice.aufraeumen(stunden=2)
    return {"auftrag": backoffice.naechster()}


@app.post("/api/backoffice/ergebnis")
async def backoffice_ergebnis(request: Request):
    d = await _json(request)
    aid = (d.get("id") or "").strip()
    a = backoffice.get(aid) if aid else None
    if a is None:
        return JSONResponse({"ok": False, "hinweis": "Unbekannter Auftrag."})
    meldung = "keine" if a.get("stumm") else ("briefing" if _backoffice_nacht() else "einzeln")
    titel = " ".join(a.get("aufgabe", "").split())[:80]
    if d.get("ok"):
        ergebnis = str(d.get("ergebnis") or "")
        backoffice.fertig(a["id"], ergebnis=ergebnis, modell=str(d.get("modell") or ""),
                          dauer_s=d.get("dauer_s") or 0, zweitmeinung=str(d.get("zweitmeinung") or ""),
                          meldung=meldung)
        text = f"Auftrag #{a['kurz']} erledigt: {titel}"
        detail = ergebnis + (f"\n\n--- Zweitmeinung (Gemini) ---\n{d['zweitmeinung']}" if d.get("zweitmeinung") else "")
    else:
        backoffice.fehlschlag(a["id"], grund=str(d.get("grund") or "unbekannt"), meldung=meldung)
        text = f"Auftrag #{a['kurz']} fehlgeschlagen: {titel} ({str(d.get('grund') or '')[:120]})"
        detail = str(d.get("grund") or "")
    if meldung == "einzeln":
        try:
            notifications.enqueue(text, abteilung="Backoffice", kategorie="backoffice", quelle="backoffice",
                                  detail=detail[:8000], dedup_stunden=0)
        except Exception:
            pass
    return JSONResponse({"ok": True, "meldung": meldung})


# -- #2: Nutzer-Praeferenzen (pro Nutzer, geraeteuebergreifend) -- z. B. das Dashboard-Layout. --------
# Kernendpunkt (kein Modul-Gate): jeder eingeloggte Nutzer liest/schreibt NUR seine eigenen Prefs
# (Schluessel = username). Ohne Tabelle/Supabase -> leer (Frontend faellt auf localStorage/Default zurueck).

def _pref_user(request: Request) -> str:
    u = getattr(request.state, "user", None) or {}
    return u.get("username") or _USER


@app.get("/api/prefs")
def prefs_get(request: Request):
    import urllib.parse as _up
    uname = _pref_user(request)
    if _sb is not None and _sb.verfuegbar():
        r = _sb.select("luna_os_prefs", params="select=prefs&username=eq." + _up.quote(uname) + "&limit=1")
        if r.get("ok") and r.get("rows"):
            return {"prefs": r["rows"][0].get("prefs") or {}}
    return {"prefs": {}}


@app.post("/api/prefs")
async def prefs_set(request: Request):
    uname = _pref_user(request)
    d = await request.json()
    prefs = d.get("prefs") if isinstance(d.get("prefs"), dict) else {}
    if _sb is not None and _sb.verfuegbar():
        _sb.upsert("luna_os_prefs", {"username": uname, "prefs": prefs}, on_conflict="username")
    return JSONResponse({"ok": True})


@app.get("/api/betrieb/status")
def betrieb_status():
    """Fuer den Waechter auf dem MACO470 (BETRIEB_ROADMAP Etappe 3): Bot-Herzschlag + haengende Telegram-Meldungen."""
    from ...core.betriebswaechter import status as _status
    return _status(ROOT / "orchestrator" / "state" / "bot_herzschlag.json", ROOT / "notifications" / "log.jsonl")


@app.get("/api/antraege/{antrag_id}")
def antrag_detail(antrag_id: str):
    a = antraege.get(antrag_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Antrag nicht gefunden")
    return _antrag_detail_dto(a)


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


def _innovation_pipe():
    """InnovationPipeline aus dem gecachten Kontext (Fachagenten via Gemini-Fallback). None ohne Kontext."""
    ctx = _ctx_cached()
    if ctx is None:
        return None
    from ...core.innovation import InnovationPipeline
    from ...governance.leak_guard import is_redactable_secret
    sec = [v for v in _CTX_CACHE["secrets"].values() if is_redactable_secret(v)]
    return InnovationPipeline(ctx.core, web=ctx.web, antraege=antraege, secrets=sec)


@app.post("/api/antraege/{antrag_id}/revidieren")
async def revidieren(antrag_id: str, request: Request):
    """CEO-Revision: Feedback (z. B. 'guenstiger/kostenlos') -> LUNA ueberarbeitet den Antrag und setzt
    ihn auf 'eingereicht' zurueck (Neufreigabe noetig)."""
    body = await _json(request)
    pipe = _innovation_pipe()
    if pipe is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Revision braucht den vollen LUNA-Kontext.")
    res = await asyncio.to_thread(pipe.revidiere, antrag_id, (body.get("feedback") or "").strip())
    return JSONResponse({"ok": bool(res.get("ok")), "res": res, "state": _state()})


@app.post("/api/antraege/neu-formatieren")
async def antraege_neu_formatieren():
    """Bringt alle offenen Antraege ins neue Format; freigegebene werden zurueckgesetzt (Neufreigabe)."""
    pipe = _innovation_pipe()
    if pipe is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Braucht den vollen LUNA-Kontext.")
    res = await asyncio.to_thread(pipe.neu_formatieren)
    return JSONResponse({"ok": True, "res": res, "state": _state()})


_CTX_CACHE: dict = {}
_SECRETS_CACHE: dict = {}
_LUNA_SESSION: dict = {}


def _secret(name: str) -> str:
    """Liest einen Wert aus orchestrator/.env (gecacht). Unabhaengig vom Anthropic-Zugang --
    damit z. B. ElevenLabs-TTS auch dann geht, wenn die volle LUNA mangels Anthropic-Key ausfaellt."""
    return _secrets_dict().get(name) or os.environ.get(name, "")


def _secrets_dict() -> dict:
    """Vollstaendiges (gecachtes) Secrets-Dict aus orchestrator/.env -- fuer Aufrufer, die mehrere Keys auf
    einmal brauchen (z. B. der manuelle Instagram-DM-Sync). Unabhaengig vom Anthropic-Zugang."""
    if "d" not in _SECRETS_CACHE:
        try:
            from ..telegram.bot import _load_secrets
            _SECRETS_CACHE["d"] = _load_secrets()
        except Exception:
            _SECRETS_CACHE["d"] = {}
    return _SECRETS_CACHE["d"]


def _ctx_cached():
    """Baut den vollen LUNA-Werkzeugkontext EINMAL (schwer) und cacht ihn. None ohne Anthropic-Key."""
    if "ctx" in _CTX_CACHE:
        return _CTX_CACHE["ctx"]
    try:
        from ..telegram.bot import _build_ctx, _load_config, _load_secrets
        cfg = _load_config()
        secrets = _load_secrets()
        if not secrets.get("ANTHROPIC_API_KEY"):
            _CTX_CACHE["ctx"] = None
            return None
        ctx, _ = _build_ctx(cfg, secrets)
        _CTX_CACHE.update(ctx=ctx, cfg=cfg, secrets=secrets)
        return ctx
    except Exception as exc:
        print(f"[luna] Voller Kontext nicht verfuegbar, Fallback auf einfachen LLM: {exc}", flush=True)
        _CTX_CACHE["ctx"] = None
        return None


def _make_conversation():
    """Frische HoaConversation aus dem gecachten Kontext (echte Tool-Schleife). None ohne Kontext.
    Frisch = kein geteilter Verlauf -> fuer Einmal-Aufgaben (z. B. Mehr-Info)."""
    ctx = _ctx_cached()
    if ctx is None:
        return None
    from ..telegram.bot import _fallbacks
    from ...core.hoa_conversation import HoaConversation
    cfg, secrets = _CTX_CACHE["cfg"], _CTX_CACHE["secrets"]
    model = cfg.get("voice", {}).get("llm_model", "claude-haiku-4-5")
    return HoaConversation(ctx, model=model, api_key=secrets["ANTHROPIC_API_KEY"],
                           fallbacks=_fallbacks(secrets, cfg))


def _luna_session():
    """Persistente LUNA-Gespraechssitzung fuer den Orb/Chat (haelt den Verlauf). None ohne Kontext."""
    if "conv" not in _LUNA_SESSION:
        _LUNA_SESSION["conv"] = _make_conversation()
    return _LUNA_SESSION["conv"]


def _elevenlabs_tts(text: str, voice_id: str, key: str):
    """Spricht Text mit ElevenLabs (eleven_turbo_v2_5) -> MP3-Bytes. None bei Fehler."""
    import urllib.request
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    payload = json.dumps({"text": text, "model_id": "eleven_turbo_v2_5",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except Exception as exc:
        print(f"[tts] ElevenLabs-Fehler: {str(exc)[:160]}", flush=True)
        return None


@app.post("/api/antraege/{antrag_id}/mehr-info")
async def mehr_info(antrag_id: str):
    a = antraege.get(antrag_id) or {}
    titel = (a.get("titel") or antrag_id)[:90]
    beschreibung = (a.get("beschreibung") or "(keine)")[:1500]
    conv = _make_conversation()
    if conv is not None:
        # Voll-agentisch: LUNA bewertet mit echten Werkzeugen (delegate an CTO/CFO, recherche_beauftragen).
        auftrag = (
            "Hole mehr Infos zu diesem offenen Antrag und bewerte ihn entscheidungsreif fuer den CEO. "
            "Konsultiere dazu den CTO (technische Machbarkeit) und den CFO (grobe Kosten) per 'delegate'; "
            "wenn externe Fakten fehlen, nutze 'recherche_beauftragen'. Fasse danach in max. 6 Saetzen "
            "zusammen: Nutzen, Machbarkeit, Kosten, klare Empfehlung (freigeben/ablehnen/nachschaerfen). "
            "Lege selbst KEINEN neuen Antrag an und entscheide nicht -- nur bewerten.\n\n"
            f"Antrag {antrag_id} -- Titel: {titel}\nBeschreibung: {beschreibung}")
        try:
            bewertung = (await asyncio.to_thread(conv.respond, auftrag)).strip()
        except Exception as exc:
            bewertung = f"(Agentische Bewertung fehlgeschlagen: {str(exc)[:160]})"
        tid = None  # delegate/recherche legen ihre eigenen Tickets an
    else:
        # Fallback (lokal/ohne Anthropic-Key): ein einfacher Gemini-Bewertungs-Call.
        prompt = ("Du bist ein erfahrener Berater (CTO/CFO-Sicht) eines Agenten-Unternehmens. Bewerte den "
                  "folgenden Antrag KURZ (max. 5 Saetze): Nutzen, technische Machbarkeit, grobe Kosten, "
                  "Empfehlung (freigeben/ablehnen/nachschaerfen). Antwort auf Deutsch.\n\n"
                  f"Titel: {titel}\nBeschreibung: {beschreibung}")
        bewertung = _llm([{"role": "user", "content": prompt}]) or "(Bewertung aktuell nicht verfügbar.)"
        tid = research.erstellen(f"Mehr Infos/Bewertung zum Antrag: {titel}", abteilung="Head of Agents")
    notifications.enqueue(f"Agenten-Bewertung zu '{titel}': {bewertung}",
                          abteilung="Berater/CTO/CFO", kategorie="bewertung", detail=bewertung)
    return JSONResponse({"ok": True, "ticket": tid, "bewertung": bewertung, "state": _state()})


LUNA_SYS = ("Du bist LUNA, der Head of Agents eines KI-Agenten-Unternehmens und Nils' persönlicher "
            "Assistent. Antworte kurz, hilfsbereit und auf Deutsch mit echten Umlauten (ä, ö, ü, ß -- "
            "niemals ae/oe/ue/ss). Du hilfst beim Bearbeiten von Anträgen, Meldungen und Aufgaben.")


def _llm(messages):
    """Ein LLM-Aufruf ueber Gemini (gratis) -> OpenAI-Fallback. Leck-geschuetzt. Leerer String bei Fehler."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return ""
    try:
        import openai

        from ...governance.leak_guard import is_redactable_secret, redact
        from ...core.model_router import GEMINI_BASE_URL
        base = GEMINI_BASE_URL if os.environ.get("GEMINI_API_KEY") else None
        model = "gemini-2.5-flash" if base else "gpt-4o-mini"
        client = openai.OpenAI(api_key=key, base_url=base)
        r = client.chat.completions.create(model=model, messages=messages)
        out = (r.choices[0].message.content or "").strip()[:1600]
        sec = [v for v in os.environ.values() if is_redactable_secret(v)]
        return redact(out, sec)
    except Exception as exc:
        return f"(LLM-Fehler: {str(exc)[:120]})"


@app.post("/api/chat")
async def chat(request: Request):
    body = await _json(request)
    msg = (body.get("message") or "").strip()
    if not msg:
        return JSONResponse({"reply": ""})
    # Echte LUNA: volle HoaConversation (Persona + Tools + Verlauf). Der Orb spricht so mit der
    # gleichen LUNA wie Telegram. Fallback: einfacher Persona-LLM-Call ohne Anthropic-Key.
    conv = _luna_session()
    if conv is not None:
        try:
            reply = await asyncio.to_thread(conv.respond, msg[:2000])
            return JSONResponse({"reply": reply or "(keine Antwort)"})
        except Exception as exc:
            print(f"[luna chat] Fehler, Fallback auf einfachen LLM: {exc}", flush=True)
    messages = [{"role": "system", "content": LUNA_SYS}]
    for h in (body.get("history") or [])[-8:]:
        rolle = "assistant" if h.get("role") == "luna" else "user"
        messages.append({"role": rolle, "content": str(h.get("text", ""))[:1200]})
    messages.append({"role": "user", "content": msg[:2000]})
    return JSONResponse({"reply": _llm(messages) or "(Kein Modell verfügbar.)"})


@app.post("/api/tts")
async def tts(request: Request):
    """Spricht Text mit LUNAs ElevenLabs-Stimme (Premium). Liefert MP3. 503/502, wenn nicht
    verfuegbar -> das Frontend faellt dann auf die Browser-Stimme zurueck."""
    body = await _json(request)
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Text")
    key = _secret("ELEVENLABS_API_KEY")
    if not key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "TTS nicht konfiguriert")
    # LUNA-OS spricht mit der deutschen Stimme „Lola" (CEO-Wahl); per .env LUNA_OS_VOICE_ID ueberschreibbar.
    from ..voice.voices import GERMAN_VOICES
    lola = next((v["id"] for v in GERMAN_VOICES if v["name"] == "Lola"), GERMAN_VOICES[0]["id"])
    voice_id = _secret("LUNA_OS_VOICE_ID") or lola
    audio = await asyncio.to_thread(_elevenlabs_tts, text[:1500], voice_id, key)
    if not audio:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "TTS fehlgeschlagen")
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/sehen")
async def sehen(request: Request):
    """LUNAs Augen: nimmt einen Screenshot (base64-PNG vom Orb) + optionale Frage und liefert eine
    Beschreibung via Vision-Modell (Gemini, gratis). Der Screenshot kommt vom Orb (Screen-Recording)."""
    import base64

    from runner.vision import bild_lesen
    body = await _json(request)
    b64 = (body.get("bild_base64") or "").strip()
    if not b64:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Bild")
    try:
        img = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ungueltiges Bild")
    res = await asyncio.to_thread(bild_lesen, img, (body.get("frage") or ""))
    return JSONResponse(res)


# ---- Second Brain (Wissensbasis) ----
def _brain_item_dto(e):
    return {"id": e.get("id"), "titel": e.get("titel") or (e.get("text", "")[:50]),
            "text": e.get("text", ""), "tags": e.get("tags", []), "quelle": e.get("quelle", "notiz"),
            "ts": e.get("ts", "")}


@app.get("/api/brain")
def brain_liste(q: str = ""):
    q = (q or "").strip()
    if q:
        # quellenuebergreifend, wenn die volle LUNA-ctx verfuegbar ist; sonst nur der Wissensspeicher.
        ctx = _ctx_cached()
        if ctx is not None:
            from ...core.hoa_tools import _brain_suchen
            res = _brain_suchen(q, ctx, [])
            return {"q": q, "treffer": res.get("treffer", [])}
        return {"q": q, "treffer": [{"quelle": "brain:" + e.get("quelle", "notiz"),
                                     "titel": e.get("titel") or e.get("text", "")[:50],
                                     "text": e.get("text", "")[:300], "ref": e.get("id", "")}
                                    for e in brain.suchen(q)]}
    return {"items": [_brain_item_dto(e) for e in brain.list(40)]}


@app.post("/api/brain")
async def brain_merken(request: Request):
    body = await _json(request)
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Text")
    bid = brain.merken(text, titel=(body.get("titel") or ""), tags=body.get("tags") or [], quelle="ceo")
    _changelog("LUNA-OS", f"Wissen im Second Brain gemerkt ({bid})", "CEO ueber LUNA-OS", "brain")
    return JSONResponse({"ok": True, "id": bid, "items": [_brain_item_dto(e) for e in brain.list(40)]})


# Org-Hierarchie (stabil, aus governance/organigramm.md). Status wird live aus dem Aktivitaetsprotokoll
# hergeleitet: kuerzlich aktiv -> 'active', vorhanden aber ruhig -> 'standby', geplant/nicht aktiviert -> 'offline'.
_DEPARTMENTS = [
    ("berater", "01 · Berater", "Unternehmensberater / Innovation", []),
    ("cao", "02 · CAO", "Admin & Operations", []),
    ("cfo", "03 · CFO", "Finance", []),
    ("cro", "04 · CRO", "Revenue / Sponsoring", []),
    ("ciso", "05 · CISO", "Security", []),
    ("cbo", "06 · CBO", "Business Development", []),
    ("cpo", "07 · CPO", "Product", []),
    ("cto", "08 · CTO", "IT / Technik", [("backend", "Backend", "offline"),
                                         ("devops", "DevOps/Infra", "offline")]),
    ("cxo", "09 · CXO", "Experience", []),
    ("cco", "10 · CCO", "Content / Marketing", [("cutter", "Video-Cutter", "standby")]),
    ("cdo", "11 · CDO", "Data", []),
    ("chro", "12 · CHRO", "People", []),
    ("clo", "13 · CLO", "Legal", []),
    ("cko", "14 · CKO", "Knowledge", []),
    ("researcher", "15 · Researcher", "Web-Recherche", []),
    ("cio", "16 · CIO", "Investment", [("risk", "Risk-Agent", "standby")]),
]


def _aktive_akteure(minuten: int = 90) -> set:
    """Kleingeschriebene Kuerzel der Akteure, die in den letzten N Minuten etwas getan haben."""
    from datetime import datetime, timedelta
    grenze = (datetime.now() - timedelta(minutes=minuten)).isoformat(timespec="seconds")
    aktiv = set()
    for e in _aktivitaet_letzte(200):
        if (e.get("ts") or "") >= grenze:
            aktiv.add((e.get("akteur") or "").strip().lower())
    return aktiv


@app.get("/api/agenten")
def agenten():
    """Org-Mindmap der Agenten mit Live-Status (active/standby/offline)."""
    aktiv = _aktive_akteure()

    def _status(key: str, default: str = "standby") -> str:
        aliases = {key}
        if key == "berater":
            aliases |= {"beratung", "innovation"}
        if key == "cio":
            aliases.add("investment")
        if key == "researcher":
            aliases.add("recherche")
        return "active" if any(al in a for a in aktiv for al in aliases) else default

    depts = []
    for key, name, rolle, subs in _DEPARTMENTS:
        st = _status(key)
        # Researcher gilt als aktiv, wenn offene Tickets laufen
        if key == "researcher" and [t for t in research.list() if t.get("status") in ("offen", "in_arbeit")]:
            st = "active"
        depts.append({"key": key, "name": name, "rolle": rolle, "status": st,
                      "subs": [{"key": sk, "name": sn, "status": ss} for sk, sn, ss in subs]})
    luna_active = bool(aktiv & {"head of agents", "luna", "ceo", "mac-aktuator", "cfo", "cto"}) or True
    return {
        "ceo": {"name": "CEO (Nils)", "rolle": "Auftraggeber", "status": "human"},
        "luna": {"name": "LUNA", "rolle": "Head of Agents", "status": "active" if luna_active else "standby"},
        "departments": depts,
        "stand": _now_iso(),
    }


def _now_iso():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


@app.get("/api/overview")
def overview():
    """Command-Center-Uebersicht: reale Counts, Provider-Status (aus .env), Agentenliste."""
    offene = _offene_antraege()
    offene_research = [t for t in research.list() if t.get("status") in ("offen", "in_arbeit")]
    providers = [{"name": n, "connected": bool(_secret(k))} for n, k in (
        ("Claude", "ANTHROPIC_API_KEY"), ("Gemini", "GEMINI_API_KEY"), ("OpenAI", "OPENAI_API_KEY"),
        ("ElevenLabs", "ELEVENLABS_API_KEY"), ("Deepgram", "DEEPGRAM_API_KEY"), ("Brave", "BRAVE_API_KEY"),
        ("GitHub", "GITHUB_TOKEN"), ("Google", "GOOGLE_OAUTH_REFRESH_TOKEN"))]
    agenten = [
        {"name": "LUNA Core", "status": "active"},
        {"name": "Researcher", "status": "active" if offene_research else "standby"},
        {"name": "Berater", "status": "standby"},
        {"name": "CTO / IT", "status": "standby"},
        {"name": "CFO / Finance", "status": "standby"},
        {"name": "Self-Maintenance", "status": "active"},
    ]
    return {
        "counts": {
            "antraege": len(offene),
            "meldungen": len(notifications.pending()),
            "research": len(offene_research),
            "wissen": len(brain.list(100000)),
            "aktivitaet": len(_aktivitaet_letzte(100000)),
        },
        "providers": providers,
        "providers_connected": sum(1 for p in providers if p["connected"]),
        "agenten": agenten,
        "monatsbudget": _budget(),
    }


def _investment_engine():
    """Lazy InvestmentEngine aus den .env-Keys (Capability). Advisory, keine Trades."""
    _secret("X")  # befuellt _SECRETS_CACHE["d"]
    from ...investment.engine import InvestmentEngine
    from ...investment.providers import MarketData
    md = MarketData(secrets=_SECRETS_CACHE.get("d", {}))
    return InvestmentEngine(md, inv_store, brain=brain.merken)


def _paper_broker():
    """Alpaca-Paper-Broker aus den .env-Keys (Capability). Read-only genutzt; inert ohne Keys."""
    from ...investment.broker import AlpacaPaperBroker
    s = _secrets_dict()
    return AlpacaPaperBroker(s.get("ALPACA_API_KEY", ""), s.get("ALPACA_API_SECRET", ""))


def _letzte_shortlist():
    scr = inv_store.list("screening")
    return scr[-1].get("shortlist", []) if scr else []


@app.get("/api/investment")
def investment():
    eng = _investment_engine()
    st = eng.status()
    return {
        "modus": st["modus"],
        "provider": [{"name": p["name"], "konfiguriert": p.get("konfiguriert")} for p in st["provider"]],
        "fehlende_keys": [p["name"] for p in st["fehlende_keys"]],
        "watchlist": st["watchlist"],
        "scorecard": eng.scorecard(),
        "historie": inv_store.historie(),
        "shortlist": _letzte_shortlist()[:12],
        "vorschlaege": [{"symbol": s.get("symbol"), "aktion": s.get("aktion"), "grund": s.get("grund"),
                         "risiko_label": s.get("risiko_label"), "konfidenz": s.get("konfidenz"),
                         "quellen": s.get("quellen", []), "ts": s.get("ts")}
                        for s in reversed(inv_store.list("suggestions"))][:15],
        "insider": [{"symbol": s.get("symbol"), "cluster": s.get("cluster"), "betrag": s.get("betrag"),
                     "rolle": s.get("rolle"), "konfidenz": s.get("konfidenz"),
                     "filing_url": s.get("filing_url"), "datum": s.get("datum"), "ts": s.get("ts")}
                    for s in inv_store.insider_signals(15)],
    }


def _inum(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _investment_loop_payload() -> dict:
    """Lern-Loop-Daten fuer das Command-Center: Kennzahlen (gesamt/je Version/je Anlageklasse), Fehler-Verlauf,
    offene Prognosen und das Abweichungs-Register. Liest die vom Bot geschriebene Datei (geteiltes Volume)."""
    from ...investment.autonomy_policy import AutonomyPolicy
    from ...investment.forecaster import Forecaster
    from ...investment.insider import InsiderModel
    fc = Forecaster(loop_store)
    modus = inv_store.mode()
    devs = loop_store.list("inv_deviations")
    fcs = loop_store.list("inv_forecasts")
    feats = loop_store.list("inv_features")
    bewertet = {d.get("forecast_id") for d in devs}
    offen = [f for f in fcs if f.get("id") not in bewertet]
    return {
        "modell_version": Forecaster.MODELL_VERSION,
        "kennzahlen": fc.kennzahlen(),
        "verlauf": fc.verlauf(),
        "insider_kontrolle": InsiderModel(None, loop_store).markt_kontrolle(),

        "offene_prognosen": [
            {"symbol": f.get("symbol"), "asset": f.get("asset", "aktie"), "richtung": f.get("richtung"),
             "ziel_return_pct": _inum(f.get("ziel_return_pct")), "konfidenz": _inum(f.get("konfidenz")),
             "erstellt_am": f.get("erstellt_am"), "faellig_am": f.get("faellig_am")}
            for f in reversed(offen)][:20],
        "register": [
            {"symbol": d.get("symbol"), "asset": d.get("asset", "aktie"),
             "prognose_return_pct": _inum(d.get("prognose_return_pct")),
             "real_return_pct": _inum(d.get("real_return_pct")), "fehler_abs_pct": _inum(d.get("fehler_abs_pct")),
             "richtungstreffer": bool(d.get("richtungstreffer")),
             "besser_als_baseline": bool(d.get("besser_als_baseline")), "backtest": bool(d.get("backtest")),
             "faellig_am": d.get("faellig_am"), "modell_version": d.get("modell_version")}
            for d in reversed(devs)][:20],
        "panel": {"symbole": len({e.get("symbol") for e in feats}), "snapshots": len(feats),
                  "letzter": loop_store.last_datum("inv_features")},
        "leitplanken": {"modus": modus, "autonom_aktiv": modus in ("paper", "live"),
                        "konfiguration": AutonomyPolicy().konfiguration()},
    }


@app.get("/api/investment/loop")
def investment_loop():
    return _investment_loop_payload()


@app.post("/api/investment/sammeln")
async def investment_sammeln():
    """'Jetzt sammeln': Merkmals-/Preis-Snapshot der Watchlist+Universum + faellige Prognosen/Abgleich --
    fuellt den Walk-Forward-Loop sofort (statt bis 07:00 zu warten). Advisory, keine Trades."""
    eng = _investment_engine()

    def run():
        from ...investment.features import FeatureCollector
        from ...investment.forecaster import Forecaster
        from ...investment.universe import panel
        wl = eng.store.watchlist()
        r = FeatureCollector(eng.market, loop_store).collect(wl)
        fc = Forecaster(loop_store)
        p = fc.prognostizieren(panel(wl))
        a = fc.auswerten()
        return {"gesammelt": len(r.get("gesammelt", [])), "uebersprungen": len(r.get("uebersprungen", [])),
                "prognosen_neu": len(p.get("erstellt", [])), "ausgewertet": a.get("neu_bewertet", 0),
                "hinweise": r.get("hinweise", [])[:3]}

    res = await asyncio.to_thread(run)
    return JSONResponse({"ok": True, **res, "loop": _investment_loop_payload()})


@app.post("/api/investment/backfill")
async def investment_backfill(request: Request):
    """Historie-Backfill (echte Tageskurse seit `seit`) + rueckwirkender Backtest -> Register/KPIs sofort gefuellt.
    Backtest schaltet keine Autonomie frei (nur Live zaehlt). Advisory, keine Trades."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    seit = (body.get("seit") or "2026-01-01").strip()
    eng = _investment_engine()

    def run():
        from ...investment.backfill import Backfill
        from ...investment.features import BASELINES
        from ...investment.forecaster import Forecaster
        from ...investment.universe import panel
        ziele = panel(eng.store.watchlist()) + BASELINES
        bf = Backfill(eng.market, loop_store)
        h = bf.lade_historie(ziele, seit=seit)
        b = bf.backtest()
        Forecaster(loop_store).prognostizieren(panel(eng.store.watchlist()))   # aktuelle Prognose(n)
        from ...investment.insider import InsiderModel                          # v4 = Insider-Discovery, 30-Tage
        im = InsiderModel(eng.market, loop_store)
        iv = im.backtest(seit=seit)
        il = im.live_prognosen()
        return {"zeilen_neu": h.get("zeilen_neu", 0), "auswertungen_neu": b.get("auswertungen_neu", 0),
                "insider_auswertungen_neu": iv.get("auswertungen_neu", 0),
                "insider_wochen": iv.get("insider_wochen", 0),
                "insider_live_prognosen": len(il.get("erstellt", [])),
                "hinweise": (h.get("hinweise", []) + iv.get("hinweise", []))[:8]}

    res = await asyncio.to_thread(run)
    return JSONResponse({"ok": True, **res, "loop": _investment_loop_payload()})


@app.post("/api/investment/screen")
async def investment_screen():
    eng = _investment_engine()
    r = await asyncio.to_thread(eng.screen_und_vorschlagen)
    return JSONResponse({"ok": True, "erstellt": len(r.get("erstellt", [])),
                         "abgelehnt": len(r.get("vom_risk_abgelehnt", [])),
                         "hinweise": r.get("hinweise", []), "investment": investment()})


@app.post("/api/investment/insider-scan")
async def investment_insider_scan():
    """Insider-Screen (SEC Form 4) ueber die Watchlist -> Signale/Alerts. Advisory, keine Trades."""
    eng = _investment_engine()
    r = await asyncio.to_thread(eng.insider_scan)
    return JSONResponse({"ok": True, "signale": len(r.get("signale", [])),
                         "hinweise": r.get("hinweise", []), "investment": investment()})


# -- Collab-CRM: Instagram-Webhook (nur Empfang/Tracken -- kein Senden) --
def _instagram():
    _secret("X")  # befuellt _SECRETS_CACHE["d"]
    from ...governance.instagram import InstagramAuth, InstagramMessaging
    return InstagramMessaging(InstagramAuth.from_env(_SECRETS_CACHE.get("d", {})))


@app.get("/api/webhook/instagram")
async def instagram_verify(request: Request):
    """Meta-Verify-Handshake (GET): gibt hub.challenge zurueck, wenn der Verify-Token stimmt."""
    p = request.query_params
    challenge = _instagram().verify_challenge(p.get("hub.mode", ""), p.get("hub.verify_token", ""),
                                              p.get("hub.challenge", ""))
    if challenge is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verify fehlgeschlagen.")
    return Response(content=challenge, media_type="text/plain")


@app.post("/api/webhook/instagram")
async def instagram_webhook(request: Request):
    """Eingehende Instagram-DMs -> CrmStore. HMAC-Signatur pflicht. Nur Empfang, kein Senden."""
    ig = _instagram()
    body = await request.body()
    if not ig.signatur_gueltig(body, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Signatur ungueltig.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload kein JSON.")
    erfasst = 0
    for n in ig.nachrichten_aus_webhook(payload):
        absender = n.get("absender") or "unbekannt"
        r = crm_store.verarbeite_eingang(absender, n["text"], quelle="instagram", absender=absender,
                                         extern_id=n.get("extern_id", ""))
        if not r.get("mid"):
            continue
        erfasst += 1
        # Auch ins Collab-Radar-Voll-Archiv spiegeln (eingehend) -> Radar waechst in Echtzeit mit, unabhaengig
        # von der (fuer grosse Postfaecher unzuverlaessigen) Konversations-Enumeration.
        try:
            ig_inbox_store.nachricht_hinzu(absender, absender, richtung="ein", text=n.get("text", ""),
                                           medien=False, extern_id=n.get("extern_id", ""),
                                           ts_msg=str(n.get("ts") or ""))
        except Exception:
            pass
        if r.get("kategorie") == "kooperation":   # nur Kooperationsanfragen melden (kein Spam bei Privatem)
            try:
                notifications.enqueue(f"Neue Kooperations-DM von {r['firma']} (Instagram): {n['text'][:180]}",
                                      abteilung="CRO", kategorie="anliegen",
                                      detail="Collab-CRM -> pruefen/antworten (kein Auto-Senden).")
            except Exception:
                pass
            try:
                brain.merken(f"Instagram-Kooperationsanfrage von {r['firma']}: {n['text'][:240]}",
                             titel=f"Collab-Anfrage {r['firma']}", tags=["crm", "cro", "instagram"],
                             quelle="crm", ref="crm:" + (n.get("extern_id") or r["mid"]))
            except Exception:
                pass
    return JSONResponse({"ok": True, "erfasst": erfasst})


@app.get("/api/crm")
def crm():
    """Collab-CRM (CRO): Pipeline-Uebersicht, Firmen (nach letztem Kontakt) + offene To-dos. Nur Lesen."""
    firmen = crm_store.firmen()
    firmen.sort(key=lambda f: f.get("letzter_kontakt") or "", reverse=True)
    return {
        "uebersicht": crm_store.uebersicht(),
        "firmen": [{"firma": f.get("firma"), "status": f.get("status"), "nachrichten": f.get("nachrichten"),
                    "quelle": f.get("quelle"), "letzter_kontakt": f.get("letzter_kontakt")}
                   for f in firmen][:40],
        "todos": [{"id": t.get("id"), "firma": t.get("firma"), "vorschlag": t.get("vorschlag"),
                   "begruendung": t.get("begruendung"), "ts": t.get("ts")}
                  for t in crm_store.todos(nur_offen=True)][:40],
    }


@app.get("/api/crm/konversation")
def crm_konversation(firma: str):
    msgs = crm_store.konversation(firma)
    return {"firma": firma, "nachrichten": [{"richtung": m.get("richtung"), "text": m.get("text"),
            "kategorie": m.get("kategorie"), "ts": m.get("ts"), "quelle": m.get("quelle")}
            for m in msgs][-50:]}


@app.get("/api/crm/timeline")
def crm_timeline(firma: str = ""):
    """Phase 20: kanaluebergreifende Nachrichten-Timeline (Instagram/Mail/... chronologisch)."""
    return {"nachrichten": crm_store.timeline(firma=(firma or None), limit=120)}


@app.post("/api/crm/todo/{todo_id}/erledigen")
def crm_todo_erledigen(todo_id: str):
    crm_store.todo_erledigen(todo_id)
    return JSONResponse({"ok": True})


# -- Kunden-Stammdaten (KUNDEN_FINANZEN Etappe 2; Modul crm ueber den Pfad /api/crm) -----------------------------

def _von(request: Request) -> str:
    u = getattr(request.state, "user", None) or {}
    return "LUNA-OS:" + (u.get("username") or "ceo")


def _kunden_aktion(fn):
    """Fachfehler als {ok: false, hinweis} (200), damit die Oberflaeche den Grund anzeigen kann."""
    try:
        return {"ok": True} | fn()
    except DubletteFehler as exc:
        return {"ok": False, "hinweis": str(exc), "dublette": exc.nummern}
    except KeyError as exc:
        return {"ok": False, "hinweis": f"Nicht gefunden: {exc.args[0] if exc.args else ''}"}
    except ValueError as exc:
        return {"ok": False, "hinweis": str(exc)}


def _mit_aufraeumen(fn, von: str = "LUNA"):
    """Aktion ausfuehren und danach erledigte Kalender-Erinnerungen (Angebot angenommen/abgelehnt, Rechnung bezahlt/
    storniert) sofort aus LUNAs Kalender loeschen. Fehler beim Aufraeumen blockieren die Aktion nie (Bot holt nach)."""
    def tun():
        r = fn()
        try:
            from ...core.erinnerungen import erledigte_entfernen
            weg = erledigte_entfernen(kunden_store.bh, _google(), von=von)
        except Exception:
            weg = []
        if weg:
            r = dict(r) | {"hinweise": list(r.get("hinweise") or [])
                           + [f"{len(weg)} Kalender-Erinnerung(en) entfernt ({', '.join(sorted({x['bezug'] for x in weg}))})."]}
        return r
    return tun


@app.get("/api/crm/kunden")
def kunden_liste(suche: str = ""):
    """Firmen mit Firmenkundennummer + Collab-Firmen, die noch keiner Nummer zugeordnet sind."""
    zuordnung = kunden_store.collab_zuordnung()
    ohne = [{"firma": f.get("firma"), "status": f.get("status"), "nachrichten": f.get("nachrichten"),
             "quelle": f.get("quelle"), "letzter_kontakt": f.get("letzter_kontakt")}
            for f in crm_store.firmen() if (f.get("firma") or "").strip().lower() not in zuordnung]
    ohne.sort(key=lambda f: f.get("letzter_kontakt") or "", reverse=True)
    return {"firmen": kunden_store.firmen(suche=suche), "collab_ohne_nummer": ohne}


@app.get("/api/crm/kunden/{nummer}")
def kunden_detail(nummer: str):
    f = kunden_store.firma(nummer)
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Firmenkundennummer")
    from ...core.firmendaten import NAMEN, luecken, offene_vorschlaege
    v = offene_vorschlaege(kunden_store.bh.eintraege()).get(f["nummer"]) or {}
    return {"firma": f, "buchungen": _firma_buchungen(f["nummer"]), "luecken": luecken(f), "feldnamen": NAMEN,
            "vorschlaege": v.get("vorschlaege") or {}, "vorschlag_quelle": v.get("quelle", ""),
            "vorschlag_ts": v.get("ts", "")}


def _akte():
    from ...core.firmenakte import Firmenakte
    return Firmenakte(kunden_store.bh, kunden_store)


@app.get("/api/crm/kunden/{nummer}/akte")
def kunden_akte(nummer: str):
    """Etappe 24: Dokumente und Mails der Firma (neueste zuerst)."""
    from ...core.firmenakte import ARTEN
    try:
        return {"dokumente": _akte().akte(nummer), "arten": ARTEN}
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Firma") from None


@app.post("/api/crm/kunden/{nummer}/akte")
async def kunden_akte_hochladen(nummer: str, request: Request):
    body = await _json(request)

    def tun():
        daten, name = _datei_b64(body.get("datei"))
        return _akte().hochladen(nummer, daten, name, titel=body.get("titel") or "", art=body.get("art") or "sonstiges",
                                 datum=body.get("datum") or "", bezug=body.get("bezug") or "", notiz=body.get("notiz") or "",
                                 von=_von(request))
    return _kunden_aktion(tun)


@app.get("/api/crm/akte/offen")
def akte_offen():
    return {"mails": [{k: m.get(k) for k in ("id", "titel", "datum", "mail_von", "notiz", "kandidaten", "ts")}
                      for m in _akte().offene()]}


@app.post("/api/crm/akte/{did}/zuordnen")
async def akte_zuordnen(did: str, request: Request):
    """Mail ohne eindeutige Firma zuordnen; leere Firma = gehoert zu keiner Firma (erledigt)."""
    body = await _json(request)
    return _kunden_aktion(lambda: _akte().zuordnen(did, body.get("firma") or "", von=_von(request)))


@app.get("/api/crm/akte/{did}/datei")
def akte_datei(did: str, i: int = 0):
    a = _akte()
    x = a.dokument(did) or next((m for m in a.offene() if m["id"] == did), None)
    if not x or not 0 <= i < len(x.get("dateien") or []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekanntes Dokument")
    d = x["dateien"][i]
    endung = Path(d.get("name") or d["pfad"]).suffix.lower()
    mime = {".pdf": "application/pdf", ".eml": "message/rfc822", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png"}.get(endung, "application/octet-stream")
    art = "inline" if mime in ("application/pdf", "image/jpeg", "image/png") else "attachment"
    return Response((kunden_store.bh.dir / d["pfad"]).read_bytes(), media_type=mime,
                    headers={"Content-Disposition": f'{art}; filename="{Path(d.get("name") or d["pfad"]).name}"'})


_RECHERCHE_TEST = None                     # Tests: FirmenRecherche mit Fake-Suche/-Abruf (kein Netz)


def _recherche():
    """Etappe 22: Firmendaten-Recherche mit Brave-Suche (nur wenn BRAVE_API_KEY gesetzt) und Impressums-Abruf."""
    from ...core.firmendaten import FirmenRecherche
    if _RECHERCHE_TEST is not None:
        return _RECHERCHE_TEST
    try:
        from ..telegram.bot import _load_secrets
        sec = _load_secrets()
    except Exception:
        sec = dict(os.environ)
    from ...governance.web_research import BraveProvider
    brave = BraveProvider(sec)
    suche = (lambda q: [(t.titel, t.url) for t in brave.suche(q, max_results=8).treffer]) if brave.verfuegbar() else None
    return FirmenRecherche(kunden_store, suche=suche)


@app.post("/api/crm/kunden/{nummer}/recherche")
async def kunden_recherche(nummer: str, request: Request):
    """Oeffentliche Firmendaten (Impressum) suchen -> Vorschlaege fuer leere Felder; uebernommen wird nur per Klick."""
    return _kunden_aktion(lambda: _recherche().recherchieren(nummer, von=_von(request)))


@app.post("/api/crm/kunden/{nummer}/vorschlaege")
async def kunden_vorschlaege(nummer: str, request: Request):
    """{"felder": [...] (leer = alle), "verwerfen": false} -- Vorschlaege uebernehmen bzw. verwerfen."""
    from ...core.firmendaten import uebernehmen
    body = await _json(request)
    return _kunden_aktion(lambda: uebernehmen(kunden_store, nummer, body.get("felder") or None,
                                              verwerfen=bool(body.get("verwerfen")), von=_von(request)))


def _firma_buchungen(nummer: str) -> dict:
    """Etappe 14: alles, was unter dieser Nummer laeuft -- Belege, Zahlungen je Jahr, erkannte Abos."""
    from ...core.eigenbelege import EigenbelegStore as _EB
    e = kunden_store.bh.eintraege()
    belege = []
    for x in _eb.EingangStore._falte(e).values():
        fe = x.get("felder") or {}
        if fe.get("lieferant_firma") == nummer:
            belege.append({"nummer": x["nummer"], "datum": fe.get("rechnungsdatum", ""), "betrag_cent": fe.get("betrag_cent", 0),
                           "art": fe.get("art", "ausgabe"), "text": fe.get("leistung") or fe.get("rechnungsnummer") or "",
                           "status": "bezahlt" if x.get("bezahlt_am") else x["status"], "quelle": "beleg"})
    for x in _EB._falte(e).values():
        if x.get("firma") == nummer:
            belege.append({"nummer": x["nummer"], "datum": x["datum"], "betrag_cent": x["betrag_cent"], "art": x["art"],
                           "text": x["text"], "status": x["status"], "quelle": "eigenbeleg"})
    belege.sort(key=lambda b: (b["datum"], b["nummer"]), reverse=True)
    zeilen = _finanzen().journal(firma=nummer)
    je_jahr: dict = {}
    for z in zeilen:
        if z["storniert"]:
            continue
        j = je_jahr.setdefault(str(z["jahr"]), {"einnahmen_cent": 0, "ausgaben_cent": 0})
        j["einnahmen_cent" if z["art"] == "einnahme" else "ausgaben_cent"] += z["betrag_cent"]
    return {"belege": belege, "je_jahr": dict(sorted(je_jahr.items(), reverse=True)), "abo": _abo(belege)}


def _abo(belege: list[dict]) -> dict:
    """Abo erkennen: in mind. 2 verschiedenen Monaten der letzten 4 ein aehnlicher Betrag (±25 %) derselben Art."""
    heute = jetzt_iso()[:7]
    j, m = int(heute[:4]), int(heute[5:7])
    fenster = {f"{j - (m - i <= 0)}-{(m - i - 1) % 12 + 1:02d}" for i in range(4)}
    je_monat: dict = {}
    for b in belege:
        if b["status"] in ("storniert", "verworfen") or str(b["datum"])[:7] not in fenster:
            continue
        je_monat.setdefault(str(b["datum"])[:7], []).append(abs(int(b["betrag_cent"] or 0)))
    betraege = sorted(c for werte in je_monat.values() for c in werte if c)
    if len(je_monat) < 2 or not betraege:
        return {}
    mitte = betraege[len(betraege) // 2]
    passend = {mon for mon, werte in je_monat.items() if any(abs(c - mitte) <= 0.25 * mitte for c in werte)}
    return {"monatlich_cent": mitte, "monate": sorted(passend)} if len(passend) >= 2 else {}


@app.post("/api/crm/kunden")
async def kunden_anlegen(request: Request):
    body = await _json(request)
    collab = (body.get("collab") or "").strip()

    def tun():
        r = kunden_store.firma_anlegen(body.get("firma") or {}, von=_von(request),
                                       trotz_dublette=bool(body.get("trotz_dublette")))
        if collab:
            kunden_store.collab_zuordnen(r["nummer"], collab, von=_von(request))
        return r
    return _kunden_aktion(tun)


@app.post("/api/crm/kunden/{nummer}")
async def kunden_aendern(nummer: str, request: Request):
    body = await _json(request)
    def tun():
        r = kunden_store.firma_aendern(nummer, body.get("firma") or {}, von=_von(request))
        if "typ" in (r.get("geaendert") or {}):              # neue Rolle -> Nummer im passenden Kreis (Etappe 14)
            r["rollennummer"] = kunden_store.rollennummer_sichern(nummer, von=_von(request))
        return r
    return _kunden_aktion(tun)


@app.post("/api/crm/kunden/{nummer}/ansprechpartner")
async def kunden_ap_anlegen(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: kunden_store.ansprechpartner_anlegen(nummer, body.get("ansprechpartner") or {},
                                                                        von=_von(request)))


@app.post("/api/crm/ansprechpartner/{nummer}")
async def kunden_ap_aendern(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: kunden_store.ansprechpartner_aendern(nummer, body.get("ansprechpartner") or {},
                                                                        von=_von(request)))


@app.post("/api/crm/kunden/{nummer}/collab")
async def kunden_collab(nummer: str, request: Request):
    """Collab-Firma zuordnen ({"collab": name}) oder loesen ({"collab": name, "loesen": true})."""
    body = await _json(request)
    fn = kunden_store.collab_loesen if body.get("loesen") else kunden_store.collab_zuordnen
    return _kunden_aktion(lambda: fn(nummer, body.get("collab") or "", von=_von(request)))


# -- Angebote (KUNDEN_FINANZEN Etappe 3; Modul crm) ----------------------------------------------------------------

def _angebote() -> AngebotStore:
    return AngebotStore(kunden_store.bh, kunden_store, Katalog(kunden_store.bh))


# -- Beauftragung / Auftragsbestaetigung (KUNDEN_FINANZEN Etappe 4; Modul crm) -----------------------------------

def _auftraege() -> AuftragBuch:
    return AuftragBuch(kunden_store.bh, kunden_store, _angebote())


def heimadresse(fd: dict) -> str:
    return " ".join(x for x in (fd.get("strasse"), fd.get("plz"), fd.get("ort")) if x)


def _zeit():
    """Etappe 25: Zeiterfassung (nur intern) -- Start der Fahrten ist die Firmenadresse aus den Firmendaten."""
    from ...core.routen import Routen
    from ...core.zeiterfassung import Zeiterfassung
    return Zeiterfassung(kunden_store.bh, kunden_store, auftraege=_auftraege(),
                         routen=Routen(kunden_store.bh.dir / "geocache.json"), heimadresse=heimadresse(_firmendaten()))


@app.get("/api/finanzen/zeit")
def zeit_liste(auftrag: str = ""):
    """Zeiten + Nachkalkulation eines Auftrags (Modul finanzen, nur intern)."""
    z = _zeit()
    out = {"laufend": z.laufend(), "einstellungen": {k: v for k, v in z.einstellungen().items() if k != "monatsbrutto_cent"}}
    if auftrag:
        a = _auftraege().auftrag(auftrag)
        if not a:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannter Auftrag")
        out |= {"eintraege": z.fuer_auftrag(a["nummer"]), "nachkalkulation": z.nachkalkulation(a)}
    return out


@app.get("/api/finanzen/zeit/einstellungen")
def zeit_einstellungen():
    return _zeit().einstellungen()


@app.post("/api/finanzen/zeit/einstellungen")
async def zeit_einstellungen_setzen(request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _zeit().einstellen(body.get("monatsbrutto"), body.get("wochenstunden"), von=_von(request)))


@app.post("/api/finanzen/zeit/start")
async def zeit_start(request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _zeit().starten(auftrag=body.get("auftrag") or "", firma=body.get("firma") or "",
                                                  adresse=body.get("adresse") or "", von=_von(request)))


@app.post("/api/finanzen/zeit/stopp")
async def zeit_stopp(request: Request):
    return _kunden_aktion(lambda: _zeit().stoppen(von=_von(request)))


@app.post("/api/finanzen/zeit/eintrag")
async def zeit_eintrag(request: Request):
    body = await _json(request)

    def tun():
        z = _zeit()
        r = z.eintragen(auftrag=body.get("auftrag") or "", firma=body.get("firma") or "", datum=body.get("datum") or "",
                        von_uhr=body.get("von") or "", bis_uhr=body.get("bis") or "", minuten=body.get("minuten"),
                        notiz=body.get("notiz") or "", adresse=body.get("adresse") or "", von=_von(request))
        if body.get("km") not in (None, "") or body.get("km_berechnen"):
            r["fahrt"] = z.fahrt_buchen(r["id"], km=body.get("km"), adresse=body.get("adresse") or "", von=_von(request))
        return r
    return _kunden_aktion(tun)


@app.get("/api/finanzen/zeit/{zid}/km")
def zeit_km(zid: str, adresse: str = ""):
    try:
        return _zeit().km_vorschlag(zid, adresse)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannter Zeiteintrag") from None


@app.post("/api/finanzen/zeit/{zid}/fahrt")
async def zeit_fahrt(zid: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _zeit().fahrt_buchen(zid, km=body.get("km"), adresse=body.get("adresse") or "",
                                                       von=_von(request)))


@app.post("/api/finanzen/zeit/{zid}/zuordnen")
async def zeit_zuordnen(zid: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _zeit().zuordnen(zid, body.get("auftrag") or "", von=_von(request)))


@app.post("/api/finanzen/zeit/{zid}/stornieren")
async def zeit_stornieren(zid: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _zeit().stornieren(zid, body.get("grund") or "", von=_von(request)))


@app.get("/api/crm/auftraege")
def auftraege_liste():
    return {"auftraege": _auftraege().liste()}


@app.get("/api/crm/auftraege/{nummer}")
def auftrag_detail(nummer: str):
    a = _auftraege().auftrag(nummer)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Auftragsnummer")
    f = kunden_store.firma(a["firma"]) or {}
    ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
    from ...core import zahlungsbedingungen as zb
    entwuerfe, rechnungen = _rechnungen()._stand()                       # Etappe 18: Vorkasse-/Schlussrechnung zeigen
    re = [{k: r.get(k) for k in ("nummer", "art", "status", "faellig_am", "summe_cent")}
          for r in sorted(rechnungen.values(), key=lambda r: r["nummer"]) if r.get("auftrag") == a["nummer"]]
    re += [{"nummer": eid, "art": x.get("art") or "rechnung", "status": "entwurf"}
           for eid, x in entwuerfe.items() if x.get("auftrag") == a["nummer"]]
    return {"auftrag": a, "firma": {k: f.get(k) for k in ("nummer", "name", "rechnungsmail")}, "ansprechpartner": ap,
            "mail_an": (ap or {}).get("mail") or f.get("rechnungsmail") or "", "google": bool(_google().verfuegbar()),
            "firmendaten": bool(_firmendaten()), "rechnungen": re,
            "zahlung_text": zb.text(a.get("zahlung"), a["geld_cent"], ab_datum=a["datum"])}


@app.post("/api/crm/angebote/{nummer}/auftrag")
async def auftrag_aus_angebot(nummer: str, request: Request):
    """Auftrag AB- aus einem angenommenen Angebot; mit {"annehmen": true} wird ein versendetes Angebot vorher angenommen."""
    body = await _json(request)
    st = _angebote()

    def tun():
        a = st.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if body.get("annehmen") and a["status"] == "versendet":
            st.status_setzen(a["nummer"], "angenommen", grund=body.get("grund") or "Auftrag angelegt", von=_von(request))
        r = _auftraege().aus_angebot(a["nummer"], leistung_von=body.get("leistung_von") or "",
                                    leistung_bis=body.get("leistung_bis") or "", notiz=body.get("notiz") or "",
                                    von=_von(request))
        hinweise = []
        for c in (kunden_store.firma(a["firma"]) or {}).get("collab", []):      # CRM-Stufe „vereinbart“
            anzeige = next((f.get("firma") for f in crm_store.firmen() if (f.get("firma") or "").strip().lower() == c), c)
            try:
                crm_store.status_setzen(anzeige, "vereinbart")
            except Exception:
                hinweise.append(f"CRM-Stufe fuer {anzeige} nicht gesetzt.")
        return r | {"hinweise": hinweise}
    return _kunden_aktion(_mit_aufraeumen(tun, _von(request)))


@app.post("/api/crm/auftraege/{nummer}")
async def auftrag_aendern(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _auftraege().aendern(nummer, body.get("auftrag") or {}, von=_von(request)))


@app.post("/api/crm/auftraege/{nummer}/status")
async def auftrag_status(nummer: str, request: Request):
    body = await _json(request)
    ziel = (body.get("status") or "").strip()
    if ziel not in ("erledigt", "storniert"):
        return {"ok": False, "hinweis": "Status muss erledigt oder storniert sein."}
    return _kunden_aktion(lambda: _auftraege().status_setzen(nummer, ziel, grund=body.get("grund") or "",
                                                             von=_von(request)))


@app.get("/api/crm/auftraege/{nummer}/pdf")
def auftrag_pdf(nummer: str, archiv: int = 0):
    ab = _auftraege()
    a = ab.auftrag(nummer)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Auftragsnummer")
    if archiv:
        if not a["pdfs"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "noch kein PDF abgelegt")
        daten = (kunden_store.bh.dir / a["pdfs"][-1]["pfad"]).read_bytes()
    else:
        fd = _firmendaten()
        if not fd:
            raise HTTPException(status.HTTP_409_CONFLICT, "Firmendaten fehlen (buchhaltung/firmendaten.json)")
        daten = ab.pdf(a["nummer"], fd)
    return Response(daten, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Auftragsbestaetigung_{a["nummer"]}.pdf"'})


@app.get("/api/crm/auftraege/{nummer}/versandvorschau")
def auftrag_versandvorschau(nummer: str):
    d = auftrag_detail(nummer)
    betreff, text = auftrag_mail_text(d["auftrag"], d["ansprechpartner"], _firmendaten())
    konto = (_google_secrets().get("GOOGLE_ACCOUNT_EMAIL") or "").strip()
    return {"an": d["mail_an"], "betreff": betreff, "text": text, "pdf": f"Auftragsbestaetigung_{d['auftrag']['nummer']}.pdf",
            "absender": f"{ABSENDER_NAME} <{konto}>" if konto else ABSENDER_NAME, "google": d["google"]}


@app.post("/api/crm/auftraege/{nummer}/senden")
async def auftrag_senden(nummer: str, request: Request):
    """Auftragsbestaetigung aus LUNAs Konto senden -- wie Angebote: nur CEO (Modul finanzen), nur mit Bestaetigung."""
    u = getattr(request.state, "user", None) or _ceo_user()
    if not hat_modul(u, "finanzen"):
        return {"ok": False, "hinweis": "Auftragsbestaetigungen senden darf nur der CEO (Modul Finanzen)."}
    body = await _json(request)
    ab = _auftraege()

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Senden braucht die ausdrueckliche Bestaetigung aus der Vorschau.")
        a = ab.auftrag(nummer)
        if not a:
            raise KeyError(nummer)
        if a["status"] == "storniert":
            raise ValueError(f"{a['nummer']} ist storniert.")
        an = (body.get("an") or "").strip()
        betreff, text = (body.get("betreff") or "").strip(), (body.get("text") or "").strip()
        if not an or "@" not in an or not betreff or not text:
            raise ValueError("Empfaenger, Betreff und Text sind Pflicht.")
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen (buchhaltung/firmendaten.json auf der NAS).")
        g = _google()
        if not g.verfuegbar():
            raise ValueError("Google ist nicht verbunden -- Senden nicht moeglich.")
        pdf = ab.pdf(a["nummer"], fd)
        r = g.mail_senden(an, betreff, text, bestaetigt=True, absender_name=ABSENDER_NAME,
                          anhaenge=[(f"Auftragsbestaetigung_{a['nummer']}.pdf", pdf, "application/pdf")])
        if not r.get("ok"):
            raise ValueError(r.get("hinweis") or "Senden fehlgeschlagen.")
        ab.pdf_ablegen(a["nummer"], pdf, an=an, von=_von(request))
        ab.status_setzen(a["nummer"], "gesendet", mail={"an": an, "message_id": r.get("id", ""),
                                                        "thread_id": r.get("thread_id", ""), "betreff": betreff},
                         von=_von(request))
        roh = g.mail_roh(r["id"]) if r.get("id") else {}
        if roh.get("ok"):                                          # Original-Mail als Geschaeftsbrief archivieren
            kunden_store.bh.beleg_ablegen(roh["roh"], f"Mail_{a['nummer']}_aus_{r['id']}.eml", jahr=int(a["datum"][:4]),
                                          art="geschaeftsbrief", bezug=a["nummer"], von=_von(request))
        return {"an": an}
    return _kunden_aktion(tun)


# -- Ausgangsrechnungen (KUNDEN_FINANZEN Etappe 5; Modul finanzen ueber den Pfad /api/finanzen) -----------------

def _rechnungen() -> RechnungStore:
    return RechnungStore(kunden_store.bh, kunden_store, Katalog(kunden_store.bh))


@app.get("/api/finanzen/rechnungen")
def rechnungen_liste(jahr: int = 0):
    return _rechnungen().uebersicht(jahr or None)


@app.get("/api/finanzen/rechnungen/{kennung}")
def rechnung_detail(kennung: str):
    r = _rechnungen().get(kennung)
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Rechnung/Entwurf")
    f = kunden_store.firma(r["firma"]) or {}
    ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == r.get("ansprechpartner")), None)
    from ...core.mahnungen import MahnStore
    ms = MahnStore(kunden_store.bh, kunden_store)
    mahn = [{k: m.get(k) for k in ("nummer", "stufe", "datum", "frist", "summe_cent", "versendet_am", "mail")}
            for m in ms.fuer_rechnung(r.get("nummer", ""))] if r.get("nummer") else []
    try:
        naechste = ms.berechnen(r["nummer"]) if r.get("nummer") else None
        mahnbar = ""
    except (ValueError, KeyError) as exc:
        naechste, mahnbar = None, str(exc)
    from ...core.firmenakte import Firmenakte
    doks = [{k: x.get(k) for k in ("id", "titel", "art", "datum", "notiz")}
            for x in Firmenakte(kunden_store.bh, kunden_store).zu_bezug(r.get("nummer", ""))] if r.get("nummer") else []
    return {"rechnung": r, "firma": {k: f.get(k) for k in ("nummer", "name", "rechnungsmail", "verbraucher")}, "dokumente": doks,
            "ansprechpartner": ap, "mail_an": f.get("rechnungsmail") or (ap or {}).get("mail") or "",
            "google": bool(_google().verfuegbar()), "firmendaten": bool(_firmendaten()),
            "steuernummer": bool(_firmendaten().get("steuernummer")), "mahnungen": mahn,
            "naechste_mahnung": naechste, "nicht_mahnbar": mahnbar}


@app.post("/api/finanzen/rechnungen")
async def rechnung_entwurf_neu(request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _rechnungen().entwurf_anlegen(body.get("rechnung") or {}, von=_von(request)))


def _datei_b64(d) -> tuple[bytes, str]:
    import base64 as _b64
    d = d or {}
    return (_b64.b64decode(str(d.get("daten") or ""), validate=True) if d.get("daten") else b""), str(d.get("name") or "")


@app.post("/api/finanzen/rechnungen/alt")
async def rechnung_alt(request: Request):
    """Etappe 19: Rechnung von vor LUNA mit Originalnummer + Original-PDF uebernehmen."""
    body = await _json(request)

    def tun():
        pdf, name = _datei_b64(body.get("datei"))
        return _rechnungen().alt_erfassen(body.get("rechnung") or {}, pdf, name, von=_von(request))
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/{nummer}/altmahnung")
async def rechnung_altmahnung(nummer: str, request: Request):
    """Etappe 19: vor LUNA verschickte Mahnung als erreichte Stufe erfassen (optional mit PDF)."""
    body = await _json(request)

    def tun():
        pdf, name = _datei_b64(body.get("datei"))
        return _mahn().alt_erfassen(nummer, datum=body.get("datum") or "", frist=body.get("frist") or "",
                                    summe=body.get("summe"), pdf=pdf or None, dateiname=name, von=_von(request))
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/aus-auftrag/{nummer}")
async def rechnung_aus_auftrag(nummer: str, request: Request):
    """Rechnungsentwurf aus dem Auftrag; `{"vorkasse": true}` = Vorkasse-Rechnung (Etappe 18)."""
    body = await _json(request)

    def tun():
        a = _auftraege().auftrag(nummer)
        if not a:
            raise KeyError(nummer)
        return _rechnungen().entwurf_aus_auftrag(a, vorkasse=bool(body.get("vorkasse")), von=_von(request))
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/{eid}")
async def rechnung_entwurf_aendern(eid: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _rechnungen().entwurf_aendern(eid, body.get("rechnung") or {}, von=_von(request)))


@app.post("/api/finanzen/rechnungen/{eid}/verwerfen")
async def rechnung_entwurf_verwerfen(eid: str, request: Request):
    return _kunden_aktion(lambda: _rechnungen().entwurf_verwerfen(eid, von=_von(request)))


@app.get("/api/finanzen/rechnungen/{kennung}/pdf")
def rechnung_pdf(kennung: str):
    rs = _rechnungen()
    r = rs.get(kennung)
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Rechnung/Entwurf")
    if r.get("status") == "entwurf":
        fd = _firmendaten()
        if not fd:
            raise HTTPException(status.HTTP_409_CONFLICT, "Firmendaten fehlen")
        daten, name = rs.vorschau_pdf(kennung, fd), f"Rechnung_Entwurf_{kennung}.pdf"
    else:
        daten = (kunden_store.bh.dir / r["belege"][0]["pfad"]).read_bytes()        # das festgeschriebene Original
        name = Path(r["belege"][0]["pfad"]).name.split("-", 1)[-1]
    return Response(daten, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})


@app.post("/api/finanzen/rechnungen/{eid}/festschreiben")
async def rechnung_festschreiben(eid: str, request: Request):
    """Nummer + PDF + unveraenderlicher Eintrag; danach Kalender-Erinnerung zur Faelligkeit (LUNAs Kalender)."""
    body = await _json(request)
    rs = _rechnungen()

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Festschreiben braucht die ausdrueckliche Bestaetigung (danach nicht mehr aenderbar).")
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen (buchhaltung/firmendaten.json auf der NAS).")
        r = rs.festschreiben(eid, fd, von=_von(request))
        hinweise = []
        if r.get("warnung"):
            w = r["waechter"]
            hinweise.append(f"Kleinunternehmer-Grenze: {round(w['anteil'] * 100)} % von 100.000 € erreicht.")
        g = _google()
        if g.verfuegbar():
            x = rs.get(r["nummer"])
            name = (kunden_store.firma(x["firma"]) or {}).get("name", x["firma"])
            art = "Vorkasse" if x.get("art") == "anzahlung" else "Rechnung"      # Etappe 18: Payment-Check
            t = g.termin_anlegen(f"💶 Payment-Check: {art} {r['nummer']} ({eur_text(x['summe_cent'])}) – {name}",
                                 f"{r['faellig_am']}T09:00:00", f"{r['faellig_am']}T09:15:00",
                                 beschreibung=(f"{r['nummer']} · {eur_text(x['summe_cent'])}"
                                               + (f" · Auftrag {x['auftrag']}" if x.get("auftrag") else "")
                                               + "\nIst das Geld da? In LUNA-OS die Zahlung erfassen -- dann löscht LUNA "
                                                 "diesen Termin."),
                                 bestaetigt=True)
            if t.get("ok"):
                rs.erinnerung_merken(r["nummer"], {"datum": r["faellig_am"], "id": t.get("termin_id", "")}, von=_von(request))
            else:
                hinweise.append(f"Kalender: {t.get('hinweis') or 'Fehler'}")
        return {"nummer": r["nummer"], "faellig_am": r["faellig_am"], "hinweise": hinweise}
    return _kunden_aktion(tun)


def eur_text(c: int) -> str:
    from ...core.beleg_pdf import eur
    return eur(c)


@app.get("/api/finanzen/rechnungen/{nummer}/versandvorschau")
def rechnung_versandvorschau(nummer: str):
    d = rechnung_detail(nummer)
    r = d["rechnung"]
    if r.get("status") == "entwurf":
        raise HTTPException(status.HTTP_409_CONFLICT, "Erst festschreiben, dann senden.")
    betreff, text = rechnung_mail_text(r, d["ansprechpartner"], _firmendaten())
    konto = (_google_secrets().get("GOOGLE_ACCOUNT_EMAIL") or "").strip()
    return {"an": d["mail_an"], "betreff": betreff, "text": text, "pdf": Path(r["belege"][0]["pfad"]).name.split("-", 1)[-1],
            "absender": f"{ABSENDER_NAME} <{konto}>" if konto else ABSENDER_NAME, "google": d["google"]}


@app.post("/api/finanzen/rechnungen/{nummer}/senden")
async def rechnung_senden(nummer: str, request: Request):
    """Festgeschriebene Rechnung (genau das archivierte PDF) aus LUNAs Konto senden -- nur mit Bestaetigung."""
    body = await _json(request)
    rs = _rechnungen()

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Senden braucht die ausdrueckliche Bestaetigung aus der Vorschau.")
        r = rs.get(nummer)
        if not r or r.get("status") == "entwurf":
            raise KeyError(nummer)
        an = (body.get("an") or "").strip()
        betreff, text = (body.get("betreff") or "").strip(), (body.get("text") or "").strip()
        if not an or "@" not in an or not betreff or not text:
            raise ValueError("Empfaenger, Betreff und Text sind Pflicht.")
        g = _google()
        if not g.verfuegbar():
            raise ValueError("Google ist nicht verbunden -- Senden nicht moeglich.")
        pfad = r["belege"][0]["pfad"]
        pdf = (kunden_store.bh.dir / pfad).read_bytes()
        s = g.mail_senden(an, betreff, text, bestaetigt=True, absender_name=ABSENDER_NAME,
                          anhaenge=[(Path(pfad).name.split("-", 1)[-1], pdf, "application/pdf")])
        if not s.get("ok"):
            raise ValueError(s.get("hinweis") or "Senden fehlgeschlagen.")
        rs.versendet(r["nummer"], {"an": an, "message_id": s.get("id", ""), "thread_id": s.get("thread_id", ""),
                                   "betreff": betreff}, von=_von(request))
        roh = g.mail_roh(s["id"]) if s.get("id") else {}
        if roh.get("ok"):
            kunden_store.bh.beleg_ablegen(roh["roh"], f"Mail_{r['nummer']}_aus_{s['id']}.eml",
                                          jahr=int(r["rechnungsdatum"][:4]), art="geschaeftsbrief", bezug=r["nummer"],
                                          von=_von(request))
        return {"an": an}
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/{nummer}/ware-erhalten")
async def rechnung_ware_erhalten(nummer: str, request: Request):
    """Etappe 12 (Barter): Ware als Gegenleistung erhalten -- Wert (Marke/eigener Nachweis), Verwendung, Nachweis-Dateien."""
    import base64 as _b64
    body = await _json(request)

    def tun():
        nachweise = []
        for d in (body.get("nachweise") or [])[:5]:
            try:
                nachweise.append((_b64.b64decode(str(d.get("daten") or ""), validate=True), str(d.get("name") or "nachweis")))
            except (ValueError, TypeError):
                raise ValueError("Nachweis-Datei ungueltig.") from None
        return _rechnungen().ware_erhalten(
            nummer, datum=body.get("datum") or "", text=body.get("text") or "", wert_marke=body.get("wert_marke"),
            wert_nachweis=body.get("wert_nachweis"), verwendung=body.get("verwendung") or "content",
            kategorie=body.get("kategorie") or "", nutzungsdauer_jahre=body.get("nutzungsdauer_jahre"),
            nachweise=nachweise, von=_von(request))
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/{nummer}/ware-stornieren")
async def rechnung_ware_stornieren(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _rechnungen().ware_stornieren(nummer, body.get("grund") or "", von=_von(request)))


# -- Mahnungen (KUNDEN_FINANZEN Etappe 10; Modul finanzen) -------------------------------------------------------

def _mahn():
    from ...core.mahnungen import MahnStore
    return MahnStore(kunden_store.bh, kunden_store)


@app.get("/api/finanzen/rechnungen/{nummer}/mahnung-vorschau")
def mahnung_vorschau(nummer: str, frist_tage: int = 7):
    return _kunden_aktion(lambda: _mahn().berechnen(nummer, frist_tage=frist_tage))


@app.post("/api/finanzen/rechnungen/{nummer}/mahnung")
async def mahnung_erstellen(nummer: str, request: Request):
    """Mahnung festschreiben (Nummer MA-, PDF). Versand danach getrennt mit Vorschau."""
    body = await _json(request)

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Mahnung erstellen braucht die Bestaetigung aus der Vorschau.")
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen.")
        return _mahn().erstellen(nummer, fd, frist_tage=int(body.get("frist_tage") or 7), von=_von(request))
    return _kunden_aktion(tun)


@app.get("/api/finanzen/mahnungen/{nummer}/pdf")
def mahnung_pdf(nummer: str):
    m = _mahn().get(nummer)
    if not m or not m.get("belege"):                    # Mahnung vor LUNA ohne PDF (Etappe 19)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Mahnung bzw. kein PDF hinterlegt")
    return Response((kunden_store.bh.dir / m["belege"][0]["pfad"]).read_bytes(), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Mahnung_{m["nummer"]}.pdf"'})


@app.get("/api/finanzen/mahnungen/{nummer}/versandvorschau")
def mahnung_versandvorschau(nummer: str):
    from ...core.mahnungen import empfaenger, mahnung_mail_text
    m = _mahn().get(nummer)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Mahnung")
    an, ap = empfaenger(kunden_store, m["firma"])
    betreff, text = mahnung_mail_text(m, ap, _firmendaten())
    konto = (_google_secrets().get("GOOGLE_ACCOUNT_EMAIL") or "").strip()
    return {"an": an, "betreff": betreff, "text": text, "pdf": f"Mahnung_{m['nummer']}.pdf",
            "absender": f"{ABSENDER_NAME} <{konto}>" if konto else ABSENDER_NAME, "google": bool(_google().verfuegbar())}


@app.post("/api/finanzen/mahnungen/{nummer}/senden")
async def mahnung_senden(nummer: str, request: Request):
    from ...core.mahnungen import senden
    body = await _json(request)

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Senden braucht die ausdrueckliche Bestaetigung aus der Vorschau.")
        return senden(_mahn(), _google(), nummer, an=(body.get("an") or "").strip(),
                      betreff=(body.get("betreff") or "").strip(), text=(body.get("text") or "").strip(),
                      von=_von(request), absender_name=ABSENDER_NAME)
    return _kunden_aktion(tun)


@app.post("/api/finanzen/rechnungen/{nummer}/bezahlt")
async def rechnung_bezahlt(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(_mit_aufraeumen(
        lambda: _rechnungen().bezahlt(nummer, datum=body.get("datum") or "", betrag=body.get("betrag"),
                                      notiz=body.get("notiz") or "", zuordnung_jahr=body.get("zuordnung_jahr"),
                                      nebenforderung=body.get("nebenforderung"), von=_von(request)), _von(request)))


@app.post("/api/finanzen/rechnungen/{nummer}/zahlung-stornieren")
async def rechnung_zahlung_stornieren(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _rechnungen().zahlung_stornieren(nummer, _index(body), body.get("grund") or "",
                                                                   von=_von(request)))


@app.post("/api/finanzen/rechnungen/{nummer}/stornieren")
async def rechnung_stornieren(nummer: str, request: Request):
    body = await _json(request)

    def tun():
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen.")
        return _rechnungen().stornieren(nummer, fd, grund=body.get("grund") or "", korrektur=bool(body.get("korrektur")),
                                        von=_von(request))
    return _kunden_aktion(_mit_aufraeumen(tun, _von(request)))


# -- Eingangsrechnungen / Belege (KUNDEN_FINANZEN Etappe 6; Modul finanzen) ---------------------------------------

def _eingang() -> _eb.EingangStore:
    return _eb.EingangStore(kunden_store.bh)


def _lieferanten() -> list[dict]:
    """Auswahl fuer Belege: aktive Lieferanten/Partner (und Kunden) mit Anzeigenummer (Etappe 14)."""
    reihe = {"lieferant": 0, "partner": 1, "kunde": 2}
    return sorted(({"nummer": f["nummer"], "anzeige": f["anzeige"], "name": f["name"], "typ": f.get("typ") or "kunde"}
                   for f in kunden_store.firmen() if f["aktiv"]), key=lambda x: (reihe.get(x["typ"], 3), x["name"].lower()))


def _firma_vorschlag(felder: dict, vorschlag: dict) -> dict:
    nr = (felder or {}).get("lieferant_firma") or kunden_store.finde(
        (felder or {}).get("lieferant") or vorschlag.get("lieferant") or "", vorschlag.get("absender") or "")
    f = kunden_store.firma(nr) if nr else None
    return {"nummer": f["nummer"], "anzeige": f["anzeige"], "name": f["name"]} if f else {}


def _firma_fuer_beleg(firma: str, name: str, art: str, absender: str, von: str) -> str:
    """Stammdaten-Nummer fuer eine Buchung: gewaehlte Firma (jede ihrer Nummern) oder finden/anlegen (Etappe 14)."""
    if firma:
        f = kunden_store.firma(firma)
        if not f:
            raise ValueError(f"Unbekannte Stammdaten-Nummer: {firma}")
        if f.get("typ") != "kunde":
            kunden_store.rollennummer_sichern(f["nummer"], von=von)
        kunden_store.absender_lernen(f["nummer"], absender, von=von)
        return f["nummer"]
    return kunden_store.zuordnen(name, art=art, absender=absender, von=von)


@app.get("/api/finanzen/belege")
def belege_liste():
    st = _eingang()
    _eb.llm_ergebnisse_uebernehmen(st, backoffice)
    return {"belege": st.liste(), "kategorien": {k: v[0] for k, v in _eb.KATEGORIEN.items()},
            "kategorien_einnahme": _eb.EINNAHME_KATEGORIEN}


@app.get("/api/finanzen/belege/{nummer}")
def beleg_detail(nummer: str):
    st = _eingang()
    _eb.llm_ergebnisse_uebernehmen(st, backoffice)
    x = st.get(nummer)
    if not x:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannter Beleg")
    llm = backoffice.get(x["llm_auftrag"]) if x.get("llm_auftrag") else None
    return {"beleg": {k: v for k, v in x.items() if k != "text"} | {"text": (x.get("text") or "")[:4000]},
            "kategorien": {k: v[0] for k, v in _eb.KATEGORIEN.items()}, "kategorien_einnahme": _eb.EINNAHME_KATEGORIEN,
            "lieferanten": _lieferanten(), "firma_vorschlag": _firma_vorschlag(x.get("felder") or {}, x.get("vorschlag") or {}),
            "ki_status": (llm or {}).get("status", "")}


@app.get("/api/finanzen/belege/{nummer}/datei")
def beleg_datei(nummer: str, i: int = 0):
    """Datei eines Belegs; i > 0 = weitere Dateien (Original-Mail .eml, Zahlungsnachweis)."""
    x = _eingang().get(nummer)
    if not x or not 0 <= i < len(x.get("belege") or []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannter Beleg")
    b = x["belege"][i]
    name = x["dateiname"] if i == 0 else (b.get("name") or Path(b["pfad"]).name[17:] or "datei")
    endung = Path(name).suffix.lower()
    mime = (x.get("mime") if i == 0 else None) or _eb.ENDUNGEN.get(endung) or (
        "message/rfc822" if endung == ".eml" else "application/octet-stream")
    art = "attachment" if endung == ".eml" else "inline"
    import re as _re
    sicher = _re.sub(r'["\\\r\n?]', "_", name.encode("ascii", "replace").decode())   # Kopfzeile nur ASCII
    kopf = {"Content-Disposition": f'{art}; filename="{sicher}"', "X-Content-Type-Options": "nosniff"}
    if mime != "application/pdf":                  # Chrome zeigt PDFs in einer Sandbox nicht an; XML/Bilder abschotten
        kopf["Content-Security-Policy"] = "sandbox"
    return Response((kunden_store.bh.dir / b["pfad"]).read_bytes(), media_type=mime, headers=kopf)


@app.post("/api/finanzen/belege/hochladen")
async def belege_hochladen(request: Request):
    """Dateien als Base64 im JSON (kein Multipart noetig); je Datei auslesen, ablegen, KI-Vorschlag anfordern."""
    import base64 as _b64
    body = await _json(request)
    dateien = body.get("dateien") or []
    if not isinstance(dateien, list) or not dateien or len(dateien) > 10:
        return {"ok": False, "hinweis": "1 bis 10 Dateien je Upload."}
    st, ergebnisse = _eingang(), []
    for d in dateien:
        name = str((d or {}).get("name") or "beleg")
        try:
            daten = _b64.b64decode(str(d.get("daten") or ""), validate=True)
            rs = _eb.datei_importieren(st, daten, name, von=_von(request))     # auch .eml/.mbox (Beleg-Import)
            if not rs:
                ergebnisse.append({"name": name, "ok": False, "hinweis": "Keine Rechnung in der Mail erkannt."})
            for r in rs:
                if not r.get("doppelt"):
                    _eb.llm_beauftragen(st, backoffice, r["nummer"])
                ergebnisse.append({"name": name, "ok": True} | {k: r.get(k) for k in ("nummer", "doppelt", "text_quelle")})
        except (ValueError, TypeError) as exc:
            ergebnisse.append({"name": name, "ok": False, "hinweis": str(exc)[:200]})
    try:                                                    # Etappe 20: Euro-Betrag zum EZB-Kurs vorschlagen
        from ...core.wechselkurse import EzbKurse, kurse_ergaenzen
        kurse_ergaenzen(st, EzbKurse(kunden_store.bh.dir / "wechselkurse.json"))
    except Exception:
        pass
    try:                                                    # Fremdwaehrung -> Kalender „Euro-Betrag eintragen“
        _eb.fremdwaehrung_erinnern(st, _google())
    except Exception:
        pass
    return {"ok": any(e["ok"] for e in ergebnisse), "ergebnisse": ergebnisse}


@app.post("/api/finanzen/belege/{nummer}/zweck")
async def beleg_zweck(nummer: str, request: Request):
    """Begruendung/Zweck des Kaufs nachtragen oder aendern (betriebliche Veranlassung, CEO 2026-09-30)."""
    body = await _json(request)
    return _kunden_aktion(lambda: _eingang().zweck_setzen(nummer, body.get("zweck") or "", von=_von(request)))


@app.post("/api/finanzen/belege/{nummer}/buchen")
async def beleg_buchen(nummer: str, request: Request):
    body = await _json(request)

    def tun():
        felder = dict(body.get("felder") or {})
        st = _eingang()
        x = st.get(nummer)
        if not x:
            raise KeyError(nummer)
        if not str(felder.get("lieferant") or "").strip():
            raise ValueError("Lieferant fehlt.")
        # Etappe 14: jeder Beleg haengt an einer Stammdaten-Nummer (gewaehlt, gefunden oder neu angelegt)
        felder["lieferant_firma"] = _firma_fuer_beleg(felder.get("lieferant_firma") or "", felder.get("lieferant") or "",
                                                      felder.get("art") or "ausgabe",
                                                      (x.get("vorschlag") or {}).get("absender") or "", _von(request))
        return st.buchen(nummer, felder, von=_von(request))
    return _kunden_aktion(_mit_aufraeumen(tun, _von(request)))


@app.post("/api/finanzen/belege/{nummer}/bezahlt")
async def beleg_bezahlt(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _eingang().bezahlt(nummer, body.get("datum") or "", betrag=body.get("betrag"),
                                                     zuordnung_jahr=body.get("zuordnung_jahr"),
                                                     notiz=body.get("notiz") or "", von=_von(request)))


@app.post("/api/finanzen/belege/{nummer}/zahlung-stornieren")
async def beleg_zahlung_stornieren(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _eingang().zahlung_stornieren(nummer, _index(body), body.get("grund") or "",
                                                                von=_von(request)))


def _index(body: dict) -> int:
    try:
        return int(body.get("index"))
    except (TypeError, ValueError):
        raise ValueError("Zahlung fehlt.") from None


# -- To-dos fuer die Hauptseite (CEO 2026-09-28): Tagesbetrieb gesammelt; Antraege/Freigaben bewusst NICHT hier ------

@app.get("/api/todos")
def todos_liste(request: Request):
    from ...core.todos import geschaefts_todos
    u = getattr(request.state, "user", None) or _ceo_user()
    out = geschaefts_todos(kunden_store.bh, kunden_store, finanzen=hat_modul(u, "finanzen"), crm=hat_modul(u, "crm"))
    heute = jetzt_iso()[:10]
    if hat_modul(u, "crm"):
        for t in crm_store.todos():
            f = str(t.get("faellig") or "")[:10]
            out.append({"id": f"crm:{t['id']}", "bereich": "CRM", "icon": "🤝", "titel": t.get("vorschlag") or "To-do",
                        "detail": t.get("firma") or "", "act": "go:crm", "act_id": "", "faellig": f,
                        "dringend": bool(f) and f <= heute,
                        "erledigen": {"pfad": f"/api/crm/todo/{t['id']}/erledigen", "label": "✓ Erledigt"}})
    if hat_modul(u, "content_ops"):
        wartet = reel_store.liste(status="wartet")
        if wartet:
            out.append({"id": "reels", "bereich": "Content", "icon": "🎬", "titel": f"{len(wartet)} Reel(s) zur Freigabe",
                        "detail": "prüfen, Caption anpassen, freigeben oder ablehnen", "act": "go:reel", "act_id": "",
                        "faellig": "", "dringend": False, "erledigen": None})
    out.sort(key=lambda t: (not t["dringend"], t["faellig"] or "9999", t["titel"]))
    return {"todos": out, "anzahl": len(out), "dringend": sum(1 for t in out if t["dringend"])}


@app.post("/api/finanzen/hinweis-quittieren")
async def finanz_hinweis_quittieren(request: Request):
    """CFO-Finanzcheck: „✓ Abgeglichen“ (Monat) / „✓ Kommt diesen Monat nicht“ (wiederkehrender Posten) -- protokolliert."""
    import re as _re
    from ...core.todos import QUITTUNG
    body = await _json(request)
    sl = str(body.get("schluessel") or "").strip().lower()[:160]

    def tun():
        if not _re.fullmatch(r"(monat:\d{4}-\d{2}|fehlt:.{1,120}:\d{4}-\d{2})", sl):
            raise ValueError("Unbekannter Hinweis.")
        kunden_store.bh.erfassen(QUITTUNG, {"schluessel": sl}, von=_von(request))
        return {"quittiert": sl}
    return _kunden_aktion(tun)


@app.post("/api/crm/angebote/{nummer}/nachgefasst")
async def angebot_nachgefasst(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(_mit_aufraeumen(lambda: _angebote().nachgefasst(nummer, notiz=body.get("notiz") or "",
                                                                          von=_von(request)), _von(request)))


# -- Finanzen: Uebersicht, Journal, EUeR, Anlagen, Eigenbelege (KUNDEN_FINANZEN Etappe 7; Modul finanzen) -----------

def _finanzen() -> Finanzen:
    return Finanzen(kunden_store.bh, kunden_store)


@app.get("/api/finanzen/uebersicht")
def finanzen_uebersicht(jahr: int = 0, zeitraum: str = "jahr"):
    try:
        return _finanzen().uebersicht(jahr or None, zeitraum or "jahr")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@app.get("/api/finanzen/posten")
def finanzen_posten(jahr: int = 0, zeitraum: str = "jahr", art: str = "", kategorie: str = "", gegenpartei: str = ""):
    """Drill-down (Etappe 8): die Zeilen hinter einer Zahl im Cockpit; `summe_cent` = die angezeigte Zahl."""
    from ...core.finanzen import kennzahlen
    j = jahr or int(jetzt_iso()[:4])
    try:
        z = _finanzen().posten(j, zeitraum or "jahr", art=art, kategorie=kategorie, gegenpartei=gegenpartei)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"jahr": j, "zeitraum": zeitraum, "zeilen": z, "kennzahlen": kennzahlen(z)}


@app.get("/api/finanzen/ki-kosten")
def finanzen_ki_kosten(jahr: int = 0):
    """KI-Verbrauch (geschaetzt) je Monat/Anbieter + Monatsbudget -- nur Anzeige, nicht in der EUeR."""
    from ...core.kosten import KostenStore
    j = jahr or int(jetzt_iso()[:4])
    return KostenStore(ROOT / "finance" / "kosten-log.jsonl").jahr(j) | {"budget": _budget()}


@app.get("/api/finanzen/journal")
def finanzen_journal(jahr: int = 0, format: str = "", firma: str = ""):
    j = jetzt_iso()[:4]
    zeilen = _finanzen().journal(jahr or int(j), firma=firma)
    if format == "csv":
        return Response("\ufeff" + journal_csv(zeilen), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="Journal_{jahr or j}.csv"'})
    return {"jahr": jahr or int(j), "zeilen": zeilen}


@app.get("/api/finanzen/euer")
def finanzen_euer(jahr: int = 0):
    return _finanzen().euer(jahr or int(jetzt_iso()[:4]))


@app.get("/api/finanzen/anlagen")
def finanzen_anlagen(jahr: int = 0):
    j = jahr or int(jetzt_iso()[:4])
    return {"jahr": j, "anlagen": _finanzen().anlagen(j)}


@app.get("/api/finanzen/abschluss")
def finanzen_abschluss(jahr: int = 0):
    """Etappe 9: Abschluss-Pruefung + EUeR je amtlicher Zeile (Eingabehilfe fuer ELSTER)."""
    from ...core import jahresabschluss as ja
    j = jahr or int(jetzt_iso()[:4])
    return {"jahr": j, "jahre": ja.jahre_mit_daten(kunden_store.bh),
            "pruefung": ja.abschluss_check(kunden_store.bh, kunden_store, j), "euer": ja.euer_zeilen(_finanzen(), j),
            "verlustvortrag": ja.verlustvortrag_hinweis(kunden_store.bh, _finanzen(), j)}


@app.post("/api/finanzen/verlustvortrag")
async def finanzen_verlustvortrag(request: Request):
    """Verbleibenden Verlust eines Jahres erfassen/korrigieren (neuer Eintrag, der letzte gilt; protokolliert)."""
    from ...core.beleg_pdf import cent
    from ...core.finanzen import VERLUSTVORTRAG
    body = await _json(request)

    def tun():
        try:
            jahr = int(body.get("jahr"))
        except (TypeError, ValueError):
            raise ValueError("Jahr fehlt.") from None
        if not 2000 <= jahr < int(jetzt_iso()[:4]):
            raise ValueError("Verlustvortrag nur fuer abgeschlossene Jahre.")
        try:
            c = cent(body.get("betrag") or 0)
        except ValueError:
            raise ValueError("Betrag ungueltig.") from None
        if c < 0:
            raise ValueError("Betrag als positive Zahl (Hoehe des Verlusts) angeben.")
        kunden_store.bh.erfassen(VERLUSTVORTRAG, {"jahr": jahr, "betrag_cent": c, "notiz": str(body.get("notiz") or "")[:300]},
                                 von=_von(request))
        return {"jahr": jahr, "betrag_cent": c}
    return _kunden_aktion(tun)


@app.get("/api/finanzen/abschluss/export")
def finanzen_export(jahr: int = 0):
    """Export fuer Finanzamt/Steuerberater (ZIP: Tabellen + index.xml, Kassenbuch, Belege, EUeR-PDF)."""
    from ...core.jahresabschluss import export_zip
    j = jahr or int(jetzt_iso()[:4])
    daten = export_zip(kunden_store.bh, kunden_store, j, _firmendaten() or {})
    return Response(daten, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="Buchhaltung_{j}.zip"'})


@app.get("/api/finanzen/abschluss/euer.pdf")
def finanzen_euer_pdf(jahr: int = 0):
    from ...core.jahresabschluss import euer_pdf
    j = jahr or int(jetzt_iso()[:4])
    return Response(euer_pdf(_finanzen(), j, _firmendaten() or {}), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="EUER_{j}.pdf"'})


@app.get("/api/finanzen/eigenbelege")
def eigenbelege_liste():
    return {"eigenbelege": EigenbelegStore(kunden_store.bh).liste(), "kategorien": KATEGORIE_NAMEN}


@app.post("/api/finanzen/eigenbelege")
async def eigenbeleg_anlegen(request: Request):
    body = await _json(request)
    def tun():
        b = dict(body.get("buchung") or {})
        if not (b.get("firma") or str(b.get("gegenpartei") or "").strip()):
            raise ValueError("Bitte angeben, von wem bzw. an wen (Gegenpartei) -- jeder Beleg braucht eine Stammdaten-Nummer.")
        EigenbelegStore.pruefen(b)                           # erst pruefen, dann ggf. Firma anlegen
        b["firma"] = _firma_fuer_beleg(b.get("firma") or "", b.get("gegenpartei") or "", b.get("art") or "ausgabe", "",
                                       _von(request))
        if not str(b.get("gegenpartei") or "").strip():
            b["gegenpartei"] = kunden_store.firma(b["firma"])["name"]
        return EigenbelegStore(kunden_store.bh).anlegen(b, von=_von(request))
    return _kunden_aktion(tun)



@app.post("/api/finanzen/eigenbelege/{nummer}/stornieren")
async def eigenbeleg_stornieren(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: EigenbelegStore(kunden_store.bh).stornieren(nummer, body.get("grund") or "",
                                                                              von=_von(request)))


@app.post("/api/finanzen/belege/{nummer}/verwerfen")
async def beleg_verwerfen(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(_mit_aufraeumen(lambda: _eingang().verwerfen(nummer, body.get("grund") or "", von=_von(request)),
                                          _von(request)))


# -- Abos / wiederkehrende Zahlungen (KUNDEN_FINANZEN Etappe 15) --------------------------------------------------

def _abos():
    from ...core.abos import AboStore
    return AboStore(kunden_store.bh)


@app.get("/api/finanzen/abos")
def abos_liste():
    from ...core.abos import TURNUS
    liste = _abos().liste()
    namen = {f["nummer"]: f for f in kunden_store.firmen()}
    for a in liste:
        f = namen.get(a["firma"]) or {}
        a["firma_name"], a["firma_nr"] = f.get("name", ""), f.get("anzeige", a["firma"])
    aktiv = [a for a in liste if a["status"] == "aktiv"]
    aus = sum(a["monatlich_cent"] for a in aktiv if a["art"] == "ausgabe")
    ein = sum(a["monatlich_cent"] for a in aktiv if a["art"] == "einnahme")
    return {"abos": liste, "turnus": {k: v[0] for k, v in TURNUS.items()}, "kategorien": KATEGORIE_NAMEN,
            "summe": {"ausgaben_monat_cent": aus, "ausgaben_jahr_cent": aus * 12, "einnahmen_monat_cent": ein},
            "firmen": _lieferanten()}


@app.post("/api/finanzen/abos")
async def abo_anlegen(request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _abos().anlegen(body.get("abo") or {}, kunden_store, von=_von(request)))


@app.post("/api/finanzen/abos/{nummer}")
async def abo_aendern(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _abos().aendern(nummer, body.get("abo") or {}, kunden_store, von=_von(request)))


@app.post("/api/finanzen/abos/{nummer}/beenden")
async def abo_beenden(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _abos().beenden(nummer, body.get("ende") or jetzt_iso()[:10], body.get("grund") or "",
                                                   von=_von(request)))


@app.post("/api/finanzen/abos/{nummer}/buchen")
async def abo_buchen(nummer: str, request: Request):
    """Faelligkeit buchen -- `faellig` (oder `schluessel` aus dem To-do der Hauptseite), optional `datum`/`betrag`."""
    body = await _json(request)
    return _kunden_aktion(lambda: _abos().buchen(nummer, body.get("faellig") or body.get("schluessel") or "", kunden_store,
                                                  datum=body.get("datum") or "", betrag=body.get("betrag"),
                                                  von=_von(request)))


@app.post("/api/finanzen/abos/{nummer}/ueberspringen")
async def abo_ueberspringen(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _abos().ueberspringen(nummer, body.get("faellig") or "", body.get("grund") or "",
                                                         von=_von(request)))


@app.post("/api/finanzen/stammdaten/zuordnen")
async def stammdaten_zuordnen(request: Request):
    """Etappe 14, einmalig/nachholend: jeder gebuchte Beleg und Eigenbeleg bekommt seine Stammdaten-Nummer (finden oder
    anlegen), jede Lieferanten-/Partnerfirma ihre L-/P-Nummer. `probe: true` = nur anzeigen, nichts schreiben."""
    from ...core.eigenbelege import EigenbelegStore as _EB
    body = await _json(request)
    probe, von = bool(body.get("probe")), _von(request)

    def tun():
        e = kunden_store.bh.eintraege()
        plan = []
        for x in sorted(_eb.EingangStore._falte(e).values(), key=lambda b: b["nummer"]):
            fe = x.get("felder") or {}
            if x["status"] == "gebucht" and not fe.get("lieferant_firma"):
                vor = kunden_store.finde(fe.get("lieferant", ""), (x.get("vorschlag") or {}).get("absender", ""))
                plan.append({"beleg": x["nummer"], "name": fe.get("lieferant", ""), "art": fe.get("art", "ausgabe"),
                             "absender": (x.get("vorschlag") or {}).get("absender", ""), "firma": vor})
        ohne = []
        for x in sorted(_EB._falte(e).values(), key=lambda b: b["nummer"]):
            if not x.get("firma"):
                if not x.get("gegenpartei"):
                    ohne.append(x["nummer"])
                    continue
                plan.append({"beleg": x["nummer"], "name": x["gegenpartei"], "art": x["art"], "absender": "",
                             "firma": kunden_store.finde(x["gegenpartei"])})
        rollen = [f["nummer"] for f in kunden_store.firmen() if f.get("typ") in ("lieferant", "partner")
                  and f["anzeige"] == f["nummer"] and not f["nummer"].startswith(("L-", "P-"))]
        if probe:
            return {"probe": True, "plan": plan, "ohne_gegenpartei": ohne, "rollennummern_fuer": rollen}
        for nr in rollen:                                   # zuerst die vorhandenen Firmen (L-00001 ... in Anlagereihenfolge)
            kunden_store.rollennummer_sichern(nr, von=von)
        erg = []
        for pz in plan:
            nr = kunden_store.zuordnen(pz["name"], art=pz["art"], absender=pz["absender"], von=von) if not pz["firma"] \
                else _firma_fuer_beleg(pz["firma"], pz["name"], pz["art"], pz["absender"], von)
            (_eingang() if pz["beleg"].startswith("ER-") else _EB(kunden_store.bh)).firma_verknuepfen(pz["beleg"], nr, von=von)
            erg.append({"beleg": pz["beleg"], "firma": kunden_store.firma(nr)["anzeige"]})
        return {"zugeordnet": erg, "ohne_gegenpartei": ohne,
                "rollennummern": {nr: kunden_store.firma(nr)["anzeige"] for nr in rollen}}
    return _kunden_aktion(tun)


@app.post("/api/finanzen/belege/{nummer}/als-nachweis")
async def beleg_als_nachweis(nummer: str, request: Request):
    """Beleg ist nur die Zahlungsquittung zu einem anderen Beleg: Datei dorthin, dieser wird verworfen."""
    body = await _json(request)
    return _kunden_aktion(_mit_aufraeumen(lambda: _eingang().als_nachweis(nummer, body.get("zu") or "", von=_von(request)),
                                          _von(request)))


@app.post("/api/finanzen/belege/{nummer}/neu-auslesen")
async def beleg_neu_auslesen(nummer: str, request: Request):
    return _kunden_aktion(lambda: {"auftrag": _eb.llm_beauftragen(_eingang(), backoffice, nummer.upper())})


@app.get("/api/crm/katalog")
def katalog_lesen(request: Request):
    """Leistungskatalog (Formate, Pakete, Zuschlaege, Texte) fuer Angebots-Editor und Preisliste (Etappe 3b)."""
    k = Katalog(kunden_store.bh)
    u = getattr(request.state, "user", None) or _ceo_user()
    from ...core.katalog import OMR
    return {"katalog": k.laden(), "gespeichert": k.pfad.exists(), "darf_aendern": hat_modul(u, "finanzen"), "omr": OMR}


@app.get("/api/finanzen/lager")
def lager_liste():
    """Etappe 21: Bestaende physischer Ware (Zugaenge minus Verkaeufe laut Rechnungen)."""
    from ...core.lager import Lager
    return {"artikel": Lager(kunden_store.bh, Katalog(kunden_store.bh)).uebersicht()}


@app.post("/api/finanzen/lager/{artikel}/bewegung")
async def lager_bewegung(artikel: str, request: Request):
    """Zugang/Korrektur erfassen (Modul finanzen)."""
    from ...core.lager import Lager
    body = await _json(request)
    return _kunden_aktion(lambda: Lager(kunden_store.bh, Katalog(kunden_store.bh)).bewegung(
        artikel, body.get("menge"), grund=body.get("grund") or "", datum=body.get("datum") or "",
        beleg=body.get("beleg") or "", von=_von(request)))


@app.post("/api/crm/katalog")
async def katalog_speichern(request: Request):
    """Katalog speichern -- Preise sind Geschaeftsdaten: nur mit Modul finanzen (Owner)."""
    u = getattr(request.state, "user", None) or _ceo_user()
    if not hat_modul(u, "finanzen"):
        return {"ok": False, "hinweis": "Preise aendern darf nur, wer das Modul Finanzen hat."}
    body = await _json(request)
    return _kunden_aktion(lambda: Katalog(kunden_store.bh).speichern(body.get("katalog") or {}, von=_von(request)))


@app.get("/api/crm/katalog/preisliste.pdf")
def katalog_preisliste(ids: str = "", firma: str = "", ap: str = ""):
    """Preisliste im Hanserautisch-Look (ohne Nummer, ohne Buchhaltungseintrag)."""
    fd = _firmendaten()
    if not fd:
        raise HTTPException(status.HTTP_409_CONFLICT, "Firmendaten fehlen (buchhaltung/firmendaten.json)")
    f = kunden_store.firma(firma) if firma else None
    a = next((x for x in (f or {}).get("ansprechpartner_liste", []) if x["nummer"] == ap.strip().upper()), None)
    auswahl = [i for i in ids.split(",") if i.strip()] or None
    try:
        daten = preisliste_pdf(Katalog(kunden_store.bh).laden(), fd, logo=kunden_store.bh.dir / "logo.jpg",
                               ids=auswahl, firma=f, ap=a)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except ImportError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PDF-Bibliothek fehlt -- Docker-Image neu bauen")
    name = "Preisliste_Hanserautisch" + (f"_{f['nummer']}" if f else "") + ".pdf"
    return Response(daten, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})


@app.get("/api/crm/angebote")
def angebote_liste(firma: str = ""):
    return {"angebote": _angebote().liste(firma=firma)}


@app.get("/api/crm/angebote/{nummer}")
def angebot_detail(nummer: str):
    a = _angebote().angebot(nummer)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Angebotsnummer")
    f = kunden_store.firma(a["firma"]) or {}
    ap = next((x for x in f.get("ansprechpartner_liste", []) if x["nummer"] == a.get("ansprechpartner")), None)
    return {"angebot": a, "firma": {k: f.get(k) for k in ("nummer", "name", "rechnungsmail", "collab")},
            "ansprechpartner": ap, "mail_an": (ap or {}).get("mail") or f.get("rechnungsmail") or "",
            "google": bool(_google().verfuegbar()), "firmendaten": bool(_firmendaten())}


@app.post("/api/crm/angebote")
async def angebot_anlegen(request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _angebote().anlegen(body.get("angebot") or {}, von=_von(request)))


@app.post("/api/crm/angebote/{nummer}")
async def angebot_aendern(nummer: str, request: Request):
    body = await _json(request)
    return _kunden_aktion(lambda: _angebote().aendern(nummer, body.get("angebot") or {}, von=_von(request)))


@app.get("/api/crm/angebote/{nummer}/pdf")
def angebot_pdf(nummer: str, archiv: int = 0):
    """PDF-Vorschau (aktueller Stand) oder mit ?archiv=1 das zuletzt abgelegte (verschickte) PDF."""
    st = _angebote()
    a = st.angebot(nummer)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Angebotsnummer")
    if archiv:
        if not a["pdfs"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "noch kein PDF abgelegt")
        daten = (kunden_store.bh.dir / a["pdfs"][-1]["pfad"]).read_bytes()
    else:
        fd = _firmendaten()
        if not fd:
            raise HTTPException(status.HTTP_409_CONFLICT, "Firmendaten fehlen (buchhaltung/firmendaten.json)")
        try:
            daten = st.pdf(a["nummer"], fd)
        except ImportError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PDF-Bibliothek fehlt -- Docker-Image neu bauen")
    return Response(daten, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Angebot_{a["nummer"]}.pdf"'})


def _angebot_pdf_ablegen(st: AngebotStore, a: dict, *, an: str, entwurf_id: str, von: str) -> dict:
    return st.pdf_ablegen(a["nummer"], st.pdf(a["nummer"], _firmendaten()), an=an, entwurf_id=entwurf_id, von=von)


@app.post("/api/crm/angebote/{nummer}/mailentwurf")
async def angebot_mailentwurf(nummer: str, request: Request):
    """PDF erzeugen + ablegen, Gmail-**Entwurf** mit Anhang anlegen. Senden macht der CEO in Gmail."""
    body = await _json(request)
    st = _angebote()

    def tun():
        a = st.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if a["status"] != "entwurf":
            raise ValueError(f"{a['nummer']} ist bereits {a['status']}.")
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen (buchhaltung/firmendaten.json auf der NAS).")
        d = angebot_detail(a["nummer"])
        an = (body.get("an") or d["mail_an"] or "").strip()
        if not an:
            raise ValueError("Keine Mail-Adresse: beim Ansprechpartner oder als Rechnungs-Mail der Firma eintragen.")
        g = _google()
        if not g.verfuegbar():
            raise ValueError("Google ist nicht verbunden -- Mail-Entwurf nicht moeglich.")
        pdf = st.pdf(a["nummer"], fd)
        betreff, text = angebot_mail_text(a, d["firma"], d["ansprechpartner"], fd)
        r = g.mail_entwurf(an, betreff, text, anhaenge=[(f"Angebot_{a['nummer']}.pdf", pdf, "application/pdf")])
        if not r.get("ok"):
            raise ValueError(r.get("hinweis") or "Gmail-Entwurf fehlgeschlagen.")
        abl = st.pdf_ablegen(a["nummer"], pdf, an=an, entwurf_id=r.get("entwurf_id", ""), von=_von(request))
        return {"an": an, "entwurf_id": r.get("entwurf_id"), "pdf": abl["pfad"]}
    return _kunden_aktion(tun)


@app.post("/api/crm/angebote/{nummer}/versendet")
async def angebot_versendet(nummer: str, request: Request):
    """CEO hat das Angebot verschickt: Inhalt einfrieren, Kalender-Erinnerungen (Nachfassen, vor Ablauf), CRM-Stufe."""
    from datetime import date as _date, timedelta as _td
    st = _angebote()

    def tun():
        a = st.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if a["status"] != "entwurf":
            raise ValueError(f"{a['nummer']} ist bereits {a['status']}.")
        hinweise = []
        pdf = next((p["pfad"] for p in reversed(a["pdfs"]) if p.get("inhalt") == a["inhalt"]), "")
        if not pdf:
            if not _firmendaten():
                raise ValueError("Firmendaten fehlen (buchhaltung/firmendaten.json auf der NAS).")
            pdf = _angebot_pdf_ablegen(st, a, an="", entwurf_id="", von=_von(request))["pfad"]
            if a["pdfs"]:
                hinweise.append("Inhalt wurde nach dem letzten Mail-Entwurf geaendert -- aktueller Stand wurde abgelegt.")
        termine, weitere = _als_versendet(st, a, pdf=pdf, von=_von(request))
        return {"termine": termine, "hinweise": hinweise + weitere}
    return _kunden_aktion(tun)


def _als_versendet(st: AngebotStore, a: dict, *, pdf: str, von: str, mail: dict | None = None) -> tuple[list, list]:
    """Gemeinsam fuer „Als versendet markieren" und „Jetzt senden": Erinnerungen, Status (friert ein), CRM-Stufe."""
    from datetime import date as _date
    termine, hinweise = _angebot_erinnerungen(a, _date.fromisoformat(jetzt_iso()[:10]))
    st.status_setzen(a["nummer"], "versendet", termine=termine, pdf=pdf, mail=mail, von=von)
    for c in (kunden_store.firma(a["firma"]) or {}).get("collab", []):   # CRM-Stufe „angebot“
        anzeige = next((f.get("firma") for f in crm_store.firmen() if (f.get("firma") or "").strip().lower() == c), c)
        try:
            crm_store.status_setzen(anzeige, "angebot")
        except Exception:
            hinweise.append(f"CRM-Stufe fuer {anzeige} nicht gesetzt.")
    return termine, hinweise


ABSENDER_NAME = "Hanserautisch – LUNA"


@app.get("/api/crm/angebote/{nummer}/versandvorschau")
def angebot_versandvorschau(nummer: str):
    """Was „Jetzt senden" verschicken wuerde: Empfaenger, Betreff, Text, PDF (vom CEO in LUNA-OS anpassbar)."""
    d = angebot_detail(nummer)
    a = d["angebot"]
    betreff, text = angebot_mail_text(a, d["firma"], d["ansprechpartner"], _firmendaten())
    konto = (_google_secrets().get("GOOGLE_ACCOUNT_EMAIL") or "").strip()
    return {"an": d["mail_an"], "betreff": betreff, "text": text, "pdf": f"Angebot_{a['nummer']}.pdf",
            "absender": f"{ABSENDER_NAME} <{konto}>" if konto else ABSENDER_NAME, "google": d["google"],
            "status": a["status"]}


@app.get("/api/crm/angebote/{nummer}/mail/{message_id}")
def angebot_mail(nummer: str, message_id: str):
    """Eine Mail zum Angebot (gesendet oder Kundenantwort) zum Aufklappen im Verlauf -- aus dem Archiv (.eml),
    sonst live aus LUNAs Gmail (noch nicht archiviert)."""
    a = _angebote().angebot(nummer)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unbekannte Angebotsnummer")
    bekannt = {(a.get("versendet_mail") or {}).get("message_id")} | {x.get("message_id") for x in a.get("antworten", [])}
    if message_id not in bekannt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mail gehoert nicht zu diesem Angebot")
    arch = (a.get("mail_archiv") or {}).get(message_id)
    if arch:
        return mail_lesen((kunden_store.bh.dir / arch["pfad"]).read_bytes()) | {"archiviert": True}
    r = _google().mail_roh(message_id)
    if not r.get("ok"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, r.get("hinweis") or "Mail nicht abrufbar")
    return mail_lesen(r["roh"]) | {"archiviert": False}


@app.post("/api/crm/angebote/{nummer}/senden")
async def angebot_senden(nummer: str, request: Request):
    """Angebot aus LUNAs Google-Konto an den Kunden senden -- Oeffentlichkeit = CEO-Tor: nur mit Modul finanzen (Owner)
    und nur mit ausdruecklicher Bestaetigung aus der Vorschau. Danach automatisch „versendet" (Erinnerungen, CRM)."""
    u = getattr(request.state, "user", None) or _ceo_user()
    if not hat_modul(u, "finanzen"):
        return {"ok": False, "hinweis": "Angebote an Kunden senden darf nur der CEO (Modul Finanzen)."}
    body = await _json(request)
    st = _angebote()

    def tun():
        if body.get("bestaetigt") is not True:
            raise ValueError("Senden braucht die ausdrueckliche Bestaetigung aus der Vorschau.")
        a = st.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if a["status"] != "entwurf":
            raise ValueError(f"{a['nummer']} ist bereits {a['status']}.")
        an = (body.get("an") or "").strip()
        betreff, text = (body.get("betreff") or "").strip(), (body.get("text") or "").strip()
        if not an or "@" not in an or not betreff or not text:
            raise ValueError("Empfaenger, Betreff und Text sind Pflicht.")
        fd = _firmendaten()
        if not fd:
            raise ValueError("Firmendaten fehlen (buchhaltung/firmendaten.json auf der NAS).")
        g = _google()
        if not g.verfuegbar():
            raise ValueError("Google ist nicht verbunden -- Senden nicht moeglich.")
        pdf = st.pdf(a["nummer"], fd)
        r = g.mail_senden(an, betreff, text, bestaetigt=True, absender_name=ABSENDER_NAME,
                          anhaenge=[(f"Angebot_{a['nummer']}.pdf", pdf, "application/pdf")])
        if not r.get("ok"):
            raise ValueError(r.get("hinweis") or "Senden fehlgeschlagen.")
        abl = st.pdf_ablegen(a["nummer"], pdf, an=an, entwurf_id="", von=_von(request))   # genau das gesendete PDF
        mail = {"an": an, "message_id": r.get("id", ""), "thread_id": r.get("thread_id", ""), "betreff": betreff}
        termine, hinweise = _als_versendet(st, st.angebot(a["nummer"]), pdf=abl["pfad"], von=_von(request), mail=mail)
        roh = g.mail_roh(mail["message_id"]) if mail["message_id"] else {}
        if roh.get("ok"):                                         # Original-Mail sofort archivieren (sonst im Poll)
            st.mail_archivieren(a["nummer"], mail["message_id"], roh["roh"], richtung="aus", von=_von(request))
        return {"an": an, "termine": termine, "hinweise": hinweise}
    return _kunden_aktion(tun)


def _angebot_erinnerungen(a: dict, basis, *, nur_fehlende: bool = False) -> tuple[list, list]:
    """Kalender-Erinnerungen 09:00: Nachfassen (basis + N Tage) und Tag vor Ablauf. Rueckgabe (termine, hinweise).
    `nur_fehlende`: bereits angelegte (gleicher Titel) auslassen; Tage in der Vergangenheit auf heute ziehen."""
    from datetime import date as _date, timedelta as _td
    heute = _date.fromisoformat(jetzt_iso()[:10])
    name = (kunden_store.firma(a["firma"]) or {}).get("name", a["firma"])
    wuensche = [(max(basis + _td(days=int(a.get("nachfassen_tage") or 7)), heute),
                 f"Angebot {a['nummer']} nachfassen: {name}")]
    ablauf = _date.fromisoformat(a["gueltig_bis"]) - _td(days=1)
    if ablauf > heute and ablauf != wuensche[0][0]:
        wuensche.append((ablauf, f"Angebot {a['nummer']} läuft morgen ab: {name}"))
    if nur_fehlende:
        da = {t.get("titel") for t in a.get("versendet_termine") or []}
        wuensche = [w for w in wuensche if w[1] not in da]
    termine, hinweise, g = [], [], _google()
    for tag, titel in wuensche:
        if not g.verfuegbar():
            hinweise.append("Google nicht verbunden -- keine Kalender-Erinnerung angelegt.")
            break
        r = g.termin_anlegen(titel, f"{tag.isoformat()}T09:00:00", f"{tag.isoformat()}T09:15:00",
                             beschreibung=f"{a['nummer']} · {name} · {a.get('titel') or ''}\nLUNA-OS -> Angebote",
                             bestaetigt=True)
        if r.get("ok"):
            termine.append({"datum": tag.isoformat(), "titel": titel, "id": r.get("termin_id", "")})
        else:
            hinweise.append(f"Kalender: {r.get('hinweis') or 'Fehler'}")
    return termine, hinweise


@app.post("/api/crm/angebote/{nummer}/erinnerungen")
async def angebot_erinnerungen_nachholen(nummer: str, request: Request):
    """Fehlende Kalender-Erinnerungen eines versendeten Angebots nachholen (z. B. nach Google-Ausfall, BF-33)."""
    from datetime import date as _date
    st = _angebote()

    def tun():
        a = st.angebot(nummer)
        if not a:
            raise KeyError(nummer)
        if a["status"] != "versendet":
            raise ValueError(f"{a['nummer']} ist {a['status']} -- Erinnerungen nur fuer versendete Angebote.")
        basis = _date.fromisoformat(str(a.get("versendet_am") or jetzt_iso())[:10])
        termine, hinweise = _angebot_erinnerungen(a, basis, nur_fehlende=True)
        if termine:
            st.erinnerungen_ergaenzen(a["nummer"], termine, von=_von(request))
        elif not hinweise:
            hinweise.append("Alle Erinnerungen sind bereits im Kalender.")
        return {"termine": termine, "hinweise": hinweise}
    return _kunden_aktion(tun)


@app.post("/api/crm/angebote/{nummer}/status")
async def angebot_status(nummer: str, request: Request):
    body = await _json(request)
    ziel = (body.get("status") or "").strip()
    if ziel not in ("angenommen", "abgelehnt"):
        return {"ok": False, "hinweis": "Status muss angenommen oder abgelehnt sein."}
    return _kunden_aktion(_mit_aufraeumen(lambda: _angebote().status_setzen(nummer, ziel, grund=body.get("grund") or "",
                                                                            von=_von(request)), _von(request)))


def jetzt_iso() -> str:
    from ...core.buchhaltung import jetzt
    return jetzt().isoformat()


@app.post("/api/crm/sync")
async def crm_sync():
    """Manueller Instagram-DM-Abruf -- macht dasselbe wie der automatische Poll: pollt die DM-Threads des
    EIGENEN Kontos ueber die Graph Conversations-API und speist neue EINGEHENDE Kooperations-DMs in den
    CRM-Pfad (Klassifikation + To-do + Notifier). Nur Empfang/Lesen -- kein Senden (Oeffentlichkeit = CEO-Tor).
    Gibt {ok, gesehen, neu} bzw. {ok:false, hinweis/api_fehler}."""
    from ...governance.instagram_token import ig_reader_aus_env
    from ...governance.leak_guard import is_redactable_secret
    from ...core.crm_instagram import CrmInstagramTracker
    sec_dict = _secrets_dict()
    reader = ig_reader_aus_env(sec_dict)
    sec = [v for v in sec_dict.values() if isinstance(v, str) and is_redactable_secret(v)]
    tracker = CrmInstagramTracker(crm=crm_store, reader=reader, secrets=sec, notify=notifications.enqueue)
    res = await asyncio.to_thread(tracker.lauf)
    return JSONResponse(res)


# -- Reel-Pipeline Stufe C: 1-Tap-Freigabe (Mac reicht ein -> CEO gibt frei; Auto-Posten = CEO-Tor) --
@app.post("/api/reel/einreichen")
async def reel_einreichen(request: Request):
    """Der Mac-Cutter reicht ein fertiges Reel ein (Video als base64 im JSON -> keine multipart-Dependency).
    Wird als 'wartet' registriert; der CEO gibt es in der Reels-App frei. Kein Auto-Posten."""
    import base64 as _b64
    body = await request.json()
    b64 = body.get("video_b64") or ""
    if not b64:
        return JSONResponse({"ok": False, "fehler": "Kein Video (video_b64)."}, status_code=400)
    try:
        daten = _b64.b64decode(b64)
    except Exception:
        return JSONResponse({"ok": False, "fehler": "video_b64 ungueltig."}, status_code=400)
    rid = uuid.uuid4().hex[:12]
    REEL_DIR.mkdir(parents=True, exist_ok=True)
    ziel = REEL_DIR / f"{rid}.mp4"
    ziel.write_bytes(daten)
    reel_store.einreichen(rid=rid, datum=str(body.get("datum", "")), thema=str(body.get("thema", "")),
                          caption=str(body.get("caption", "")), video=str(ziel),
                          spiele=body.get("spiele") or [], dauer_sek=body.get("dauer_sek"),
                          clips=body.get("clips") or [])
    thema = str(body.get("thema", ""))
    datum = str(body.get("datum", ""))
    try:
        notifications.enqueue(
            f"Neues Reel ({thema}, {datum}) wartet auf Freigabe -> LUNA-OS App Reels.",
            abteilung="CBO", kategorie="anliegen",
            detail="Auto-Reel-Pipeline: in der Reels-App ansehen und Freigeben/Ablehnen (Auto-Posten = CEO-Tor).")
    except Exception:
        pass
    return JSONResponse({"ok": True, "id": rid})


@app.get("/api/reel")
def reel_liste():
    """Eingereichte Reels (neueste zuerst) fuer die Reels-App."""
    return {"reels": reel_store.liste(limit=60)}


@app.get("/api/entwicklungs-roadmap")
def entwicklungs_roadmap_liste():
    """Read-only: die Entwicklungs-Roadmap (aus freigegebenen Antraegen) fuer die LUNA-OS-Ansicht.
    Schreiben passiert nur ueber den Freigabe-Hook / die CLI -- die Web-Ansicht ist rein lesend."""
    return {"items": entwicklungs_roadmap.list()}


@app.get("/api/reel/{rid}/video")
def reel_video(rid: str):
    """Liefert das eingereichte Reel-Video (Inline-Vorschau in der Reels-App)."""
    r = reel_store.holen(rid)
    if not r or not r.get("video") or not Path(r["video"]).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video nicht gefunden.")
    return FileResponse(r["video"], media_type="video/mp4")


def _reel_posten(rid: str) -> None:
    """Stufe D: freigegebenes Reel als Facebook-Reel veroeffentlichen (Hintergrund). Status -> gepostet|fehler.
    Braucht einen Seiten-Token mit pages_manage_posts (Token-Scope). Bis dahin schlaegt es sauber fehl."""
    r = reel_store.holen(rid)
    if not r or not r.get("video"):
        return
    try:
        from ...governance.facebook_reels import poste_reel
        from ...governance.instagram_token import InstagramTokenManager
        sec = _secrets_dict()
        mgr = InstagramTokenManager.from_env(sec)
        page_id, token = mgr.page_info(ig_user_id=sec.get("INSTAGRAM_IG_USER_ID", ""))
        res = poste_reel(page_id, token, r["video"], r.get("caption", ""))
    except Exception as exc:
        res = {"ok": False, "fehler": str(exc)[:200]}
    if res.get("ok"):
        reel_store.status_setzen(rid, "gepostet", fb_video_id=res.get("video_id"))
        try:
            notifications.enqueue(f"Reel auf Facebook veroeffentlicht (video_id {res.get('video_id')}).",
                                  abteilung="CBO", kategorie="info")
        except Exception:
            pass
    else:
        reel_store.status_setzen(rid, "fehler", fehler=(res.get("fehler") or "Upload fehlgeschlagen")[:300])


@app.post("/api/reel/{rid}/freigeben")
async def reel_freigeben(rid: str, request: Request, hintergrund: BackgroundTasks):
    """CEO-Freigabe -> Status 'freigegeben' (optional angepasster Caption-Text) und startet den FB-Upload
    (Stufe D) im Hintergrund. Auto-Posten passiert NUR nach dieser Freigabe (CEO-Tor)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    caption = (body or {}).get("caption")
    ok = reel_store.status_setzen(rid, "freigegeben", **({"caption": caption} if caption is not None else {}))
    if ok:
        hintergrund.add_task(_reel_posten, rid)
    return JSONResponse({"ok": ok})


@app.post("/api/reel/{rid}/posten")
def reel_posten(rid: str, hintergrund: BackgroundTasks):
    """Upload erneut anstossen (z. B. nach Fehler). Nur fuer bereits eingereichte Reels."""
    if not reel_store.holen(rid):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reel nicht gefunden.")
    hintergrund.add_task(_reel_posten, rid)
    return JSONResponse({"ok": True, "status": "upload_gestartet"})


@app.post("/api/reel/{rid}/ablehnen")
async def reel_ablehnen(rid: str, request: Request):
    """CEO-Ablehnung -> Status 'abgelehnt' (wird nicht gepostet). Mit `{neu:true}` wird gleich ein NEUER
    Reel-Job (gleiches Thema/Spiel) in die Queue gelegt -> der Worker baut einen Ersatz."""
    body = await _json(request)
    ok = reel_store.status_setzen(rid, "abgelehnt")
    neu_job = False
    if ok and bool((body or {}).get("neu")):
        r = reel_store.holen(rid) or {}
        spiele = r.get("spiele") or []
        einzel = spiele[0] if (len(spiele) == 1 and spiele[0] not in ("alle Spiele", "?", "")) else ""
        job = _reel_job_einreihen(thema=(r.get("thema") or ""), spiel=einzel, alle_spiele=(not einzel),
                                  min_dauer=15, max_dauer=(_inum(r.get("dauer_sek")) or 45))
        neu_job = bool(job.get("ok"))
        if neu_job:
            _changelog("Cutter", f"Reel abgelehnt -> Ersatz angefordert ({r.get('thema') or 'Auto'})",
                       "CEO ueber LUNA-OS", "cutter")
    return JSONResponse({"ok": ok, "neu_job": neu_job})


def _radar_kompakt(k: dict) -> dict:
    a = k.get("analyse") or {}
    return {"contact_id": k.get("contact_id"), "name": k.get("name"),
            "nachrichten": k.get("nachrichten"), "ein": k.get("ein"), "aus": k.get("aus"),
            "letzte_ts": k.get("letzte_ts"), "letzte_richtung": k.get("letzte_richtung"),
            "letzter_text": k.get("letzter_text"), "analysiert": bool(a),
            "collab": bool(a.get("collab")), "zusammenfassung": a.get("zusammenfassung") or "",
            "stand": a.get("stand") or "", "offene_todos": a.get("offene_todos") or [],
            "warten_auf": a.get("warten_auf") or "", "gesehen_ts": k.get("gesehen_ts"),
            "reminder_ts": k.get("reminder_ts")}


@app.get("/api/collab-radar")
def collab_radar(nur_collab: int = 0):
    """Collab-Radar (Phase 3): Kontakte aus dem Voll-Postfach-Archiv mit KI-Analyse -- collab ja/nein,
    Zusammenfassung, Stand, offene To-dos, wer am Zug. Nur Lesen. `nur_collab=1` filtert auf Kooperationen."""
    kontakte = ig_inbox_store.kontakte()
    kontakte.sort(key=lambda k: k.get("letzte_ts") or "", reverse=True)
    alle = [_radar_kompakt(k) for k in kontakte]
    uebersicht = {
        "kontakte": len(alle),
        "collab": sum(1 for k in alle if k["collab"]),
        "warten_auf_uns": sum(1 for k in alle if k["collab"] and k["warten_auf"] == "uns"),
        "offene_todos": sum(len(k["offene_todos"]) for k in alle if k["collab"]),
        "unanalysiert": sum(1 for k in alle if not k["analysiert"]),
    }
    liste = [k for k in alle if k["collab"]] if nur_collab else alle
    return {"uebersicht": uebersicht, "kontakte": liste[:100]}


@app.get("/api/collab-radar/verlauf")
def collab_radar_verlauf(contact_id: str):
    """Voller Gespraechs-Verlauf eines Kontakts (ein/aus, Medien-Marker), chronologisch."""
    msgs = ig_inbox_store.verlauf(contact_id)
    return {"contact_id": contact_id, "nachrichten": [
        {"richtung": m.get("richtung"), "text": ("[Medien]" if m.get("medien") else m.get("text")),
         "ts": m.get("ts_msg") or m.get("ts")} for m in msgs][-80:]}


# content_ops -- Trends (K2)
@app.get("/api/trends")
def trends():
    return {"trends": trends_store.list(100)}


@app.post("/api/trends/{trend_id}/status")
async def trends_status(trend_id: str, request: Request):
    body = await _json(request)
    r = await asyncio.to_thread(trends_store.status_setzen, trend_id, (body.get("status") or "").strip())
    return JSONResponse({"ok": bool(r.get("ok")), "res": r, "trends": trends_store.list(100)})


@app.get("/api/ideas")
def ideas():
    return {"ideas": ideas_store.list(100)}


@app.post("/api/ideas/{idea_id}/status")
async def ideas_status(idea_id: str, request: Request):
    body = await _json(request)
    r = await asyncio.to_thread(ideas_store.status_setzen, idea_id, (body.get("status") or "").strip())
    return JSONResponse({"ok": bool(r.get("ok")), "res": r, "ideas": ideas_store.list(100)})


@app.get("/api/drafts")
def drafts():
    return {"drafts": drafts_store.list(100)}


@app.post("/api/drafts/{draft_id}/status")
async def drafts_status(draft_id: str, request: Request):
    body = await _json(request)
    r = await asyncio.to_thread(drafts_store.status_setzen, draft_id, (body.get("status") or "").strip())
    return JSONResponse({"ok": bool(r.get("ok")), "res": r, "drafts": drafts_store.list(100)})


@app.get("/api/sources")
def sources():
    return {"sources": sources_store.list(200)}


@app.post("/api/sources/{source_id}/aktiv")
async def sources_aktiv(source_id: str, request: Request):
    body = await _json(request)
    aktiv = bool(body.get("is_active"))
    r = await asyncio.to_thread(sources_store.patch, source_id, {"is_active": aktiv})
    return JSONResponse({"ok": bool(r.get("ok")), "res": r, "sources": sources_store.list(200)})


@app.get("/api/ai-inbox")
def ai_inbox():
    return {"items": aiinbox_store.list(100)}


@app.post("/api/ai-inbox/{item_id}/recommendation")
async def ai_inbox_recommendation(item_id: str, request: Request):
    body = await _json(request)
    r = await asyncio.to_thread(aiinbox_store.status_setzen, item_id, (body.get("recommendation") or "").strip())
    return JSONResponse({"ok": bool(r.get("ok")), "res": r, "items": aiinbox_store.list(100)})


@app.get("/api/investment/detail")
async def investment_detail(symbol: str, asset: str = "aktie"):
    eng = _investment_engine()
    d = await asyncio.to_thread(eng.detail, symbol, asset)
    d["kurs_historie"] = loop_store.kurs_serie(symbol)   # eigene angesammelte Kurs-Historie (Loop)
    return JSONResponse(d)


@app.get("/api/investment/suche")
async def investment_suche(q: str = ""):
    eng = _investment_engine()
    return JSONResponse(await asyncio.to_thread(eng.market.suche, q))


@app.post("/api/investment/watchlist")
async def investment_watchlist(request: Request):
    body = await _json(request)
    sym = (body.get("symbol") or "").strip()
    if not sym:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Symbol")
    inv_store.watchlist_add(sym, asset=(body.get("asset") or "aktie"))
    _changelog("CIO", f"Watchlist ergaenzt: {sym.upper()}", "CEO ueber LUNA-OS", "investment")
    return JSONResponse({"ok": True, "investment": investment()})


@app.post("/api/investment/watchlist/remove")
async def investment_watchlist_remove(request: Request):
    body = await _json(request)
    sym = (body.get("symbol") or "").strip()
    if not sym:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Symbol")
    inv_store.watchlist_remove(sym)
    _changelog("CIO", f"Watchlist entfernt: {sym.upper()}", "CEO ueber LUNA-OS", "investment")
    return JSONResponse({"ok": True, "investment": investment()})


# -- Depot-Ansichten: Paper (Alpaca-Sim, read-only) + echtes Depot (manuelles Transaktions-Ledger). --
@app.get("/api/investment/portfolio")
async def investment_portfolio():
    """Paper-Depot: Gesamtwert + Positionen (Aktien/ETF/Krypto) aus dem Alpaca-Paper-Konto."""
    from ...investment.portfolio import paper_portfolio
    return JSONResponse(await asyncio.to_thread(paper_portfolio, _paper_broker()))


@app.get("/api/investment/depot")
async def investment_depot():
    """Echtes Depot: aus dem Transaktions-Ledger gefaltete Netto-Positionen, live bewertet. Plus Buchungsliste."""
    from ...investment.portfolio import real_portfolio, depot_hinweise
    market = _investment_engine().market
    agg = inv_store.real_positionen()
    cfg = inv_store.settings()

    def _bauen():
        dp = real_portfolio(agg["positionen"], market, realisiert=agg["realisiert"])
        dp["transaktionen"] = list(reversed(inv_store.real_trades()))[:50]   # neueste zuerst
        dp["hinweise"] = depot_hinweise(dp["positionen"], stop_pct=cfg["depot_stop_pct"],
                                        target_pct=cfg["depot_target_pct"])   # rein beratend (LUNA)
        return dp
    return JSONResponse(await asyncio.to_thread(_bauen))


@app.post("/api/investment/depot/trade")
async def investment_depot_trade(request: Request):
    """Bucht einen Kauf/Verkauf ins echte Depot (manuell, keine echte Ausfuehrung)."""
    body = await _json(request)
    sym = (body.get("symbol") or "").strip()
    if not sym:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Symbol")
    klasse = (body.get("klasse") or "aktie").strip().lower()
    if klasse not in ("aktie", "etf", "krypto"):
        klasse = "aktie"
    side = "verkauf" if str(body.get("side", "kauf")).lower().startswith("verk") else "kauf"
    rid = inv_store.real_trade(sym, side=side, klasse=klasse, stueck=_inum(body.get("stueck")),
                               preis=_inum(body.get("preis")), gebuehr=_inum(body.get("gebuehr")),
                               kurs_id=(body.get("kurs_id") or "").strip(),
                               waehrung=(body.get("waehrung") or "USD").strip(),
                               datum=(body.get("datum") or "").strip())
    _changelog("CIO", f"Echtes Depot: {side} gebucht {sym.upper()} ({klasse})", "CEO ueber LUNA-OS", "investment")
    return JSONResponse({"ok": True, "id": rid})


@app.post("/api/investment/depot/storno")
async def investment_depot_storno(request: Request):
    """Storniert eine einzelne Buchung im echten Depot."""
    body = await _json(request)
    eid = (body.get("id") or "").strip()
    if not eid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "keine id")
    inv_store.real_storno(eid)
    _changelog("CIO", f"Echtes Depot: Buchung storniert {eid}", "CEO ueber LUNA-OS", "investment")
    return JSONResponse({"ok": True})


def _investment_engine_mit_broker():
    """Engine inkl. Paper-Broker fuer Order-Ausfuehrung (paper_order). Risk-Agent per Default."""
    from ...investment.engine import InvestmentEngine
    from ...investment.providers import MarketData
    return InvestmentEngine(MarketData(secrets=_secrets_dict()), inv_store, broker=_paper_broker())


@app.post("/api/investment/paper-order")
async def investment_paper_order(request: Request):
    """Manuelle Paper-Order (CEO). Zweistufig: ohne bestaetigt -> Schaetzwert+Risk zurueck; mit bestaetigt -> ausfuehren.
    PAPER = Spielgeld, kein Echtgeld-Tor. Autonomes Handeln durch LUNA bleibt separat gated."""
    body = await _json(request)
    sym = (body.get("symbol") or "").strip()
    if not sym:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kein Symbol")
    side = "sell" if str(body.get("side", "buy")).lower().startswith(("s", "verk")) else "buy"
    asset = "krypto" if (body.get("asset") or "aktie").strip().lower() == "krypto" else "aktie"
    qty = _inum(body.get("qty"))
    bestaetigt = bool(body.get("bestaetigt"))
    eng = _investment_engine_mit_broker()
    res = await asyncio.to_thread(eng.paper_order, sym, qty, side, asset=asset, bestaetigt=bestaetigt)
    if bestaetigt and res.get("ok"):
        _changelog("CIO", f"Paper-Order {side} {qty} {sym.upper()}", "CEO ueber LUNA-OS", "investment")
    return JSONResponse(res)


# -- Einstellungen (in der Weboberflaeche anpassbar; geteilte SSOT fuer Web + Telegram-Bot). --
_SETTING_STUNDE = {"briefing_morgen_stunde", "briefing_abend_stunde"}
_SETTING_STUNDE_OPT = {"ruhezeit_von", "ruhezeit_bis"}          # Stunde ODER None (= aus)
_SETTING_BOOL = {"depot_alerts", "alert_investment", "alert_crm", "alert_security", "alert_content"}


def _coerce_setting(key: str, wert):
    """Bringt einen Einstellwert in den richtigen Typ + Wertebereich. Wirft ValueError bei Unfug."""
    if key in _SETTING_BOOL:
        return bool(wert) if not isinstance(wert, str) else wert.strip().lower() in ("1", "true", "an", "ja", "on")
    if key in _SETTING_STUNDE:
        return max(0, min(23, int(float(wert))))
    if key in _SETTING_STUNDE_OPT:
        if wert in (None, "", "aus"):
            return None
        return max(0, min(23, int(float(wert))))
    return max(0.0, float(wert))                                # pct / Betrag


@app.get("/api/settings")
def settings_get():
    return JSONResponse(inv_store.settings())


@app.post("/api/settings")
async def settings_set(request: Request):
    body = await _json(request)
    roh = body.get("settings") if isinstance(body.get("settings"), dict) else body
    from ...investment.store import SETTINGS_DEFAULTS
    werte, fehler = {}, {}
    for k, v in (roh or {}).items():
        if k not in SETTINGS_DEFAULTS:
            continue
        try:
            werte[k] = _coerce_setting(k, v)
        except (TypeError, ValueError):
            fehler[k] = v
    if werte:
        inv_store.set_settings(werte)
        _changelog("CEO", "Einstellungen geaendert: " + ", ".join(sorted(werte)), "CEO ueber LUNA-OS", "settings")
    return JSONResponse({"ok": not fehler, "gespeichert": sorted(werte), "fehler": fehler,
                         "settings": inv_store.settings()})


@app.get("/api/lagebild")
def lagebild():
    ctx = _ctx_cached()
    ins = ctx.insights if (ctx is not None and getattr(ctx, "insights", None)) else insights_intern
    try:
        return {"daten": ins.daten(), "text": ins.lagebild()}
    except Exception as exc:
        return {"daten": insights_intern.daten(), "text": insights_intern.lagebild(),
                "hinweis": str(exc)[:120]}


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


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Lunas Gesicht als Browser-Icon (auch fuer Aufrufe ohne <link>, z. B. PDF-Ansicht)."""
    return FileResponse(STATIC / "favicon.ico", media_type="image/x-icon")
