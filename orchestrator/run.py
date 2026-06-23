"""Einstieg: startet den HoA-Kern hinter einem Kanal-Adapter.

dry_run=true  -> MockBackend (kein API-Key, keine Kosten).
dry_run=false -> AgentSdkBackend (GATE B: ANTHROPIC_API_KEY noetig, verifizierte Bindings).
"""
from __future__ import annotations

import tomllib
from functools import partial
from pathlib import Path

from orchestrator.channels.terminal import TerminalAdapter
from orchestrator.core.backends import AgentSdkBackend, MockBackend
from orchestrator.core.hoa import HeadOfAgents
from orchestrator.core.subagents import load_default_subagents
from orchestrator.governance.ceo_gate_hook import CeoGate
from orchestrator.governance.changelog_tool import append_changelog
from orchestrator.governance.leak_guard import load_env_secrets
from orchestrator.observability.logging import Logger

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(ROOT / "orchestrator" / "config.toml", "rb") as fh:
        return tomllib.load(fh)


def build_core(cfg: dict) -> HeadOfAgents:
    subagents = load_default_subagents()
    if cfg["run"]["dry_run"]:
        backend = MockBackend()
    else:
        # GATE B: echtes Backend. CEO-Tor zusaetzlich als SDK-PreToolUse-Hook.
        backend = AgentSdkBackend(
            cfg["models"],
            cfg["effort"],
            gate=CeoGate(),
            max_turns=cfg["run"].get("max_turns", 4),
        )
    secrets = load_env_secrets(ROOT / "orchestrator" / ".env")
    # Dry-Run/Smoke-Laeufe verschmutzen das kanonische Changelog NICHT:
    # sie schreiben in ein separates, per .gitignore ausgeschlossenes Log.
    if cfg["run"]["dry_run"]:
        log_dir = ROOT / "orchestrator" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        changelog_path = log_dir / "changelog_dryrun.md"
        if not changelog_path.exists():
            changelog_path.write_text("# Changelog (Dry-Run)\n\n## Eintraege\n", encoding="utf-8")
    else:
        changelog_path = ROOT / cfg["governance"]["changelog_file"]
    changelog = partial(append_changelog, changelog_path)
    return HeadOfAgents(
        backend,
        subagents,
        gate=CeoGate(),
        leak_secrets=secrets,
        changelog=changelog,
        logger=Logger(),
    )


def main() -> None:
    cfg = load_config()
    core = build_core(cfg)
    mode = "DRY-RUN (Mock)" if cfg["run"]["dry_run"] else "LIVE (Agent SDK)"
    print(f"Head of Agents bereit -- {mode}. 'exit' zum Beenden.")
    TerminalAdapter().run(core)


if __name__ == "__main__":
    main()
