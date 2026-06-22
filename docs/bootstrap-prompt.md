# Claude-Code-Prompt — Bootstrap „Hanserautisch Agenten-Unternehmen"

> Diesen gesamten Block in Claude Code einfuegen. Er legt das Fundament an (Governance + Changelog + Agenten-Charta-System), noch ohne Agenten-Verhalten zu bauen.

---

Du richtest in diesem Repository das Fundament fuer das **Hanserautisch Agenten-Unternehmen** ein. Baue noch KEIN Agenten-Verhalten — nur die Struktur, Governance-Dateien und Charta-Vorlagen.

## Oberste Regel: Cross-Tool-Kompatibilitaet (sehr wichtig)
Dieses Projekt muss von **Claude Code, Codex und ChatGPT gleichermassen** verstanden werden.
- **`AGENTS.md`** (Repo-Root) ist die **einzige kanonische Quelle** fuer alle Regeln und Konventionen. Codex und ChatGPT lesen diese Datei.
- **`CLAUDE.md`** (Repo-Root) importiert sie per Zeile `@AGENTS.md` und enthaelt darunter nur Claude-Code-spezifische Hinweise. Keine Regel-Dubletten — Claude-spezifisches steht ausschliesslich im Zusatzteil.
- Schreibe alle Regeln **tool-neutral** (keine Annahme von Claude-only-Features in `AGENTS.md`).
- Menschlich gelesene Inhalte auf **Deutsch**.

## Zweite Regel: Changelog-Pflicht (ab Sekunde eins)
Lege `projekt_changelog.md` (Repo-Root) an. In `AGENTS.md` wird verbindlich festgehalten:
> **Keine Aufgabe gilt als abgeschlossen, bevor ein Changelog-Eintrag geschrieben wurde.** Jede Erstellung, Aenderung oder Loeschung von Dateien, jede Struktur- oder Mandatsaenderung MUSS in `projekt_changelog.md` protokolliert werden — von jedem Tool und jedem Agenten.

Eintragsformat (neueste Eintraege oben, direkt unter der Ueberschrift „## Eintraege"):
```
## [JJJJ-MM-TT HH:MM] — <Akteur, z. B. Claude Code / Codex / Head of Agents>
- **Was:** <kurz, was geändert wurde>
- **Warum:** <Grund/Anweisung>
- **Betroffen:** <Dateien/Agenten>
```

## Dritte Regel: Charta-Schreibrechte
- Jeder Agent hat eine eigene Charta-Datei unter `agents/`.
- **Nur der Head of Agents darf Charta-Dateien erstellen, aendern oder loeschen — und ausschliesslich auf ausdrueckliche Anweisung des CEO (Nils).**
- Abteilungs-Agenten lesen ihre eigene Charta **nur** (read-only); sie duerfen ihr eigenes Mandat nicht umschreiben.
- Vor jeder Charta-Aenderung zeigt der Head of Agents den Diff und wartet auf Bestaetigung. Danach: Aenderung + Changelog-Eintrag.
- Alles liegt in Git → lueckenloses Protokoll + Rollback.

## Anzulegende Struktur
```
/
  AGENTS.md
  CLAUDE.md
  README.md
  projekt_changelog.md
  agents/
    _TEMPLATE.md
    REGISTRY.md
    00_head-of-agents.md
    01_unternehmensberater.md
    02_cao.md
    03_cfo.md
    04_cro.md
    05_ciso.md
    06_cbo.md
    07_cpo.md
    08_cto.md
    09_cxo.md
    10_cco-content.md
    11_cdo.md
    12_chro.md
    13_clo.md
    14_cko.md
```

## Inhalte

**`AGENTS.md`** — kanonische Regeln, enthaelt mindestens:
- Zweck des Projekts und das Prinzip „CEO → Head of Agents → Abteilungs-Agenten". Abteilungs-Agenten sprechen nur mit dem Head of Agents, nie direkt mit dem CEO.
- Die drei Regeln oben (Cross-Tool, Changelog-Pflicht inkl. Format, Charta-Schreibrechte) ausformuliert.
- „Geht nicht" gibt es nicht als Endstation: blockierte Aufgaben gehen an den CTO-Agenten, der einen technischen Weg oder eine Alternative findet.
- Mensch-Freigabe-Tore: alles mit Geld, Recht, Vertraegen oder Oeffentlichkeit wird dem CEO vorgelegt, nie autonom ausgefuehrt.
- Konventionen: Deutsch fuer Menschen-Texte, modell-agnostisch denken, Git-Commit + Changelog nach jeder Aenderung.

**`CLAUDE.md`** — erste Zeile `@AGENTS.md`, darunter ein kurzer Abschnitt „Nur fuer Claude Code" (z. B. Hinweis, dass dies dieselben Regeln wie AGENTS.md sind und nicht abweichen darf).

**`README.md`** — menschliche Uebersicht: Was das System ist, das Org-Prinzip, wie die Dateien zusammenhaengen (AGENTS.md = Regeln, agents/ = Charten, projekt_changelog.md = Protokoll), wie man eine Aufgabe an den Head of Agents gibt.

**`agents/_TEMPLATE.md`** — Charta-Vorlage mit genau diesen Feldern:
```
# Agent: <Klarname> (<Kürzel>)
Status: aktiv | Entwurf
Modell: <empfohlenes Modell, modell-agnostisch>

## Rolle
<1–2 Sätze>

## Auftrag / Verantwortlichkeiten
- <…>

## Ausdrücklich NICHT
- <Grenzen / was dieser Agent nicht tut>

## Tools & Zugänge
- <…>

## Eskalation
- Wann an Head of Agents, wann an CTO (Blockaden), wann an CEO (Geld/Recht/Öffentlichkeit).

## Output-Format
- <wie Ergebnisse an den Head of Agents geliefert werden>

## Änderungsregel
Diese Datei darf nur der Head of Agents auf Anweisung des CEO ändern.
```

**`agents/REGISTRY.md`** — Org-Chart (CEO → Head of Agents → Abteilungen) plus Tabelle aller Agenten mit Kuerzel, Klarname, Status, Charta-Dateiname.

**`agents/00_head-of-agents.md`** — vollstaendige Charta nach Vorlage. Kernpunkte: einziger Gespraechspartner des CEO; zerlegt Anweisungen, delegiert, buendelt, eskaliert; **exklusives Schreibrecht auf `agents/`** (auf CEO-Anweisung, mit Diff-Vorlage); muss nach jeder Aktion den Changelog schreiben; Modell-Empfehlung: starkes agentisches Modell, guenstiges Modell fuers interne Routing.

**Die 14 Abteilungs-Charten** — aus der Vorlage erzeugen, vorerst `Status: Entwurf`, mit ausgefuellter Rolle/Auftrag je Agent (Kurzfassung genuegt; Detail kommt spaeter):
- 01 Unternehmensberater — Strategie, Marktanalyse, Entscheidungsvorlagen
- 02 CAO Chief Administrative Officer — Verwaltung, Prozesse, Termine, Beschaffung
- 03 CFO Chief Financial Officer — Budget, Forecast, Reporting (nur Entwuerfe; Steuerberater zeichnet)
- 04 CRO Chief Revenue Officer — Umsatz, Vertrieb, Partnerschaften, Pricing (ersetzt das fruehere „CUO")
- 05 CISO Chief Information Security Officer — IT-Sicherheit, DSGVO, Zugriffe
- 06 CBO Chief Brand Officer — Markenfuehrung, Tonalitaet, Visual Identity
- 07 CPO Chief Product Officer — Produktstrategie, Roadmap der App, Specs
- 08 CTO Chief Technology Officer — Technik, Infrastruktur, „IT-Feuerwehr" fuer blockierte Aufgaben
- 09 CXO Chief Experience Officer — Fan-/Nutzererlebnis, UX/CX
- 10 CCO Chief Content Officer — Content-Strategie & -Produktion ueber alle Kanaele, steuert den Video-Cutter-Agenten
- 11 CDO Chief Data Officer — Daten, KPIs, Dashboards, liefert anderen saubere Zahlen
- 12 CHRO Chief Human Resources Officer — Personal, Vertraege-Vorlagen, Onboarding
- 13 CLO Chief Legal Officer — Recht, Vertraege, IP/Lizenzen (nur Entwuerfe; Anwalt zeichnet)
- 14 CKO Chief Knowledge Officer — Wissensbasis, versorgt Agenten mit Kontext

## Abschluss
1. Git initialisieren (falls noch nicht) und alles in einem ersten Commit festhalten.
2. Ersten Changelog-Eintrag schreiben: „Projekt initialisiert — Governance, Charta-System und 14 Agenten-Entwuerfe angelegt."
3. Mir zum Schluss ausgeben: den Verzeichnisbaum, den vollstaendigen Inhalt von `agents/00_head-of-agents.md` und `AGENTS.md` zur Kontrolle.

## Guardrails
- Noch kein Agenten-Verhalten / keine Orchestrierungslogik bauen — nur Struktur und Dokumente.
- Keine Secrets/Keys anlegen oder erfinden.
- `AGENTS.md` tool-neutral halten; nichts Claude-Spezifisches dort hineinschreiben.
- Nach jeder Aenderung gilt die Changelog-Pflicht — auch fuer diesen ersten Lauf.
