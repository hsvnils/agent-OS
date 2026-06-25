"""Phase 9 -- Innovations-Pipeline (Unternehmensberater).

Orchestriert die bestehenden Bausteine zu einem entscheidungsreifen Vorschlag:

    Beobachten (Web-Recherche, Phase 8)
        -> Idee (Unternehmensberater, Agent 01)
        -> Bewertung: Machbarkeit (CTO) + Kostenvoranschlag (CFO)
        -> Antrag (Phase 6), den der CEO ueber den HoA entscheidet.

**Kein Ausfuehren** -- der Output ist ein Antrag (Status `eingereicht`). Damit bleibt das Mensch-Tor hart:
Umsetzung erst nach CEO-Freigabe (Phase 7). Leck-geschuetzt; Modell-Backend ist injizierbar (Offline-Tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..governance.leak_guard import redact


@dataclass
class InnovationErgebnis:
    thema: str
    befund: str = ""
    quellen: list[str] = field(default_factory=list)
    idee: str = ""
    machbarkeit: str = ""
    kostenvoranschlag: str = ""
    antrag_id: str | None = None


class InnovationPipeline:
    """Berater-getriebener Workflow; nutzt Web (Researcher), Modell-Backend und den Antrags-Store."""

    def __init__(self, core, *, web=None, antraege=None, secrets: list[str] | None = None):
        self.core = core            # HeadOfAgents: backend + subagents
        self.web = web              # WebResearch (optional)
        self.antraege = antraege    # Antraege (optional)
        self.secrets = secrets or []

    def run(self, thema: str = "Neue Entwicklungen bei KI-Agenten") -> InnovationErgebnis:
        erg = InnovationErgebnis(thema=thema)

        # 1. Beobachten -- Web-Recherche (ueber den Researcher/Web-Router), wenn verfuegbar.
        if self.web is not None:
            r = self.web.recherchiere(f"Aktuelle Entwicklungen, Tools und Best Practices: {thema}")
            if getattr(r, "ok", False):
                erg.befund = redact(r.zusammenfassung or "\n".join(
                    f"- {t.titel}: {t.auszug}" for t in r.treffer if t.titel), self.secrets)
                erg.quellen = [t.url for t in r.treffer if t.url]

        # 2. Idee -- Unternehmensberater (Agent 01).
        erg.idee = self._frag(
            "berater",
            "Du bist der Unternehmensberater (Innovation). Schlage GENAU EINE konkrete, umsetzbare "
            "Weiterentwicklung fuer dieses KI-Agenten-Unternehmen vor: erste Zeile ein praegnanter Titel, "
            "danach 2-3 Saetze Nutzen/Begruendung. Beziehe den Recherche-Befund ein, wenn vorhanden.\n\n"
            f"Thema: {thema}\n\nRecherche-Befund:\n{erg.befund or '(keine Recherche)'}")

        # 3. Bewertung -- CTO (Machbarkeit) + CFO (Kostenvoranschlag).
        erg.machbarkeit = self._frag(
            "cto", "Bewerte knapp die technische Machbarkeit, den Aufwand und Risiken dieser Idee "
            "(3-5 Saetze):\n\n" + erg.idee)
        erg.kostenvoranschlag = self._frag(
            "cfo", "Erstelle einen knappen Kostenvoranschlag (einmalige + laufende monatliche Kosten, grob) "
            "fuer diese Idee:\n\n" + erg.idee)

        # 4. Antrag -- entscheidungsreif buendeln (Phase 6). Keine Ausfuehrung.
        if self.antraege is not None:
            beschreibung = (
                f"Idee (Unternehmensberater):\n{erg.idee}\n\n"
                f"Technische Machbarkeit (CTO):\n{erg.machbarkeit}\n\n"
                f"Kostenvoranschlag (CFO):\n{erg.kostenvoranschlag}\n\n"
                f"Quellen: {', '.join(erg.quellen) if erg.quellen else '(keine)'}")
            erg.antrag_id = self.antraege.stellen(
                _titel(erg.idee), beschreibung, von="Unternehmensberater (Innovation)",
                kategorie="Innovation/Beschaffung (Kosten pruefen)")
        return erg

    def _frag(self, agent_key: str, prompt: str) -> str:
        spec = self.core.subagents.get(agent_key)
        system_prompt = spec.system_prompt if spec else ""
        try:
            out = self.core.backend.respond(agent_key, system_prompt, prompt, {})
        except Exception as exc:  # Modell-/Backend-Fehler nicht durchreichen
            return f"(nicht verfuegbar: {str(exc)[:120]})"
        return redact(out, self.secrets)


def _titel(idee: str) -> str:
    """Erste nicht-leere Zeile als Kurztitel (max. 80 Zeichen)."""
    for line in (idee or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:80]
    return "Innovations-Vorschlag"
