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

## Stand (M1)

- Menueleisten-Orb (NSStatusItem, `.accessory`-Policy), drei Zustaende.
- „Mit LUNA sprechen…" -> `/api/chat` der lokalen LUNA, Antwort als Dialog.
- „Verbindung pruefen" (Ping `GET /`), Live-Status im Menue.
- „Not-Aus" schreibt ein Sperr-Flag (`~/.luna_orb_killswitch`), das der kuenftige Aktuator vor jeder
  Aktion prueft.

## Naechste Milestones

- **M2** — On-Screen-Awareness (vorderste App, Accessibility-Baum, Screenshot) + App-Wissen.
- **M3** — Aktuator mit Tor (Allowlist/Vorschau/Bestaetigung/Not-Aus/Audit) + erste TextEdit-Aktion.
- **M4** — Voice-Schleife am Orb (Mikrofon -> /api/chat -> TTS).
