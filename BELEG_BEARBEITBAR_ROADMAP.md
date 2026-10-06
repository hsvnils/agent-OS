# Roadmap: Belege bis zum Versand bearbeitbar, danach nur mit Begruendung

- Status: in Umsetzung
- Stand: 2026-10-06
- Arbeitsbranch: `ai/beleg-bearbeitbar`
- Basiscommit: `eec7c30`
- Naechster Schritt: B1-B3 gebaut (2026-10-06) -- Deploy, dann Abnahme durch den CEO an echten Belegen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-06)

„Im Auftrag kann ich nichts aendern? Wieso nicht? Der duerfte doch erst festgeschrieben sein, wenn er versendet wurde?
Ein Beleg muss im Grunde immer bearbeitbar und speicherbar sein. Immer erst wenn er verschickt wird, muss er
festgeschrieben sein und kann nur mit Klick auf Bearbeiten und Eingabe einer Begruendung geaendert werden.“

## Analyse (read-only, 2026-10-06)

| Beleg | heute bearbeitbar | gesperrt ab | Aenderung danach |
|---|---|---|---|
| Angebot | Entwurf: alles | Versand (`angebot_status` versendet) | keine (nur neues Angebot) |
| Auftrag | nur Leistungszeitraum und Notiz | **sofort beim Anlegen** (Positionen aus dem Angebot eingefroren, `core/beauftragung.py`) | keine |
| Rechnung | Entwurf: alles | **Festschreiben** (Nummer, eigener Schritt vor dem Versand) | Storno + Korrektur-Entwurf |

- Der Auftrag widerspricht der CEO-Regel am deutlichsten: Er ist ab dem ersten Moment gesperrt, auch wenn er nie
  versendet wurde (Beispiel AB-2026-0001 CR Container: angelegt 28.09., nie gesendet).
- Bei der Rechnung haengt die Sperre am Festschreiben, nicht am Versand. Fuer eine **ausgestellte** Rechnung gilt
  rechtlich: Sie wird nicht mehr veraendert, sondern storniert und neu ausgestellt (§ 14 UStG, GoBD -- Hinweis, keine
  Beratung; im Zweifel Steuerberatung). Das bleibt auch kuenftig so -- nur der Ablauf fuer den CEO wird gleich.
- Angebot und Auftrag sind Geschaeftsbriefe (6 Jahre Aufbewahrung, kein Buchungsbeleg): Eine geaenderte Fassung nach dem
  Versand ist zulaessig, solange die versendete Fassung abgelegt bleibt -- das tut sie schon heute (PDF mit
  Inhalts-Hash in der Kette).
- Vorbild fuer Fassungen gibt es: Konzept-Mappe und Projektbericht kennen „(Version 2)“ im Mailbetreff.

## Grundsatz (fuer alle drei Belegarten gleich)

1. **Bis zum Versand:** Formular frei aenderbar und speicherbar (jede Speicherung als Ereignis in der Kette).
2. **Versand** (ueber LUNA oder „Im Mail-Programm oeffnen“ + „als versendet markieren“) **schreibt fest**.
3. **Nach dem Versand:** Formular nur lesen, Knopf **„✎ Bearbeiten …“** -> Begruendung eingeben -> Formular offen ->
   Speichern erzeugt eine neue Fassung mit Grund im Verlauf; Hinweis „Geaendert nach Versand – bitte erneut senden“.
4. Nichts wird ueberschrieben: Die Kette behaelt jede Fassung, das versendete PDF bleibt abgelegt.

## Etappe B1: Auftrag bis zum Versand voll bearbeitbar

- Status: umgesetzt
- Ziel / Scope: `AuftragBuch.aendern` nimmt alle Formularfelder an (Firma, Ansprechpartner, Titel, Positionen,
  Zuschlaege, Rabatt, Ware/Barter, Zahlungsbedingungen inkl. Vorkasse, Layout, Einleitung) -- solange der Auftrag
  **nicht versendet** und **beauftragt** ist und es **keine festgeschriebene Rechnung** dazu gibt (sonst passt die
  Rechnung nicht mehr zum Auftrag). Vorkasse-Betrag/-Frist und die vereinbarten Konditionen (Postings, TKP) werden aus
  der neuen Fassung berechnet. Formular im Auftrag offen mit „Änderungen speichern“; Hinweis im Formular, ab wann er
  gesperrt ist. Der Rechnungs-**Entwurf** zu einem geaenderten Auftrag bekommt einen Hinweis „Auftrag geaendert –
  Positionen pruefen“.
- Nicht-Scope: Angebot und Rechnung unveraendert; das angenommene Angebot bleibt wie versendet (die Abweichung zeigt
  die Belegverfolgung).
- Gate: Tests (aendern vor/nach Versand, mit/ohne festgeschriebene Rechnung, Vorkasse neu, Kette unveraendert gueltig,
  Gegenprobe rot); Browsertest Rechner 1300 / iPad 820 / iPhone 17 Pro.
- Verifikation: Szenario „Auftrag nicht versendet“ -> Position aendern + speichern -> PDF zeigt neue Position;
  Szenario „versendet“ -> Formular gesperrt, Server lehnt ab.
- Risiko / Rueckweg: Server-Regel wird gelockert; Rueckweg = Commit zuruecknehmen (alte Ereignisse bleiben lesbar).
- Aufwand: mittel.

## Etappe B2: Angebot und Auftrag nach dem Versand -- „Bearbeiten“ mit Begruendung

- Status: umgesetzt
- Ziel / Scope: Knopf „✎ Bearbeiten …“ bei versendetem Angebot (solange nicht angenommen/abgelehnt) und versendetem
  Auftrag (Regeln wie B1); Pflicht-Begruendung, neues Ereignis `*_entsperrt` mit Grund; danach neue Fassung
  (Version 2, 3 …) mit Grund im Verlauf, Mailbetreff „(Version 2)“, Hinweis „erneut senden“. Gueltig-bis und
  Erinnerungen des Angebots laufen ab dem erneuten Versand neu.
- Nicht-Scope: angenommenes Angebot (dann wird der Auftrag geaendert); Rechnung (B3).
- Gate/Verifikation wie B1, zusaetzlich: alte Fassung als PDF weiter abrufbar, Grund im Verlauf sichtbar.
- Risiko / Rueckweg: wie B1.
- Aufwand: mittel.

## Etappe B3: Rechnung -- Festschreiben erst beim Versand

- Status: umgesetzt
- Ziel / Scope (Empfehlung): Den eigenen Schritt „🔒 Festschreiben“ abschaffen. Der Entwurf bleibt bis zum Senden
  bearbeitbar; **„Senden …“ vergibt Nummer und schreibt fest** in einem Schritt (auch beim Weg „Im Mail-Programm
  oeffnen“: Nummer beim Erzeugen der Mail). Nach dem Versand: „✎ Bearbeiten …“ + Begruendung erzeugt automatisch die
  Stornorechnung und einen Korrektur-Entwurf mit allen Daten -- fuer den CEO derselbe Ablauf wie bei Angebot/Auftrag,
  rechtlich sauber (ausgestellte Rechnung wird nie veraendert).
- Alternative: Festschreiben bleibt ein eigener Schritt, nur der Knopf „Bearbeiten …“ (= Storno + Korrektur) kommt dazu.
- Offene Frage an den CEO: Gibt es Faelle, in denen eine Rechnung eine Nummer braucht, **ohne** versendet zu werden
  (z. B. ausgedruckt uebergeben)? Dann bekommt „Senden …“ eine dritte Wahl „Ohne Versand festschreiben“.
- Nicht-Scope: Mahnungen, Eingangs-/Eigenbelege.
- Gate: Tests (Nummer erst beim Versand, keine Luecken im Nummernkreis bei Abbruch, Bearbeiten nach Versand = Storno +
  Korrektur, Gegenprobe); Browsertest wie B1; Verfahrensdokumentation Abschnitt 2.2 anpassen.
- Risiko / Rueckweg: Aenderung im Rechnungsablauf (Nummernvergabe); Rueckweg = Commit zuruecknehmen.
- Aufwand: mittel.

## Umsetzung (2026-10-06, Go CEO fuer B1-B3)

- B1: `AuftragBuch.aendern` nimmt alle Formularfelder an, `AuftragBuch.sperre` liefert den Grund (versendet / fest wegen
  Rechnung oder Postings); Vorkasse wird aus der neuen Fassung berechnet, Konditionen tragen das Aenderungsdatum.
  Formular im Auftrag offen mit „Änderungen speichern“. Leistungszeitraum und Notiz bleiben wie bisher frei (rechts).
- B2: `auftrag_entsperrt` / `angebot_entsperrt` (Grund Pflicht) -> neue Fassung, „Version N“ im PDF und Mailbetreff;
  beim Angebot zurueck in den Entwurf, die kommenden Erinnerungen der alten Fassung loescht LUNA; angenommene
  Angebote bleiben (Hinweis auf den Auftrag). Knopf „✎ Bearbeiten …“ (mobil vorne in der Leiste).
- B3: Entwurf hat „✉️ Senden …“ (vergibt die Nummer, schreibt fest, oeffnet direkt den Versand ueber LUNA oder das
  Mail-Programm) und „🔒 Ohne Mail festschreiben …“; festgeschriebene Rechnung: „✎ Bearbeiten …“ = Storno + Korrektur-
  Entwurf mit Begruendung. Handlungsbedarf: „Rechnungsentwurf pruefen und senden“. Kein neuer Server-Ablauf noetig.
- Tests `test_beleg_bearbeitbar.py` (5, Gegenproben rot), Browser Rechner/iPad/iPhone in sechs Zustaenden.

## Nicht-Scope

Keine Aenderung an bereits versendeten oder festgeschriebenen Belegen in der Kette; keine Loeschung; Mahnungen,
Eingangs- und Eigenbelege bleiben wie sie sind.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`,
bei B3 `docs/verfahrensdokumentation-buchhaltung.md`.

## Definition of Done

Angebot, Auftrag und Rechnung sind bis zum Versand frei bearbeitbar, mit dem Versand festgeschrieben und danach nur
ueber „Bearbeiten …“ mit Begruendung aenderbar -- jede Fassung nachvollziehbar in der Kette.
