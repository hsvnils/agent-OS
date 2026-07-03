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
| **paper** (Code fertig, AUS) | simuliert mit echten Kursen (Alpaca Paper) | L2 | GATE C |
| **live** (gesperrt) | echtes Auto-Trading, harte Limits + Kill-Switch | L3 | GATE D |

Ausfuehrungs-Pfad = austauschbare Komponente (advisory = loggen/melden; **paper = Alpaca-Paper-Adapter**
`investment/broker.py`; live = spaeter). `investment_modus` schaltet den Modus (paper = CEO-Tor); `live` ist
im Tool hart gesperrt.

**GATE C aktivieren (CEO):** (1) Alpaca-**Paper**-Konto anlegen, `ALPACA_API_KEY` + `ALPACA_API_SECRET` in
`orchestrator/.env` (Mac + NAS) setzen (neuer Broker = CEO-Tor); (2) Container neu starten; (3) LUNA:
„Investment-Modus auf paper" -> mit bestaetigt=true. Danach sind **Paper-Orders** moeglich -- jede Order
zusaetzlich CEO-bestaetigt (`paper_order ... bestaetigt=true`), echtes Geld bleibt unberuehrt.

## 3 Maker/Checker (Pflicht)

- **Maker:** CIO / Portfolio-Synthese-Agent erzeugt den Vorschlag.
- **Checker:** **Risk-Agent (16a, aktiv)** prueft JEDEN Vorschlag, vergibt Risiko-Label und kann
  Veto/Nachschaerfung verlangen — **kein** Alert an LUNA ohne sein Urteil.

## 4 Risiko-Limits & Schwellwerte (Platzhalter bis paper)

> Im advisory-Modus als **Empfehlung**; ab paper/live **hart durchgesetzt** vom Risk-Agent. Konkrete Werte
> legt der CEO bei GATE C/D fest. Erhoehung eines Limits = CEO-Tor.

- **Max. Positionsgroesse je Wert: 5 % des Equity** (hart ab paper, `RiskAgent.MAX_POSITION_PCT`; Kauf nur,
  wenn Ordervolumen <= Buying-Power UND <= 5 % Equity). Min-Equity fuer Orders: `MIN_EQUITY`. Erhoehung = CEO-Tor.
- Max. Exposure je Sektor/Asset-Klasse: _tbd_ · Tagesverlust-Limit (paper/live): _tbd_ · Kill-Switch:
  aktivierbar, Default AUS (CEO-Tor).
- Anomalie-Schwelle (Prognose vs. Realitaet) fuer Obduktion: _tbd_ (Start z. B. > 1.5x erwartete Bewegung).
- Konfidenz-Mindestschwelle fuer einen Alert: _tbd_.

## 5 Freigabe- & Eskalations-Regeln

- **CEO-Tor (immer Freigabe):** jeder echte Trade · jede Modus-Aktivierung (paper/live) · jeder neue
  kostenpflichtige Datendienst/Broker · jede Erhoehung von Risiko-Limits · Charta-Aenderungen.
- **CFO** erstellt Kostenvoranschlag fuer bezahlte Dienste/Broker; **HoA** prueft gegen `finance/budget.md`.
- **CISO/CTO**: Keys/Capabilities (Least-Privilege, Leck-Schutz). **Changelog-Pflicht** nach jeder Aktion.
- Konflikt Maker/Checker -> CIO mediiert; ungeloest/strategisch -> HoA -> CEO.

## 6 Datenspeicher + All-Time-Historie (Datenhaltungs-Garantie)

**Append-only / event-sourced.** Der `InvestmentStore` (`investment/log.jsonl`) schreibt **ausschliesslich
anhaengend** -- jeder Screen, jede Prognose (inkl. **Basis-Preis** zum Prognosezeitpunkt), jedes eingetretene
Ergebnis (Actual), jeder Vorschlag und jeder Modus-Wechsel wird **dauerhaft mit Zeitstempel** gespeichert.
**Nichts wird ueberschrieben oder geloescht** (auch „Watchlist entfernen" ist nur ein neues Event). Damit ist
der Vorhersage-vs-Realitaet-Abgleich (Scorecard) jederzeit ueber die **komplette Historie** moeglich;
Auswertungen lesen die **gesamte** Historie (kein Lese-Limit). `store.historie()` zeigt die All-Time-Zaehlung.

Tabellen (Supabase-Ziel `inv_*`, uebergangsweise dateibasiert): `watchlist` · `screening` · `forecasts` ·
`actuals` · `scorecard` · `suggestions` · `mode` · `positions`. CDO normalisiert; CFO sieht Datendienst-Kosten.

**Durabilitaet / „nichts geht verloren":**
- Die Live-Historie liegt im **NAS-Docker-Volume**; sie ist **gitignored + vom Code-Sync ausgeschlossen**,
  damit ein Deploy sie **nie ueberschreibt**.
- **Off-NAS-Backup:** `deploy/backup-from-nas.sh` zieht eine **zeitgestempelte Kopie** aller Live-Stores auf
  den Mac (zweite, unabhaengige Kopie; alte Backups bleiben). Regelmaessig ausfuehren (oder spaeter cron).
- **Durables Ziel = Supabase** (vorhandenes Pro-Projekt): queryable, repliziert, gesichert -- die eigentliche
  Langfrist-Loesung (Roadmap Phase 1, noch nicht verdrahtet). Bis dahin: Datei-Store + Backup-Skript.

## 7 Status

- **Phase 0 (GATE A): erledigt** — CIO-Charta (Entwurf) + Risk-Agent (aktiv) + dieses Dokument + Registry/
  Organigramm. Keine Datenanbindung, keine Keys, keine Trades.
- **Phase 1/2: erledigt** — gratis Datenanbindung (Capability) + Store + advisory-Schleifen + Scorecard.
- **GATE C: Code fertig 2026-07-03 (AUS)** — Alpaca-Paper-Adapter (`investment/broker.py`), harte
  Order-Limits (`RiskAgent.pruefe_order`), Paper-Ausfuehrungspfad (`InvestmentEngine.paper_order`, Modus-Gate +
  CEO-Bestaetigung je Order), Tools `investment_modus`/`paper_konto`/`paper_order`. **Inert bis** CEO Alpaca-
  Keys setzt + paper aktiviert. Naechstes (CEO): Keys + Aktivierung, dann Paper-Track-Record aufbauen.
