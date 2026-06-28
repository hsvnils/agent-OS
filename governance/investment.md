# Investment — Steuerungsdokument der Investment-Abteilung (CIO)

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt kanonisch und uebergeordnet — bei Widerspruch gilt
> `AGENTS.md`. Regelt Modi, Risiko-Limits, Schwellwerte, Eskalations- und Freigabe-Regeln der
> Investment-Abteilung. Fahrplan: [`../INVESTMENT_ROADMAP.md`](../INVESTMENT_ROADMAP.md). Autonomie-Regeln:
> [`autonomie-stufen.md`](autonomie-stufen.md). Charten: [`../agents/16_cio.md`](../agents/16_cio.md),
> [`../agents/16a_risk-agent.md`](../agents/16a_risk-agent.md).
>
> **Aktiver Modus: `advisory`.** Paper/live sind nur vorbereitet (ausgeschaltet, gated).

---

## 1 Harte Leitplanken (verbindlich)

1. Keine personalisierte Anlageberatung, keine Garantien — nur Entscheidungs-Unterstuetzung.
2. **Kein automatischer Trade ohne ausdrueckliche CEO-Freigabe.** Jeder echte Trade + jede Aktivierung von
   paper/live = **CEO-Tor** (AGENTS.md 4).
3. Jeder Vorschlag/Alert traegt **Grund + Quelle + Konfidenz + Risiko-Label**.
4. Vertrauen vor Geld: Track-Record/Scorecard ab Tag eins; live erst nach gutem Paper-Track-Record.
5. Secrets nur via Capability-/`.env`-Muster + Leck-Schutz; nie committen.

## 2 Betriebsmodi (Schalter advisory → paper → live)

Modus in `finance/investment-config.md` bzw. Supabase `inv_mode` (Wechsel = CEO-Tor):

| Modus | Bedeutung | Autonomie-Stufe | GATE |
|-------|-----------|-----------------|------|
| **advisory** (aktiv) | nur Vorschlaege; CEO fuehrt selbst aus | L1/L2 | — |
| **paper** (geplant) | simuliert mit echten Kursen (Alpaca Paper) | L2 | GATE C |
| **live** (geplant, AUS) | echtes Auto-Trading, harte Limits + Kill-Switch | L3 | GATE D |

Ausfuehrungs-Pfad = austauschbare Komponente (advisory = loggen/melden; paper/live = Broker-Adapter).

## 3 Maker/Checker (Pflicht)

- **Maker:** CIO / Portfolio-Synthese-Agent erzeugt den Vorschlag.
- **Checker:** **Risk-Agent (16a, aktiv)** prueft JEDEN Vorschlag, vergibt Risiko-Label und kann
  Veto/Nachschaerfung verlangen — **kein** Alert an LUNA ohne sein Urteil.

## 4 Risiko-Limits & Schwellwerte (Platzhalter bis paper)

> Im advisory-Modus als **Empfehlung**; ab paper/live **hart durchgesetzt** vom Risk-Agent. Konkrete Werte
> legt der CEO bei GATE C/D fest. Erhoehung eines Limits = CEO-Tor.

- Max. Positionsgroesse je Wert: _tbd_ · Max. Exposure je Sektor/Asset-Klasse: _tbd_
- Tagesverlust-Limit (paper/live): _tbd_ · Kill-Switch: aktivierbar, Default AUS (CEO-Tor).
- Anomalie-Schwelle (Prognose vs. Realitaet) fuer Obduktion: _tbd_ (Start z. B. > 1.5x erwartete Bewegung).
- Konfidenz-Mindestschwelle fuer einen Alert: _tbd_.

## 5 Freigabe- & Eskalations-Regeln

- **CEO-Tor (immer Freigabe):** jeder echte Trade · jede Modus-Aktivierung (paper/live) · jeder neue
  kostenpflichtige Datendienst/Broker · jede Erhoehung von Risiko-Limits · Charta-Aenderungen.
- **CFO** erstellt Kostenvoranschlag fuer bezahlte Dienste/Broker; **HoA** prueft gegen `finance/budget.md`.
- **CISO/CTO**: Keys/Capabilities (Least-Privilege, Leck-Schutz). **Changelog-Pflicht** nach jeder Aktion.
- Konflikt Maker/Checker -> CIO mediiert; ungeloest/strategisch -> HoA -> CEO.

## 6 Datenspeicher (Supabase, geplant; uebergangsweise dateibasiert)

`inv_watchlist` · `inv_screening` · `inv_forecasts` · `inv_actuals` · `inv_scorecard` · `inv_suggestions` ·
`inv_mode` · `inv_paper_trades`/`inv_positions`. CDO normalisiert; CFO sieht die Datendienst-Kosten.

## 7 Status

- **Phase 0 (GATE A): erledigt** — CIO-Charta (Entwurf) + Risk-Agent (aktiv) + dieses Dokument + Registry/
  Organigramm. Keine Datenanbindung, keine Keys, keine Trades.
- Naechstes: **Phase 1 (GATE B)** — gratis Datenanbindung (Capability) + Supabase-Tabellen.
