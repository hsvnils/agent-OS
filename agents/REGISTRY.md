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
   └── 14  CKO   — Chief Knowledge Officer
```

Kommunikationsregel: Abteilungs-Agenten sprechen **nur mit dem Head of Agents**, nie direkt mit dem CEO.

> Diese Datei ist die **textbasierte Quelle der Wahrheit** (Agenten, Status, Charta-Datei). Die **visuelle
> Hierarchie-Darstellung** liegt in [`governance/organigramm.md`](../governance/organigramm.md)
> (+ [`organigramm.xmind`](../governance/organigramm.xmind)) und verweist auf diese Registry zurueck.

## Uebersichtstabelle

Zwei Zustaende werden unterschieden:
- **Status** = Charta/Mandat (`aktiv` = Mandat steht; `Entwurf` = noch nicht).
- **Orchestrator** = ob der Agent **real verdrahtet** ist und ueber den Orchestrator laeuft
  (`verdrahtet` vs. `—`).

| Kuerzel | Klarname | Status | Orchestrator | Charta-Datei |
|--------|----------|--------|--------------|--------------|
| HoA  | Head of Agents | aktiv | **verdrahtet** | `00_head-of-agents.md` |
| —    | Unternehmensberater | **aktiv** | **verdrahtet** | `01_unternehmensberater.md` |
| CAO  | Chief Administrative Officer | Entwurf | — | `02_cao.md` |
| CFO  | Chief Financial Officer | **aktiv** | — | `03_cfo.md` |
| CRO  | Chief Revenue Officer | Entwurf | — | `04_cro.md` |
| CISO | Chief Information Security Officer | Entwurf | — | `05_ciso.md` |
| CBO  | Chief Brand Officer | **aktiv** | — | `06_cbo.md` |
| CPO  | Chief Product Officer | Entwurf | — | `07_cpo.md` |
| CTO  | Chief Technology Officer | **aktiv** | **verdrahtet** | `08_cto.md` |
| CXO  | Chief Experience Officer | Entwurf | — | `09_cxo.md` |
| CCO  | Chief Content Officer | **aktiv** | — | `10_cco-content.md` |
| CDO  | Chief Data Officer | Entwurf | — | `11_cdo.md` |
| CHRO | Chief Human Resources Officer | Entwurf | — | `12_chro.md` |
| CLO  | Chief Legal Officer | Entwurf | — | `13_clo.md` |
| CKO  | Chief Knowledge Officer | Entwurf | — | `14_cko.md` |

> **Charta aktiv (Welle 1):** Head of Agents, CFO, CBO, CTO, CCO, Unternehmensberater.
> **Im Orchestrator verdrahtet (Bootstrap):** Head of Agents, CTO, Unternehmensberater. Die uebrigen
> Agenten werden spaeter durch HoA + CTO (+ Berater) aufgebaut; ihre Verdrahtung folgt.
