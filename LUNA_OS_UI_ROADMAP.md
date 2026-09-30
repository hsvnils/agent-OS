# Roadmap: LUNA-OS Navigation, Handlungsbedarf und WebApp-Login
- Status: in Umsetzung
- Stand: 2026-09-30
- Arbeitsbranch: `ai/plan-ui-navigation` (Plan); Umsetzung je Etappe auf eigenem Branch `ai/ui-etappe-<n>`
- Basiscommit: `86393dc`
- Naechster Schritt: CEO-Go 2026-09-30 fuer Etappen 1-6 am Stueck (Passkey ausdruecklich dazu); Etappen 2+6 umgesetzt, weiter mit Etappe 1. Deploy braucht einen Image-Neubau (neue Bibliothek `webauthn`).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-09-30)

„Das Menue oben ist unuebersichtlich, es sind viele Punkte ... eine Home-Seite mit den Bereichen, pro Bereich eine
Bereichs-Homeseite mit dem Wichtigsten ... Mobil ein seitliches Menue?“ Dazu: „eine Kachel, die alle dringenden
Handlungen ueber das gesamte LUNA-System anzeigt“ und „auf iPhone/iPad als WebApp muss ich mich immer neu einloggen,
der Schluesselbund schlaegt nichts vor -- per Face ID entsperren?“

Abgestimmte Skizze (klickbar, Beispielwerte): https://claude.ai/artifact/VkVbv67aDxPpu8KqmUX2bR
CEO-Entscheidungen 2026-09-30: Einteilung in 4 Bereiche passt; Freigaben als Glocke oben rechts (Empfehlung
uebernommen); Glocke zaehlt allen dringenden Handlungsbedarf.

## Analyse (read-only, 2026-09-30)

- **Navigation:** `orchestrator/channels/web/static/app-v2.js:65` `SECTIONS` = **19 Punkte**, in der Kopfzeile als
  reine Symbole ohne Text (`buildShell`, Zeile 96). Fachlich Zusammengehoeriges liegt verstreut (Angebote/Rechnungen/
  Belege/Finanzen zwischen CRM, Radar und Cutter).
- **Nutzung (NAS `nutzung/log.jsonl`, 30 Tage):** dash 48, angebote 29, kunden 13, finanzen 13, rechnungen 10,
  belege 9, crm 7, investment 5, devroadmap 4, freigaben/radar/content je 3, agenten/cutter/team je 2,
  wissen/system/einstellungen/reel je 1. Geschaeftsteil = 74 von 110 Oeffnungen ausserhalb des Dashboards.
- **iPhone (390 px, echte `index-v2.html` im 390-px-Rahmen gerendert):** nur 10 von 19 Symbolen sichtbar, Rest nur
  per Wischen ohne Hinweis; Seitenkoepfe quetschen Titel und Knoepfe; Kunden-Suchfeld ragt ueber den Rand; Tabellen
  abgeschnitten; `viewport-fit=cover` gesetzt, aber `style-v2.css` nutzt keine `safe-area`-Abstaende (0 Treffer);
  „LUNA fragen“ unter 1000 px ausgeblendet (`.v2-pills {display:none}`).
- **Login:** `orchestrator/channels/web/app.py:197` `auth()` ist die einzige, globale Pruefung
  (`FastAPI(dependencies=[Depends(auth)])`) und nutzt **HTTP-Basic** (`WWW-Authenticate: Basic`). Ursache fuer das
  CEO-Problem: Eine iOS-Home-Bildschirm-WebApp behaelt Basic-Anmeldungen nicht ueber einen Neustart der App, und der
  Schluesselbund fuellt nur echte Login-Formulare aus, nicht den System-Dialog. Keine Fehlversuch-Bremse vorhanden.
- **Maschinen-Zugaenge per Basic** (muessen weiter funktionieren): `deploy/luna_waechter.py:41` (MACO470-Waechter),
  `cutter/luna_bridge.py:31` (Cutter-Bruecke), Konto `maco470-worker`, Webhooks (`/api/webhook/*`, ausgenommen).
- Register/Fehler: keine Vorentscheidung zu Login/Passkey im Entscheidungs-Register; BF-A30 (Basic-Auth griff am
  Webhook) ist behoben und bleibt beachtet.

## Scope / Nicht-Scope

- Scope: Oberflaeche LUNA-OS V2 (`app-v2.js`, `style-v2.css`, `index-v2.html`), neue Lese-Endpunkte, Login-Seite und
  Sitzungen in `app.py`, Tests.
- Nicht-Scope: V1-Oberflaeche; Inhalte der Unterseiten (Angebote, Finanzen usw. bleiben inhaltlich wie heute);
  `.env`/Passwoerter (der CEO aendert Passwoerter selbst); Telegram-Bot; Maschinen-Zugaenge (bleiben Basic);
  Container-Neustart (CEO).

## Etappen

### Etappe 1: Neue Navigation (4 Bereiche, Glocke, iPhone-Seitenmenue)
- Status: umgesetzt (2026-09-30) -- Browsertest: 19/19 Seiten erreichbar, Team-Rechte filtern Bereiche, keine
  Ueberbreite; dabei BF-46 gefunden und behoben. Die funktionslosen Knoepfe 🔎/🌐 DE sind entfernt, „Freigabe pruefen“/
  „Screen starten“ als Pills entfallen (Glocke bzw. Knopf auf der Investment-Seite).
- Ziel / Scope: Kopfzeile mit 4 beschrifteten Bereichen -- **Geschaeft** (Kunden, Angebote, Rechnungen, Belege,
  Finanzen), **Content & Collabs** (CRM, Radar, Content, Cutter, Reels), **Investment**, **LUNA & System**
  (Freigaben, Agenten, Wissen, Roadmap, System, Team, Einstellungen). Im Bereich eine zweite Reihe mit den
  Unterpunkten, Pfadzeile „Start › Bereich › Seite“. Glocke oben rechts mit Zaehler (bis Etappe 3: offene
  Freigaben). Unter 700 px: ☰-Seitenmenue mit allen Bereichen/Unterpunkten, „LUNA fragen“ im Menue, Abstaende fuer
  Notch/Home-Balken (`env(safe-area-inset-*)`). Modul-Rechte gelten weiter (was ein Teammitglied nicht darf, fehlt
  auch im Menue). Alle bisherigen Sprungziele (`go(id)`) bleiben gueltig.
- Nicht-Scope: Bereichs-Startseiten (Etappe 4), Handlungsbedarf (Etappe 3).
- Gate: Browsertest bei 1440 px und im 390-px-Rahmen: 4 Bereiche sichtbar, jeder der 19 bisherigen Punkte in
  hoechstens 2 Klicks erreichbar, Seitenmenue oeffnet/schliesst, Nutzer ohne Modul sieht den Punkt nicht, kein
  JS-Fehler; Suite + Doku-Check gruen.
- Verifikation: Browsertest `fx`-Harness -> erwartet `bereiche=4 erreichbar=19/19 fehler=[]`; live nach Neustart
  `GET /` liefert neue `app-v2.js?v=`-Nummer.
- Risiko / Rueckweg: reine Oberflaeche; Rueckweg = vorheriger Commit.
- Aufwand: mittel.

### Etappe 2: Login fuer die WebApp (Schluesselbund, angemeldet bleiben)
- Status: umgesetzt (2026-09-30) -- `core/sitzungen.py`, `static/login.html`, `auth()` in `app.py`; Tests `test_login.py`
- Ziel / Scope: Eigene Login-Seite (Formular mit `autocomplete="username"` / `current-password`) -> iCloud-
  Schluesselbund schlaegt die Daten vor und fuellt sie per Face ID aus. Nach erfolgreichem Login ein
  **Sitzungs-Cookie** (`HttpOnly`, `Secure`, `SameSite=Lax`, Laufzeit 30 Tage, gleitend verlaengert); Sitzungen
  serverseitig gespeichert (nur Hash des Tokens, Datei auf der NAS, nicht im Git) und widerrufbar: „Abmelden“ und in
  den Einstellungen „Alle Geraete abmelden“ mit Liste der Geraete. Fehlversuch-Bremse (z. B. 5 Fehlversuche ->
  Wartezeit). POST-Anfragen per Cookie nur von der eigenen Adresse (Origin-Pruefung). HTTP-Basic bleibt fuer
  Maschinen-Zugaenge (Waechter, Cutter-Bruecke, maco470-worker) unveraendert gueltig. `apple-mobile-web-app-capable`
  pruefen, damit die WebApp als eigenstaendige App startet.
- Nicht-Scope: Passwoerter aendern (CEO), neue Abhaengigkeiten.
- CEO-Tor / CISO: Zugriffs-Policy aendert sich (`AGENTS.md` 5.7) -> CISO-Sicht (Cookie-Flags, Laufzeit, Widerruf,
  Bremse) steht in der Etappe dokumentiert; Go des CEO gilt als Freigabe.
- Gate: Tests: falsches Passwort -> kein Cookie; richtiges -> Cookie mit HttpOnly/Secure/SameSite; widerrufene
  Sitzung -> 401; 6. Fehlversuch gebremst; Basic-Zugang weiter 200; Webhooks weiter offen; POST mit fremdem Origin
  abgelehnt. Suite + Doku-Check gruen.
- Verifikation: live `curl` mit Basic auf `/api/betrieb/status` -> 200 (Waechter unberuehrt); CEO: iPhone-WebApp
  schliessen, 1 h spaeter oeffnen -> ohne Login drin; Login-Feld bietet Schluesselbund-Eintrag an.
- Risiko / Rueckweg: Aussperren -> Basic bleibt als Weg erhalten; Rueckweg = vorheriger Commit.
- Aufwand: klein bis mittel.

### Etappe 3: Handlungsbedarf ueber das ganze LUNA-System
- Status: umgesetzt (2026-09-30) -- `core/handlungsbedarf.py`, `GET /api/handlungsbedarf` (Tages-To-dos + Antraege +
  Investment-Entscheidungen + Betriebsstoerungen), Startseiten-Kachel ersetzt „Zu erledigen“, eigene Seite mit Filter,
  Glocke zaehlt „dringend“. Nicht enthalten (Grund im Modul): Backup-Status (nur MACO470) und Sicherheits-Befunde
  (kommen als Antrag unter Freigaben).
- Ziel / Scope: Neuer Sammler (`core/handlungsbedarf.py`, Endpunkt `GET /api/handlungsbedarf`), der aus allen
  Bereichen die Punkte holt, die der CEO tun muss, mit Stufe **dringend** (ueberfaellig/heute), **diese Woche**,
  **wenn Zeit ist**, Grund, Bereich und Sprungziel. Quellen: bestehende Geschaefts-To-dos (`core/todos.py`:
  Rechnungen, Angebote, Belege, Zeit zuordnen, Firmendaten-Vorschlaege, Vorkasse), Freigaben/Antraege, Reels zur
  Freigabe, neue Collab-Anfragen (CRM), Investment-Vorschlaege, Betrieb (Bot-Herzschlag, Backup, haengende
  Meldungen), Sicherheits-Audit. Kachel „Handlungsbedarf“ ganz oben auf der Startseite, eigene Seite mit Filter
  nach Bereich; Glocke zaehlt „dringend“. Erledigt wird ueber den Sprung in die Fachseite (keine neuen Aktionen).
- Gate: Test je Quelle (Punkt erscheint mit richtiger Stufe und verschwindet nach Erledigung), leere Quellen
  brechen nichts; Browsertest Kachel/Seite/Glocke. Suite + Doku-Check gruen; `docs/datenfluesse.md` nachgetragen.
- Verifikation: live `GET /api/handlungsbedarf` -> Summe der Punkte je Quelle = Zaehlung direkt in der Quelle
  (Gegenprobe je Quelle).
- Aufwand: mittel.

### Etappe 4: Startseite und Bereichs-Startseiten
- Status: umgesetzt (2026-09-30) -- Startseite: Handlungsbedarf fest oben, 4 Bereichs-Kacheln mit Live-Zahlen
  (Finanz-Uebersicht, Reels, Investment-Loop, Betriebsstatus, Handlungsbedarf), darunter „Dein Dashboard“ (anpassbar wie
  bisher). Bereichs-Startseiten mit Kennzahlen und „Als Naechstes in diesem Bereich“. „Freigaben offen“ kommt aus
  derselben Quelle wie die Glocke.
- Ziel / Scope: Startseite = Handlungsbedarf + 4 Bereichs-Kacheln mit je 2-3 Live-Zahlen (Reihenfolge nach Nutzung),
  darunter das bisherige anpassbare Dashboard. Je Bereich eine Startseite mit Kennzahlen, „Als Naechstes in diesem
  Bereich“ (aus Etappe 3) und Sprungknoepfen. Zahlen nur aus bestehenden Endpunkten.
- Gate: jede Kennzahl = Wert der Fachseite (Gegenprobe); Browsertest Desktop + 390 px.
- Aufwand: mittel.

### Etappe 5: Mobil-Feinschliff der Seiten (iPhone und iPad)
- Status: geplant
- Ziel / Scope: Seitenkoepfe unter 700 px untereinander; Suchfelder volle Breite; breite Tabellen scrollen in der
  Karte; Tipp-Flaechen mindestens 44 px; Pruefung bei 390 px (iPhone) und 820/1180 px (iPad hoch/quer).
- Gate: Browsertest ueber alle 19 Seiten bei 390 px: keine Seite breiter als der Bildschirm (`scrollWidth = clientWidth`).
- Aufwand: klein bis mittel.

### Etappe 6 (optional): Face ID direkt per Passkey
- Status: umgesetzt (2026-09-30, CEO: „Passkey kannst du gern mit einbauen“) -- `core/passkeys.py`, `static/passkey.js`,
  Einstellungen „Anmeldung & Geraete“, Angebot nach Passwort-Login; `webauthn==3.0.1` im `deploy/Dockerfile` (OSV ohne
  Funde) -> Deploy mit Image-Neubau
- Ziel / Scope: Anmeldung per Passkey (WebAuthn) -- Face ID statt Passwort, das Passwort bleibt als Notweg. Braucht
  eine neue Python-Abhaengigkeit (z. B. `webauthn`, Open Source, kostenlos) -> Register-Eintrag, CISO-Pruefung, CEO-Go.
- Aufwand: mittel.

## Reihenfolge

1 -> 2 -> 3 -> 4 -> 5, 6 optional. Etappe 2 ist unabhaengig und kann vorgezogen werden (taeglicher Aerger, kleiner
Aufwand). Gebaut wird nach Go am Stueck, am Ende ein Deploy und ein Neustart.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Etappe 2: Sitzungsdatei; Etappe 3:
neuer Endpunkt), `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md` bei Funden, `UI.md` (Navigation).

## Definition of Done

Etappen 1-5 verifiziert und vom CEO auf iPhone, iPad und Rechner abgenommen; der CEO setzt den Status auf
abgeschlossen, der ausfuehrende Agent traegt ein.
