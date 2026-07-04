"""Telegram-Bot (Long-Polling): Text- + Sprachnachrichten an den Head of Agents.

Start (nach GATE, Token in orchestrator/.env):
    python -m orchestrator.channels.telegram.bot

Sicherheit: bedient nur die autorisierte Chat-ID (TELEGRAM_ALLOWED_CHAT_ID). Ist keine gesetzt, antwortet
der Bot mit der Chat-ID, damit der CEO sie eintragen kann -- er fuehrt dann NICHTS aus.
"""
from __future__ import annotations

import json
import sys
import time
import tomllib
import urllib.parse
import urllib.request
import uuid
from functools import partial
from pathlib import Path

from ...core.telegram_format import fuer_telegram

ROOT = Path(__file__).resolve().parents[3]
API = "https://api.telegram.org"


def _load_config() -> dict:
    with open(ROOT / "orchestrator" / "config.toml", "rb") as fh:
        return tomllib.load(fh)


def _load_secrets() -> dict:
    env = ROOT / "orchestrator" / ".env"
    out: dict[str, str] = {}
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _build_ctx(cfg: dict, secrets: dict):
    """Live-HoA-Werkzeugkontext (Opus-Backend, Gedaechtnis, Antraege, Execution-Engine)."""
    from ...core.antraege import Antraege
    from ...core.backends import AgentSdkBackend, FallbackBackend
    from ...core.execution import ExecutionEngine
    from ...core import execution_live as live
    from ...core.hoa import HeadOfAgents
    from ...core.hoa_tools import ToolContext
    from ...core.memory import Memory
    from ...core.subagents import load_all_subagents
    from ...governance.ceo_gate_hook import CeoGate
    from ...governance.changelog_tool import append_changelog
    from ...observability.logging import Logger

    from ...governance.leak_guard import is_redactable_secret
    secret_values = [v for v in secrets.values() if is_redactable_secret(v)]
    # Fachagenten-Backend: Claude-CLI mit Gemini/OpenAI-Fallback (greift bei Anthropic-Sperre/Limit).
    backend = FallbackBackend(
        AgentSdkBackend(cfg["models"], cfg["effort"], gate=CeoGate(),
                        max_turns=cfg["run"].get("max_turns", 4)),
        fallbacks=_fallbacks(secrets, cfg))
    # Antrag adc5: zentrales Aktivitaetsprotokoll. Der Changelog-Callback ist die zentrale Engstelle
    # (Antrags-Lebenszyklus, Execution, Charta) -- jeder Changelog-Eintrag wird zusaetzlich strukturiert
    # ins Protokoll geschrieben, ohne jeden Agenten einzeln zu instrumentieren.
    from ...core.aktivitaet import Aktivitaet
    aktivitaet = Aktivitaet(ROOT / "aktivitaet" / "log.jsonl", secrets=secret_values)
    _md_changelog = partial(append_changelog, ROOT / cfg["governance"]["changelog_file"])

    def changelog(actor, was, warum="", betroffen=""):
        _md_changelog(actor, was, warum, betroffen)
        try:
            aktivitaet.log(actor, was, kategorie="governance", detail=warum, bezug=betroffen)
        except Exception:
            pass

    mem_cfg = cfg.get("memory", {})
    memory = Memory(ROOT / mem_cfg.get("path", "orchestrator/memory/log.jsonl"),
                    secrets=secret_values, recall_limit=mem_cfg.get("recall_limit", 5)) \
        if mem_cfg.get("enabled", True) else None
    core = HeadOfAgents(backend, load_all_subagents(), gate=CeoGate(), leak_secrets=secret_values,
                        changelog=changelog, logger=Logger(), memory=memory)
    antraege = Antraege(ROOT / "antraege" / "log.jsonl", secrets=secret_values, changelog=changelog)
    engine = ExecutionEngine(
        antraege, make_workspace=live.real_make_workspace(
            ROOT, snapshot=secrets.get("EXECUTION_AUTO_SNAPSHOT", "").strip() in ("1", "true", "yes")),
        run_agent=live.real_run_agent(model=cfg.get("voice", {}).get("exec_model", "claude-opus-4-8")),
        run_tests=live.real_run_tests(), diff=live.real_diff(),
        secrets=secret_values, changelog=changelog,
    )
    # Phase 8: Web-Research aus denselben .env-Secrets bauen (nicht os.environ -- die App
    # injiziert .env nicht in die Prozess-Umgebung). Ohne Keys -> Fall-B-Hinweis (CEO-Tor).
    from ...governance.web_research import WebResearch
    from ...core.research_tickets import ResearchTickets
    from ...governance.google_workspace import GoogleAuth, GoogleWorkspace
    web = WebResearch.from_env(env=secrets, secrets=secret_values)
    research = ResearchTickets(ROOT / "research" / "log.jsonl", secrets=secret_values, changelog=changelog)
    # Phase 11: Google Workspace aus denselben .env-Secrets. Ohne OAuth-Credentials -> Fall-B (CEO-Tor).
    # GOOGLE_CALENDAR_DEFAULT_ATTENDEE wird bei jedem Termin automatisch eingeladen (z. B. private iCloud).
    google = GoogleWorkspace(GoogleAuth.from_env(env=secrets),
                             standard_einladung=secrets.get("GOOGLE_CALENDAR_DEFAULT_ATTENDEE", ""),
                             zeitzone=secrets.get("GOOGLE_CALENDAR_TIMEZONE", "Europe/Berlin"))
    # Proaktiver Notifier (Outbox) -- LUNA/Watcher melden sich unaufgefordert beim CEO.
    from ...core.notifications import Notifications
    notifications = Notifications(ROOT / "notifications" / "log.jsonl", secrets=secret_values)
    # Phase 23<->21: Web-Recherche meldet Prompt-Injection-Verdacht an CISO/Security (web wurde oben gebaut).
    web.notify = notifications.enqueue
    # Phase 12: 24/7-Watcher (kostenlos). GitHub-Token optional (Rate-Limit); Hintergrund-LLM aus.
    from ...core.scheduler import WatchScheduler, WatchStore
    from ...governance.github_watch import GitHubWatch
    watch = WatchScheduler(WatchStore(ROOT / "watch" / "log.jsonl", secrets=secret_values),
                           github=GitHubWatch(env=secrets), web=web, research=research,
                           notify=notifications.enqueue, google=google, secrets=secret_values)
    # Briefings/Agenda (manuelle Punkte).
    from ...core.briefing import Agenda
    from ...core.kosten import KostenStore
    agenda = Agenda(ROOT / "agenda" / "log.jsonl", secrets=secret_values)
    kosten = KostenStore(ROOT / "finance" / "kosten-log.jsonl", secrets=secret_values)
    # Finance 2.5: Token/Kosten JE AGENT erfassen -- der Backend-Callback bucht Subagenten-Aufrufe
    # (SDK-Pfad + OpenAI-Fallback) mit ihrem agent_key in den KostenStore. Fehler nie durchreichen.
    def _kosten_sink(agent_key, modell, in_tok, out_tok, usd):
        try:
            kosten.record(quelle="agent", agent=agent_key, modell=modell,
                          input_tokens=in_tok, output_tokens=out_tok, kosten_usd=usd)
        except Exception:
            pass
    backend.on_usage = _kosten_sink
    if getattr(backend, "primary", None) is not None:
        backend.primary.on_usage = _kosten_sink
    # Second Brain (Wissensbasis) + proaktive Tages-Insights (Lagebild).
    from ...core.brain import Brain
    from ...core.insights import Insights
    brain = Brain(ROOT / "brain" / "log.jsonl", secrets=secret_values)
    from ...core.trajektorien import TrajektorienStore
    trajektorien = TrajektorienStore(ROOT / "trajektorien" / "log.jsonl", secrets=secret_values)
    from ...core.social_kit import SocialStore
    social = SocialStore(ROOT / "social" / "log.jsonl", secrets=secret_values)
    insights = Insights(antraege=antraege, research=research, agenda=agenda, google=google,
                        secrets=secret_values)
    # Investment-Abteilung (CIO, advisory) -- Marktdaten via Capability, Alerts ueber den Notifier.
    from ...investment.broker import AlpacaPaperBroker
    from ...investment.engine import InvestmentEngine
    from ...investment.providers import MarketData
    from ...investment.store import InvestmentStore
    # GATE C: Paper-Broker (Alpaca). Inert ohne Keys; paper-Modus aktivieren + jede Order = CEO-Tor.
    _paper_broker = AlpacaPaperBroker(secrets.get("ALPACA_API_KEY", ""), secrets.get("ALPACA_API_SECRET", ""))
    investment = InvestmentEngine(
        MarketData(secrets=secrets), InvestmentStore(ROOT / "investment" / "log.jsonl", secrets=secret_values),
        notify=notifications.enqueue, brain=brain.merken, broker=_paper_broker)
    from ...core.crm import CrmStore
    from ...core.crm_projection import SupabaseCrmProjection
    from ...governance.supabase import SupabaseAuth, SupabaseClient
    _sb_auth = SupabaseAuth.from_env(secrets)
    _crm_proj = SupabaseCrmProjection(SupabaseClient(_sb_auth)) if _sb_auth.verfuegbar() else None
    crm = CrmStore(ROOT / "crm" / "log.jsonl", secrets=secret_values, changelog=changelog, projektor=_crm_proj,
                   notify=notifications.enqueue)
    from ...investment.approvals import ApprovalStore
    approvals = ApprovalStore(ROOT / "approvals" / "log.jsonl", secrets=secret_values)
    return ToolContext(core=core, antraege=antraege, engine=engine,
                       finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=secret_values,
                       web=web, research=research, google=google, watch=watch,
                       notifications=notifications, agenda=agenda, secret_dict=secrets,
                       kosten=kosten, aktivitaet=aktivitaet, visuals=[],
                       brain=brain, insights=insights, investment=investment, crm=crm,
                       trajektorien=trajektorien, social=social, approvals=approvals), secret_values


def _api(token: str, method: str, params: dict, timeout: int = 60) -> dict:
    url = f"{API}/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _send_approval(token: str, chat_id, apv: dict) -> dict:
    """Schickt eine Freigabe mit Inline-Keyboard (Ja / Nein / Andere Summe). Klick kommt als callback_query."""
    kb = {"inline_keyboard": [[{"text": "✅ Ja", "callback_data": f"apv:{apv['id']}:yes"},
                               {"text": "❌ Nein", "callback_data": f"apv:{apv['id']}:no"}],
                              [{"text": "✏️ Andere Summe", "callback_data": f"apv:{apv['id']}:amt"}]]}
    return _api(token, "sendMessage", {"chat_id": chat_id, "text": fuer_telegram(apv.get("frage", "Freigabe?")),
                                       "reply_markup": json.dumps(kb)})


def _deliver_approvals(token: str, chat_id, ctx) -> None:
    """Stellt offene, noch nicht gesendete 1-Tap-Freigaben als Buttons zu (sofort, ohne auf den Poll zu warten)."""
    if not chat_id or getattr(ctx, "approvals", None) is None:
        return
    try:
        for a in ctx.approvals.pending_unsent()[:5]:
            if _send_approval(token, chat_id, a).get("ok"):
                ctx.approvals.mark_sent(a["id"])
    except Exception as exc:
        print(f"[approval] Zustell-Fehler: {exc}", flush=True)


def _parse_betrag(text: str) -> float:
    """Zieht einen USD-Betrag aus einer Nachricht (z. B. '50', '50 USD', '50,5')."""
    import re
    m = re.search(r"(\d+(?:[.,]\d+)?)", text or "")
    return float(m.group(1).replace(",", ".")) if m else 0.0


def _neue_paper_freigabe(ctx, eng, params: dict, betrag_usd: float):
    """Legt eine neue Paper-Order-Freigabe fuer einen USD-Betrag an (Kurs frisch geholt). -> Freigabe-ID | None."""
    symbol = params.get("symbol")
    asset = params.get("asset", "aktie")
    side = params.get("side", "buy")
    preis_vorgabe = None
    if asset == "krypto":
        alp, usd = eng.krypto_usd(symbol)
        if not alp or usd <= 0:
            return None
        symbol, preis_vorgabe = alp, usd
    preis = _autonomie_f(preis_vorgabe if preis_vorgabe is not None else (eng._aktueller_preis(symbol, asset) or 0))
    if preis <= 0:
        return None
    qty = round(betrag_usd / preis, 6)
    if qty <= 0:
        return None
    frage = f"Paper-{'Kauf' if side == 'buy' else 'Verkauf'}: {qty:g} {symbol} (~{round(betrag_usd, 2)} USD). Ausfuehren?"
    payload = {"symbol": symbol, "qty": qty, "side": side, "asset": asset}
    if preis_vorgabe is not None:
        payload["preis"] = preis_vorgabe
    return ctx.approvals.add("paper_order", payload, frage=frage)


def _approval_ausfuehren(ctx, apv: dict) -> str:
    """Fuehrt die bei 'Ja' hinterlegte Aktion aus und liefert eine kurze Ergebnis-Zeile."""
    typ = apv.get("typ")
    p = apv.get("payload") or {}
    if typ == "paper_order":
        eng = getattr(ctx, "investment", None)
        if eng is None:
            return "Investment-Abteilung nicht verfuegbar."
        r = eng.paper_order(p.get("symbol", ""), p.get("qty", 0), p.get("side", "buy"),
                            asset=p.get("asset", "aktie"), bestaetigt=True, preis=p.get("preis"))
        if r.get("ok"):
            return f"Paper-Order platziert: {p.get('side')} {p.get('qty'):g} {p.get('symbol')} (~{r.get('geschaetzter_wert')} USD)."
        return "Order nicht ausgefuehrt: " + str(r.get("grund") or r.get("hinweis") or "unbekannt")
    return "Unbekannter Freigabe-Typ."


def _send_document(token: str, chat_id, dateiname: str, inhalt: bytes, caption: str = "") -> dict:
    """Sendet eine Datei (z. B. SVG-Visualisierung, Phase 14) per multipart/form-data."""
    boundary = "----luna" + uuid.uuid4().hex
    parts: list[bytes] = []

    def feld(name: str, wert: str):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                     f"{wert}\r\n".encode())

    feld("chat_id", str(chat_id))
    if caption:
        feld("caption", caption[:1000])
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
                  f"filename=\"{dateiname}\"\r\nContent-Type: image/svg+xml\r\n\r\n").encode())
    parts.append(inhalt if isinstance(inhalt, bytes) else str(inhalt).encode())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(f"{API}/bot{token}/sendDocument", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _download_voice(token: str, file_id: str) -> bytes | None:
    info = _api(token, "getFile", {"file_id": file_id}, timeout=30)
    path = (info.get("result") or {}).get("file_path")
    if not path:
        return None
    try:
        with urllib.request.urlopen(f"{API}/file/bot{token}/{path}", timeout=30) as r:
            return r.read()
    except Exception:
        return None


def _transcribe(audio: bytes, deepgram_key: str, language: str = "de") -> str:
    url = f"https://api.deepgram.com/v1/listen?model=nova-2&language={language}&smart_format=true"
    req = urllib.request.Request(url, data=audio, method="POST",
                                 headers={"Authorization": f"Token {deepgram_key}",
                                          "Content-Type": "audio/ogg"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        return d["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as exc:
        return f"[Transkription fehlgeschlagen: {exc}]"


def _start_watch_loop(watch, interval_hours: float, *, maintenance=None, notify=None) -> None:
    """Phase 12: kostenloser 24/7-Hintergrund-Tick (GitHub jeden Lauf; Fachbereiche rundenweise) +
    IT-Self-Maintenance-Check je Lauf.

    Daemon-Thread -- macht NUR freie Datenarbeit (keine Token). Fehler werden geloggt UND proaktiv gemeldet.
    """
    import itertools
    import threading
    import time

    from ...core.watch_config import DEPARTMENT_WATCH
    if watch is None:
        return
    depts = list(DEPARTMENT_WATCH.keys())

    def loop():
        rot = itertools.cycle(depts) if depts else None
        time.sleep(20)  # Start nicht blockieren
        while True:
            try:
                if not watch.store.paused():         # Notbremse respektieren
                    watch.github_tick()              # kostenlos (GitHub-API)
                    if rot is not None:
                        watch.dept_tick(next(rot))    # je Tick EINE Abteilung -> Brave-Gratis-Quota schonen
                if maintenance is not None:           # IT-Healthcheck (kostenlos) -- meldet Probleme selbst
                    maintenance.lauf()
            except Exception as exc:                 # nie den Bot mitreissen -- aber proaktiv melden
                print(f"[watch] Tick-Fehler: {exc}", flush=True)
                if notify is not None:
                    try:
                        notify(f"Fehler im Hintergrund-Loop: {str(exc)[:200]}",
                               abteilung="IT/Self-Maintenance", kategorie="fehler", quelle="watch-loop")
                    except Exception:
                        pass
            time.sleep(max(0.1, interval_hours) * 3600)

    threading.Thread(target=loop, daemon=True, name="watch-loop").start()


def _start_selfdev_loop(ctx, secrets) -> None:
    """Geplanter Selbst-Entwicklungs-Loop: 1x taeglich 09:00 (DE) EIN Bereich -> Antrag -> Freigabe-Push.

    Nur aktiv mit SELF_DEV_ENABLED=1 (CEO-Freigabe der laufenden Token-Kosten); respektiert die Notbremse.
    """
    import itertools
    import threading
    import time
    from datetime import datetime

    if (secrets.get("SELF_DEV_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on")
            or ctx.watch is None):
        return
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None
    from ...core.self_development import SelfDevelopment
    from ...core.watch_config import DEPARTMENT_WATCH
    sd = SelfDevelopment(ctx.core, web=ctx.web, watch=ctx.watch, antraege=ctx.antraege,
                         notify=ctx.notifications.enqueue, secrets=ctx.leak_secrets, enabled=True)
    depts = itertools.cycle(list(DEPARTMENT_WATCH.keys()))

    def loop():
        time.sleep(45)
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                if jetzt.hour == 9 and not ctx.agenda.briefing_gesendet("selfdev", datum) \
                        and not ctx.watch.store.paused():
                    # Abwechselnd: gerade Tage = interne Luecken-/Mandatsanalyse (proaktive Vorschlaege aus
                    # dem System), ungerade = externe Web-Entwicklungen.
                    modus = "intern" if jetzt.day % 2 == 0 else "extern"
                    sd.vorschlag_fuer(next(depts), modus=modus)   # erzeugt Antrag + Freigabe-Push
                    ctx.agenda.markiere_briefing("selfdev", datum)
            except Exception as exc:
                print(f"[selfdev] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="selfdev-loop").start()


def _start_security_loop(ctx, secrets) -> None:
    """Phase 21: taeglicher Sicherheits-Audit (CISO-Ausbau) -- 1x taeglich 04:00 (DE), L1 (nur melden).

    Kostenlos/regelbasiert (kein LLM). Nur aktiv mit SECURITY_AUDIT_ENABLED=1; respektiert die Notbremse.
    Keine autonome Aenderung -- Befunde gehen als Meldung an den CEO (Antrag nur on-demand ueber das Tool).
    """
    import subprocess
    import threading
    import time
    from datetime import datetime

    if secrets.get("SECURITY_AUDIT_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on") \
            or ctx.agenda is None:
        return
    from ...core.security_agent import SecurityAgent
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None

    def _run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd=str(ROOT)).stdout
        except Exception:
            return ""

    def loop():
        time.sleep(90)
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                if jetzt.hour == 4 and not ctx.agenda.briefing_gesendet("security-audit", datum) \
                        and (ctx.watch is None or not ctx.watch.store.paused()):
                    SecurityAgent(repo_root=ROOT, env=secrets, secrets=ctx.leak_secrets, run=_run,
                                  notify=ctx.notifications.enqueue).lauf(als_antrag=False)
                    ctx.agenda.markiere_briefing("security-audit", datum)
            except Exception as exc:
                print(f"[security] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="security-loop").start()


def _start_content_feed_loop(ctx, secrets) -> None:
    """K3: geplanter Content-Feed-Loop -- 1x taeglich 07:00 (DE) volle Pipeline Trends->Ideen->Drafts.

    Trends kostenlos (Brave); Ideen/Drafts ueber den Content-Fachagenten (LLM, guenstiges Modell). Alles
    landet als Kandidat mit Review-Status in Supabase -> LUNA-OS (Trends/Ideen/Drafts) fuers Team. Autonomie
    L1/L2 (nur Kandidaten + melden; kein Auto-Publish, Oeffentlichkeit = CEO-Tor). Nur aktiv mit
    CONTENT_FEED_ENABLED=1; respektiert die Notbremse.
    """
    import threading
    import time
    from datetime import datetime

    if (secrets.get("CONTENT_FEED_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on")):
        return
    from ...governance.supabase import SupabaseAuth, SupabaseClient
    from ...core.hoa_tools import _content_feed
    sb = SupabaseClient(SupabaseAuth.from_env(secrets))
    if not sb.verfuegbar() or ctx.agenda is None:
        return
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None
    feed = _content_feed(ctx, sb, ctx.leak_secrets)

    def loop():
        time.sleep(60)
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                if jetzt.hour == 7 and not ctx.agenda.briefing_gesendet("content-feed", datum):
                    feed.pipeline_lauf(max_pro_stufe=5)   # pausen-bewusst; meldet neue Kandidaten je Stufe
                    ctx.agenda.markiere_briefing("content-feed", datum)
            except Exception as exc:
                print(f"[content-feed] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="content-feed-loop").start()


def _start_briefing_loop(ctx, notify) -> None:
    """Morgen-Briefing 08:00 + Abend-Briefing 20:00 (Europe/Berlin). Token-frugal (regelbasiert)."""
    import threading
    import time
    from datetime import datetime

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None  # ohne tzdata: Serverzeit (im Container besser tzdata installieren)
    if ctx.agenda is None or notify is None:
        return
    from ...core.briefing import Briefing

    plan = {8: "morgen", 20: "abend"}

    def loop():
        time.sleep(30)
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                art = plan.get(jetzt.hour)
                if art and not ctx.agenda.briefing_gesendet(art, datum):
                    text = Briefing(antraege=ctx.antraege, research=ctx.research, watch=ctx.watch,
                                    agenda=ctx.agenda, secrets=ctx.leak_secrets).erstellen(
                                        art, jetzt=jetzt.replace(tzinfo=None) if tz else jetzt)
                    # Proaktive Tages-Insights ans Morgen-Briefing anhaengen (Lagebild: Termine/Mails/Entsch.).
                    if art == "morgen" and ctx.insights is not None:
                        try:
                            text += "\n\n" + ctx.insights.lagebild(
                                jetzt=jetzt.replace(tzinfo=None) if tz else jetzt)
                        except Exception as exc:
                            print(f"[briefing] Lagebild-Fehler: {exc}", flush=True)
                    notify(text, abteilung="LUNA-Briefing", kategorie="briefing", quelle="briefing",
                           dedup_stunden=0)
                    ctx.agenda.markiere_briefing(art, datum)
            except Exception as exc:
                print(f"[briefing] Fehler: {exc}", flush=True)
            time.sleep(300)  # alle 5 min pruefen

    threading.Thread(target=loop, daemon=True, name="briefing-loop").start()


def _autonomie_f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _autonomie_kontext(eng, forecaster, watch, datum: str) -> dict:
    """Baut den Live-Kontext fuer die Autonomie-Leitplanken (Paper): Equity, Tagesverlust, Kill-Switch,
    genutztes Nacht-Budget + heutige Trades, Track-Record-Freischaltung."""
    konto = (eng.paper_konto() or {}).get("konto") or {}
    equity = _autonomie_f(konto.get("equity"))
    last = _autonomie_f(konto.get("last_equity")) or equity
    tagesverlust = round((1 - equity / last) * 100, 2) if last > 0 else 0.0   # positiv = Verlust
    heute = [p for p in eng.store.list("positions")
             if p.get("modus") == "paper" and p.get("status") == "platziert" and p.get("ts", "")[:10] == datum]
    k = forecaster.kennzahlen().get("gesamt", {})
    freigeschaltet = k.get("n", 0) >= 20 and _autonomie_f(k.get("richtungsquote")) >= 0.55
    return {"equity": equity, "tagesverlust_pct": tagesverlust,
            "kill_switch": bool(watch and watch.store.paused()),
            "nacht_budget_genutzt": round(sum(_autonomie_f(p.get("order_wert")) for p in heute), 2),
            "trades_im_fenster": len(heute), "autonomie_freigeschaltet": freigeschaltet}


def _auto_trade_tick(ctx, eng, forecaster, auto_trader, datum: str) -> None:
    """Ein Auto-Trade-Durchlauf (nur Paper): Top-Chance dimensionieren -> Leitplanken -> autonom / Freigabe."""
    lp = auto_trader.policy.lp
    kontext = _autonomie_kontext(eng, forecaster, ctx.watch, datum)
    chancen = [c for c in forecaster.chancen([], min_konfidenz=lp.min_konfidenz)
               if c.get("asset") in ("aktie", "etf")][:1]   # USD-Werte; Krypto (EUR-Quelle) hier bewusst aussen vor
    for c in chancen:
        preis = eng._aktueller_preis(c["symbol"], c["asset"])
        if not preis or preis <= 0:
            continue
        betrag = round(min(lp.max_position_eur, kontext["equity"] * lp.max_position_pct / 100.0), 2)
        qty = round(betrag / preis, 4)
        if qty <= 0:
            continue
        trade = {"symbol": c["symbol"], "asset": c["asset"], "side": "buy", "betrag_eur": betrag,
                 "konfidenz": c["konfidenz"], "signale": c.get("signale_zahl", 0), "risiko_label": "konservativ"}
        d = auto_trader.entscheide(trade, kontext)
        if d["aktion"] == "auto":
            r = eng.paper_order(c["symbol"], qty, "buy", asset=c["asset"], bestaetigt=True)
            if ctx.notifications:
                ok = r.get("ok")
                ctx.notifications.enqueue(
                    f"Autonome Paper-Order: buy {qty:g} {c['symbol']} (~{betrag} USD) — "
                    f"{'platziert' if ok else 'abgelehnt: ' + str(r.get('grund') or r.get('hinweis'))}.",
                    abteilung="CIO", kategorie="investment", quelle="auto-trade", dedup_stunden=0)
        elif d["aktion"] == "freigabe" and ctx.approvals is not None:
            gruende = "; ".join(d["urteil"]["gruende"][:2]) or "Freigabe noetig"
            frage = (f"Paper-Kauf: {qty:g} {c['symbol']} (~{betrag} USD, Konf. {round(c['konfidenz'] * 100)}%, "
                     f"{c.get('signale_zahl', 0)} Signale). {gruende}. Ausfuehren?")
            ctx.approvals.add("paper_order", {"symbol": c["symbol"], "qty": qty, "side": "buy",
                                              "asset": c["asset"]}, frage=frage)
        # aktion == "skip" -> globaler Schutzschalter -> nichts tun


def _auto_trade_krypto_tick(ctx, eng, forecaster, datum: str) -> None:
    """Nacht-Durchlauf KRYPTO (24/7, Paper): handelt NUR die seltene Top-Chance (strenger Nacht-Filter) in
    winziger Summe. Enge Nacht-Leitplanke -> autonom NACH Track-Record, davor 1-Tap-Freigabe. Die meisten
    Naechte passiert nichts. Downside aktuell nur durch den Mini-Einsatz begrenzt (Stop-Loss noch nicht als
    Order platziert)."""
    from ...investment.autonomy_policy import AutonomyPolicy, Leitplanken
    from ...investment.auto_trader import AutoTrader, ist_nacht_chance
    from ...investment.broker import alpaca_krypto_symbol
    lp = Leitplanken.nacht_krypto()
    trader = AutoTrader(AutonomyPolicy(lp=lp, whitelist=set()))
    kontext = _autonomie_kontext(eng, forecaster, ctx.watch, datum)
    # Top-Krypto-Chance -> nur wenn sie den strengen Filter besteht (hohe Konfidenz, alle Signale einig, hohes Ziel)
    chancen = [c for c in forecaster.chancen([], min_konfidenz=lp.min_konfidenz)
               if c.get("asset") == "krypto"
               and ist_nacht_chance(c, min_konfidenz=lp.min_konfidenz, min_signale=lp.min_signale)]
    if not chancen:
        return                                               # keine wuerdige Chance -> nichts tun (Normalfall)
    c = chancen[0]
    alp = alpaca_krypto_symbol(c["symbol"])
    if not alp:                                              # bei Alpaca nicht handelbar
        return
    usd = eng.market.crypto_preis([c["symbol"]], vs="usd")
    preis = _autonomie_f((usd.get("preise", {}).get(c["symbol"]) or {}).get("usd")) if usd.get("ok") else 0.0
    if preis <= 0:
        return
    betrag = round(min(lp.max_position_eur, kontext["equity"] * lp.max_position_pct / 100.0), 2)
    qty = round(betrag / preis, 6)
    if qty <= 0:
        return
    trade = {"symbol": alp, "asset": "krypto", "side": "buy", "betrag_eur": betrag,
             "konfidenz": c["konfidenz"], "signale": c.get("signale_zahl", 0), "risiko_label": "spekulativ"}
    d = trader.entscheide(trade, kontext)
    if d["aktion"] == "auto":
        r = eng.paper_order(alp, qty, "buy", asset="krypto", bestaetigt=True, preis=preis)
        if ctx.notifications:
            ctx.notifications.enqueue(
                f"Autonome Nacht-Krypto-Order: buy {qty:g} {alp} (~{betrag} USD, Konf. "
                f"{round(c['konfidenz'] * 100)}%, Ziel {c.get('ziel_return_pct'):+.1f}%) — "
                f"{'platziert' if r.get('ok') else 'abgelehnt'}.",
                abteilung="CIO", kategorie="investment", quelle="auto-trade", dedup_stunden=0)
    elif d["aktion"] == "freigabe" and ctx.approvals is not None:
        frage = (f"Nacht-Top-Chance (Krypto, Paper): {qty:g} {alp} (~{betrag} USD, Konf. "
                 f"{round(c['konfidenz'] * 100)}%, {c.get('signale_zahl', 0)} Signale, Ziel "
                 f"{c.get('ziel_return_pct'):+.1f}%). Autonom erst nach Track-Record. Ausfuehren?")
        ctx.approvals.add("paper_order", {"symbol": alp, "qty": qty, "side": "buy", "asset": "krypto",
                                          "preis": preis}, frage=frage)


def _positionen_index(eng) -> dict:
    """Offene Paper-Positionen -> {normalisiertes Symbol: {order_symbol, qty, asset}}.
    Schluessel: Ticker (Aktie) bzw. Basis (Krypto, z. B. 'BTC') -- damit Live-Kandidaten zugeordnet werden koennen."""
    from ...investment.monitor import krypto_order_symbol
    idx: dict = {}
    broker = getattr(eng, "broker", None)
    if broker is None or not broker.verfuegbar:
        return idx
    for p in broker.positionen():
        asset = "krypto" if p.get("asset_class") == "crypto" else "aktie"
        sym = p.get("symbol") or ""
        if asset == "krypto":
            order_sym = krypto_order_symbol(sym)      # BTCUSD -> BTC/USD
            key = order_sym.split("/")[0]             # BTC
        else:
            order_sym = sym.upper()
            key = order_sym
        idx[key] = {"order_symbol": order_sym, "qty": _autonomie_f(p.get("qty")), "asset": asset}
    return idx


def _market_monitor_tick(ctx, eng, monitor, betrag_usd: float = 30.0) -> None:
    """Positions-BEWUSSTER Monitor (nur Paper): Live-Kurse Watchlist+Universum -> auffaellige Bewegungen.
    Nicht im Depot + Dip -> Kauf-Vorschlag. Im Depot + scharfer Abfall -> SCHUTZ-Verkauf-Vorschlag (kein
    Nachkauf!). Anstieg -> Info-Alert (das +15%-Take-Profit macht der Exit-Monitor). Alles per 1-Tap-Freigabe."""
    from ...investment.broker import alpaca_krypto_symbol
    from ...investment.universe import panel
    if ctx.approvals is None:
        return
    quotes: dict = {}
    krypto_ids: list = []
    for w in panel(eng.store.watchlist()):
        sym, asset = w.get("symbol"), w.get("asset", "aktie")
        if asset == "krypto":
            krypto_ids.append(sym)
            continue
        q = eng.market.aktie_quote(sym)
        if q.get("ok") and _autonomie_f(q.get("preis")) > 0:
            quotes[sym] = {"preis": _autonomie_f(q.get("preis")), "asset": asset}
    if krypto_ids:
        r = eng.market.crypto_preis(krypto_ids, vs="usd")
        for cid, v in (r.get("preise") or {}).items() if r.get("ok") else []:
            p = _autonomie_f(v.get("usd"))
            if p > 0:
                quotes[cid] = {"preis": p, "asset": "krypto"}
    idx = _positionen_index(eng)
    offene = ctx.approvals.offen()
    offene_sells = {(a.get("payload") or {}).get("symbol") for a in offene if (a.get("payload") or {}).get("side") == "sell"}
    offene_buys = {(a.get("payload") or {}).get("symbol") for a in offene if (a.get("payload") or {}).get("side") == "buy"}
    for c in monitor.beobachte(quotes)[:3]:
        asset, preis = c["asset"], c["preis"]
        if asset == "krypto":
            order_sym = alpaca_krypto_symbol(c["symbol"])
            if not order_sym:
                continue
            key = order_sym.split("/")[0]
        else:
            order_sym = (c["symbol"] or "").upper()
            key = order_sym
        held = idx.get(key)
        if c["richtung"] == "faellt":
            if held:                                          # halten wir -> Schutz-Verkauf statt Nachkauf
                if order_sym in offene_sells or held["qty"] <= 0:
                    continue
                frage = (f"Live-Abfall: {c['symbol']} faellt {c['move_pct']:+.1f}% (kurzfristig) — du haeltst es. "
                         f"Position schuetzen? Verkauf {held['qty']:g} {order_sym} (Paper)?")
                ctx.approvals.add("paper_order", {"symbol": order_sym, "qty": held["qty"], "side": "sell",
                                                  "asset": asset, "preis": preis}, frage=frage)
            else:                                             # nicht im Depot -> Kauf-Chance
                if order_sym in offene_buys:
                    continue
                qty = round(betrag_usd / preis, 6)
                if qty <= 0:
                    continue
                frage = (f"Live-Dip: {c['symbol']} faellt {c['move_pct']:+.1f}% (kurzfristig). Kauf-Chance im "
                         f"Paper? {qty:g} {order_sym} (~{betrag_usd:g} USD). Ausfuehren?")
                ctx.approvals.add("paper_order", {"symbol": order_sym, "qty": qty, "side": "buy",
                                                  "asset": asset, "preis": preis}, frage=frage)
        elif ctx.notifications is not None:                   # steigt -> Info (Take-Profit macht der Exit-Monitor)
            zusatz = " — im Depot" if held else ""
            ctx.notifications.enqueue(
                f"Live-Bewegung: {c['symbol']} {c['move_pct']:+.1f}% in kurzer Zeit{zusatz}.",
                abteilung="CIO", kategorie="investment", quelle="monitor", dedup_stunden=1)


def _exit_monitor_tick(ctx, eng, *, stop_pct: float = 8.0, target_pct: float = 15.0) -> None:
    """Ueberwacht offene Paper-Positionen: -stop_pct -> AUTOMATISCHER Verkauf (Stop-Loss, Kapitalschutz);
    +target_pct -> 'Gewinn mitnehmen?'-Vorschlag per 1-Tap-Freigabe. Der automatische Stop laeuft auch bei
    aktiver Notbremse (Risiko schliessen ist immer erlaubt)."""
    broker = getattr(eng, "broker", None)
    if broker is None or not broker.verfuegbar:
        return
    from ...investment.monitor import exit_signal, krypto_order_symbol
    offene_sells = {(a.get("payload") or {}).get("symbol") for a in ctx.approvals.offen()
                    if ctx.approvals is not None and (a.get("payload") or {}).get("side") == "sell"}
    for p in broker.positionen():
        sig = exit_signal(p.get("unrealized_plpc"), stop_pct=stop_pct, target_pct=target_pct)
        if not sig:
            continue
        qty = _autonomie_f(p.get("qty"))
        if qty <= 0:
            continue
        asset = "krypto" if p.get("asset_class") == "crypto" else "aktie"
        sym = krypto_order_symbol(p.get("symbol")) if asset == "krypto" else (p.get("symbol") or "")
        preis = _autonomie_f(p.get("current_price")) or None
        plpc = round(_autonomie_f(p.get("unrealized_plpc")) * 100, 1)
        if sig == "stop":                                    # Stop-Loss -> automatisch verkaufen
            r = eng.paper_order(sym, qty, "sell", asset=asset, bestaetigt=True, preis=preis)
            if ctx.notifications:
                ctx.notifications.enqueue(
                    f"Auto-Stop-Loss: {qty:g} {sym} bei {plpc:+.1f}% verkauft — "
                    f"{'ok' if r.get('ok') else 'Fehler: ' + str(r.get('grund') or r.get('hinweis'))}.",
                    abteilung="CIO", kategorie="investment", quelle="exit", dedup_stunden=0)
        elif sig == "target" and ctx.approvals is not None and sym not in offene_sells:   # Take-Profit -> vorschlagen
            frage = (f"Gewinn mitnehmen? {p.get('symbol')} steht bei {plpc:+.1f}%. "
                     f"Verkauf {qty:g} {sym} (Paper)?")
            ctx.approvals.add("paper_order", {"symbol": sym, "qty": qty, "side": "sell", "asset": asset,
                                              "preis": preis}, frage=frage)


def _start_investment_loop(ctx, secrets) -> None:
    """Automatischer Investment-Screen (advisory, token-frugal/kostenlos): werktags 16:00 DE ein Markt-Screen
    -> Vorschlaege (jeder vom Risk-Agent geprueft) -> Alerts ueber den Notifier; montags 09:00 Wochenprognose.

    Zusaetzlich (Walk-Forward-Lern-Loop, Schritt 1): taeglich ~07:00 ein **Merkmals-/Preis-Snapshot** der
    Watchlist + Benchmarks (SPY/BTC) in den `LoopStore` (lokal + Supabase). Baut unsere eigene Kurs-Historie
    auf -- Grundlage fuer 7-Tage-Prognose, Abgleich und das getrennte Abweichungs-Register.

    Standardmaessig AUS. Aktivierung: INVESTMENT_AUTO_SCREEN=1 (Screen/Prognose) bzw. INV_FEATURE_LOOP=1
    (Merkmals-Sammler). Autonomie-Stufe L1: nur Lesen/Melden, keine Trades, kein Geld.
    """
    import threading
    import time
    from datetime import datetime

    eng = getattr(ctx, "investment", None)
    if eng is None:
        return
    auto_screen = secrets.get("INVESTMENT_AUTO_SCREEN", "").strip().lower() in ("1", "true", "yes", "on")
    feature_loop = secrets.get("INV_FEATURE_LOOP", "").strip().lower() in ("1", "true", "yes", "on")
    monitor_an = secrets.get("INV_MONITOR", "").strip().lower() in ("1", "true", "yes", "on")
    if not (auto_screen or feature_loop or monitor_an):
        return
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None

    def _letztes_datum(tabelle):
        items = eng.store.list(tabelle)
        return (items[-1].get("ts", "")[:10]) if items else ""

    collector = None
    forecaster = None
    auto_trader = None
    if feature_loop:
        from ...governance.supabase import SupabaseAuth, SupabaseClient
        from ...investment.auto_trader import AutoTrader
        from ...investment.features import FeatureCollector
        from ...investment.forecaster import Forecaster
        from ...investment.loop_store import LoopStore
        _auth = SupabaseAuth.from_env(secrets)
        _sb = SupabaseClient(_auth) if _auth.verfuegbar() else None
        _leak = [v for v in secrets.values() if isinstance(v, str) and v]
        _loop_store = LoopStore(ROOT / "investment" / "features.jsonl", supabase=_sb, secrets=_leak)
        collector = FeatureCollector(eng.market, _loop_store)
        forecaster = Forecaster(_loop_store)
        auto_trader = AutoTrader()
    # Autonomer Paper-Trader: standardmaessig AUS; nur Paper; autonom erst nach Track-Record-Freischaltung.
    auto_trade_an = secrets.get("INV_AUTO_TRADE", "").strip().lower() in ("1", "true", "yes", "on")
    # Intraday-Markt-Monitor: standardmaessig AUS; alle ~10 Min Live-Kurse -> Dip-Vorschlaege per Freigabe.
    monitor = None
    if monitor_an:
        from ...investment.monitor import MarketMonitor
        monitor = MarketMonitor()

    def loop():
        time.sleep(45)
        _autotrade_datum = ""
        _autotrade_krypto_datum = ""
        _last_monitor = 0.0
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                # Alle ~10 Min (nur Paper): Positions-Schutz (Stop-Loss/Take-Profit) IMMER; Live-Dip-Monitor optional
                if eng.store.mode() == "paper" and time.time() - _last_monitor > 600:
                    _last_monitor = time.time()
                    _exit_monitor_tick(ctx, eng)             # Kapitalschutz: Auto-Stop-Loss + Take-Profit-Vorschlag
                    if monitor is not None:
                        _market_monitor_tick(ctx, eng, monitor)
                # Taeglicher Merkmals-/Preis-Snapshot (~07:00) + Abgleich faelliger Prognosen, 1x/Tag
                if collector is not None and jetzt.hour == 7 and collector.store.last_datum("inv_features") != datum:
                    r = collector.collect(eng.store.watchlist(), datum=datum)
                    ctx.notifications.enqueue(
                        f"Merkmals-Snapshot: {len(r['gesammelt'])} Werte erfasst ({datum}), "
                        f"{len(r['uebersprungen'])} bereits vorhanden.",
                        abteilung="CIO", kategorie="investment", quelle="feature-loop", dedup_stunden=0)
                    a = forecaster.auswerten(heute=datum)   # 7-Tage-Prognosen gegen die Realitaet abgleichen
                    if a["neu_bewertet"]:
                        k = a["kennzahlen"].get("gesamt", {})
                        ctx.notifications.enqueue(
                            f"Prognose-Abgleich: {a['neu_bewertet']} ausgewertet. "
                            f"Fehler (MAE) {k.get('mae_pct')}% vs. Baseline {k.get('baseline_mae_pct')}%, "
                            f"Richtungsquote {round((k.get('richtungsquote') or 0) * 100)}%.",
                            abteilung="CIO", kategorie="investment", quelle="loop-abgleich", dedup_stunden=0)
                # Woechentliche 7-Tage-Prognose (Mo ~09:00), 1x/Tag -- Watchlist + Discovery-Universum
                if forecaster is not None and jetzt.weekday() == 0 and jetzt.hour == 9:
                    _fc = forecaster.store.list("inv_forecasts")
                    if (_fc[-1].get("erstellt_am") if _fc else "") != datum:
                        from ...investment.universe import panel
                        wl = eng.store.watchlist()
                        p = forecaster.prognostizieren(panel(wl), datum=datum)
                        ctx.notifications.enqueue(
                            f"7-Tage-Prognose erstellt: {len(p['erstellt'])} Werte "
                            f"(Modell {forecaster.MODELL_VERSION}, faellig {p['faellig_am']}).",
                            abteilung="CIO", kategorie="investment", quelle="loop-prognose", dedup_stunden=0)
                        # Chancen AUSSERHALB der Watchlist -> je durch den Risk-Agent (engine.vorschlag) -> Alert
                        for ch in forecaster.chancen([w.get("symbol") for w in wl], max_n=3):
                            try:
                                eng.vorschlag(
                                    ch["symbol"], aktion="beobachten",
                                    grund=f"7-Tage-Prognose steigt {ch['ziel_return_pct']:+.1f}% (nicht auf Watchlist)",
                                    asset=ch["asset"], veraenderung_pct=ch["ziel_return_pct"],
                                    konfidenz=ch["konfidenz"], quellen=["7-Tage-Prognose " + forecaster.MODELL_VERSION])
                            except Exception as exc:
                                print(f"[investment] Chancen-Vorschlag-Fehler: {exc}", flush=True)
                # Taeglicher Markt-Screen (werktags ~16:00), 1x/Tag
                if auto_screen and jetzt.weekday() < 5 and jetzt.hour == 16 and _letztes_datum("screening") != datum:
                    r = eng.screen_und_vorschlagen(max_vorschlaege=3)
                    n = len(r.get("erstellt", []))
                    ctx.notifications.enqueue(
                        f"Markt-Screen erledigt: {n} neue Vorschläge (Risk-geprüft), "
                        f"{len(r.get('vom_risk_abgelehnt', []))} vom Risk-Agent abgelehnt. Modus: advisory.",
                        abteilung="CIO", kategorie="investment")
                    try:
                        eng.scorecard_aktualisieren()  # faellige Wochenprognosen auswerten (Track-Record)
                    except Exception as exc:
                        print(f"[investment] Scorecard-Fehler: {exc}", flush=True)
                # Wochenprognose montags ~09:00, 1x/Tag
                if auto_screen and jetzt.weekday() == 0 and jetzt.hour == 9 and _letztes_datum("forecasts") != datum:
                    eng.wochenprognose()
                # Autonomer Paper-Trade Aktien/ETF (werktags ~15:00), 1x/Tag -- nur Paper, AUS by default
                if auto_trade_an and auto_trader is not None and forecaster is not None \
                        and jetzt.weekday() < 5 and jetzt.hour == 15 and _autotrade_datum != datum \
                        and eng.store.mode() == "paper":
                    _autotrade_datum = datum
                    _auto_trade_tick(ctx, eng, forecaster, auto_trader, datum)
                # Nacht-Krypto (24/7, ~02:00), 1x/Nacht -- nur Paper; Krypto=spekulativ -> Freigabe-Buttons
                if auto_trade_an and auto_trader is not None and forecaster is not None \
                        and jetzt.hour == 2 and _autotrade_krypto_datum != datum \
                        and eng.store.mode() == "paper":
                    _autotrade_krypto_datum = datum
                    _auto_trade_krypto_tick(ctx, eng, forecaster, datum)
            except Exception as exc:
                print(f"[investment] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="investment-loop").start()
    aktive = []
    if auto_screen:
        aktive.append("werktags 16:00 Markt-Screen + Mo 09:00 Wochenprognose")
    if feature_loop:
        aktive.append("taeglich 07:00 Merkmals-Snapshot + Prognose-Abgleich, Mo 09:00 7-Tage-Prognose")
    if auto_trade_an:
        aktive.append("werktags 15:00 Auto-Paper-Trade Aktien/ETF + 02:00 Nacht-Krypto (Leitplanken; autonom "
                      "erst nach Track-Record, sonst Freigabe)")
    if monitor_an:
        aktive.append("Intraday-Monitor alle ~10 Min (Live-Dips -> Freigabe-Vorschlaege)")
    print("Investment-Loop aktiv (" + "; ".join(aktive) + ").", flush=True)


def _start_cfo_loop(ctx, notify) -> None:
    """CFO-Kostenpruefung 1x taeglich nachts (03:00 DE): Freeware-/Abo-/Token-Sparpotenziale -> Push.

    Ein LLM-Lauf/Tag (token-frugal). Manuell jederzeit ueber 'kosten_optimierung'. Respektiert die Notbremse.
    """
    import threading
    import time
    from datetime import datetime

    from ...core.hoa_tools import run_tool
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = None
    if ctx.agenda is None or notify is None:
        return

    def loop():
        time.sleep(60)
        while True:
            try:
                jetzt = datetime.now(tz) if tz else datetime.now()
                datum = jetzt.strftime("%Y-%m-%d")
                paused = ctx.watch is not None and ctx.watch.store.paused()
                if jetzt.hour == 3 and not ctx.agenda.briefing_gesendet("cfo-kosten", datum) and not paused:
                    res = run_tool("kosten_optimierung", {}, ctx)
                    stat = ctx.kosten.monat() if ctx.kosten is not None else {}
                    kopf = (f"Laufende Modellkosten {stat.get('monat', '')}: ca. {stat.get('gesamt_eur', 0)} EUR "
                            f"(je Provider: {stat.get('je_provider', {})}).\n\n" if stat else "")
                    if res.get("ok"):
                        notify("Tägliche Kostenprüfung — Vorschläge liegen vor.",
                               abteilung="CFO/Finance", kategorie="kosten", quelle="cfo-loop",
                               detail=(kopf + str(res.get("vorschlaege", "")))[:1800], dedup_stunden=0)
                    ctx.agenda.markiere_briefing("cfo-kosten", datum)
            except Exception as exc:
                print(f"[cfo] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="cfo-loop").start()


def _fallbacks(secrets: dict, cfg: dict) -> list[dict]:
    """Chat-Fallbacks in Reihenfolge: Gemini (Gratis-Tier) zuerst, dann OpenAI. Nur mit gesetztem Key."""
    from ...core.model_router import GEMINI_BASE_URL
    v = cfg.get("voice", {})
    return [
        {"name": "gemini", "key": secrets.get("GEMINI_API_KEY", ""), "base_url": GEMINI_BASE_URL,
         "model": v.get("gemini_model", "gemini-2.5-flash")},
        {"name": "openai", "key": secrets.get("OPENAI_API_KEY", ""), "base_url": None,
         "model": v.get("openai_model", "gpt-4o-mini")},
    ]


def main() -> None:
    cfg = _load_config()
    secrets = _load_secrets()
    token = secrets.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN fehlt in orchestrator/.env. Bot via @BotFather erstellen und Token "
              "eintragen.", file=sys.stderr)
        raise SystemExit(2)
    allowed = secrets.get("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
    deepgram = secrets.get("DEEPGRAM_API_KEY", "")
    language = cfg.get("voice", {}).get("language", "de")

    from ...core.hoa_conversation import HoaConversation
    ctx, _ = _build_ctx(cfg, secrets)
    model = cfg.get("voice", {}).get("llm_model", "claude-haiku-4-5")
    sessions: dict[int, HoaConversation] = {}
    awaiting_betrag: dict[int, dict] = {}   # chat_id -> Order-Parameter, wenn auf 'Andere Summe' gewartet wird

    print("Telegram-Bot bereit." + ("" if allowed else " WARNUNG: keine TELEGRAM_ALLOWED_CHAT_ID gesetzt."))
    try:
        watch_h = float(secrets.get("WATCH_INTERVAL_HOURS", "") or 6)
    except ValueError:
        watch_h = 6.0
    from ...core.self_maintenance import SelfMaintenance
    maintenance = SelfMaintenance(secrets=ctx.secret_dict or {}, watch=ctx.watch, google=ctx.google,
                                  repo_root=ROOT, notify=ctx.notifications.enqueue)
    _start_watch_loop(ctx.watch, watch_h, maintenance=maintenance, notify=ctx.notifications.enqueue)
    print(f"Watch-Loop aktiv (alle {watch_h:g} h, kostenlos: GitHub + 1 Fachbereich/Tick + IT-Healthcheck).",
          flush=True)
    _start_briefing_loop(ctx, ctx.notifications.enqueue)
    print("Briefing-Loop aktiv (Morgen 08:00 + Abend 20:00, Europe/Berlin).", flush=True)
    _start_cfo_loop(ctx, ctx.notifications.enqueue)
    print("CFO-Kostenloop aktiv (taeglich 03:00, Freeware/Abos/Token-Sparpotenziale).", flush=True)
    _start_selfdev_loop(ctx, secrets)
    if secrets.get("SELF_DEV_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        print("Self-Dev-Loop aktiv (taeglich 09:00, 1 Bereich -> Antrag mit Freigabe-Push).", flush=True)
    _start_investment_loop(ctx, secrets)  # nur aktiv mit INVESTMENT_AUTO_SCREEN=1
    _start_content_feed_loop(ctx, secrets)  # K3: nur aktiv mit CONTENT_FEED_ENABLED=1
    if secrets.get("CONTENT_FEED_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        print("Content-Feed-Loop aktiv (taeglich 07:00, Pipeline Trends->Ideen->Drafts -> Kandidaten in "
              "LUNA-OS).", flush=True)
    _start_security_loop(ctx, secrets)  # Phase 21: nur aktiv mit SECURITY_AUDIT_ENABLED=1
    if secrets.get("SECURITY_AUDIT_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        print("Security-Audit-Loop aktiv (taeglich 04:00, regelbasiert, L1-Meldung).", flush=True)
    offset = 0
    _last_poll = 0.0
    crm_sync = None
    if getattr(ctx, "crm", None) is not None and getattr(ctx.crm, "projektor", None) is not None:
        from ...core.crm_sync import CrmSync
        crm_sync = CrmSync(ctx.crm, ctx.crm.projektor.client, cursor_path=ROOT / "crm" / "sync_cursor.txt")
    while True:
        upd = _api(token, "getUpdates", {"offset": offset, "timeout": 30}, timeout=35)
        # Alle ~15 min kostenlos: neue Mails/Termin-Kollisionen pruefen + steckengebliebene Tickets schliessen.
        import time as _t
        if _t.time() - _last_poll > 900:
            _last_poll = _t.time()
            try:
                if ctx.watch is not None and not ctx.watch.store.paused():
                    ctx.watch.mail_tick()
                    ctx.watch.kalender_tick()
                if ctx.research is not None:
                    ctx.research.aufraeumen(stunden=1)
                if crm_sync is not None:          # Rueckschreiben: HCC-CRM-Aenderungen lokal uebernehmen
                    crm_sync.pull()
                # Phase 19: CRM-Akten mit passenden Gmail-Mails anreichern (Kanal 'mail'; dedupliziert).
                if ctx.crm is not None and ctx.google is not None \
                        and (ctx.watch is None or not ctx.watch.store.paused()):
                    from ...core.crm_mail import CrmMailTracker
                    CrmMailTracker(crm=ctx.crm, google=ctx.google,
                                   eigene_adresse=secrets.get("GOOGLE_ACCOUNT_EMAIL", "hanserautisch@gmail.com"),
                                   secrets=ctx.leak_secrets,
                                   notify=(ctx.notifications.enqueue if ctx.notifications else None)).lauf()
                # Instagram-DM-Poll: standardmaessig AUS (grosse Konten -> Meta-Timeout "reduce the amount
                # of data"; ausserdem ohne App-Veroeffentlichung keine fremden DMs). Opt-in INSTAGRAM_DM_POLL=1;
                # manuell jederzeit via Tool `crm_dm_abrufen`.
                _ig_tok = secrets.get("INSTAGRAM_ACCESS_TOKEN") or secrets.get("INSTAGRAM_PAGE_TOKEN")
                _ig_id = secrets.get("INSTAGRAM_IG_USER_ID")
                _ig_poll_an = str(secrets.get("INSTAGRAM_DM_POLL", "")).strip().lower() in ("1", "true", "yes", "on")
                if _ig_poll_an and ctx.crm is not None and _ig_tok and _ig_id \
                        and (ctx.watch is None or not ctx.watch.store.paused()):
                    from ...core.crm_instagram import CrmInstagramTracker
                    from ...governance.instagram import InstagramConversations
                    CrmInstagramTracker(crm=ctx.crm,
                                        reader=InstagramConversations(_ig_tok, _ig_id),
                                        secrets=ctx.leak_secrets,
                                        notify=(ctx.notifications.enqueue if ctx.notifications else None)).lauf()
            except Exception as exc:
                print(f"[poll] Fehler: {exc}", flush=True)
        # Proaktive Outbox zustellen -- LUNA/Watcher melden sich unaufgefordert beim CEO.
        if allowed and ctx.notifications is not None:
            try:
                for n in ctx.notifications.pending()[:10]:
                    ab = n.get("abteilung") or n.get("quelle") or ""
                    kurz = n["id"].split("-")[-1]
                    kopf = f"🔔 {ab}: " if ab else "🔔 "
                    msg = f"{kopf}{n['text']}  (#{kurz})"
                    if n.get("detail"):
                        msg += f"\nDetails: schreib mir \"zeig #{kurz}\""
                    if _api(token, "sendMessage",
                            {"chat_id": allowed, "text": fuer_telegram(msg)}).get("ok"):
                        ctx.notifications.mark_sent(n["id"])
                        # Kontext in die CEO-Session geben, damit LUNA bei Rueckfragen ("ist freigegeben")
                        # weiss, worauf der CEO sich bezieht (Pushes kommen sonst ausserhalb des Chats an).
                        try:
                            cid = int(allowed)
                            conv = sessions.get(cid)
                            if conv is None:
                                conv = HoaConversation(ctx, model=model,
                                                       api_key=secrets["ANTHROPIC_API_KEY"],
                                                       fallbacks=_fallbacks(secrets, cfg))
                                sessions[cid] = conv
                            kontext = f"(Proaktive Meldung, die ich dem CEO gesendet habe:) {ab}: {n['text']}"
                            if n.get("detail"):
                                kontext += f" | Detail: {str(n['detail'])[:300]}"
                            conv.messages.append({"role": "user", "content": kontext})
                            conv.messages.append({"role": "assistant",
                                                  "content": [{"type": "text", "text": msg}]})
                        except Exception:
                            pass
            except Exception as exc:
                print(f"[notify] Zustell-Fehler: {exc}", flush=True)
        # Offene 1-Tap-Freigaben als Ja/Nein-Buttons zustellen (Schritt 5).
        if allowed:
            _deliver_approvals(token, allowed, ctx)
        for u in upd.get("result", []):
            offset = u["update_id"] + 1
            # Button-Klick (callback_query) auf eine Freigabe-Anfrage
            cb = u.get("callback_query")
            if cb:
                try:
                    data = cb.get("data") or ""
                    cbchat = str((((cb.get("message") or {}).get("chat")) or {}).get("id", ""))
                    if allowed and cbchat != allowed:
                        _api(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Nicht autorisiert."})
                    elif data.startswith("apv:") and getattr(ctx, "approvals", None) is not None:
                        _, aid, ent = data.split(":", 2)
                        apv = ctx.approvals.get(aid)
                        mid = (cb.get("message") or {}).get("message_id")
                        if not apv or apv.get("status") != "offen":
                            _api(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Bereits entschieden."})
                        elif ent == "amt":                       # Andere Summe -> auf neuen USD-Betrag warten
                            p = apv.get("payload") or {}
                            awaiting_betrag[int(cbchat)] = {"symbol": p.get("symbol"), "asset": p.get("asset", "aktie"),
                                                            "side": p.get("side", "buy")}
                            ctx.approvals.entscheiden(aid, False, ergebnis="andere Summe angefragt")
                            _api(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": "USD-Betrag eingeben"})
                            if mid:
                                _api(token, "editMessageText",
                                     {"chat_id": cbchat, "message_id": mid, "reply_markup": json.dumps({"inline_keyboard": []}),
                                      "text": fuer_telegram(apv.get("frage", "") + "\n\n✏️ Schick mir den gewuenschten USD-Betrag als Zahl.")})
                        else:
                            ja = ent == "yes"
                            res = _approval_ausfuehren(ctx, apv) if ja else "Abgelehnt."
                            ctx.approvals.entscheiden(aid, ja, ergebnis=(res if ja else "abgelehnt"))
                            _api(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": ("Ja" if ja else "Nein")})
                            if mid:
                                _api(token, "editMessageText",
                                     {"chat_id": cbchat, "message_id": mid, "reply_markup": json.dumps({"inline_keyboard": []}),
                                      "text": fuer_telegram(apv.get("frage", "") + f"\n\n{'✅ Ja' if ja else '❌ Nein'} — {res}")})
                except Exception as exc:
                    print(f"[callback] Fehler: {exc}", flush=True)
                continue
            msg = u.get("message") or u.get("edited_message")
            if not msg:
                continue
            chat_id = msg["chat"]["id"]
            if allowed and str(chat_id) != allowed:
                _api(token, "sendMessage", {"chat_id": chat_id,
                     "text": f"Nicht autorisiert. Deine Chat-ID: {chat_id}"})
                continue
            if not allowed:
                _api(token, "sendMessage", {"chat_id": chat_id,
                     "text": f"Setze TELEGRAM_ALLOWED_CHAT_ID={chat_id} in orchestrator/.env und starte neu."})
                continue
            text = msg.get("text")
            if not text and msg.get("voice") and deepgram:
                audio = _download_voice(token, msg["voice"]["file_id"])
                text = _transcribe(audio, deepgram, language) if audio else None
            if not text:
                continue
            # Antwort auf 'Andere Summe': Betrag lesen -> frische Freigabe (Ja/Nein/Andere Summe) senden
            if chat_id in awaiting_betrag and getattr(ctx, "approvals", None) is not None:
                params = awaiting_betrag.pop(chat_id)
                betrag = _parse_betrag(text)
                if betrag > 0:
                    aid = _neue_paper_freigabe(ctx, ctx.investment, params, betrag)
                    apv = ctx.approvals.get(aid) if aid else None
                    if apv and _send_approval(token, chat_id, apv).get("ok"):
                        ctx.approvals.mark_sent(aid)
                    else:
                        _api(token, "sendMessage", {"chat_id": chat_id,
                             "text": "Konnte keinen Kurs holen — Freigabe abgebrochen."})
                else:
                    _api(token, "sendMessage", {"chat_id": chat_id,
                         "text": "Das war keine Zahl — Freigabe abgebrochen. Frag gern neu."})
                continue
            if text.strip().lower() in ("/reset", "/neu", "/start"):
                sessions.pop(chat_id, None)
                _api(token, "sendMessage", {"chat_id": chat_id,
                     "text": "Verlauf zurückgesetzt. Wie kann ich helfen?"})
                continue
            conv = sessions.setdefault(chat_id, HoaConversation(
                ctx, model=model, api_key=secrets["ANTHROPIC_API_KEY"], fallbacks=_fallbacks(secrets, cfg)))
            try:
                antwort = conv.respond(text)
            except Exception as exc:
                # Defensive: Session verwerfen, damit der Chat nie dauerhaft blockiert.
                sessions.pop(chat_id, None)
                print(f"[chat] Fehler, Session zurueckgesetzt: {exc}", flush=True)
                antwort = ("Es gab gerade einen technischen Fehler — ich habe den Verlauf zurückgesetzt. "
                           "Bitte stell die Frage noch einmal.")
            _api(token, "sendMessage", {"chat_id": chat_id, "text": fuer_telegram(antwort)[:4000]})
            _deliver_approvals(token, chat_id, ctx)   # falls die Antwort eine Freigabe erzeugt hat: sofort senden
            # Phase 14: erzeugte Visualisierungen als Bild-Datei (SVG) nachsenden.
            if ctx.visuals:
                for vis in ctx.visuals:
                    _send_document(token, chat_id, vis.get("dateiname", "visualisierung.svg"),
                                   vis.get("svg", "").encode("utf-8"), caption=vis.get("titel", ""))
                ctx.visuals.clear()
        time.sleep(0.5)


if __name__ == "__main__":
    main()
