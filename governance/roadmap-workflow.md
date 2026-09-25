# Roadmap-Workflow

- Status: verbindlich
- Stand: 2026-09-25
- Arbeitsbranch: `ai/doku-standards`
- Hinweis: Diese Datei beschreibt den verbindlichen Ablauf fuer Roadmaps. Sie ist selbst keine Roadmap und
  aktiviert keine Arbeit. `AGENTS.md` bleibt uebergeordnet; bei Widerspruch gilt `AGENTS.md`.

## Zweck

Immer derselbe Ablauf, wenn eine Roadmap erstellt und spaeter abgearbeitet wird. Gilt fuer Claude Code, Codex,
ChatGPT und den Head of Agents gleichermassen und ergaenzt `AGENTS.md`; deren Regeln (Changelog-Pflicht,
CEO-Tore, Charta-Schreibrechte, Request-Protokoll) werden dadurch weder ersetzt noch gelockert.

## Grundregel

Eine Roadmap ist ein **Plan, kein Auftrag**. Bis die Roadmap fertig ist **und** der CEO ausdruecklich das Go
zum Abarbeiten gegeben hat, wird **nichts** geaendert: kein App-Code, keine Migration, kein Deploy, kein
Container-/Dienst-Neustart, keine Konfiguration, kein produktiver Datenwrite. Erlaubt sind in dieser Zeit
ausschliesslich: read-only Analyse, die Roadmap-Datei selbst, ihr Eintrag im Roadmap-Verzeichnis
(`ROADMAP.md`) und der Changelog-Eintrag.

## Phase A - Vorbereitung

- **A1 Branch zuerst.** Eigenen Branch `ai/<kurzer-themenname>` anlegen. Nie direkt auf `main` arbeiten.
- **A2 Datei anlegen.** Genau eine Markdown-Datei im Repository-Root, benannt nach dem Schema
  `<THEMA>_ROADMAP.md` (Grossbuchstaben, Ziffern, Unterstrich). Die Namenskonvention ist Pflicht, weil
  `scripts/doku_check.py` daran alle Roadmaps findet und prueft.
- **A3 Pflicht-Header.** Der Kopf enthaelt `Status`, `Stand`, `Arbeitsbranch`, `Basiscommit`,
  `Naechster Schritt` und `Hinweis` (Vorlage siehe unten). Ohne diese Felder scheitert der Doku-Check.
- **A4 Registrieren.** Die Datei im Abschnitt „Roadmap-Verzeichnis" in `ROADMAP.md` eintragen
  (`ROADMAP.md` ist die Master-Roadmap; Teil-Roadmaps haengen daran).
- **A5 Uebergabe in der Datei.** Das Header-Feld `Naechster Schritt` ist die tool-neutrale Uebergabe: Es nennt
  jederzeit den naechsten **sicheren** Schritt, damit ein Wechsel zwischen Claude Code, Codex, ChatGPT oder
  einer neuen Sitzung ohne Gespraechsverlauf funktioniert. Es wird bei jedem Etappenwechsel fortgeschrieben.

## Phase B - Analyse (read-only)

- **B1 Belegpflicht.** Jeder Befund braucht einen Nachweis (Befehlsausgabe, Log, Datei-Zitat mit Zeile,
  Testlauf, API-Antwort). Der produktive Zustand auf NAS oder MACO470 gilt ohne Nachweis als **unbekannt** und
  wird nicht behauptet.
- **B2 Ursache vor Loesung.** Erst die Wirkkette vollstaendig verstehen (Quelle -> Verarbeitung ->
  Speicherung -> Zustellung/Anzeige; siehe `docs/datenfluesse.md`), dann planen. Keine Symptomkosmetik ohne
  benannte Ursache.
- **B3 Register zuerst.** Vor jeder Bewertung externer Tools/Ideen und vor jeder Architekturentscheidung
  `docs/entscheidungs-register.md` pruefen (schon entschieden? warum?), vor jeder Fehlersuche
  `docs/bekannte-fehler.md`.
- **B4 Scope und Nicht-Scope.** Beides ausdruecklich aufschreiben. Folgende **Schutzbereiche** gehoeren in den
  Nicht-Scope, solange keine eigene CEO-Freigabe vorliegt:
  - `.env`-Dateien, Secrets, Token-Stores, SSH-/Deploy-Schluessel, Zugriffe (CISO, `AGENTS.md` 5.7)
  - der Telegram-Bot (genau **ein** Poller, laeuft auf der NAS; nie zusaetzlich starten)
  - Live-Daten: Stores auf der NAS, Supabase-Tabellen, NAS-Clip-Archiv, Backups
  - laufende Dienste und Zeitplaene: Container `luna-telegram`/`luna-os`, `cutter-worker`, `luna-backup.timer`,
    DSM-Aufgaben, Windows-Aufgaben/Keepalive, Scheduler-Zeiten
  - Charta-Dateien unter `agents/` (nur HoA auf CEO-Anweisung, `AGENTS.md` 3.3)
  - alle CEO-Tor-Kategorien (`AGENTS.md` 4 und 5.4): Geld/Budget, Recht, Oeffentlichkeit (Posten auf
    Facebook/Instagram, Mails nach aussen), Trades, neue kostenpflichtige Modelle/Dienste, Loeschen von Daten
- **B5 Umfang messen.** Wie viele Datensaetze, Dateien, Endpunkte, Agenten, Geraete sind betroffen? Zahlen
  statt Gefuehl, damit priorisiert werden kann.

## Phase C - Plan und Gates

- **C1 Etappen.** Die Arbeit in kleine, einzeln abnehmbare Etappen schneiden. Jede Etappe hat Ziel und Scope.
- **C2 Gate je Etappe.** Messbare Abnahmekriterien, nicht „sieht gut aus". Beispiele: Test-Gate gruen (siehe
  E5), Doku-Check gruen, Readback liefert exakt den erwarteten Wert, Wirkung beim Empfaenger nachgewiesen,
  visuelle Abnahme durch den CEO.
- **C3 Verifikation vorab formulieren.** Fuer jede Etappe den konkreten Pruefbefehl **und das erwartete
  Ergebnis** schon in der Roadmap notieren. Die Pruefung muss exakt gefiltert sein (Zeitraum, Konto, Geraet,
  Job-ID); eine unscharfe Pruefung erzeugt Fehlalarme und gilt nicht als Verifikation. **„Erzeugt" ist nicht
  „angekommen":** Wo etwas zugestellt wird (Telegram, Mail, Post, Datei auf anderem Geraet), wird am
  Empfaenger geprueft, nicht am Absender.
- **C4 Dry-Run-Pflicht.** Vor jeder produktiven Mutation ein Trockenlauf, der zeigt, was sich wie aendern
  wuerde, ohne zu schreiben (z. B. `deploy/sync-to-nas.sh --dry-run`, `SELECT` mit der geplanten Regel,
  Skript mit `--dry-run`).
- **C5 Risiko und Umkehrbarkeit.** Pro Etappe: was kann schiefgehen, wie wird es bemerkt, wie kommt man zurueck.
  Bevorzugt reversible Mittel (Feature-Flag/deaktivieren statt loeschen, additive Migration statt Ersetzung).
- **C6 Reihenfolge und Aufwand.** Abhaengigkeiten zwischen Etappen benennen, dazu je eine grobe Aufwands- und
  Risikoeinschaetzung.
- **C7 Dokumentationspflicht vorab benennen.** Welche Dateien bei der Umsetzung fortgeschrieben werden:
  - `projekt_changelog.md` (immer)
  - Etappen-Status in der Roadmap selbst (`geplant` -> `umgesetzt` -> `deployt` -> `verifiziert`)
  - `ROADMAP.md` (Status-Uebersicht, Roadmap-Verzeichnis)
  - `docs/entscheidungs-register.md` (jede getroffene oder verworfene Entscheidung mit Grund)
  - `docs/bekannte-fehler.md` (neu gefundene Fehler, Stolperfallen, Umgehungen)
  - `docs/datenfluesse.md` (jede neue/geaenderte Verbindung, Tabelle, Datei, Schnittstelle)
  - `AGENTS.md` Abschnitt 7 (neue Dateien/Ordner), betroffene `governance/`-Dokumente
- **C8 Definition of Done.** Woran ist die Gesamt-Roadmap fertig, und wer setzt den Status auf abgeschlossen
  (Standard: der CEO nimmt ab, der ausfuehrende Agent traegt ein).

## Phase D - Freigabe

- **D1 Vorlegen statt loslegen.** Die fertige Roadmap wird dem CEO vorgelegt. Bis zum Go wird nichts umgesetzt.
- **D2 Go pro Etappe.** Es gibt kein Blanko-Go fuer die gesamte Roadmap. Jede Etappe wird einzeln freigegeben.
- **D3 Was das Go einer Etappe abdeckt.** Aenderungen und Commits **auf dem Arbeitsbranch** innerhalb des
  Etappen-Scopes (Git-Disziplin nach `AGENTS.md` 6).
- **D4 Immer eigene, ausdrueckliche Freigabe.** Push, Merge nach `main`, Deploy auf NAS oder MACO470,
  Container-/Dienst-Neustart, Supabase-Migration, Aenderung an Zeitplaenen/Cronjobs/DSM-Aufgaben,
  Policy-/Zugriffsaenderung, jeder produktive Datenwrite und alles aus den CEO-Tor-Kategorien.

## Phase E - Abarbeitung

- **E1 Dry-Run zuerst.** Ergebnis dem CEO zeigen, erst dann anwenden.
- **E2 Produktive Ausfuehrung durch den CEO, wo Rechte fehlen.** Schritte mit `sudo` auf der NAS
  (Container-Neustart), Supabase-SQL-Migrationen, DSM- und Windows-Einstellungen fuehrt der CEO aus; der Agent
  liefert den fertigen, geprueften Befehl bzw. Inhalt und die Readback-Pruefung dazu.
- **E3 Verifikation.** Genau die in C3 festgelegte Pruefung ausfuehren und das Ergebnis gegen die Erwartung
  stellen. Nur ein bestandener Readback setzt die Etappe auf `verifiziert`.
- **E4 Doku fortschreiben.** Nach jedem produktiven Schritt Etappen-Status, `Naechster Schritt` und Changelog
  aktualisieren, bevor die naechste Etappe beginnt.
- **E5 Test-Gate (statt CI).** Das Repo hat keine CI. Am Gate jeder Etappe laufen lokal beide Suiten
  (`orchestrator/tests`, `cutter/tests`) und `scripts/doku_check.py`. Massstab ist die Baseline in
  `docs/bekannte-fehler.md`: **kein neuer roter Test**. Aendert eine Etappe die Baseline (Test repariert oder
  bewusst neu rot), wird sie dort fortgeschrieben.
- **E6 Bei Abweichung stoppen.** Weicht ein Ergebnis von der Erwartung ab, wird gestoppt und gemeldet. Keine
  Reparatur auf Verdacht, keine zweite Mutation ohne neue Analyse und neue Freigabe. Der Befund kommt nach
  `docs/bekannte-fehler.md`.

## Phase F - Abschluss

- **F1 Status fortschreiben.** `Status`, `Stand` und `Naechster Schritt` im Kopf der Roadmap aktualisieren;
  erledigte Etappen als abgeschlossen markieren; Status in `ROADMAP.md` nachziehen.
- **F2 Folgethemen.** Offene Folgethemen ausdruecklich in der Roadmap nennen (oder als neue Roadmap/Backlog in
  `ROADMAP.md` eintragen).
- **F3 Integration.** Push, Merge nach `main`, Deploy und Loeschen des Arbeitsbranches nur nach ausdruecklichem
  Auftrag (D4). Nach einem Code-Merge werden Deploy-Befehl und noetiger Neustart ausdruecklich benannt.

## Pflicht-Header (Vorlage)

```markdown
# Roadmap: <Titel>

- Status: <geplant | in Umsetzung | abgeschlossen | verworfen>
- Stand: <JJJJ-MM-TT>
- Arbeitsbranch: `ai/<thema>`
- Basiscommit: `<kurzer sha>`
- Naechster Schritt: <der naechste sichere Schritt, in einem Satz>
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.
```

## Etappen-Vorlage

```markdown
### Etappe <n>: <Titel>

- Status: <geplant | umgesetzt | deployt | verifiziert>
- Ziel / Scope / Nicht-Scope: ...
- Gate: ...
- Verifikation: `<Befehl>` -> erwartet: <exaktes Ergebnis>
- Dry-Run: ...
- Risiko / Rueckweg: ...
- Abhaengig von / Aufwand / Risiko: ...
```

## Bestand

Aeltere Roadmaps und Plaene (`ROADMAP.md`, `INVESTMENT_ROADMAP.md`, `HCC_INTEGRATION_ROADMAP.md`,
`docs/maco470-roadmap.md`, `*_PLAN.md`) entstanden vor diesem Workflow. Sie werden nicht umbenannt (Links
bleiben gueltig); `scripts/doku_check.py` fuehrt sie als Bestand. Wer eine Bestands-Roadmap inhaltlich
weiterfuehrt, ruestet dabei den Pflicht-Header nach und nimmt sie aus der Bestandsliste.

## Kurz-Checkliste

1. Branch `ai/<thema>` angelegt.
2. `<THEMA>_ROADMAP.md` mit Pflicht-Header angelegt.
3. Im Roadmap-Verzeichnis in `ROADMAP.md` registriert.
4. Register und bekannte Fehler geprueft; read-only Analyse mit Belegen, Ursache benannt.
5. Scope und Nicht-Scope inklusive Schutzbereichen notiert.
6. Etappen mit Gates, Verifikation samt Erwartung, Dry-Run, Risiko und Umkehrbarkeit beschrieben.
7. Dokumentationspflichten und Definition of Done benannt.
8. `Naechster Schritt` gesetzt, Changelog-Eintrag geschrieben.
9. Roadmap vorgelegt, nichts geaendert.
10. Go pro Etappe eingeholt, dann erst umsetzen.
