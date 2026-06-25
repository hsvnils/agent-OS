# PHASE9_PLAN.md — Innovations-Pipeline (Unternehmensberater)

> **Status: GEBAUT (offline getestet).** Detailplan zu Phase 9 der `ROADMAP.md`. Der Unternehmensberater
> (Agent 01) erzeugt **bewertete, entscheidungsreife Verbesserungs-Vorschlaege** und legt sie als **Antrag**
> (Phase 6) vor. `AGENTS.md` bleibt kanonisch.

---

## 1. Zweck & strikter Scope

Ein orchestrierter Mehr-Agenten-Workflow buendelt vorhandene Bausteine zu einem Vorschlag:

```
Beobachten (Web-Recherche, Phase 8 / Researcher)
   -> Idee (Unternehmensberater, Agent 01)
   -> Bewertung: Machbarkeit (CTO) + Kostenvoranschlag (CFO)
   -> Antrag (Phase 6)  ->  CEO entscheidet
```

**In diesem Build:** ein Lauf erzeugt EINE bewertete Idee als Antrag (Status `eingereicht`). **Kein
Ausfuehren** -- Umsetzung erst nach CEO-Freigabe (Phase 7). Mensch-Tor bleibt hart.

## 2. Sicherheits-Invarianten

1. **Output ist ein Antrag, keine Aktion.** Die Pipeline schreibt nie Code/Charten und beschafft nichts.
2. **Kosten governt:** neue Modelle/Dienste/Abos bleiben CEO-Tor; der CFO-Kostenvoranschlag ist Teil des
   Antrags, die Entscheidung trifft der CEO.
3. **Leck-Schutz** auf allen Agenten-Ausgaben; Backend injizierbar (Offline-Self-Checks ohne Netz/Kosten).
4. **Robust:** faellt ein Agent/Backend aus, entsteht der Antrag trotzdem (mit Hinweis) -- kein Absturz.

## 3. Bausteine (gebaut)

- `orchestrator/core/innovation.py` — `InnovationPipeline` (Web -> Berater -> CTO/CFO -> `Antraege.stellen`),
  `InnovationErgebnis`.
- HoA-Tool `innovation_scouting(thema?)` in `orchestrator/core/hoa_tools.py` (nutzt `ctx.web`, `ctx.antraege`,
  `ctx.core`-Backend/Subagenten).
- `orchestrator/tests/test_innovation.py` — 6 Offline-Self-Checks (Antrag erzeugt, ohne Web lauffaehig,
  Backend-Fehler-Robustheit, Leck-Schutz, Tool, Titel-Helfer). Gesamtsuite 73/73 OK.

## 4. Bedienung / Folgefluss

- LUNA: `innovation_scouting` (optional mit Thema) -> bewerteter Antrag landet im Antrags-Store.
- CEO sieht/entscheidet ueber `antraege_zeigen` / `antrag_freigeben` (Telegram). Nach Freigabe kann die
  Execution-Engine (Phase 7) ihn umsetzen -- Branch + Tests, kein Merge ohne CEO.

## 5. Spaeter / Erweiterung

- Input weiterer Abteilungen je nach Idee (z. B. CISO, CDO) statt nur CTO/CFO.
- Mehrere Ideen je Lauf + Priorisierung; proaktiver Scheduler (Phase 12) startet Scouting periodisch.
