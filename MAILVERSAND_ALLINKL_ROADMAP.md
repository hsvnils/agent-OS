# Roadmap: Kundenmails ueber All-Inkl (luna-hoa@hanserautisch.de) statt Gmail
- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/plan-contentplan-allinkl`
- Basiscommit: `655f82a`
- Naechster Schritt: CEO-Go fuer M1 abwarten; vorher legt der CEO das Postfach-Passwort selbst in `orchestrator/.env` an
  (CEO-Tor: neuer Zugang).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Kann LUNA ausgehende Mails auch ueber eine meiner All-Inkl-Adressen versenden?“ -- **Ja**, technisch ueber den Mailserver
von All-Inkl (SMTP zum Senden, IMAP zum Lesen). Entscheidungen: **statt Gmail fuer Kundenmails**, Absender
**luna-hoa@hanserautisch.de**.

## Analyse (read-only, 2026-10-05)

- Heute gehen alle Kundenmails ueber LUNAs Gmail-Konto (`governance/google_workspace.py` `mail_senden`): Angebot,
  Auftragsbestaetigung, Rechnung, Mahnung, Projektbericht, Konzept; danach Original-Mail (.eml) archiviert, bei Angeboten
  Kundenantworten im 15-min-Poll ueber den Gmail-Verlauf erkannt (`angebote.antworten_pruefen`, Thread-ID).
- Gmail bleibt fuer LUNAs eigene Dinge (Kalender, Drive, Beleg-Eingang, Mailsuche) -- nur der **Kundenversand** wechselt.
- Technik ohne neue Bibliothek: Python `smtplib`/`imaplib` (Standard); Server-Daten von All-Inkl (Host des KAS-Servers,
  SMTP 465/587, IMAP 993). SPF/DKIM fuer die eigene Domain kommen von All-Inkl.
- Schutz: Zugangsdaten nur in `orchestrator/.env` (NAS + MACO470), nie im Git, nie ausgegeben; Eintrag in der
  Zugriffs-Policy (CISO). All-Inkl ist schon Anbieter des CEO -- kein neuer Datenempfaenger.

## Etappe M1: Versand ueber All-Inkl

- Status: geplant
- Ziel / Scope: neuer Versandweg „All-Inkl“ mit dem gleichen Aufruf wie Gmail (Empfaenger, Betreff, Text, Anhaenge);
  Absender „Hanserautisch – LUNA <luna-hoa@hanserautisch.de>“; die gesendete Mail wird per IMAP in „Gesendet“ abgelegt und
  wie bisher als .eml archiviert; Schalter in der `.env` (Kundenversand = allinkl | gmail), Rueckfall auf Gmail nur
  per Schalter (nie automatisch, damit kein Kunde Mails von zwei Absendern bekommt). Versanddialoge zeigen den Absender.
- Gate: Tests mit Attrappe (kein echter Versand); **ein echter Testversand an eine CEO-Adresse** nach Freigabe; CISO-Eintrag.
- Aufwand: mittel.

## Etappe M2: Antworten der Kunden

- Status: geplant
- Ziel / Scope: Kundenantworten im Postfach luna-hoa@ per IMAP erkennen (Zuordnung ueber Message-ID/In-Reply-To bzw.
  Belegnummer im Betreff), im Verlauf des Belegs anzeigen, archivieren und per Telegram melden -- wie heute bei Gmail.
- Gate: Tests (Zuordnung, keine Doppelmeldung); echter Test mit einer Antwort des CEO.
- Aufwand: mittel.

## Etappe M3: Umschalten und Beobachten

- Status: geplant
- Ziel / Scope: Kundenversand auf All-Inkl umstellen, eine Woche beobachten (Zustellung, Spam-Ordner beim Empfaenger,
  Antworten), Erkenntnisse in `docs/bekannte-fehler.md`.
- Gate: CEO-Bestaetigung.
- Aufwand: klein.

## Nicht-Scope

Kein Wechsel von Kalender/Drive/Beleg-Eingang weg von Google; kein Massenversand/Newsletter; Passwort, DNS und Postfach-
Einstellungen bei All-Inkl macht der CEO selbst.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (SMTP/IMAP All-Inkl),
`governance/zugriffs-policy.md` (CISO), `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`.

## Definition of Done

Alle Kundenmails gehen von luna-hoa@hanserautisch.de raus, liegen dort in „Gesendet“ und in der Firmenakte, Antworten werden
erkannt und gemeldet.
