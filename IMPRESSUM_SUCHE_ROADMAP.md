# Roadmap: Kundendaten aus dem Impressum beim Anlegen einer Firma

- Status: in Umsetzung
- Stand: 2026-10-06
- Arbeitsbranch: `ai/impressum-suche`
- Basiscommit: `1120e1f`
- Naechster Schritt: I1 live (2026-10-06) -- Abnahme durch den CEO beim naechsten Neukunden; I2 (lokale KI) nur bei Bedarf.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-06)

„Beim Anlegen einer Firma den Website-Link zum Impressum eintragen, auf ‚Kundendaten suchen' druecken, und die lokale KI holt
die Daten aus dem Impressum und fuellt sie ein.“

## Analyse (read-only, 2026-10-06)

- Es gibt schon eine Impressum-Recherche (`core/firmendaten.py`, KUNDEN_FINANZEN Etappe 22): fuer **bestehende** Firmen mit
  Luecken, Knopf „🔎 Fehlende Daten im Netz suchen“ in der Firma, woechentlich im Bot. Sie liest das Impressum **regelbasiert**
  (Muster fuer Strasse, PLZ/Ort, USt-ID, Handelsregister, Telefon, Rechnungs-Mail) -- ohne KI, Vorschlaege nur per Klick.
- Beim **Neu-Anlegen** gibt es das nicht; der Firmenname wird nicht aus dem Impressum gelesen.
- Sicherheitsluecke fuer eine frei eingegebene Adresse: `_abruf` ruft jede URL ab -- auch interne Geraete im Heimnetz
  (NAS, Fritz!Box). Vor dem Einbau muss der Abruf auf oeffentliche http(s)-Adressen beschraenkt werden (gilt dann auch fuer die
  bestehende Recherche).
- Lokale KI: `qwen3:14b` laeuft auf dem MACO470 (Backoffice); die Web-App laeuft auf der NAS.

## Etappe I1: „Kundendaten suchen“ im Formular (regelbasiert)

- Status: umgesetzt
- Ziel / Scope: im Formular „Neue Firma“ (und in der Firma) Feld „Website / Impressum-Link“ + Knopf „🔎 Kundendaten suchen“:
  LUNA ruft die Seite (bzw. das verlinkte Impressum) ab, liest Firmenname (Rechtsform-Zeile), Strasse, PLZ, Ort, USt-ID,
  Handelsregister, Telefon, Mail und fuellt **leere** Felder vor (farbig markiert, mit Quelle); gespeichert wird erst mit
  „Anlegen“/„Speichern“. Schutz: nur oeffentliche http(s)-Adressen (keine privaten/lokalen IPs, keine Umleitung ins Heimnetz),
  Zeit- und Groessenlimit.
- Gate: Tests (Impressum-Beispiele, Name mit Rechtsform, Schutz gegen interne Adressen inkl. Umleitung, Gegenprobe);
  Browsertest Rechner/iPad/iPhone 17 Pro; echter Test mit 2-3 Kunden-Websites.
- Aufwand: klein bis mittel.
- Umsetzung (2026-10-06): `core/firmendaten.py` `oeffentlich()` (nur http(s), Port 80/443, ohne Zugangsdaten, alle IPs global --
  keine privaten/lokalen/Link-Local/CGNAT/Multicast-Netze) + `_SichereUmleitung` (Umleitungen ebenso geprueft), `name_lesen()`
  (Zeile mit Rechtsform, nicht „Vertreten durch …“), `aus_impressum()` (eingegebene Seite, dann /impressum, /imprint,
  Impressum-Links der Startseite); Endpunkt `POST /api/crm/impressum-suche` (nur Vorschlag, kein Ereignis). Oberflaeche: Feld +
  „🔎 Kundendaten suchen“ in „Neue Firma“ und in der Firma, fuellt nur leere Felder (markiert, mit Quelle). Echter Test:
  hsv.de, spiegel.de, all-inkl.com gelesen; dabei Registergericht „des Amtsgerichtes …“ und „Umsatzsteuer-ID :“ nachgeruestet.

## Etappe I2: Lokale KI als Ergaenzung (optional)

- Status: geplant
- Ziel / Scope: findet die Regel zu wenig (z. B. Impressum als Fliesstext), liest die lokale KI (`qwen3:14b`, MACO470) den
  Impressumstext und liefert die Felder als JSON; Ergebnis ebenfalls nur als Vorschlag, gekennzeichnet „von der KI gelesen“.
  Nur der oeffentliche Impressumstext geht an das lokale Modell (kein externer Dienst).
- Gate: Tests mit Attrappe; Vergleich Regel vs. KI an echten Impressen; Laufzeit (lokales Modell braucht Sekunden).
- Aufwand: mittel.

## Nicht-Scope

Kein automatisches Speichern ohne Klick; keine Daten von Portalen (Northdata, LinkedIn usw.); keine Privatpersonen.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`.

## Definition of Done

Beim Anlegen einer Firma fuellt „Kundendaten suchen“ die Stammdaten aus dem Impressum vor, sicher gegen Abrufe ins Heimnetz.
