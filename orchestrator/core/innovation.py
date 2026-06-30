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

import re
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

    def run(self, thema: str = "Neue Entwicklungen bei KI-Agenten", *, abteilung: str = "berater",
            wissen: str = "") -> InnovationErgebnis:
        """Erzeugt einen bewerteten Vorschlag als Antrag.

        `abteilung`: welcher Fachagent die Idee liefert (Default Berater = firmenweite Innovation; sonst
        Selbst-Weiterentwicklung dieses Bereichs, Phase 13). `wissen`: vorhandener Fachbereichs-Wissensstand
        (spart eine Web-Recherche -> token-frugal).
        """
        erg = InnovationErgebnis(thema=thema)

        # 1. Befund -- vorhandener Wissensstand bevorzugt; sonst Web-Recherche (ueber den Researcher).
        if wissen:
            erg.befund = redact(wissen, self.secrets)
        elif self.web is not None:
            r = self.web.recherchiere(f"Aktuelle Entwicklungen, Tools und Best Practices: {thema}")
            if getattr(r, "ok", False):
                erg.befund = redact(r.zusammenfassung or "\n".join(
                    f"- {t.titel}: {t.auszug}" for t in r.treffer if t.titel), self.secrets)
                erg.quellen = [t.url for t in r.treffer if t.url]

        # 2. Idee -- vom zustaendigen Fachagenten (Berater firmenweit, sonst der Bereich selbst).
        rolle = ("der Unternehmensberater (Innovation)" if abteilung == "berater"
                 else f"der Fachbereich '{abteilung}'")
        erg.idee = self._frag(
            abteilung,
            f"Du bist {rolle}. Schlage GENAU EINE konkrete, umsetzbare Weiterentwicklung in deinem "
            "Verantwortungsbereich vor: erste Zeile ein praegnanter Titel, danach 2-3 Saetze "
            "Nutzen/Begruendung. Stuetze dich auf den aktuellen Wissensstand, wenn vorhanden.\n\n"
            f"Thema: {thema}\n\nWissensstand/Befund:\n{erg.befund or '(keiner)'}")

        # 3. Bewertung -- CTO (Machbarkeit) + CFO (Kostenvoranschlag).
        erg.machbarkeit = self._frag(
            "cto", "Bewerte knapp die technische Machbarkeit, den Aufwand und Risiken dieser Idee "
            "(3-5 Saetze):\n\n" + erg.idee)
        erg.kostenvoranschlag = self._frag(
            "cfo",
            "Erstelle einen KNAPPEN, auf einen Blick erfassbaren Kostenvoranschlag in EURO. "
            "Genau dieses Format, hoechstens ~7 Zeilen, KEINE Tabellen, KEINE Pipes (|), KEINE Sterne:\n"
            "Zeile 1 MUSS exakt so beginnen: 'KOSTEN: ~<einmalig> EUR einmalig, ~<laufend> EUR/Monat'.\n"
            "Dann (falls sinnvoll) 'Stufen:' mit 2 Varianten und ihrem UNTERSCHIED, z. B.:\n"
            "  - Sparvariante (~20 EUR/Monat): <was man dafuer bekommt>\n"
            "  - Mehr (~40 EUR/Monat): <was zusaetzlich dazukommt>\n"
            "Dann 'Nutzen: <ein Satz: was es bringt/spart, wann es sich rechnet>'.\n"
            "Dann 'Kostentreiber: <der eine Haupt-Hebel, der die Kosten bestimmt>'.\n"
            "Schaetze grob; nenne Spannen. Fuer diese Idee:\n\n" + erg.idee)

        # 4. Antrag -- entscheidungsreif buendeln (Phase 6). Keine Ausfuehrung.
        if self.antraege is not None:
            von = ("Unternehmensberater (Innovation)" if abteilung == "berater"
                   else f"{abteilung} (Selbst-Entwicklung)")
            titel = _titel(erg.idee)
            # Klar gegliederter, markdown-freier Antrag (saubere Darstellung in Telegram + LUNA-OS).
            quellen = ", ".join(erg.quellen) if erg.quellen else "(aus dem Wissensstand)"
            kosten = _clean(erg.kostenvoranschlag)
            kopf = _kosten_kopf(kosten)  # die KOSTEN-Kernzeile ganz nach oben (auf einen Blick)
            beschreibung = (
                (f"{kopf}\n\n" if kopf else "")
                + f"IDEE ({von})\n{_clean(erg.idee, titel)}\n\n"
                f"MACHBARKEIT (CTO)\n{_clean(erg.machbarkeit)}\n\n"
                f"KOSTEN (CFO)\n{kosten}\n\n"
                f"QUELLEN\n{quellen}")
            erg.antrag_id = self.antraege.stellen(
                titel, beschreibung, von=von,
                kategorie="Innovation/Beschaffung (Kosten pruefen)")
        return erg

    def _frag(self, agent_key: str, prompt: str) -> str:
        spec = self.core.subagents.get(agent_key)
        system_prompt = spec.system_prompt if spec else ""
        try:
            out = self.core.backend.respond(agent_key, system_prompt, prompt, {})
        except Exception as exc:  # Modell-/Backend-Fehler nicht durchreichen
            return f"(nicht verfügbar — Modell/Backend-Fehler: {str(exc)[:120]})"
        return redact(out, self.secrets)


def _titel(idee: str) -> str:
    """Erste nicht-leere Zeile als Kurztitel (max. 80 Zeichen), ohne Markdown."""
    for line in (idee or "").splitlines():
        line = _strip_md(line)
        if line:
            return line[:80]
    return "Innovations-Vorschlag"


def _strip_md(s: str) -> str:
    """Entfernt Markdown-Schmuck aus einer Zeile (**, *, #, __) und wandelt Tabellen in lesbaren Text."""
    s = s or ""
    if re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", s) and "-" in s:  # Tabellen-Trennzeile |---|---|
        return ""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", s)
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s)
    s = s.replace("**", "").replace("__", "")
    if s.strip().startswith("|") or " | " in s:            # Tabellen-Zeile -> 'a · b · c'
        s = re.sub(r"\s*\|\s*", " · ", s.strip().strip("|")).strip(" ·")
    return s.strip()


def _kosten_kopf(kosten: str) -> str:
    """Holt die KOSTEN-Kernzeile ('KOSTEN: ...') aus dem CFO-Text -- fuer die Anzeige ganz oben."""
    for line in (kosten or "").splitlines():
        s = line.strip()
        if s.upper().startswith("KOSTEN"):
            return "💶 " + s
    return ""


def _clean(text: str, drop_titel: str | None = None) -> str:
    """Markdown-frei + getrimmt; entfernt optional eine fuehrende Zeile, die den Titel dupliziert."""
    zeilen = [_strip_md(z) for z in (text or "").splitlines()]
    # fuehrende Leerzeilen weg
    while zeilen and not zeilen[0]:
        zeilen.pop(0)
    if drop_titel and zeilen and zeilen[0][:80].strip().lower() == _strip_md(drop_titel)[:80].strip().lower():
        zeilen.pop(0)
        while zeilen and not zeilen[0]:
            zeilen.pop(0)
    return "\n".join(zeilen).strip() or "(keine Angabe)"
