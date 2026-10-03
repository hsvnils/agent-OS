# Roadmap: Digitaler Beleg (Belegblatt in LUNA-OS statt Datenliste)
- Status: in Umsetzung
- Stand: 2026-10-04
- Arbeitsbranch: `ai/digitaler-beleg`
- Basiscommit: `df6385c`
- Naechster Schritt: D1-D3 gebaut (2026-10-04); Deploy + Abnahme an echten Belegen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-03)

„Jeder Beleg, den ich mir im System im Browser anschaue, soll auch aussehen wie ein digitaler Beleg. Nicht genau wie
die PDF, aber mit Adresse des Kunden, Positionen und allen wichtigen Beleg-Infos.“

Skizze: `docs/skizzen/digitaler-beleg.html` (Variante A vom CEO gewaehlt).

## Analyse (read-only, 2026-10-03)

- Heute zeigen die Detailansichten (`anDetail`, `abDetail`, `reDetail` in `static/app-v2.js`) Datenzeilen
  (Status, Firma, Ansprechpartner …) und eine Positionstabelle; Kundenanschrift, Absender, Einleitung,
  Zahlungshinweis und Fusszeile gibt es nur im PDF.
- Die PDF-Inhalte entstehen serverseitig aus denselben Bausteinen: `angebote._empfaenger` (Anschrift),
  `anrede_moin`, `_bloecke` (Textbausteine), `pdf_posten` (Positionen je Gruppe), Summen (`summen`/`_summen`),
  Zahlungstext (`zahlungsbedingungen.text`, Rechnung: Ueberweisungs-/Ware-Hinweis), `_firmendaten()` (Briefkopf,
  Steuernummer, Bank; nur auf der NAS).
- Mahnungen haben keine eigene Detailansicht (nur Zeilen in der Rechnung mit PDF-Link).
- Altrechnungen (`RG-…`) haben eine Position (Betrag laut Original) und das Original-PDF.
- Betroffen: 3 Detailansichten + 1 neue (Mahnung), 4 Endpunkte erhalten einen gemeinsamen Block `blatt`.

## Grundsatz

Das Blatt zeigt **dieselben Inhalte wie das PDF**, weil der Server sie mit denselben Funktionen erzeugt (ein Baustein
`core/belegblatt.py` liefert Absender, Empfaengerzeilen, Kopfdaten, Anrede, Einleitung, Positionsgruppen, Summen,
Zahlungshinweis, Fusszeile). Interne Daten (Nachkalkulation, Zeiten, Kennzahlen, Notizen) kommen nie aufs Blatt.

## Etappe D1: Belegblatt-Baustein + Rechnungen

- Status: umgesetzt (2026-10-04) -- `core/belegblatt.py` + `teile()` in Rechnung/Auftrag/Angebot/Mahnung (PDF und Blatt
  nutzen dieselben Texte), Block `blatt` im Rechnungs-Detail, Blatt mit Stempel, Seitenleiste mit Mini-Belegverfolgung,
  Aktionsleiste unten auf iPad/iPhone. Tests `test_belegblatt.py` (Blatt = PDF-Inhalte, keine internen Felder) mit
  Gegenprobe; Browsertest 1300/820/390 px, hell und dunkel.
- Ziel / Scope: `core/belegblatt.py` + Block `blatt` im Rechnungs-Detail; Oberflaeche `belegBlatt()` (weisses
  Papier auch im Dunkelmodus, blau-roter Balken, Anschrift, Kopfdaten, Positionen je Gruppe, Summen, Zahlungshinweis,
  Fusszeile, Status-Stempel OFFEN/BEZAHLT/UEBERFAELLIG/STORNIERT/ENTWURF). Rechner: Blatt links, Seitenleiste rechts
  (Status, Mini-Belegverfolgung, Zahlungen & Mahnungen, Verlauf), Aktionen oben. iPhone: Blatt volle Breite,
  Positionen als kompakte Zeilen, Aktionsleiste unten. Gilt fuer Rechnung, Vorkasse, Schlussrechnung (mit Abzug),
  Storno, Entwurf (Nummer „wird vergeben“) und Altrechnung (mit Link aufs Original-PDF).
- Gate: Tests (Blatt-Inhalte = PDF-Inhalte: Anschrift, Nummer, Summe, Faelligkeit; keine internen Felder);
  Browsertest 1300/820/390 px, Hell und Dunkel.
- Aufwand: mittel.

## Etappe D2: Angebot und Auftragsbestaetigung

- Status: umgesetzt (2026-10-04) -- Angebot und Auftragsbestaetigung als Blatt; Auftrag mit Reitern Beleg/Postings/
  Zeiten/Bericht auf iPad/iPhone, am Rechner interne Bereiche unter dem Blatt („🔒 Intern“).
- Ziel / Scope: Gleiches Blatt fuer Angebot (gueltig bis, Zuschlaege, Rabatt, Zahlungsbedingungen inkl. Vorkasse,
  „So kalkulieren wir“ nur wenn auch im PDF) und Auftragsbestaetigung (Leistungszeitraum, Bezug Angebot,
  Konditionen). Beim Auftrag: auf dem iPhone Reiter „📄 Beleg · 📣 Postings · ⏱ Zeiten · 📝 Bericht“, am Rechner die
  internen Bereiche unter der Seitenleiste (klar als intern markiert). Bearbeiten bleibt im Editor.
- Gate: Tests wie D1; Browsertest 1300/820/390 px.
- Aufwand: mittel.

## Etappe D3: Mahnung als eigenes Blatt + Feinschliff

- Status: umgesetzt (2026-10-04) -- `GET /api/finanzen/mahnungen/<nr>`, Mahnung als Blatt (auch vor LUNA verschickte
  mit Original-PDF), erreichbar aus Rechnung und Belegverfolgung; Primaeraktionen zuerst in der Leiste unten.
- Ziel / Scope: neue Detailansicht je Mahnung (Forderungsaufstellung: offener Betrag, Verzugszinsen mit Zeitraum,
  Pauschale/Mahnkosten, Frist; Senden aus der Ansicht), erreichbar aus Rechnung, Belegverfolgung und Handlungsbedarf.
  Mini-Belegverfolgung oeffnet Belege direkt; einheitliche Aktionsleiste unten auf dem iPhone fuer alle Belege.
- Gate: Tests (Mahnungs-Blatt = Mahnungs-PDF-Zahlen); Browsertest 1300/820/390 px.
- Aufwand: klein bis mittel.

## Nicht-Scope

Keine Aenderung an PDFs, Nummern, Buchungen oder gespeicherten Belegen; kein neuer Editor; Eingangs-/Eigenbelege
behalten ihre Ansicht (Beleg-Vorschau des Originals).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Block `blatt` in den
Detail-Endpunkten), `docs/entscheidungs-register.md` (Variante A).

## CEO-Entscheidungen (2026-10-03)

1. Variante A: am Rechner Blatt links + Seitenleiste rechts, auf dem iPhone Blatt volle Breite + Aktionsleiste unten,
   Auftrag mit Reitern.

## Definition of Done

D1-D3 verifiziert (Rechner, iPad, iPhone; Hell/Dunkel) und vom CEO an echten Belegen abgenommen
(RE-2026-0003, AB-2026-0002, RG-11052026 mit Mahnungen).
