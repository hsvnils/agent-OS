"""Reale Abhaengigkeiten der Execution-Engine (Phase 7, LIVE, billbar).

Stellt die injizierbaren Funktionen der `ExecutionEngine` mit echten Implementierungen bereit:
- `real_make_workspace`: Git-Worktree auf Branch `antrag/<id>` (isoliert, main bleibt unberuehrt).
- `real_run_agent`: Coding-Agent (Claude Agent SDK mit Datei-/Bash-Tools) im Worktree (Opus).
- `real_run_tests`: Offline-Self-Checks im Worktree.
- `real_diff`: staged Diff-Stat als Bericht-Grundlage.
- `cleanup_workspace` / `merge_branch`: Worktree entfernen bzw. Branch nach main mergen (nur mit CEO).

Wird ausschliesslich ueber die ExecutionEngine fuer FREIGEGEBENE Antraege benutzt.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

EXECUTION_RULES = (
    "Du bist ein Ausfuehrungs-Agent eines Agenten-Unternehmens. Setze die Aufgabe um, indem du Dateien in "
    "DIESEM Arbeitsverzeichnis anlegst oder aenderst. Halte dich strikt an die Aufgabe und arbeite minimal. "
    "Aendere NIEMALS Charten (Ordner agents/) oder kanonische Regeln (AGENTS.md, CLAUDE.md). Keine "
    "destruktiven Aktionen (kein rm -rf, kein git history rewrite), nichts ausserhalb des Verzeichnisses. "
    "In .md-Dateien keine Umlaute (ae/oe/ue/ss). Antworte am Ende mit 1-2 Saetzen: was geaendert wurde und "
    "was der CEO pruefen sollte."
)


def _git(repo: str, *args, check=False):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check)


def real_make_workspace(repo_root):
    repo_root = Path(repo_root)

    def make(antrag_id: str):
        branch = f"antrag/{antrag_id}"
        ws = repo_root / ".worktrees" / f"antrag-{antrag_id}"
        # Defensiv: Bind-Mount-Repo (Eigentuemer != Prozess-User) sonst "dubious ownership" -> exit 128.
        _git(repo_root, "config", "--global", "--add", "safe.directory", str(repo_root))
        if ws.exists():
            _git(repo_root, "worktree", "remove", "--force", str(ws))
        _git(repo_root, "worktree", "prune")             # verwaiste Worktree-Eintraege aufraeumen
        _git(repo_root, "branch", "-D", branch)          # evtl. alten Branch entfernen (Fehler ignoriert)
        _git(repo_root, "worktree", "add", "-b", branch, str(ws), "HEAD", check=True)
        return (str(ws), branch)

    return make


def real_run_agent(model: str = "claude-opus-4-8", max_turns: int = 30):
    def run(task: str, cwd: str) -> str:
        return asyncio.run(_arun(task, cwd, model, max_turns))
    return run


async def _arun(task: str, cwd: str, model: str, max_turns: int) -> str:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

    options = ClaudeAgentOptions(
        system_prompt=EXECUTION_RULES,
        model=model,
        cwd=cwd,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="bypassPermissions",  # isolierter Worktree-Branch
        setting_sources=[],
        mcp_servers={},
        strict_mcp_config=True,
        max_turns=max_turns,
        env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
    )
    parts: list[str] = []
    async for msg in query(prompt=task, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
    return "".join(parts).strip()


def real_run_tests(python_exe: str | None = None):
    py = python_exe or sys.executable

    def run(cwd: str):
        r = subprocess.run(
            [py, "-m", "unittest", "discover", "-s", "orchestrator/tests", "-t", "."],
            cwd=cwd, capture_output=True, text=True, timeout=300,
        )
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-3:])
        return (r.returncode == 0, tail)

    return run


def real_diff():
    def run(cwd: str) -> str:
        _git(cwd, "add", "-A")
        return _git(cwd, "diff", "--cached", "--stat").stdout.strip()
    return run


def commit_branch(cwd: str, message: str) -> bool:
    _git(cwd, "add", "-A")
    r = _git(cwd, "commit", "-m", message)
    return r.returncode == 0


def merge_branch(repo_root, branch: str, message: str) -> tuple[bool, str]:
    """Mergt den Antrags-Branch nach main (nur auf CEO-Bestaetigung aufrufen)."""
    r = _git(repo_root, "merge", "--no-ff", "-m", message, branch)
    return (r.returncode == 0, (r.stdout + r.stderr).strip()[:300])


def cleanup_workspace(repo_root, antrag_id: str) -> None:
    ws = Path(repo_root) / ".worktrees" / f"antrag-{antrag_id}"
    _git(repo_root, "worktree", "remove", "--force", str(ws))
