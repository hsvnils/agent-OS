# Roadmap: Betrieb und Qualitaet (aus der Antrags-Durchsicht 2026-09-29)

- Status: in Umsetzung
- Stand: 2026-09-29
- Arbeitsbranch: `ai/antraege-aufraeumen`
- Basiscommit: `79d6fbc`
- Naechster Schritt: Etappe 1 deployen (Go fuer Merge/Push/Deploy), nach dem naechsten Montag 04:00 pruefen, dass hoechstens
  ein Antrag kam und keiner ein abgelehntes Thema wiederholt; danach Go fuer Etappe 2.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anlass (CEO, 2026-09-29)

Der CEO hat die offenen Freigaben mit Claude Code durchgesehen („bewerte einmal alles ... was davon wir in Roadmaps
umwandeln ... und was wir mittlerweile nicht mehr brauchen“). Befund (Antrags-Store der NAS, 143 Ereignisse):

- **97 offene Antraege**, alle Kategorie „Innovation/Beschaffung (Kosten pruefen)“, alle aus den automatischen
  Ideen-Laeufen (Unternehmensberater 27, dazu 13 Fachbereiche reihum), Juni bis September.
- Einteilung (CEO-bestaetigt „Passt, lass uns starten“): **8** Fehler-Antraege (Modell-/Backend-Fehler, BF-30),
  **41** schon umgesetzt, **39** nicht (mehr) noetig, **9** in Roadmaps ueberfuehrt (diese Datei, Etappen 1–4, und
  `KUNDEN_FINANZEN_ROADMAP.md` Etappen 3c und 17).
- **Ursache der Flut:** `orchestrator/core/innovation.py` (`InnovationPipeline.run`) reicht jede Idee als Antrag ein,
  ohne mit bestehenden oder abgelehnten Antraegen abzugleichen; der Selbst-Entwicklungs-Lauf
  (`channels/telegram/bot.py`, `_start_selfdev_loop`) ruft sie **taeglich** um 04:00 fuer einen Bereich auf. Deshalb
  kehren dieselben Themen wieder (Infrastruktur-Monitoring 3x, Technik-Inventar 4x, Richtwert je 1.000 Follower 4x,
  Research-Agent 3x, Wissens-Erfassung 5x, Nutzer-Feedback-Kanal 3x).

## Register und bekannte Fehler (B3)

- Register: „Innovation ohne echte Idee: kein Antrag mehr“ (2026-09-27), „Nacht-Jobs ueber das Backoffice: Self-Dev
  04:00“ (2026-09-27), „Gemini 3.5 Flash Free-Tier ... Datenschutz-Haken: Free-Tier nutzt Inhalte“ (2026-07-06).
- Bekannte Fehler: BF-30 (Fehlertext als Antrag, behoben); Lehre „Erzeugt ist nicht angekommen“ (Telegram-Zustellung
  5 Wochen tot, `docs/bekannte-fehler.md`).

## Scope / Nicht-Scope

- Scope: Ideen-Pipeline und Selbst-Entwicklungs-Takt, Doku-Check, Betriebs-Monitoring, Datenschutz-Pruefung (Entwurf).
- Nicht-Scope (Schutzbereiche, `governance/roadmap-workflow.md` B4): `.env`/Secrets, Telegram-Bot starten, Live-Daten
  aendern (ausser dem vom CEO beauftragten Schliessen der 97 Antraege), Container/Zeitplaene ohne Go, Charten,
  CEO-Tor-Kategorien (Rechtliches bleibt Entwurf).

### Etappe 1: Ideen-Laeufe entruempeln (Dubletten-Filter + ruhigerer Takt)

- Status: umgesetzt (CEO-Go 2026-09-29 „Go fuer Etappe 1“), Deploy + Verifikation offen
- Ergebnis: `core/innovation.py` `finde_dublette` (Kernwoerter ohne Fuellwoerter, Wortstaemme, Wortanfang ab 6 Zeichen;
  Dublette = mind. 2 gemeinsame Kernwoerter, >= 60 % des kuerzeren und >= 30 % des laengeren Titels; Fehler-Antraege
  zaehlen nicht), Pruefung direkt nach der Idee -> bei Dublette kein Antrag, keine CTO/CFO-Bewertung, keine
  Freigabe-Meldung, Hinweis „Thema schon beantragt (A-..., Status)“ in Tool-Antworten und Bot-Log;
  `self_development.selfdev_wochentag` + Bot: Lauf nur am Wochentag `SELF_DEV_WOCHENTAG` (Standard Montag) 04:00,
  intern/extern im Wochenwechsel. Tests `test_ideen_dubletten.py` (7 Faelle, 12 echte Titelpaare) + 5 Gegenproben;
  Suite gruen. Probelauf ueber den echten Verlauf (103 Antraege): 14 waeren als Wiederholung zurueckgehalten worden.
- Ziel / Scope: Vor dem Einreichen prueft `InnovationPipeline.run` den Titel gegen **alle** bisherigen Antraege
  (auch abgelehnte/geloeschte/erledigte) mit einem regelbasierten Wortvergleich (Fuellwoerter wie „Einfuehrung/
  Etablierung/zentral“ raus, Wortstaemme, gleiche Wortanfaenge ab 6 Zeichen). Treffer -> **kein Antrag**, Ergebnis nennt
  „Dublette zu A-...“, keine Freigabe-Meldung. Selbst-Entwicklung laeuft **einmal pro Woche** (Montag 04:00, per
  `.env` `SELF_DEV_WOCHENTAG` aenderbar) statt taeglich. Nicht-Scope: LLM-Vergleich (kostet), Charten.
- Kalibrierung (2026-09-29, 97 echte Titel): trifft die Wiederholungen (z. B. drei Titel zum Infrastruktur-Monitoring,
  Technik-Inventar, Richtwert, Research-Agent, Secrets-Register); Fehlgriff „Investment: Research statt Ausfuehrung“ ~
  „Research-Agent“ wird durch eine zweite Schwelle (Anteil am laengeren Titel) ausgeschlossen.
- Gate: Test mit den echten Titelpaaren (Treffer und Nicht-Treffer) + Gegenprobe; ein abgelehnter Antrag verhindert
  seine Wiederholung; Takt-Test (Montag ja, Dienstag nein); Suite gruen.
- Verifikation: `.venv/bin/python -m pytest -q orchestrator` -> gruen; nach Deploy: in der Woche nach dem Montagslauf
  hoechstens 1 neuer Antrag, kein Titel wiederholt ein abgelehntes Thema.
- Dry-Run: Vergleich laeuft vorher gegen eine Kopie des Antrags-Stores (Scratchpad), nichts wird eingereicht.
- Risiko / Rueckweg: echte neue Idee faelschlich als Dublette -> Ergebnis nennt den Treffer (CEO kann on-demand
  nachfragen); Rueckweg: Filter per Schalter aus bzw. Git-Revert.
- Abhaengig von / Aufwand: Schliessen der 97 Antraege (damit die Absagen als Vergleich dienen); klein (1 Sitzung).

### Etappe 2: Changelog-Disziplin automatisch pruefen

- Status: geplant (aus Antraegen „Automatisiertes Changelog-Validierungssystem“ / „Automatisierte Ueberpruefung der
  Changelog-Disziplin“, CAO)
- Ziel / Scope: `scripts/doku_check.py` prueft zusaetzlich, dass der neueste Changelog-Eintrag das Pflichtformat hat
  (Kopf `## [JJJJ-MM-TT HH:MM] — Akteur`, Was/Warum/Betroffen) und dass Eintraege nicht in der Zukunft liegen (BF-09:
  geschaetzte Uhrzeiten); optional: Commit ohne Aenderung an `projekt_changelog.md` im Pre-Commit-Hinweis. 0 EUR.
- Gate: Test mit gueltigem, fehlerhaftem und zukuenftigem Eintrag + Gegenprobe; Doku-Check auf dem echten Repo gruen.
- Risiko / Rueckweg: Fehlalarm -> Regel lockern; Rueckweg Git-Revert. Aufwand: klein.

### Etappe 3: Betriebs-Monitoring Ende-zu-Ende

- Status: geplant (aus drei Antraegen „zentrales Infrastruktur-Monitoring (+ Alerting)“, CTO)
- Bestand: Betriebswacht (Cutter-Queue, Worker-Herzschlag, Reel-Nacht), Selbstwartung/Systemcheck, Sicherheits-Audit.
- Luecke: Niemand prueft von aussen, ob die NAS-Container leben, ob Telegram-Nachrichten **ankommen** und ob das
  naechtliche Backup auf dem MACO470 gelaufen ist.
- Ziel / Scope (Vorschlag, Details bei Go): leichter Waechter auf dem MACO470 (systemd-Timer, kein LLM) prueft
  LUNA-OS-Erreichbarkeit, Alter des letzten Bot-Herzschlags/Watch-Logs, Ergebnis des Backups; bei Ausfall eine
  Meldung ueber einen zweiten Weg (z. B. Mail aus LUNAs Postfach oder Telegram direkt vom MACO470). Nicht-Scope: neue
  kostenpflichtige Monitoring-Dienste.
- Gate: gezielt simulierter Ausfall (Herzschlag alt) loest genau eine Meldung aus; Normalbetrieb bleibt still.
- Risiko / Rueckweg: Meldungsflut -> Dedup wie Betriebswacht; Timer abschaltbar. Aufwand: mittel. Neuer Dienst/Timer =
  Schutzbereich -> eigenes Go.

### Etappe 4: Datenschutz-Check der KI-Nutzung (Entwurf)

- Status: geplant (aus Antraegen „Leitfaden LLM-Datenschutz“ (CLO) und „Expertise EU AI Act“ (CLO))
- Ziel / Scope: read-only Bestandsaufnahme, welche Daten an welches Modell gehen (Chat ueber Gemini-Gratis, das
  Eingaben nutzen darf; Backoffice lokal; Beleg-/Kundendaten), plus kurze Einordnung der fuer einen Creator relevanten
  Pflichten (DSGVO, EU AI Act Transparenz). Ergebnis: Entwurf mit Empfehlungen (z. B. Kunden-/Rechnungsdaten nur lokal).
- Gate: Liste aller Datenfluesse zu Modellen mit Beleg aus `docs/datenfluesse.md` und Code; CEO entscheidet.
- Risiko: Rechtsfragen -> nur Entwurf (CEO-Tor Recht). Aufwand: klein.

## Reihenfolge

1 -> 2 -> 3; 4 unabhaengig. Content-Feedback-Loop und CRM-Lead -> Angebot stehen in `KUNDEN_FINANZEN_ROADMAP.md`.

## Kosten

0 EUR (Eigenbau, vorhandene Geraete). Etappe 3 ggf. Telegram/Mail ueber vorhandene Zugaenge.

## Dokumentationspflichten

Changelog, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`,
`docs/datenfluesse.md` (Etappe 3: neue Verbindung MACO470 -> NAS/Telegram).

## Definition of Done

Keine wiederkehrenden Dubletten mehr in den Freigaben, Changelog-Format automatisch geprueft, ein stiller Ausfall von
NAS/Bot/Backup wird gemeldet, Datenschutz-Entwurf liegt dem CEO vor. Status „abgeschlossen“ setzt der CEO.
