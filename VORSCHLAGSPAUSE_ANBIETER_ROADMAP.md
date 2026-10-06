# Roadmap: Investment-Vorschlaege pausieren (systemweit) und Anbieter-Liste

- Status: in Umsetzung
- Stand: 2026-10-06
- Arbeitsbranch: `ai/vorschlagspause-anbieter`
- Basiscommit: `945e1eb`
- Naechster Schritt: P1+P2 gebaut (2026-10-06) -- Deploy, Abnahme durch den CEO; P3 optional.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-06)

„Knopf in den Einstellungen, um Investment-Entscheidungen zu pausieren, sodass keine Vorschlaege gemacht werden, aber
das Tracking im Hintergrund weiterlaeuft“ -- „auch fuer Invest-Vorschlaege im OS, also systemweit“. Ausserdem: „ersichtlich,
von wo die Investment-Tipps/Daten herkommen … vor allem, wenn wir irgendwo einen Zugang bei einem Anbieter eingerichtet
haben, der eventuell Kosten verursacht. Ich brauche quasi eine Liste der Anbieter.“

## Analyse (read-only, 2026-10-06)

**Hintergrund-Jobs** (alle im Bot, `_start_investment_loop`, Takt 5 Minuten):

| Job | Art |
|---|---|
| Tages-Snapshot, Prognose-Pruefung, Insider-Pruefung (07:00), Wochenprognose (Mo 09:00), Scorecard | **Tracking** (bleibt an) |
| Markt-Screen (werktags 16:00), Chancen aus der Wochenprognose | **Vorschlag** |
| Live-Dip-Monitor (10 min): Kauf-/Schutz-Freigaben, „Live-Bewegung“ | **Vorschlag** |
| Echtdepot-Hinweise (10 min) + Zeile im Briefing | **Vorschlag** |
| Paper-Take-Profit „Gewinn mitnehmen?“ | **Vorschlag** |
| Auto-Paper-Trade (werktags 15:00) und Nacht-Krypto (02:00) | **Entscheidung** (Order oder Freigabe) |
| Paper-Stop-Loss (10 min): verkauft automatisch | **Schutz** (Entscheidung offen, s. u.) |

- Vorschlaege entstehen an wenigen Stellen: Freigaben (`ApprovalStore.add`), `InvestmentEngine.vorschlag`, direkte
  Investment-Meldungen in die Outbox. In LUNA-OS erscheinen offene Freigaben als „N Investment-Entscheidung(en) offen“
  (Glocke/Handlungsbedarf) und in der Investment-App.
- Die bestehende Notbremse (`autonomie_pausieren`) stoppt nur den Auto-Trader, nicht Screen, Monitore und Hinweise.
  Der Schalter „Advisory-Alerts (Telegram)“ betrifft nur Echtdepot-Hinweise; Freigaben umgehen die Alert-Filter.
- Einstellungen liegen an **einer** Stelle (`investment/log.jsonl`, Tabelle `settings`, `GET/POST /api/settings`) --
  dort gehoert der neue Schalter hin.

**Anbieter:** Investment nutzt CoinGecko, SEC EDGAR, Finnhub, Alpha Vantage, FMP und Alpaca (Paper) -- laut Code alle in
der Gratis-Stufe, aber **ohne Kostenerfassung**. Systemweit kommen u. a. Anthropic, Gemini, OpenAI, Brave, Google,
Telegram, Meta, All-Inkl, Deepgram, ElevenLabs/Cartesia, GitHub, Supabase und oeffentliche Dienste (EZB, OSV …) dazu.
Kosten erfasst das System heute nur fuer KI-Token (`core/kosten.py`); Daten-Anbieter und Abos fehlen. Ob ein Konto
tatsaechlich kostenpflichtig ist, steht nicht im Code -- das kann nur im jeweiligen Anbieter-Konto geprueft werden.

## Etappe P1: Schalter „Investment-Vorschlaege pausieren“ (systemweit)

- Status: umgesetzt
- Ziel / Scope: Neue Einstellung `vorschlaege_pausiert` (mit Datum, wer) im Investment-Einstellungsspeicher; Schalter in
  ⚙ Einstellungen -> Investment und als Hinweis-Banner in der Investment-App („Vorschlaege pausiert seit … – Tracking
  laeuft“), dazu LUNA-Werkzeug „Investment-Vorschlaege pausieren/fortsetzen“ (Chat/Telegram). Waehrend der Pause:
  keine neuen Freigaben, keine Vorschlaege, keine Investment-Meldungen per Telegram, keine Depot-Hinweise im Briefing (der Depot-Stand bleibt),
  keine Investment-Eintraege in Glocke/Handlungsbedarf und keine Vorschlagsliste in der Investment-App; schon offene
  Freigaben werden ausgeblendet und verfallen wie heute nach 2 Tagen. Tracking-Jobs laufen unveraendert weiter und
  zaehlen mit, wie viele Vorschlaege unterdrueckt wurden (sichtbar im Banner).
- Entscheidung CEO (Empfehlung): **Auto-Trader pausiert mit** (er trifft Entscheidungen). **Paper-Stop-Loss laeuft weiter**
  (Schutz, nur Spielgeld) und meldet nur im Verlauf, nicht per Telegram.
- Nicht-Scope: Echtgeld-Handel (gibt es nicht), Aenderungen an Prognosemodellen.
- Gate: Tests je Vorschlagsstelle (pausiert -> nichts erzeugt/zugestellt, Tracking-Ereignisse weiter geschrieben;
  Gegenprobe rot); Browsertest Rechner/iPad/iPhone.
- Risiko / Rueckweg: zentraler Schalter an mehreren Stellen; Rueckweg = Schalter aus bzw. Commit zuruecknehmen.
- Aufwand: mittel.

## Etappe P2: Anbieter & Datenquellen (Liste in LUNA-OS)

- Status: umgesetzt
- Ziel / Scope: Eine kanonische Anbieter-Liste im Code (`core/anbieter.py`): Name, Bereich (Investment, KI, Mail …),
  wofuer, welche Daten gehen hin, Schluessel-**Namen** (nie Werte), Tarif laut Code (gratis / kostenpflichtig /
  unbekannt), Kostenerfassung ja/nein, Link zur Konto-/Abrechnungsseite. Seite „🔌 Anbieter & Datenquellen“ unter
  LUNA & System: je Anbieter „eingerichtet“ (Schluessel hinterlegt) oder „nicht eingerichtet“, Filter „nur eingerichtete“,
  „moeglicherweise kostenpflichtig“ hervorgehoben. In der Investment-App eine Kachel „Datenquellen“ (nur die
  Investment-Anbieter) und an jedem Vorschlag die Quelle der Daten, soweit bekannt.
- Doku-Check: Ein neuer Schluessel/Dienst im Code ohne Eintrag in der Anbieter-Liste macht `scripts/doku_check.py` rot
  -- die Liste kann nicht veralten.
- Nicht-Scope: Kontostaende/Rechnungen der Anbieter abrufen (dafuer braeuchte es weitere Zugaenge = CEO-Tor).
- Gate: Tests (keine Schluesselwerte in der Antwort, Doku-Check-Gegenprobe), Browsertest.
- Aufwand: mittel.

## Etappe P3: Kosten je Anbieter (optional, nach P2)

- Status: geplant
- Ziel / Scope: Monatliche Kosten je Anbieter aus den Abos der Buchhaltung (Etappe 15) bzw. von Hand im Anbieter-Eintrag;
  Summe in der Anbieter-Liste, Uebernahme in die Kostenstatistik des CFO (`finance/kosten-statistik.md`).
- Aufwand: klein bis mittel.

## Umsetzung (2026-10-06, Go CEO fuer P1+P2, Empfehlungen angenommen)

- P1: Einstellung `vorschlaege_pausiert` im Investment-Einstellungsspeicher; Schalter in ⚙ Einstellungen (eigene Kachel,
  wirkt sofort) und als Hinweis in der Investment-App; LUNA-Werkzeug `investment_vorschlaege_pausieren`. Waehrend der
  Pause: `InvestmentEngine.vorschlag` protokolliert nur (Tabelle `unterdrueckt`), automatische Freigaben laufen ueber
  `_auto_freigabe` (nur protokollieren), Auto-Trader ueber den Schutzschalter aus, Echtdepot-Hinweise und die Hinweise
  im Briefing ruhen (Depot-Stand bleibt), Investment-Meldungen gehen nicht per Telegram raus, Glocke ohne Investment,
  Vorschlagsliste leer. Vom CEO selbst angestossene Freigaben („Andere Summe“) bleiben moeglich; Paper-Stop-Loss
  verkauft weiter (ohne Telegram-Meldung). Tracking-Jobs unveraendert.
- P2: `governance/dienste_register.py` ist die kanonische Anbieter-Liste (25 Anbieter in 7 Bereichen, Stand aus den
  Schluesselnamen, Tarif laut Code, Kostenerfassung, Konto-Link); `register()` fuer den CFO-Ueberblick bleibt
  kompatibel. `GET /api/anbieter` (Gesamtliste nur CEO, Investment-Teil fuer das Modul invest), Seite
  „🔌 Anbieter & Datenquellen“ unter LUNA & System mit Filter „eingerichtet & kann kosten“, Kachel „Datenquellen“ in der
  Investment-App, Quelle an jedem Vorschlag. `scripts/doku_check.py` Pruefung 7: jeder Zugangs-Schluessel im Code
  muss einem Anbieter zugeordnet sein (fand sofort `IG_ANALYSE_BASE_URL`).
- Tests `test_vorschlagspause.py` (6, Gegenproben rot), Browser Rechner/iPad/iPhone.

## Nicht-Scope

Kein automatisches Kuendigen oder Anlegen von Konten, keine neuen Anbieter, keine Aenderung am Paper-Trading-Modus.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md`,
`docs/bekannte-fehler.md`.

## Definition of Done

Ein Schalter stoppt alle Investment-Vorschlaege in Telegram und LUNA-OS, waehrend das Tracking weiterlaeuft; eine Liste
zeigt alle angebundenen Anbieter mit Zweck, Einrichtungsstatus und Kostenhinweis.
