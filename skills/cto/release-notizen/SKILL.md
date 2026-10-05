---
name: release-notizen
version: 1.0.0
beschreibung: Schreibt verstaendliche Release-Notizen fuer den CEO aus Commits, Changelog und Roadmap-Etappen.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Release-Notizen (CTO, mit dem CPO)

## Wann anwenden
Nach einem Deploy, als Wochenueberblick oder wenn der CEO fragt „Was ist neu?“.

## Quellen
`projekt_changelog.md` (neueste oben), `git log` seit dem letzten Deploy, Roadmap-Status (`ROADMAP.md`, Etappen),
`docs/bekannte-fehler.md` (behobene Fehler).

## Regeln
- Fuer den CEO schreiben: was er jetzt tun/sehen kann, wo (Bereich in LUNA-OS, Telegram), nicht wie es gebaut ist.
- Gruppieren: **Neu** · **Verbessert** · **Behoben** · **Bekannt/offen** · **Was du tun musst** (z. B. Neustart, Test).
- Ehrlich: nicht gepruefte Dinge als „nicht live geprueft“ kennzeichnen; keine Uebertreibung.
- Kurz: je Punkt ein Satz, Fachbegriffe vermeiden oder erklaeren.

## Ausgabe
Release-Notiz mit Datum und Version (UI-Version, Commit), maximal eine Bildschirmseite.
