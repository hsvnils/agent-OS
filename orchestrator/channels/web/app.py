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
from functools import partial
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from ...core.antraege import Antraege
from ...core.brain import Brain
from ...core.crm import CrmStore
from ...core.content_store import (AIINTEL_FELDER, AIINTEL_RECS, ContentStore, CUTTER_FELDER, CUTTER_STATUSES,
                                   DRAFT_FELDER, DRAFT_STATUSES, IDEA_FELDER, IDEA_STATUSES, SOURCE_FELDER,
                                   TREND_FELDER, TREND_STATUSES)
from ...core.briefing import Agenda
from ...core.insights import Insights
from ...core.notifications import Notifications
from ...core.research_tickets import ResearchTickets
from ...core.team_auth import MODULE, MODUL_LABELS, TeamAuth, erlaubte_apps, hat_modul, modul_fuer_pfad
from ...governance.changelog_tool import append_changelog

ROOT = Path(__file__).resolve().parents[3]
STATIC = Path(__file__).resolve().parent / "static"

_changelog = partial(append_changelog, ROOT / "projekt_changelog.md")
antraege = Antraege(ROOT / "antraege" / "log.jsonl", changelog=_changelog)
notifications = Notifications(ROOT / "notifications" / "log.jsonl")
research = ResearchTickets(ROOT / "research" / "log.jsonl", changelog=_changelog)
agenda = Agenda(ROOT / "agenda" / "log.jsonl")
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
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def state():
    return _state()


@app.get("/api/me")
def me(request: Request):
    """K4: der eingeloggte Nutzer + seine sichtbaren Apps (SSOT fuers Frontend-Gating)."""
    u = getattr(request.state, "user", None) or _ceo_user()
    return {"username": u.get("username"), "display_name": u.get("display_name"),
            "role": u.get("role"), "allowed_modules": u.get("allowed_modules") or [],
            "apps": erlaubte_apps(u)}


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


@app.get("/api/cutter/queue")
def cutter_queue():
    """Vom Mac-Watcher gepollt: offene (queued) Jobs."""
    return {"jobs": [j for j in cutter_store.list(limit=100) if j.get("status") == "queued"]}


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
    if "d" not in _SECRETS_CACHE:
        try:
            from ..telegram.bot import _load_secrets
            _SECRETS_CACHE["d"] = _load_secrets()
        except Exception:
            _SECRETS_CACHE["d"] = {}
    return _SECRETS_CACHE["d"].get(name) or os.environ.get(name, "")


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
