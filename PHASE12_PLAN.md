# PHASE12_PLAN.md — Durable Watch-Queue + Scheduler (24/7, token-frugal)

> **Status: GEBAUT + LIVE (Hintergrund-Loop).** Detailplan zu Phase 12 der `ROADMAP.md`. Das System
> beobachtet rund um die Uhr die Aussenwelt — **ohne Token zu verbrennen**. `AGENTS.md` bleibt kanonisch.

---

## 1. Leitplanken (CEO)

1. **Keine unnoetigen Token.** Der 24/7-Hintergrund macht **ausschliesslich kostenlose** Datenarbeit
   (GitHub-API + Brave-Gratis-Suche) und flaggt regelbasiert. **Kein LLM im Hintergrund** (`llm_enabled=False`);
   teure Synthese (`innovation_scouting`) nur auf CEO-Anfrage.
2. **Abteilungsrelevante Suchen.** Pro Fachbereich kuratierte Themen (`orchestrator/core/watch_config.py`):
   jede Abteilung bekommt gezielte Aussenwelt-Signale (z. B. CISO -> Prompt-Injection, CFO -> API-Pricing,
   CDO -> RAG/Vektor-DBs, CLO -> EU AI Act ...).
3. **GitHub im Blick.** Repos mit vielen Sternen, die **schnell wachsen** — Velocity per Sterne-Delta
   (Historie) + Neueinsteiger-Proxy.

## 2. Architektur

| Baustein | Zweck |
|----------|-------|
| `orchestrator/governance/github_watch.py` | GitHub-Search (frei), `flag_fast_growers` (Velocity/Neuheit), Mock. |
| `orchestrator/core/watch_config.py` | Abteilungs-Themen (Suche + GitHub-Topics) + firmenweite Topics. |
| `orchestrator/core/scheduler.py` | `WatchStore` (durable JSONL: Sterne-Historie, Funde dedupliziert, Lauf-Zeiten) + `WatchScheduler` (github_tick/dept_tick/briefing). |
| `bot.py` Hintergrund-Loop | Daemon-Thread: GitHub jeden Tick, **eine** Abteilung je Tick (Brave-Quota schonen). Intervall `WATCH_INTERVAL_HOURS` (Default 6 h). |

## 3. Token-/Kosten-Frugalitaet (wie genau)

- **Tier 1 (frei, immer):** GitHub-API (60/h ohne Token, 5000/h mit `GITHUB_TOKEN`) + Brave-Gratis.
- **Regelbasiertes Flagging** statt LLM: Sterne-Zuwachs-Schwelle, Neuheit, Dedup nach URL.
- **Rundenweise Fachbereiche:** je Tick nur 1 Abteilung -> ~12 Brave-Suchen/Tag, weit im Gratis-Rahmen.
- **Kein Hintergrund-LLM.** Erst wenn der CEO einen Fund vertiefen will, laeuft `innovation_scouting` (gated,
  im Budget).
- **Durable/Resume:** Zustand in `watch/log.jsonl`; nach Neustart laufen Historie/Funde/Intervalle weiter.

## 4. Bedienung (Telegram, alles kostenlos)

- `github_trends [thema]` — schnell wachsende High-Star-Repos.
- `dept_briefing <abteilung>` — relevante Fachbereichs-Treffer sammeln + zeigen.
- `watch_digest [github|fachbereich]` — gesammelte Funde, neueste zuerst.
- `watch_tick` — manueller Durchlauf.

## 5. Self-Checks

`orchestrator/tests/test_watch.py` — 7 Offline-Checks (Velocity/Neuheit, Dedup, kein Hintergrund-LLM,
Fachbereichs-Suche, Config, Tools, Durable-Resume). Gesamtsuite 80/80 OK.

## 6. Spaeter

- Push-Benachrichtigung an den CEO (Telegram) bei besonders auffaelligen Funden.
- Optionaler Tier-3-Digest (LLM) mit hartem Budget-Cap, explizit aktivierbar.
- Auto-Bruecke: auffaelliger Fund -> Vorschlag fuer `innovation_scouting` (CEO entscheidet).
