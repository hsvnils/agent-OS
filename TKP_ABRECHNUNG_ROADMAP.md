# Roadmap: TKP-Abrechnung nach erzielter Reichweite und Reichweiten-Ausgleich

- Status: in Umsetzung
- Stand: 2026-10-27
- Arbeitsbranch: `ai/tkp-abrechnung`
- Basiscommit: `31558c3`
- Naechster Schritt: T1-T3 umgesetzt (CEO-Go 2026-10-27, Empfehlungen E1-E9 angenommen) -- Merge, Deploy (`luna-os` + `luna-telegram`), dann CEO-Abnahme an einem Probe-Angebot je Abrechnungsart (Angebot -> Auftrag -> Kennzahlen -> Rechnungsentwurf, ohne Versand) und Sichtpruefung Desktop/iPad/iPhone. Vor dem ersten echten Kunden: Klauseltexte anwaltlich pruefen (E9).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-27)

1. Dem Kunden statt einer festen Summe einen **TKP anbieten** und **nach der Kampagne** anhand der **tatsaechlich
   erzielten Reichweite** abrechnen.
2. Zusaetzlich eine Angebotsvariante mit Festpreis, bei der **Mehr- oder Minderleistung** gegenueber der vereinbarten
   Reichweite **mit einem TKP X ausgeglichen** wird.

## Bestand (Analyse, read-only)

| Baustein | Stand | Nachweis |
|---|---|---|
| TKP-Kalkulation | Position mit Kontakte x TKP / 1.000 + Produktion, Preis rechnet der Server, **ergibt immer einen Festpreis** | `orchestrator/core/angebote.py:85-95`, `katalog.tkp_preis` |
| Plan-Werte im Auftrag | Kontakte/TKP/Produktion/Preis je Position eingefroren, Katalog wirkt nicht zurueck | `orchestrator/core/postings.py:1-8` |
| Ist-Werte | je Posting Kennzahlen (Screenshot -> Gemini -> „✅ Stimmt“ des CEO); Kontakt = Aufrufe (Reel/Story) bzw. Impressionen (Bild-Post), Messpunkt 7 Tage | `postings.py` `KONTAKT`, `ERINNERN_TAGE` |
| Plan gegen Ist | Gegenwert Ist, Mehrleistung, effektiver TKP **werden schon berechnet** -- aber nur im Projektbericht angezeigt, **nicht abgerechnet** | `postings.vergleich` (`postings.py:272`), `projektbericht.py:191-224` |
| Vorlage „erst spaeter abrechnen“ | Provision (Etappe 23): Position ohne Betrag im Angebot, Euro-Wert erst in der Rechnung, Festschreiben gesperrt solange offen, Vorkasse nur vom Festpreis-Anteil | `angebote._provision`, `provision_abgerechnet` |
| Rechnung aus Auftrag | uebernimmt Positionen 1:1, keine negativen Positionen erlaubt | `rechnungen.entwurf_aus_auftrag`, `angebote.py` „negativer Preis“ |
| Vertragstext | AGB/Vertragsentwurf § 8: „Reichweiten sind Planungsgroessen ... keine Garantie“ -- widerspricht kuenftig Variante 2/3 | `orchestrator/core/vertrag_entwuerfe.py:100` |

Fazit: Messung und Rechenweg sind da. Es fehlen die **Abrechnungsart im Angebot**, die **Uebernahme der Ist-Werte in
die Rechnung**, eine **Ausgleichsposition (auch als Abzug)** und der **Vertragstext**.

## Die drei Abrechnungsarten (je Angebot, gilt fuer alle TKP-Positionen)

| Art | Angebot zeigt | Rechnung | Beispiel Reel: Plan 37.000, TKP 30 EUR, Produktion 490 EUR; Ist 45.000 |
|---|---|---|---|
| **Festpreis** (heute) | 1.600 EUR | 1.600 EUR | 1.600 EUR (Bericht zeigt +240 EUR Mehrwert) |
| **Nach Reichweite** | „30 EUR TKP je 1.000 Aufrufe + 490 EUR Produktion · voraussichtlich 1.600 EUR · hoechstens X EUR“ | Ist x TKP + Produktion | 45.000 x 30 / 1.000 + 490 = **1.840 EUR** |
| **Festpreis mit Ausgleich** | 1.600 EUR + Klausel „Abweichung ueber ±10 % gleichen wir mit TKP Y aus“ | 1.600 EUR + Position „Ausgleich Mehrleistung“ bzw. Abzug „Ausgleich Minderleistung“ | +8.000 Aufrufe (21,6 %) x 30 EUR = **+240 EUR** (bei Ausgleichs-TKP 20 EUR: +160 EUR) |

Minderleistung, gleiches Beispiel mit Ist 30.000: Nach Reichweite 1.390 EUR; mit Ausgleich -7.000 (18,9 %) x 30 EUR =
**-210 EUR** -> 1.390 EUR. Die **Produktion bleibt immer voll** berechnet.

## Entscheidungen fuer den CEO (mit Empfehlung)

- **E1 Ebene:** Abrechnungsart **je Angebot** (alle TKP-Positionen gleich), nicht je Position. *Empfehlung: je Angebot.*
- **E2 Was ist ein Kontakt:** wie im Projektbericht -- Reel/Story = Aufrufe, Bild-Post = Impressionen, Stand **7 Tage nach
  Veroeffentlichung**, Nachweis = Insights-Screenshots im Projektbericht. Steht woertlich im Angebot. *Empfehlung: so lassen.*
- **E3 Bezugsgroesse:** Ausgleich ueber die **Summe der Kampagne** (ein schwaches Reel wird von einem starken aufgefangen),
  nicht je Posting. *Empfehlung: Kampagnensumme.*
- **E4 Toleranz (nur Ausgleich):** Bagatellgrenze **±10 %** -- darin kein Ausgleich, darueber die **ganze** Abweichung.
  Je Angebot aenderbar (0 % = immer ausgleichen). *Empfehlung: 10 %, ganze Abweichung.*
- **E5 Ausgleichs-TKP:** Standard = vereinbarter TKP, je Angebot aenderbar (z. B. Mehrleistung guenstiger). *Empfehlung:
  ein Wert fuer beide Richtungen.*
- **E6 Deckel:** Nach Reichweite **hoechstens X EUR** (Standard: voraussichtliche Summe +25 %); Ausgleich nach oben
  hoechstens +25 % vom Media-Wert. Nach unten kein Deckel, aber Produktion bleibt. Aenderbar/abschaltbar. *Empfehlung:
  +25 %, weil Kunden ein Budget freigeben muessen.*
- **E7 Minderleistung:** als **Abzug auf der Rechnung** (Position mit Minus). Nachlieferung (Bonus-Story statt Geld) als
  spaetere Option. Ist schon mehr per Vorkasse bezahlt als geschuldet -> vorhandene Gutschrift. *Empfehlung: Abzug.*
- **E8 Vorkasse:** bei „Nach Reichweite“ nur auf Produktion (+ optional % der voraussichtlichen Summe), wie bei der
  Provision. *Empfehlung: so.*
- **E9 Vertrags-/Angebotstext:** Klauseltext fuer beide Varianten und angepasster § 8 im Vertragsentwurf entstehen als
  **Entwurf (Claude Code, ungeprueft)** -- vor dem ersten echten Einsatz anwaltlich pruefen (CEO-Tor Recht).

## Etappen

Entscheidungen E1-E9: vom CEO am 2026-10-27 wie empfohlen angenommen („Empfehlungen passen, Go fuer T1-T3“).

### T1: Abrechnungsart im Angebot und Auftrag

- Status: umgesetzt (2026-10-27) -- Kopf-Feld `abrechnung` (`core/tkp_abrechnung.pruefen`), mit dem Auftrag eingefroren
  und dort aenderbar wie die uebrigen Formularfelder; Angebot/Auftrag zeigen „Gesamt (voraussichtlich)“, Hoechstbetrag und
  Klauseltext (PDF beider Layouts, Belegblatt); Vorkasse bei „nach Reichweite“ nur auf Produktion + Festpreis-Positionen;
  Inhalts-Hash alter Angebote unveraendert. LUNA-OS: Block „📊 Abrechnung der Reichweite“ mit Toleranz, Ausgleichs-TKP,
  Deckel und Vorschau „hoechstens“. Abweichungen: Klauseltext wird aus den Werten erzeugt (kein frei aenderbarer
  Textbaustein); Kleinunternehmer-Waechter prueft wie bisher die Rechnung, nicht das Angebot.

- Ziel / Scope: Schalter „Abrechnung“ (Festpreis / Nach Reichweite / Festpreis mit Ausgleich) im Angebots-Editor mit
  Feldern Toleranz, Ausgleichs-TKP, Deckel; Server prueft und friert alles mit dem Auftrag ein. Angebotssumme bei „Nach
  Reichweite“ als „voraussichtlich“ (+ „hoechstens“); PDF (Angebot, Auftragsbestaetigung) mit Rechenweg und Klauseltext
  (Textbaustein, aenderbar). Kleinunternehmer-Waechter rechnet mit dem Deckel. Festpreis bleibt Standard -- alte
  Angebote unveraendert.
- Gate: Tests (drei Arten, Grenzwerte, Deckel, Einfrieren im Auftrag, Altangebote unveraendert) mit Gegenprobe; PDF
  gesichtet; Doku-Check gruen; Browser-Pruefung 1300/820/402 px (ehrlich: ohne Browser durch den CEO).
- Risiko / Rueckweg: additiv (neues Feld, Standard = Festpreis) -> abschalten = Feld ignorieren.
- Aufwand: mittel.

### T2: Rechnung mit Ist-Werten und Ausgleich

- Status: umgesetzt (2026-10-27) -- „Rechnung erstellen“ uebernimmt die bestaetigten Kontakte (`rechnungs_positionen`):
  nach Reichweite je TKP-Position eine Media-Zeile (erzielt x TKP, Kontakte je Position gedeckelt) + Produktionszeile; mit
  Ausgleich eine Zeile „Reichweiten-Ausgleich: Mehr-/Minderleistung“ (einzige erlaubte negative Position). Betrag rechnet
  immer der Server (`berechnen`); abweichender Wert nur mit Grund; fehlende Messung sperrt das Festschreiben; erneutes
  „Rechnung erstellen“ zieht neue Messwerte in den bestehenden Entwurf nach (von Hand gesetzte Werte bleiben). Vorkasse wird
  wie bisher als Abzug verrechnet. Projektbericht als PDF-Anlage: nicht umgesetzt (Bericht geht wie bisher eigenstaendig
  raus).

- Ziel / Scope: „Rechnung erstellen“ uebernimmt die bestaetigten Kontakte aus den Postings (Kampagnensumme): bei „Nach
  Reichweite“ Betrag je Position aus Ist (mit Deckel), bei „Ausgleich“ zusaetzliche Position „Ausgleich Mehrleistung“
  bzw. „Ausgleich Minderleistung“ (erste erlaubte negative Position, nur dieser Typ). Rechnung zeigt Plan, Ist, TKP,
  Prozent. **Festschreiben gesperrt**, solange Kennzahlen fehlen (wie offene Provision); Ist-Wert von Hand nur mit Grund
  (bestehende Regel „Preis ueberschreiben mit Grund“). Projektbericht optional als PDF-Anlage. Vorkasse wird verrechnet;
  Ueberzahlung -> Gutschrift.
- Gate: Tests (Ist aus Postings, Toleranz knapp drin/knapp drueber, Deckel, Minus-Position nur als Ausgleich, Sperre bei
  fehlenden Kennzahlen, Vorkasse-Verrechnung) mit Gegenprobe; Rechnungs-PDF gesichtet; Doku-Check gruen.
- Risiko / Rueckweg: festgeschriebene Rechnungen bleiben unveraenderlich; Fehler -> Storno + Korrektur (vorhanden).
- Aufwand: mittel bis gross (negative Position und Summenlogik sind neu).

### T3: Bericht, Handlungsbedarf, Vertragstext

- Status: umgesetzt (2026-10-27) -- Projektbericht schreibt „abgerechnet …“ statt „Mehrwert“, Handlungsbedarf
  „Rechnung nach Reichweite erstellen“ (sobald alle TKP-Postings gemessen und noch keine Rechnung da), Vertragsentwurf
  § 8 = Platzhalter `{Reichweite}` + `REICHWEITE_KLAUSELN` je Art (Entwurf; die in LUNA-OS schon geladene Vorlage v1 bleibt
  unveraendert -- neue Fassung nur nach anwaltlicher Pruefung), Register-Eintrag. Tests `test_tkp_abrechnung.py` (16) +
  7 Gegenproben rot, Suite gruen.

- Ziel / Scope: Projektbericht nennt bei Abrechnung nach Reichweite/Ausgleich „abgerechnet“ statt „Mehrwert“;
  Handlungsbedarf „Kennzahlen komplett -> Rechnung nach Reichweite erstellen“; Vertragsentwurf § 8 in drei Varianten
  je Abrechnungsart (Entwurf, E9); Eintrag in `docs/entscheidungs-register.md`.
- Gate: Tests Bericht/Handlungsbedarf; Doku-Check gruen; CEO-Abnahme an einem Probe-Auftrag (Angebot -> Auftrag ->
  Kennzahlen -> Rechnung, ohne Versand).
- Aufwand: klein.

## Nicht-Scope

- Automatisches Abholen der Kennzahlen bei Meta (Meta-Anbindung verworfen 2026-09-29); Ist kommt wie heute aus den
  bestaetigten Screenshots.
- Versand an Kunden (bleibt CEO-Klick), echter Einsatz der Klauseltexte vor anwaltlicher Pruefung.
- Nachlieferung statt Geld (spaetere Option), Abrechnung nach Klicks/Verkaeufen (dafuer gibt es die Provision).
- Live-Daten, `.env`, Dienste, Charta-Dateien.

## Dokumentationspflicht bei Umsetzung

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md` (E1-E9),
`docs/bekannte-fehler.md` bei Funden, `docs/datenfluesse.md` (nur falls neue Verbindung -- erwartet: keine),
`docs/verfahrensdokumentation-buchhaltung.md` (negative Ausgleichsposition, Ist-Werte als Rechnungsgrundlage).
