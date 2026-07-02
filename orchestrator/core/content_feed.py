"""K3 -- Content-Feed-Loop: LUNA-Agenten fuettern content_ops.

Erste Ausbaustufe (Pilot): der Content-Researcher erzeugt ueber die bestehende Web-Recherche
(Brave, kostenlos) **Trend-Kandidaten** und schreibt sie mit Status `new` nach `trend_signals`
(Supabase) -> erscheinen in der LUNA-OS-App „Trends" -> das Team reviewt. Ersetzt den alten
Dummy-Worker Schritt fuer Schritt (danach Ideen/Drafts analog).

Als **Loop** entworfen (governance/autonomie-stufen.md §5b):
- **Ziel:** bis zu N neue, nicht-doppelte Trend-Kandidaten je Lauf (Status `new`, Team-Review offen).
- **Trigger:** WatchScheduler (24/7-Hintergrund, token-frugal) oder manuell (LUNA-Tool / CEO).
- **Lauf:** Brave-Web-Recherche je Content-Suchthema (guenstig, KEIN Hintergrund-LLM), Bulk je Thema.
- **Verifikation:** Dedup gegen bestehende `source_url` + **Team-Review** in LUNA-OS (Maker/Checker, L1).
- **Stop:** max je Thema + max gesamt je Lauf + Notbremse (`WatchStore.paused`).

Autonomie **L1** (nur Kandidaten sammeln + melden; kein Auto-Publish -- Oeffentlichkeit = CEO-Tor).
Leck-geschuetzt (Recherche laeuft ueber WebResearch mit redact); keine neue Dependency.
"""
from __future__ import annotations

from .watch_config import themen_fuer


class ContentFeed:
    """Erzeugt Trend-Kandidaten aus der Web-Recherche und schreibt sie nach content_ops (trend_signals).

    Bausteine werden injiziert (Offline-Self-Checks ohne Netz/Keys):
    - `web`          -- WebResearch (Brave-first); ohne Provider -> Fall-B, Lauf erzeugt nichts.
    - `trends_store` -- ContentStore fuer `trend_signals` (add + Dedup via list).
    - `notify`       -- callable(text, *, abteilung, kategorie, quelle, detail) -> Push an den CEO.
    - `research`     -- ResearchTickets (Nachverfolgbarkeit des Laufs), optional.
    - `watch_store`  -- WatchStore (Notbremse `paused()`), optional.
    - `themen`       -- Such-Themen; Default = kuratierte Content-Themen (watch_config, Abteilung 'cco').
    """

    def __init__(self, *, web, trends_store, notify=None, research=None, watch_store=None,
                 themen: list[str] | None = None, secrets: list[str] | None = None):
        self.web = web
        self.trends_store = trends_store
        self.notify = notify
        self.research = research
        self.watch_store = watch_store
        self.themen = list(themen) if themen else list(themen_fuer("cco").get("suche", []))
        self.secrets = secrets or []

    def trend_lauf(self, *, max_pro_thema: int = 3, max_gesamt: int = 8) -> dict:
        """Ein Loop-Durchlauf: bis zu `max_gesamt` neue Trend-Kandidaten (Status `new`) anlegen."""
        if self.watch_store is not None and self.watch_store.paused():
            return {"ok": False, "pausiert": True, "erzeugt": 0}
        if self.web is None or self.trends_store is None:
            return {"ok": False, "erzeugt": 0, "hinweis": "Web-Recherche oder Trend-Store nicht verfuegbar."}

        vorhandene = self._vorhandene_urls()
        erzeugt: list[dict] = []
        quellen: list[str] = []
        for thema in self.themen:
            if len(erzeugt) >= max_gesamt:
                break
            erg = self.web.recherchiere(thema)   # Brave-first, kostenlos
            if not getattr(erg, "ok", False):
                continue
            for t in getattr(erg, "treffer", [])[:max_pro_thema]:
                if len(erzeugt) >= max_gesamt:
                    break
                if not t.url or t.url in vorhandene:
                    continue
                row = {
                    "title": (t.titel or thema)[:300],
                    "description": (t.auszug or "")[:1000],
                    "source_type": "web",
                    "source_name": f"Web-Recherche (Brave) -- {thema}"[:200],
                    "source_url": t.url,
                    "status": "new",
                }
                if self.trends_store.add(row).get("ok"):
                    vorhandene.add(t.url)
                    erzeugt.append(row)
                    quellen.append(t.url)

        self._dokumentieren(erzeugt, quellen)
        self._melden(erzeugt)
        return {"ok": True, "erzeugt": len(erzeugt), "kandidaten": erzeugt}

    # -- intern --

    def _vorhandene_urls(self) -> set[str]:
        """Bereits bekannte Trend-Quellen (Dedup, damit derselbe Fund nicht mehrfach landet)."""
        try:
            return {r.get("source_url") for r in self.trends_store.list(limit=200) if r.get("source_url")}
        except Exception:
            return set()

    def _dokumentieren(self, erzeugt: list[dict], quellen: list[str]) -> None:
        if self.research is None or not erzeugt:
            return
        tid = self.research.erstellen(
            f"Trend-Scouting: {len(erzeugt)} neue Kandidaten", abteilung="content")
        self.research.in_arbeit(tid)
        self.research.erledigen(
            tid, provider="brave",
            befund=f"{len(erzeugt)} neue Trend-Kandidaten (Status new) fuer das Content-Review angelegt.",
            quellen=quellen)

    def _melden(self, erzeugt: list[dict]) -> None:
        if self.notify is None or not erzeugt:
            return
        detail = "\n".join(f"- {r['title']}: {r['source_url']}" for r in erzeugt)
        try:
            self.notify(
                f"{len(erzeugt)} neue Trend-Kandidaten fuer das Content-Review (Status: new) -- in LUNA-OS "
                "unter „Trends“.",
                abteilung="Content/Researcher", kategorie="content", quelle="content-feed", detail=detail)
        except Exception:
            pass
