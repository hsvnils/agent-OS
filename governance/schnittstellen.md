# Schnittstellen — kanal-agnostischer Kern + Adapter-Roadmap

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt uebergeordnet; bei Widerspruch gilt `AGENTS.md`.
> Referenziert aus [`orchestrierung.md`](orchestrierung.md). Technischer Plan: [`../ORCHESTRATOR_PLAN.md`](../ORCHESTRATOR_PLAN.md).

## Grundsatz: Kern vs. Kanal trennen

Die **HoA-Logik** (Auftragsannahme, Zerlegung, Delegation, Buendelung) ist strikt getrennt von der
**Ein-/Ausgabe (I/O-Kanal)**. Der HoA-Kern nimmt eine Nachricht entgegen und liefert eine Antwort als
**Stream** — voellig unabhaengig davon, ueber welchen Kanal sie kam.

Jeder Front-end-Kanal programmiert gegen eine schmale, dokumentierte Schnittstelle (Adapter-Pattern):

```
Kanal-Adapter  --send_to_core(message)-->  HoA-Kern  --receive_stream()-->  Kanal-Adapter
   (Terminal / Live-Voice / Telegram)        (unveraendert, kanal-agnostisch)
```

**Schnittstellen-Vertrag (ChannelAdapter):**
- `send_to_core(message)` — uebergibt Text (spaeter Audio) an den Kern.
- `receive_stream()` — liefert die Antwort als Stream zurueck (Text; spaeter Audio/Stream).
- Sitzungs-/Kontextverwaltung (Sitzungs-ID, Verlauf) liegt im Adapter, nicht in der Kernlogik.

So docken neue Oberflaechen an, **ohne den HoA-Kern zu aendern**.

## Adapter-Roadmap

| Adapter | Status | Beschreibung |
|---------|--------|--------------|
| **Terminal** | **fertig** | Streaming-Chat im Terminal; der CEO spricht mit dem HoA und erteilt Anweisungen. |
| **Live-Voice (Browser)** | **jetzt** | Echtzeit-Sprachoberflaeche im Browser auf Basis von Pipecat. Transport: **WebRTC lokal/peer-to-peer** (kein kostenpflichtiger Transport-Dienst). Pipeline: Mikrofon -> VAD/Turn -> STT -> **Bruecke zum HoA-Kern** -> TTS -> Lautsprecher; Barge-in aktiv. Mit **show_panel** (Einblendungen waehrend des Gespraechs). STT/TTS sind kostenpflichtig (CEO-Tor). Code: `orchestrator/channels/voice/`. |
| **Telegram** | **geplant** | Text- UND Sprachnachrichten ueber Telegram (Voice -> STT -> HoA -> Antwort als Text und/oder Voice). Fuer unterwegs. NICHT in diesem Build. |
| **Mock** | intern | Test-Adapter fuer Offline-Self-Checks (kein echtes Modell, keine Kosten). |

## Live-Voice im Browser (Detail)

- **Schichten:** `channels/voice/bridge.py` (framework-unabhaengige Andockstelle Sprache<->HoA-Kern,
  offline testbar), `panels.py` (show_panel), `pipeline.py` (Pipecat-Pipeline, Laufzeit),
  `server.py` (WebRTC-Server + statische Seite), `static/` (minimale Browser-Oberflaeche).
- **show_panel:** Der HoA kann waehrend des Gespraechs Inhalte einblenden — `kostenuebersicht`
  (liest read-only aus `finance/`), `tabelle`, `text/markdown`. Reine Anzeige-Wuensche sind lesend
  und laufen NICHT durch das CEO-Tor; alle anderen Anweisungen gehen durch den HoA-Kern (Tor,
  Gedaechtnis, Delegation). **Keine Secrets in Panels** (Leck-Schutz gilt auch hier).
- **CEO-Tore im Sprachkanal:** Beruehrt eine Anweisung ein Tor (Geld, Recht, Oeffentlichkeit, neue
  externe Kosten, Mandats-/Charta-Aenderung, Datenloeschung), fuehrt der HoA sie NICHT aus, sondern
  antwortet gesprochen mit einer Freigabe-Anfrage und protokolliert sie. (Sprachgebundene
  Freigabe-Bestaetigung folgt spaeter.)
- **Provider:** STT Deepgram (Default), TTS Cartesia ODER ElevenLabs (CEO waehlt); per `config.toml`
  austauschbar. Keys ausschliesslich in `orchestrator/.env` (Capability-Muster: der Adapter erhaelt
  die Faehigkeit, nie den Key).

## Roadmap (Voice-Ausbau)

- **Stufe 2:** „Jarvis-Gesicht" — Orb/Wellenform via Pipecat Voice UI Kit (reine Visualisierung).
- **Stufe 3:** optionale Mac-App-Verpackung via Tauri (.dmg).
- **Spaeter:** Telegram (Text + Voice).

## Anforderung an die Architektur

Live-Voice und Telegram muessen **ohne Aenderung am HoA-Kern** andockbar sein. Der Leck-Schutz
(`.env`-Redaktion) gilt **kanaluebergreifend** — kein Key erscheint je im Klartext, auch nicht ueber Voice
oder Telegram (auch nicht in Panels).
