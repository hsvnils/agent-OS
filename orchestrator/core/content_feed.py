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

from ..governance.leak_guard import redact
from .watch_config import themen_fuer


class ContentFeed:
    """Fuettert content_ops: Trends (Brave) -> Ideen -> Drafts (Fachagent), jeweils als Kandidaten
    mit Review-Status fuer das Team (Trends `new` -> Ideen `inbox` -> Drafts `idea`).

    Bausteine werden injiziert (Offline-Self-Checks ohne Netz/Keys):
    - `web`          -- WebResearch (Brave-first); ohne Provider -> Fall-B, Trend-Lauf erzeugt nichts.
    - `trends_store` -- ContentStore fuer `trend_signals` (add + Dedup via list).
    - `ideas_store`  -- ContentStore fuer `ideas` (Ideen-Stufe), optional.
    - `drafts_store` -- ContentStore fuer `content_drafts` (Draft-Stufe), optional.
    - `core`         -- HeadOfAgents (backend + subagents) fuer die LLM-Stufen (Ideen/Drafts), optional.
    - `notify`       -- callable(text, *, abteilung, kategorie, quelle, detail) -> Push an den CEO.
    - `research`     -- ResearchTickets (Nachverfolgbarkeit des Laufs), optional.
    - `watch_store`  -- WatchStore (Notbremse `paused()`), optional.
    - `themen`       -- Such-Themen; Default = kuratierte Content-Themen (watch_config, Abteilung 'cco').
    - `agent`        -- Fachagent-Kuerzel fuer Ideen/Drafts (Default 'cco' = Content).
    """

    def __init__(self, *, web, trends_store, ideas_store=None, drafts_store=None, core=None,
                 notify=None, research=None, watch_store=None, themen: list[str] | None = None,
                 agent: str = "cco", secrets: list[str] | None = None):
        self.web = web
        self.trends_store = trends_store
        self.ideas_store = ideas_store
        self.drafts_store = drafts_store
        self.core = core
        self.notify = notify
        self.research = research
        self.watch_store = watch_store
        self.themen = list(themen) if themen else list(themen_fuer("cco").get("suche", []))
        self.agent = agent
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
        self._melden(erzeugt, "Trend-Kandidaten", "Trends")
        return {"ok": True, "erzeugt": len(erzeugt), "kandidaten": erzeugt}

    def ideen_lauf(self, *, max_gesamt: int = 5) -> dict:
        """Aus offenen Trend-Signalen (Status `new`) Content-Ideen ableiten (Fachagent) und als Kandidaten
        (Status `inbox`) nach `ideas` schreiben. Der Trend wird auf `reviewing` gesetzt (idempotent: nur
        `new` wird verarbeitet). Braucht `ideas_store` + `core` (LLM)."""
        if not self._bereit(self.ideas_store):
            return {"ok": False, "erzeugt": 0, "hinweis": "Ideen-Stufe braucht ideas_store + core (LLM)."}
        trends = [t for t in self.trends_store.list(limit=100)
                  if t.get("status") == "new" and t.get("title")][:max_gesamt]
        erzeugt: list[dict] = []
        for t in trends:
            idee = self._generiere_idee(t)
            if not idee:
                continue
            if self.ideas_store.add(idee).get("ok"):
                if t.get("id"):
                    self.trends_store.status_setzen(t["id"], "reviewing")   # Trend als verarbeitet markieren
                erzeugt.append(idee)
        self._melden(erzeugt, "Content-Ideen", "Ideen-Labor", kategorie="content-ideen")
        return {"ok": True, "erzeugt": len(erzeugt), "kandidaten": erzeugt}

    def drafts_lauf(self, *, max_gesamt: int = 5) -> dict:
        """Aus offenen Ideen (Status `inbox`) Draft-Entwuerfe (Hook/Caption/Hashtags) ableiten (Fachagent)
        und als Kandidaten (Status `idea`) nach `content_drafts` schreiben. Die Idee wird auf `sorted`
        gesetzt (idempotent: nur `inbox` wird verarbeitet). Braucht `drafts_store` + `ideas_store` + `core`."""
        if not self._bereit(self.drafts_store) or self.ideas_store is None:
            return {"ok": False, "erzeugt": 0, "hinweis": "Draft-Stufe braucht drafts_store + ideas_store + core."}
        ideen = [i for i in self.ideas_store.list(limit=100)
                 if i.get("status") == "inbox" and i.get("title")][:max_gesamt]
        erzeugt: list[dict] = []
        for i in ideen:
            draft = self._generiere_draft(i)
            if not draft:
                continue
            if self.drafts_store.add(draft).get("ok"):
                if i.get("id"):
                    self.ideas_store.status_setzen(i["id"], "sorted")       # Idee als verarbeitet markieren
                erzeugt.append(draft)
        self._melden(erzeugt, "Draft-Entwuerfe", "Drafts", kategorie="content-drafts")
        return {"ok": True, "erzeugt": len(erzeugt), "kandidaten": erzeugt}

    def pipeline_lauf(self, *, max_pro_stufe: int = 5) -> dict:
        """Vollständiger K3-Durchlauf Trends -> Ideen -> Drafts. Trends kostenlos (Brave); Ideen/Drafts
        nur wenn `core` (LLM) verfuegbar. Respektiert die Notbremse (in jeder Stufe geprueft)."""
        trends = self.trend_lauf(max_gesamt=max_pro_stufe)
        ideen = self.ideen_lauf(max_gesamt=max_pro_stufe) if self.core is not None else {"erzeugt": 0}
        drafts = self.drafts_lauf(max_gesamt=max_pro_stufe) if self.core is not None else {"erzeugt": 0}
        return {"ok": True, "trends": trends.get("erzeugt", 0),
                "ideen": ideen.get("erzeugt", 0), "drafts": drafts.get("erzeugt", 0),
                "pausiert": bool(trends.get("pausiert"))}

    # -- LLM-Stufen (Ideen/Drafts) --

    def _generiere_idee(self, trend: dict) -> dict | None:
        antwort = self._frag(
            "Du bist der Content-Stratege. Leite aus diesem Trend-Signal GENAU EINE konkrete, umsetzbare "
            "Content-Idee ab. Antworte NUR in diesem Format (keine weiteren Zeilen):\n"
            "TITEL: <praegnanter Content-Titel>\n"
            "IDEE: <2-3 Saetze: Aufhaenger + Umsetzung>\n"
            "FORMAT: <Reel|Post|Story|Carousel>\n\n"
            f"Trend: {trend.get('title', '')}\n{(trend.get('description') or '')[:600]}")
        if not antwort:
            return None
        titel = self._feld(antwort, "TITEL") or _erste_zeile(antwort)
        idee = self._feld(antwort, "IDEE") or antwort.strip()
        fmt = self._feld(antwort, "FORMAT")
        if not titel:
            return None
        return {"title": titel[:300], "description": idee[:1000], "status": "inbox",
                "category": (fmt or "")[:60] or None, "source_type": "trend",
                "ai_summary": f"Aus Trend abgeleitet: {trend.get('title', '')}"[:500]}

    def _generiere_draft(self, idee: dict) -> dict | None:
        antwort = self._frag(
            "Du bist der Content-Redakteur. Schreibe aus dieser Content-Idee EINEN Instagram-Reel-Entwurf. "
            "Antworte NUR in diesem Format (keine weiteren Zeilen):\n"
            "HOOK: <erster Satz, der in <=1 Sekunde fesselt>\n"
            "CAPTION: <2-4 Saetze Caption>\n"
            "HASHTAGS: <5-8 Hashtags mit #, durch Leerzeichen getrennt>\n\n"
            f"Idee: {idee.get('title', '')}\n{(idee.get('description') or '')[:600]}")
        if not antwort:
            return None
        hook = self._feld(antwort, "HOOK")
        caption = self._feld(antwort, "CAPTION")
        hashtags = [h for h in self._feld(antwort, "HASHTAGS").split() if h.startswith("#")]
        if not (hook or caption):
            return None
        return {"title": (idee.get("title") or "Reel-Entwurf")[:300], "platform": "instagram",
                "content_format": "reel", "status": "idea", "hook": hook[:500] or None,
                "caption": caption[:2000] or None, "hashtags": hashtags or None}

    def _frag(self, prompt: str, agent: str | None = None) -> str:
        """Fachagent-LLM-Aufruf (Gemini-Fallback wie ueberall); leck-geschuetzt. '' bei Fehler."""
        if self.core is None:
            return ""
        key = agent or self.agent
        spec = self.core.subagents.get(key) if getattr(self.core, "subagents", None) else None
        system = spec.system_prompt if spec else ""
        try:
            out = self.core.backend.respond(key, system, prompt, {})
        except Exception:
            return ""
        return redact(out or "", self.secrets)

    @staticmethod
    def _feld(text: str, label: str) -> str:
        for line in (text or "").splitlines():
            s = line.strip().lstrip("*-# ").strip()
            if s.lower().startswith(label.lower()) and ":" in s:
                return s.split(":", 1)[1].strip().strip("*").strip()
        return ""

    def _bereit(self, ziel_store) -> bool:
        return ziel_store is not None and self.core is not None and not self._pausiert()

    def _pausiert(self) -> bool:
        return self.watch_store is not None and self.watch_store.paused()

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

    def _melden(self, erzeugt: list[dict], was: str, app: str, *, kategorie: str = "content") -> None:
        if self.notify is None or not erzeugt:
            return
        detail = "\n".join(
            f"- {r.get('title', '')}" + (f": {r['source_url']}" if r.get("source_url") else "")
            for r in erzeugt)
        try:
            self.notify(
                f"{len(erzeugt)} neue {was} fuer das Content-Review -- in LUNA-OS unter „{app}“.",
                abteilung="Content/Researcher", kategorie=kategorie, quelle="content-feed", detail=detail)
        except Exception:
            pass
