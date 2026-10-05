# Roadmap: CLO-Ausbau (Skills, Rechtsquellen, Beobachtung, echter Pruef-Lauf)
- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/clo-ausbau`
- Basiscommit: `77fa015`
- Naechster Schritt: CEO-Go je Etappe abwarten (Empfehlung: C1-C4 am Stueck, C5 getrennt als Charta-Aenderung).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Wer hat die Entwuerfe gemacht, der CLO? Wie sind seine Skills aktuell ausgestattet? Muessen wir den nochmal mit
Infos/Gesetzen oder sonst was fuettern?“ -- Antwort: Die ersten Vertragsentwuerfe hat Claude Code geschrieben, nicht der
CLO; der CLO soll so ausgestattet werden, dass er Vertraege fachlich vorpruefen und der Anwaeltin eine Pruefliste
uebergeben kann.

## Analyse (read-only, 2026-10-05)

- **Charta** `agents/13_clo.md`: Status „Entwurf“; Mandat nur Entwuerfe, ein Anwalt zeichnet; Schwerpunkt Club-Logo-/
  DFL-/HSV-Lizenzen, Musik-/Content-Rechte, KI-Kennzeichnung; „Vertrags-/Recherchewerkzeuge“ stehen nur als Text da.
- **Skills:** keine (`skills/` hat nur `berater`, `cbo`, `cdo`, `cro`; geladen ueber `core/dept_skills.py`, Format
  `governance/skill-standard.md`, Security-Gate `core/skill_gate.py`).
- **Wissen:** keine Rechtsquellen im System (keine Normen, Leitfaeden, Urteile, Checklisten).
- **Recherche:** keine eigene; Websuche nur ueber den Researcher (Brave, Tool `recherche_beauftragen`).
- **Beobachtung:** Watcher-Themen fuer den CLO (`core/watch_config.py`): „EU AI Act updates“, „AI copyright ruling“,
  „LLM compliance datenschutz“ -- Influencer-/Werbe-, AGB- und Urheberrecht fehlen.
- **Modell:** konfiguriert Sonnet 5; weil der Anthropic-Schluessel ungueltig ist (BF-18), antwortet Gemini.
- **Herkunft der Vertragsentwuerfe** (V2): Claude Code, ungeprueft -- Beschriftung am 2026-10-05 korrigiert
  (`quelle = "Entwurf Claude Code (ungeprueft)"`, Knopf „Erste Entwuerfe laden“).

## Etappe C1: Skills fuer den CLO

- Status: geplant
- Ziel / Scope: eigene Skills unter `skills/clo/` (Format laut Skill-Standard, durch das Security-Gate), je mit
  Anwendungsfall, **Pruef-Checkliste**, Kernnormen in Kurzfassung, Ausgabeformat („Entwurf -- anwaltliche Pruefung
  erforderlich“) und Quellen mit Stand-Datum:
  1. `werbekennzeichnung` -- UWG (§ 5a Abs. 4), Medienstaatsvertrag (§ 8, § 22), Digitale-Dienste-Gesetz (§ 6),
     Leitfaden der Medienanstalten; Plattform-Kennzeichnungen.
  2. `agb-pruefung` -- BGB §§ 305-310 (Einbeziehung, ueberraschende Klauseln, Inhaltskontrolle; Unterschied
     Unternehmer/Verbraucher).
  3. `nutzungsrechte` -- UrhG §§ 31 ff. (Einraeumung, Zweckuebertragung § 31 Abs. 5), § 32 (angemessene Verguetung),
     KUG §§ 22/23 (Recht am eigenen Bild), Whitelisting/Paid-Ads.
  4. `musik-in-videos` -- Plattform-Musikbibliotheken bei kommerziellen Beitraegen, GEMA, lizenzfreie Quellen.
  5. `kleinunternehmer-hinweise` -- § 19 UStG (Pflichthinweis auf Belegen und in Vertraegen).
  6. `ki-kennzeichnung` -- EU AI Act (Transparenzpflichten fuer KI-erzeugte/-veraenderte Inhalte), Plattformregeln.
  7. `club-und-markenrechte` -- bisheriger Schwerpunkt (Vereinslogos, DFL-/HSV-Bilder, Markenrecht), Lizenzanfragen.
- Gate: Skill-Format-Pruefung + Security-Gate bestanden; Test „CLO laedt seine Skills“.
- Aufwand: mittel.

## Etappe C2: Rechtsquellen (Wissensbasis)

- Status: geplant
- Ziel / Scope: je Skill eine `quellen.md` mit den einschlaegigen Paragraphen im Wortlaut (Gesetze sind amtliche Werke
  und frei nutzbar, § 5 UrhG; Quelle gesetze-im-internet.de, Abrufdatum) und Leitfaeden/Urteilen **nur als Verweis mit
  eigener Kurzfassung** (Urheberrecht der Verlage/Medienanstalten). Jede Quelle mit „Stand“ und „naechste Pruefung“;
  der CLO nennt in jedem Ergebnis die Fundstelle und den Stand.
- Gate: jede Kernnorm eines Skills hat eine Quelle mit Stand; Doku-Check.
- Aufwand: mittel.

## Etappe C3: Aktualitaet (Beobachtung)

- Status: geplant
- Ziel / Scope: Watcher-Themen des CLO auf das Geschaeft umstellen (Influencer-/Werbekennzeichnung, BGH-/OLG-Urteile zu
  Influencern, AGB-Recht B2B, Urheber-/Bildrecht Social Media, KI-Kennzeichnung, Medienanstalten); Treffer als Meldung
  „Rechtsquelle veraltet? -- Skill X pruefen“ ins Briefing, Stand-Datum der Quellen ueberwachen (Hinweis nach 6 Monaten).
- Gate: Test (Themen gesetzt, veraltete Quelle erzeugt Hinweis); keine neuen Kosten (Brave wie bisher).
- Aufwand: klein.

## Etappe C4: Echter CLO-Pruef-Lauf der Vertragsentwuerfe

- Status: geplant
- Ziel / Scope: LUNA beauftragt den CLO mit den vier Entwuerfen (AGB, Kooperationsvertrag, Nutzungsrechte, NDA) und
  seinen Skills. Ergebnis: **Pruefbericht fuer die Anwaeltin** (je Paragraph Ampel, Fundstelle, Risiko, offene Frage)
  als PDF in der Firmenakte bzw. im Vertragswerk, plus ueberarbeitete Texte als **Version 2** (Status Entwurf, Quelle
  „CLO-Agent, ungeprueft“). Datenfluss: nur die Vertragstexte gehen an das Modell (Gemini), keine Kundendaten.
- Gate: Bericht liegt vor, jede Aussage mit Fundstelle; Versionen im Vertragswerk; der CEO liest, bevor etwas an die
  Anwaeltin geht.
- Aufwand: mittel.

## Etappe C5 (getrennt, CEO-Tor Charta): Charta-Anpassung

- Status: geplant
- Ziel / Scope: Charta des CLO auf den Ist-Stand heben -- Schwerpunkt um Influencer-/Werbe-, AGB- und Urheberrecht
  ergaenzen, echte Werkzeuge nennen (Skills, Quellen, Recherche ueber den Researcher, Vertragswerk), Status „Entwurf“
  -> „aktiv“. **Nur der Head of Agents auf ausdrueckliche CEO-Anweisung, mit Diff-Vorlage und Bestaetigung**
  (`AGENTS.md` 3.3).
- Aufwand: klein.

## Nicht-Scope

Keine Rechtsberatung und keine verbindlichen Aussagen; Auswahl/Beauftragung der Anwaeltin bleibt beim CEO (CEO-Tor
Recht + Geld); keine kostenpflichtigen Rechtsdatenbanken (juris, beck-online -- waeren ein neues Abo = CEO-Tor).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md`
(C4: Vertragstexte an Gemini), `docs/datenschutz-ki-nutzung.md` (C4).

## Definition of Done

C1-C4 verifiziert: Skills geladen, Quellen mit Stand, Beobachtung aktiv, Pruefbericht zu den vier Entwuerfen liegt vor
und ist vom CEO gelesen; C5 nach CEO-Anweisung mit bestaetigtem Diff.
