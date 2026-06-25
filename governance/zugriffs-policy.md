# Zugriffs-Policy — Capabilities und erlaubte Agenten (Least-Privilege)

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt uebergeordnet; bei Widerspruch gilt `AGENTS.md`.
> Owner ist spaeter der **CISO**. Bis dieser im Orchestrator aktiv ist, genehmigt der **HoA**
> Policy-Aenderungen; **neue externe Zugaenge = CEO-Tor**. Technische Umsetzung: der **CTO**.

## Prinzip

- **Secrets bleiben in `orchestrator/.env`** (per `.gitignore` ausgeschlossen, nie committen). Kein Tool und
  kein Agent gibt je einen rohen Key aus.
- **Capability-Muster:** Externe Integrationen sind **Tools**, die ihren Key intern aus der `.env` lesen.
  Agenten erhalten **Faehigkeiten (Tools)**, niemals den Key-Text.
- **Least-Privilege:** Ein Agent erhaelt nur die Capabilities, die er fuer sein Mandat braucht.

## Vergabe-Verfahren (CTO-Tool `grant_capability`)

- **Fall A — vorhandene, bereits bezahlte Capability, im Budget:** gewaehren (Agent in die Policy
  aufnehmen), **CEO informieren** + Changelog. Autonom durch die IT auf HoA-Anforderung.
- **Fall B — neue Kosten / neuer externer Zugang / neuer Account:** NICHT gewaehren; **CEO-Freigabe-Anfrage**
  erzeugen + Changelog. Budget-Pruefung gegen `finance/budget.md`. Erst nach Freigabe.

## Policy-Tabelle (Capability -> erlaubte Agenten)

> Bootstrap-Stand: noch **keine externen Capabilities** vergeben. Der Betrieb des Orchestrators selbst
> (HoA/Subagenten) laeuft ueber `ANTHROPIC_API_KEY` (GATE B) und ist keine vergebene Business-Capability.

| Capability | Beschreibung | Erlaubte Agenten | Status |
|------------|--------------|------------------|--------|
| `web_research` (Brave) | Rohe Web-Treffer fuer einfache Lookups. | **res (Researcher)** | **LIVE** seit 2026-06-25 (CEO-Freigabe via `BRAVE_API_KEY`, Gratis-Kontingent) |
| `web_research` (Anthropic-Web) | Agentische Mehrschritt-Recherche + Synthese fuer komplexe Fragen. | **res (Researcher)** | **vorbereitet -- CEO-Tor offen** (billbar; aus, bis `WEB_RESEARCH_ANTHROPIC=1`) |

> **Least-Privilege (Phase 8.5):** Die Web-Capability haelt **ausschliesslich der Researcher (Agent 15)**.
> Andere Abteilungen erhalten Web-Infos **nur ueber ihn** (via LUNA): sie melden ihren Bedarf an den HoA, der
> den Researcher beauftragt (`recherche_beauftragen` -> Research-Ticket). So gibt es **einen** Ort fuer
> Kosten, Rate-Limit und Audit.

> **Go-Live `web_research` (Fall B, CEO-Tor):** Beide Provider sind externer Zugang/Kosten.
> - **Brave Search API** -- ✅ aktiv. `BRAVE_API_KEY` in `orchestrator/.env` (Gratis-Kontingent; vom CEO geliefert).
> - **Anthropic-Web** -- nutzt den vorhandenen `ANTHROPIC_API_KEY`, ist aber **billbar** (ca. 10 USD je 1000
>   Suchen + Token). Bleibt **aus**, bis der CEO die Kosten freigibt durch `WEB_RESEARCH_ANTHROPIC=1` in
>   `orchestrator/.env` (vorher CFO-Kostenvoranschlag). Bis dahin laufen auch komplexe Anfragen ueber Brave.
> Ohne Freigabe liefert der jeweilige Provider einen Fall-B-Hinweis statt Ergebnissen (kein Absturz).

## Aenderungshistorie

| Datum | Capability | Agent | Aktion | Genehmigt durch |
|-------|------------|-------|--------|-----------------|
| 2026-06-25 | `web_research` | berater, cto | vorbereitet (Code+Tests) | offen (CEO-Tor) |
| 2026-06-25 | `web_research` (Brave) | berater, cto | **live** (BRAVE_API_KEY hinterlegt) | CEO (Key geliefert) |
| 2026-06-25 | `web_research` | res (Researcher) | auf Researcher **verengt** (Least-Privilege, Agent 15 neu) | CEO (Charta-Freigabe) |
