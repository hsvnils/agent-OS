"""Phase 24 Baustein (c) -- Skill-Security-Gate (gepruefter Skill-Import).

Prueft einen Skill (Ordner mit `SKILL.md` + evtl. Skripten) **VOR der Uebernahme** mit dem Phase-22-
Sicherheits-Gate -- und **fuehrt ihn NIE aus** (rein statisch, deterministisch, kein LLM). Motivation:
importierte Community-Skills mit Skripten sind ~2x haeufiger verwundbar (SkillSpector) -> jeder Fremd-Skill
laeuft zuerst hier durch.

Wiederverwendung des bestehenden Gates (kein Doppel-Code):
- **Injection-/PII-Scan** des `SKILL.md`-Instruktionstextes ueber `input_guard.pruefe`
  (ein Skill kann Prompt-Injection in seiner Anleitung verstecken).
- **AST-Scan** der Python-Skripte ueber `SecurityAgent._einstufen_call`
  (os.system/os.popen, eval/exec, subprocess(shell=True), pickle, yaml.load ohne Loader, __import__).
- **Shell-Heuristik** fuer `*.sh`/`*.bash` (wir parsen Shell nicht per AST): `curl|bash`, `rm -rf`, `sudo`, `eval`.
- **Score/Finding/SARIF** aus `security_agent`.

**Governance:** Dieses Gate ist die *technische Vorpruefung*. Ein Fremd-Skill bleibt zusaetzlich **CEO-Tor**
(AGENTS.md 5.4) -- das Gate ersetzt die CEO-Freigabe NICHT, es bereitet sie vor (Exit-Code-/Verdikt-Logik).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import input_guard, skill_format
from .security_agent import Finding, SecurityAgent, _SCORE_PUNKTE, nach_sarif

# Shell-Muster, die eine Ablehnung (hoch) bzw. manuelle Pruefung (mittel) ausloesen.
_SHELL_RISKANT: list[tuple[str, str, re.Pattern]] = [
    ("hoch", "remote-code-exec", re.compile(r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba)?sh\b", re.I)),
    ("hoch", "destruktiv", re.compile(r"\brm\s+-rf\b", re.I)),
    ("hoch", "code-eval", re.compile(r"\beval\b", re.I)),
    ("mittel", "privilegien", re.compile(r"\bsudo\b", re.I)),
]

# Verdikt -> Exit-Code (fuer CI/Pipeline-Gate, analog SkillSpector).
_EXIT_CODE = {"bestanden": 0, "pruefen": 1, "abgelehnt": 2}


@dataclass
class GateErgebnis:
    verdikt: str                                    # "bestanden" | "pruefen" | "abgelehnt"
    score: int                                      # 0-100 (Phase-22-Gewichtung)
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockiert(self) -> bool:
        """True nur bei hartem Fail (mind. ein 'hoch'-Fund) -- Import darf nicht uebernommen werden."""
        return self.verdikt == "abgelehnt"

    @property
    def exit_code(self) -> int:
        return _EXIT_CODE.get(self.verdikt, 1)

    def sarif(self) -> dict:
        return nach_sarif(self.findings, tool_name="LUNA-SkillGate")

    def zusammenfassung(self) -> str:
        n = len([f for f in self.findings if f.schwere != "ok"])
        return f"Skill-Gate: {self.verdikt.upper()} (Risiko-Score {self.score}/100, {n} Befund(e))"


def _scan_python(root: Path) -> list[Finding]:
    """AST-Scan aller *.py im Skill -> riskante Aufrufe (Reuse der Phase-22-Einstufung)."""
    treffer: list[tuple[str, str, int, str]] = []
    out: list[Finding] = []
    for pfad in sorted(root.rglob("*.py")):
        try:
            baum = ast.parse(pfad.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            out.append(Finding("skill-code", "mittel", "Python-Datei nicht parsebar",
                               pfad.name, "Manuell pruefen -- absichtlich verschleierter Code?"))
            continue
        rel = pfad.relative_to(root).as_posix()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Call):
                befund = SecurityAgent._einstufen_call(knoten)
                if befund:
                    treffer.append((befund[0], rel, getattr(knoten, "lineno", 0), befund[1]))
    if treffer:
        def _z(ts):
            return "; ".join(f"{d}:{z} ({m})" for _, d, z, m in ts[:8])
        hoch = [t for t in treffer if t[0] == "hoch"]
        mittel = [t for t in treffer if t[0] == "mittel"]
        if hoch:
            out.append(Finding("skill-code", "hoch", f"{len(hoch)} riskante(r) Code-Aufruf(e) im Skill",
                               _z(hoch), "Skill NICHT uebernehmen (kein shell=True/eval/exec/os.system "
                               "in Fremd-Skripten)."))
        if mittel:
            out.append(Finding("skill-code", "mittel", f"{len(mittel)} potenziell riskante(r) Code-Aufruf(e)",
                               _z(mittel), "Manuell pruefen (yaml.safe_load; kein pickle auf Fremddaten)."))
    return out


def _scan_shell(root: Path) -> list[Finding]:
    """Heuristik-Scan der Shell-Skripte (kein AST fuer Shell verfuegbar)."""
    treffer: list[tuple[str, str, str]] = []                 # (schwere, datei, muster)
    for pfad in sorted(list(root.rglob("*.sh")) + list(root.rglob("*.bash"))):
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = pfad.relative_to(root).as_posix()
        for schwere, muster, rx in _SHELL_RISKANT:
            if rx.search(text):
                treffer.append((schwere, rel, muster))
    out: list[Finding] = []
    hoch = [t for t in treffer if t[0] == "hoch"]
    mittel = [t for t in treffer if t[0] == "mittel"]
    if hoch:
        out.append(Finding("skill-shell", "hoch", f"{len(hoch)} gefaehrliche(s) Shell-Muster",
                           "; ".join(f"{d} ({m})" for _, d, m in hoch[:8]),
                           "Skill NICHT uebernehmen (Remote-Exec/rm -rf/eval in Shell)."))
    if mittel:
        out.append(Finding("skill-shell", "mittel", f"{len(mittel)} zu pruefende(s) Shell-Muster",
                           "; ".join(f"{d} ({m})" for _, d, m in mittel[:8]),
                           "Manuell pruefen (Privilegien-Eskalation via sudo)."))
    return out


def pruefe_skill(skill_dir) -> GateErgebnis:
    """Statisches Sicherheits-Gate fuer einen Skill-Ordner. Fuehrt NICHTS aus.

    Verdikt: 'abgelehnt' bei mind. einem 'hoch'-Fund (harter Block), 'pruefen' bei mittel/niedrig,
    sonst 'bestanden'. Der Import bleibt in jedem Fall CEO-Tor.
    """
    root = Path(skill_dir)
    findings: list[Finding] = []

    if not root.exists() or not root.is_dir():
        findings.append(Finding("skill-format", "hoch", "Skill-Ordner nicht gefunden",
                               str(skill_dir), "Pfad pruefen."))
        return GateErgebnis("abgelehnt", 100, findings)

    # 0. Format-Konformitaet (Baustein a): SKILL.md-Existenz + skill-card-Pflichtfelder.
    findings += skill_format.validiere(root)

    # 1. Instruktionstext (SKILL.md) auf Injection/Manipulation + PII
    md = root / "SKILL.md"
    if md.exists():
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            text = ""
        b = input_guard.pruefe(text)
        if b.injection:
            findings.append(Finding("skill-instruktion", "hoch",
                               "Prompt-Injection-/Manipulationsmuster in SKILL.md",
                               "Muster: " + ", ".join(b.injection),
                               "Skill NICHT uebernehmen -- die Anleitung versucht, das System zu manipulieren."))
        if b.pii:
            findings.append(Finding("skill-instruktion", "niedrig", "PII in SKILL.md",
                               "Enthalten: " + ", ".join(b.pii),
                               "Vor Uebernahme PII entfernen/redigieren."))

    # 2. Python-Skripte (AST) + 3. Shell-Skripte (Heuristik)
    findings += _scan_python(root)
    findings += _scan_shell(root)

    luecken = [f for f in findings if f.schwere != "ok"]
    score = min(100, sum(_SCORE_PUNKTE.get(f.schwere, 0) for f in luecken))
    if any(f.schwere == "hoch" for f in luecken):
        verdikt = "abgelehnt"
    elif luecken:
        verdikt = "pruefen"
    else:
        verdikt = "bestanden"
    return GateErgebnis(verdikt, score, findings)
