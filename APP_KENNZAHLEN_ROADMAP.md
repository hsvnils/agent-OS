# Roadmap: Kennzahlen der Hanserautisch-App in LUNA-OS (Teil 1)

- Status: in Umsetzung
- Stand: 2026-11-28
- Arbeitsbranch: `ai/app-kennzahlen` (Teil 1), `ai/app-kennzahlen-live` (Erweiterung Live, AK5-AK7)
- Basiscommit: `fef5b17`
- Naechster Schritt: AK0-AK6 live; AK4 bestanden 2026-11-28. Offen: AK7 (Live-Abgleich + Sichtabnahme durch den CEO, To-do 27.11.), danach Status „abgeschlossen“.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Auftrag

CEO-Auftrag vom 2026-11-26 (Uebergabe aus der App-Entwicklung, Datei `LUNA_UEBERGABE.md`, Stand 2026-11-25, ohne
Secret-Werte): LUNA holt einmal taeglich die Tageskennzahlen der Hanserautisch-App ueber eine feste HTTPS-Schnittstelle,
legt sie lokal dauerhaft ab (die Ablage ist das Archiv, Zeitreihen auch ohne Quelle) und zeigt sie in einer Kachel
„Hanserautisch-App“. Meldungen per Telegram. Teil 2 (aktive Nutzer, Wiederkehr, App-Versionen, Seitenaufrufe) folgt mit
dem App-Update 1.0.2 (12) ueber dieselbe Schnittstelle.

Fuer die OFC-Kasse zurueckgestellt (CEO 2026-11-26: „was dringendes vorziehen“); dort warten nur noch CEO-Schritte.

## Quelle (Kurzfassung der verbindlichen Schnittstelle)

- `GET https://yygrgcvepxrfbiaxvrmb.supabase.co/functions/v1/luna-kennzahlen?von=JJJJ-MM-TT&bis=JJJJ-MM-TT`,
  Kopfzeile `Authorization: Bearer <Token>`. Berliner Tage, beide einschliesslich; hoechstens 400 Tage; `bis` nicht nach
  heute. Nur lesend, kein CORS, kein Supabase-Schluessel, kein Datenbank-Zugang.
- Antwort: `ok`, `revision`, `von`, `bis`, `erzeugt_am`, `anzahl`, `zeilen[]` mit `datum`, `kennzahl`, `dim1`, `dim2`,
  `wert`, `stand`. Lange Form: eine Zeile = ein Wert fuer `(datum, kennzahl, dim1, dim2)`.
- Status: 200 speichern; 400/405 Fehler im eigenen Code, nicht wiederholen; 401 sofort melden, nicht wiederholen;
  500 melden; 502 nach 5, 15, 45 Minuten wiederholen.
- Die letzten drei Tage rechnet die Quelle jede Nacht neu (`stand` wird neuer). Fehlende Zeile = 0, ausser vor dem
  Messbeginn (`ab`) einer Kennzahl. Momentaufnahmen gibt es erst ab 2026-11-24. Unbekannte Kennzahlen speichern, nicht
  anzeigen.
- Kennzahl-Katalog mit Bedeutung, Aufteilung und `ab`: Teil B, Abschnitt 3 der Uebergabe; wird in AK1 als feste Tabelle
  in den Code uebernommen (Quelle der Anzeige-Texte und der `ab`-Daten).

## Analyse (read-only, Belege)

- **B1 Erreichbarkeit und Token (2026-11-26, MACO470):** Einmaliger Abruf, ausgegeben wurden nur Status, Anzahl und
  Kennzahl-Namen, **keine Werte**:
  - `von=bis=2026-11-25` -> HTTP 200, `revision 2026-11-25.k1c`, 37 Zeilen, 26 Kennzahlen, 5 KB.
  - `von=2026-05-14, bis=2026-11-25` -> HTTP 200, 2.255 Zeilen, 196 Tage, 33 Kennzahlen, 303 KB. Groesste Gruppen:
    `pushes_art` 806, `tipps` 235, `chatnachrichten_stunde` 219, `pushes` 214.
  - Noch keine Zeilen fuer `abo_bewegungen`, `abos_neu`, `kontoloeschungen` (fehlende Zeile = 0 bzw. Messbeginn).
- **B5 Umfang:** rund 40-60 Zeilen je Tag, rund 20.000 im Jahr. Das passt in eine NAS-Datei; es braucht keine Datenbank.
- **Token:** Lese-Token nur fuer diese eine Function (Angaben der App-Sitzung 2026-11-26): kein Datenbank-Zugang, kein
  Schreiben, keine anderen Functions; Schutzbedarf vertraulich (geschaeftliche Kennzahlen), nicht personenbezogen; Sperren
  durch ein neues Token in Supabase (altes sofort 401). Es gehoert nur dorthin, wo der Abruf laeuft: seit 2026-11-26 in der
  **NAS**-`.env` (vom CEO per SSH uebertragen, ohne Wertanzeige, Pruefsumme MACO = NAS), die Kopie auf dem MACO470 ist
  entfernt (Readback `0`).
- **Netz-Regel (`AGENTS.md` 5.7):** Das ist eine feste Daten-Schnittstelle, keine freie Websuche. Sie darf direkt
  angebunden werden, braucht aber eine CISO-Freigabe und einen Eintrag im Wachtest `orchestrator/tests/test_netz_wache.py`.
- **Vorgaenger-Plan:** `MONETARISIERUNG_ROADMAP.md` M5 sah einen Datenbank-Zugang ueber die Rolle `luna_reader`
  (Session-Pooler) vor. Der neue Weg (nur eine HTTPS-Function mit eigenem Token, kein DB-Zugang) ist enger und ersetzt
  ihn. M5 wird mit dieser Roadmap erledigt und dort darauf verwiesen (AK1).
- **Datenschutz:** Die Quelle liefert nur Summen, keine Personen. Die Abo- und Umsatzzahlen gehen an **kein**
  KI-Modell (CEO-Regel, `docs/datenschutz-ki-nutzung.md`): kein Chat-Werkzeug, kein Briefing-Text ueber ein Modell, keine
  Globale Suche. Anzeige und Rechnung laufen nur deterministisch im Code. Auch Claude Code prueft nur Zeilenzahlen, nie
  Werte; der Summenabgleich laeuft in LUNA-OS beim CEO (AK2).
- **App-Projekt:** LUNA aendert dort nichts. Sie ruft nur die eine Adresse lesend ab.

## Scope

Abruf (Erstabruf, taeglich, Nachholen, Wiederholen), lokale Ablage mit Upsert nach `stand`, Kachel „Hanserautisch-App“
(Oben, Community, Geld, Betrieb; Zeitraeume 7 Tage, 30 Tage, Saison, alles), Kontroll-Abgleich je Stichtag,
Telegram-Meldungen, Doku (Zugriffs-Policy, Dienste-Register, `docs/datenfluesse.md`, Netz-Wache, Datenschutz).

## Nicht-Scope

- Jede Aenderung am App-Projekt (Supabase der App, Function, App-Code, Store-Konsolen).
- Teil 2 (aktive Nutzer, Wiederkehr, Versionen, Seitenaufrufe): eigene Etappen nach 1.0.2 (12). Neue Kennzahlen werden ab
  AK1 aber schon gespeichert.
- Chat-Werkzeug oder Modell-Zugriff auf die Zahlen; Weitergabe an Gemini, Claude, OpenAI oder den Netz-Agenten.
- Store-Abrechnungen und Installationen (`MONETARISIERUNG_ROADMAP.md` M7).
- Schutzbereiche nach `governance/roadmap-workflow.md` B4: `.env` (das Token traegt der CEO ein), Telegram-Bot (nie
  zusaetzlich starten), Container-Neustarts (CEO), Live-Daten.

## Offene Entscheidungen (CEO)

| Nr | Frage | Empfehlung |
|---|---|---|
| E1 (CEO 2026-11-26: wie empfohlen) | Wer sieht die Kachel? | **Nur der CEO** (Rolle owner, wie OFC), weil Abo- und Umsatzzahlen drin stehen. Team spaeter per eigener Freigabe. |
| E2 (wie empfohlen) | Was heisst „Saison“ im Zeitraum-Filter? | **01.07. bis 30.06.**, die laufende Saison 2026/27 also ab 01.07.2026 (Daten ab 14.05.). |
| E3 (wie empfohlen) | Wo liegt das Archiv? | **NAS-Datei** `app_kennzahlen/log.jsonl` (Ereignis-Log wie `fanclub/`, nicht im Git, im naechtlichen Backup). Kein Supabase, damit die Zahlen nicht in eine weitere Cloud gehen. |
| E4 (wie empfohlen) | Meilenstein-Meldungen nur per Telegram oder zusaetzlich als To-do? | **Nur Telegram**; Stoerungen (401, zwei Fehlschlaege, kein frischer Lauf) zusaetzlich in der Glocke von LUNA-OS. |

## Etappen

### Etappe AK0: Zugang freigeben (CISO) und Token auf die NAS

- Status: deployt und verifiziert (2026-11-26, Erstabruf ok), umgesetzt (CISO-Pruefung 2026-11-26 durch den HoA, Auflagen im Code und per Test belegt; Token auf der NAS)
- Ziel / Scope: CISO-Pruefung der neuen festen Schnittstelle nach `AGENTS.md` 5.7:
  - nur diese eine Adresse, nur GET;
  - Token nur aus der Umgebung lesen, nie in Log, Fehlertext, Antwort, Datei oder Repo;
  - Zeitlimit beim Abruf;
  - nur TLS mit Zertifikatspruefung;
  - Antwort wird auf das Schema geprueft (Felder, Typen, Datumsformat), alles andere wird verworfen.
  
  Token in der **NAS**-`.env`: **erledigt 2026-11-26** (CEO, Readback `1`, Pruefsumme gleich), MACO470-Kopie entfernt.
- Nicht-Scope: Container-Neustart (folgt mit dem Deploy von AK1).
- Gate: Zugriffs-Policy-Zeile `app_kennzahlen` auf **FREIGEGEBEN (CISO, Auflagen)**, Aenderungshistorie ergaenzt.
- Verifikation: `ssh luna-nas "grep -c '^HANSERAUTISCH_LUNA_API_TOKEN=' /volume1/docker/ki-unternehmen/orchestrator/.env"`
  -> erwartet: `1`.
- Risiko / Rueckweg: Ein Token-Leck erlaubt nur das Lesen von Summen; der Widerruf laeuft ueber ein neues Token in der App
  (App-Sitzung) und das Entfernen der Zeile aus der `.env`.
- Abhaengig von: nichts. Aufwand: klein.

### Etappe AK1: Abruf und Archiv

- Status: deployt und verifiziert (2026-11-26, Erstabruf ok), umgesetzt 2026-11-26 (`orchestrator/core/app_kennzahlen.py`, Tests `test_app_kennzahlen.py`)
- Ziel / Scope: Neues Modul `orchestrator/core/app_kennzahlen.py`. Es macht Folgendes:
  - **Client:** Er liest das Token aus der Umgebung. Er teilt Zeitraeume in Abschnitte von hoechstens 400 Tagen und setzt
    `bis` nie nach heute (Berlin). Fehler behandelt er nach der Statustabelle; Fehlertexte enthalten nie das Token.
  - **Archiv:** NAS-Datei `app_kennzahlen/log.jsonl` (E3). Ein Wert wird nur angehaengt, wenn er neu ist oder sein `stand`
    neuer ist. Beim Lesen gewinnt je Schluessel der neueste `stand`. Jede Abfrage wird mit Zeitpunkt, Zeitraum, Status und
    Anzahl protokolliert, ohne Werte.
  - **Unbekannte Kennzahlen** werden gespeichert und als „unbekannt“ gezaehlt.
  - **Kennzahl-Katalog** (Teil B, Abschnitt 3) als feste Tabelle mit `ab`, Einheit und Anzeige-Text.
  - **Erstabruf** ab 2026-05-14; bei leerem Archiv holt der Lauf ihn selbst.
  - **CLI** `python -m orchestrator.core.app_kennzahlen --dry-run` zeigt nur Anzahl je Kennzahl, neu und aktualisiert,
    nie Werte.
  - **Doku:** Eintrag im Dienste-Register (`governance/dienste_register.py`, Schluessel-Name, Tarif gratis), Host und
    Speicher in `docs/datenfluesse.md` (doku-check-Bloecke), Eintrag im Wachtest `test_netz_wache.py`, Nachtrag
    `docs/datenschutz-ki-nutzung.md`, Verweis in `MONETARISIERUNG_ROADMAP.md` M5, `AGENTS.md` 7 (Ordner
    `app_kennzahlen/`), Speicher im Deploy ausgenommen und im Backup.
- Tests (mit Gegenproben, die bei falschem Code rot werden):
  - Ein aelterer `stand` ueberschreibt nicht, ein neuerer schon.
  - Bei 401 kein zweiter Abruf; 400 wird nicht wiederholt; bei 502 kommt ein Wiederholungsplan.
  - 401 Tage werden in zwei Abschnitte geteilt; `bis` wird auf heute (Berlin) begrenzt.
  - Das Token steht weder im Log noch im Fehlertext noch in der Ausnahme.
  - Eine unbekannte Kennzahl wird gespeichert.
  - Eine fehlende Zeile ergibt 0, vor `ab` dagegen „keine Daten“.
  - Eine kaputte Antwort (falsches Schema) wird verworfen.
- Gate: Test-Gate (Baseline `docs/bekannte-fehler.md`, kein neuer roter Test), Doku-Check gruen.
- Dry-Run: Tests mit einer nachgebauten Antwort im echten Format (Felder aus dem Lesetest B1). Gegen die echte Quelle
  gibt es keinen Probelauf vom MACO470 aus, weil das Token nur noch auf der NAS liegt. Erste echte Pruefung ist der erste
  Abruf auf der NAS -> erwartet: rund 2.255+ Zeilen ab 14.05., Status 200, nur Zaehlungen geprueft.
- Verifikation nach dem Deploy (NAS, nur Zaehlungen): Die Abruf-Protokollzeile meldet Status 200, und die Zeilenzahl im
  Archiv entspricht der `anzahl` der Antwort.
- Risiko / Rueckweg: Das Archiv ist nur additiv; ein Fehler betrifft nur die eigene Datei. Rueckweg: Abruf per Schalter
  `APP_KENNZAHLEN_AN=0` aus, die Datei bleibt.
- Abhaengig von: AK0. Aufwand: mittel. Risiko: niedrig.

### Etappe AK2: Kachel „Hanserautisch-App“ und Kontroll-Abgleich

- Status: deployt und verifiziert (2026-11-26, Erstabruf ok), umgesetzt 2026-11-26 (Hauptmenuepunkt „📱 App“, nur CEO; headless geprueft Rechner/iPad/iPhone, hell/dunkel)
- Ziel / Scope: LUNA-OS-Kachel, sichtbar nach E1. Inhalt:
  - **Oben:** Abo-Aequivalente gegen das Ziel 1.000, aktive Abos, MRR brutto, Registrierungen pro Tag und gesamt.
  - **Community:** Tipps je Art, Tippquote je Spieltag, Chatnachrichten pro Tag (Community/Freunde) und je Stunde,
    Check-ins je Methode, Freundschaften, Fangesaenge, Mitfahren, Stadionbewertungen, Lieblingsvereine.
  - **Geld:** Abo-Bewegungen, Umwandlung, auslaufende Geschenke.
  - **Betrieb:** Pushes je Status und Plattform, Push-Quote, offene Moderation samt Alter, Cron- und Function-Fehler,
    Datenbankgroesse, Datenstand (letzter `stand`, letzter Abruf).
  - **Zeitraeume:** 7 Tage, 30 Tage, Saison (E2), alles.
  - Hinweis „n unbekannte Kennzahlen gespeichert“.
  - Knopf **„Jetzt abrufen“** (nur der CEO).
  - **Kontroll-Abgleich:** Der CEO fuegt das Ergebnis der Kontrollabfrage (Teil B, Abschnitt 5) fuer einen Stichtag
    ein. LUNA vergleicht je Kennzahl Zeilenzahl und Summe deterministisch und zeigt ✅/❌. So sieht kein Modell die Werte.
  - Diagramme nach dem Dataviz-Verfahren; Rechner, iPad (820 px) und iPhone (402 px, Safe Areas).
- Gate: Test-Gate; eine Gegenprobe fuer den Abgleich (eine abweichende Summe wird ❌); headless geprueft auf Rechner,
  iPad und iPhone; nur der CEO hat Zugriff (Team-Rolle bekommt 403).
- Verifikation: `GET /api/app-kennzahlen/status` (nur Zaehlungen) -> erwartet: Archiv-Zeilen > 0, letzter Abruf 200.
- Risiko / Rueckweg: reine Anzeige; Rueckweg ist die Kachel ausblenden.
- Abhaengig von: AK1. Aufwand: mittel-gross.

### Etappe AK3: Taeglicher Lauf und Meldungen

- Status: deployt und verifiziert (2026-11-26, Erstabruf ok), umgesetzt 2026-11-26 (Thread `app_kennzahlen` in `luna-telegram`)
- Ziel / Scope: Zeitplan im Container `luna-telegram` (einziger Ort fuer Zeitplaene).
  - **Taeglicher Lauf** ab 06:30 Berlin: `von = gestern - 3`, `bis = gestern`. Verpasste Tage werden ab dem letzten
    gespeicherten Tag minus 3 nachgeholt.
  - **Wiederholung** nach 5, 15 und 45 Minuten bei 502.
  - **Telegram-Meldungen,** jede nur einmal je Anlass:
    - um 06:45 kein frischer `tagesabschluss_lauf` fuer gestern oder sein `stand` ist aelter als 30 Stunden;
    - zwei Fehlschlaege hintereinander oder ein 401;
    - `moderation_aeltester_stunden` ueber 24;
    - `cron_fehlschlaege` > 0 oder `function_fehler` > 5 an einem Tag;
    - Meilensteine: Abo-Aequivalente 100/250/500/750/1.000, jedes volle Tausend registrierter Konten.
  
  Die Meldungstexte entstehen im Code, nicht durch ein Modell, und kommen nicht in das Chat-Gedaechtnis.
- Gate: Test-Gate mit Gegenproben (Meldung nur einmal; 06:44 meldet nicht, 06:45 schon; Meilenstein 250 meldet beim
  Ueberschreiten, nicht taeglich). Die Zustellung wird beim Empfaenger geprueft (Telegram `typ:"sent"` im Outbox-Log).
- Verifikation: Am Tag nach dem Deploy zeigt das Abruf-Protokoll um 06:30 Berlin den Status 200 und den Zeitraum
  gestern-3 bis gestern.
- Risiko / Rueckweg: Zu viele Meldungen -> die Schwellen stehen im Code als Konstanten; Schalter `APP_KENNZAHLEN_AN=0`.
- Abhaengig von: AK1 (bevorzugt mit AK2 in einem Deploy). Aufwand: mittel.

### Etappe AK4: Abnahme

- Status: bestanden 2026-11-28 -- Stichtage 01.11., 15.11., 22.11. „Alle gleich“ (CEO 2026-11-26); Tageslauf am 27.11. und 28.11. jeweils 06:30 von selbst, Status 200, 0 verworfen, letzter Tag 27.11. (NAS, nur Zaehlungen); Meldungen einmalig (1 Meilenstein neu, 1 Function-Fehler).
- Gate (aus dem Auftrag):
  1. Der Erstabruf ab 2026-05-14 ist vollstaendig.
  2. Fuer drei Stichtage zeigt der Kontroll-Abgleich je Kennzahl dieselbe Zeilenzahl und Summe wie die
     Supabase-Kontrollabfrage (der CEO fuehrt sie aus und fuegt das Ergebnis in LUNA-OS ein).
  3. Der taegliche Abruf laeuft an zwei Tagen hintereinander von selbst; Claude Code prueft das am Stichtag mit Beleg.
  
  Dazu kommt die Sichtabnahme durch den CEO auf Rechner, iPad und iPhone.
- Nach dem Deploy wird sofort ein datiertes To-do „Roadmap: APP_KENNZAHLEN_ROADMAP.md“ angelegt (F4).

## Umsetzungsstand (2026-11-26)

- **CISO-Pruefung AK0 (HoA nach `AGENTS.md` 5.7):** Die Auflagen sind erfuellt und per Test belegt:
  - nur die eine Adresse, nur GET;
  - Token nur aus der Umgebung, nie in Fehlertext oder Ausnahme (Gegenprobe);
  - TLS mit Zertifikatspruefung, Zeitlimit 60 s;
  - Antwort-Schema geprueft, ungueltige Zeilen verworfen;
  - Eintrag im Wachtest `test_netz_wache.py`.
- **Datenschutz:** Meldungen mit `quelle=app_kennzahlen` gehen nicht in den Chat-Verlauf des Bots (der fuegte zugestellte
  Meldungen bisher als Kontext fuers Modell an), sind in `benachrichtigungen_zeigen`/`meldung_details` ausgeblendet und
  kommen nicht ins Morgen-Briefing. Kein Chat-Werkzeug fuer die Zahlen.
- **Gegenproben:** Sechs absichtliche Fehler machen die Tests rot:
  - Filter im Chat-Werkzeug entfernt;
  - Upsert ueberschreibt immer;
  - nach 401 wird wiederholt;
  - Meilensteine schon beim Erstabruf;
  - Ausnahmetext im Fehler;
  - Bot gibt die Meldung in den Chat.
- **Abweichung vom Plan:** Es gab keinen Dry-Run gegen die echte Quelle vom MACO470 aus, weil das Token nur auf der NAS
  liegt (Empfehlung der App-Sitzung). Erste echte Pruefung ist der Erstabruf nach dem Deploy (startet etwa 90 Sekunden
  nach dem Neustart von selbst, weil das Archiv leer ist).
- **Diagrammfarben:** Blau/Ocker/Magenta (hell `#2f6bff/#a16207/#be185d`, dunkel `#5b8bff/#d4a017/#e0619b`), hoechstens
  drei Reihen je Diagramm. OKLab-Abstand mindestens 8,7 auch bei simulierter Rot-, Gruen- und Blauschwaeche; Status-Farben
  bleiben frei. Der Validator des Dataviz-Skills war hier nicht lauffaehig (kein Node); die Pruefung wurde in Python
  nachgerechnet.

## Erweiterung: Live-Zahlen „Heute live“ (Auftrag 2026-11-26 abends)

### Auftrag

Uebergabe `LUNA_UEBERGABE_LIVE.md` aus der App-Entwicklung (Stand 2026-11-26, ohne Secret-Werte). Zusaetzlich zum
naechtlichen Tagesabruf holt LUNA alle 15 Minuten eine kleine Auswahl an Live-Zahlen und zeigt sie im Bereich „📱 App“ oben
als „Heute live“ mit der Uhrzeit des Stands. Gleiche Function, gleiches Token, neuer Parameter `art=live` (ohne `von`/`bis`).
Live-Werte sind vorlaeufig und gehoeren **nicht** in die Tageswerte.

### Analyse (Belege aus Code und Uebergabe)

- **Kein neuer Zugang, kein neuer Host:** dieselbe Adresse `…/functions/v1/luna-kennzahlen`, dasselbe Token
  `HANSERAUTISCH_LUNA_API_TOKEN` (NAS-`.env`), derselbe Abruf-Code (`core/app_kennzahlen.py` `abrufen`, Netz-Wache
  `_urlopen`). Die CISO-Freigabe vom 2026-11-26 deckt „nur GET an diese eine Adresse“ ab; neu ist nur der Takt.
- **Last:** 96 Abrufe je Tag (alle 15 Minuten), die Antwort hat wenige Dutzend Zeilen. Fuer NAS und Function unkritisch.
- **Wo der Lauf laeuft:** im bestehenden Minuten-Thread `app_kennzahlen` im Container `luna-telegram`; die Anzeige liest in
  `luna-os` die Ablage. Beide Container haben das Token in der Umgebung.
- **Ablage getrennt von den Tageswerten:**
  - `app_kennzahlen/live.json` enthaelt den letzten Live-Stand und wird bei jedem Abruf ersetzt.
  - Dazu kommt optional ein Tagesverlauf `app_kennzahlen/live_verlauf/<JJJJ-MM-TT>.jsonl`, aelter als 7 Tage wird geloescht
    (L3). Loeschen eigener, vorlaeufiger Zwischenwerte ist ein CEO-Tor (Loeschen von Daten) und wird mit dieser
    Roadmap ausdruecklich vorgelegt.
- **Meilensteine:** Die Schluessel bleiben dieselben wie beim Tagesabruf (`meilenstein:abo:<n>`, `meilenstein:reg:<n>`), damit
  nichts doppelt kommt. Fuer die Registrierten zaehlt live `registrierte_stand` (Profile jetzt) statt `registrierte_gesamt`.
- **Moderation ueber 24 Stunden** bleibt am Tagesabruf (sonst alle 15 Minuten).
- **Datenschutz unveraendert:** nur Summen; Meldungen `quelle=app_kennzahlen` gehen nicht in Chat-Verlauf, Chat-Werkzeuge
  oder Briefing; Abo- und Umsatzzahlen gehen an kein KI-Modell.

### Offene Entscheidungen (CEO)

| Nr | Frage | Empfehlung |
|---|---|---|
| L1 (wie empfohlen) | Wo stellt man den Takt ein? | **In LUNA-OS im Bereich App** (nur CEO), Standard 15 Minuten, erlaubt 5-60. Eine `.env`-Zeile braeuchte jedes Mal einen Neustart. |
| L2 (wie empfohlen) | Nach einem 401 ist der Live-Abruf angehalten. Wie geht es weiter? | **Knopf „Live wieder starten“** im Bereich App (nur CEO) plus Meldung per Telegram; der Tagesabruf behandelt 401 wie bisher. |
| L3 (wie empfohlen) | Tagesverlauf fuer die Kurve „Registrierungen heute“? | **Ja**, Dateien je Tag, nach 7 Tagen automatisch geloescht (nur diese eigenen Live-Zwischenwerte; die Tageswerte bleiben unberuehrt). |
| L4 (wie empfohlen) | 4 Fehlschlaege hintereinander: nur Telegram oder auch die Glocke? | **Beides**, wie bei den Tageswerten (E4): einmal melden, bis es wieder geht. |
| L5 (wie empfohlen) | Live-Abgleich fuer die Abnahme? | **Wie beim Kontroll-Abgleich:** Du fuegst das Ergebnis von `select * from public.luna_live_kennzahlen_v1();` in LUNA-OS ein, LUNA vergleicht je Kennzahl den Wert mit dem Live-Stand derselben Minute und zeigt ✅/❌. So sieht kein Modell die Zahlen. |
| L6 (wie empfohlen) | `anmeldungen_ohne_abschluss` in den Tageswerten? | **Ja**, als Momentaufnahme ab dem ersten Nachtlauf; in „Registrierte gesamt“ als zweite, gestrichelte Linie („ohne Profil“), sobald Daten da sind. |

### Antworten der App-Sitzung (2026-11-26, zu den Rueckfragen aus `LUNA_ANTWORT_LIVE.md`)

- **Vorschlag bestaetigt:**
  - Takt 15 Minuten, erlaubt 5-60, **nie unter 5**, kein paralleler zweiter Abruf;
  - bei Fehlern nicht sofort wiederholen, sondern beim naechsten Takt;
  - `live.json` getrennt von den Tageswerten; Fehlerverhalten, Anzeige und gestrichelte Linie wie vorgeschlagen.
- **`luna_live_kennzahlen_v1()`:**
  - Spalten in dieser Reihenfolge: `datum`, `kennzahl`, `dim1`, `dim2`, `wert`, `stand`; sortiert nach kennzahl, dim1,
    dim2.
  - `dim1`/`dim2` sind leere Zeichenketten, nie NULL (beim Kopieren leere Zelle; ein `NULL` wird wie leer behandelt).
  - Im Abgleich zaehlen nur kennzahl, dim1, dim2 und wert; eine Abweichung um 1 bei Zaehlern ist kein Fehler.
- **Antwortformat:** `ok`, `anzahl` und `zeilen` sind immer da; statt `von`/`bis` steht `"art": "live"`. Neu auch beim
  Tagesabruf: `"art": "tag"`. Zusaetzliche Felder muessen erlaubt sein; das tut `schema_pruefen` bereits, es prueft nur
  `ok` und `zeilen`.
- **Mitternacht:** Die Grenze ist Mitternacht Europe/Berlin. Danach kommt der neue Tag mit Zaehlern ab 0
  (`registrierungen` = 0, andere fehlen = 0); die Stand-Zahlen laufen ohne Sprung weiter.
- **Kosten:** kein Rate-Limit; jeder Abruf dauert 12-15 ms. 96 bzw. 288 Aufrufe am Tag sind im Tarif enthalten, keine
  Mehrkosten.
- **Meilensteine:** `registrierte_stand` ist richtig. Der Wert kann durch Kontoloeschungen sinken, deshalb jede Schwelle
  wirklich nur einmal melden, auch wenn der Wert kurz darunter und wieder darueber geht. Das ist bereits so: Der
  Meldungs-Vermerk je Schwelle bleibt bestehen; der Test in AK5 deckt den Fall ausdruecklich ab.

### Etappe AK5: Live-Abruf, Ablage und Meldungen

- Status: umgesetzt 2026-11-26 (`abrufen_live`, `live_lauf` im Minuten-Thread von `luna-telegram`, `live.json` + `live_verlauf/` mit Loeschen nach 7 Tagen, `live_einstellung.json` (Takt 5-60, Freigabe nach 401), Fehlerregeln, Meilensteine mit denselben Schluesseln, Glocke; Tests `test_app_kennzahlen_live.py` mit Gegenproben; nebenbei: beschaedigte Zeilen im Tages-Archiv werden uebersprungen)
- Ziel / Scope:
  - **Abruf:** `abrufen_live` mit `art=live`, gleiche Schutzregeln (Token nur aus der Umgebung, nie in Log oder Fehlertext,
    Schema-Pruefung, Zeitlimit). Takt nach L1 im bestehenden Minuten-Thread.
  - **Ablage:** `live.json` (ersetzt) und der Tagesverlauf nach L3 mit Loeschen nach 7 Tagen. Unbekannte Kennzahlen werden
    gespeichert; bei den heutigen Zaehlern ist eine fehlende Zeile 0.
  - **Fehler:**
    - 401 meldet sofort und haelt den Live-Abruf an (L2);
    - 502 und Netzfehler versucht LUNA beim naechsten Takt still erneut;
    - nach 4 Fehlschlaegen hintereinander gibt es eine Meldung (Telegram und Glocke, L4), bis es wieder geht.
  - **Meilensteine** aus den Live-Zahlen mit denselben Schluesseln (keine Dopplung).
  - **Doku:** Dienste-Register (Zweck), `docs/datenfluesse.md` (Speicher, Takt), Zugriffs-Policy (Takt), Backup-Liste
    bzw. `ohne-backup` fuer die Live-Dateien.
- Gate: Tests mit Gegenproben:
  - Live-Werte landen nie im Tages-Archiv;
  - der Takt wird eingehalten und ist nicht schneller als 5 Minuten;
  - nach 401 kein weiterer Abruf bis zur Freigabe;
  - 3 Fehlschlaege melden nichts, der 4. genau einmal, nach Erfolg ist die Sperre wieder offen;
  - ein Meilenstein kommt nicht doppelt (Tagesabruf und Live);
  - Verlauf aelter als 7 Tage wird geloescht, juengere Dateien bleiben;
  - das Token steht weder in Log noch in Datei.
- Verifikation (NAS, nur Zaehlungen): `GET /api/app-kennzahlen/live/status` -> erwartet: letzter Abruf 200, Alter unter 16
  Minuten, Zahl der Kennzahlen > 0.
- Risiko / Rueckweg: Schalter `APP_KENNZAHLEN_LIVE=0` stoppt nur den Live-Abruf; die Tageswerte laufen weiter.
- Aufwand: mittel.

### Etappe AK6: Anzeige „Heute live“, Live-Abgleich, neue Tageskennzahl

- Status: umgesetzt 2026-11-26 (Block „Heute live“ mit Stand, veraltet ab 45 Minuten, 9 Kacheln, „Anmeldungen ohne Abschluss“ mit Hinweis, Kurve „Registrierungen heute“, Takt und „Live wieder starten“, Live-Abgleich; Abschnitte „bis gestern“; `anmeldungen_ohne_abschluss` im Katalog, gestrichelte Linie; headless Rechner/iPhone)
- Ziel / Scope:
  - **Block „Heute live“** oben im Bereich App:
    - Zeile „Stand HH:MM“; ist der letzte erfolgreiche Abruf aelter als 45 Minuten, sind die Zahlen grau und als „veraltet“
      markiert.
    - Kacheln: Registrierte jetzt („+N heute“), Abo-Aequivalente gegen 1.000, aktive Abos, MRR brutto, neue Abos heute,
      Tipps heute, Check-ins heute, Chatnachrichten heute, offene Moderation.
    - Darunter klein „Anmeldungen ohne Abschluss: X ohne Profil, Y E-Mail unbestaetigt“ mit Hinweis (Supabase
      Authentication zaehlt Anmeldungen, LUNA zaehlt Profile).
    - Optional die Kurve „Registrierungen heute“ (L3).
  - **Bisherige Kacheln** sind beschriftet mit „bis gestern“.
  - **Einstellungen:** Takt (L1) und „Live wieder starten“ (L2).
  - **Live-Abgleich** (L5).
  - **Neue Tageskennzahl:** `anmeldungen_ohne_abschluss` in den Katalog, gestrichelte Linie in „Registrierte gesamt“ (L6).
  - **Geraete:** Rechner, iPad, iPhone, hell und dunkel.
- Gate: Tests mit Gegenproben (veraltet ab 45 Minuten; ❌ bei abweichendem Wert); headless Rechner/iPad/iPhone.
- Abhaengig von: AK5. Aufwand: mittel.

### Etappe AK7: Abnahme Live

- Gate (aus dem Auftrag):
  1. Der Live-Abgleich zur selben Minute zeigt je Kennzahl denselben Wert; kleine Abweichungen sind nur erlaubt, wenn genau
     dazwischen etwas dazukam.
  2. Der Live-Abruf laeuft einen Tag lang im Takt ohne Telegram-Flut. Claude Code prueft das Protokoll: rund 96 Abrufe,
     hoechstens eine Fehlermeldung.
  3. Sichtabnahme auf Rechner, iPad und iPhone.
- Nach dem Deploy wird sofort ein datiertes To-do angelegt (F4).

## Reihenfolge, Aufwand, Deploy

AK0 -> AK1 -> AK2 -> AK3, nach CEO-Go je Etappe am Stueck gebaut, dann **ein** Deploy mit einem Neustart beider
Container durch den CEO. Die Neuerstellung `docker compose up -d` ist noetig, weil ein neuer Speicher dazukommt und das
Token auf der NAS neu ist. Gesamtaufwand rund 1-2 Arbeitstage.

## Dokumentationspflichten

`projekt_changelog.md` (immer), Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (E1-E4, Ersatz
von M5-`luna_reader`), `docs/datenfluesse.md`, `governance/zugriffs-policy.md`, `governance/dienste_register.py`,
`docs/datenschutz-ki-nutzung.md`, `docs/bekannte-fehler.md` (Baseline, Funde), `AGENTS.md` Abschnitt 7.

## Definition of Done

AK4 bestanden und Sichtabnahme durch den CEO; danach traegt Claude Code den Status „abgeschlossen“ ein. Teil 2 ist
Folgethema (eigene Etappen nach App-Update 1.0.2 (12)).
