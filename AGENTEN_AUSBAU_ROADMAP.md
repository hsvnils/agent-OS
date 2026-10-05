# Roadmap: Agenten-Ausbau (Bestandsaufnahme, Skills, Quellen, Nutzung, Charten)
- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/plan-agenten`
- Basiscommit: `313dacb`
- Naechster Schritt: CEO-Entscheidungen zu den Rand-Agenten (A5) und Go fuer A1-A4 abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Wir sollten uns dann mal generell die Agenten und ihre aktuellen Skills anschauen und ausbauen.“

## Bestandsaufnahme (read-only, 2026-10-05)

Quellen: Charten `agents/*.md`, `skills/*`, `core/watch_config.py`, Code-Verweise, NAS-Protokolle `watch/log.jsonl`
(Watcher-Funde je Abteilung) und `research/log.jsonl` (Recherche-Auftraege je Abteilung), `aktivitaet/log.jsonl`.

| Agent | Charta | Skills | Watcher-Funde (gesamt / zuletzt) | Was wirklich arbeitet (Code) |
|---|---|---|---|---|
| **HoA / LUNA** | aktiv | 0 | -- | Telegram-Bot, LUNA-OS, ~60 Werkzeuge, Briefings, Freigaben |
| **CFO** | aktiv | **0** | 25 / 04.10. | stark: Buchhaltung, Rechnungen, Belege, Mahnwesen, EUeR, Abos, Finanzcheck 05:00, Kosten |
| **CRO** | aktiv | 4 | 21 / 24.09. | CRM, Angebote/Katalog, Collab-Radar (aus) |
| **CDO** | aktiv | 2 | 20 / 04.10. | Leistungs-Agent (Wochenbericht), Kosten-Rohdaten |
| **CTO** | aktiv | **0** | 40 / 29.09. | Watcher (GitHub), Self-Dev-Vorschlaege, Execution (blockiert) |
| **CISO** | Entwurf | **0** | 33 / 26.09. | Security-Audit 04:00, Input-Guard, Skill-Gate |
| **CCO** (Content) | aktiv | **0** | 19 / 17.08. | Content-Feed 02:00, Cutter/Reels |
| **CBO** (Marke) | aktiv | 2 | 19 / 10.09. | Social-Kit |
| **CLO** (Recht) | Entwurf | **7** (neu) | 19 / 24.09. | Skills + Rechtsquellen mit Nachtabgleich, Pruef-Lauf (seit 05.10.) |
| **Berater** | aktiv | 3 | 27 / 05.10. | Innovations-/Self-Dev-Laeufe |
| **Researcher** | aktiv | 0 | -- | Web-Recherche (Brave), Tickets (304 ohne Abteilung, 150 von Abteilungen) |
| **CIO** + Risk | Entwurf / aktiv | 0 | -- | Investment-System (Paper), **nicht** ueber „delegate“ befragbar |
| **CKO** (Wissen) | Entwurf | 0 | 19 / 06.09. | nur Charta |
| **CXO** (Erlebnis) | Entwurf | 0 | 15 / 14.09. | nur Charta |
| **CPO** (Produkt) | Entwurf | 0 | 20 / 05.09. | nur Charta |
| **CHRO** (Personal) | Entwurf | 0 | 11 / 03.08. | nur Charta |
| **CAO** (Verwaltung) | Entwurf | 0 | 9 / 18.09. | nur Charta |

**Befunde:**
1. **Nutzung je Agent wird nicht gemessen:** Wie oft LUNA einen Fachagenten fragt („delegate“), steht in keinem
   Protokoll -- das Aktivitaetsprotokoll kennt nur Researcher, HoA und einzelne Laeufe. Ohne Zahlen ist „wer ist
   wichtig“ Bauchgefuehl.
2. **Die Agenten mit dem meisten Code haben keine Skills** (CFO, CTO, CISO, CCO): ihre Arbeit steckt im Code, ihr
   Wissen fuer Fragen und Pruefungen nicht.
3. **Wissen/Quellen gibt es nur beim CLO** (seit heute); CFO (UStG, EStG, AO, GoBD) und CISO (DSGVO, TDDDG) arbeiten
   ohne hinterlegte Normen.
4. **Watcher-Themen** sind bei den meisten noch auf KI-Werkzeuge gerichtet, nicht auf dein Geschaeft.
5. **Fuenf Agenten bestehen nur aus einer Charta** (CKO, CXO, CPO, CHRO, CAO) -- Status „Entwurf“, kein Code, keine Skills.
6. **Modell-Angaben in den Charten** (Opus, GPT-5.5, Grok …) stimmen nicht mit der Realitaet ueberein: faktisch
   antwortet Gemini (Anthropic-Schluessel ungueltig, BF-18). Werkzeuge stehen teils nur als Text da.
7. **CIO/Risk** sind nicht ueber „delegate“ erreichbar (fehlen in `ALL_AGENT_CHARTERS`).

## Etappe A1: Transparenz -- Nutzung messen und Agenten zeigen

- Status: geplant
- Ziel / Scope: jede Fachagenten-Anfrage protokollieren (Agent, Zeit, Dauer, Skills geladen, Modell, Erfolg -- ohne
  Inhalte); Seite „🛰 Agenten“ in LUNA-OS je Agent: Charta-Status, Skills, Quellen mit Stand, Watcher-Themen und letzte
  Funde, Nutzung (30/90 Tage); im Wochenbericht des Leistungs-Agenten „wer wird gefragt“. CIO/Risk befragbar machen.
- Gate: Tests; Browsertest Rechner/iPad/iPhone 17 Pro.
- Aufwand: mittel.

## Etappe A2: Geschaefts-Agenten mit Skills und Quellen

- Status: geplant
- Ziel / Scope (Skills im Skill-Standard, Quellen-Mechanik des CLO wiederverwenden):
  - **CFO** (4): Beleg-/GoBD-Pruefung, Monats- und Jahresabschluss-Check (EUeR), Preis-/Margen-Analyse (Nachkalkulation,
    TKP-Vergleich), Liquiditaetsvorschau; Quellen UStG/EStG/AO (gesetze-im-internet.de) + GoBD (BMF, Verweis) mit
    Nachtabgleich.
  - **CCO** (4): Hook und Skript schreiben, Reel-Formate/Dramaturgie, Content-Kalender, Briefing -> Konzept (passt zur
    Konzept-Mappe K4).
  - **CRO** (+2): Angebot nachfassen/verhandeln, Folgeauftrag/Upsell aus Kampagnen-Historie und Ist-Kennzahlen.
  - **CDO** (+1): Kampagnen-Auswertung (TKP-Vergleich, Engagement) fuer Berichte.
- Gate: Skill-Gate, Tests „Skills geladen“, Quellen mit Stand; Nachtabgleich fuer CFO-Quellen.
- Aufwand: mittel bis gross.

## Etappe A3: Betriebs-Agenten mit Skills

- Status: geplant
- Ziel / Scope: **CISO** (3: Zugriffs-/Rollenpruefung, Secret-Hygiene, Datenschutz-Check mit Quellen DSGVO/BDSG/TDDDG),
  **CTO** (3: Deploy-Checkliste, Fehlersuche entlang `docs/bekannte-fehler.md`, Release-Notizen), **Researcher** (1:
  Quellenbewertung/Recherche-Protokoll).
- Gate: wie A2.
- Aufwand: mittel.

## Etappe A4: Watcher-Themen auf das Geschaeft zuschneiden

- Status: geplant
- Ziel / Scope: Suchthemen aller Abteilungen auf Hanserautisch ausrichten (z. B. CFO: Kleinunternehmer/Steuer fuer
  Creator; CRO: Influencer-Preise/Marktdaten; CCO: Reel-Trends Fussball; CISO: Sicherheitsluecken der genutzten
  Dienste), weiter token-frugal (Brave, ein Bereich je Takt).
- Gate: Test; keine neuen Kosten.
- Aufwand: klein.

## Etappe A5: Rand-Agenten entscheiden (CEO)

- Status: geplant
- Ziel / Scope: fuer CKO, CXO, CPO, CHRO, CAO je eine Entscheidung: **aktivieren** (mit Aufgabe + Skills, z. B. CHRO
  fuer Freie wie Kamera/Schnitt -- Briefings, Vertraege, Abrechnung; CKO fuer das Clip-/Wissens-Gedaechtnis), **zusammenlegen**
  (z. B. CAO in HoA, CXO+CPO zu „LUNA-OS-Produkt“) oder **ruhend** (bleibt, wird nicht befragt, keine Watcher-Last).
- Gate: CEO-Entscheidung; Charta-Aenderungen nur ueber A6.
- Aufwand: klein (Entscheidung), Umsetzung je nach Wahl.

## Etappe A6: Charten auf den Ist-Stand heben (CEO-Tor)

- Status: geplant
- Ziel / Scope: je Charta Status, realistische Modell-Richtwerte, echte Werkzeuge/Skills/Quellen, Ergebnis aus A5;
  inklusive CLO_AUSBAU C5. **Nur der Head of Agents auf CEO-Anweisung, je Charta mit Diff-Vorlage und Bestaetigung**
  (`AGENTS.md` 3.3).
- Aufwand: mittel (viele kleine Diffs).

## Nicht-Scope

Keine neuen kostenpflichtigen Modelle/Dienste (CEO-Tor); keine Autonomie-Erweiterung (Agenten beraten weiter nur);
keine Aenderung an Charten ausserhalb von A6.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`,
`agents/REGISTRY.md` (A5/A6).

## Definition of Done

A1-A4 verifiziert; A5 entschieden; A6 je Charta mit bestaetigtem Diff umgesetzt.
