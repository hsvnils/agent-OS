# Roadmap: Frontdesk/Backoffice — Gemini spricht, das lokale LLM arbeitet im Hintergrund

- Status: in Umsetzung
- Stand: 2026-09-26
- Arbeitsbranch: `ai/frontdesk-backoffice`
- Basiscommit: `ec1173c`
- Naechster Schritt: 2026-09-28 Morgen-Briefing pruefen (Nacht-Jobs 02:00/03:00/04:00 lokal? Meldungen gebuendelt?), dann
  7 Tage Beobachtung (Etappe 5).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO-Idee 2026-09-26)

**Frontdesk:** Gemini (schnell, Gratis-Tier) spricht mit dem CEO in Telegram — versteht, fragt nach, erledigt Schnelles
(Kalender, Mails lesen, Status) und nimmt groessere Aufgaben als **Auftrag** an („Auftrag #A12 angelegt, ich melde mich").
**Backoffice:** Das lokale LLM auf dem MACO470 arbeitet die Auftraege **nacheinander im Hintergrund** ab — langsam ist
ok, nachts ist ok — und meldet das Ergebnis per Telegram. Wirkung: kein Warten im Chat, keine API-Kosten, das lokale
Modell belastet den MACO470 nur, wenn Arbeit ansteht.

## Register und bekannte Fehler (B3)

- Register: Idee Frontdesk/Backoffice (SPAETER/OPTIONAL, 2026-09-26); Gemini-Gratis als Chat-Standard (BESCHLOSSEN);
  `qwen3:30b-a3b` auf dem MACO470 VERWORFEN (RAM), `qwen3:14b` ZURUECKGESTELLT (Zeichensalat); Werkzeugauswahl live.
- Bekannte Fehler: BF-22 (RAM: ~12,7 GB Grundlast, 30B zu gross), BF-23 (14B-Zeichensalat, vermutlich KV-Kompression
  + Flash-Attention + Prompt-Cache), BF-25 (Gemini behauptet Erledigungen ohne Werkzeug), BF-21 (verwaistes Modell nach
  Ollama-Neustart), BF-02 (MACO470 nach unbeaufsichtigtem Neustart tot).

## Analyse (Belege, 2026-09-26)

- **Keine allgemeine Auftrags-Warteschlange im Bot.** `recherche_beauftragen` (`core/hoa_tools.py:602`) legt ein Ticket
  an, recherchiert aber **synchron** im selben Aufruf. Hintergrund-Ablaeufe gibt es nur als feste Zeitplaene
  (CFO 03:00, Content 07:00, Self-Dev 09:00 — `docs/datenfluesse.md` Abschnitt 4).
- **Vorhandene Bausteine:** Outbox fuer proaktive Meldungen (`core/notifications.py`, `enqueue`, Zustellung im
  Bot-Hauptloop, Dedup); Antraege-Store; `FallbackBackend` mit `LOCAL_LLM_FACHAGENTEN` (Text ohne Werkzeuge, lokal
  zuerst — gebaut, nicht aktiv); Cutter-Muster: Warteschlange auf der NAS + Worker auf dem MACO470 ueber die LUNA-OS-API
  (`cutter/luna_bridge.py`).
- **Backoffice-Aufgaben brauchen keine 98 Werkzeuge:** Zusammenfassen, Entwerfen, Bewerten sind Text-Aufgaben -> kleiner
  Kontext (4k-8k statt 32k) -> deutlich weniger RAM fuer den Kontext. Das macht `qwen3:14b` (9,3 GB) realistisch; 30B
  bleibt wegen der Gewichte (18,6 GB) bei ~17 GB verfuegbar zu gross (BF-22).
- **RAM-Waechter:** Der NAS-Bot sieht den Speicher des MACO470 nicht; ein Worker **auf** dem MACO470 koennte vor dem
  Laden pruefen, ob genug frei ist (Messung per PowerShell wie in dieser Analyse).

## Entscheidungen (CEO, 2026-09-26 — alle drei Vorschlaege uebernommen)

- **Aufgaben:** auf ausdruecklichen Wunsch („bis morgen", „im Hintergrund", „ausfuehrlich") **und** wenn der Frontdesk
  die Aufgabe als gross einstuft (Recherche-Zusammenfassungen, Entwuerfe, Analysen, Antrags-Bewertungen). Schnelles
  bleibt sofort im Chat. Geld/Recht/Oeffentlichkeit: nur Entwuerfe.
- **Zeitfenster:** sofort, wenn der MACO470 genug RAM frei hat (Waechter vor dem Laden), sonst 01:00-06:00; Modell nach
  jedem Stapel entladen.
- **Meldung:** tagsueber jedes Ergebnis einzeln per Telegram (kurz + „Details: #Axx"), nachts Erledigtes gebuendelt im
  Morgen-Briefing.

## Entscheidungen (Vorschlaege, Stand der Planung)

1. **Welche Aufgaben gehen ins Backoffice?** Vorschlag: auf ausdruecklichen Wunsch („bis morgen", „im Hintergrund",
   „ausfuehrlich") oder wenn der Frontdesk die Aufgabe als gross einstuft — z. B. Recherche-Zusammenfassungen, Entwuerfe
   (Mail, Content, Konzept), Antrags-Bewertungen, Analysen. Alles mit Geld/Recht/Oeffentlichkeit bleibt CEO-Tor:
   das Backoffice liefert nur **Entwuerfe**.
2. **Wann darf das Backoffice das Modell laden?** Vorschlag: sofort, wenn der MACO470 genug frei hat (RAM-Waechter),
   sonst im Nachtfenster 01:00-06:00; das Modell nach jedem Stapel entladen.
3. **Wie meldet es sich?** Vorschlag: jedes fertige Ergebnis einzeln per Telegram (kurz + „Details: #A12"), nachts
   erledigte gebuendelt im Morgen-Briefing.

## Gegenpruefung und Datenschutz (CEO 2026-09-27)

- **Stufe 1** Entwurf lokal (immer, 0 EUR) · **Stufe 2** Gemini liest Bewertungen/Analysen gegen und ergaenzt (0 EUR,
  Gratis-Tier) · **Stufe 3** Vertiefung auf CEO-Wunsch (Recherche + Gemini; **Claude spaeter als eigenes CEO-Tor**:
  neuer Schluessel, Guthaben, Budgetgrenze).
- Messung 2026-09-27 01:39: waehrend einer Inferenz hatten Ollama/`llama-server` **nur lokale Verbindungen**
  (4 Momentaufnahmen). Modelle sind reine Gewichtsdateien; ins Netz koennte nur Ollama selbst (Modell-Downloads,
  Update-Pruefung). Firewall-Sperre fuer Ollama-Ausgang: **vorerst nicht** (CEO). Cloud-Stufen (Gemini/Claude) geben
  Inhalte nach aussen — beim Gemini-Gratis-Tier ggf. zur Produktverbesserung (Bedingungen vor Ausbau pruefen).

## Scope

Auftrags-Warteschlange, Backoffice-Worker mit RAM-Waechter und Zeitfenster, Frontdesk-Werkzeuge (Auftrag erteilen,
Status), Regel gegen falsche Erledigungs-Behauptungen, Plausibilitaetsfilter fuer lokale Ergebnisse, Meldung per Outbox.

## Nicht-Scope

- Werkzeug-Aufrufe durch das Backoffice (es arbeitet mit Text; Werkzeuge bleiben beim Frontdesk) — spaeter moeglich
- Execution/Code-Umsetzung (Claude-CLI), Vision/Video
- Aenderung der CEO-Tore; Posten/Senden bleibt freigabepflichtig
- Schutzbereiche laut `governance/roadmap-workflow.md` B4

## Etappen

### Etappe 1: Backoffice-Modell bestimmen (Messung)

- Status: **verifiziert** (CEO 2026-09-27: `qwen3:14b` als Backoffice-Modell akzeptiert, mit besseren Anweisungen —
  Ich-Form als Nils, nur Deutsch, Bewertungsvorlagen — und Gemini als Gegenleser); gemessen 2026-09-26 23:22-23:41 — `qwen3:14b`, native Ollama-API,
  `num_ctx` 8192 je Anfrage (keine Windows-Aenderung), ohne Werkzeuge, Server weiter mit Flash-Attention + KV `q8_0`.
  9 Auftraege (Recherche zusammenfassen, Mail-Entwurf, Antrag bewerten, je 3x): **kein Zeichensalat, keine
  Wiederholungsschleife** (BF-23 trat hier nicht auf); 64-203 s je Auftrag, ~7 Tok/s; Modell 9,7 GB komplett auf der
  Grafik; Windows verfuegbar **min 3,1 GB, Mittel 4,3 GB** (59 Messungen, keine Dauer-Auslagerung).
  Qualitaet: Recherche-Zusammenfassung inhaltlich treu, ein wichtiger Punkt fehlte; Mail korrekt, aber in 3. Person
  („Nils ist auf Dienstreise") statt aus Sicht des CEO; Antrags-Bewertung knapp und oberflaechlich, einmal mit englischen
  Brocken („Approve", „Timeliness"). Automatische Pruefung: 1 Fehlalarm („kaum Deutsch" bei knappen Stichpunkten).
- Uebernommen: Re-Test lokaler Modelle aus `WERKZEUGAUSWAHL_ROADMAP.md` Etappe 4 und Etappe 2 aus
  `LOKALES_LLM_ROADMAP.md` (beide abgeschlossen/verschoben am 2026-09-26).
- Ziel / Scope: `qwen3:14b` fuer **Text-Aufgaben** ohne Werkzeugliste messen — mit und ohne KV-Kompression/Flash-Attention
  (BF-23 eingrenzen), Kontext 8k; drei typische Auftraege (Recherche zusammenfassen, Mail-Entwurf, Antrag bewerten),
  je 3 Laeufe; RAM-Verlauf ueber >= 15 min; Plausibilitaet (Wiederholungen, Zeichensalat, Sprache).
- Gate: 9/9 brauchbare Ergebnisse (CEO beurteilt 3 davon), Windows dauerhaft >= 3 GB verfuegbar, kein Zeichensalat.
- Verifikation: Messprotokoll mit RAM-Verlauf; Stichprobe dem CEO vorgelegt.
- Dry-Run: Messung nur auf dem MACO470, keine Live-Daten.
- Risiko / Rueckweg: Windows-Einstellungen (KV/Flash-Attention) aendern den Chat nicht (lokal pausiert); zurueck per
  Umgebungsvariable.
- Abhaengig von: Entscheidungen · Aufwand: klein · Risiko: niedrig
- Freigaben: Etappe; Windows-Einstellungen (CEO).

### Etappe 2: Auftrags-Warteschlange + Backoffice-Worker

- Status: **verifiziert** (2026-09-27 13:06) — Nachtweg (echter Worker, Briefing 08:02 zugestellt) und Tagweg (Einzelmeldung
  13:01 beim CEO angekommen, Abruf per „zeig #5c68" und „zeig Auftrag #a59b" korrekt; Screenshot CEO) bestanden.
  `backoffice/log.jsonl`), LUNA-OS `/api/backoffice/*` (Modul administration; Meldung tagsueber einzeln ueber die Outbox
  mit vollem Ergebnis als Detail, 01-06 Uhr nur Briefing), Morgen-Briefing-Abschnitt, Werkzeug `auftrag_details`,
  `backoffice/worker.py` (RAM-Waechter per PowerShell — funktioniert auch aus systemd, gemessen —, Anweisungen je Art,
  Plausibilitaetsfilter + 1 Wiederholung, Gemini-Gegenlesen fuer Bewertung/Analyse, Entladen nach dem Stapel),
  `deploy/backoffice-worker.service`. Neuer Store in Deploy-Schutz, Backup, `.gitignore`, Datenfluesse (Doku-Check hat
  die Luecke gemeldet). Tests: 20 neue + erweiterter Namens-Test (alle Funktionen in Bot und Web-App; fand die
  Fehlerklasse „fehlender Import im except" — Gegenprobe mit `timedelta` rot); Suite 854 passed / 0 failed.
- **Probelauf Ende-zu-Ende (2026-09-27 02:01, MACO470, Test-App + echter Worker + echtes Modell + echtes Gemini, keine
  Live-Daten):** 3/3 fertig in 314 s, Modell danach entladen, nachts korrekt keine Einzelmeldung. Qualitaet mit neuen
  Anweisungen besser: Mail in Ich-Form mit Unterschrift, Bewertung mit allen 7 Pflichtpunkten, Gemini-Zweitmeinung
  kritisch und hilfreich; Zusammenfassung liess erneut einen wichtigen Punkt weg (Tippfehler „unterstüzt").
- **Live-Test Nachtweg (2026-09-27 02:27, echte NAS + echter Dienst):** Test-Auftrag `#d868` (Mail-Entwurf) nach 17 s
  abgeholt, nach 62 s `fertig`, Modell entladen, `meldung: briefing` (keine Nacht-Nachricht). **Qualitaetsmangel:** das
  Modell erfand ein Datum mit falschem Jahr („Freitag, den 15.11.2024") und verdrehte die Aussage („sind hochgeladen"
  statt „lade bis Freitag hoch"). Ursache: kennt das heutige Datum nicht. Vorschlag (CEO-Entscheidung): aktuelles
  Datum in die Anweisung + Regel „keine Daten/Zahlen/Fakten erfinden, [Platzhalter] setzen".
- Hinweis: Zeitstempel/IDs auf der NAS sind UTC (Container), z. B. `A-20260927-002737` = 02:27 Ortszeit.
- **Briefing-Weg verifiziert:** Morgen-Briefing 2026-09-27 08:02 enthielt `#d868` unter „Nachts im Backoffice erledigt"
  und wurde zugestellt (`sent`).
- **BF-28 behoben** (`7d390b6`): Datum + „nichts erfinden" in der Anweisung, Pruefung fremder Jahreszahlen.
- **Tagtest 2026-09-27 12:45:** Test-Auftrag `#a59b` wurde vom RAM-Waechter **zu Recht** zurueckgehalten (nur 10,6 GB
  verfuegbar, Schwelle 13 GB) — tagsueber mit laufendem Desktop wartet das Backoffice realistisch oft bis zur Nacht.
  Das Warten war unsichtbar -> jetzt ein Protokoll-Hinweis je Zustandswechsel. Meldeweg per **simuliertem** Ergebnis
  (klar markiert, CEO-Go) getestet: Einzelmeldung `N-…-5c68` um 13:00 zugestellt (`sent`); Empfang + beide Abrufe vom CEO
  per Screenshot bestaetigt (13:06).
- Ziel / Scope: Store `auftraege/log.jsonl` auf der NAS (Status neu -> in_arbeit -> fertig/fehlgeschlagen, Ergebnis,
  Dauer); Worker nach Cutter-Muster auf dem MACO470 (holt Auftraege ueber die LUNA-OS-API, prueft RAM + Zeitfenster,
  laedt das Modell, arbeitet nacheinander, entlaedt, meldet Ergebnis zurueck); Plausibilitaetsfilter (bei Zeichensalat:
  ein zweiter Versuch, sonst `fehlgeschlagen` + Meldung). Meldung ueber die Outbox.
- Gate: Tests gruen; Probelauf mit 3 Test-Auftraegen Ende-zu-Ende (anlegen -> Worker -> Ergebnis -> Telegram-Meldung am
  **Empfaenger** geprueft).
- Verifikation: Auftrags-Store zeigt 3x `fertig`; Telegram-Nachrichten beim CEO angekommen; RAM-Protokoll ohne
  Dauer-Auslagerung.
- Risiko / Rueckweg: Worker-Dienst stoppen; Store bleibt als Protokoll. Neuer Store -> Deploy-Schutz + Backup +
  `docs/datenfluesse.md` (Doku-Check erzwingt es).
- Abhaengig von: 1 · Aufwand: mittel-gross · Risiko: mittel
- Freigaben: Etappe; Deploy NAS + MACO470; neuer systemd-Dienst (CEO: sudo auf dem MACO470 hat Claude Code).

### Etappe 3: Frontdesk-Werkzeuge + Ehrlichkeitsregel

- Status: **verifiziert** (2026-09-27 14:03) — deployt `73e5392` + Korrektur `28c1bb2`; Live-Test 2 bestanden (unten) — Werkzeuge
  `auftrag_erteilen` (Kern-Set, immer sichtbar) und `auftraege_zeigen`; Auftrags-IDs jetzt `B-...` (Antraege sind `A-...`,
  gleiches Format -> Verwechslungsgefahr); System-Prompt: Backoffice-Regel, Ehrlichkeitsregel, Duzen (BF-27);
  Nachfassen (einmal), wenn eine Erledigung ohne Werkzeug behauptet oder eine nicht existierende Auftrags-ID genannt
  wird; Protokoll Kategorie `ehrlichkeit`. Werkzeugauswahl-Gate knapp gerissen (5.252 Token) -> Beschreibungen
  gekuerzt -> 64/64, Ø 4.835. Tests 863 passed / 0 failed.
- **Probelauf Gemini (2026-09-27, Wegwerf-Ablagen):** 1. Lauf: Hintergrund 4/10 — **4x „Auftrag angelegt" mit
  erfundener ID ohne Werkzeug** (Ursache: woertliche Antwort-Vorlage im Prompt + Erkennung nur mit Hilfsverb).
  Korrigiert (keine Vorlage, Erkennung ohne Hilfsverb, ID-Existenzpruefung). 2. Lauf: **Hintergrund 9/10** ans
  Backoffice (2x per Nachfassen), 0 Erfindungen, 1 ehrliche Rueckfrage; **Erledigung 10/10 ehrlich** (7 Werkzeug,
  3 „technischer Fehler" durch leere Gemini-Antworten, BF-24).
- **Live-Test 1 (2026-09-27 13:50, nach Deploy `73e5392`):** gescheitert — Gemini antwortete „Absolut, mache ich. Hier ist
  die Auftrags-ID für den Entwurf:" (18 Token) **ohne Werkzeugaufruf**; kein Auftrag angelegt. Neue Spielart von BF-25
  (Ankuendigung statt Behauptung). Korrektur (CEO-Go, `28c1bb2`): deterministisches Nachfassen bei ausdruecklichem
  Hintergrund-Wunsch ohne `auftrag_erteilen` + Erkennung von Ankuendigungen ohne Tat (Doppelpunkt am Ende, „mache ich"/
  „lege ich an"). 3 neue Tests (Live-Fall nachgestellt), Gegenprobe rot, Suite 866 passed. Deployt, Neustart CEO.
- **Live-Test 2 (2026-09-27 14:02):** gleiche Nachricht -> LUNA ruft `auftrag_erteilen` direkt auf (Protokoll
  „vorausgewaehlt", kein Nachfassen noetig), antwortet „Auftrag #e037 ist angelegt" mit **echter** ID
  (`B-20260927-120256-e037`). Worker-Protokoll 14:03: „Wartet: 1 Auftrag offen, aber nur 12.0 GB verfuegbar (< 13 GB)
  — spaetestens ab 1:00 Uhr." Ergebnis kommt ueber den in Etappe 2 verifizierten Meldeweg.
- Ziel / Scope: Werkzeuge `auftrag_erteilen(aufgabe, art)` und `auftraege_zeigen`; System-Prompt-Regel: „Erledigt"
  nur nach einem Werkzeug-Ergebnis im selben Zug, sonst „Auftrag angelegt"; optional Erkennung von
  Erledigungs-Behauptungen ohne Werkzeug-Aufruf (BF-25) mit Nachfassen.
- Gate: Probelauf mit Gemini: 10 typische „mach mal im Hintergrund"-Nachrichten -> jeweils Auftrag angelegt; 10
  Erledigungs-Faelle -> Werkzeug wirklich aufgerufen.
- Abhaengig von: 2 · Aufwand: mittel · Risiko: niedrig

### Etappe 4: Bestehende Hintergrund-Jobs ueber das Backoffice

- Status: **deployt** (2026-09-27; erster Nachtlauf 2026-09-28 02:00-04:00, Beobachtung 7 Tage) — CEO-Entscheidungen:
  Content-Feed 07:00 -> **02:00**, Self-Dev 09:00 -> **04:00**, CFO bleibt 03:00; nachts erzeugte Job-Meldungen gebuendelt
  ins **Morgen-Briefing**. Umsetzung: `core/hintergrund.py` (Hintergrund-Modus je Job-Thread); `FallbackBackend` schickt im
  Hintergrund-Modus Fachagenten-Aufrufe als **stillen Auftrag** (`art=roh`, eigener System-Prompt, `stumm`) ans Backoffice und
  wartet (Takt 10 s, Zeitlimit 20 min -> Cloud-Fallback, Auftrag abgehakt); interaktive Aufrufe unveraendert.
  `Notifications`: Meldungen aus dem Hintergrund-Modus `nach_briefing`, werden nicht sofort zugestellt, nicht vom
  Lawinenschutz verworfen, erscheinen morgens unter „Nachts von den Agenten". Worker: Job-Auftraege ohne Mindestlaenge und
  ohne Gegenlesen, 90 s Nachlauf fuer Job-Serien, **keep_alive 2 min statt ausdruecklichem Entladen** (ein ausdrueckliches
  Entladen brach im Probelauf eine laufende Anfrage ab -> leere Huelle), leere Huellen als eigener Fehler. Innovation: ohne
  echte Idee **kein Antrag** mehr (vorher Antrag mit Fehlertext als Titel; revidiert frueheres Verhalten), Titel ohne
  „TITEL:". Tests: 20+ neu/angepasst, Gegenproben rot.
- **Probelauf (2026-09-27 15:03, echtes lokales Modell, Wegwerf-Ablage):** Content-Idee (TITEL/IDEE/FORMAT), Innovations-Idee
  und CFO-Kostenvoranschlag (Zeile `KOSTEN:`) **alle lokal, alle Formate zerlegbar**, 66-99 s je Aufruf. Erster Versuch war
  durch einen parallelen Worker gestoert (s. o.) — dabei erledigte der echte Worker den Chat-Auftrag `#e037` (Meldung
  zugestellt).
- Ziel / Scope: CFO-Lauf, Content-Feed, Self-Dev/Innovation als Auftraege an das Backoffice statt direkt an die Cloud.
- Gate: eine Woche lang alle Jobs lokal erledigt oder sauber auf Gemini ausgewichen; Kostenlog ohne Cloud-Kosten.
- Abhaengig von: 2 · Aufwand: klein-mittel · Risiko: niedrig

### Etappe 5: Beobachtung und Abschluss

- Status: geplant
- Ziel / Scope: 7 Tage Betrieb; Auswertung Durchlaufzeiten, Fehlschlaege, RAM, CEO-Zufriedenheit.
- Gate: CEO-Abnahme.

## Reihenfolge

Entscheidungen -> 1 -> 2 -> 3 -> 4 -> 5. Etappe 1 ist klein und klaert, ob es ueberhaupt ein brauchbares Backoffice-Modell gibt.

## Kosten

Einmalig 0 EUR, laufend Strom des MACO470. Einsparung: alle Hintergrund-Aufgaben ohne Cloud-Token.

## Dokumentationspflichten

`projekt_changelog.md`, Etappen-Status + `Naechster Schritt` hier, `ROADMAP.md` (Verzeichnis), `docs/datenfluesse.md`
(neuer Store, neuer Worker, neue API-Endpunkte), `docs/bekannte-fehler.md` (BF-23/25), `docs/entscheidungs-register.md`,
`governance/zugriffs-policy.md` (Worker-Zugriff), `LOKALES_LLM_ROADMAP.md` (Fortsetzung Etappe 2 dort).

## Definition of Done

Der CEO kann im Chat Auftraege erteilen, die ohne Cloud-Kosten im Hintergrund erledigt und zuverlaessig gemeldet werden;
der MACO470 bleibt dabei bedienbar; Gemini behauptet keine Erledigungen mehr ohne Nachweis. Abnahme durch den CEO.
