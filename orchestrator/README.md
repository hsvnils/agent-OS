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

## Start (GATE B — echter Mini-Lauf)

Nach Eintragen des `ANTHROPIC_API_KEY` und `dry_run = false`:

```sh
python orchestrator/run.py
```

## Status

- **Phase 1 (jetzt):** Geruest, Konfiguration, Governance-Dokumente angelegt.
- **Ausstehend:** Python-Module (Kern, Adapter, Hooks, Tests) — werden umgesetzt, sobald ein
  Python-Interpreter verfuegbar ist (Self-Checks muessen ausfuehrbar sein). Danach GATE B fuer den
  echten Mini-Lauf.
