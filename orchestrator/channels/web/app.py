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
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from ...core.antraege import Antraege
from ...core.brain import Brain
from ...core.briefing import Agenda
from ...core.insights import Insights
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
brain = Brain(ROOT / "brain" / "log.jsonl")
# Internes Lagebild (ohne Google); fuer das volle Lagebild (Termine/Mails) nutzt der Endpunkt die LUNA-ctx.
insights_intern = Insights(antraege=antraege, research=research, agenda=agenda)
# Investment (Phase 2, advisory): Engine + Store. MarketData wird lazy aus den .env-Keys gebaut.
from ...investment.store import InvestmentStore
inv_store = InvestmentStore(ROOT / "investment" / "log.jsonl")

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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login nötig",
                            headers={"WWW-Authenticate": "Basic"})


app = FastAPI(title="LUNA-OS", dependencies=[Depends(auth)])


def _md_strip(s: str) -> str:
    """Entfernt Markdown-Schmuck (**, *, #, __) fuer eine saubere Darstellung in LUNA-OS."""
    import re as _re
    s = _re.sub(r"\*\*(.+?)\*\*", r"\1", s or "")
    s = _re.sub(r"__(.+?)__", r"\1", s)
    s = _re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", s)
    return s.replace("**", "").replace("__", "").strip()


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
    return InvestmentEngine(md, inv_store)


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
    }


@app.post("/api/investment/screen")
async def investment_screen():
    eng = _investment_engine()
    r = await asyncio.to_thread(eng.screen_und_vorschlagen)
    return JSONResponse({"ok": True, "erstellt": len(r.get("erstellt", [])),
                         "abgelehnt": len(r.get("vom_risk_abgelehnt", [])),
                         "hinweise": r.get("hinweise", []), "investment": investment()})


@app.get("/api/investment/detail")
async def investment_detail(symbol: str, asset: str = "aktie"):
    eng = _investment_engine()
    return JSONResponse(await asyncio.to_thread(eng.detail, symbol, asset))


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
