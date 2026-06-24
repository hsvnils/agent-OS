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

## Kostenvoranschlag -- Mobile Kontaktwege (CFO, 2026-06-24)

> Vorbereitung der CEO-Freigabe (AGENTS.md 5.9) fuer „unterwegs erreichbar": Telegram + Handy-Browser jetzt,
> echter Telefon-Anruf spaeter. Einmalige + laufende Kosten geschaetzt.

| Posten | Einmalig | Laufend | Bemerkung |
|--------|----------|---------|-----------|
| Telegram-Bot (Bot API) | 0 | 0 | Bot-Token kostenlos; nur ein Token noetig |
| Telegram-Nutzung (Text) | 0 | nur HoA-LLM je Nachricht | Haiku-Sprechpfad guenstig; Delegation/Umsetzung = Opus |
| Telegram-Nutzung (Sprachnachricht) | 0 | STT 0,4-0,8 ct/Min + TTS 2-6 ct/Min | nur bei Voice-Notizen; gleiche Saetze wie Live-Voice |
| Handy-Browser -- Dev-Tunnel (cloudflared/ngrok) | 0 | 0 | HTTPS-Tunnel zu localhost; nur waehrend der Mac laeuft |
| Handy-Browser -- kleiner VPS (24/7) | 0 | ca. 4-8 EUR/Monat | z. B. Hetzner/Railway/Fly; CPU reicht (STT/TTS/LLM sind API-Calls) |
| (spaeter) Telefon-Anruf via Twilio | ~0 | Nummer ~1 USD/Mon + ~1-2 ct/Min | echter Anruf; eigener GATE, ans Ende verschoben |

> **Fazit CFO:** Telegram ist praktisch **fixkostenfrei** (nur nutzungsabhaengige STT/TTS/LLM wie bisher).
> Fuer den Handy-Browser **24/7** faellt **nur Hosting** an: kostenlos per Dev-Tunnel (solange der Mac laeuft)
> oder ~4-8 EUR/Monat fuer einen kleinen Dauer-VPS. Dominanter Kostentreiber bleibt unveraendert die
> HoA-/Delegations-Reasoning (Opus). Empfehlung: mit Telegram + Dev-Tunnel **ohne Fixkosten** starten; einen
> VPS erst, wenn echter 24/7-Betrieb gewuenscht ist.

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
