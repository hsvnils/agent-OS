# MEMORY_PLAN.md — Agenten-Gedaechtnis (schlank, dateibasiert)

> **Status: PLAN — wartet auf GATE C (CEO-Freigabe).** In diesem Lauf wird **kein** Memory-Laufzeit-Code
> geschrieben. Erst nach Freigabe beginnt die Implementierung (offline, ohne Kosten, mit Self-Checks).
> `AGENTS.md` bleibt kanonisch und uebergeordnet; dieser Plan ist ihr untergeordnet.

---

## 1. Zweck & Scope

Die Agenten (HoA, CTO, Berater) sollen sich **ueber Auftraege und Sitzungen hinweg erinnern** — an
CEO-Anweisungen, Delegationen, Ergebnisse, Eskalationen und Entscheidungen. Heute ist der Kern zustandslos:
jeder `handle()`-Aufruf startet ohne Bezug zu frueheren Auftraegen.

**In diesem Build:** ein **schlanker, dateibasierter, git-versionierter** Memory-Store im Repo, append-only,
auditierbar, **ohne externen Dienst** (kein CEO-Tor, keine Kosten). Der HoA liest relevantes Gedaechtnis vor
der Delegation in seinen Kontext und schreibt nach jedem Auftrag einen Memory-Eintrag.

**Ausdruecklich NICHT in diesem Build:** keine semantische Suche/Embeddings, keine Datenbank/Supabase, keine
externen Speicher (alles spaetere, separat freizugebende GATES).

---

## 2. Abgrenzung zum Changelog (wichtig)

- **`projekt_changelog.md`** = Datei-/Struktur-**Provenienz** („was wurde an Dateien geaendert").
- **Agenten-Gedaechtnis** = **Aufgaben-/Entscheidungs-Erinnerung** („welcher Auftrag, wie zerlegt, welches
  Ergebnis, welche offene Eskalation"). Keine Duplikate — beide bestehen nebeneinander.

---

## 3. Isolation (Pflicht)

Beim GATE-B-Lauf zeigte sich: Die gebundelte Claude-CLI laedt ihr **Auto-Memory-Verzeichnis**
(`~/.claude/.../memory/`) — also das **persoenliche** Gedaechtnis des menschlichen Claude-Code-Nutzers — in
die Subagenten. Das ist eine unerwuenschte Vermischung.

- Das Orchestrator-Gedaechtnis liegt **ausschliesslich** unter `orchestrator/memory/` und ist vom
  persoenlichen Claude-Code-Memory **getrennt**.
- Teil der Umsetzung: das **Auto-Laden** des persoenlichen Memory in den Subagenten **unterbinden** (per
  SDK-Option/`cwd`/Env pruefen und abschalten), damit Firmen-Agenten nur das Firmen-Gedaechtnis sehen.

---

## 4. Form & Struktur

- **Kanonischer Store:** `orchestrator/memory/log.jsonl` — **append-only JSONL**, eine Zeile pro Eintrag
  (robust maschinell les-/schreibbar; nicht `.md`, daher von der Umlaut-Regel ausgenommen — Leck-Schutz gilt
  dennoch).
- **Eintrag (Felder):** `ts` (ISO-Zeit), `session_id`, `instruction` (CEO-Auftrag), `delegated_to`
  (Subagenten), `status` (`ok` | `mit_fehler` | `eskalation`), `result_digest` (kurze Zusammenfassung),
  `eskalationen`, `tags` (abgeleitete Stichworte fuer Recall).
- **Dry-Run:** schreibt in `orchestrator/memory/log_dryrun.jsonl` (per `.gitignore` ausgeschlossen), damit der
  kanonische Store sauber bleibt — analog zum bestehenden `changelog_dryrun.md`-Muster.

---

## 5. Lese-/Schreib-Pfad

- **Lesen (`recall`)** — vor der Delegation ruft der HoA `recall(instruction, limit)`: liefert die letzten N
  Eintraege **plus** stichwort-relevante aeltere Eintraege (einfaches Keyword-/Substring-Matching, **keine**
  Embeddings). Ergebnis wird als kompakter „Gedaechtnis-Kontext"-Block in die HoA-Verarbeitung gegeben.
- **Schreiben (`append`)** — nach dem Buendeln schreibt der HoA genau **einen** Memory-Eintrag pro Auftrag.
- **Leck-Schutz:** jeder Eintrag laeuft vor dem Schreiben durch `redact()` (keine `.env`-Werte im Store).

---

## 6. Dateien & Konfiguration

```
orchestrator/
  core/
    memory.py            # NEU: append(record) / recall(query, limit), dry-run-bewusst, leck-geschuetzt
    hoa.py               # ERWEITERT: recall vor Delegation, append nach Buendeln
  memory/
    log.jsonl            # kanonischer Store (versioniert)
    log_dryrun.jsonl     # Dry-Run (gitignored)
    README.md            # Zweck/Abgrenzung (umlautfrei)
  tests/
    test_memory.py       # NEU: Self-Checks (siehe 7)
  config.toml            # NEU: [memory] enabled, path, recall_limit
governance/
  gedaechtnis.md         # NEU: Memory-Policy (Abgrenzung, Isolation, Retention) -- AGENTS.md untergeordnet
.gitignore               # ERWEITERT: orchestrator/memory/log_dryrun.jsonl
```

---

## 7. Self-Checks (offline, ohne Kosten)

1. **Round-Trip:** `append` -> `recall` findet den Eintrag wieder; Reihenfolge neueste zuerst.
2. **Relevanz:** `recall("stichwort")` liefert den passenden aelteren Eintrag, nicht nur die letzten N.
3. **Leck-Schutz:** ein in den Eintrag gelegter Test-Secret-Wert erscheint **nicht** im Store.
4. **HoA-Integration:** zweiter Auftrag sieht den Gedaechtnis-Kontext des ersten (Mock-Backend; Assertion,
   dass der Kontext injiziert wurde).
5. **Dry-Run-Trennung:** Dry-Run schreibt in `log_dryrun.jsonl`, der kanonische Store bleibt unveraendert.
6. **Isolation:** der Store-Pfad ist `orchestrator/memory/`, nicht das persoenliche Claude-Code-Memory.

Bestehende 12 Self-Checks bleiben gruen; Ziel danach: **>= 18/18 OK**.

---

## 8. Governance

- **Kein CEO-Tor** (lokal, dateibasiert, keine Kosten/kein externer Dienst).
- **Umlaut-Regel** gilt fuer alle neuen `.md` (README, `gedaechtnis.md`); JSONL ist ausgenommen.
- **Changelog-Pflicht** nach jeder Aenderung; **Git-Commit** je Schritt.
- **Retention:** vorerst append-only ohne Pruning; spaeter eigener Schritt.

---

## 9. GATES

- **GATE C (jetzt):** Freigabe dieses `MEMORY_PLAN.md`. Erst danach Implementierung.
- **Danach:** Implementierung offline mit Self-Checks (ohne Kosten).
- **Optionale Live-Verifikation:** ein kurzer billbarer Lauf (nutzt das vorhandene GATE-B-Guthaben), der
  zeigt, dass sich das Gedaechtnis ueber zwei Auftraege hinweg traegt.
- **Spaeter (eigene GATES):** semantische Suche/Embeddings, Datenbank/Supabase, Retention/Pruning.
