"""Execution-Engine (Phase 7): setzt FREIGEGEBENE Antraege isoliert um.

Sicherheits-Invarianten:
- Nur Antraege mit Status `freigegeben` werden ausgefuehrt (Doppelpruefung).
- Arbeit in einem Git-Worktree auf Branch `antrag/<id>` -- niemals direkt auf main, kein Merge ohne CEO.
- Tests sind Pflicht: rote Self-Checks -> Status `fehlgeschlagen`.
- Charten (`agents/`) und kanonische Regeln (`AGENTS.md`/`CLAUDE.md`) sind geschuetzt: nur mit ausdruecklich
  als `mandat` freigegebenem Antrag aenderbar (AGENTS.md 3.3).
- Leck-Schutz: keine Secrets in Berichten/Logs.

Die Abhaengigkeiten (Workspace/Agent/Tests/Diff) sind **injizierbar** -> offline mit Mocks testbar (ohne
Kosten), live mit echten Implementierungen (Git-Worktree + Coding-Agent + Self-Checks).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..governance.leak_guard import redact

# Pfade, die nur mit explizit dafuer freigegebenem Antrag (kategorie=mandat) geaendert werden duerfen.
_GESCHUETZT = ("agents/", "agents.md", "claude.md")


@dataclass
class ExecutionResult:
    ok: bool
    status: str            # erledigt | fehlgeschlagen | abgelehnt
    branch: str = ""
    tests_ok: bool = False
    bericht: str = ""


class ExecutionEngine:
    def __init__(self, antraege, *,
                 make_workspace: Callable[[str], tuple[str, str]],
                 run_agent: Callable[[str, str], str],
                 run_tests: Callable[[str], tuple[bool, str]],
                 diff: Callable[[str], str],
                 secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None):
        self.antraege = antraege
        self.make_workspace = make_workspace   # (antrag_id) -> (workspace_pfad, branch)
        self.run_agent = run_agent             # (task, cwd) -> Agent-Ausgabe
        self.run_tests = run_tests             # (cwd) -> (ok, ausgabe)
        self.diff = diff                       # (cwd) -> git-diff-Text
        self.secrets = secrets or []
        self.changelog = changelog

    def umsetzen(self, antrag_id: str) -> ExecutionResult:
        a = self.antraege.get(antrag_id)
        if a is None:
            return ExecutionResult(False, "abgelehnt", bericht="Antrag nicht gefunden.")
        if a.get("status") != "freigegeben":
            return ExecutionResult(
                False, "abgelehnt",
                bericht=f"Antrag {antrag_id} ist nicht freigegeben (Status: {a.get('status')}).",
            )
        # Charta-/Governance-Schutz
        scope = (str(a.get("betroffen", "")) + " " + str(a.get("beschreibung", ""))).lower()
        if any(p in scope for p in _GESCHUETZT) and a.get("kategorie") != "mandat":
            return ExecutionResult(
                False, "abgelehnt",
                bericht="Antrag wuerde geschuetzte Dateien (Charten/kanonische Regeln) aendern -- "
                        "nur mit ausdruecklicher Mandats-Freigabe.",
            )

        self.antraege.status_setzen(antrag_id, "in_umsetzung")
        workspace, branch = self.make_workspace(antrag_id)
        task = self._task(a)
        try:
            agent_out = self.run_agent(task, workspace)
        except Exception as exc:
            self.antraege.status_setzen(antrag_id, "fehlgeschlagen", grund=str(exc)[:200])
            return ExecutionResult(False, "fehlgeschlagen", branch=branch,
                                   bericht=self._redact(f"Ausfuehrung fehlgeschlagen: {exc}"))

        tests_ok, test_out = self.run_tests(workspace)
        diff_text = self.diff(workspace)
        status = "erledigt" if tests_ok else "fehlgeschlagen"
        self.antraege.status_setzen(antrag_id, status)
        if self.changelog:
            self.changelog("Head of Agents", f"Antrag {antrag_id} {status} (Branch {branch})",
                           "Execution-Engine (Phase 7)", branch)
        bericht = self._bericht(antrag_id, branch, a, tests_ok, test_out, diff_text, agent_out)
        return ExecutionResult(tests_ok, status, branch=branch, tests_ok=tests_ok, bericht=bericht)

    # -- intern --

    def _task(self, a: dict) -> str:
        return (
            "Setze folgenden FREIGEGEBENEN Antrag um. Arbeite ausschliesslich in diesem Verzeichnis. "
            "Aendere KEINE Charten (agents/) und keine kanonischen Regeln (AGENTS.md/CLAUDE.md). "
            "Halte dich knapp an die Aufgabe; fuehre am Ende die Self-Checks aus.\n\n"
            f"Titel: {a.get('titel', '')}\nBeschreibung: {a.get('beschreibung', '')}"
        )

    def _bericht(self, antrag_id, branch, a, tests_ok, test_out, diff_text, agent_out) -> str:
        diff_kurz = "\n".join(diff_text.splitlines()[:20])
        text = (
            f"Antrag {antrag_id} -- {a.get('titel', '')}\n"
            f"Branch: {branch}\n"
            f"Tests: {'gruen' if tests_ok else 'ROT'} ({test_out.strip()[:120]})\n"
            f"Ergebnis-Notiz: {str(agent_out).strip()[:300]}\n"
            f"Aenderungen (Auszug):\n{diff_kurz}\n"
            f"Naechster Schritt: Branch pruefen und mergen (manuell oder per Bestaetigung)."
        )
        return self._redact(text)

    def _redact(self, s: str) -> str:
        return redact(s, self.secrets)
