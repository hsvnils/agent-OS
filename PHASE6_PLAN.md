# PHASE6_PLAN.md — Antrags-/Freigabe-Workflow (Rueckgrat der Mensch-im-Spiel-Steuerung)

> **Status: PLAN — wartet auf GATE (Design-Freigabe).** Detailplan zu Phase 6 der `ROADMAP.md`. Hier wird die
> kontrollierte Bruecke gebaut, ueber die Abteilungen/HoA **Aenderungen vorschlagen** und der **CEO sie
> freigibt** — bevor in Phase 7 ueberhaupt etwas ausgefuehrt wird. `AGENTS.md` bleibt kanonisch.

---

## 1. Zweck & Scope

Ein **Antrag** (Proposal) ist die einzige Bruecke fuer Aenderungen/Beschaffungen/Ideen. Jeder Antrag durchlaeuft
einen nachvollziehbaren Lebenszyklus; der CEO entscheidet; nichts wird autonom ausgefuehrt.

**In diesem Build:** Antrags-Store + Lebenszyklus + HoA-Werkzeuge (stellen, zeigen, freigeben/ablehnen) +
Panel + Self-Checks. **Ausdruecklich NICHT:** echte Ausfuehrung von Aenderungen (das ist Phase 7) und
autonomes, eigenstaendiges Einreichen durch Abteilungen im Hintergrund (kommt mit Phase 9/12). Phase 6 liefert
die **Mechanik + Governance**; der HoA stellt Antraege (auch stellvertretend fuer eine konsultierte Abteilung).

---

## 2. Datenmodell & Store

- **Store:** `antraege/log.jsonl` (append-only, **event-sourced**, git-versioniert, auditierbar). Dry-Run ->
  `antraege/log_dryrun.jsonl` (gitignored). Zustand wird durch Falten der Events abgeleitet.
- **Event-Felder:** `ts`, `antrag_id`, `event` (`eingereicht`|`freigegeben`|`abgelehnt`|`in_umsetzung`|
  `erledigt`|`fehlgeschlagen`), `von` (Agent/HoA), `titel`, `beschreibung`, `kategorie` (CEO-Tor-Kategorie
  falls beruehrt), `betroffen`, `begruendung`/`grund`, `akteur` (bei Freigabe: CEO). Leck-geschuetzt.
- **Abgeleiteter Zustand je Antrag:** aktueller Status + Verlauf. Abgegrenzt von Changelog (Datei-Provenienz)
  und Gedaechtnis (Aufgaben-Erinnerung) — Antraege = Entscheidungs-/Freigabe-Vorgaenge.

## 3. Lebenszyklus

```
eingereicht --(CEO ja)--> freigegeben --(Phase 7)--> in_umsetzung --> erledigt | fehlgeschlagen
            --(CEO nein)-> abgelehnt
```

- **freigegeben** heisst in Phase 6 nur: Entscheidung dokumentiert, bereit zur Umsetzung. Die eigentliche
  Ausfuehrung macht die Execution-Engine (Phase 7) — weiterhin auf Branch + Tests + CEO-Merge.

## 4. HoA-Werkzeuge (Voice jetzt; spaeter auch Telegram)

- `antrag_stellen(titel, beschreibung, kategorie?, betroffen?)` — reicht einen Antrag ein (HoA, ggf.
  stellvertretend fuer eine Abteilung). Antwort: Antrag-ID + Status `eingereicht`.
- `antraege_zeigen(status?)` — offene/alle Antraege als Panel + gesprochene Kurzfassung.
- `antrag_freigeben(antrag_id)` / `antrag_ablehnen(antrag_id, grund)` — **nur nach ausdruecklicher
  CEO-Bestaetigung**. Der HoA bestaetigt die Entscheidung vorher gesprochen ("Ich gebe Antrag X frei, richtig?").

> CEO-Tor bleibt: Freigabe ist eine **CEO-Handlung**. Der HoA fuehrt sie nur auf ausdrueckliche Ansage aus und
> protokolliert jede Transition (Changelog + Antrags-Log).

## 5. Oberflaeche

- Neuer Panel-Typ `antraege` (Liste: ID, Titel, von, Status, Kategorie). Auf „zeig mir die Antraege".
- Spaeter (Phase 14): visuelle/MindMap-Darstellung.

## 6. Dateien

```
orchestrator/
  core/antraege.py            # NEU: create/list/get + Status-Transitionen (event-sourced), leck-geschuetzt
  channels/voice/pipeline.py  # ERWEITERT: Tools antrag_stellen/antraege_zeigen/antrag_freigeben/ablehnen
  channels/voice/panels.py    # ERWEITERT: Panel-Typ 'antraege'
  tests/test_antraege.py      # NEU: Self-Checks
antraege/log.jsonl            # NEU: kanonischer Store (versioniert)
.gitignore                    # ERWEITERT: antraege/log_dryrun.jsonl
governance/antraege.md        # NEU: Policy (Lebenszyklus, wer darf was, Abgrenzung)
```

## 7. Self-Checks (offline, ohne Kosten)

1. **Round-Trip:** `antrag_stellen` -> `list` zeigt ihn als `eingereicht`.
2. **Freigabe/Ablehnung:** Status-Transitionen korrekt; Verlauf erhalten.
3. **Event-Sourcing:** Zustand wird korrekt aus Events gefaltet (auch nach mehreren Transitionen).
4. **Leck-Schutz:** ein Test-Secret in einem Antrag erscheint nicht im Store.
5. **Changelog:** jede Transition erzeugt einen umlautfreien Changelog-Eintrag.
6. **Panel:** `antraege`-Panel listet offene Antraege korrekt.

Bestehende Self-Checks bleiben gruen; Ziel danach: **>= 30/30**.

## 8. Governance & Sicherheit

- **Keine Ausfuehrung in Phase 6** — nur Vorschlag + Entscheidung. Ausfuehrung erst Phase 7 (Branch+Tests+Merge).
- Freigabe ist CEO-Handlung; HoA bestaetigt vorher; alles auditierbar (Antrags-Log + Changelog).
- CEO-Tor-Kategorie wird am Antrag vermerkt; bei Geld/Recht/Oeffentlichkeit etc. ist Freigabe zwingend.

## 9. GATE

- **GATE (jetzt):** Freigabe dieses Designs. Danach Offline-Implementierung mit Self-Checks (ohne Kosten),
  danach kurze Live-Probe im Sprachkanal (Antrag stellen, anzeigen, freigeben).
- **Offene Designfrage fuer den CEO:** Freigabe ausschliesslich per Sprache/Text durch dich (so geplant) —
  oder zusaetzlich eine sichtbare Bestaetigung in der Oberflaeche? (Standard: Sprach-/Textbestaetigung.)
