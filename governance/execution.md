# Execution-Policy (Phase 7 — handelnde Agenten)

> Lebendes Steuerungsdokument, `AGENTS.md` untergeordnet. Umsetzung: `orchestrator/core/execution.py`;
> Detailplan: `PHASE7_PLAN.md`; Roadmap: `ROADMAP.md` (Phase 7).

## Zweck

Freigegebene Antraege (Phase 6) werden von einem Ausfuehrungs-Agenten real umgesetzt — kontrolliert,
isoliert, getestet, reversibel.

## Invarianten (nicht verhandelbar)

1. **Nur `freigegebene` Antraege** werden ausgefuehrt (Doppelpruefung in der Engine).
2. **Isolation:** Arbeit in einem Git-Worktree auf Branch `antrag/<id>`; nie direkt auf main.
3. **Kein Merge ohne CEO:** Ergebnis ist Branch + Bericht. Merge entweder manuell durch den CEO in Git oder
   per ausdruecklich sprach-/text-bestaetigtem `antrag_mergen`.
4. **Tests Pflicht:** Self-Checks nach der Aenderung; rot -> Status `fehlgeschlagen`.
5. **Charten/Regeln geschuetzt:** `agents/`, `AGENTS.md`, `CLAUDE.md` nur mit Antrag der Kategorie `mandat`
   (HoA-exklusiv, AGENTS.md 3.3); sonst lehnt die Engine ab.
6. **Werkzeug-Grenzen:** Lesen/Schreiben im Repo + begrenzte Bash (Tests, Git-Branch/Worktree). Keine
   destruktiven/History-rewriting/externen Aktionen. Leck-Schutz: keine Secrets in Diffs/Berichten/Logs.
7. **CEO-Tor bleibt:** Geld/Recht/Oeffentlichkeit/Loeschung -> zusaetzliche Bestaetigung.
8. **Notbremse + Limits:** harte Turn-/Zeit-/Kosten-Grenze pro Lauf; Stopp-Befehl bricht ab.

## Ausloesung (CEO-Entscheidung)

- **CEO-Auftrag:** kurze Rueckfrage „Soll ich das machen?" genuegt als Freigabe.
- **Agenten-Idee:** der HoA legt zuerst den Plan dar (was + wie); der CEO gibt frei, fordert Revision oder
  mehr Details. Erst dann Umsetzung.

## Status-Fluss

```
freigegeben -> in_umsetzung -> erledigt (Tests gruen) | fehlgeschlagen (rot/Fehler/Abbruch)
```

Jede Transition: Changelog-Eintrag. Worktree bleibt zur Pruefung bestehen; Aufraeumen nach Merge/Verwerfen.
