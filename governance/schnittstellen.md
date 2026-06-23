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
| **Terminal** | **jetzt (Bootstrap)** | Streaming-Chat im Terminal; der CEO spricht mit dem HoA und erteilt Anweisungen. Minimal, nur um den HoA real bedienbar zu machen. |
| **Live-Voice (Jarvis-Stil)** | **geplant — primaer** | Echtzeit-Sprachoberflaeche: Sprache rein -> HoA-Kern -> Sprache raus (niedrige Latenz, freihaendige Dauerkonversation). Technisch: Echtzeit-STT -> Kern -> TTS. NICHT im Bootstrap gebaut. |
| **Telegram** | **geplant** | Text- UND Sprachnachrichten ueber Telegram (Voice -> STT -> HoA -> Antwort als Text und/oder Voice). Fuer unterwegs. NICHT im Bootstrap gebaut. |
| **Mock** | intern | Test-Adapter fuer Offline-Self-Checks (kein echtes Modell, keine Kosten). |

## Anforderung an die Architektur

Live-Voice und Telegram muessen **ohne Aenderung am HoA-Kern** andockbar sein. Der Leck-Schutz
(`.env`-Redaktion) gilt **kanaluebergreifend** — kein Key erscheint je im Klartext, auch nicht ueber Voice
oder Telegram.
