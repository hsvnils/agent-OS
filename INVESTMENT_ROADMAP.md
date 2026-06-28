# INVESTMENT_ROADMAP.md — Investment-Abteilung (CIO) fuer LUNA

> **Lebende Roadmap.** Leitet den `Investment_Abteilung_Bauplan.md` (CEO-Vorlage 2026-06-28) in eine
> Schritt-fuer-Schritt-Einarbeitung ins bestehende LUNA-System ueber. **Advisory-only zum Start**, mit
> sauberem, gateten Schalter Richtung Paper- und spaeter Live-Trading. `AGENTS.md` bleibt kanonisch und
> uebergeordnet; jede Phase ist ihr untergeordnet. `.md` umlautfrei (ae/oe/ue/ss), Changelog-Pflicht.
>
> **Status: GEPLANT** — noch nichts umgesetzt; dies ist der Fahrplan. Wir arbeiten ihn Phase fuer Phase ein.

---

## 0. Harte Leitplanken (verbindlich, gelten in JEDER Phase)

1. **Keine Finanzberatung, keine Garantien.** LUNA/CIO liefert Entscheidungs-UNTERSTUETZUNG (Analyse, Prognose,
   Begruendung) -- **niemals personalisierte Anlageberatung**. Maerkte sind riskant; vergangene Treffer sagen
   nichts ueber die Zukunft.
2. **Kein automatischer Trade ohne ausdrueckliche CEO-Freigabe.** Jeder echte Kauf/Verkauf und jede Aktivierung
   von Paper-/Live-Modus ist ein **CEO-Tor** (AGENTS.md 4: Geld). Der Assistent fuehrt nie autonom aus.
3. **Immer Grund + Quelle + Konfidenz + Risiko-Label** bei jedem Vorschlag/Alert.
4. **Vertrauen vor Geld.** Track-Record/Scorecard ab Tag eins; Live erst nach nachweislich gutem Paper-Track-Record.
5. **Secrets nur via Capability-/`.env`-Muster + Leck-Schutz**; keine Keys im Klartext, nie committen.

---

## 1. Status-Uebersicht (Single Source of Truth)

| Phase | Thema | Modus | GATE | Status |
|------:|-------|-------|------|--------|
| 0 | Plan & Charta (CIO + Governance) | advisory | GATE A: Freigabe Plan/Charta | 🔲 geplant |
| 1 | Datenanbindung (gratis) + Speicher | advisory | GATE B: gratis API-Keys in .env (CISO/CTO) | 🔲 geplant |
| 2 | Die drei Schleifen (Screen/Prognose/Alerts) | advisory | — (kein Ausfuehren) | 🔲 geplant |
| 3 | Vertrauen aufbauen + Paper-Modus | advisory → paper | GATE C: Paper aktivieren (Alpaca) | 🔲 geplant |
| 4 | Live-Trading (hart abgesichert) | live | GATE D: Live aktivieren (haerteste Guardrails) | 🔲 geplant |

**Aktiver Modus dieses Bauplans: ausschliesslich `advisory`.** Paper/live werden nur als ausgeschalteter,
gateter Pfad vorbereitet.

---

## 2. Neue Rolle: CIO — Chief Investment Officer

- Neuer Agent `agents/15_cio.md` (Charta nach `_TEMPLATE.md`), Status zunaechst **Entwurf**, im Org unter LUNA.
  **Charta-Erstellung nur durch LUNA/Head of Agents auf ausdrueckliche CEO-Anweisung** (AGENTS.md 3.3) -- mit
  Diff-Vorlage + Bestaetigung.
- Auftrag: datenbasierte Investment-Analyse + -Vorschlaege (Aktien/ETF/Krypto), fuehrt Prognosen + Scorecard,
  ueberwacht Fruehbeweger, liefert actionable Vorschlaege an LUNA. **Trifft keine Trades autonom.**
- Aufnahme in `agents/REGISTRY.md`; Einhaengen im `governance/organigramm.md` (+ `.xmind`) unter LUNA.

**Unter-Agenten (Skizze, orientiert an `virattt/ai-hedge-fund`):** Markt-Screener · Technik-Analyst ·
Fundamental-Analyst · News/Sentiment-Analyst · Risk-Agent · Portfolio/Synthese-Agent. Autonomie-Prinzip:
Unter-Agenten loesen selbst, eskalieren an den CIO; der CIO an LUNA nur bei Bedarf.

---

## 3. Betriebsmodi (der gatete Schalter advisory → paper → live)

Modus-Schalter in `finance/investment-config.md` bzw. Supabase `inv_mode` (vom CEO aenderbar; Wechsel = CEO-Tor):

- **advisory** (Default/jetzt): nur Vorschlaege; LUNA meldet (Telegram + LUNA-OS), der CEO fuehrt selbst aus.
- **paper** (geplant): simuliertes Ausfuehren mit echten Kursen ueber **Alpaca Paper-Trading** -> realer,
  geldloser Track-Record. Aktivierung = **GATE C**.
- **live** (geplant, standardmaessig AUS): echtes Auto-Trading ueber Broker-API. Aktivierung = **GATE D** +
  Voraussetzungen: Broker-Keys (Capability), harte Risiko-Limits (max. Positionsgroesse, Tagesverlust-Limit),
  **Kill-Switch**, Freigabe pro Trade oder pro Mandat.

**Architektur:** Ausfuehrungs-Pfad als **austauschbare Komponente** bauen (advisory = nur loggen/melden;
paper/live = Broker-Adapter). Der Schalter ist da, ohne dass jetzt etwas Echtes ausgefuehrt wird.

---

## 4. Phasen mit GATES (Einarbeitung in LUNA)

### Phase 0 — Plan & Charta — GATE A
- `agents/15_cio.md` + Unter-Agenten-Skizze (LUNA auf CEO-Anweisung), `governance/investment.md` (lebendes
  Steuerungsdokument: Modi, Risiko-Limits, Schwellwerte, Eskalations-/Freigabe-Regeln; referenziert aus
  `AGENTS.md` + `governance/orchestrierung.md`), Registry/Organigramm aktualisieren. Diese Roadmap ist Teil 0.
- **Self-Checks:** Doku konsistent, keine Code-Wirkung. **GATE A:** CEO-Freigabe von Plan/Charta.

### Phase 1 — Datenanbindung (gratis) + Speicher — GATE B
- Anbindung via **MCP/Capability** (passt zum vorhandenen MCP-Einsatz): Finnhub, Alpha-Vantage-MCP (offiziell),
  CoinGecko, SEC EDGAR, FMP. Architektur-Referenz `virattt/ai-hedge-fund`.
- **Supabase** (vorhandenes Pro-Projekt, kein neuer Dienst) als Investment-Speicher; Tabellen siehe Abschnitt 6.
  (Knuepft an den bestehenden Backlog-Punkt „Supabase als Queue-/Store-Backend" der Haupt-ROADMAP an.)
- **Self-Checks gegen Mock/aufgezeichnete Daten** (ohne Kosten/ohne Live-Calls). **GATE B:** gratis API-Keys in
  `.env` (CTO provisioniert, CISO-Freigabe; Capability-Muster, Leck-Schutz).

### Phase 2 — Die drei Kern-Schleifen (advisory)
- **3.1 Taeglicher Markt-Screen:** ein/zwei **Bulk-Abfragen** (Gesamtmarkt-Mover, ungewoehnliches Volumen,
  relative Outperformance; Fokus kleine Werte, die staerker steigen als vergleichbare) -> **Shortlist**; nur die
  Shortlist wird tief analysiert (Technik/Fundamental/Sentiment). Crypto 24/7 ueber guenstigen Pfad.
  **Bulk statt Einzel-Polling** (Kosten-/Rate-Limit-Schutz). Laeuft ueber den vorhandenen **WatchScheduler**
  (token-frugaler 24/7-Loop) + **Researcher** (Web-„Warum").
- **3.2 Wochenprognose + Scorecard (walk-forward):** Prognose je Wert mit **Rationale + Konfidenz**, gespeichert;
  nach einer Woche Soll-Ist automatisch vergleichen -> **Scorecard** (Trefferquote, mittlerer Fehler,
  beste/schlechteste Calls). **Anomalie-Obduktion:** bei Abweichung > Schwelle recherchiert der
  News/Sentiment-Analyst die Ursache (mit Quellen).
- **3.3 Alerts:** actionable Vorschlag -> CIO -> LUNA -> **Notifier/Telegram + LUNA-OS-Panel „Investment"**.
  Jeder Alert: Wert, Aktion, **Grund**, **Quelle(n)**, Konfidenz, **Risiko-Label** (konservativ/spekulativ),
  Zeitbezug. (Nutzt den bestehenden proaktiven Notifier + Telegram-Kanal.)
- **Self-Checks:** Screener liefert Shortlist; Prognose gespeichert; Scorecard rechnet Soll-Ist; Obduktion
  recherchiert; Alert enthaelt Grund+Quelle+Risiko-Label. **Keine Ausfuehrung.**

### Phase 3 — Vertrauen aufbauen, dann Paper — GATE C
- advisory laufen lassen, Track-Record sammeln; Scorecard im LUNA-OS sichtbar machen.
- Erst nach belastbarem Track-Record: **Paper-Modus** (Alpaca Paper-Trading, kostenlos) ueber den
  austauschbaren Broker-Adapter aktivieren. **GATE C** (CEO-Tor); weiter Track-Record (jetzt simuliert mit
  echten Kursen).

### Phase 4 — Live-Trading — GATE D (haerteste Stufe)
- **Nur nach gutem Paper-Track-Record.** Broker-Keys (Capability), harte Risiko-Limits, Tagesverlust-Limit,
  **Kill-Switch**, Audit jeder Order im Aktivitaetsprotokoll, Freigabe pro Trade oder pro Mandat.
- **GATE D:** strengstes CEO-Tor; Trade-Ausfuehrung = hoechste Risikostufe.

Jede Phase: Self-Checks gruen, Changelog (umlautfrei), Commit.

---

## 5. Daten & Dienstleister

- **Start kostenlos, nahe-Echtzeit (Minuten reichen -- kein HFT):** Finnhub (~60/min), Alpha Vantage (50+
  Indikatoren, MCP, Crypto/Forex), CoinGecko (Crypto), SEC EDGAR (Filings), FMP (250/Tag, Screener/Fundamentals).
- **Erste optionale Mini-Ausgabe (nur bei Bedarf, via CFO-Kostenvoranschlag = CEO-Tor):** FMP ~$19/Mo oder
  Finnhub-Paid (~$80/Mo). Nicht zum Start noetig.
- **MCP-Server (Referenz):** Alpha-Vantage-MCP (offiziell), `wshobson/maverick-mcp`,
  `stefanoamorelli/sec-edgar-mcp`, `Alex2Yang97/yahoo-finance-mcp`. Alle Keys ueber **Capability-Muster**.
- **Broker paper/live (geplant):** Alpaca (kommissionsfrei, US-Aktien + Crypto, Paper-Modus). Keys
  Capability-Muster; Aktivierung CEO-Tor.

---

## 6. Datenspeicher (Supabase)

Supabase (vorhandenes Pro-Projekt) als Investment-Speicher. Tabellen mindestens: `inv_watchlist`,
`inv_screening`, `inv_forecasts`, `inv_actuals`, `inv_scorecard`, `inv_suggestions`, `inv_mode`,
`inv_paper_trades`/`inv_positions`. CDO liefert/normalisiert; CFO sieht die Datendienst-Kosten in seiner
Kostenstatistik. (Bis Supabase angebunden ist, koennen Stores uebergangsweise dateibasiert laufen -- wie die
uebrigen LUNA-Stores.)

---

## 7. Governance-Integration

- **CEO-Tore (immer Freigabe):** jeder echte Trade, jede Aktivierung von paper/live, jeder neue kostenpflichtige
  Datendienst/Broker, jede Erhoehung von Risiko-Limits.
- **CFO** erstellt Kostenvoranschlag fuer jeden bezahlten Dienst/Broker; **HoA** prueft gegen Monatsbudget
  (`finance/budget.md`).
- **Secret-/Capability-Muster + Leck-Schutz** fuer alle Keys (Daten + Broker).
- **Charta-Aenderungen** nur durch LUNA auf CEO-Anweisung (AGENTS.md 3.3). **Changelog-Pflicht** nach jeder Aktion.
- `governance/investment.md` als lebendes Steuerungsdokument (Modi, Limits, Schwellwerte, Eskalation/Freigabe).

---

## 8. Anbindung an das bestehende LUNA-System (Wiederverwendung)

- **24/7-Loops:** `core/scheduler.py` (WatchScheduler) treibt den taeglichen Screen + Wochenzyklus
  (token-frugal, Bulk).
- **Researcher (Agent 15-Muster)** liefert das „Warum"/die Anomalie-Obduktion ueber Research-Tickets.
- **Notifier** (`core/notifications.py`) + **Telegram** + **LUNA-OS** stellen Alerts/Scorecard zu; geplantes
  **LUNA-OS-Panel „Investment"** (Watchlist, Shortlist, Scorecard, offene Vorschlaege) im Command-Center-Stil
  (siehe `UI.md`).
- **CFO/Budget** governt Kosten; **CISO/CTO** governt Keys/Capabilities.
- **Antrags-/Freigabe-Workflow (Phase 6 der Haupt-ROADMAP)** ist der Kanal fuer jede gatete Aktivierung
  (paper/live, bezahlte Dienste).

---

## 9. Kosten (Ueberblick)

- **Daten:** Start ~0 EUR (Free-Tiers); optionale Mini-Ausgabe ~$19/Mo (FMP) bei Bedarf.
- **LLM-Tokens:** guenstiges Modell fuers Routine-Screening, starkes Modell fuer die Synthese -> grob wenige
  Euro/Monat.
- **Broker:** Alpaca Paper kostenlos; Live = eigenes Geld + Broker-Gebuehren.
- **Telegram + Hosting:** vorhandene NAS + Supabase.
- Realistisch: Start ~0–5 EUR/Monat; bei kleinem Daten-Upgrade ~20–25 EUR/Monat.

---

## 10. Design-Lehre „Loop Engineering" (uebernommene Denkweise, kein Code-Import)

Aus `cobusgreyling/loop-engineering` (MIT) uebernehmen wir die **Konzepte als Entwurfsraster** -- nicht die
npm-CLIs (die zielen auf Coding-Agenten/GitHub-Actions, nicht auf LUNAs Python-Orchestrator; vieles davon hat
LUNA bereits):

- **Stufenweise Autonomie L1 → L2 → L3** (Report → Assisted → Unattended) = exakt unser **advisory → paper →
  live** mit GATES. Diese Treppe ist die Leitidee fuer JEDE neue autonome Schleife.
- **Maker/Checker (Sub-Agenten-Verifikation)** = CIO-Synthese + **Risk-Agent** als Gegenpruefer vor jedem
  Vorschlag.
- **Kosten je Schleife budgetieren** = CFO-Kostenstatistik je Loop/Datendienst.
- **Skills/persistentes Wissen** = unser **Second Brain**; **Plugins/Connectors (MCP)** = Daten-MCPs;
  **Scheduling/Automations** = WatchScheduler; **Worktrees** = Git-Branch-Sandbox der Execution-Engine.

Empfehlung: **kein Einbau der Bibliothek/CLIs**, aber die L1→L2→L3-Treppe + Maker/Checker + Loop-Kostenbudget
als feste Entwurfsregeln fuer Investment (und kuenftige autonome Loops) verankern -- ideal in
`governance/investment.md` und `governance/orchestrierung.md`.

---

## 11. Naechster Schritt

**Phase 0 (GATE A):** Auf CEO-Freigabe legt LUNA/Head of Agents die CIO-Charta (`agents/15_cio.md`, Status
Entwurf) + `governance/investment.md` an und haengt den CIO ins Organigramm. Erst danach Phase 1 (gratis Daten).
Nichts davon fuehrt Trades aus -- es ist die governance-konforme Grundlage.
