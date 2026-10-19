# Roadmap: Kundenordner auf der NAS mit Freigabe-Link per Mail

- Status: in Umsetzung
- Stand: 2026-10-19
- Arbeitsbranch: `ai/kundenordner-injektion`
- Basiscommit: `b9b9944`
- Naechster Schritt: F2 (Freigabe-Link) und F3 (Link per Mail) bauen, dann Deploy F1-F3.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-19)

„LUNA legt einen Ordner fuer Kunden auf der NAS an, um darueber Dateien freizugeben, und verschickt den Link zum
freigegebenen Ordner per E-Mail mit.“

## Analyse (read-only, 2026-10-19)

- Vorhanden: **Lieferungen je Auftrag** (`core/lieferungen.py`): Dateien (auch grosse Videos vom iPhone in Stuecken) liegen
  unter `lieferungen/<Auftrag>/` auf der NAS, die Liste steht in der Kette. Sie sind nur fuer angemeldete Nutzer von LUNA-OS
  erreichbar -- der Kunde kann sie heute nicht abrufen.
- Von aussen erreichbar ist nur **LUNA-OS ueber 443** (`os.hanserautisch.synology.me`, Reverse-Proxy, Let's Encrypt); jeder
  Pfad ausser Login/Passkey verlangt eine Anmeldung (`_OFFEN` in `channels/web/app.py`).
- Kundenversand ueber All-Inkl (luna@) mit mehreren Empfaengern, CC/BCC und Textbausteinen ist vorhanden.
- **Zwei Wege fuer den Link:**
  - **A (Empfehlung): eigener Freigabe-Link in LUNA-OS** (`/teilen/<zufaelliger Schluessel>`): nur dieser eine Pfad ist ohne
    Anmeldung erreichbar und zeigt nur die Dateien dieses einen Ordners zum Herunterladen; mit Ablaufdatum, optional Passwort,
    jederzeit widerrufbar, jeder Abruf wird protokolliert. Kein neuer Port, kein DSM-Konto noetig.
  - **B: Synology-Freigabelink (File Station)** -- braucht ein DSM-Konto mit Freigaberechten und eine Freigabe des DSM nach
    aussen (zusaetzlicher Port bzw. QuickConnect). Mehr Angriffsflaeche, und LUNA kann die Abrufe nicht sehen.

## Etappe F1: Kundenordner

- Status: gebaut 2026-10-19 (`core/kundenordner.py`, Endpunkte `/api/crm/kunden/<nr>/ordner`, `/api/crm/kundenordner/*`, Firmenakte „🗂️ Kundenordner“, Knopf „🗂️ In Kundenordner“ an Lieferungen, Chat-Werkzeug `kundenordner_anlegen`, Backup-Spiegel in `deploy/backup-from-nas.sh`; Test `test_kundenordner.py`), Deploy mit F2/F3
- Ziel / Scope: Ordner je Kunde und Projekt (`kundenordner/<Kundennummer>/<Projekt bzw. Auftrag>/`, nur NAS, nicht im Git,
  im Backup), angelegt per Knopf in der Firmenakte bzw. am Auftrag oder durch LUNA im Chat („leg fuer Kiez Burger einen
  Ordner Herbstkampagne an“). Dateien hochladen (auch grosse Videos in Stuecken, wie bei Lieferungen), ansehen, entfernen;
  Lieferungen eines Auftrags koennen mit einem Klick in den Ordner uebernommen werden.
- Gate: Tests (Pfade nur innerhalb des Kundenordners, Namen bereinigt, grosse Dateien); Browser Rechner/iPad/iPhone.
- Aufwand: mittel.

## Etappe F2: Freigabe-Link

- Status: geplant
- Ziel / Scope (Weg A): „🔗 Freigeben …“ -> Link mit Ablauf (Standard 30 Tage), optional Passwort, Anzeige „Nur ansehen und
  herunterladen“. Oeffentliche Seite im Hanserautisch-Look mit Dateiliste und Einzel-/ZIP-Download; Abruf-Protokoll und
  „Link widerrufen“ am Ordner. Schutz: langer Zufallsschluessel, Ablauf, Begrenzung der Abrufe je Minute, keine anderen
  Pfade ohne Anmeldung, kein Verzeichnis-Wechsel.
- Freigabe: neuer oeffentlich erreichbarer Pfad = **CISO-Freigabe** (Zugriffs-Policy) und CEO-Entscheidung.
- Gate: Tests (abgelaufen/widerrufen = kein Zugriff, falsches Passwort, Pfad-Tricks wie `../`, nur dieser Ordner); Browser.
- Aufwand: mittel.

## Etappe F3: Link per Mail

- Status: geplant
- Ziel / Scope: „✉️ Link senden …“ im Ordner: Versanddialog mit Empfaengern der Firma (wie bei Belegen, mehrere, CC/BCC),
  neue Textbaustein-Art „Dateifreigabe“ (Link, Ablaufdatum, ggf. Hinweis auf das Passwort -- das Passwort selbst nie in
  derselben Mail); Versand nur per Klick (Mails an Kunden = CEO-Tor). Auch aus dem Chat: LUNA bereitet die Mail vor, du
  bestaetigst. Versand steht im Verlauf der Firma.
- Gate: Tests (Mail enthaelt Link + Ablauf, nie das Passwort, Versand nur mit Bestaetigung); Browser.
- Aufwand: klein.

## Nicht-Scope

Kein Hochladen durch Kunden (spaeter moeglich), keine dauerhaften Links ohne Ablauf, keine Freigaben aus der Buchhaltung.

## Entscheidungen fuer den CEO

1. Weg A (eigener LUNA-OS-Link, Empfehlung) oder B (Synology-Freigabe)?
2. Standard-Ablauf 30 Tage und Passwort optional -- passt das?

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`,
`governance/zugriffs-policy.md` (CISO, oeffentlicher Pfad), `deploy/` (Ausschluss, Backup).

## Definition of Done

Fuer jeden Kunden gibt es Ordner auf der NAS; ein Klick erzeugt einen sicheren, ablaufenden Link, den LUNA per Mail an
die Ansprechpartner schickt -- jeder Abruf ist sichtbar, und der Link laesst sich jederzeit widerrufen.
