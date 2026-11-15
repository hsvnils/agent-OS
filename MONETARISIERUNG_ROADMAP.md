# Roadmap: LUNA-OS als Steuerzentrale fuer Monetarisierung und Weg zur Selbststaendigkeit

- Status: in Umsetzung
- Stand: 2026-11-15
- Arbeitsbranch: `ai/plan-monetarisierung`
- Basiscommit: `a048c2d`
- Naechster Schritt: M8 umgesetzt auf `ai/monetarisierung-m8` -- CEO-Freigabe fuer Merge und Deploy; danach Kneipen-Formate
  im Live-Katalog anlegen (Preise = CEO-Entscheidung, offene Punkte A16); Gate M8 mit der ersten echten Kneipe. Uebrig: M5 (L4b, ab
  01.01.2027), M7 (ab Februar 2027).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-11-14)

„Am Ende will ich das alles im LUNA-OS sehen und damit arbeiten koennen. LUNA soll unser zentrales Tool sein." Dazu gehoeren
Einnahmen **je Saeule**, Follower, Reichweiten und App-Nutzerzahlen mit Verlauf, Meilensteine mit Kontinuitaet, Posting-Rhythmus je
Plattform und Erinnerungen an alles, was Menschen regelmaessig liefern muessen.

Der inhaltliche Plan (mit echten Zahlen) liegt vertraulich in `strategie/monetarisierungsplan-entwurf.md` und
`strategie/weg-zur-selbststaendigkeit.xmind` (nicht im Git, oeffentliches Repo). Diese Roadmap beschreibt nur die Technik.

## Saeulen (verbindliche Gliederung, CEO 2026-11-14)

S1 Kooperationen (inkl. App-Werbeflaechen, die eine Marke bucht) · S2 Plattform-Monetarisierung (S2a Facebook, S2b TikTok,
S2c YouTube, S2d Instagram) · S3 Fan-App (S3a Anker-Crew-Abos, S3b Kneipen-Listung) · S4 Affiliates · S5 Merch ·
S6 Auftragsproduktion. Jede Auswertung zeigt die Saeulen getrennt, Summen nur zusaetzlich.

## Analyse (read-only, 2026-11-14)

| Bereich | Heute in LUNA-OS | Nachweis | Luecke |
|---|---|---|---|
| Einnahmen | Kassenbuch, Rechnungen, Gutschriften mit Monatsauswertung, Kleinunternehmer-Waechter | `orchestrator/core/finanzen.py:296`, `plattform.py:105`, `rechnungen.py:177` | Einnahmen nur `umsatz`/`anlage_abgang`, keine Saeule (`eingangsbelege.py:55`) |
| Zeit | Projektzeiten, Zeiterfassung | `buchhaltung/zeiterfassung.json` (NAS) | Stunden ohne Saeule |
| Reichweite | Instagram-Insights mit Monatshistorie, nur als Chat-Werkzeug | `social_kit.py:53`, `:122`, `hoa_tools.py:367` | keine Ansicht, kein Facebook/TikTok/YouTube |
| Kampagnen-Kennzahlen | je Kundenauftrag, Screenshot-Auslesen | `postings.py:172`, `kennzahlen_lesen.py` | nicht fuer eigene Kanaele |
| Ziele | Plan/Ist nur je Auftrag | `postings.py:274` | keine Firmenziele, keine Gates |
| Erinnerungen | einmalige To-dos mit Telegram | `aufgaben.py:154` | keine Wiederholung (`TODOS_ROADMAP.md:48` Nicht-Scope) |
| App | nichts | -- | Kennzahlen, Store-Abrechnungen |

**Fan-App (Angaben der App-Sitzung, 2026-11-14):** eigenes Supabase-Projekt (Frankfurt), Abos direkt ueber StoreKit 2 und Play
Billing in Tabelle `subscriptions`; kein Analytics-SDK; Installationen nur in App Store Connect/Play Console. Fuer LUNA ist in
der App-Roadmap (L4b, geplant bis 20.11.) eine Rolle `luna_reader` vorgesehen, die **nur** die Funktion
`luna.abo_kennzahlen(von, bis)` ausfuehren darf (Summen, nie Konten). Abo-Zahlen gibt es erst ab 01.01.2027.

## Scope

Saeulen-Zuordnung, Plan- und Gate-Modell, Kennzahlen-Erfassung (Schnittstelle, CSV, Screenshot), Posting-Rhythmus,
wiederkehrende Erinnerungen, Import von Store-Abrechnungen, lesender Abruf der App-Summen, Ansichten fuer Rechner, iPad und iPhone.

## Nicht-Scope (nur mit eigener CEO-Freigabe)

- **Aenderungen am App-Projekt** (Supabase der App, App-Code, Store-Konsolen): LUNA liest hoechstens ueber `luna_reader`.
  Kneipen-Listungen (`listed_until`) traegt der Betreiber in der App selbst ein; LUNA erinnert nur.
- **Abo-Kennzahlen der App gehen an kein Sprachmodell** und bekommen kein Chat-Werkzeug (`docs/datenschutz-ki-nutzung.md`);
  Anzeige und Rechnung nur deterministisch im Code.
- Neue Zugaenge (Facebook-Seiten-Insights, App-Datenbank, Store-APIs): CISO-Freigabe, Passwoerter setzt der CEO selbst in die `.env`.
- Korrektur des Kleinunternehmer-Waechters (BF-95): erst nach Steuerberater, eigene Freigabe.
- Automatisches Posten, Werbebuchungen, kostenpflichtige Analyse-Dienste (CEO-Tor).
- Schutzbereiche laut `governance/roadmap-workflow.md` B4.

## Etappen

Reihenfolge: M1 -> M2 sind das Fundament. M3, M4 und M6 sind unabhaengig danach. M5 braucht L4b der App und Daten ab 01.01.2027.
M7 braucht die erste Store-Abrechnung (Anfang Februar 2027). M8 kann jederzeit.

### M1 Saeulen fuer Einnahmen und Stunden (mittel, Risiko niedrig) -- umgesetzt 2026-11-14, gemergt (Deploy durch CEO, Sichtabnahme gesammelt am Ende)
- **Stand:** `orchestrator/core/saeulen.py`, Reiter Finanzen -> Saeulen, `GET /api/finanzen/saeulen`,
  `POST /api/finanzen/saeulen/zuordnen|stunden`, Ereignisse `saeule_zugeordnet`/`saeule_stunden`; 8 Tests mit Gegenprobe
  (`orchestrator/tests/test_saeulen.py`). Probe auf einer Lesekopie der Kette: Summe der Saeulen = 3.026,08 EUR = Einnahmen 2026.
  Stunden ohne Auftrag als Schaetzung je Monat/Person/Saeule (die Zeiterfassung verlangt einen Auftrag).
- **Ziel:** Jede Einnahme (Rechnung, Gutschrift, Eigenbeleg) und jede Projektzeit bekommt eine Saeule; Vorschlag per Regel
  (Gegenpartei/Text), Bestaetigung durch Menschen. Einmalige Zuordnung der Bestandsdaten 2026.
- **Anzeige:** Finanzen -> Saeulen: Monat und Jahr je Saeule mit Deckungsbeitrag, Stunden und Euro je Stunde; Summe zusaetzlich.
- **Umkehrbar:** Saeule ist ein additives Feld im Kassenbuch-Ereignis; ohne Feld = „nicht zugeordnet".
- **Gate:** Tests mit Gegenprobe (unbekannte Gegenpartei bleibt unzugeordnet); Summe aller Saeulen = bisheriger Umsatz;
  CEO-Sichtabnahme auf Rechner und iPhone.

### M2 Plan, Meilensteine und Ampel (mittel, Risiko niedrig) -- live 2026-11-14, Plan-Vorlage 0.4 eingespielt (Sichtabnahme am Ende)
- **Stand:** `orchestrator/core/plan.py` (Plan als Ereignis `plan_gespeichert`, Regeln in_folge/schnitt/x_von_y mit Formeln wie
  `2*L_nils`, Ampel, Kooperationen Soll/Ist), `Saeulen.monatsreihe`, Reiter Finanzen -> Plan mit Formular und Verlauf,
  `GET/POST /api/finanzen/plan`, `POST /api/finanzen/plan/kriterium`; 10 Tests inkl. Gegenprobe 5+1 Monate.
  Grenze: Fixkosten sind ein Wert fuer alle Gates; Anteils-Kriterien (groesste Saeule, Plattform, wiederkehrend) vorerst zum Abhaken.
- **Ziel:** Planmodell mit Ersatzbedarf E und Netto-Luecke L je Person, Annahmen (Ø Kooperation, Fixkosten), Saeulenziele je
  Gate, Gate-Leiter G0-G6 mit Kontinuitaetsregeln (z. B. 6 Monate in Folge, 9 von 12), Ampel je Saeule; **Kooperationen Soll/Ist**
  (Anzahl und Euro) je Monat. Alles im LUNA-OS bearbeitbar, Aenderungen mit Verlauf.
- **Gate:** Tests rechnen die Kontinuitaet nach (5 gute Monate + 1 schlechter = nicht erreicht); Gegenprobe; Sichtabnahme.

### M3 Reichweiten und Follower je Plattform (mittel, Risiko mittel) -- umgesetzt 2026-11-14, gemergt und deployt 2026-11-15
- **Stand:** `orchestrator/core/reichweite.py` (Speicher `reichweite/log.jsonl`, Wochenwerte je Plattform, CSV-Import mit
  Vorschau und Spaltenzuordnung, Tagesreichweite wird nicht addiert, Bruchmarke Meta 15.06.2026), Instagram automatisch montags
  (Bot, vorhandener Zugang) und per Knopf, LUNA-OS Content & Collabs -> Reichweiten (Follower je Plattform mit Verlauf, Luecken,
  Wochentabelle, Eingabe von Hand, CSV-Import); 9 Tests inkl. Gegenproben. **Offen:** Kalibrierung mit echten Exporten (Gate);
  Facebook-Seite ueber die Schnittstelle braucht einen neuen Zugang (Seiten-Token mit `read_insights`) = CISO-Freigabe.
- **Ziel:** Woechentliche Kennzahlen je Plattform mit Verlauf und Diagramm: Follower, Reichweite, Aufrufe, Interaktionen,
  Shares, Saves. Wege: Instagram automatisch (vorhanden); Facebook-Seite ueber die Meta-Schnittstelle (`read_insights`,
  `pages_read_engagement`, CISO-Freigabe); CSV-Import aus Business Suite, TikTok Studio und YouTube Studio; Screenshot als Rueckfall.
- **Achtung:** Meta hat 2025/2026 Metriken umgestellt (`views` statt `impressions`); Zeitreihen werden mit Bruchmarke gefuehrt.
- **Gate:** Import echter Exporte ergibt dieselben Werte wie die Konsole (Stichprobe je Plattform); Gegenprobe mit kaputter CSV.

### M4 Posting-Rhythmus Soll/Ist (klein, Risiko niedrig) -- umgesetzt 2026-11-15, gemergt und deployt 2026-11-15
- **Stand:** `orchestrator/core/posting_rhythmus.py`: Soll je Plattform und Format als Spanne je Woche (Startwerte aus dem Skill,
  Aenderung gilt ab der laufenden Woche, Ereignis `soll` im Reichweiten-Log); Ist: Instagram taeglich aus der Medienliste des
  eigenen Kontos (gleiche Schnittstelle und gleicher Zugang wie M3, Zeitpunkte in Europe/Berlin), Facebook eingetragen oder
  mindestens die von LUNA geposteten Reels, TikTok/YouTube von Hand (neue Metriken `beitraege_kurz`, `beitraege_lang`);
  Briefing dienstags (Vorwoche unter Soll) und mittwochs bis samstags (automatisch gezaehlt und hinter dem Wochen-Tempo);
  LUNA-OS Reichweiten -> Kachel „Posting-Rhythmus“ mit 8-Wochen-Verlauf und Soll-Bearbeitung, `POST /api/reichweite/soll`.
  9 Tests inkl. Gegenprobe (Zaehlung nach UTC statt Berlin wird rot).
- **Ziel:** Soll je Plattform und Woche (Startwerte aus Skill `kanal-wachstum`, anpassbar), Ist aus Instagram-Schnittstelle und
  Importen; Hinweis im Briefing, wo nachzulegen ist (z. B. TikTok-Videos ueber 1 Minute fuer Creator Rewards).
- **Gate:** Ist-Zaehlung stimmt mit einer Stichwoche ueberein.

### M5 App-Kennzahlen (mittel, Risiko mittel; braucht L4b und Daten ab 01.01.2027)
- **Ziel:** Taeglicher Abruf von `luna.abo_kennzahlen(von, bis)` ueber den Session-Pooler mit TLS; Anzeige aktive Abos
  (Monat/Jahr, Store), Neu, Kuendigungen, Konten, aktive Push-Geraete, Tippspiel-Teilnehmer; dazu Installationen aus
  Store-Exporten. Ziel „1.000 Abo-Aequivalente bis 27.11.2027" als Kurve.
- **Datenschutz:** nur Summen, kein Chat-Werkzeug, kein Sprachmodell. Neue Verbindung in `docs/datenfluesse.md`.
- **Gate:** Readback gegen App Store Connect und Play Console fuer einen Stichtag; Verbindung lehnt Tabellenzugriff ab (Gegenprobe).

### M6 Wiederkehrende Erinnerungen (mittel, Risiko niedrig) -- umgesetzt 2026-11-14, gemergt
- **Stand:** To-dos mit `wiederholung` (woechentlich/monatlich/quartalsweise/jaehrlich, `serie`, `naechste`): Erledigen legt
  genau einen Nachfolger an (Erinnerung mit gleichem Abstand, Kalender mit); Vorlagen fuer Datenlieferungen
  (`orchestrator/core/daten_rhythmus.py`, `GET/POST /api/aufgaben/vorlagen`, Auswahl durch den CEO); Teilzeit-Antrag: Tageslauf
  05:00 legt je Brueckenjob-Gate einmal ein To-do an, sobald die „in Folge“-Regel zur Haelfte steht; Chat-Werkzeug
  `todo_anlegen` mit `wiederholung`. 10 Tests inkl. Gegenprobe. Kneipen-Enddatum folgt mit M8 (braucht App-Daten).
- **Ziel:** Wiederholungen fuer To-dos (woechentlich, monatlich, quartalsweise) mit Telegram-Erinnerung: Reichweiten-Export
  montags, Abrechnungen bis zum 5., Quartalsdaten, Kneipen-Listung verlaengern vor `listed_until`, Teilzeit-Antrag 3 Monate vor
  einem Brueckenjob-Gate.
- **Gate:** Erinnerung kommt beim Empfaenger an (Telegram `typ:"sent"`), Erledigen erzeugt den naechsten Termin; Gegenprobe.

### M7 Store-Abrechnungen (klein, Risiko mittel; ab Februar 2027)
- **Ziel:** Import der monatlichen Financial Reports (App Store Connect) und Earnings (Google Play) als Einnahmen S3a, mit
  Kennzeichnung „Leistungsort Ausland" fuer die spaetere Waechter-Korrektur (BF-95).
- **Gate:** Summe je Monat = Auszahlung laut Bank; Gegenprobe mit Rueckbuchung.

### M8 Kneipen als Kunden (klein, Risiko niedrig) -- umgesetzt 2026-11-15
- **Stand:** `orchestrator/core/kneipen.py`: Listungen werden aus den festgeschriebenen Rechnungen abgeleitet (Positionen
  `kneipe_monat`/`kneipe_saison` oder Text „Spieltags-Partner“/„Kneipen-Listung“; Zeitraum = Leistungszeitraum, sonst Monate bzw.
  30.06. am Saisonende; Storno nimmt sie heraus) -- kein eigener Speicher. Beim Festschreiben zwei To-dos mit Telegram-Erinnerung:
  „in der App bis … listen“ und 14 Tage vor Ablauf „Verlaengerung anbieten“ (je Rechnung einmal). Finanzen -> Reiter „Kneipen“
  (`GET /api/finanzen/kneipen`), Katalog-Standard „Kneipen (Fan-App)“, Kneipen-Formate in der Marken-Preisliste nicht vorausgewaehlt,
  Saeulen-Regel S3b erkennt „Spieltags-Partner“. 6 Tests inkl. Gegenproben (Storno, nur einmal). Live-Katalog unveraendert (A16).
- **Ziel:** Kneipen-Listung als Katalogposition (Monat und Saisonpaket), Rechnung ueber LUNA, Liste aktiver und auslaufender
  Listungen mit Erinnerung, das Enddatum in der App zu setzen.
- **Gate:** Testkneipe von Angebot bis Rechnung; Erinnerung kommt an.

## Pruefung je Etappe

Tests in `orchestrator/tests` mit Gegenprobe, `scripts/doku_check.py` gruen, Anzeige auf Rechner, iPad (820 px) und iPhone
(402 x 874, Safe Areas) geprueft, CEO-Sichtabnahme. Deploy nur nach eigener Freigabe (NAS-Sync, Neustart `luna-os`/`luna-telegram`).

## Dokumentationspflicht

`projekt_changelog.md` immer; Status hier; `ROADMAP.md`; `docs/datenfluesse.md` (M3, M5, M7); `docs/entscheidungs-register.md`;
`docs/bekannte-fehler.md`; `docs/datenschutz-ki-nutzung.md` (M5).

## Definition of Done

Alle Saeulen, Gates, Reichweiten, App-Kennzahlen und Erinnerungen sind im LUNA-OS sichtbar und bedienbar; der Monatsbericht
zeigt je Saeule Plan/Ist und den Stand auf der Gate-Leiter. Der CEO nimmt ab.
