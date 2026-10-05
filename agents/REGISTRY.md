# Agenten-Registry

> Org-Chart und Uebersicht aller Agenten. Aenderungen an Charten (und damit an dieser Liste) nimmt
> **nur der Head of Agents auf CEO-Anweisung** vor (siehe `AGENTS.md`, Abschnitt 3.3).

## Org-Chart

```
CEO (Nils)
   │
   ▼
Head of Agents (00)
   │
   ├── 01  Unternehmensberater
   ├── 02  CAO   — Chief Administrative Officer
   ├── 03  CFO   — Chief Financial Officer
   ├── 04  CRO   — Chief Revenue Officer
   ├── 05  CISO  — Chief Information Security Officer
   ├── 06  CBO   — Chief Brand Officer
   ├── 07  CPO   — Chief Product Officer
   ├── 08  CTO   — Chief Technology Officer  (IT-Feuerwehr)
   ├── 09  CXO   — Chief Experience Officer
   ├── 10  CCO   — Chief Content Officer
   ├── 11  CDO   — Chief Data Officer
   ├── 12  CHRO  — Chief Human Resources Officer
   ├── 13  CLO   — Chief Legal Officer
   ├── 14  CKO   — Chief Knowledge Officer
   ├── 15  RES   — Researcher (zentraler Web-Recherche-Dienst)
   ├── 16  CIO   — Chief Investment Officer (Investment-Abteilung)
   │       └── 16a Risk-Agent (aktiv) — Pflicht-Gegenpruefer (Checker)
   └── 17  VID   — Videograf-Berater (Drehpraxis fuer Kundenauftraege)
```

Kommunikationsregel: Abteilungs-Agenten sprechen **nur mit dem Head of Agents**, nie direkt mit dem CEO.

> Diese Datei ist die **textbasierte Quelle der Wahrheit** (Agenten, Status, Charta-Datei). Die **visuelle
> Hierarchie-Darstellung** liegt in [`governance/organigramm.md`](../governance/organigramm.md)
> (+ [`organigramm.xmind`](../governance/organigramm.xmind)) und verweist auf diese Registry zurueck.

## Uebersichtstabelle

Zwei Zustaende werden unterschieden:
- **Status** = Charta/Mandat (`aktiv` = Mandat steht; `Entwurf` = noch nicht).
- **Orchestrator** = ob der Agent **real verdrahtet** ist und ueber den Orchestrator laeuft
  (`verdrahtet` = eigene Laeufe/Werkzeuge; `befragbar` = LUNA fragt ihn ueber `delegate`, mit Charta + Skills als
  System-Prompt; Stand 2026-10-05: alle Fachagenten).

| Kuerzel | Klarname | Status | Orchestrator | Charta-Datei |
|--------|----------|--------|--------------|--------------|
| HoA  | Head of Agents | aktiv | **verdrahtet** | `00_head-of-agents.md` |
| —    | Unternehmensberater | **aktiv** | **verdrahtet** | `01_unternehmensberater.md` |
| CAO  | Chief Administrative Officer | **aktiv** | **befragbar** | `02_cao.md` |
| CFO  | Chief Financial Officer | **aktiv** | **befragbar** | `03_cfo.md` |
| CRO  | Chief Revenue Officer | **aktiv** | **befragbar** | `04_cro.md` |
| CISO | Chief Information Security Officer | **aktiv** | **befragbar** | `05_ciso.md` |
| CBO  | Chief Brand Officer | **aktiv** | **befragbar** | `06_cbo.md` |
| CPO  | Chief Product Officer | **aktiv** | **befragbar** | `07_cpo.md` |
| CTO  | Chief Technology Officer | **aktiv** | **verdrahtet** | `08_cto.md` |
| CXO  | Chief Experience Officer | **aktiv** | **befragbar** | `09_cxo.md` |
| CCO  | Chief Content Officer | **aktiv** | **befragbar** | `10_cco-content.md` |
| CDO  | Chief Data Officer | **aktiv** | **befragbar** | `11_cdo.md` |
| CHRO | Chief Human Resources Officer | **aktiv** | **befragbar** | `12_chro.md` |
| CLO  | Chief Legal Officer | **aktiv** | **befragbar** | `13_clo.md` |
| CKO  | Chief Knowledge Officer | **aktiv** | **befragbar** | `14_cko.md` |
| RES  | Researcher | **aktiv** | **verdrahtet** | `15_researcher.md` |
| CIO  | Chief Investment Officer | Entwurf | **befragbar** | `16_cio.md` |
| CIO-RISK | Risk-Agent (Unter-Agent des CIO) | **aktiv** | **befragbar** | `16a_risk-agent.md` |
| VID  | Videograf-Berater | **aktiv** | **befragbar** | `17_videograf.md` |

> **Charta aktiv (Welle 1):** Head of Agents, CFO, CBO, CTO, CCO, Unternehmensberater, Researcher.
> **Welle 2 (AGENTEN_AUSBAU A6, 2026-10-05):** CAO, CISO, CPO, CXO, CHRO, CLO, CKO aktiv; CIO bleibt Entwurf.
> **Im Orchestrator verdrahtet (Bootstrap):** Head of Agents, CTO, Unternehmensberater, Researcher. Die
> uebrigen Agenten werden spaeter durch HoA + CTO (+ Berater) aufgebaut; ihre Verdrahtung folgt.
