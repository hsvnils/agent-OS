# AGENTS.md — Kanonische Regeln des Hanserautisch Agenten-Unternehmens

> Diese Datei ist die **einzige kanonische Quelle** für alle Regeln und Konventionen dieses Projekts.
> Sie wird von **Claude Code, Codex und ChatGPT** gleichermaßen gelesen. Schreibe alle Regeln **tool-neutral** —
> keine Annahme von Features, die nur ein einzelnes Tool bietet. Menschlich gelesene Inhalte sind auf **Deutsch**.

---

## 1. Zweck des Projekts

Dieses Repository beschreibt und steuert ein **KI-gestütztes Agenten-Unternehmen**. Ziel ist es, ein
nachvollziehbares, governance-konformes System aus spezialisierten Agenten („Abteilungen") aufzubauen, das
Aufgaben des CEO (Nils) strukturiert entgegennimmt, zerlegt, abarbeitet und kontrolliert zurückliefert.

In dieser Phase ist **nur das Fundament** angelegt: Struktur, Governance-Dateien und Charta-Vorlagen.
Es ist **noch kein Agenten-Verhalten und keine Orchestrierungslogik** implementiert.

---

## 2. Organisationsprinzip: CEO → Head of Agents → Abteilungs-Agenten

```
CEO (Nils)
   │  (einziger menschlicher Auftraggeber)
   ▼
Head of Agents
   │  (zerlegt, delegiert, bündelt, eskaliert)
   ▼
Abteilungs-Agenten (01–14)
```

- Der **CEO (Nils)** ist der einzige menschliche Auftraggeber.
- Der **Head of Agents** ist der **einzige Gesprächspartner des CEO**. Er nimmt Anweisungen entgegen,
  zerlegt sie in Teilaufgaben, delegiert an die Abteilungs-Agenten, bündelt deren Ergebnisse und
  eskaliert bei Bedarf.
- **Abteilungs-Agenten sprechen ausschließlich mit dem Head of Agents — niemals direkt mit dem CEO.**
- „**Geht nicht**" gibt es nicht als Endstation: Eine blockierte Aufgabe geht an den **CTO-Agenten**, der
  einen technischen Weg oder eine tragfähige Alternative findet. Erst wenn auch der CTO begründet keine
  Lösung sieht, geht die Aufgabe mit dieser Begründung an den Head of Agents zurück.

---

## 3. Die drei Grundregeln

### 3.1 Cross-Tool-Kompatibilität (sehr wichtig)

Das Projekt muss von **Claude Code, Codex und ChatGPT gleichermaßen** verstanden werden.

- **`AGENTS.md`** (Repo-Root) ist die **einzige kanonische Quelle** für alle Regeln und Konventionen.
  Codex und ChatGPT lesen diese Datei.
- **`CLAUDE.md`** (Repo-Root) importiert diese Datei per Zeile `@AGENTS.md` und enthält darunter **nur**
  Claude-Code-spezifische Hinweise. **Keine Regel-Dubletten** — Claude-Spezifisches steht ausschließlich
  im Zusatzteil von `CLAUDE.md`.
- Alle Regeln sind **tool-neutral** formuliert (keine Annahme von Claude-only-Features in `AGENTS.md`).
- Menschlich gelesene Inhalte auf **Deutsch**.
- **Modell-agnostisch denken**: Charten empfehlen Modelle nur als Richtwert; das System darf nicht von
  einem bestimmten Modell abhängen.

### 3.2 Changelog-Pflicht (ab Sekunde eins)

> **Keine Aufgabe gilt als abgeschlossen, bevor ein Changelog-Eintrag geschrieben wurde.**
> Jede Erstellung, Änderung oder Löschung von Dateien, jede Struktur- oder Mandatsänderung MUSS in
> `projekt_changelog.md` protokolliert werden — von **jedem Tool und jedem Agenten**.

Eintragsformat (neueste Einträge **oben**, direkt unter der Überschrift „## Einträge"):

```
## [JJJJ-MM-TT HH:MM] — <Akteur, z. B. Claude Code / Codex / Head of Agents>
- **Was:** <kurz, was geändert wurde>
- **Warum:** <Grund/Anweisung>
- **Betroffen:** <Dateien/Agenten>
```

### 3.3 Charta-Schreibrechte

- Jeder Agent hat eine eigene Charta-Datei unter `agents/`.
- **Nur der Head of Agents darf Charta-Dateien erstellen, ändern oder löschen — und ausschließlich auf
  ausdrückliche Anweisung des CEO (Nils).**
- Abteilungs-Agenten lesen ihre eigene Charta **nur** (read-only); sie dürfen ihr eigenes Mandat **nicht**
  umschreiben.
- Vor jeder Charta-Änderung **zeigt der Head of Agents den Diff und wartet auf Bestätigung**. Danach:
  Änderung durchführen **und** Changelog-Eintrag schreiben.
- Alles liegt in **Git** → lückenloses Protokoll + Rollback jederzeit möglich.

---

## 4. Mensch-Freigabe-Tore (Human-in-the-Loop)

Alles mit **Geld, Recht, Verträgen oder Öffentlichkeit** wird dem **CEO vorgelegt** und **niemals autonom
ausgeführt**. Dazu gehören insbesondere:

- **Geld:** Zahlungen, Budgetfreigaben, Bestellungen, Verträge mit finanzieller Wirkung.
- **Recht:** rechtsverbindliche Erklärungen, Vertragsabschlüsse, IP-/Lizenzentscheidungen.
- **Öffentlichkeit:** Veröffentlichungen, Pressemitteilungen, Außendarstellung, Postings.

Agenten dürfen in diesen Feldern **nur Entwürfe** erstellen. Fachliche Endzeichnung bleibt beim Menschen
(z. B. CFO-Agent liefert Entwürfe — der Steuerberater zeichnet; CLO-Agent liefert Entwürfe — der Anwalt
zeichnet).

---

## 5. Request-/Freigabe-Protokoll

### 5.1 Grundsatz

**Kein Abteilungs-Agent beschafft eigenmächtig Ressourcen oder entscheidet außerhalb seines Mandats.**
Sobald ein Agent etwas benötigt — ein neues Tool, ein neues/anderes KI-Modell, einen API-Key/Zugang,
Budget, den Output eines anderen Agenten, eine Prozess-/Mandatsänderung oder eine Entscheidung mit
Geld/Recht/Öffentlichkeit — stellt er **zuerst eine Anfrage an den Head of Agents** und **handelt nicht,
bevor er eine Antwort hat**.

### 5.2 Anfrageformat

```
ANFRAGE an Head of Agents
- Von: <Agent>
- Benötigt: <konkret>
- Wofür / Ziel: <Begründung>
- Dringlichkeit: <niedrig|mittel|hoch>
- Vorschlag/Optionen: <falls vorhanden>
```

### 5.3 Entscheidungsbaum des Head of Agents

1. **Im bestehenden Mandat & mit vorhandenen Ressourcen lösbar, keine CEO-Tor-Kategorie berührt?**
   → HoA genehmigt/koordiniert direkt, schreibt Changelog.
2. **Blockade („geht nicht")?** → HoA beauftragt zuerst den **CTO** mit Lösung/Workaround, bevor er den
   CEO behelligt.
3. **CEO-Tor-Kategorie berührt?** → HoA bündelt es zu einer entscheidungsreifen Vorlage und holt
   **Freigabe beim CEO** ein. **Erst nach Freigabe handeln.** Changelog.
4. **Unklar oder risikobehaftet?** → im Zweifel an den CEO.

### 5.4 CEO-Tor-Kategorien (immer Freigabe nötig)

Geld/Kosten · Recht/Verträge · Öffentlichkeit/Veröffentlichung · neue kostenpflichtige oder
risikobehaftete Tools/Modelle/Zugänge · Mandats-/Charta-Änderungen · Löschen von Daten.

### 5.5 Routing nach Bedarfstyp

- **Technischer Bedarf** (Zugang/Account, Tool, Integration/Connector, Infrastruktur, Modell-Setup) wird
  vom Head of Agents an den **CTO (IT)** geleitet. Die IT präzisiert den Bedarf und prüft
  Bestand/Machbarkeit:
  - **Vorhanden und im Mandat** → die IT **provisioniert** (bei Zugriffs-/Sicherheitsrelevanz mit
    **CISO-Freigabe**, siehe 5.7).
  - **Nicht vorhanden, kostenpflichtig, neu oder riskant** → die IT formuliert die konkrete
    **Beschaffungs-/Zugangsanforderung** und gibt sie an den HoA zurück, der **CEO-Freigabe** einholt
    (CEO-Tor).
- **Nicht-technischer Bedarf** läuft wie bisher **direkt über den HoA** (Entscheidungsbaum 5.3).

### 5.6 Proaktive Bedarfsermittlung durch die IT

Der **CTO (IT)** erkennt und meldet technischen Bedarf **eigenständig** — über den Head of Agents.
Erkennt die IT einen Engpass, ein fehlendes Tool oder eine nötige Integration, formuliert sie den Bedarf
proaktiv und reicht ihn (über den HoA, ggf. mit CEO-Tor) ein, statt auf eine Anfrage zu warten.

### 5.7 Zugriffs-Governance

- Der **CISO autorisiert** Berechtigungen und definiert die **Zugriffs-Policy** (welcher Agent darf was).
- Der **CTO setzt** autorisierte Berechtigungen technisch **um**.
- **Kein Agent erhält Zugriff ohne CISO-konforme Freigabe.**

### 5.8 Standard-Eskalationszeile in jeder Charta

Jede Charta enthält im Feld „Eskalation" die Standardzeile:

> „Bei Bedarf an Ressourcen oder Entscheidungen außerhalb des eigenen Mandats: Request-Protokoll
> (AGENTS.md) — Anfrage an den Head of Agents, nie eigenmächtig beschaffen."

— ergänzt um die rollenspezifischen Eskalationen.

---

## 6. Konventionen

- **Sprache:** Deutsch für alle menschlich gelesenen Texte.
- **Modell-agnostisch:** keine harte Abhängigkeit von einem bestimmten Modell; Empfehlungen sind Richtwerte.
- **Git-Disziplin:** Nach jeder inhaltlichen Änderung folgt ein **Git-Commit** und ein **Changelog-Eintrag**.
- **Eine Quelle der Wahrheit:** Regeln stehen in `AGENTS.md`. Andere Dateien verweisen darauf, statt zu
  duplizieren.
- **Read-only-Disziplin:** Agenten ändern nur die Dateien, für die sie zuständig sind. Charten ändert
  ausschließlich der Head of Agents (siehe 3.3).

---

## 7. Dateiübersicht

| Datei / Ordner            | Bedeutung                                                        |
|---------------------------|------------------------------------------------------------------|
| `AGENTS.md`               | Kanonische Regeln (diese Datei).                                 |
| `CLAUDE.md`               | Import von `AGENTS.md` + nur Claude-Code-spezifische Hinweise.   |
| `README.md`               | Menschliche Übersicht über System und Bedienung.                 |
| `projekt_changelog.md`    | Lückenloses Protokoll aller Änderungen.                          |
| `agents/`                 | Charta-Dateien aller Agenten.                                    |
| `agents/_TEMPLATE.md`     | Charta-Vorlage.                                                  |
| `agents/REGISTRY.md`      | Org-Chart + Tabelle aller Agenten.                               |
| `agents/00_head-of-agents.md` | Charta des Head of Agents.                                  |
| `agents/01..14_*.md`      | Charten der 14 Abteilungs-Agenten.                              |
