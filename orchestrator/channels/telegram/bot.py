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
from functools import partial
from pathlib import Path

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
    from ...core.backends import AgentSdkBackend
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
    backend = AgentSdkBackend(cfg["models"], cfg["effort"], gate=CeoGate(),
                              max_turns=cfg["run"].get("max_turns", 4))
    changelog = partial(append_changelog, ROOT / cfg["governance"]["changelog_file"])
    mem_cfg = cfg.get("memory", {})
    memory = Memory(ROOT / mem_cfg.get("path", "orchestrator/memory/log.jsonl"),
                    secrets=secret_values, recall_limit=mem_cfg.get("recall_limit", 5)) \
        if mem_cfg.get("enabled", True) else None
    core = HeadOfAgents(backend, load_all_subagents(), gate=CeoGate(), leak_secrets=secret_values,
                        changelog=changelog, logger=Logger(), memory=memory)
    antraege = Antraege(ROOT / "antraege" / "log.jsonl", secrets=secret_values, changelog=changelog)
    engine = ExecutionEngine(
        antraege, make_workspace=live.real_make_workspace(ROOT),
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
    # Phase 12: 24/7-Watcher (kostenlos). GitHub-Token optional (Rate-Limit); Hintergrund-LLM aus.
    from ...core.scheduler import WatchScheduler, WatchStore
    from ...governance.github_watch import GitHubWatch
    watch = WatchScheduler(WatchStore(ROOT / "watch" / "log.jsonl", secrets=secret_values),
                           github=GitHubWatch(env=secrets), web=web, research=research,
                           notify=notifications.enqueue, google=google, secrets=secret_values)
    # Briefings/Agenda (manuelle Punkte).
    from ...core.briefing import Agenda
    agenda = Agenda(ROOT / "agenda" / "log.jsonl", secrets=secret_values)
    return ToolContext(core=core, antraege=antraege, engine=engine,
                       finance_dir=ROOT / "finance", repo_root=ROOT, leak_secrets=secret_values,
                       web=web, research=research, google=google, watch=watch,
                       notifications=notifications, agenda=agenda, secret_dict=secrets), secret_values


def _api(token: str, method: str, params: dict, timeout: int = 60) -> dict:
    url = f"{API}/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
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
                    sd.vorschlag_fuer(next(depts))   # erzeugt Antrag + Freigabe-Push
                    ctx.agenda.markiere_briefing("selfdev", datum)
            except Exception as exc:
                print(f"[selfdev] Fehler: {exc}", flush=True)
            time.sleep(300)

    threading.Thread(target=loop, daemon=True, name="selfdev-loop").start()


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
                    notify(text, abteilung="LUNA-Briefing", kategorie="briefing", quelle="briefing",
                           dedup_stunden=0)
                    ctx.agenda.markiere_briefing(art, datum)
            except Exception as exc:
                print(f"[briefing] Fehler: {exc}", flush=True)
            time.sleep(300)  # alle 5 min pruefen

    threading.Thread(target=loop, daemon=True, name="briefing-loop").start()


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
    _start_selfdev_loop(ctx, secrets)
    if secrets.get("SELF_DEV_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        print("Self-Dev-Loop aktiv (taeglich 09:00, 1 Bereich -> Antrag mit Freigabe-Push).", flush=True)
    offset = 0
    _last_poll = 0.0
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
                    if _api(token, "sendMessage", {"chat_id": allowed, "text": msg}).get("ok"):
                        ctx.notifications.mark_sent(n["id"])
            except Exception as exc:
                print(f"[notify] Zustell-Fehler: {exc}", flush=True)
        for u in upd.get("result", []):
            offset = u["update_id"] + 1
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
            if text.strip().lower() in ("/reset", "/neu", "/start"):
                sessions.pop(chat_id, None)
                _api(token, "sendMessage", {"chat_id": chat_id,
                     "text": "Verlauf zurueckgesetzt. Wie kann ich helfen?"})
                continue
            conv = sessions.setdefault(chat_id, HoaConversation(ctx, model=model,
                                                                api_key=secrets["ANTHROPIC_API_KEY"]))
            try:
                antwort = conv.respond(text)
            except Exception as exc:
                # Defensive: Session verwerfen, damit der Chat nie dauerhaft blockiert.
                sessions.pop(chat_id, None)
                print(f"[chat] Fehler, Session zurueckgesetzt: {exc}", flush=True)
                antwort = ("Es gab gerade einen technischen Fehler -- ich habe den Verlauf zurueckgesetzt. "
                           "Bitte stell die Frage noch einmal.")
            _api(token, "sendMessage", {"chat_id": chat_id, "text": antwort[:4000]})
        time.sleep(0.5)


if __name__ == "__main__":
    main()
