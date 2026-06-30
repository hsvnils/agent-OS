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
    def __init__(self, core, *, web=None, watch=None, antraege=None, notify=None,
                 secrets: list[str] | None = None, enabled: bool = False, max_pro_lauf: int = 1):
        self.core = core
        self.web = web
        self.watch = watch          # WatchScheduler -> Fachbereichs-Wissensstand
        self.antraege = antraege
        self.notify = notify        # proaktive Meldung an den CEO (Freigabe anfordern)
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

    def vorschlag_fuer(self, abteilung: str, *, modus: str = "extern") -> SelfDevErgebnis:
        """EIN bewerteter Vorschlag fuer einen Bereich -> Antrag.

        modus='extern': aus dem Web-Wissensstand (neue Entwicklungen). modus='intern': Luecken-/Mandats-
        Analyse -- der Bereich prueft seine Charta gegen seine aktuellen Faehigkeiten und schlaegt vor, was
        ihm fehlt (Werkzeug/Daten/Prozess). So kommen Verbesserungsvorschlaege PROAKTIV aus dem System.
        """
        abteilung = (abteilung or "berater").strip().lower()
        if modus == "intern":
            spec = self.core.subagents.get(abteilung)
            charta = (spec.system_prompt[:1500] if spec else "")
            thema = f"Interne Lücken-/Mandatsanalyse {abteilung}"
            wissen = (f"Dein Mandat (Charta-Auszug):\n{charta}\n\nFrage dich kritisch: Welche EINE Faehigkeit, "
                      "welches Werkzeug, welche Daten oder welcher Prozess fehlt dir, um dein Mandat optimal "
                      "zu erfuellen? Schlage genau diese eine konkrete Verbesserung vor.")
        else:
            thema = f"Selbst-Weiterentwicklung Fachbereich {abteilung}"
            wissen = self._wissen_text(abteilung)
        pipe = InnovationPipeline(self.core, web=self.web, antraege=self.antraege, secrets=self.secrets)
        erg = pipe.run(thema, abteilung=abteilung, wissen=wissen)
        # Proaktiv den CEO um Freigabe bitten (Antrag liegt vor, wird nicht ausgefuehrt).
        if erg.antrag_id and self.notify is not None:
            titel = (erg.idee.splitlines()[0][:70] if erg.idee else "Vorschlag")
            try:
                self.notify(f"Neuer Vorschlag: {titel}. Zum Entscheiden antworte mir: 'gib {erg.antrag_id} "
                            f"frei' oder 'lehn {erg.antrag_id} ab'.",
                            abteilung=f"{abteilung} (Selbst-Entwicklung)", kategorie="freigabe",
                            quelle="self-dev", detail=erg.idee)
            except Exception:
                pass
        return SelfDevErgebnis(abteilung=abteilung, idee=erg.idee, machbarkeit=erg.machbarkeit,
                               kostenvoranschlag=erg.kostenvoranschlag, antrag_id=erg.antrag_id)

    def lauf(self, abteilungen: list[str] | None = None) -> dict:
        """Geplanter Mehr-Bereichs-Lauf -- GATED (Token-/Notbremsen-Schutz).

        Aus, solange `enabled=False` oder die Autonomie pausiert ist. Begrenzt auf `max_pro_lauf` Bereiche.
        """
        if self.watch is not None and getattr(self.watch.store, "paused", lambda: False)():
            return {"ok": False, "hinweis": "Autonomie pausiert (Notbremse) -- kein Selbst-Entwicklungs-Lauf."}
        if not self.enabled:
            return {"ok": False, "hinweis": "Selbst-Entwicklungs-Loop ist aus (SELF_DEV_ENABLED=1 nötig). "
                    "On-demand über das Tool selbstentwicklung."}
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
