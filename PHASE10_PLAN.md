# PHASE10_PLAN.md — Mobile Kontaktwege: Telegram + Handy-Browser

> **Status: PLAN — wartet auf GATE.** Detailplan zu Phase 10 der `ROADMAP.md`: unterwegs mit dem Head of
> Agents erreichbar. Echter Telefon-Anruf (Phase 10b, Twilio) ist bewusst ans Ende verschoben.
> `AGENTS.md` bleibt kanonisch; Kostenvoranschlag des CFO in `finance/kosten-statistik.md`.

---

## 1. Ziel

Von unterwegs Auftraege/Ideen/Notizen geben, Freigaben erteilen und Statusmeldungen erhalten — per
**Telegram** (Text + Sprachnachricht) und per **Handy-Browser** (die bestehende Live-Voice-Seite ueber HTTPS).

## 2. Teil A — Telegram-Kanal

- **Adapter** `orchestrator/channels/telegram/` am bestehenden **kanal-agnostischen Kern**: Update empfangen
  -> Text bzw. transkribierte Sprachnachricht -> HoA -> Antwort als Text (+ optional Sprachnachricht via TTS).
- **Geteiltes HoA-Gehirn:** Damit Telegram dieselbe konversationelle Qualitaet + Werkzeuge (delegate,
  frage_finance, antrag_*, set_budget) hat wie der Voice-Kanal, wird die HoA-Tool-Schleife
  **kanal-unabhaengig** bereitgestellt (Anthropic-API mit demselben System-Prompt + denselben Tools) und von
  beiden Kanaelen genutzt. `show_panel` entfaellt im Text-Kanal (stattdessen Text/Tabelle).
- **Push:** Abschlussberichte (was/welche Abteilung/Status/zu pruefen) und Freigabe-Anfragen pusht der HoA
  aktiv per Telegram.
- **Wichtig:** Ein echter **Anruf** an einen Telegram-Bot ist nicht moeglich (Bots nehmen keine Anrufe an) —
  daher Sprach**nachricht** (Push-to-talk), nicht Live-Telefonie.
- **Secrets/Governance:** Bot-Token in `orchestrator/.env` (Capability-Muster, CISO); Leck-Schutz; CEO-Tore
  gelten auch hier (gatebehaftete Anweisungen -> Freigabe-Anfrage statt Ausfuehrung).

## 3. Teil B — Handy-Browser (Hosting/HTTPS)

Die bestehende Live-Voice-Seite vom Handy aus nutzen. Mikrofon im mobilen Browser **braucht HTTPS**.
- **Sofort, fixkostenfrei:** HTTPS-**Dev-Tunnel** (cloudflared/ngrok) zu `localhost:7860` -> URL am Handy
  oeffnen. Laeuft, solange der Mac laeuft.
- **24/7:** kleiner Dauer-**VPS** (~4-8 EUR/Monat, CPU reicht) als persistenter Host. **Nicht Vercel**
  (serverless, ungeeignet fuer WebRTC/Langlauf).

## 4. Dateien (geplant)

```
orchestrator/
  core/hoa_conversation.py     # NEU: kanal-unabhaengige HoA-Tool-Schleife (Anthropic-API + Tools)
  channels/telegram/bot.py     # NEU: Telegram-Adapter (Text + Sprachnachricht, Push)
  channels/voice/pipeline.py   # nutzt die geteilte Tool-Schleife (Refactor, Verhalten gleich)
  tests/test_telegram_bridge.py# NEU: Offline-Self-Checks (ohne Token/Netz)
governance/schnittstellen.md   # Telegram-Status aktualisieren
orchestrator/.env(.example)    # TELEGRAM_BOT_TOKEN
```

## 5. Self-Checks (offline, ohne Kosten)

1. Text-Eingang -> HoA-Antwort (Mock-Backend), gleiches Ergebnis wie Voice-Bruecke (Kanal-Gleichheit).
2. Sprachnachricht -> (gemockte) Transkription -> HoA -> Antwort.
3. CEO-Tor: gatebehaftete Anweisung -> Freigabe-Anfrage statt Ausfuehrung.
4. Leck-Schutz: kein Secret in ausgehenden Nachrichten/Logs.
5. Push: Bericht-/Freigabe-Nachricht wird korrekt formatiert erzeugt.

## 6. GATE

- **GATE (jetzt):** Freigabe + (a) **Telegram-Bot-Token** (via @BotFather, kostenlos) in `orchestrator/.env`,
  (b) **Hosting-Wahl** fuer den Handy-Browser: Dev-Tunnel (kostenlos) oder VPS (~4-8 EUR/Monat).
- **Danach:** Offline-Adapter + Self-Checks (ohne Kosten); dann Live-Test (Telegram-Nachricht/Sprachnotiz;
  Handy-Browser ueber die HTTPS-URL).
- **Phase 10b (spaeter):** echter Telefon-Anruf via Twilio (eigener GATE, Kosten).
