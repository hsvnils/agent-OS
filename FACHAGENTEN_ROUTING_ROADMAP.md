# Roadmap: Fachagenten-Routing (LUNA bestimmt die zustaendige Abteilung selbst)
- Status: in Umsetzung
- Stand: 2026-10-05
- Arbeitsbranch: `ai/routing`
- Basiscommit: `e290304`
- Naechster Schritt: R1-R4 live (2026-10-05); R5 laeuft bis 2026-10-19 -- dann „wer wird gefragt“ auswerten und abschliessen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Sofern ich LUNA nach einem bestimmten Agenten/Abteilung frage, wuerde ich nie sagen ‚Frage den CXO nach XYZ‘,
sondern ich wuerde immer einfach die Frage stellen, bspw. ‚Wie hoch ist das monatliche Budget?‘ oder ‚Wie sind unsere
aktuellen Zahlungsbedingungen?‘ An welche Abteilung die Frage geht, muss LUNA selbst entscheiden.“

## Analyse (read-only, 2026-10-05)

- **Wer entscheidet heute?** Das Chat-Modell (Gemini) waehlt selbst, ob es ein Werkzeug nutzt oder einen Fachagenten
  fragt. `delegate` gehoert zum KERN der Werkzeugauswahl und ist bei jeder Nachricht sichtbar
  (`orchestrator/core/werkzeugauswahl.py`, `KERN`).
- **Befund 1 -- keine Zustaendigkeiten:** Die Beschreibung von `delegate` nennt nur Kuerzel
  („an: berater, cao, cfo, cro, ciso, cbo, cpo, cto, cxo, cco, cdo, chro, clo, cko, res, cio, risk“,
  `core/hoa_tools.py` Zeile 57). Was welcher Agent macht -- inzwischen 17 Fachagenten mit neuen Rollen aus A5 --,
  steht nirgends im Blick des Modells. Der System-Prompt (`core/hoa_conversation.py`, `TEXT_SYSTEM_PROMPT`) sagt nur
  „'delegate' fuer Fachfragen an Spezialisten“.
- **Befund 2 -- Werkzeuge statt Agenten:** Viele Sachfragen beantwortet ein Werkzeug direkt (101 Werkzeuge in 12
  Gruppen), z. B. Budget ueber `frage_finance`. Das ist richtig, wird aber in der Fachagenten-Zaehlung
  (`agenten_nutzung/log.jsonl`, nur `delegate`) nicht dem zustaendigen Bereich zugerechnet -- „wer wird gefragt“
  zeigt ein unvollstaendiges Bild.
- **Befund 3 -- Fachagenten ohne Daten:** `delegate` gibt dem Agenten nur Charta, Skills, Watcher-Funde und den
  Aufgabentext. Fuer „Wie sind unsere Zahlungsbedingungen?“ gibt es kein Chat-Werkzeug: Die Regeln stehen im Code
  (`core/zahlungsbedingungen.py`: Zahlungsziel Standard 14 Tage, Vorkasse je Angebot, Frist 7 Tage), im
  Leistungskatalog (`buchhaltung/katalog.json`, Textbausteine) und in der AGB-Vorlage im Vertragswerk. Ein gefragter
  CFO wuerde allgemein statt mit den echten Bedingungen antworten.
- **Datenschutz-Rahmen:** Kunden, Rechnungen und Finanzen haben bewusst **keine** Chat-Werkzeuge
  (`docs/datenschutz-ki-nutzung.md`, CEO 2026-09-29). Geschaeftsregeln ohne Personenbezug (Zahlungsbedingungen,
  Katalog/Preise, AGB-Text) sind davon nicht betroffen.

## Etappe R1: Zustaendigkeitskarte und Routing-Regel

- Status: umgesetzt (2026-10-05) -- `core/zustaendigkeit.py` (`ZUSTAENDIG`, `ROUTING_REGEL`), Beschreibung von `delegate`
  mit Zustaendigkeiten, Regel im System-Prompt. Mehrverbrauch +~320 Token je Nachricht (4.850 -> 5.171 im Mittel);
  Token-Gate der Werkzeugauswahl von 5.000 auf 5.200 angehoben.
- Ziel / Scope: je Agent eine Zeile „wofuer zustaendig“ (aus der Charta abgeleitet, eine Quelle: Charta-Abschnitt
  „Rolle“ bzw. eine kleine Karte im Code, per Test gegen die Charten geprueft) in der Beschreibung von `delegate`;
  Regel im System-Prompt: „Der CEO nennt keine Abteilung. Bestimme selbst, wer zustaendig ist. Reine Datenfragen mit
  dem passenden Werkzeug beantworten; Fach-/Bewertungsfragen an den zustaendigen Agenten; braucht der Agent Zahlen,
  erst die Daten holen und in der Aufgabe mitgeben. In der Antwort kurz nennen, wer geantwortet hat.“
- Gate: Test (alle 17 Agenten in der Karte, Karte passt zu `ALL_AGENT_CHARTERS`); Token-Mehrverbrauch gemessen
  (Ziel unter 600 Token je Nachricht).
- Aufwand: klein.

## Etappe R2: Geschaeftsregeln lesbar machen

- Status: umgesetzt (2026-10-05) -- Werkzeug `geschaeftsregeln` (Zahlungsbedingungen, Mahnwesen, Katalog, Projekt-
  stunde/km-Satz, AGB in Kraft); Test: keine Kunden-/Rechnungsdaten im Ergebnis.
- Ziel / Scope: neues Nur-Lese-Werkzeug `geschaeftsregeln` (Gruppe „finanzen“, Stichwoerter wie Zahlungsbedingung,
  Zahlungsziel, Vorkasse, Preis, Paket, Katalog, AGB, Konditionen): Standard-Zahlungsziel und Vorkasse-Regeln,
  Leistungskatalog (Formate, Pakete, Zuschlaege, Projektstunde/km-Satz), AGB-Fassung in Kraft (Titel/Version/Status).
  **Keine** Kunden-, Rechnungs- oder Kontodaten.
- Gate: Test „keine personenbezogenen Felder im Ergebnis“; Eintrag in `docs/datenfluesse.md` und
  `docs/datenschutz-ki-nutzung.md` (Katalog/Regeln gehen ueber den Chat an Gemini -- ohne Personenbezug).
- Aufwand: klein bis mittel.

## Etappe R3: Zaehlung „wer wird gefragt“ vollstaendig

- Status: umgesetzt (2026-10-05) -- `run_tool` zaehlt Werkzeug-Antworten beim Bereich (`WERKZEUG_BEREICH`), Profil und
  Leistungsbericht zeigen „direkt“ und „ueber Werkzeuge“.
- Ziel / Scope: jede Werkzeug-Antwort wird -- ohne Inhalte -- dem zustaendigen Bereich zugerechnet (z. B.
  `frage_finance`, `geschaeftsregeln` -> CFO; `recherche_beauftragen` -> Researcher; `crm_*` -> CRO;
  `sicherheits_audit` -> CISO; Investment -> CIO). Profil und Leistungsbericht zeigen „direkt gefragt“ (`delegate`)
  und „ueber Werkzeuge“ getrennt. Werkzeuge ohne Fachbereich (Kalender, Mail, System) bleiben bei LUNA.
- Gate: Test (jedes Werkzeug hat genau einen Bereich oder „LUNA“, analog zur Gruppenpflicht der Werkzeugauswahl).
- Aufwand: klein.

## Etappe R4: Routing-Test mit Sachfragen

- Status: umgesetzt (2026-10-05) -- 20 Sachfragen (`tests/test_fachagenten_routing.py`), offline 100 % Werkzeug
  angeboten; Probelauf `scripts/routing_probelauf.py` ueber gemini-2.5-flash: 80 % / 80 % vor dem Nachschaerfen,
  danach 95 % / 100 % / 100 % (Gate 85 %). Zwei Testfragen ersetzt, weil sie Daten brauchten, die LUNA bewusst nicht
  hat (Angebotstext, zu pruefender Text); Wertung: Werkzeug desselben Bereichs zaehlt als richtig (z. B. `brain_suchen`
  = CKO), Rechtsfrage „Verzugszinsen duerfen“ darf an den CLO. Rest-Fehlgriff als BF-56.
- Ziel / Scope: 20 typische Fragen ohne Abteilungsnamen mit erwartetem Bereich/Werkzeug, z. B. „Wie hoch ist das
  monatliche Budget?“ (frage_finance), „Wie sind unsere Zahlungsbedingungen?“ (geschaeftsregeln), „Darf ich im Reel
  Musik aus den Charts nutzen?“ (CLO), „Sieht das Angebot fuer die Kiez Alm verstaendlich aus?“ (CXO), „Was kostet uns
  ein Kameramann pro Tag?“ (CHRO), „Welche Zugaenge sollten wir mal pruefen?“ (CISO). Teil 1 offline: Werkzeugauswahl
  enthaelt das noetige Werkzeug. Teil 2 als Probelauf ueber Gemini (Gratis-Stufe, ohne Kunden-/Mail-Daten, nur
  lesende Werkzeuge) mit Trefferquote.
- Gate: offline 100 %; Probelauf mindestens 85 % richtiger Bereich, Fehlgriffe in `docs/bekannte-fehler.md`.
- Aufwand: mittel.

## Etappe R5: Beobachtung im Betrieb

- Status: laeuft (2026-10-05 bis 2026-10-19)
- Ziel / Scope: nach dem Deploy zwei Wochen „wer wird gefragt“ im Leistungsbericht beobachten; auffaellige
  Fehlgriffe (falscher Bereich, Antwort ohne Daten) nachschaerfen.
- Gate: CEO-Eindruck + Zahlen aus dem Leistungsbericht.
- Aufwand: klein.

## Nicht-Scope

Keine Chat-Werkzeuge fuer Kunden-, Rechnungs- oder Kontodaten (Datenschutz-Entscheidung 2026-09-29); kein neues oder
kostenpflichtiges Modell (CEO-Tor); keine automatische Weitergabe von Fachagenten an andere Fachagenten (Agenten
sprechen nur ueber LUNA); keine Charta-Aenderungen (A6 ist abgeschlossen; Rollen kommen aus den Charten).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` und `docs/datenschutz-ki-nutzung.md`
(R2), `docs/bekannte-fehler.md` (R4), `docs/entscheidungs-register.md`.

## Definition of Done

Sachfragen ohne Abteilungsnamen landen nachweislich beim richtigen Bereich (R4), Zahlungsbedingungen und Katalog
sind mit echten Werten beantwortbar, „wer wird gefragt“ zeigt Werkzeuge und Fachagenten.
