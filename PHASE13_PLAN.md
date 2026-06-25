# PHASE13_PLAN.md — Self-Development-Loop (Apex)

> **Status: GEBAUT (on-demand) + abgesichert.** Der staerkste GATE der Roadmap. Das System schlaegt
> Verbesserungen an sich selbst vor — **ausschliesslich** ueber den freigegebenen Antrags-/Execution-Pfad.
> `AGENTS.md` bleibt kanonisch und uebergeordnet.

---

## 1. Der geschlossene Kreis

```
24/7-Monitoring (Phase 12, kostenlos)  ->  Fachbereichs-Wissensstand je Abteilung
   ->  Agent leitet Verbesserung in SEINEM Bereich ab (Phase 13)
   ->  Bewertung CTO (Machbarkeit) + CFO (Kosten)  ->  ANTRAG (Phase 6)
   ->  CEO-Freigabe ueber den HoA (Telegram)
   ->  Execution-Engine setzt um (Phase 7: Branch + Tests, KEIN Merge ohne CEO)
   ->  Berichte/Freigaben mobil (Phase 10/11).  Kreis geschlossen.
```

## 2. Harte Invarianten (nicht verhandelbar)

1. **Nur Vorschlaege, nie Ausfuehrung.** Output ist immer ein Antrag (`eingereicht`). Selbst-Modifikation
   laeuft ausnahmslos ueber freigegebenen Antrag -> Branch -> Tests -> CEO-Merge (Phase 6/7).
2. **Token-frugal.** Sammeln (Wissensstand) ist kostenlos. Die teure Vorschlags-Erzeugung (LLM) ist
   **on-demand** (CEO fragt). Der **geplante** Loop ist per Default **AUS** (`enabled=False` / `SELF_DEV_ENABLED`).
3. **Notbremse.** `autonomie_pausieren(true)` haelt alle autonomen Ablaeufe an (Watcher + Selbst-Entwicklung);
   der Hintergrund-Loop und `selbstentwicklung`/`lauf` respektieren den Pausenschalter.
4. **Governance unveraendert.** CEO-Tor, Charta-Schreibrechte (HoA-only), Leck-Schutz, Budget bleiben in Kraft.

## 3. Bausteine (gebaut)

- `orchestrator/core/innovation.py` — `InnovationPipeline.run(..., abteilung=, wissen=)`: abteilungs- und
  wissensbasierte Vorschlaege (Default berater = firmenweit).
- `orchestrator/core/self_development.py` — `SelfDevelopment`: `vorschlag_fuer(abteilung)` (on-demand) und
  `lauf()` (geplant, gated). Zieht den Wissensstand je Abteilung aus dem Watcher.
- HoA-Tools: `selbstentwicklung(abteilung?)`, `autonomie_pausieren(pausieren)`, `autonomie_status`.
- `WatchStore.set_pause/paused` + Bot-Loop respektiert die Pause.
- `orchestrator/tests/test_self_development.py` — 6 Offline-Self-Checks. Gesamtsuite 88/88 OK.

## 4. Bedienung (Telegram)

- `selbstentwicklung [abteilung]` — ein bewerteter Selbst-Entwicklungs-Antrag (LLM; auf CEO-Anfrage).
- `antraege_zeigen` / `antrag_freigeben` / `antrag_umsetzen` / `antrag_mergen` — der CEO-Entscheidungspfad.
- `autonomie_pausieren true|false`, `autonomie_status` — Notbremse.

## 5. Optionaler geplanter Betrieb (bewusst aus)

`SelfDevelopment.lauf()` ist fuer einen periodischen Betrieb vorgesehen, aber **per Default deaktiviert**
(`SELF_DEV_ENABLED`). Aktivierung ist eine CEO-Entscheidung (laufende Token-Kosten) mit hartem Per-Lauf-Cap
(`max_pro_lauf`) und der Notbremse als Sicherheitsnetz.
