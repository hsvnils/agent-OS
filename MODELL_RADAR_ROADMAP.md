# Roadmap: Modell-Radar (Artificial Analysis + Hersteller-News)

- Status: geplant
- Stand: 2026-10-13
- Arbeitsbranch: `ai/modell-radar`
- Basiscommit: `b40d9d1`
- Naechster Schritt: CEO-Go fuer R1-R3 und Entscheidung zum Gratis-Konto bei Artificial Analysis abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-13)

„Der Researcher soll https://artificialanalysis.ai/de ueberwachen, um Vorschlaege fuer Verbesserungen und/oder
Modellwechsel zu machen. Das Gleiche fuer die Webseiten der fuehrenden KI-Anbieter, damit wir die neuesten News der
Hersteller nicht verpassen.“

## Analyse (read-only, 2026-10-13)

- Register: `artificialanalysis.ai` kommt bisher nur als Quelle einer Einzelbewertung vor (Nemotron), keine Ueberwachung.
- Vorhanden: Watcher (Phase 12, `core/scheduler.py`, `core/watch_config.py`) -- alle 6 h GitHub + Brave-Suche **einer**
  Abteilung, regelbasiert, ohne LLM; Funde im Watch-Store, Researcher (Agent 15) mit Research-Tickets. Feste Quellen
  (Feeds/Seiten) und ein Modellvergleich fehlen.
- **Artificial Analysis** (geprueft 2026-10-13): `robots.txt` erlaubt alles; es gibt eine **kostenlose Daten-API**
  (`/api/v2/data/llms/models`: Intelligenz-Index, Tempo, Preise je Modell; 1.000 Abrufe/Tag, Schluessel ueber ein Gratis-Konto,
  **Quellenangabe Pflicht**, Nutzungsbedingungen beachten). Die API ist der saubere Weg -- die Webseite selbst abzugreifen ist
  unnoetig und fehleranfaellig.
- **Hersteller-Quellen** (Erreichbarkeit geprueft 2026-10-13):
  - mit Feed: OpenAI News (RSS), Google DeepMind Blog (RSS), Google AI Blog (RSS), Qwen Blog (RSS), Ollama Releases
    (GitHub-Atom, unser lokaler Modell-Server), DeepSeek Releases (GitHub-Atom).
  - ohne Feed (Seite lesen, neue Artikel-Links erkennen): Anthropic News, Mistral News, Meta AI Blog, xAI News.
  - Aenderungsprotokolle der APIs, die wir nutzen: Gemini-API-Changelog, Anthropic Release Notes, OpenAI Changelog
    (wichtig fuer **Abschaltungen und Preisaenderungen** unserer Modelle).
- Genutzte Modelle stehen in `orchestrator/config.toml` und der NAS-`.env` (Chat = Gemini, Rueckfaelle, Fachagenten, lokal
  qwen3:14b auf dem MACO470) -- der Radar liest nur die **Namen**, nie Schluessel.

## Etappe R1: Hersteller-News

- Status: geplant
- Ziel / Scope: Researcher prueft die Quellen oben **einmal taeglich** (Feeds bzw. News-Seite, je Quelle robots.txt geachtet,
  eigener User-Agent, kein Massenabruf). Neue Beitraege werden dedupliziert gespeichert und regelbasiert eingestuft:
  - **🔴 sofort per Telegram:** betrifft ein Modell, das wir nutzen (Abschaltung/„deprecat“, Preisaenderung, API-Aenderung).
  - **🟡 Wochenuebersicht:** neue Modelle, Preissenkungen, grosse Releases.
  - **⚪ nur Archiv:** alles andere.
- Nicht-Scope: Volltexte speichern (nur Titel, Link, Datum, kurzer Anriss), Social Media der Hersteller.
- Gate: Tests mit aufgezeichneten Feeds/Seiten (kein Netz), Einstufung, keine Doppelmeldung, Gegenprobe rot.
- Aufwand: mittel.

## Etappe R2: Artificial Analysis -- Modellvergleich und Vorschlaege

- Status: geplant
- Ziel / Scope: taeglich die Modellliste ueber die Gratis-API (gecacht, weit unter dem Limit). Abgleich mit **unseren**
  Modellen je Einsatz (Chat, Rueckfall, Fachagenten, lokal): Vorschlag, wenn ein anderes Modell bei mindestens gleicher
  Qualitaet deutlich guenstiger oder schneller ist, oder bei gleichem Preis deutlich besser. Vorschlag = **Antrag
  „Modellwechsel pruefen“** mit Kostenvoranschlag des CFO (AGENTS.md 5.9) -- **nie automatisch wechseln** (neues Modell =
  CEO-Tor). Quellenangabe „Daten: Artificial Analysis“ ueberall, wo Werte gezeigt werden.
- Voraussetzung (CEO-Tor, kostenlos): Gratis-Konto bei Artificial Analysis anlegen, Schluessel `ARTIFICIALANALYSIS_API_KEY`
  in die NAS-`.env` (CISO-Freigabe). Ohne Schluessel laeuft R1/R3 trotzdem.
- Gate: Tests mit aufgezeichneter API-Antwort, Schwellen, keine Wiederholung desselben Vorschlags, Gegenprobe rot.
- Aufwand: mittel.

## Etappe R3: Uebersicht und Wochenbericht

- Status: geplant
- Ziel / Scope: LUNA-OS (LUNA & System -> Wissen bzw. eigener Reiter „🧭 Modell-Radar“): Neuigkeiten je Hersteller (Filter
  wichtig/alle), Tabelle „unsere Modelle vs. beste Alternativen“ (Qualitaet, Preis, Tempo), offene Vorschlaege.
  Wochenbericht montags mit dem Leistungsbericht per Telegram (Top-News + Vorschlaege); Zusammenfassung regelbasiert, optional
  ueber das lokale Modell (kostenlos).
- Gate: Tests; Browser Rechner/iPad/iPhone.
- Aufwand: klein bis mittel.

## Nicht-Scope

Kein automatischer Modellwechsel, keine kostenpflichtigen Datenquellen (kommerzielle API von Artificial Analysis), keine
Speicherung kompletter Artikel.

## Entscheidungen fuer den CEO

1. Gratis-Konto bei Artificial Analysis anlegen (Schluessel kostenlos, Quellenangabe Pflicht)? Empfehlung: ja.
2. Herstellerliste: Anthropic, OpenAI, Google (DeepMind + Gemini-API), Meta, Mistral, xAI, DeepSeek, Qwen, dazu Ollama --
   passt das, oder weitere (z. B. NVIDIA, Microsoft)?

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neue externe Quellen),
`docs/entscheidungs-register.md`, `orchestrator/governance/dienste_register.py` (Artificial Analysis als Anbieter).

## Definition of Done

Neuigkeiten der Hersteller kommen taeglich an (Wichtiges sofort, Rest woechentlich), Abschaltungen unserer Modelle werden
nicht verpasst, und der Researcher schlaegt begruendete Modellwechsel mit Kosten vor -- entschieden wird beim CEO.
