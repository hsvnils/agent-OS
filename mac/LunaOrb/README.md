# LUNA am Mac — Menueleisten-Orb (Phase 17)

Nativer macOS-Menueleisten-Orb fuer das **Live-Co-Working** (Phase 17). Lebt als Accessory-App in der
Menueleiste (kein Dock-Icon), zeigt den Orb mit drei Zustaenden (ruhig / hoert zu / spricht) und spricht
mit der **lokalen LUNA** (`orchestrator/channels/web`, `127.0.0.1:8765`). Steuerung des Rechners +
On-Screen-Awareness folgen in den naechsten Milestones — siehe `../../PHASE17_PLAN.md`.

## Bauen

```bash
cd mac/LunaOrb
swift build            # Debug-Binary nach .build/debug/LunaOrb
```

Voraussetzung: Xcode / Swift-Toolchain (getestet mit Swift 6.3 / Xcode 26).

## Starten

```bash
./.build/debug/LunaOrb   # Orb erscheint oben rechts in der Menueleiste
```

Die **lokale LUNA** muss laufen, damit „Mit LUNA sprechen…" funktioniert:

```bash
cd <repo>
source .venv/bin/activate
python -m orchestrator.channels.web        # http://127.0.0.1:8765
```

Abweichende URL: Env `LUNA_LOCAL_URL` setzen.

## Stand (M1–M4)

- **M1** Menueleisten-Orb (NSStatusItem, `.accessory`), drei Zustaende; „Mit LUNA tippen…" -> `/api/chat`;
  „Verbindung pruefen"; „Not-Aus" -> Sperr-Flag `~/.luna_orb_killswitch`.
- **M2/M3** On-Screen-Awareness + App-Wissen + Aktuator laufen serverseitig (Paket `runner/`, LUNA-Tools).
  Menue-Schalter „Modus: Sofort/Bestaetigen" (`~/.luna_orb_mode`).
- **M4** **Live-Gespraech** (`VoiceSession.swift`): „Live-Gespraech starten" im Menue ->
  Mikrofon (AVAudioEngine, Echo-Cancellation) -> SFSpeechRecognizer (de-DE) -> `/api/chat` ->
  Antwort per ElevenLabs (`/api/tts`, Fallback System-Stimme). **Barge-in**: reinreden stoppt die Wiedergabe.
  Orb spiegelt zuhoeren/sprechen.

### Live-Gespraech testen
1. Lokale LUNA starten (siehe oben), Orb starten.
2. Orb anklicken -> **„Live-Gespraech starten"**. Beim ersten Mal **Mikrofon + Spracherkennung erlauben**.
3. Sprich; bei Sprechpause antwortet LUNA hoerbar. Du kannst jederzeit **reinreden** (Barge-in).
4. **„Gespraech beenden"** stoppt die Schleife.

> Berechtigungen: das Binary traegt eine eingebettete `Info.plist` mit den Mikrofon-/Sprach-Texten.
> Falls macOS keinen Dialog zeigt, hilft das Verpacken in ein echtes `.app`-Bundle (geplanter Haerteschritt).

## Naechste Schritte

- **NAS-Bruecke** („eine LUNA, zwei Gesichter") — gemeinsamer Zustand statt lokaler Insel.
- Allowlist wachsen lassen (weitere Apps/Verben, gegated), Cursor-Steuerung, Claude Computer-Use (ab 01.07.).
- Verpacken als signiertes `.app` (Autostart via launchd).
