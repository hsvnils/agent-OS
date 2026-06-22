# Hanserautisch Agenten-Unternehmen

Dieses Repository ist das **Fundament eines KI-gestuetzten Agenten-Unternehmens**. Es bildet eine
Organisation aus spezialisierten Agenten („Abteilungen") ab, die Aufgaben strukturiert, nachvollziehbar und
governance-konform abarbeitet.

> **Status:** Fundament angelegt. Es ist **noch kein Agenten-Verhalten** implementiert — nur Struktur,
> Governance und Charta-Vorlagen.

---

## Das Organisationsprinzip

```
CEO (Nils)  →  Head of Agents  →  Abteilungs-Agenten (01–14)
```

- **CEO (Nils)** ist der einzige menschliche Auftraggeber.
- **Head of Agents** ist der **einzige Gespraechspartner des CEO**. Er zerlegt Anweisungen, delegiert an die
  Abteilungen, buendelt die Ergebnisse und eskaliert bei Bedarf.
- **Abteilungs-Agenten** sprechen **nur mit dem Head of Agents**, nie direkt mit dem CEO.
- Blockierte Aufgaben gehen an den **CTO-Agenten** („IT-Feuerwehr"), der einen Weg oder eine Alternative
  findet — „geht nicht" ist keine Endstation.
- **Geld, Recht, Vertraege und Oeffentlichkeit** werden immer dem CEO vorgelegt, nie autonom ausgefuehrt.

---

## Wie die Dateien zusammenhaengen

| Datei / Ordner            | Rolle                                                              |
|---------------------------|-------------------------------------------------------------------|
| **`AGENTS.md`**           | **Die Regeln.** Einzige kanonische Quelle, von allen Tools gelesen.|
| `CLAUDE.md`               | Importiert `AGENTS.md` + nur Claude-Code-spezifische Hinweise.    |
| `README.md`               | Diese menschliche Uebersicht.                                       |
| **`projekt_changelog.md`**| **Das Protokoll.** Lueckenloses Logbuch aller Aenderungen.          |
| **`agents/`**             | **Die Charten.** Eine Datei je Agent — Rolle, Auftrag, Grenzen.   |
| `agents/REGISTRY.md`      | Org-Chart + Uebersichtstabelle aller Agenten (Quelle der Wahrheit). |
| `agents/_TEMPLATE.md`     | Vorlage fuer neue Charten.                                          |
| `governance/orchestrierung.md` | Wie der Head of Agents Auftraege orchestriert (+ `.xmind`).   |
| `governance/organigramm.md` | Visuelle Hierarchie CEO → HoA → Abteilungen → Unter-Agenten (+ `.xmind`). |

Kurz: **`AGENTS.md` = Regeln**, **`agents/` = Charten**, **`projekt_changelog.md` = Protokoll**,
**`governance/` = Ablauflogik & Hierarchie**.

---

## Wie man eine Aufgabe stellt

1. Die Aufgabe wird **dem Head of Agents** gegeben (nie direkt einer Abteilung).
2. Der Head of Agents zerlegt sie, delegiert an die zustaendigen Abteilungs-Agenten und buendelt die
   Ergebnisse.
3. Alles mit **Geld, Recht, Vertraegen oder Oeffentlichkeit** kommt als **Entwurf** zurueck zur Freigabe durch
   den CEO.
4. Nach jeder Aenderung wird ein **Changelog-Eintrag** geschrieben und committet.

Den vollstaendigen Auftrags-Lebenszyklus beschreibt [`governance/orchestrierung.md`](governance/orchestrierung.md).

---

## Die Abteilungen (Kurzueberblick)

| Kuerzel | Agent | Schwerpunkt |
|--------|-------|-------------|
| 00 | Head of Agents | Orchestrierung, einziger CEO-Kontakt |
| 01 | Unternehmensberater | Strategie, Marktanalyse, Entscheidungsvorlagen |
| 02 | CAO | Verwaltung, Prozesse, Termine, Beschaffung |
| 03 | CFO | Budget, Forecast, Reporting (nur Entwuerfe) |
| 04 | CRO | Umsatz, Vertrieb, Partnerschaften, Pricing |
| 05 | CISO | IT-Sicherheit, DSGVO, Zugriffe |
| 06 | CBO | Markenfuehrung, Tonalitaet, Visual Identity |
| 07 | CPO | Produktstrategie, Roadmap, Specs |
| 08 | CTO | Technik, Infrastruktur, „IT-Feuerwehr" |
| 09 | CXO | Fan-/Nutzererlebnis, UX/CX |
| 10 | CCO | Content-Strategie & -Produktion, Video-Cutter-Steuerung |
| 11 | CDO | Daten, KPIs, Dashboards |
| 12 | CHRO | Personal, Vertragsvorlagen, Onboarding |
| 13 | CLO | Recht, Vertraege, IP/Lizenzen (nur Entwuerfe) |
| 14 | CKO | Wissensbasis, Kontextversorgung |

Details siehe [`agents/REGISTRY.md`](agents/REGISTRY.md) und die einzelnen Charta-Dateien.
