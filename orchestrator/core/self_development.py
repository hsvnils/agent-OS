"""Phase 13 -- Self-Development-Loop (Apex).

Schliesst den Kreis: aus dem 24/7-Fachbereichs-Wissensstand (Phase 12, kostenlos) erzeugen die Agenten
**konkrete Verbesserungs-Vorschlaege in IHREM Bereich** -> bewerteter **Antrag** (Phase 6) -> der CEO gibt
ueber den HoA frei -> die Execution-Engine (Phase 7) setzt um (Branch + Tests, kein Merge ohne CEO).

**Harte Invarianten:**
- **Nur Vorschlaege, nie Ausfuehrung.** Output ist ein Antrag (Status `eingereicht`). Selbst-Modifikation
  ausschliesslich ueber den freigegebenen Antrags-/Execution-Pfad.
- **Token-frugal:** Das Sammeln (Wissensstand) ist kostenlos. Die teure Vorschlags-Erzeugung (LLM) laeuft
  **on-demand** (CEO fragt) -- der **geplante** Loop (`lauf`) ist per Default **aus** (`enabled=False`).
- **Notbremse:** ein Pausenschalter haelt alle autonomen Ablaeufe an (siehe WatchStore.pause).
"""
from __future__ import annotations

from dataclasses import dataclass

from .innovation import InnovationPipeline


@dataclass
class SelfDevErgebnis:
    abteilung: str
    idee: str = ""
    machbarkeit: str = ""
    kostenvoranschlag: str = ""
    antrag_id: str | None = None
    hinweis: str = ""


class SelfDevelopment:
    def __init__(self, core, *, web=None, watch=None, antraege=None, secrets: list[str] | None = None,
                 enabled: bool = False, max_pro_lauf: int = 1):
        self.core = core
        self.web = web
        self.watch = watch          # WatchScheduler -> Fachbereichs-Wissensstand
        self.antraege = antraege
        self.secrets = secrets or []
        self.enabled = enabled      # geplanter Loop nur, wenn explizit aktiviert (Token-Schutz)
        self.max_pro_lauf = max_pro_lauf

    def _wissen_text(self, abteilung: str) -> str:
        if self.watch is None:
            return ""
        try:
            funde = self.watch.briefing(abteilung, limit=8)
        except Exception:
            funde = []
        return "\n".join(f"- {f.get('titel', '')}: {f.get('detail', '') or f.get('url', '')}"
                         for f in funde if f.get("titel"))

    def vorschlag_fuer(self, abteilung: str) -> SelfDevErgebnis:
        """On-demand: EIN bewerteter Selbst-Entwicklungs-Vorschlag fuer einen Bereich -> Antrag."""
        abteilung = (abteilung or "berater").strip().lower()
        wissen = self._wissen_text(abteilung)
        pipe = InnovationPipeline(self.core, web=self.web, antraege=self.antraege, secrets=self.secrets)
        erg = pipe.run(f"Selbst-Weiterentwicklung Fachbereich {abteilung}",
                       abteilung=abteilung, wissen=wissen)
        return SelfDevErgebnis(abteilung=abteilung, idee=erg.idee, machbarkeit=erg.machbarkeit,
                               kostenvoranschlag=erg.kostenvoranschlag, antrag_id=erg.antrag_id)

    def lauf(self, abteilungen: list[str] | None = None) -> dict:
        """Geplanter Mehr-Bereichs-Lauf -- GATED (Token-/Notbremsen-Schutz).

        Aus, solange `enabled=False` oder die Autonomie pausiert ist. Begrenzt auf `max_pro_lauf` Bereiche.
        """
        if self.watch is not None and getattr(self.watch.store, "paused", lambda: False)():
            return {"ok": False, "hinweis": "Autonomie pausiert (Notbremse) -- kein Selbst-Entwicklungs-Lauf."}
        if not self.enabled:
            return {"ok": False, "hinweis": "Selbst-Entwicklungs-Loop ist aus (SELF_DEV_ENABLED=1 noetig). "
                    "On-demand ueber das Tool selbstentwicklung."}
        ziele = (abteilungen or self._bereiche_mit_wissen())[: self.max_pro_lauf]
        ergebnisse = [self.vorschlag_fuer(a) for a in ziele]
        return {"ok": True, "antraege": [e.antrag_id for e in ergebnisse if e.antrag_id]}

    def _bereiche_mit_wissen(self) -> list[str]:
        """Bereiche mit gesammeltem Wissensstand (neueste zuerst), fuer den geplanten Lauf."""
        if self.watch is None:
            return ["berater"]
        gesehen: list[str] = []
        for f in self.watch.briefing(None, limit=100):
            ab = f.get("abteilung")
            if ab and ab not in gesehen:
                gesehen.append(ab)
        return gesehen or ["berater"]
