# Roadmap: Eigenes Google-Konto fuer LUNA

- Status: in Umsetzung
- Stand: 2026-09-28
- Arbeitsbranch: `ai/luna-google-konto`
- Basiscommit: `cccda42`
- Naechster Schritt: Go fuer Etappe 2 (Deploy, Umschalten auf das LUNA-Konto per Google-Link, ein Neustart).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur aktuellen
  Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-09-28)

„Luna braucht einfach ein eigenes Google-Konto, von dem aus sie eigenstaendig agieren und die Google Produkte nutzen
kann." LUNA arbeitet kuenftig mit **eigenem** Gmail, Kalender, Drive und Sheets. Das Konto **hanserautisch@gmail.com**
(auch YouTube, Meta-Logins usw.) ist danach **nicht mehr** mit LUNA verbunden.

## Register und bekannte Fehler (B3)

- Register: Phase 11 (Google Workspace) sah urspruenglich ein **separates Konto** vor (`deploy/google-oauth-setup.md`
  Schritt 1) -- umgesetzt wurde es mit hanserautisch@gmail.com. Neu: Entscheidung „LUNA eigenes Google-Konto"
  (2026-09-28, CEO).
- Bekannte Fehler: **BF-33** (`invalid_grant`, stiller Ausfall) -- ein viel genutztes Hauptkonto widerruft Zugaenge
  eher (Passwortwechsel, Sicherheitspruefungen); der neue Selbstcheck meldet so etwas jetzt.

## Analyse (Belege, 2026-09-28)

- **Heutiger Zugriff** (`governance/google_workspace.py` `SCOPES`): Gmail lesen + Entwuerfe (`gmail.compose` erlaubt
  technisch auch Senden, im Code gated), Kalender lesen/schreiben, Drive lesen (alles) + eigene Dateien, Sheets lesen/
  schreiben -- alles auf hanserautisch@gmail.com. Groesstes Risiko: Lesezugriff aufs Hauptpostfach (Passwort-Resets).
- **Nutzer der Google-Anbindung** (grep): Briefing/Insights (`core/insights.py`: Agenda, neue Mails), 24/7-Watcher
  (`core/scheduler.py`: neue Mails, Kalender-Kollisionen), CRM-Mail-Tracking (`core/crm_mail.py`: Mails je Firma),
  LUNA-Suche (`core/hoa_tools.py`: Mail/Drive), Selbstcheck, Telegram-Werkzeuge (Mail/Kalender/Drive/Sheets, gated),
  LUNA-OS-Angebote (Gmail-Entwurf mit PDF, Kalender-Erinnerungen). Kalender immer `calendarId="primary"` (4 Stellen).
- **Technische Grenze:** Bei privaten Gmail-Konten kann ein Programm nur im **eigenen** Postfach arbeiten
  (Postfach-Delegation gilt nur in der Gmail-Oberflaeche). Mit eigenem LUNA-Konto sieht LUNA also nur, was in **ihrem**
  Postfach landet -> Weiterleitung aus hanserautisch@gmail.com per Filter. Kalender dagegen laesst sich direkt teilen.

## Scope

LUNA-Google-Konto anbinden (OAuth mit `deploy/google_oauth_neu.py`), eigener LUNA-Kalender
(`calendarId` konfigurierbar), eigenes LUNA-Postfach (keine Weiterleitung), Angebots-Versand auf das neue Modell umstellen,
Drive/Sheets im LUNA-Konto, alten Zugang auf hanserautisch@gmail.com widerrufen, Doku/Tests.

## Nicht-Scope

- Konto anlegen, Zwei-Faktor, Wiederherstellung, Kalender-Freigabe, Gmail-Filter, Widerruf im alten Konto: macht der
  **CEO** (Konten/Zugaenge = CEO-Tor, CISO)
- Google Workspace (kostenpflichtig) -- verworfen zugunsten eines kostenlosen Kontos (CEO 2026-09-28)
- Mails nach aussen **ohne** CEO-Klick (Oeffentlichkeit bleibt CEO-Tor, auch aus LUNAs eigenem Konto)
- YouTube, Meta, sonstige Dienste von hanserautisch@gmail.com
- Schutzbereiche laut `governance/roadmap-workflow.md` B4 (Token nur ueber das Skript in die `.env`)

## Entscheidungen (CEO, 2026-09-28)

1. **Konto:** `luna.hanserautisch@gmail.com` (Wiederherstellung: Handynummer/Mail des CEO).
2. **Angebote verschicken:** LUNA sendet **aus ihrem Konto**, erst nach dem Klick „Jetzt senden" des CEO in LUNA-OS
   (mit Vorschau); Antworten landen bei LUNA und werden dem CEO gemeldet.
3. ~~Mail-Eingang: komplette Weiterleitung~~ -- **revidiert (CEO 2026-09-28): keine Weiterleitung.** „ALLES was mit Luna
   zu tun hat, soll in ihrem Konto passieren, nicht im hanserautisch@gmail.com." LUNA bekommt nur Mails, die direkt an
   `luna.hanserautisch@gmail.com` gehen.
4. **Kalender:** nur LUNAs eigener -- keine Freigabe des CEO-Kalenders (auch nicht zum Lesen). Der CEO sieht LUNAs Termine
   per Einladung an seine iCloud-Adresse oder indem er LUNAs Konto in der Apple-Kalender-App hinzufuegt; will LUNA einen
   Termin des CEO kennen, laedt er sie ein.
5. **Cloud-Projekt „LUNA"** (Anmelde-App) bleibt beim CEO-Konto (menschliche Kontrolle, keine Daten).
6. **Vollstaendige Trennung:** nach der Umschaltung hat LUNA keinerlei Zugriff mehr auf hanserautisch@gmail.com.

## Etappen

Jede Etappe: Tests + Gegenprobe, Probelauf, CEO-Go, Deploy, Verifikation beim Empfaenger.

### Etappe 0: Konto anlegen (CEO)

- Status: abgeschlossen (2026-09-28) -- CEO: `luna.hanserautisch@gmail.com` angelegt, Zwei-Faktor aktiv, smarte
  Funktionen deaktiviert
- Ziel / Scope: Gmail-Konto anlegen, Zwei-Faktor-Anmeldung, Wiederherstellung auf den CEO; im Google-Cloud-Projekt der
  LUNA-App das Konto als Testnutzer eintragen oder die App auf „In Produktion" stellen (sonst verfaellt der Zugang im
  Testmodus nach 7 Tagen). Anleitung Schritt fuer Schritt liefert Claude Code. **Befund 2026-09-28:** App steht
  bereits auf „In Produktion" (Nutzertyp Extern, 1 von 100 Nutzern) -- kein Testnutzer-Eintrag noetig.
- Gate: CEO kann sich im neuen Konto anmelden.

### Etappe 1: Eigener LUNA-Kalender (Kalender-ID konfigurierbar)

- Status: abgeschlossen (Code, 2026-09-28) -- wirkt mit der Umschaltung in Etappe 2
- Ergebnis: Kalender-ID konfigurierbar (`GOOGLE_CALENDAR_ID`, Standard `primary` = eigener Kalender des angemeldeten
  Kontos -> nach Etappe 2 LUNAs). **Kein** `.env`-Eintrag noetig. Zwischenstaende korrigiert: Eintrag
  `GOOGLE_CALENDAR_ID=hanserautisch@gmail.com` wieder entfernt; die gebaute Lese-Funktion `GOOGLE_CALENDAR_LESEN` bleibt
  **ungenutzt** (ohne Eintrag wirkungslos). BF-34 (Ganztags-/Uhrzeit-Termine gemischt) behoben. Tests + Gegenproben,
  Suite 853 gruen.
- Gate: nach Etappe 2 -- Angebots-Erinnerung liegt in LUNAs Kalender und erscheint per Einladung im Apple-Kalender.

### Etappe 2: Umschalten auf das LUNA-Konto

- Status: geplant
- Ziel / Scope: `deploy/google_oauth_neu.py` mit dem LUNA-Konto (Token nur in die `.env` MACO470 + NAS),
  Selbstcheck gruen, Telegram-Werkzeuge + Briefing + Watcher gegen das neue Konto pruefen.
- Gate: Briefing, Agenda und LUNA-Suche laufen; Selbstcheck meldet keinen Fehler.

### Etappe 3: ~~Mail-Eingang ueber Weiterleitung~~

- Status: verworfen (CEO 2026-09-28, keine Weiterleitung) -- CRM-Mail-Tracking, Briefing und Watcher arbeiten nach
  Etappe 2 mit LUNAs eigenem Postfach.

### Etappe 4: Angebots-Versand nach Entscheidung 2

- Status: geplant
- Ziel / Scope: Knopf „Jetzt senden" in LUNA-OS (CEO-Klick = Freigabe, Vorschau von Empfaenger/Betreff/Text/PDF),
  Versand aus dem LUNA-Konto, Status „versendet" automatisch, Antworten des Kunden dem Angebot zuordnen und melden.
- Gate: Test-Angebot an eine eigene Adresse, PDF-Anhang korrekt, Status/Verlauf stimmen.

### Etappe 5: Alten Zugang widerrufen + Abschluss

- Status: geplant
- Ziel / Scope: CEO entfernt „LUNA" unter myaccount.google.com -> Sicherheit -> Drittanbieter-Zugriff im Konto
  hanserautisch@gmail.com; Doku (`deploy/google-oauth-setup.md`, `docs/datenfluesse.md`, Zugriffs-Policy) aktualisieren.
- Gate: alter Token ist ungueltig, alles laeuft ueber das LUNA-Konto.
