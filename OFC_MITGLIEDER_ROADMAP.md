# Roadmap: OFC-Mitglieder nur noch in LUNA-OS (weg vom Google-Formular)

- Status: abgeschlossen
- Stand: 2026-11-28
- Arbeitsbranch: `ai/ofc-mitglieder`
- Basiscommit: `4b1dde2`
- Naechster Schritt: keiner -- abgeschlossen 2026-11-28 (Sichtabnahme durch den CEO: „Sichtabnahme ok“).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Auftrag (CEO 2026-11-26)

„Ich will zukuenftig weg vom Google-Formular und nur noch mit dem LUNA-OS arbeiten.“ Mitglieder sollen in LUNA-OS
bearbeitet werden koennen, der Mitgliedsstatus (Gold/Standard/Foerder) sichtbar sein. Neue Mitglieder traegt der CEO selbst
in LUNA-OS ein (**Variante a**); eine oeffentliche Anmeldeseite ist **nicht** Teil dieser Roadmap.

## Analyse (read-only, Belege; nur Zahlen, keine Namen)

- **Quelle heute:** Google-Tabelle „Mitgliedschaftsanfrage“ (Formularantworten), von LUNA nur lesend gelesen
  (`core/ofc_mitglieder.py` `lesen`, OFC OM). LUNA schreibt dort nie (CEO-Regel). Bearbeiten geht nur in der Tabelle.
- **Umfang am 2026-11-26** (`GET /api/ofc/mitglieder`, nur Zaehlungen ausgewertet):
  - 130 Zeilen: 119 Mitglieder mit Nummer (alle mit E-Mail) und 11 Anfragen ohne Nummer.
  - 18 Spalten: Zeitstempel, HSVInside-Mitglied (Nummer), HSV-Mitgliedsnummer, Mitglied seit, Beitrag, Naechste Zahlung,
    Anrede, Vorname, Nachname, Mitgliedschaft, Geburtstag, E-Mail (zweimal), HSV-Mitglied ja/nein, anderer Fanclub,
    Handy, Adresse, Kommentar.
- **Mitgliedschaften:**
  - 52 Standard (kostenfrei);
  - 65 Gold, in zwei Schreibweisen: 49 + 16 („jährliche“/„Jährliche Zahlung“);
  - 1 Foerder (Betrag im Kommentar);
  - 1 „Vorstand“.
- **Datenqualitaet:** 2 Mitgliedsnummern sind doppelt vergeben, 3 Namen doppelt eingetragen (Hinweise der Liste).
- **Abhaengigkeiten:** Alle OFC-Funktionen holen die Liste ueber **eine** Stelle `_ofc_mitglieder_daten()` in
  `channels/web/app.py`. Betroffen sind Beitraege (KA), Eingangs-Erkennung, Zahlungsbitten (TV3), Ticketversand (TV4),
  Namenssuche (TV2/TV3b) und die Mitgliederansicht. Ein Umschalten an dieser Stelle stellt alles gleichzeitig um, wenn
  das neue Verzeichnis dieselbe Form liefert (`mitglieder`/`anfragen` mit `nummer`, `name`, `vorname`, `nachname`,
  `email`, `mitgliedschaft`, `seit`, `beitrag`, `felder`).
- **Datenschutz:** Heute speichert LUNA die Mitgliederdaten nicht (nur 5 Minuten im Speicher). Kuenftig liegen Name,
  Adresse, Geburtstag, Handy und E-Mail im Fanclub-Speicher auf der NAS (nicht im Git, im Backup). Keine KI, nur der CEO
  sieht sie.

## Scope

Eigenes Mitgliederverzeichnis in LUNA (einmaliger Import aus der Tabelle), Mitglieder anlegen, bearbeiten und kuendigen (Archiv, keine Nachrichten mehr), Mitgliedschaft
und Status sichtbar und filterbar, Anfrage -> Mitglied aufnehmen, Verlauf jeder Aenderung, Umstellung aller OFC-Funktionen
auf das eigene Verzeichnis mit Parallelbetrieb und Abgleich, Export (CSV/PDF) fuer den Vorstand.

## Nicht-Scope

- Oeffentliche Anmeldeseite (Variante b): spaeter eigene Roadmap mit CEO-Freigabe und CISO-Pruefung.
- Schreiben in die Google-Tabelle (bleibt nur lesend, bis sie abgeschaltet wird).
- Endgueltiges Loeschen von Mitgliederdaten (CEO-Tor; Kuendigung = Archiv, nicht loeschen).
- Mails an Mitglieder ausser den bestehenden Zahlungsbitten/Tickets (TV3/TV4).
- Schutzbereiche nach `governance/roadmap-workflow.md` B4.

## Offene Entscheidungen (CEO)

| Nr | Frage | Empfehlung |
|---|---|---|
| E1 (wie empfohlen) | Welche Felder uebernimmt LUNA? | **Alle 18**, aufgeraeumt: Anrede, Vor-/Nachname, E-Mail (die zweite E-Mail-Spalte nur, wenn die erste leer ist), Handy, Adresse, Geburtstag, HSV-Mitglied + HSV-Nummer, anderer Fanclub, Mitgliedschaft, Beitrag, Mitglied seit, Naechste Zahlung, Kommentar, „Anfrage am“ (Zeitstempel). |
| E2 (wie empfohlen) | Mitgliedschaftsarten? | **Gold** (jaehrlich, Betrag aus E-K2 = 40 €), **Standard** (kostenfrei), **Foerder** (Betrag je Mitglied eintragbar). **Vorstand** ist keine eigene Art, sondern ein Haken „Vorstand“ zusaetzlich zur Mitgliedschaft. Beide Gold-Schreibweisen werden „Gold“. |
| E3 (wie empfohlen) | Doppelte Nummern (2) und doppelte Namen (3)? | **In der Import-Vorschau (MV0) klaerst du sie**: Fuer jede doppelte Nummer waehlst du, wer sie behaelt; der andere bekommt die naechste freie Nummer. Doppelte Namen werden nur angezeigt (koennen echte Namensvettern sein). |
| E4 (CEO-Zusatz 2026-11-26) | Kuendigung? | **Knopf „Kündigen“ am Mitglied** (Datum der Kuendigung, optional Notiz, mit Rueckfrage): das Mitglied wandert ins **Archiv** (eigene Ansicht „🗄 Archiv“, aus Liste und Suche verschwunden) und bekommt **keine Nachrichten mehr** von LUNA -- Zahlungsbitten und Ticketmails werden im Code fuer Archivierte gesperrt, auch bei offenen Karten. Ab dem Folgejahr kein Beitrags-Soll mehr; bereits Bezahltes bleibt. Nichts wird geloescht; „Wieder aufnehmen“ holt es zurueck. Endgueltiges Loeschen (z. B. auf Wunsch nach DSGVO) spaeter als eigene Funktion mit Bestaetigung (CEO-Tor). |
| E5 (wie empfohlen) | Neue Mitgliedsnummern? | **Naechste freie Nummer** (hoechste + 1, vierstellig wie bisher); du kannst sie beim Anlegen aendern. |
| E6 (wie empfohlen) | Wann wird umgeschaltet? | **Nach einem Parallelbetrieb**: LUNA zeigt einen Abgleich Tabelle <-> LUNA. Bei 0 Abweichungen schaltest du um; ab da ist LUNA die Quelle und die Tabelle nur noch Archiv. Danach schliesst du das Google-Formular. |

## Etappen

### Etappe MV0: Import-Vorschau (nur lesend)

- Status: umgesetzt 2026-11-26 (`core/ofc_verzeichnis.py` `import_vorschau`, `GET /api/ofc/mitglieder/import/vorschau`; `ofc_mitglieder.lesen` liefert dazu alle erkannten Felder als `werte`)
- Ziel / Scope: `GET /api/ofc/mitglieder/import/vorschau` zeigt, was uebernommen wuerde: Anzahl, Felder, Mitgliedschaften
  nach E2, Konflikte (doppelte Nummern mit Auswahl, doppelte Namen, fehlende E-Mail). Nichts wird gespeichert.
- Gate: Vorschau auf der NAS: 119 Mitglieder + 11 Anfragen, 2 Nummernkonflikte, Gold einheitlich.
- Aufwand: klein.

### Etappe MV1: Eigenes Verzeichnis und einmaliger Import

- Status: umgesetzt 2026-11-26 (`import_anwenden` einmalig mit Konfliktwahl, Ereignis `ofc_verzeichnis`, `GET /api/ofc/mitglieder/abgleich` -- bewusst geloeste Nummernkonflikte zaehlen nicht als Abweichung; Knopf „🗂 LUNA-Verzeichnis“; Tests `test_ofc_verzeichnis.py` mit Gegenproben)
- Ziel / Scope:
  - **Speicher:** Ereignisse `ofc_person_mitglied` (anlegen/aendern) im Fanclub-Speicher `fanclub/log.jsonl`; jede Aenderung
    ist ein neues Ereignis (Verlauf).
  - **Import:** einmalig, nach Bestaetigung, mit den Konflikt-Entscheidungen aus MV0. Danach liegt das Verzeichnis in LUNA.
  - **Noch keine Umstellung:** Die Funktionen lesen weiter aus der Tabelle (Schalter `OFC_MITGLIEDER_QUELLE=google`).
- Gate: Tests mit Gegenproben (Import doppelt ausgefuehrt legt nichts doppelt an; Konfliktwahl wird beachtet); Abgleich
  Tabelle <-> LUNA zeigt 0 Abweichungen ausser den bewusst geloesten Konflikten.
- Abhaengig von: MV0. Aufwand: mittel.

### Etappe MV2: Bearbeiten in LUNA-OS

- Status: umgesetzt 2026-11-26 (`ofc_verzeichnis.speichern/aufnehmen/kuendigen/wieder_aufnehmen/verlauf/export_csv`, `GET/POST /api/ofc/verzeichnis…`; 👥 Mitglieder zeigt nach dem Import das LUNA-Verzeichnis mit Reitern Mitglieder/Anfragen/Archiv, Filtern, ＋ Mitglied, ✏️ Bearbeiten, Kuendigen, Aufnehmen, Wieder aufnehmen, Verlauf, Export; **Gekuendigte sind schon jetzt fuer Zahlungsbitten und Ticketversand gesperrt und fehlen in der Personensuche**; Beitrags-Soll folgt mit MV3; Tests `test_ofc_verzeichnis.py` mit Gegenproben)
- Ziel / Scope: In 👥 Mitglieder:
  - **„＋ Mitglied“** legt ein Mitglied an (Nummer nach E5).
  - **✏️ Bearbeiten** fuer alle Felder aus E1.
  - **Mitgliedschaft** (Gold/Standard/Foerder + Betrag) und Haken „Vorstand“.
  - **„Kündigen“** mit Datum und Rueckfrage (E4): Mitglied ins **Archiv**, aus Liste und Suche ausgeblendet, „Wieder
    aufnehmen“ moeglich; im Code gesperrt fuer jede Mail (Zahlungsbitte, Tickets) und ohne Beitrags-Soll ab dem Folgejahr.
  - **Anfrage aufnehmen:** Anfrage -> Mitglied mit Nummer.
  - **Verlauf** je Mitglied (wer, wann, was geaendert).
  - **Liste** mit Filter nach Mitgliedschaft, Status und Vorstand; Zahlen je Art oben.
  - **Export** CSV/PDF.
  
  Ansicht auf Rechner, iPad und iPhone.
- Gate: Tests mit Gegenproben (Nummer doppelt -> abgelehnt; Kuendigen loescht nichts; gekuendigtes Mitglied bekommt keine
  Zahlungsbitte und keine Ticketmail, auch nicht automatisch; ungueltige E-Mail -> abgelehnt);
  headless Rechner/iPad/iPhone.
- Abhaengig von: MV1. Aufwand: mittel-gross.

### Etappe MV3: Umstellen auf LUNA als Quelle

- Status: deployt und verifiziert 2026-11-26 (Vorher/Nachher-Vergleich Beitraege 2027 identisch); umgesetzt 2026-11-26 (`ofc_verzeichnis.als_mitgliederliste` in der Form von `ofc_mitglieder.lesen`, Weiche `quelle` -- LUNA sobald das Verzeichnis existiert, Rueckweg `OFC_MITGLIEDER_QUELLE=google`; `_ofc_mitglieder_daten()` und alle direkten Leser (Namen, Mitglieder-API, Beitraege) folgen der Weiche, Import-Vorschau und Abgleich lesen weiter die Tabelle (`_ofc_tabelle_daten`); Beitraege ohne Soll nach dem Kuendigungsjahr, Foerderbetrag als Beitrag; Hinweistexte ohne Tabellenbezug; Tests mit Gegenproben)
- Ziel / Scope:
  - **Umschalter:** `_ofc_mitglieder_daten()` liefert je nach `OFC_MITGLIEDER_QUELLE` (`google` | `luna`) die Daten aus
    der Tabelle oder aus dem eigenen Verzeichnis, in derselben Form.
  - **Abgleich-Ansicht** bis zum Umschalten (E6).
  - **Nach dem Umschalten** nutzen Beitraege, Eingangs-Erkennung, Zahlungsbitten, Ticketversand und Namenssuche das
    LUNA-Verzeichnis.
  - **Doku:** Zugriffs-Policy (Tabelle nur noch Archiv), Datenfluesse, Datenschutz-Nachtrag.
- Gate: Gesamte Testsuite mit beiden Quellen; nach dem Umschalten Stichprobe durch den CEO (Beitraege 2027, eine
  Zahlungsbitte, eine Mitgliederansicht).
- Abhaengig von: MV2. Aufwand: mittel.

### Etappe MV4: Google-Formular abschalten (CEO)

- Status: erledigt 2026-11-26 (CEO; danach auf der NAS geprueft: Verzeichnis 119 + 11, Beitraege 2027 Soll 2.640 € aus LUNA, Personensuche 119; der Abgleich mit der Tabelle meldet nach Ablauf des 5-Minuten-Speichers „nicht lesbar“ -- gewollt)
- Ziel / Scope: Der CEO schliesst das Google-Formular und nimmt die Freigabe der Tabelle fuer LUNAs Google-Konto zurueck.
  LUNA liest die Tabelle danach nicht mehr; der Lese-Code bleibt fuer einen Rueckweg im Repo (Schalter).
- Gate: Mitgliederansicht und alle OFC-Funktionen laufen ohne Tabelle (LUNA zeigt „Quelle: LUNA“).

## Reihenfolge, Aufwand, Deploy

MV0 -> MV1 -> MV2 -> MV3 -> MV4. MV0 und MV1 koennen zusammen gebaut und mit einem Deploy ausgeliefert werden; danach
Import durch den CEO. Gesamtaufwand rund 2 Arbeitstage. Kein neuer Zugang, keine neuen Kosten.

## Dokumentationspflichten

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (E1-E6, „Variante a“, Ende des
Google-Formulars), `docs/datenfluesse.md`, `docs/datenschutz-ki-nutzung.md` (Mitgliederdaten jetzt gespeichert),
`governance/zugriffs-policy.md` (Tabelle -> Archiv), `docs/bekannte-fehler.md`, `OFC_ROADMAP.md` (Verweis).

## Definition of Done

MV4 erledigt: Mitglieder werden nur noch in LUNA-OS gepflegt, alle OFC-Funktionen lesen aus LUNA, das Google-Formular ist
geschlossen; Sichtabnahme durch den CEO. Danach Status „abgeschlossen“.
