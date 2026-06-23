# orchestrator/ — Bootstrap-Orchestrator (HoA + CTO + Berater)

Laufzeit-Schicht des Agenten-Unternehmens auf Basis des **Claude Agent SDK (Python)**. In dieser
Bootstrap-Stufe sind **genau drei** Agenten real verdrahtet: **Head of Agents**, **CTO** und
**Unternehmensberater**. Plan und Begruendung: [`../ORCHESTRATOR_PLAN.md`](../ORCHESTRATOR_PLAN.md).

> `AGENTS.md` (Repo-Root) bleibt kanonisch und uebergeordnet. Charten sind die Single Source of Truth fuer
> System-Prompts; dieser Code dupliziert sie nicht, sondern liest sie zur Laufzeit.

## Voraussetzungen

- **Python 3.11+** (auf diesem Rechner aktuell NICHT installiert — siehe Hinweis unten).
- Abhaengigkeiten (geplant): `claude-agent-sdk`, `anthropic`, `pytest` (fuer Self-Checks).

## Einrichtung (geplant)

```sh
# 1. Python 3.11+ installieren (z. B. python.org oder winget: 'winget install Python.Python.3.12')
# 2. Virtuelle Umgebung
python -m venv orchestrator/.venv
# 3. Aktivieren (Windows PowerShell): orchestrator/.venv/Scripts/Activate.ps1
# 4. Abhaengigkeiten
pip install claude-agent-sdk anthropic pytest
# 5. Secrets-Vorlage kopieren und ausfuellen (GATE B)
cp orchestrator/.env.example orchestrator/.env   # ANTHROPIC_API_KEY eintragen
```

## Self-Checks (offline, ohne echte Kosten)

Im **Dry-Run-/Mock-Modus** (`config.toml: dry_run = true`) laufen die Self-Checks ohne API-Key und ohne
Kosten:

```sh
pytest orchestrator/tests -v
```

## Start (GATE B — echter Mini-Lauf, billbar)

Voraussetzungen fuer den Live-Pfad:

```sh
# 1. Agent-SDK + Claude CLI (das SDK ruft die CLI auf)
pip install claude-agent-sdk
npm install -g @anthropic-ai/claude-code      # Claude CLI
# 2. Key eintragen (GATE B)
cp orchestrator/.env.example orchestrator/.env   # ANTHROPIC_API_KEY ausfuellen
# 3. In config.toml: dry_run = false
# 4. Starten
python -m orchestrator.run
```

> Hinweis: Der Live-Lauf verursacht **echte Modell-Kosten** und braucht die Claude CLI. Bis dahin laeuft
> alles im Dry-Run (Mock) ohne Kosten.

## Status

- **Phase 1-4 (fertig):** Geruest, Konfiguration, Governance-Dokumente; Kern (`core/`), Kanal-Adapter
  (`channels/`), Governance-Hooks/Tools (`governance/`), Beobachtbarkeit (`observability/`), Einstieg
  `run.py`. **Self-Checks: 10/10 OK** (Dry-Run/Mock, ohne Kosten).
- **GATE B (offen):** echter Mini-Lauf ueber den Terminal-Adapter. Benoetigt `claude-agent-sdk`, Claude CLI
  und `ANTHROPIC_API_KEY`. Der `AgentSdkBackend` ist gegen die offiziellen SDK-Bindings gebaut und wird beim
  Mini-Lauf erstmals real ausgefuehrt.
