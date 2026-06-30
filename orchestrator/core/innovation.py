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
        erg.kostenvoranschlag = self._frag("cfo", _CFO_PROMPT + erg.idee)

        # 4. Antrag -- entscheidungsreif buendeln (Phase 6). Keine Ausfuehrung.
        if self.antraege is not None:
            von = ("Unternehmensberater (Innovation)" if abteilung == "berater"
                   else f"{abteilung} (Selbst-Entwicklung)")
            titel = _titel(erg.idee)
            quellen = ", ".join(erg.quellen) if erg.quellen else "(aus dem Wissensstand)"
            beschreibung = _baue_beschreibung(von, titel, erg.idee, erg.machbarkeit,
                                              erg.kostenvoranschlag, quellen)
            erg.antrag_id = self.antraege.stellen(
                titel, beschreibung, von=von,
                kategorie="Innovation/Beschaffung (Kosten pruefen)")
        return erg

    def revidiere(self, antrag_id: str, feedback: str = "", *, neutral: bool = False) -> dict:
        """Ueberarbeitet einen bestehenden Antrag anhand von CEO-Feedback (z. B. 'guenstiger/kostenlos')
        und setzt ihn auf 'eingereicht' zurueck (Neufreigabe noetig). neutral=True: nur sauber neu
        formatieren, Inhalt in der Sache beibehalten. Laeuft ueber die Fachagenten (Gemini-Fallback)."""
        if self.antraege is None:
            return {"ok": False, "fehler": "Kein Antrags-Store."}
        a = self.antraege.get(antrag_id)
        if a is None:
            return {"ok": False, "fehler": f"Antrag {antrag_id} nicht gefunden."}
        von = a.get("von", "Head of Agents")
        alt = a.get("beschreibung", "")
        fb = (feedback or "").strip()
        if neutral or not fb:
            auftrag = ("Bring den folgenden Vorschlag inhaltlich unveraendert, aber knapp auf den Punkt: "
                       "erste Zeile praegnanter Titel, dann 2-4 Saetze Loesung/Nutzen.")
            ceo = ""
        else:
            auftrag = ("Ueberarbeite den folgenden Vorschlag anhand des CEO-Feedbacks. Finde wo immer moeglich "
                       "GUENSTIGERE oder KOSTENLOSE Wege (Open-Source/Freeware/vorhandene Mittel/manuell). "
                       f"CEO-Feedback: '{fb}'. Erste Zeile praegnanter Titel, dann 2-4 Saetze Loesung/Nutzen.")
            ceo = f"\nCEO-Vorgabe: {fb}"
        idee = self._frag(_agent_fuer(von), auftrag + "\n\nBestehender Vorschlag:\n" + alt[:1500])
        machbarkeit = self._frag("cto", "Bewerte knapp Machbarkeit/Aufwand/Risiken (3-5 Saetze):\n\n" + idee)
        kosten = self._frag("cfo", _CFO_PROMPT + idee + ceo)
        titel = _titel(idee)
        beschreibung = _baue_beschreibung(von, titel, idee, machbarkeit, kosten,
                                          "(aus dem Wissensstand)", revision=(None if neutral else fb))
        self.antraege.revidieren(antrag_id, titel=titel, beschreibung=beschreibung,
                                 grund=("Revision: " + fb) if fb else "Neu formatiert")
        return {"ok": True, "antrag_id": antrag_id, "titel": titel}

    def neu_formatieren(self) -> dict:
        """Batch: alle nicht-finalen Antraege sauber ins neue Format bringen; freigegebene werden dabei
        auf 'eingereicht' zurueckgesetzt (Neufreigabe noetig)."""
        if self.antraege is None:
            return {"ok": False, "fehler": "Kein Antrags-Store."}
        verarbeitet = []
        for a in self.antraege.list():
            if a.get("status") in ("erledigt", "abgelehnt", "geloescht"):
                continue
            r = self.revidiere(a["antrag_id"], "", neutral=True)
            verarbeitet.append({"id": a["antrag_id"], "ok": bool(r.get("ok"))})
        return {"ok": True, "anzahl": len(verarbeitet), "verarbeitet": verarbeitet}

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


# Einheitliches, auf einen Blick erfassbares CFO-Format (EUR, Stufen, Nutzen, Kostentreiber).
_CFO_PROMPT = (
    "Erstelle einen KNAPPEN, auf einen Blick erfassbaren Kostenvoranschlag in EURO. "
    "Genau dieses Format, hoechstens ~7 Zeilen, KEINE Tabellen, KEINE Pipes (|), KEINE Sterne:\n"
    "Zeile 1 MUSS exakt so beginnen: 'KOSTEN: ~<einmalig> EUR einmalig, ~<laufend> EUR/Monat'.\n"
    "Dann (falls sinnvoll) 'Stufen:' mit 2 Varianten und ihrem UNTERSCHIED, z. B.:\n"
    "  - Sparvariante (~20 EUR/Monat): <was man dafuer bekommt>\n"
    "  - Mehr (~40 EUR/Monat): <was zusaetzlich dazukommt>\n"
    "Wenn es kostenlos/mit Bordmitteln geht, sag das klar (KOSTEN: 0 EUR ...).\n"
    "Dann 'Nutzen: <ein Satz: was es bringt/spart, wann es sich rechnet>'.\n"
    "Dann 'Kostentreiber: <der eine Haupt-Hebel, der die Kosten bestimmt>'.\n"
    "Schaetze grob; nenne Spannen. Fuer diese Idee:\n\n")


def _baue_beschreibung(von: str, titel: str, idee: str, machbarkeit: str, kosten: str,
                       quellen: str, *, revision: str | None = None) -> str:
    """Klar gegliederter, markdown-freier Antrag; Kosten-Kernzeile ganz oben (auf einen Blick)."""
    kosten_clean = _clean(kosten)
    kopf = _kosten_kopf(kosten_clean)
    teile = []
    if kopf:
        teile.append(kopf)
    if revision:
        teile.append(f"↻ REVIDIERT (CEO-Feedback): {revision}")
    if teile:
        teile.append("")  # Leerzeile nach dem Kopf
    teile += [
        f"IDEE ({von})\n{_clean(idee, titel)}", "",
        f"MACHBARKEIT (CTO)\n{_clean(machbarkeit)}", "",
        f"KOSTEN (CFO)\n{kosten_clean}", "",
        f"QUELLEN\n{quellen}",
    ]
    return "\n".join(teile)


def _agent_fuer(von: str) -> str:
    """Leitet aus dem 'von'-Feld den zustaendigen Fachagenten ab (Self-Dev: der Bereich; sonst Berater)."""
    v = (von or "").lower()
    for key in ("cto", "cfo", "cro", "ciso", "cbo", "cpo", "cxo", "cco", "cdo", "clo", "cko", "cao", "chro"):
        if v.startswith(key):
            return key
    return "berater"


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
