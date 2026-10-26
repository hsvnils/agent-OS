# Roadmap: Netz-Agent in Quarantaene (nur er geht ins Internet)

- Status: in Umsetzung
- Stand: 2026-10-26
- Arbeitsbranch: `ai/netz-agent`
- Basiscommit: `3158621`
- Naechster Schritt: Q3 eine Woche beobachten (bis 2026-11-02); Q4 wartet auf CEO-Go.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-23)

„Ein Agent, der nur klare Aufgaben bekommt, dann ins Netz geht, um sie zu erledigen, mit dem Ergebnis wiederkommt und es
einem anderen Agenten gibt -- damit der Agent im Internet keinen Zugriff auf unsere Dateien und Infos hat, und als Schutz
gegen Prompt Injection.“ Zusatz: **Alle anderen Agenten fuehren keine freien Websuchen durch.**

Prinzip (bekannt als Quarantaene- bzw. Dual-LLM-Muster): **Wer fremde Inhalte liest, darf nichts; wer etwas darf, liest
keine fremden Inhalte ungefiltert.**

## Ausgangslage (read-only, 2026-10-23)

- Die Websuche als Chat-Werkzeug haelt nur der Researcher (Agent 15, `web_research`, Brave). Er laeuft aber im Container
  `luna-telegram`, der das ganze Repo und die komplette `orchestrator/.env` sieht (Bind-Mount `/volume1/docker/ki-unternehmen`).
- Direkt ins Netz gehen ausserdem: 24/7-Watcher (GitHub-API + Brave je Abteilung), Content-Feed (Brave), Modell-Radar
  (Herstellerseiten, Artificial Analysis, Ollama-Bibliothek), Rechtsquellen (Gesetzestexte), Impressum-Vorschlaege und
  Innovations-Scouting (Brave). Letzte 7 Tage: 18 Recherchen (alle Brave), ~4.000 GitHub-Abfragen, 65 Watch-Funde.
- Gefundene Texte gehen heute an LUNAs Chat-Modell mit allen Werkzeugen; abgesichert durch PROMPT_INJECTION_SCHUTZ I1-I4
  (markieren, Handlungs-Sperre, Link-Filter, Protokoll).
- **Nicht betroffen (bleiben, wo sie sind):** feste Daten-Schnittstellen ohne freies Surfen -- Google (Mail, Kalender,
  Drive), All-Inkl, Telegram, Boersen-/Krypto-APIs, EZB-Kurse, OSV, Kartendienste, kuenftig die App-Datenbank.

## Zielbild

```
LUNA / Abteilungen ──Aufgabe (nur die Frage, keine internen Daten)──▶ netz_queue/auftraege/
                                                                        │
                                       Container luna-netz (eigener, ohne LUNA-Dateien, ohne LUNA-.env)
                                       sucht (Brave), oeffnet nur Treffer-Seiten, fasst zusammen
                                                                        │
LUNA ◀──Ergebnis-Formular (Antwort, Fakten, Quellen; Laengen geprueft)── netz_queue/ergebnisse/
      └─ Pruefung beim Empfang: Schema, Laengen, input_guard (I1-I4), bleibt „fremde Daten“
```

## Entscheidungen fuer den CEO (Q0)

1. **Modell im Netz-Agenten** -- **entschieden 2026-10-23: Claude-API** (CEO, statt Gemini; Budget laut CEO 100 USD/Monat,
   Abrechnung vor Q2 klaeren: das Claude-Max-Abo ist kein API-Guthaben). Urspruengliche Empfehlung **Gemini Flash (Gratis-Stufe)** -- es sieht
   nur oeffentliche Webseiten und die Frage, keine internen Daten. Alternative: lokales Modell auf dem MACO470 (dann
   braucht der Container Zugang ins Heimnetz, was Q4 widerspricht).
2. **Charta** -- **entschieden 2026-10-23: wie empfohlen.** Empfehlung: der Netz-Agent ist ein **technischer Arbeiter des Researchers** (keine eigene Charta, keine
   Gespraeche), die Capability `web_research` wandert vom Researcher zum Netz-Agenten; der Researcher formuliert die
   Aufgaben und bewertet die Ergebnisse. Das ist eine **Charta-Aenderung** an `agents/15_researcher.md` (HoA mit Diff, CEO-
   Bestaetigung).
3. **Regel verbindlich machen** -- **entschieden 2026-10-23: ja, nach Q3.** (Q5): „Nur der Netz-Agent ruft freie Webseiten und Websuchen ab“ in `AGENTS.md` 5.7 und
   `governance/zugriffs-policy.md` -- Aenderung der kanonischen Regeln, daher ausdrueckliches CEO-Go.

## Etappe Q1: Container und Warteschlange (ohne Modell)

- Status: verifiziert 2026-10-23 (27d2f57; Container `luna-netz` sieht nur `netz_agent` und `netz_queue`; Umgebung nur `BRAVE_API_KEY` und `GPG_KEY` -- letzterer ist der oeffentliche Signatur-Fingerabdruck des Python-Basis-Images, kein Geheimnis; Probe-Auftrag 8 Treffer, 2 Seiten; BF-73 DNS direkt nach Start beobachten)
- Ziel / Scope / Nicht-Scope: neuer, eigenstaendiger Ordner `netz_agent/` (nur Standardbibliothek, **importiert nichts aus
  `orchestrator/`**); Container `luna-netz` in `deploy/docker-compose.yml` mit genau zwei Mounts: `netz_agent/` (nur
  lesen) und `netz_queue/` (lesen/schreiben); eigene `netz_agent/.env` nur mit `BRAVE_API_KEY` (nicht im Git); Nutzer ohne
  Root, Dateisystem sonst nur lesend, kein Port nach aussen. Ablauf: Auftrag `netz_queue/auftraege/<id>.json` -> Brave-
  Suche -> Seiten **nur aus den Suchtreffern** oeffnen (nur http/https, Port 80/443, keine Weiterleitung auf private oder
  lokale Adressen, hoechstens 1 MB und 15 s je Seite, hoechstens 5 Seiten je Auftrag) -> Rohtreffer als Ergebnis-Datei.
  Seite `netz_queue/` nicht im Git, vom Deploy ausgenommen. Nicht-Scope: Modell, Umstellung der bestehenden Wege.
- Gate: Tests (Auftrag -> Ergebnis, private Adressen und Weiterleitungen abgelehnt, Groessen-/Zeitgrenzen, keine Datei
  ausserhalb von `netz_queue/` lesbar), Suite und Doku-Check gruen.
- Verifikation: nach dem Deploy (CEO) im Container `ls /app` -> erwartet: nur `netz_agent` und `netz_queue`; `env | grep
  -c KEY` -> erwartet: 1 (nur der Brave-Schluessel); ein Probe-Auftrag „Wetter Hamburg heute“ liefert eine Ergebnis-Datei
  mit Treffern.
- Dry-Run: `docker compose config` zeigt die Mounts des neuen Dienstes, bevor er startet; Container zuerst mit `--dry-run`
  (liest Auftraege, ruft nichts ab).
- Risiko / Rueckweg: Container startet nicht -> bestehende Wege laufen unveraendert weiter (noch nicht umgestellt);
  Dienst aus `docker-compose.yml` entfernen.
- Abhaengig von / Aufwand / Risiko: Q0 / mittel / niedrig. **Neubau und Start fuehrt der CEO aus.**

## Etappe Q2: Modell und Ergebnis-Formular

- Status: verifiziert 2026-10-26 (105b5ee; Container `luna-netz` neu erstellt, Probe ueber die NAS-Warteschlange: 8 Treffer, 3 Seiten, Formular mit `claude-haiku-5-5` fuer 0,0014 EUR, LUNA-Pruefung ok -- 4 Fakten, 3 Quellen)
- Ziel / Scope / Nicht-Scope: Modell laut Q0 im Netz-Agenten (eigener Schluessel in `netz_agent/.env`); es bekommt nur
  die Frage und die Seiteninhalte, **keine Werkzeuge**, und liefert ein festes Formular: `antwort` (hoechstens 1.500
  Zeichen), `fakten` (hoechstens 10, je 300 Zeichen, jeweils mit Quellen-Nummer), `quellen` (nur URLs aus den Treffern),
  `unsicher` (ja/nein + Grund). LUNA-Seite: `core/netz_auftraege.py` stellt Auftraege ein, holt Ergebnisse, prueft Schema
  und Laengen, verwirft Abweichungen, schickt alle Texte durch `input_guard` (I1-I4) und protokolliert Verdacht.
  Auftraege werden vor dem Einstellen geprueft: keine Mailadressen, IBAN, Kundennummern, Belegnummern, Dateipfade.
- Gate: Tests (gueltiges Formular, zu lang/falsche Felder/fremde Quelle verworfen, Injection im Ergebnis markiert,
  Auftrag mit internen Daten abgelehnt), Gegenproben, Suite gruen.
- Verifikation: drei echte Testfragen ueber die Warteschlange -> erwartet: drei gueltige Formulare mit Quellen aus den
  Treffern; ein praeparierter Angriffstext im Ergebnis kommt markiert bei LUNA an und sperrt Aktionen (I3).
- Dry-Run: Formular-Pruefung zuerst nur protokollieren, nicht verwerfen.
- Risiko / Rueckweg: Modell liefert unbrauchbare Formulare -> Ergebnis „unsicher“, Researcher meldet; Modell tauschbar.
- Abhaengig von / Aufwand / Risiko: Q1 / mittel / mittel.

## Etappe Q3: Alle Netzwege umstellen

- Status: umgesetzt 2026-10-26 (Netz-Agent: Auftragsart `seiten` (Rohinhalt, RSS/XML, Zeichensatz aus Kopf/`<meta charset>`) und `suche` ohne Formular; LUNA: `NetzProvider` in `WebResearch` (Researcher, Watcher, Content-Feed, Scouting), `such_funktion` fuer Firmen-/Partner-Suche, Seitenabrufe von Firmendaten, Modell-Radar (ausser AA-API) und Rechtsquellen ueber den Netz-Agenten, Brave-Klasse stillgelegt, Systemcheck „Netz-Agent erreichbar“; Wachtest `test_netz_wache.py` (feste Schnittstellen als Liste). Echte Proben vom MACO470: alle 5 Wege ok, 31/31 Gesetzes-Pruefsummen unveraendert, 15/15 Radar-Quellen mit identischen Beitraegen. Abweichung: GitHub-API bleibt feste Schnittstelle (Register). Nachbesserung: Impressum-Kandidaten als ein Sammelauftrag, Netz-Agent holt bis zu 5 Seiten gleichzeitig, Takt 1 s), live 2026-10-26 (Live-Pruefung: Recherche mit Formular ok, Firmen-Suche HTTP 200 mit 8 Feldern, Warteschlange ohne haengende Auftraege; `BRAVE_API_KEY` aus `orchestrator/.env` auf NAS und MACO470 entfernt, `luna-os`/`luna-telegram` neu erstellt, Backoffice-Dienst neu gestartet). Wochen-Beobachtung bis 2026-11-02
- Ziel / Scope / Nicht-Scope: Researcher (`web_research`), Watcher (Brave-Teil), Content-Feed, Innovations-Scouting,
  Impressum-Vorschlaege, Modell-Radar (Herstellerseiten), Rechtsquellen und Skill-/GitHub-Radar laufen ueber den
  Netz-Agenten; `BRAVE_API_KEY` wird aus `orchestrator/.env` entfernt (CEO). Feste Daten-Schnittstellen (siehe oben)
  bleiben. Nicht-Scope: neue Recherche-Funktionen.
- Gate: Tests je umgestelltem Weg; **Wachtest**: kein Modul unter `orchestrator/` ausser `core/netz_auftraege.py` ruft
  Brave, GitHub-Suche oder freie URLs ab (Pruefung im Doku-Check gegen eine Liste erlaubter fester Schnittstellen),
  Gegenprobe; Suite und Doku-Check gruen.
- Verifikation: eine Woche Betrieb -> erwartet: alle Recherchen/Watch-Funde mit Herkunft `netz-agent`; im Container
  `luna-telegram` ist `BRAVE_API_KEY` nicht mehr gesetzt; Wachtest gruen.
- Dry-Run: je Weg zuerst parallel (alter Weg + Netz-Agent, nur alter Weg wirkt), Ergebnisse vergleichen.
- Risiko / Rueckweg: Ergebnisse schlechter oder langsamer -> Weg einzeln per Schalter zurueck auf alt, bis behoben.
- Abhaengig von / Aufwand / Risiko: Q2 / mittel bis gross / mittel.

## Etappe Q4: Heimnetz fuer den Netz-Agenten sperren

- Status: geplant
- Ziel / Scope / Nicht-Scope: Der Container `luna-netz` darf ins Internet, aber nicht ins Heimnetz (NAS-Oberflaeche,
  Fritz!Box, MACO470, LUNA-OS): eigenes Docker-Netz plus Sperrregel fuer private Adressbereiche (DSM-Firewall oder
  `DOCKER-USER`-Regel -- fuehrt der CEO aus, Befehl liefert der Agent).
- Gate: Pruefung aus dem Container.
- Verifikation: aus `luna-netz` `192.168.178.1`, `192.168.178.129:8765` und `192.168.178.184` -> erwartet: keine Verbindung;
  `https://api.search.brave.com` -> erwartet: erreichbar.
- Dry-Run: Regel zuerst anzeigen, Wirkung mit einer einmaligen Probe testen.
- Risiko / Rueckweg: Regel blockiert zu viel -> Regel entfernen (Befehl liegt bei).
- Abhaengig von / Aufwand / Risiko: Q1 / klein / mittel (Synology-Eigenheiten).

## Etappe Q5: Angriffstests und Regel verbindlich

- Status: geplant
- Ziel / Scope / Nicht-Scope: Angriffs-Testreihe gegen den Netz-Agenten (praeparierte Seiten: Anweisungen, versteckter
  Text, Link-Abfluss, uebergrosse Antworten) -- er darf nichts ausser dem Formular liefern; Kennzahlen im CISO-Bericht
  (Auftraege, verworfene Formulare, Verdacht); Regel aus Q0 Nr. 3 in `AGENTS.md` 5.7 und `governance/zugriffs-policy.md`;
  Charta-Aenderung Researcher (Q0 Nr. 2).
- Gate: Testreihe mit Gegenprobe, Doku-Check, CEO-Abnahme.
- Verifikation: Testreihe gruen; CISO-Bericht zeigt die Netz-Agent-Zeile; `AGENTS.md` enthaelt die Regel.
- Dry-Run: Regel- und Charta-Text zuerst als Diff vorlegen.
- Risiko / Rueckweg: reine Doku/Tests.
- Abhaengig von / Aufwand / Risiko: Q3 / klein / niedrig.

## Was der Netz-Agent nicht verhindert

Eine manipulierte Seite kann ihn zu einer **falschen Antwort** bringen (Fehlinformation, kein Datenleck). Dagegen:
Quellen-Pflicht, Feld `unsicher`, mehrere Quellen je Aussage, Entscheidungen bleiben beim CEO; I1-I4 bleiben aktiv.

## Nicht-Scope

Keine neuen Recherche-Funktionen; keine Umstellung fester Daten-Schnittstellen; kein Modell mit Werkzeugen im
Netz-Agenten; keine Kosten (Brave-Gratisstufe, Gemini-Gratisstufe laut Q0).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md`
(neuer Container, Warteschlange, Wege), `docs/datenschutz-ki-nutzung.md` (Modell im Netz-Agenten),
`governance/zugriffs-policy.md`, `AGENTS.md` (Abschnitt 5.7 Regel, Abschnitt 7 `netz_agent/`, `netz_queue/`), `deploy/`
(Compose, Ausschluss), `docs/bekannte-fehler.md` bei Befunden, Charta `agents/15_researcher.md` (nur ueber den HoA).

## Definition of Done

Nur noch der Container `luna-netz` ruft freie Webseiten und Websuchen ab; er sieht keine LUNA-Dateien, keine LUNA-.env
und nicht das Heimnetz; LUNA bekommt von ihm nur gepruefte Formulare, die weiter als fremde Daten gelten; ein Wachtest
verhindert neue direkte Web-Abrufe; die Regel steht in `AGENTS.md`. Abschluss setzt der Agent nach CEO-Abnahme.
