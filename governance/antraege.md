# Antrags-/Freigabe-Policy

> Lebendes Steuerungsdokument, `AGENTS.md` untergeordnet. Umsetzung: `orchestrator/core/antraege.py`;
> Detailplan: `PHASE6_PLAN.md`; Roadmap-Einordnung: `ROADMAP.md` (Phase 6).

## Zweck

Ein **Antrag** ist die einzige kontrollierte Bruecke fuer Aenderungen, Beschaffungen und Ideen. Abteilungen
und der Head of Agents reichen ein; der **CEO entscheidet**. Es wird **nichts autonom ausgefuehrt** (AGENTS.md
4/5). Die tatsaechliche Umsetzung freigegebener Antraege erfolgt erst spaeter (Roadmap Phase 7) auf
Git-Branch + Tests + CEO-Merge.

## Lebenszyklus

```
eingereicht --(CEO ja)--> freigegeben --(Phase 7)--> in_umsetzung --> erledigt | fehlgeschlagen
            --(CEO nein)-> abgelehnt
```

- **freigegeben** dokumentiert nur die Entscheidung; ausgefuehrt wird in Phase 7.

## Wer darf was

- **Einreichen:** HoA (auch stellvertretend fuer eine konsultierte Abteilung). Eigenstaendiges Einreichen
  durch Abteilungen im Hintergrund kommt mit spaeteren Phasen (proaktiv/geplant).
- **Freigeben/Ablehnen:** ausschliesslich der **CEO** — der HoA fuehrt es nur auf ausdrueckliche Ansage aus und
  bestaetigt vorher gesprochen.

## Store & Audit

- Append-only, event-sourced: `antraege/log.jsonl` (versioniert). Dry-Run: `antraege/log_dryrun.jsonl`
  (gitignored).
- Jede Transition erzeugt einen umlautfreien Changelog-Eintrag. Leck-Schutz: keine `.env`-Werte im Store.
- Abgegrenzt von Changelog (Datei-Provenienz) und Gedaechtnis (Aufgaben-Erinnerung).

## CEO-Tor

Beruehrt ein Antrag Geld/Recht/Oeffentlichkeit/neue Kosten/Mandat/Datenloeschung, wird die Kategorie am Antrag
vermerkt; eine Freigabe ist zwingend (AGENTS.md 5.4). Die spaetere Ausfuehrung bleibt CEO-Tor-pflichtig.
