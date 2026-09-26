# Roadmap: Werkzeugauswahl — nur passende Werkzeuge je Nachricht

- Status: in Umsetzung
- Stand: 2026-09-26
- Arbeitsbranch: `ai/werkzeugauswahl`
- Basiscommit: `3523a38`
- Naechster Schritt: CEO-Go fuer Etappe 2 (Nachladen + Verdrahtung hinter Schalter `WERKZEUGAUSWAHL`, Probelauf mit
  Gemini).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel

LUNA schickt dem Modell nicht mehr bei jeder Nachricht alle 97 Werkzeuge (~12.000 Token), sondern ein kleines
Kern-Set plus die Gruppen, die zur Nachricht passen — und kann fehlende Werkzeuge jederzeit nachladen.
Wirkung: Prompt von ~13.600 auf voraussichtlich 3.000–5.000 Token. Damit werden lokale Modelle auf dem MACO470
ueberhaupt erst tragfaehig (weniger Speicher fuer den Kontext, schnelleres Einlesen, weniger Verwirrung durch
irrelevante Werkzeuge), und auch Gemini wird schneller und stoesst seltener an Limits.

## Register und bekannte Fehler (B3)

- Register: „Gemini-Gratis als Standard fuer den Chat" (BESCHLOSSEN 2026-09-26); `qwen3:30b-a3b` auf dem MACO470
  VERWORFEN, `qwen3:14b` ZURUECKGESTELLT — beide Befunde nennen die grosse Werkzeugliste als Hauptlast.
- Bekannte Fehler: BF-05 (Gemini-Rate-Limit), BF-17 (stilles Kuerzen bei zu kleinem Kontext), BF-22 (RAM),
  BF-23 (Zeichensalat beim 14B).
- Kein Vorbild im Code: `core/routing.py` enthaelt nur Schluesselwoerter fuer CEO-Tore und die Fachagenten-Wahl.

## Analyse (Belege, gemessen 2026-09-26)

- `tool_specs()` liefert **97 Werkzeuge, 42.206 Zeichen, ~12.058 Token**; System-Prompt ~1.600 Token. Groesste:
  `paper_order_freigabe`, `xmind_bearbeiten`, `rechner_aktion` (je ~1.300 Zeichen).
- Die Namen bilden klare Themengruppen (Praefixe): Antraege (10), Investment/Paper/Insider (12), CRM/Instagram/Social
  (9), Office (Mail/Kalender/Termin/Drive/Tabelle/Posteingang, 16), Recherche/Watch/Innovation (9), Rechner/
  Bildschirm/Apps/XMind/Obsidian (8), System/Autonomie/Sicherheit/Skills (10), Finanzen/Kosten/Budget (5),
  Gedaechtnis (Brain/Erfahrung/Wissensstand/Notiz, 6), Rest (Delegation, Meldungen, Lagebild, Visualisierung ...).
- Es wird **nicht protokolliert**, welche Werkzeuge LUNA tatsaechlich nutzt -> fuer die Auswahl gibt es heute keine
  Nutzungsdaten; ein Testkatalog ersetzt sie zunaechst, ein Nutzungsprotokoll liefert sie kuenftig.
- Einstieg im Code: `HoaConversation` uebergibt `self.tools` (alle) an `router.create`; `run_tool` fuehrt jedes
  Werkzeug per Name aus — die Auswahl betrifft nur, was das Modell **sieht**, nicht, was ausgefuehrt werden darf.

## Scope

Werkzeug-Gruppen + Kern-Set, deterministische Vorauswahl (Schluesselwoerter, ohne LLM-Aufruf), Nachladen
(Meta-Werkzeug + automatisch bei unbekanntem Werkzeug), Nutzungsprotokoll, Schalter per `.env`, Re-Test lokaler Modelle.

## Nicht-Scope

- Aenderung einzelner Werkzeuge oder ihrer Rechte/CEO-Tore (Auswahl ≠ Berechtigung)
- Fachagenten-Pfad (`FallbackBackend`, ohne Werkzeuge), Sprachkanal, Execution
- LLM-basierte Vorauswahl (kostet je Nachricht einen Aufruf) — hoechstens spaeter, falls der Testkatalog es verlangt
- Schutzbereiche laut `governance/roadmap-workflow.md` B4

## Etappen

### Etappe 1: Testkatalog, Gruppen, Vorauswahl (ohne Wirkung)

- Status: **verifiziert** (2026-09-26, Branch `ai/werkzeugauswahl`) — `orchestrator/core/werkzeugauswahl.py`: Kern-Set
  (12 Werkzeuge, ~1.500 Token) + 11 Gruppen (350-1.650 Token), alle 97 Werkzeuge genau einmal zugeordnet (Test).
  Testkatalog 64 Nachrichten: **100 % Treffer, im Mittel 4.412 Token** (min 3.114, max 6.237) statt ~13.600.
  Ehrlicher Hinweis: Der Katalog ist „im eigenen Saft" — erster Lauf 98,4 % (63/64), danach ein Stichwort ergaenzt
  (`ticket`). Echte Trefferquote zeigt erst das Nutzungsprotokoll ab Etappe 2/3. Gegenprobe: ohne Kalender-Stichwoerter
  91 % -> Test rot. Suite 825 passed / 0 failed.
- Ziel / Scope: `core/werkzeugauswahl.py` mit Gruppen-Zuordnung aller 97 Werkzeuge, einem Kern-Set (immer dabei)
  und der Vorauswahl aus der CEO-Nachricht (+ bereits im Gespraech genutzte Gruppen bleiben geladen). Ein
  **Testkatalog** mit >= 50 typischen CEO-Nachrichten und erwarteten Werkzeugen (abgeleitet aus System-Prompt und
  Werkzeug-Beschreibungen). Ein Test stellt sicher, dass jedes Werkzeug genau einer Gruppe zugeordnet ist (neue
  Werkzeuge ohne Gruppe -> Test rot).
- Gate: Trefferquote im Testkatalog >= 95 % (erwartetes Werkzeug in der Auswahl), mittlere Groesse der Auswahl
  <= 5.000 Token; Tests gruen.
- Verifikation: `pytest orchestrator/tests/test_werkzeugauswahl.py -q` -> erwartet `0 failed`; Bericht-Ausgabe:
  Trefferquote und Token-Groesse je Katalogeintrag.
- Dry-Run: entfaellt (keine produktive Wirkung).
- Risiko / Rueckweg: keins (nicht verdrahtet); `git revert`.
- Abhaengig von: – · Aufwand: mittel · Risiko: niedrig

### Etappe 2: Nachladen + Verdrahtung hinter Schalter

- Status: geplant
- Ziel / Scope: Meta-Werkzeug `werkzeuge_laden(gruppe)` im Kern-Set (Beschreibung listet alle Gruppen in einer Zeile);
  ruft das Modell ein nicht mitgeschicktes Werkzeug, wird es trotzdem ausgefuehrt und seine Gruppe fuer den weiteren
  Verlauf nachgeladen. Verdrahtung in `HoaConversation` hinter `WERKZEUGAUSWAHL=an` (Standard aus).
  Nutzungsprotokoll: welches Werkzeug wurde gerufen, war es vorausgewaehlt oder nachgeladen (Aktivitaetsprotokoll,
  Kategorie `werkzeug`).
- Gate: Tests gruen (Schalter aus = identisches Verhalten; Nachladen; unbekanntes Werkzeug); Probelauf mit Gemini ueber
  den Testkatalog: jede Nachricht fuehrt zum erwarteten Werkzeug.
- Verifikation: Probelauf-Skript auf dem MACO470 mit Test-Ablagen -> erwartet >= 95 % richtige Werkzeuge, mittlerer
  Prompt <= 5.000 Token (aus `usage`).
- Dry-Run: Probelauf ohne Live-Daten; `deploy/sync-to-nas.sh --dry-run` vor dem Deploy.
- Risiko / Rueckweg: Werkzeug fehlt in der Auswahl -> Nachladen faengt es ab; Schalter aus.
- Abhaengig von: 1 · Aufwand: mittel · Risiko: niedrig
- Freigaben: Etappe, Merge, Deploy + Neustart (CEO).

### Etappe 3: Live mit Gemini

- Status: geplant
- Ziel / Scope: `WERKZEUGAUSWAHL=an` in der NAS-`.env`.
- Gate: 7 Tage ohne Beschwerde „LUNA konnte X nicht"; Kostenlog: mittlere `in`-Token je Chat-Aufruf deutlich unter
  heute (~13.000-15.000).
- Verifikation: `finance/kosten-log.jsonl` (quelle `chat`) vor/nach vergleichen; Nutzungsprotokoll: Anteil
  „nachgeladen" < 10 %.
- Risiko / Rueckweg: Schalter aus + Neustart.
- Abhaengig von: 2 · Aufwand: klein · Risiko: niedrig

### Etappe 4: Re-Test lokales Modell (zurueck zu `LOKALES_LLM_ROADMAP.md`)

- Status: geplant
- Ziel / Scope: `qwen3:14b` (und ggf. `qwen3:30b-a3b`) mit kleinem Prompt erneut messen: Speicher unter Last ueber
  >= 15 min, Antwortzeiten, Qualitaet (kein Zeichensalat, BF-23), plus Plausibilitaetsfilter fuer lokale Antworten
  (Wiederholungen/Zeichensalat -> naechster Anbieter). Bei Bestehen: `LOCAL_LLM_CHAT` wieder aktivieren.
- Gate: 8-Nachrichten-Test >= 90 % lokal und fehlerfrei, Windows dauerhaft >= 3 GB verfuegbar.
- Abhaengig von: 3 · Aufwand: mittel · Risiko: mittel
- Freigaben: Etappe; Windows-Einstellungen (CEO); `.env` + Neustart.

## Reihenfolge

1 -> 2 -> 3 -> 4. Etappe 1 ist rein lokal und risikolos; der Testkatalog ist der Massstab fuer alles Weitere.

## Kosten

Einmalig 0 EUR, laufend 0 EUR. Wirkung: weniger Token je Chat-Aufruf bei allen Anbietern.

## Dokumentationspflichten

`projekt_changelog.md` (jede Etappe), Etappen-Status + `Naechster Schritt` hier, `ROADMAP.md` (Verzeichnis),
`docs/datenfluesse.md` (Nutzungsprotokoll im Aktivitaetsprotokoll), `docs/bekannte-fehler.md` (BF-05/BF-23 nach Etappe
4), `docs/entscheidungs-register.md` (Auswahlverfahren), `LOKALES_LLM_ROADMAP.md` (Fortsetzung).

## Definition of Done

Etappen 1–3 `verifiziert`: LUNA schickt im Mittel <= 5.000 Token Werkzeuge/Prompt, ohne dass Aufgaben scheitern.
Etappe 4 entscheidet, ob das lokale Modell zurueckkommt. Abnahme durch den CEO.
