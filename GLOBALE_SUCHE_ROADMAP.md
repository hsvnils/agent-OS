# Roadmap: Globale Suche in LUNA-OS

- Status: in Umsetzung
- Stand: 2026-10-06
- Arbeitsbranch: `ai/suche-und-sortierung`
- Basiscommit: `e3c8e23`
- Naechster Schritt: G1 gebaut (2026-10-06) -- CEO-Go fuer Merge, Push und Deploy; G2 nur bei Bedarf.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-06)

„Eine globale Textsuche, die die Ergebnisse in Kategorien aufteilt wie Auftraege, Rechnungen, Ausgaben aus Finanzen usw.“

## Analyse (read-only, 2026-10-06)

- Heute gibt es nur Suchen je Bereich (z. B. Kunden: Name, Nummer, Ort, Ansprechpartner); keine bereichsuebergreifende Suche.
- Alle Geschaeftsdaten liegen in der Buchhaltungs-Kette auf der NAS (Firmen, Angebote, Auftraege, Rechnungen, Mahnungen,
  Eingangs-/Eigenbelege, Content-Plan, Konzept-Mappen, Firmenakte, Vorstellungen) -- durchsuchbar ohne neuen Dienst.
- Rechte: Team-Nutzer sehen nur ihre Module; die Suche muss das einhalten (z. B. Finanzen nur mit Modul finanzen).

## Etappe G1: Suche ueber alle Geschaeftsdaten

- Status: umgesetzt
- Ziel / Scope: Lupe 🔎 oben in der Leiste (Rechner: auch Taste „/“), Suchfeld mit Ergebnissen beim Tippen, gruppiert nach
  **Kunden & Interessenten, Angebote, Auftraege, Rechnungen, Mahnungen, Ausgaben (Belege), Eigenbelege, Content-Plan,
  Konzepte, Akte & Mails** -- je Gruppe Anzahl + die besten Treffer, Klick oeffnet den Beleg/die Firma. Gesucht wird in
  Nummer, Firmenname, Ansprechpartner, Titel, Positionen, Lieferant, Zweck/Notiz, Betrag („1.600“, „1600,00“) und Datum
  („03.10.“, „Oktober 2026“). Ohne Umlaut-/Gross-Klein-Probleme („Muenchen“ = „München“). Nur Bereiche, die der Nutzer sehen darf.
- Gate: Tests (Treffer je Kategorie, Betrag/Datum, Umlaute, Rechte, Gegenprobe); Browsertest Rechner/iPad/iPhone 17 Pro;
  Antwortzeit unter 1 s bei heutigem Datenbestand.
- Aufwand: mittel.
- Umsetzung (2026-10-06): `core/suche.py` (je Datensatz normalisierter Suchtext inkl. Betraegen „1.600,00/1600“ und Daten
  „03.10.2026/oktober 2026“; alle Suchwoerter muessen vorkommen; Kategorien nur bei Recht auf die App; je Gruppe Anzahl + 8 beste
  Treffer, exakte Nummer zuerst, sonst neueste), `GET /api/suche?q=`. Oberflaeche: 🔎 in der Kopfleiste und Taste „/“, Suche beim
  Tippen, Enter oeffnet den ersten Treffer, Klick oeffnet Firma/Beleg/Content-Plan-Tag/Konzept.

## Etappe G2: Inhalte durchsuchen (optional)

- Status: geplant
- Ziel / Scope: zusaetzlich der Text in Belegen (PDF-/Foto-Text, schon fuer die Erkennung gelesen) und in archivierten Mails
  (.eml der Akte und der Kundenantworten), mit Textausschnitt um den Treffer.
- Gate: Tests; Antwortzeit (ggf. Zwischenspeicher/Index auf der NAS).
- Aufwand: mittel.

## Nicht-Scope

Keine Suche im Internet, keine KI-Antworten in der Suche (dafuer gibt es „LUNA fragen“), keine Aenderung von Daten.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`.

## Definition of Done

Ein Suchfeld findet alles Geschaeftliche, nach Kategorien geordnet, auf Rechner, iPad und iPhone.
