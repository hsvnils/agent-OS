# PHASE7_PLAN.md — Execution-Engine (handelnde Agenten)

> **Status: PLAN — wartet auf GATE (staerkste Freigabe).** Detailplan zu Phase 7 der `ROADMAP.md`. Hier
> bekommen Abteilungen die Faehigkeit, **freigegebene** Antraege wirklich umzusetzen — wie wenn der CEO die
> Aenderung selbst in Claude Code machen wuerde —, aber auf einem **Git-Branch mit Tests** und **niemals
> ohne CEO-Merge**. `AGENTS.md` bleibt kanonisch.

---

## 1. Zweck & strikter Scope

Ein **freigegebener** Antrag (Phase 6, Status `freigegeben`) wird von einem **Ausfuehrungs-Agenten**
(Claude Agent SDK mit Datei-/Bash-/Test-Werkzeugen) in einer **isolierten Arbeitskopie** umgesetzt. Ergebnis:
ein Branch + Bericht (Diff, Testergebnis, was zu pruefen ist). Der CEO entscheidet ueber den Merge.

**In diesem Build:** Ausfuehrung genau EINES freigegebenen Antrags auf Branch + Self-Checks + Bericht +
Status-Fortschreibung. **Ausdruecklich NICHT:** Auto-Merge, Push, Deploy, Dauerbetrieb/Resume (Phase 12),
Aenderung von Charten ausser bei ausdruecklich dafuer freigegebenem Antrag (AGENTS.md 3.3).

## 2. Sicherheits-Invarianten (nicht verhandelbar)

1. **Nur `freigegebene` Antraege** werden ausgefuehrt — niemals `eingereicht`. Doppelpruefung in der Engine.
2. **Isolation:** Arbeit in einem **Git-Worktree** auf Branch `antrag/<id>`; das laufende Repo/der
   Voice-Server bleibt unberuehrt. **Kein Commit auf `main`, kein Push, kein Merge** ohne CEO.
3. **Tests Pflicht:** nach der Aenderung laufen die Offline-Self-Checks; rot -> Status `fehlgeschlagen`.
4. **Werkzeug-Grenzen:** nur Lesen/Schreiben im Repo + begrenzte Bash (Tests, Git-Branch/Worktree). Keine
   destruktiven Aktionen (`rm -rf`, History-Rewrite), keine externen/kostenpflichtigen Aktionen, kein Netz
   ausser noetig. Leck-Schutz aktiv (keine Secrets in Diffs/Berichten/Logs).
5. **Charten/Governance geschuetzt:** `agents/*` (Charten) und kanonische Regeln werden NICHT veraendert,
   ausser der Antrag ist genau dafuer + CEO-freigegeben (HoA-exklusiv, AGENTS.md 3.3).
6. **CEO-Tor bleibt:** beruehrt der Antrag Geld/Recht/Oeffentlichkeit/Loeschung -> zusaetzliche Bestaetigung.
7. **Notbremse + Limits:** harte max-turns/Zeit-/Kosten-Grenze pro Lauf; ein Stopp-Befehl bricht ab.

## 3. Ablauf

```
Antrag freigegeben (Phase 6)
   -> antrag_umsetzen(id)  [HoA-Tool, nur freigegeben]
      1. git worktree add ../.worktrees/antrag-<id> -b antrag/<id>
      2. Ausfuehrungs-Agent (Opus, Coding-Tools) arbeitet die Aufgabe im Worktree
      3. Self-Checks im Worktree ausfuehren
      4. git diff + Testergebnis -> Bericht
      5. Status: erledigt (Tests gruen) | fehlgeschlagen (rot/Fehler)
   -> HoA berichtet gesprochen: "Im Branch antrag/<id> umgesetzt: ...; Tests X/X; zu pruefen: ..."
   -> CEO entscheidet ueber Merge (manuell bzw. spaeteres antrag_mergen mit CEO-Bestaetigung)
```

## 4. Technische Umsetzung

- **Execution-Backend:** dieselbe gebundelte Claude-CLI wie heute, aber mit **aktivierten Coding-Tools**
  (`allowed_tools = Read, Write, Edit, Bash, Grep, Glob`), `cwd` = Worktree, `setting_sources=[]`,
  `permission_mode` so, dass Datei-Edits im Worktree erlaubt sind. System-Prompt = Charta des zustaendigen
  Agenten + strenge Ausfuehrungsregeln (Branch-only, Tests, kein Merge, keine Charta-Edits, Leck-Schutz).
- **Engine** `core/execution.py`: Worktree/Branch anlegen, Agent starten, Tests laufen lassen, Diff/Bericht
  erzeugen, aufraeumen, Antrags-Status setzen. Bei Rate-/Guthaben-Limit: sauberer Abbruch + Bericht
  (echtes Resume erst Phase 12).
- **Anbindung:** HoA-Tool `antrag_umsetzen(antrag_id)` (prueft `freigegeben`), spaeter optional
  `antrag_mergen(antrag_id)` (nur nach CEO-Bestaetigung).

## 5. Dateien

```
orchestrator/
  core/execution.py            # NEU: ExecutionEngine (Worktree, Agent-Lauf, Tests, Bericht, Guards)
  core/backends.py             # ERWEITERT: Coding-Variante (allowed_tools, permission_mode, cwd)
  channels/voice/pipeline.py   # ERWEITERT: Tool antrag_umsetzen (nur freigegeben)
  tests/test_execution.py      # NEU: Self-Checks mit MOCK-Ausfuehrung (ohne Kosten)
governance/execution.md        # NEU: Policy (Invarianten, Branch/Tests/Merge, Grenzen)
.gitignore                     # ERWEITERT: .worktrees/
```

## 6. Self-Checks (offline, ohne Kosten — mit Mock-Ausfuehrung)

1. **Guard:** Engine verweigert Ausfuehrung, wenn Antrag nicht `freigegeben` ist.
2. **Worktree/Branch:** Branch `antrag/<id>` wird angelegt, Arbeit isoliert, Aufraeumen funktioniert.
3. **Status-Fortschreibung:** freigegeben -> in_umsetzung -> erledigt/fehlgeschlagen, Verlauf erhalten.
4. **Tests-Gate:** rote Self-Checks -> Status `fehlgeschlagen` + Bericht.
5. **Charta-Schutz:** ein Antrag, der `agents/*` aendern wuerde, wird ohne explizite Freigabe-Markierung
   abgelehnt.
6. **Leck-Schutz:** ein Test-Secret taucht in keinem Bericht/Log auf.

(Die echte Coding-Ausfuehrung wird im Self-Check **gemockt**; der reale Lauf folgt am GATE.)

## 7. GATE (staerkste Stufe)

- **GATE (jetzt):** Freigabe dieses Designs.
- **Danach:** Offline-Implementierung mit Mock-Self-Checks (ohne Kosten).
- **Live-GATE:** EIN echter, kleiner, von dir freigegebener Antrag wird real auf einem Branch umgesetzt
  (billbar, Opus). Ergebnis: Branch + Bericht; du pruefst und mergst.
- **Offene Designfragen fuer den CEO:**
  1. **Merge:** manuell durch dich in Git (Standard) — oder ein `antrag_mergen`-Tool mit Sprach-Bestaetigung?
  2. **Aufloesung:** Ausfuehrung nur auf ausdruecklichen Befehl (`antrag_umsetzen`) — oder direkt nach
     Freigabe automatisch? (Empfehlung: nur auf ausdruecklichen Befehl, ein Schritt nach der Freigabe.)
