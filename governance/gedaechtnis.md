# Gedaechtnis-Policy (Agenten-Memory)

> Lebendes Steuerungsdokument, `AGENTS.md` untergeordnet. Beschreibt, wie das Orchestrator-Gedaechtnis
> gefuehrt wird. Umsetzung: `orchestrator/core/memory.py`; Plan: `MEMORY_PLAN.md`.

## Zweck

Die Orchestrator-Agenten sollen sich ueber Auftraege und Sitzungen hinweg an Anweisungen, Delegationen,
Ergebnisse und Eskalationen erinnern. Das Gedaechtnis ist **dateibasiert**, **git-versioniert** und
**auditierbar** — kein externer Dienst (kein CEO-Tor, keine Kosten).

## Abgrenzung zum Changelog

- `projekt_changelog.md` = Datei-/Struktur-Provenienz.
- Gedaechtnis (`orchestrator/memory/log.jsonl`) = Aufgaben-/Entscheidungs-Erinnerung.

Keine Inhalte doppelt fuehren.

## Isolation vom persoenlichen Claude-Code-Memory

Das Firmen-Gedaechtnis liegt ausschliesslich unter `orchestrator/memory/`. Es ist **getrennt** vom
persoenlichen Claude-Code-Memory des menschlichen Nutzers (`~/.claude/.../memory/`). Die gebundelte
Claude-CLI laedt ihr Auto-Memory-Verzeichnis in Subagenten; dieses Auto-Laden wird fuer die Orchestrator-
Subagenten unterbunden, damit Firmen-Agenten nur das Firmen-Gedaechtnis sehen (Status/Umsetzung siehe
`MEMORY_PLAN.md`, Abschnitt 3).

## Leck-Schutz & Konventionen

- Jeder Eintrag laeuft vor dem Schreiben durch `redact()` — keine `.env`-Werte im Store.
- JSONL-Store ist von der Markdown-Umlaut-Regel ausgenommen; alle `.md` bleiben umlautfrei.
- Dry-Run schreibt nach `orchestrator/memory/log_dryrun.jsonl` (gitignored).

## Retention

Vorerst append-only ohne Pruning. Aufraeumen/Verdichten ist eine spaetere, separat freizugebende Ausbaustufe
(ebenso semantische Suche/Embeddings und eine Datenbank-Anbindung, z. B. Supabase).
