"""Hintergrund-Modus fuer naechtliche Agenten-Jobs (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 4).

Die Job-Loops (CFO 03:00, Content-Feed 02:00, Self-Dev 04:00) laufen in `hintergrund_modus()`. Solange der Modus in
einem Thread aktiv ist,
- schickt das `FallbackBackend` Fachagenten-Aufrufe zuerst als stillen Auftrag ans Backoffice (lokales Modell auf dem
  MACO470, mit RAM-Waechter) und wartet auf das Ergebnis -- erst danach Cloud-Fallback;
- markiert `Notifications.enqueue` Meldungen fuer das Morgen-Briefing statt sofortiger Zustellung (CEO 2026-09-27).
Interaktive Aufrufe (Chat, `delegate`) laufen nie im Hintergrund-Modus und bleiben sofort.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

_AKTIV: ContextVar[bool] = ContextVar("luna_hintergrund", default=False)


def aktiv() -> bool:
    return _AKTIV.get()


@contextmanager
def hintergrund_modus():
    token = _AKTIV.set(True)
    try:
        yield
    finally:
        _AKTIV.reset(token)
