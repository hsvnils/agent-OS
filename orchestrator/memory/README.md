# orchestrator/memory/ — Agenten-Gedaechtnis

Schlanker, dateibasierter Store fuer das **Aufgaben-/Entscheidungs-Gedaechtnis** der Orchestrator-Agenten
(Head of Agents, CTO, Berater). Plan/Begruendung: [`../../MEMORY_PLAN.md`](../../MEMORY_PLAN.md).

## Inhalt

- `log.jsonl` — kanonischer, **versionierter** Store. Eine JSON-Zeile pro Auftrag (append-only).
- `log_dryrun.jsonl` — Dry-Run-Store, per `.gitignore` ausgeschlossen (Smoke-/Mock-Laeufe verschmutzen den
  kanonischen Store nicht).

## Abgrenzung (wichtig)

- **Changelog** (`projekt_changelog.md`) = Datei-/Struktur-Provenienz („was wurde geaendert").
- **Dieses Gedaechtnis** = „welcher Auftrag, wie zerlegt, welches Ergebnis, welche offene Eskalation".

Keine Duplikate; beide bestehen nebeneinander.

## Eintragsfelder

`ts`, `session_id`, `instruction`, `delegated_to`, `status` (`ok` | `mit_fehler` | `eskalation`),
`result_digest`, `eskalationen`, `tags`.

## Governance

- Jeder Eintrag laeuft vor dem Schreiben durch den Leck-Schutz (keine `.env`-Werte im Store).
- Vom **persoenlichen** Claude-Code-Memory (`~/.claude/...`) strikt getrennt (siehe `governance/gedaechtnis.md`).
- JSONL ist von der Markdown-Umlaut-Regel ausgenommen; diese README als `.md` ist umlautfrei.
