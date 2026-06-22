# Hanserautisch Agenten-Unternehmen

Dieses Repository ist das **Fundament eines KI-gestützten Agenten-Unternehmens**. Es bildet eine
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
- **Head of Agents** ist der **einzige Gesprächspartner des CEO**. Er zerlegt Anweisungen, delegiert an die
  Abteilungen, bündelt die Ergebnisse und eskaliert bei Bedarf.
- **Abteilungs-Agenten** sprechen **nur mit dem Head of Agents**, nie direkt mit dem CEO.
- Blockierte Aufgaben gehen an den **CTO-Agenten** („IT-Feuerwehr"), der einen Weg oder eine Alternative
  findet — „geht nicht" ist keine Endstation.
- **Geld, Recht, Verträge und Öffentlichkeit** werden immer dem CEO vorgelegt, nie autonom ausgeführt.

---

## Wie die Dateien zusammenhängen

| Datei / Ordner            | Rolle                                                              |
|---------------------------|-------------------------------------------------------------------|
| **`AGENTS.md`**           | **Die Regeln.** Einzige kanonische Quelle, von allen Tools gelesen.|
| `CLAUDE.md`               | Importiert `AGENTS.md` + nur Claude-Code-spezifische Hinweise.    |
| `README.md`               | Diese menschliche Übersicht.                                       |
| **`projekt_changelog.md`**| **Das Protokoll.** Lückenloses Logbuch aller Änderungen.          |
| **`agents/`**             | **Die Charten.** Eine Datei je Agent — Rolle, Auftrag, Grenzen.   |
| `agents/REGISTRY.md`      | Org-Chart + Übersichtstabelle aller Agenten.                      |
| `agents/_TEMPLATE.md`     | Vorlage für neue Charten.                                          |
| `docs/orchestrierung.md`  | Wie der Head of Agents Aufträge orchestriert (+ `docs/orchestrierung.xmind`). |

Kurz: **`AGENTS.md` = Regeln**, **`agents/` = Charten**, **`projekt_changelog.md` = Protokoll**,
**`docs/orchestrierung.md` = Ablauflogik**.

---

## Wie man eine Aufgabe stellt

1. Die Aufgabe wird **dem Head of Agents** gegeben (nie direkt einer Abteilung).
2. Der Head of Agents zerlegt sie, delegiert an die zuständigen Abteilungs-Agenten und bündelt die
   Ergebnisse.
3. Alles mit **Geld, Recht, Verträgen oder Öffentlichkeit** kommt als **Entwurf** zurück zur Freigabe durch
   den CEO.
4. Nach jeder Änderung wird ein **Changelog-Eintrag** geschrieben und committet.

Den vollständigen Auftrags-Lebenszyklus beschreibt [`docs/orchestrierung.md`](docs/orchestrierung.md).

---

## Die Abteilungen (Kurzüberblick)

| Kürzel | Agent | Schwerpunkt |
|--------|-------|-------------|
| 00 | Head of Agents | Orchestrierung, einziger CEO-Kontakt |
| 01 | Unternehmensberater | Strategie, Marktanalyse, Entscheidungsvorlagen |
| 02 | CAO | Verwaltung, Prozesse, Termine, Beschaffung |
| 03 | CFO | Budget, Forecast, Reporting (nur Entwürfe) |
| 04 | CRO | Umsatz, Vertrieb, Partnerschaften, Pricing |
| 05 | CISO | IT-Sicherheit, DSGVO, Zugriffe |
| 06 | CBO | Markenführung, Tonalität, Visual Identity |
| 07 | CPO | Produktstrategie, Roadmap, Specs |
| 08 | CTO | Technik, Infrastruktur, „IT-Feuerwehr" |
| 09 | CXO | Fan-/Nutzererlebnis, UX/CX |
| 10 | CCO | Content-Strategie & -Produktion, Video-Cutter-Steuerung |
| 11 | CDO | Daten, KPIs, Dashboards |
| 12 | CHRO | Personal, Vertragsvorlagen, Onboarding |
| 13 | CLO | Recht, Verträge, IP/Lizenzen (nur Entwürfe) |
| 14 | CKO | Wissensbasis, Kontextversorgung |

Details siehe [`agents/REGISTRY.md`](agents/REGISTRY.md) und die einzelnen Charta-Dateien.
