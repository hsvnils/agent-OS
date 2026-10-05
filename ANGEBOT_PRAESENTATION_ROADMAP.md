# Roadmap: Canva-Praesentation im Angebot (DE/EN)
- Status: abgeschlossen
- Stand: 2026-10-05
- Arbeitsbranch: `ai/canva-videograf`
- Basiscommit: `782e428`
- Naechster Schritt: keiner -- abgeschlossen auf CEO-Wunsch (2026-10-05); Fehler beim ersten echten Angebot meldet der CEO.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Oeffentliche Canva-Links mit in Angebote einbauen. Deutscher Link: https://canva.link/so4wrkmr0n7gfq1 -- Englischer
Link: https://canva.link/yyeywahmisjymuw“. Entscheidungen: Link **im Angebots-PDF und im Mailtext**; Sprache **je Angebot
waehlbar** (Deutsch / Englisch / keiner, Standard Deutsch).

## Analyse (read-only, 2026-10-05)

- Angebote kennen bisher **keine Sprache** (`orchestrator/core/angebote.py`); der Gmail-Entwurf entsteht in `mail_text()`
  (Zeile 813), das PDF und der digitale Beleg nutzen gemeinsam `AngebotStore.teile()` (Zeile 508).
- Texte des Angebots/der Preisliste liegen im Leistungskatalog (`core/katalog.py`, Abschnitt `texte`, nur NAS in
  `buchhaltung/katalog.json`, editierbar im Katalog-Editor, Aenderungen in der Kette protokolliert).
- Die Links sind oeffentlich; der Versand des Angebots bleibt wie bisher beim CEO (Gmail-Entwurf, Senden = CEO).

## Etappe P1: Praesentations-Link im Angebot

- Status: umgesetzt (2026-10-05) -- Katalog-Felder `praesentation_de/_en` + Linktexte (Standard = CEO-Links, alte
  Kataloge bekommen den Standard, "" = aus, nur https), Angebotsfeld `praesentation` (Standard de, eingefroren als
  {sprache, url, text}), klickbar in beiden PDF-Layouts, im digitalen Beleg und im Mailtext; Altangebote ohne Link.
  Tests `test_angebot_praesentation.py`; Browsertest Editor/Beleg/Katalog auf Rechner, iPad, iPhone 17 Pro.
- Ziel / Scope:
  - Katalog-Texte: `praesentation_de` und `praesentation_en` (Standard = die zwei Links oben) plus Linktext je Sprache
    (Vorschlag: „Unsere Praesentation ansehen“ / „View our presentation“), im Katalog-Editor aenderbar.
  - Angebot: neues Feld `praesentation` = `de` | `en` | `""`, Standard `de`; Auswahl im Angebots-Editor; wird wie
    Positionen beim Anlegen festgehalten (spaetere Katalogaenderung aendert bestehende Angebote nicht).
  - PDF: klickbarer Link unter den Positionen/Summen (vor dem Fusstext); digitaler Beleg (Belegblatt) zeigt ihn gleich.
  - Mailtext: eine Zeile mit dem Link vor der Grussformel.
  - Auftragsbestaetigung und Rechnung: kein Link (nur Angebot).
- Gate: Tests (Standard Deutsch, Englisch, keiner; Link klickbar im PDF; Mailtext; Altangebote ohne Feld = kein Link
  bzw. Deutsch -- Entscheidung im Test festgehalten); Browsertest Angebots-Editor + Detail auf Rechner, iPad, iPhone 17 Pro.
- Aufwand: klein.

## Nicht-Scope

Keine Uebersetzung des Angebots selbst ins Englische (nur der Link); kein Abruf/Einbetten der Canva-Inhalte; kein
automatischer Versand.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Katalog-Feld), `docs/entscheidungs-register.md`.

## Definition of Done

Neues Angebot enthaelt je nach Auswahl den deutschen oder englischen Canva-Link in PDF, digitalem Beleg und Mailtext.
