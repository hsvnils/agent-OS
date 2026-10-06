# Roadmap: Wiederkehrender Content und Vorstellungs-Mails aus LUNA-OS

- Status: geplant
- Stand: 2026-10-06
- Arbeitsbranch: `ai/serien-und-akquise`
- Basiscommit: `ba6465b`
- Naechster Schritt: CEO-Go fuer S1, V1 und V2 abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-06)

1. „Wiederkehrenden Content im Content-Plan anlegbar machen.“
2. „Mails aus LUNA-OS versenden, um bspw. Unternehmen per Mail anzuschreiben und sich vorzustellen -- mit vorgeschriebenen
   Textbausteinen, und LUNA kennt die Mails dann schon.“ Entscheidungen: **Firma wird beim Senden angelegt** (als
   Interessent), **zur Einwilligung nur ein Hinweis** (kein Pflichtfeld; Risiko traegt der CEO, siehe Recht).

## Analyse (read-only, 2026-10-06)

- Content-Plan (`core/contentplan.py`): Einzel-Eintraege `plan_eintrag` mit Datum; keine Wiederholung.
- Versand: alle Kundenmails ueber All-Inkl (`governance/allinkl_mail.py`, `KUNDENVERSAND=allinkl`); Antworten erkennt der
  15-min-Poll ueber die Kennung im Versand-Ereignis (`core/mail_antworten.py`) -- jede neue Mailart, die ihre Kennung in
  der Kette speichert, wird automatisch mit erkannt.
- Textbausteine (`core/textbausteine.py`): 7 Belegarten, Signatur; Vorstellungs-Mail fehlt als Art.
- Firmen (`core/kunden.py`): Typen kunde/lieferant/partner; kein Interessent.
- Recht: Werbung per E-Mail ohne vorherige ausdrueckliche Einwilligung ist eine unzumutbare Belaestigung (§ 7 Abs. 2 UWG),
  nach der Rechtsprechung auch gegenueber Unternehmen -- reine Kaltakquise ist abmahnfaehig. Zulaessig u. a. nach einer
  Anfrage/Einwilligung der Firma oder als Antwort auf deren Kontakt. CEO-Entscheidung: nur Hinweis im Dialog; der Anlass
  kann optional vermerkt werden (Nachweis). Keine Rechtsberatung -- verbindlich klaert das die Anwaeltin.

## Etappe S1: Wiederkehrender Content

- Status: geplant
- Ziel / Scope: Eintrag mit Wiederholung **woechentlich, alle 2 Wochen, monatlich (gleicher Tag)** und optionalem Enddatum
  (sonst offen); im Kalender erscheinen die Termine automatisch (berechnet, nicht vorab gespeichert); jeder Termin hat eigenen
  Status (Idee -> Online) und laesst sich einzeln aendern oder auslassen; „ganze Serie aendern/beenden“ wirkt ab dem
  gewaehlten Termin, Vergangenes bleibt. Ereignisse `plan_serie`, `plan_serie_termin`, `plan_serie_ende` in der Kette.
- Gate: Tests (Termine im Zeitraum, Monatsende z. B. 31., Ausnahme/Einzelaenderung, Serienende, Gegenprobe); Browsertest
  Rechner/iPad/iPhone 17 Pro.
- Aufwand: mittel.

## Etappe V1: Vorstellungs-Mail aus LUNA-OS

- Status: geplant
- Ziel / Scope: Knopf „✉️ Neue Mail“ (Kunden und Firmenakte): Empfaenger = Firma aus der Liste **oder** Name + Mailadresse
  (+ optional Ansprechpartner) eintippen; neue Textbaustein-Art „Vorstellung“ (mehrere Vorlagen, mit Signatur, in den
  Einstellungen bearbeitbar), Text anpassbar, optional Anhang (z. B. Praesentation/Canva-Link aus den Vorlagen); Hinweis zur
  Einwilligung im Dialog + optionaler Anlass. Beim Senden: neue Firma als **Interessent** anlegen (Dubletten-Pruefung ueber
  Name/Domain), Versand ueber luna@hanserautisch.de, Mail (.eml) in der Firmenakte, Kennung in der Kette -> Antworten erkennt
  und meldet LUNA wie bei Belegen. Senden nur per Klick (Oeffentlichkeit = CEO-Tor).
- Gate: Tests (Firma neu/vorhanden, Dublette, Kennung + Antwort-Zuordnung, kein Versand ohne Bestaetigung, Gegenprobe);
  Browsertest; ein echter Testversand an eine CEO-Adresse.
- Aufwand: mittel bis gross.

## Etappe V2: Nachfassen und Ueberblick

- Status: geplant
- Ziel / Scope: Liste „Vorstellungen“ (wer angeschrieben, wann, Antwort ja/nein); Erinnerung im Handlungsbedarf, wenn nach
  N Tagen (Standard 7) keine Antwort kam; „Nachfassen …“ mit eigener Vorlage; Interessent -> Kunde, sobald ein Angebot
  angenommen wird.
- Gate: Tests; Browsertest.
- Aufwand: klein bis mittel.

## Nicht-Scope

Kein Massenversand/Newsletter, keine gekauften Adresslisten, keine automatische Mail ohne Klick, keine Web-Suche nach
Firmenadressen in dieser Roadmap.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`,
`docs/bekannte-fehler.md`.

## Definition of Done

Wiederkehrende Inhalte stehen als Serie im Content-Plan; Vorstellungs-Mails gehen in einem Schritt aus LUNA-OS raus, die
Firma steht danach als Interessent mit Mail in der Akte, und Antworten werden erkannt und gemeldet.
