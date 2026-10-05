# Roadmap: Konzept-Mappe je Vorgang (Briefing, Ideen, Skript, Shotlist, Drehplan, Kunden-Freigabe)
- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/plan-konzept-vertrag` (Plan); Umsetzung auf eigenem Branch
- Basiscommit: `6636d02`
- Naechster Schritt: CEO-Go fuer K1-K3 abwarten (Entscheidungen 2026-10-05 liegen vor); Skizze `docs/skizzen/konzept-und-vertrag.html`.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Ab der ersten Anlage (Angebot) eine Moeglichkeit, Content-Ideen, Skript und Co. mit abzuspeichern -- durch die
Folgebelege mitgeschliffen. Ein Bereich fuer Ideen zum Content, Skript, Shotlist usw., auch als PDF exportierbar.“

## Analyse (read-only, 2026-10-05)

- Es gibt keinen Ort fuer projektbezogene Content-Planung: die Content-Pipeline (K3, Supabase Trends/Ideen/Drafts) ist
  fuer **eigene** Inhalte; „Vorgegebenes Skript“ existiert nur als Katalog-Zuschlag (+20 %).
- Belege einer Kundenkette sind verbunden (Angebot -> Auftrag -> Rechnung ..., `core/belegverfolgung.py`); Postings
  je Position existieren ab dem Auftrag (`core/postings.py`, IDs `<AB>-P<Pos>-<Nr>`).
- Dateien liegen auftragsbezogen unter `lieferungen/` auf der NAS (nicht im Git, kein Backup -- CEO 2026-10-01).
- PDF im Hanserautisch-Layout gibt es (`beleg_pdf.hanserautisch_pdf`, Projektbericht `core/projektbericht.py`).

## Grundsatz (CEO-Entscheidung 1)

**Eine Mappe je Vorgang**, nicht je Beleg: Sie entsteht beim Angebot (oder beim direkt angelegten Auftrag) und ist in
Auftrag, Rechnung und Bericht **derselbe Stand** -- nichts wird kopiert. Der Vorgang ist die Kette der
Belegverfolgung; seine Kennung ist der erste Beleg (z. B. `AN-2026-0003`). Wird aus dem Angebot ein Auftrag, haengt die
Mappe automatisch auch dort. Aenderungen stehen mit Verlauf in der Hash-Kette (`konzept_*`-Ereignisse).

## Etappe K1: Mappe + Briefing + Ideen

- Status: geplant
- Ziel / Scope: `core/konzept.py`; Bereich „🎬 Konzept“ in Angebot und Auftrag (iPhone: eigener Reiter), Hinweis mit
  Link in Rechnung/Bericht. **Briefing:** Ziel, Zielgruppe, Kernbotschaft, Tonalitaet, Do's & Don'ts, Pflichtangaben
  (Kennzeichnung „Werbung“, Link, Rabattcode, Markierungen), Ansprechpartner fuer Freigaben. **Ideen:** Liste mit Titel,
  Beschreibung, Format, Status (Idee / ausgewaehlt / verworfen), Moodboard-Bilder (NAS, wie Lieferungen).
- Gate: Tests (eine Mappe je Vorgang, Angebot -> Auftrag zeigt dieselbe Mappe, Verlauf bei Aenderung, fremde Vorgaenge
  getrennt); Browsertest 1300/820/402 px (iPhone 17 Pro, Safe Areas).
- Aufwand: mittel.

## Etappe K2: Skript je Posting + Shotlist + Drehplan

- Status: geplant
- Ziel / Scope: **Skript** je Leistung -- vor dem Auftrag je Angebotsposition, ab dem Auftrag je Posting (Reel 1,
  Reel 2 ...; die Skripte wandern mit): Hook (erste 3 Sek.), Text/Voice-over, Einblendungen, Musik-Hinweis, CTA,
  Laenge. **Shotlist:** Szenen mit Einstellung, Ort, Personen/Requisite, Dauer, Zuordnung zum Skript; beim Dreh auf
  dem iPhone als **Drehmodus** (grosse Haken, bleibt offline-tauglich lesbar). **Drehplan:** Termin(e), Ort,
  Ansprechpartner vor Ort, Mitbringen-Liste; Termin optional in den Kalender (Google, wie Angebots-Erinnerungen).
- Gate: Tests (Skript wandert von Position zu Posting, Shotlist abhaken mit Verlauf); Browsertest inkl. Drehmodus
  auf 402 px.
- Aufwand: mittel.

## Etappe K3: PDF-Export + Kunden-Freigabe

- Status: geplant
- Ziel / Scope: PDF im Hanserautisch-Layout mit Auswahl: **„Konzept fuer den Kunden“** (Briefing, ausgewaehlte Ideen,
  Skripte) oder **„Drehliste intern“** (Shotlist + Drehplan). **Freigabe:** Versand aus LUNAs Konto nur nach CEO-Klick
  (Aussenkommunikation = CEO-Tor), Status Entwurf / beim Kunden / freigegeben (mit Datum) / Aenderungswunsch;
  gesendete Fassung unveraenderlich in der Firmenakte, neue Version bei Aenderung; Handlungsbedarf „Freigabe
  ausstehend seit 3 Tagen“ und „Dreh morgen -- Shotlist pruefen“.
- Gate: Tests (Freigabe-Status, eingefrorene Fassung, Versand nur mit Bestaetigung); PDF-Pruefung; Browsertest.
- Aufwand: mittel.

## Etappe K4 (eigener Vorschlag): LUNA hilft beim Konzept

- Status: geplant (Vorschlag Claude Code, eigenes Go noetig)
- Ziel / Scope: aus Briefing + Katalog-Format Ideen- und Skript-Entwuerfe vorschlagen (Gemini, wie der Chat), der
  CEO waehlt aus und passt an; Kennzahlen frueherer Postings (P1-P4) als Hinweis „was lief gut“.
- Gate: Datenschutz-Eintrag (Briefing des Kunden geht an Google) -- CEO-Entscheidung.
- Aufwand: klein bis mittel.

## Nicht-Scope

Kein Video-Schnitt/Upload in der Mappe (dafuer Lieferungen und Cutter); keine automatische Veroeffentlichung; keine
Aenderung an Belegen, Nummern oder PDFs der Belege.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Ereignisse, Endpunkte, NAS-Ordner,
Kalender, Mail), `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`.

## CEO-Entscheidungen (2026-10-05)

1. Eine Mappe **je Vorgang** (ab Angebot bzw. direkt angelegtem Auftrag, in allen Folgebelegen derselbe Stand).
2. Bereiche: **Briefing, Ideen + Skript je Posting, Shotlist + Drehplan, Kunden-Freigabe**.

## Definition of Done

K1-K3 verifiziert (Rechner, iPad, iPhone 17 Pro) und vom CEO an einem echten Vorgang abgenommen (Konzept erstellt,
als PDF freigegeben, Dreh mit Shotlist auf dem iPhone); K4 nach eigenem Go.
