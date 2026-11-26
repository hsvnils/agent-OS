# Roadmap: Kennzahlen der Hanserautisch-App in LUNA-OS (Teil 1)

- Status: geplant
- Stand: 2026-11-26
- Arbeitsbranch: `ai/app-kennzahlen`
- Basiscommit: `fef5b17`
- Naechster Schritt: Roadmap liegt dem CEO vor; offene Entscheidungen E1-E4 beantworten, dann Go fuer AK0 (CISO-Pruefung und Token auf der NAS) und AK1.
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
- **Token:** liegt seit 2026-11-26 in `orchestrator/.env` auf dem **MACO470**, eingetragen vom CEO und ohne Wertanzeige
  geprueft. Die Zeitplaene laufen aber im Container `luna-telegram` und die Anzeige in `luna-os`, beide auf der **NAS**.
  Dort fehlt das Token noch (AK0, CEO).
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
| E1 | Wer sieht die Kachel? | **Nur der CEO** (Rolle owner, wie OFC), weil Abo- und Umsatzzahlen drin stehen. Team spaeter per eigener Freigabe. |
| E2 | Was heisst „Saison“ im Zeitraum-Filter? | **01.07. bis 30.06.**, die laufende Saison 2026/27 also ab 01.07.2026 (Daten ab 14.05.). |
| E3 | Wo liegt das Archiv? | **NAS-Datei** `app_kennzahlen/log.jsonl` (Ereignis-Log wie `fanclub/`, nicht im Git, im naechtlichen Backup). Kein Supabase, damit die Zahlen nicht in eine weitere Cloud gehen. |
| E4 | Meilenstein-Meldungen nur per Telegram oder zusaetzlich als To-do? | **Nur Telegram**; Stoerungen (401, zwei Fehlschlaege, kein frischer Lauf) zusaetzlich in der Glocke von LUNA-OS. |

## Etappen

### Etappe AK0: Zugang freigeben (CISO) und Token auf die NAS

- Status: geplant
- Ziel / Scope: CISO-Pruefung der neuen festen Schnittstelle nach `AGENTS.md` 5.7:
  - nur diese eine Adresse, nur GET;
  - Token nur aus der Umgebung lesen, nie in Log, Fehlertext, Antwort, Datei oder Repo;
  - Zeitlimit beim Abruf;
  - nur TLS mit Zertifikatspruefung;
  - Antwort wird auf das Schema geprueft (Felder, Typen, Datumsformat), alles andere wird verworfen.
  
  Der CEO traegt das Token in die **NAS**-`.env` ein (`/volume1/docker/ki-unternehmen/orchestrator/.env`); den Befehl
  ohne Wertanzeige liefert Claude Code. Die MACO470-Kopie bleibt fuer Entwicklung und Probe.
- Nicht-Scope: Container-Neustart (folgt mit dem Deploy von AK1).
- Gate: Zugriffs-Policy-Zeile `app_kennzahlen` auf **FREIGEGEBEN (CISO, Auflagen)**, Aenderungshistorie ergaenzt.
- Verifikation: `ssh luna-nas "grep -c '^HANSERAUTISCH_LUNA_API_TOKEN=' /volume1/docker/ki-unternehmen/orchestrator/.env"`
  -> erwartet: `1`.
- Risiko / Rueckweg: Ein Token-Leck erlaubt nur das Lesen von Summen; der Widerruf laeuft ueber ein neues Token in der App
  (App-Sitzung) und das Entfernen der Zeile aus der `.env`.
- Abhaengig von: nichts. Aufwand: klein.

### Etappe AK1: Abruf und Archiv

- Status: geplant
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
- Dry-Run: CLI `--dry-run` auf dem MACO470 gegen die echte Quelle -> erwartet: rund 2.255 Zeilen ab 14.05., 0 Fehler.
  Ausgegeben werden nur Zaehlungen.
- Verifikation nach dem Deploy (NAS, nur Zaehlungen): Die Abruf-Protokollzeile meldet Status 200, und die Zeilenzahl im
  Archiv entspricht der `anzahl` der Antwort.
- Risiko / Rueckweg: Das Archiv ist nur additiv; ein Fehler betrifft nur die eigene Datei. Rueckweg: Abruf per Schalter
  `APP_KENNZAHLEN_AN=0` aus, die Datei bleibt.
- Abhaengig von: AK0. Aufwand: mittel. Risiko: niedrig.

### Etappe AK2: Kachel „Hanserautisch-App“ und Kontroll-Abgleich

- Status: geplant
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

- Status: geplant
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

- Status: geplant
- Gate (aus dem Auftrag):
  1. Der Erstabruf ab 2026-05-14 ist vollstaendig.
  2. Fuer drei Stichtage zeigt der Kontroll-Abgleich je Kennzahl dieselbe Zeilenzahl und Summe wie die
     Supabase-Kontrollabfrage (der CEO fuehrt sie aus und fuegt das Ergebnis in LUNA-OS ein).
  3. Der taegliche Abruf laeuft an zwei Tagen hintereinander von selbst; Claude Code prueft das am Stichtag mit Beleg.
  
  Dazu kommt die Sichtabnahme durch den CEO auf Rechner, iPad und iPhone.
- Nach dem Deploy wird sofort ein datiertes To-do „Roadmap: APP_KENNZAHLEN_ROADMAP.md“ angelegt (F4).

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
