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

**Router** (`route_komplexitaet`): einfache Anfrage -> Brave, komplexe (Analyse/Vergleich/Synthese, lange oder
mehrteilige Fragen) -> Anthropic. Explizite `tiefe` schlaegt die Heuristik. Ist der bevorzugte Provider nicht
verfuegbar, wird auf den anderen ausgewichen.

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

1. **Brave:** Account anlegen, `BRAVE_API_KEY` -> `orchestrator/.env` (CISO/Secret-Handling).
2. **Anthropic-Web:** CFO-Kostenvoranschlag (laufende Suchkosten) -> HoA-Budget-Check -> **CEO-Freigabe**.
3. Keys auf dem **NAS-Klon** (Produktion) hinterlegen; Mac bleibt fuer Entwicklung.
4. Nach Freigabe: Capability-Status in der Zugriffs-Policy auf „live" + kurzer Live-Smoke-Test.

> Erst nach 1–4 liefert `web_recherche` echte Ergebnisse. Bis dahin ist alles gebaut, getestet und sicher
> inaktiv (Fall-B-Hinweis).
