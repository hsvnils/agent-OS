# Roadmap: Schutz gegen Prompt Injection ausbauen und verfeinern

- Status: geplant
- Stand: 2026-10-19
- Arbeitsbranch: `ai/kundenordner-injektion`
- Basiscommit: `b9b9944`
- Naechster Schritt: CEO-Go fuer I1-I4 abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-19)

„Schutz gegen Prompt Injection ausbauen und verfeinern.“

## Analyse (read-only, 2026-10-19)

- Vorhanden (Phase 23, `core/input_guard.py`, 150 Zeilen): regelbasierte Muster (Anweisung ueberschreiben, Rollenwechsel,
  System-Prompt abfragen, Ablehnung verbieten, Daten ausleiten, Werkzeug-Schmuggel, versteckte HTML-Kommentare,
  Jailbreak-Personas, unsichtbare Zeichen), PII-Erkennung, Markierung „nicht vertrauenswuerdig“.
- **Angewendet nur an vier Stellen:** Instagram-DMs (`core/crm.py`), CRM-Mails (`core/crm_mail.py`), Web-Recherche
  (`governance/web_research.py`), Skill-Gate.
- **Nicht geschuetzt (belegt in `core/hoa_tools.py`):** die Chat-Werkzeuge `mail_lesen`, `mail_suchen`, `posteingang`,
  `drive_lesen`, `tabelle_lesen` geben Fremdtext ungeprueft an das Modell; ebenso Texte aus Eingangsbelegen (PDF/Mail ->
  Gemini-Auslesen), Firmenakte, Kundenantworten auf Belege, Content-Feed (Trends aus dem Netz), Backoffice-Auftraege mit
  Fremdtext.
- Was schon hilft: Senden/Aendern ist hinter `bestaetigt=true` bzw. Klick des CEO; Investment-Trades sind gesperrt.
  Es fehlt aber eine Sperre, die greift, **nachdem** Fremdtext gelesen wurde.

## Etappe I1: Abdeckung -- jeder Fremdtext wird markiert

- Status: geplant
- Ziel / Scope: zentrale Stelle im Werkzeug-Aufruf: Ergebnisse aller Werkzeuge mit Fremdinhalt (Mail, Drive, Tabellen,
  Recherche, Akte, Belegtexte, Kundenantworten, Content-Feed) laufen durch `input_guard` und kommen als klar abgegrenzter
  „nicht vertrauenswuerdiger Inhalt“ beim Modell an; Liste der Fremdinhalt-Werkzeuge im Code mit Test, dass keines fehlt.
- Gate: Tests je Quelle (Injection im Mailtext wird markiert), Gegenprobe; Token-Budget der Werkzeugauswahl bleibt eingehalten.
- Aufwand: mittel.

## Etappe I2: Erkennung verfeinern

- Status: geplant
- Ziel / Scope: Text vor dem Pruefen normalisieren (Unicode-Lookalikes, Leerzeichen/Punkte zwischen Buchstaben, Leetspeak,
  Gross-/Kleinschreibung), neue Muster: Rollen-Markierungen im Text („assistant:“, „system:“), Markdown-Bilder/Links, die
  Daten in eine Adresse schreiben, versteckter Text in HTML (unsichtbar, weiss auf weiss, winzig), Base64-Bloecke mit
  Anweisungen, Aufforderungen an LUNA-Werkzeuge mit deren Namen. **Testkorpus** mit boesartigen und harmlosen Beispielen
  (deutsch/englisch) -- Fehlalarm-Quote wird gemessen und darf nicht steigen.
- Gate: Korpus-Test (Erkennungsrate rauf, Fehlalarme <= heute), Gegenprobe.
- Aufwand: mittel.

## Etappe I3: Handlungs-Sperre nach Fremdtext

- Status: geplant
- Ziel / Scope: Hat LUNA im laufenden Gespraechszug Fremdtext mit Verdacht gelesen, sind Werkzeuge mit Aussenwirkung
  (Mail senden, Termine, Dateien/Tabellen schreiben, Freigaben, Antraege umsetzen, Loeschen) fuer diesen Zug gesperrt bzw.
  nur nach ausdruecklicher Rueckfrage beim CEO; ausserdem: Antworten mit Links zu fremden Adressen, die Daten aus dem
  Gespraech enthalten, werden blockiert (Datenabfluss ueber Links).
- Gate: Tests (Sperre greift nur nach Verdacht, normaler Ablauf unberuehrt, Rueckfrage), Gegenprobe.
- Aufwand: mittel.

## Etappe I4: Ueberwachung und Angriffstests

- Status: geplant
- Ziel / Scope: jeder Verdacht wird protokolliert (Quelle, Muster -- ohne Inhalt) und steht im naechtlichen CISO-Bericht
  und im Leistungsbericht; Telegram-Hinweis bei Verdacht in Mails/Belegen. Eine **Angriffs-Testreihe** (typische Angriffe
  gegen Mail, Drive, Web, Belege) laeuft mit der Testsuite und schlaegt an, wenn eine Aenderung den Schutz schwaecht.
- Gate: Tests; Browser (Kennzahl im Leistungsbericht).
- Aufwand: klein bis mittel.

## Nicht-Scope

Kein zusaetzliches KI-Modell als Waechter (kostet und kann selbst getaeuscht werden) -- spaeter optional ueber das lokale
Modell; keine Aenderung an Charten.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md`,
`governance/zugriffs-policy.md` (CISO).

## Definition of Done

Jeder Fremdtext kommt markiert beim Modell an, die Erkennung ist breiter bei gleichbleibenden Fehlalarmen, nach einem
Verdacht kann LUNA nichts mit Aussenwirkung tun, ohne dich zu fragen, und jeder Verdacht ist im CISO-Bericht sichtbar.
