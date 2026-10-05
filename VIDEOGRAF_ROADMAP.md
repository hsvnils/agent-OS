# Roadmap: Videograf-Berater (Agent 17)
- Status: abgeschlossen
- Stand: 2026-10-05
- Arbeitsbranch: `ai/videograf-v2v4`
- Basiscommit: `782e428`
- Naechster Schritt: keiner -- V1-V4 live, abgeschlossen auf CEO-Wunsch (2026-10-05); Praxistest beim naechsten Kunden, Fehler meldet der CEO.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Agent als professionellen Videografen-Berater aufbauen (fuer Vorschlaege im Kontext zu Ideen/Shotlist usw. in
Kundenauftraegen).“ Entscheidungen: **eigener Agent (17)** direkt unter LUNA; Vorschlaege **per Knopf in der
Konzept-Mappe und im Chat**.

## Analyse (read-only, 2026-10-05)

- Konzept-Mappe je Vorgang (`orchestrator/core/konzept.py`): Briefing, Ideen (`idee`), Skripte je Posting (`skript`),
  Shotlist-Szenen (`szene`, mit erledigt/entfernen), Drehplan (`dreh`), Bilder, Kunden-Freigabe, PDF fuer Kunde/Dreh.
- Fachagenten werden aus Charta + Skills gebaut (`core/subagents.py` `ALL_AGENT_CHARTERS`, `core/dept_skills.py`),
  befragt ueber `delegate`; LUNA ordnet Sachfragen selbst zu (`core/zustaendigkeit.py`, FACHAGENTEN_ROUTING).
- Inhaltlich naechste Agenten: CCO (Reels, Skripte, Konzepte), CHRO (Freie Kamera/Schnitt), CXO (Kundendokumente).
  Der Videograf ergaenzt sie um **Drehpraxis**: Einstellungen, Kamera, Licht, Ton, Equipment, Ablauf am Set.
- Modell: wie alle Fachagenten derzeit Gemini (BF-18); fuer den Knopf in der Mappe gehen **Briefing, Idee und Skript**
  des Auftrags an Gemini (Kundenname der Firma ja, keine Ansprechpartner-/Kontaktdaten).

## Etappe V1: Charta (CEO-Tor, nur HoA mit Diff)

- Status: umgesetzt (2026-10-05) -- Charta-Diff vom CEO bestaetigt („Charta passt, leg sie an“): `agents/17_videograf.md`,
  Registry, `governance/organigramm.md`, Fachagenten-Liste (`vid`), Zustaendigkeitszeile, Organigramm-Kachel „17 · VID“,
  Watcher-Themen. Token der Werkzeugauswahl im Mittel 5.190 (Gate 5.200 -- knapp, bei V4 beobachten).
- Ziel / Scope: neue Charta `agents/17_videograf.md` nach `agents/_TEMPLATE.md` -- Rolle „professioneller Videograf-
  Berater fuer Kundenauftraege und eigene Reels“, Auftrag (Shotlist, Bildsprache, Licht/Ton, Equipment, Drehplan,
  Machbarkeit am Ort), Ausdruecklich NICHT (keine Buchung von Freien = CHRO, kein Posten, keine Kosten), Skills,
  Eskalation, Output. Dazu Registry, `ALL_AGENT_CHARTERS` (Kuerzel `vid`), Zustaendigkeitszeile, Organigramm
  (`_DEPARTMENTS`), Watcher-Themen (z. B. „Reels Videografie Tipps“, „Smartphone Video Equipment“, „Licht Gastronomie
  Video“). **Die Charta legt der Head of Agents als Diff vor; erst nach CEO-Bestaetigung wird sie angelegt.**
- Gate: CEO bestaetigt den Charta-Diff; Tests (Agent befragbar, Karte vollstaendig, Organigramm).
- Aufwand: klein.

## Etappe V2: Skills

- Status: umgesetzt (2026-10-05) -- 5 Skills unter `skills/vid/`, Security-Gate bestanden, im System-Prompt.
- Ziel / Scope: `skills/vid/` (Security-Gate):
  1. `shotlist-erstellen` -- aus Idee/Skript eine Shotlist (Szene, Einstellungsgroesse, Perspektive, Bewegung,
     Dauer, Ton, Hinweis), 9:16 zuerst, Hook-Shot zuerst.
  2. `bildsprache-und-kamera` -- Einstellungsgroessen, Perspektiven, Kamerabewegung, Smartphone vs. Kamera,
     Bildrate/Zeitlupe, Stabilisierung.
  3. `licht-und-ton` -- vor Ort (Gastronomie, Stadion, draussen, Nacht), Mikrofon/Funkstrecke, Stoergeraeusche.
  4. `equipment-und-drehplan` -- Gear-Liste je Dreh, Ablauf/Zeitplan, Puffer, Genehmigungen und Personen im Bild
     (Hinweis auf CLO-Skills `nutzungsrechte`/KUG), Backup der Daten.
  5. `b-roll-und-schnittdenken` -- B-Roll, Uebergaenge, Material fuer den Video-Cutter (Laenge, Reserve).
- Gate: Skill-Gate bestanden; Test „Skills geladen“.
- Aufwand: mittel.

## Etappe V3: Knopf in der Konzept-Mappe

- Status: umgesetzt (2026-10-05) -- `core/videograf.py` + `POST /api/crm/konzept-videograf/{vorgang}` (gemini-2.5-flash,
  Probe mit Beispielkonzept: 10 Szenen in 18,6 s); Knoepfe „🎥 Videograf“ an Ideen und Skripten, Vorschlagsfeld im Dreh-Tab,
  Szenen einzeln oder alle per Klick uebernehmen (Quelle gesetzt, 🎥 in der Shotlist); Kontext ohne Ansprechpartner,
  Telefon, Freigabe-Personen und Notizen (Test + Gegenprobe); Nutzung zaehlt beim Videografen (quelle `konzept`).
- Ziel / Scope: je Idee bzw. Skript ein Knopf „🎥 Videograf-Vorschlaege“ -> Anfrage an Agent 17 (Charta + Skills,
  Kontext: Briefing, Idee, Skript, vorhandene Szenen, Drehort/-zeit) -> Ergebnis als **Entwurf**: vorgeschlagene
  Shotlist-Szenen (je Szene uebernehmen per Klick), Hinweise zu Licht/Ton/Equipment, Drehplan-Ergaenzungen. Nichts wird
  ohne Klick in die Mappe geschrieben; uebernommene Szenen tragen die Quelle „Videograf-Agent (Vorschlag)“. Laeuft im
  Hintergrund mit Fortschrittsanzeige (Antwortzeit Gemini). Zaehlt in „wer wird gefragt“ beim Videografen.
- Gate: Tests (Parsen/Validieren der Antwort, Uebernahme nur per Klick, Quelle gesetzt, keine Kontaktdaten im Prompt);
  Browsertest Konzept-Mappe auf Rechner, iPad und iPhone 17 Pro; Doku Datenfluesse/Datenschutz.
- Aufwand: mittel.

## Etappe V4: Im Chat befragbar

- Status: umgesetzt (2026-10-05) -- drei Drehfragen im Routing-Probelauf, 3 Laeufe je 23/23 (100 %).
- Ziel / Scope: LUNA ordnet Drehfragen ohne Abteilungsnamen dem Videografen zu („Wie filme ich die Kiez Alm abends
  am besten?“, „Welches Mikro fuer ein Interview im Stadion?“); Probelauf `scripts/routing_probelauf.py` um 3 Fragen
  erweitert, Abgrenzung zu CCO (Idee/Skript) und CHRO (Freie buchen/bezahlen) geprueft.
- Gate: Probelauf weiter mindestens 85 %, die neuen Fragen richtig.
- Aufwand: klein.

## Nicht-Scope

Keine Buchung oder Bezahlung von Freien (CHRO/CFO, CEO-Tor Geld); kein Kauf von Equipment (CEO-Tor); kein autonomes
Veraendern der Konzept-Mappe; kein neues kostenpflichtiges Modell.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `agents/REGISTRY.md` (V1), `docs/datenfluesse.md` und
`docs/datenschutz-ki-nutzung.md` (V3), `docs/entscheidungs-register.md`.

## Definition of Done

Agent 17 existiert mit bestaetigter Charta und 5 Skills, liefert per Knopf uebernehmbare Shotlist-Vorschlaege in der
Konzept-Mappe und wird im Chat bei Drehfragen automatisch gefragt.
