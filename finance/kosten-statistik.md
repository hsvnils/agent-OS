# Kostenstatistik — fortlaufend

> Vom **CFO** monatlich fortgeschriebene Kostenstatistik je Agent/Posten. **Alte Monate bleiben als
> Historie erhalten.** Rohdaten kommen vom **CDO**; Budget-Abgleich gegen `finance/budget.md`.
> Erfasste Kostenarten: Token-/API-Ausgaben je Agent, Tool-Abos, Pipeline-Kosten (z. B. Video-Cutter).
> Siehe `AGENTS.md`, Abschnitt 5.9 „Kosten & Budget".

## Geschaetzte Kosten -- Live-Voice-Kanal (CEO-Tor, am 2026-06-23 freigegeben)

> Neue externe kostenpflichtige Dienste: STT (Deepgram) + TTS (Cartesia ODER ElevenLabs). Der
> WebRTC-Transport ist lokal/peer-to-peer und **kostenlos**. Ist-Kosten erscheinen ab Nutzung in der
> Monatsstatistik unten.

| Posten | Schaetzung | Bemerkung |
|--------|-----------|-----------|
| STT Deepgram | grob 0,4-0,8 Cent/Min | Streaming-Transkription, deutsch |
| TTS Cartesia | grob 1-2 Cent/Min | niedrigste Latenz |
| TTS ElevenLabs | grob 2-6 Cent/Min | beste deutsche Stimmqualitaet (alternativ zu Cartesia) |
| HoA-Reasoning (Opus) | ca. 0,12-0,25 USD je Anweisung | groesster Kostentreiber, nicht voice-spezifisch |

> Faustregel: STT/TTS liegen im niedrigen Centbereich pro Gespraechsminute; der dominante Kostentreiber
> bleibt die HoA-Reasoning (Opus) pro Anweisung. Budget wird vom CEO in `budget.md` festgelegt.

## Monats-Soll-Ist (Uebersicht)

| Monat (JJJJ-MM) | Budget (EUR) | Ist gesamt (EUR) | Differenz | Trend | Groesster Kostentreiber |
|-----------------|--------------|------------------|-----------|-------|-----------------------|
| `<JJJJ-MM>`     | `<aus budget.md>` | —           | —         | —     | —                     |

## Detail je Monat und Posten

> Fortschreibung: Pro neuem Monat einen neuen Abschnitt „### `<JJJJ-MM>`" **oben** anlegen; Vormonate als
> Historie **unveraendert** lassen.

### `<JJJJ-MM>` (Platzhalter)

| Agent/Posten | Kostenart | Ist (EUR) | Anteil | Bemerkung |
|--------------|-----------|-----------|--------|-----------|
| —            | —         | —         | —      | Noch keine Ist-Kosten erfasst. |
