"""Self-Maintenance -- die IT ueberwacht kontinuierlich, ob die eigenen Prozesse laufen.

Leichte, **kostenlose** Health-Checks (keine LLM-Aufrufe): noetige Keys vorhanden, Google-Zugang aktiv,
Stores beschreibbar, Watcher-Heartbeat aktuell. Bei einem Problem meldet sich die IT **proaktiv** beim CEO
(ueber den Notifier; Dedup verhindert Spam). On-demand abrufbar ueber das Tool `systemcheck`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


class SelfMaintenance:
    def __init__(self, *, secrets: dict | None = None, watch=None, google=None,
                 repo_root: Path | None = None, notify=None, heartbeat_stunden: float = 13):
        self.secrets = secrets or {}
        self.watch = watch
        self.google = google
        self.repo_root = Path(repo_root) if repo_root else None
        self.notify = notify
        self.heartbeat_stunden = heartbeat_stunden

    def pruefe(self) -> list[dict]:
        """Liste aller Komponenten-Checks: {komponente, ok, hinweis}."""
        c: list[dict] = []

        def add(komp, ok, hinweis=""):
            c.append({"komponente": komp, "ok": bool(ok), "hinweis": hinweis})

        s = self.secrets
        add("LUNA-Gehirn (ANTHROPIC_API_KEY)", bool(s.get("ANTHROPIC_API_KEY")),
            "" if s.get("ANTHROPIC_API_KEY") else "Key fehlt -- LUNA kann nicht antworten.")
        add("Telegram", bool(s.get("TELEGRAM_BOT_TOKEN") and s.get("TELEGRAM_ALLOWED_CHAT_ID")),
            "" if s.get("TELEGRAM_BOT_TOKEN") else "Bot-Token/Chat-ID fehlt.")
        add("Web-Recherche (Brave)", bool(s.get("BRAVE_API_KEY")),
            "" if s.get("BRAVE_API_KEY") else "BRAVE_API_KEY fehlt -- Recherche/Watcher eingeschränkt.")
        if self.google is not None:
            ok = self.google.verfuegbar()
            add("Google Workspace", ok, "" if ok else "OAuth-Credentials fehlen -- Mail/Kalender inaktiv.")
        if self.repo_root is not None:
            ok = self._schreibbar(self.repo_root)
            add("Daten-Stores beschreibbar", ok, "" if ok else "Repo-Verzeichnis nicht beschreibbar.")
        if self.watch is not None:
            add("Watcher-Heartbeat", *self._heartbeat())
        return c

    def lauf(self) -> list[dict]:
        """Checks ausfuehren; bei Problemen proaktiv melden (Dedup im Notifier). Gibt die Probleme zurueck."""
        probleme = [x for x in self.pruefe() if not x["ok"]]
        if probleme and self.notify is not None:
            detail = "\n".join(f"- {p['komponente']}: {p['hinweis']}" for p in probleme)
            try:
                self.notify(f"{len(probleme)} Problem(e) bei der Prozessüberwachung entdeckt.",
                            abteilung="IT/Self-Maintenance", kategorie="fehler",
                            quelle="self-maintenance", detail=detail)
            except Exception:
                pass
        return probleme

    # -- intern --

    def _schreibbar(self, pfad: Path) -> bool:
        try:
            probe = pfad / ".health_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except Exception:
            return False

    def _heartbeat(self) -> tuple[bool, str]:
        last = self.watch.store.last_run("github")
        if not last:
            return True, "noch kein Lauf (frisch gestartet)"
        try:
            alt = datetime.now() - datetime.fromisoformat(last)
        except ValueError:
            return True, ""
        if alt > timedelta(hours=self.heartbeat_stunden):
            return False, f"Watcher lief zuletzt vor {int(alt.total_seconds() // 3600)} h -- evtl. hängt der Loop."
        return True, f"zuletzt vor {int(alt.total_seconds() // 60)} min"
