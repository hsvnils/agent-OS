# Roadmap: Kundenmails ueber All-Inkl (luna@hanserautisch.de) statt Gmail
- Status: in Umsetzung
- Stand: 2026-10-05
- Arbeitsbranch: `ai/mail-allinkl`
- Basiscommit: `3a08276`
- Naechster Schritt: M2 live -- echter Test: Testmail aus LUNA-OS an den CEO, der CEO antwortet (auch von einer eigenen
  Adresse), Telegram-Meldung „Antwort auf die LUNA-Testmail“ innerhalb von 15 Minuten; M3 (Beobachten) laeuft weiter.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Kann LUNA ausgehende Mails auch ueber eine meiner All-Inkl-Adressen versenden?“ -- **Ja**, technisch ueber den Mailserver
von All-Inkl (SMTP zum Senden, IMAP zum Lesen). Entscheidungen: **statt Gmail fuer Kundenmails**, Absender
**luna@hanserautisch.de** (CEO-Korrektur 2026-10-05, vorher luna-hoa@).

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

- Status: verifiziert (2026-10-05: Anmeldung ok, Testmails an CEO-Adressen angekommen, kein Spam)
- Ziel / Scope: neuer Versandweg „All-Inkl“ mit dem gleichen Aufruf wie Gmail (Empfaenger, Betreff, Text, Anhaenge);
  Absender „Hanserautisch – LUNA <luna@hanserautisch.de>“; die gesendete Mail wird per IMAP in „Gesendet“ abgelegt und
  wie bisher als .eml archiviert; Schalter in der `.env` (Kundenversand = allinkl | gmail), Rueckfall auf Gmail nur
  per Schalter (nie automatisch, damit kein Kunde Mails von zwei Absendern bekommt). Versanddialoge zeigen den Absender.
- Gate: Tests mit Attrappe (kein echter Versand); **ein echter Testversand an eine CEO-Adresse** nach Freigabe; CISO-Eintrag.
- Aufwand: mittel.
- Umsetzung (2026-10-05): `governance/allinkl_mail.py` -- `AllInklMail` mit gleichem Aufruf wie Gmail (`mail_senden`,
  `mail_roh`), SMTP (SSL 465, sonst STARTTLS), Message-ID `<luna-…@hanserautisch.de>` (Kennung = Archiv-Name der .eml),
  Ablage der identischen Bytes per IMAP-APPEND in „Gesendet“ (Ordner per `\Sent`-Flag erkannt oder `ALLINKL_GESENDET_ORDNER`;
  scheitert die Ablage, ist die Mail trotzdem raus und in der Firmenakte); Fehlertexte ohne Zugangsdaten. Schalter
  `KUNDENVERSAND=allinkl|gmail` (Standard gmail) gilt fuer alle 6 Versandwege der Web-App und die Folgemahnung per Telegram;
  steht er auf allinkl und fehlt etwas, kommt ein klarer Fehler statt Rueckfall auf Gmail. Versanddialoge zeigen den
  Absender des gewaehlten Weges, „Jetzt senden“ ist gesperrt, wenn er nicht bereit ist (Mail-Programm geht immer).
  Pruefung `GET /api/finanzen/kundenversand` (Anmeldung SMTP+IMAP, kein Versand), Testmail
  `POST /api/finanzen/kundenversand/testmail` (nur mit Bestaetigung). Antworten erkennt erst M2.

## Etappe M2: Antworten der Kunden

- Status: umgesetzt (Gate offen: echter Test mit einer Antwort)
- Ziel / Scope: Kundenantworten im Postfach luna@ per IMAP erkennen (Zuordnung ueber Message-ID/In-Reply-To bzw.
  Belegnummer im Betreff), im Verlauf des Belegs anzeigen, archivieren und per Telegram melden -- wie heute bei Gmail.
- Gate: Tests (Zuordnung, keine Doppelmeldung); echter Test mit einer Antwort des CEO.
- Aufwand: mittel.
- Umsetzung (2026-10-05): `core/mail_antworten.py` im 15-min-Poll des Bots (nur bei `KUNDENVERSAND=allinkl`): Posteingang
  der letzten 30 Tage per IMAP nur lesend (`SELECT` readonly, `BODY.PEEK` -- Gelesen-Status bleibt, nichts verschoben/geloescht);
  Zuordnung ueber `In-Reply-To`/`References` mit der Kennung `<luna-…@hanserautisch.de>` aus dem Versand-Ereignis (alle
  Belegarten, Konzept-Versand speichert die Kennung jetzt mit), sonst Belegnummer im Betreff -- nur fuer Belege, die ueber
  All-Inkl gingen (Mahnung zaehlt fuer ihre Rechnung). Angebot: Antwort im Verlauf + .eml wie bei Gmail; andere Belege:
  Mail in die Firmenakte mit Bezug (Rechnung/Mahnung -> Rechnung, dort unter Dokumente). Ereignis `mail_antwort` (genau
  einmal), Telegram-Meldung „✉️ Antwort auf …“; Absender des CEO (`BELEG_ABSENDER`) und LUNA zaehlen nie als Kunde;
  Mails ohne Zuordnung bleiben unberuehrt. Testmail (`POST /api/finanzen/kundenversand/testmail`) speichert ihre Kennung
  (`kundenversand_testmail`); eine Antwort darauf wird auch von CEO-Adressen erkannt, nur gemeldet, nicht abgelegt.

## Etappe M3: Umschalten und Beobachten

- Status: in Umsetzung (umgeschaltet 2026-10-05 auf CEO-Anweisung, vor M2; Beobachtung laeuft)
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

Alle Kundenmails gehen von luna@hanserautisch.de raus, liegen dort in „Gesendet“ und in der Firmenakte, Antworten werden
erkannt und gemeldet.
