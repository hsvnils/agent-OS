# PHASE8_PLAN.md — Web-Research / Self-Education

> **Status: OFFLINE GEBAUT — Go-Live wartet auf GATE (CEO-Tor, klein + CISO).** Detailplan zu Phase 8 der
> `ROADMAP.md`. Der **Berater** (Innovations-Scouting) und die **IT/CTO** (Self-Education) bekommen einen
> kontrollierten Internet-Zugriff (Suche + Synthese). `AGENTS.md` bleibt kanonisch und uebergeordnet.

---

## 1. Zweck & Scope

Internet-Zugriff als **Capability** (Tool, das seinen Key intern aus `.env` liest — nie der Agent selbst),
fuer fundierte Innovations-/Self-Education-Recherche. Ergebnis ist **Wissen** (Treffer + Synthese mit Quellen),
keine Ausfuehrung. **In diesem Build:** Provider-Abstraktion + Router + Offline-Self-Checks. **NICHT:** keine
autonomen Aktionen aus Web-Inhalten, kein Schreiben/Beschaffen, keine Live-Calls ohne freigegebene Keys.

## 2. Provider (zwei, hinter einer Abstraktion)

| Provider | Staerke | Key | Kosten |
|----------|---------|-----|--------|
| **Brave Search** | rohe Web-Treffer, guenstig/schnell (einfache Lookups) | `BRAVE_API_KEY` (neuer Account) | Gratis-Kontingent, dann gering |
| **Anthropic-Web** | agentische Mehrschritt-Recherche + Synthese mit Quellen (komplexe Fragen) | vorhandener `ANTHROPIC_API_KEY` | billbar (~10 USD/1000 Suchen + Token) |

**Routing-Policy (CEO, 2026-06-25): Brave zuerst, Anthropic nur als Eskalation.** Der Researcher liefert
**immer zuerst Brave**. Anthropic-Web (billbar) wird NUR genutzt, wenn Brave nicht verfuegbar ist, ein
Limit/Fehler liefert, keine Treffer bringt, ODER der CEO eine **Revision/weitere Recherche** beauftragt
(`recherche_beauftragen(..., eskalation=true)`). Schlaegt Anthropic-Web fehl (z. B. Guthaben), faellt der
Researcher automatisch auf Brave zurueck.

## 3. Sicherheits-Invarianten (nicht verhandelbar)

1. **CEO-Tor (Fall B):** Beide Provider sind externer Zugang/Kosten. Ohne freigegebene Keys liefert das Tool
   einen **Fall-B-Hinweis** (CEO-Freigabe-Anfrage) statt Ergebnissen — **kein Absturz**.
2. **Externe Inhalte = Daten, nie Anweisung:** Schutz vor Prompt-Injection; Fundstuecke werden nicht als
   Instruktionen behandelt.
3. **Leck-Schutz:** Secrets werden via `leak_guard.redact` aus **Anfrage und Ergebnis** entfernt; kein Key
   verlaesst je das System.
4. **Least-Privilege:** Capability `web_research` nur fuer `berater` + `cto` (Zugriffs-Policy).

## 4. Bausteine (gebaut)

- `orchestrator/governance/web_research.py` — `Provider`-Protokoll, `MockProvider` (offline), `BraveProvider`,
  `AnthropicProvider` (natives web_search-Tool, lazy import), `WebResearch`-Router + `route_komplexitaet`.
- HoA-Tool `web_recherche(query, tiefe?)` in `orchestrator/core/hoa_tools.py` (gated, Leck-Schutz);
  `ToolContext.web` injizierbar (sonst aus env).
- `orchestrator/tests/test_web_research.py` — 8 Offline-Self-Checks (Router, Provider-Wahl, Fallback,
  CEO-Tor ohne Keys, Leck-Schutz, Tool-Handler, CEO-Tor-Query). Gesamtsuite 49/49 OK.
- `governance/zugriffs-policy.md` — Capability-Eintrag + Go-Live-Bedingungen.

## 5. GATE — Go-Live-Checkliste (CEO)

1. **Brave:** ✅ **live** seit 2026-06-25 — `BRAVE_API_KEY` in `orchestrator/.env` (Mac + NAS-Produktion),
   vom CEO geliefert (Gratis-Kontingent). Einfache UND komplexe Anfragen laufen aktuell ueber Brave.
2. **Anthropic-Web:** ✅ **freigeschaltet** 2026-06-25 (CEO) — `WEB_RESEARCH_ANTHROPIC=1` (Mac + NAS), nur als
   Eskalation. **Offen:** laeuft ueber raw-API-Guthaben (nicht CLI-Abo) — aktuell „credit balance too low",
   daher faellt die Eskalation auf Brave zurueck, bis das API-Guthaben aufgeladen ist (console.anthropic.com).
3. Keys/Flags auf dem **NAS-Klon** (Produktion) hinterlegen; Mac bleibt fuer Entwicklung.
4. Capability-Status in der Zugriffs-Policy fortschreiben + Live-Smoke-Test.

> **Wichtig (CEO-Tor):** Der `ANTHROPIC_API_KEY` ist ohnehin vorhanden — deshalb ist die billbare
> Anthropic-Web-Suche bewusst hinter dem expliziten Flag `WEB_RESEARCH_ANTHROPIC=1` gesperrt, nicht hinter
> Key-Praesenz. So entstehen keine Suchkosten ohne ausdrueckliche Freigabe.
