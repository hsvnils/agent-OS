# Reel-Pipeline -- Plan & Design (Facebook, Ad-Umsatz)

> Vollautomatische taegliche Reel-Erstellung aus dem NAS-Spielarchiv, mit 1-Tap-Freigabe und Upload als
> Facebook-Reel. Quelle: CEO-Ziel 2026-07-04 (ROADMAP Backlog). Entscheidungen unten sind CEO-bestaetigt.

## CEO-Entscheidungen (2026-07-07)
- **Freigabe:** 1-Tap pro Reel (Cutter schneidet automatisch, CEO gibt jedes Reel per Telegram/LUNA-OS frei,
  erst dann Upload). Bleibt governance-konform (Auto-Posten = CEO-Tor, AGENTS.md 4).
- **Clip-Auswahl:** Themen-Mix ueber die Spiele hinweg (Tagesthema steuert die Auswahl).
- **Format/Ton:** Facebook-Reel (9:16) mit Originalton (kein Rechte-/Monetarisierungsrisiko durch Fremdmusik).
- **Themen-Tagging v0:** Heuristik (Audio-Energie/Szenendichte, lokal/gratis). Gemini-Video-Tagging spaeter
  optional (CEO-Tor, Paid-Tier, Clips zu Google).

## Architektur (wer laeuft wo)
```
Mac (ffmpeg/whisper, launchd)              NAS (LUNA-OS + Seiten-Token)
-----------------------------              ----------------------------
cutter.reel_daily (taeglich, z. B. 06:00)
  - Clip-Index aktualisieren
  - Tagesthema + gemischte Auswahl (Anti-Doppel)
  - 45s-Reel schneiden (Originalton)
  - outbox/<datum>/reel.mp4 + metadata.json  --->  erkennt neues Reel
                                                    - Antrag (Phase 6) + Video-Vorschau
                                                    - 1-Tap-Freigabe (Telegram)
                                                    - nach OK: Upload FB-Reels (Seiten-Token)
                                                    - Status + fb_video_id zurueck in metadata.json
```
Genutzte Bausteine: bestehende Cutter-Pipeline (`cutter/pipeline.py`), `cutter/luna_bridge.py` (Mac<->LUNA-OS),
Antrags-/Freigabe-Workflow (Phase 6), selbst-erneuernder Seiten-Token (`governance/instagram_token.py`).

## Dateistruktur (NAS)
```
<REEL_ROOT>/
  source/                         Rohmaterial -- bestehende Spiel-Ordner ("HSV vs FCB - 2026-05-01")
  outbox/<datum>/reel.mp4         fertiges Reel je Tag
  outbox/<datum>/metadata.json    Thema, Caption, verwendete Clips, Status, fb_video_id
  state/clip_index.json           gecachter Clip-Index (Dauer/Audio/Energie/Themen)
  state/used.jsonl                Anti-Doppel: welche Clips wann schon dran waren
  logs/
```
Die Spiel-Ordner bleiben unveraendert die Quelle. Pfade sind per Env/CLI konfigurierbar
(`REEL_SOURCE`/`REEL_OUTBOX`/`REEL_STATE`), da die NAS am Mac gemountet ist.

## Bau-Stufen
- **Stufe A -- Clip-Index** (`cutter/reel_source.py`): scannt `source/`, erfasst je Clip Dauer/Audio + eine
  heuristische Energie (0..1), gecacht in `state/clip_index.json`. Ohne Meta baubar. **[gebaut]**
- **Stufe B -- Tages-Selektor + Schnitt** (`cutter/reel_select.py` + `cutter/reel_daily.py`): Tagesthema
  (rotierend), themenbasierte Auswahl ueber Spiele mit Anti-Doppel, Schnitt via bestehender Pipeline, Ablage
  in `outbox/<datum>/` + `metadata.json`, Protokoll in `used.jsonl`. Ohne Meta baubar. **[gebaut]**
- **Stufe C -- 1-Tap-Freigabe-Bridge**: LUNA-OS erkennt neues Reel -> Antrag mit Video-Vorschau -> Telegram-
  Freigabe. Nutzt den vorhandenen Freigabe-Workflow. **[offen]**
- **Stufe D -- Facebook-Upload**: Token-Scopes pruefen/erweitern (`pages_manage_posts` + `pages_read_engagement`;
  Seed-Token einmalig neu holen -- fuer die EIGENE Seite i. d. R. ohne grosses App-Review). Upload via FB-Reels-
  API (`POST /{page-id}/video_reels`, 3-Phasen: start -> upload -> finish `video_state=PUBLISHED`). **[offen]**
- **Stufe E -- Betrieb**: CFO-Kostenueberwachung, Themen-Rotation ausbauen, Retries, spaeter Performance-Report
  (Insights). **[offen]**

## Governance / Risiken
- **Auto-Posten = CEO-Tor** -> geloest ueber 1-Tap-Freigabe pro Reel (Stufe C).
- **Musik/Rechte** -> Originalton (kein Fremdmusik-Risiko fuer Monetarisierung).
- **Content endlich** -> Themen-Mix + Anti-Doppel strecken das Spielarchiv; Wiederholung nach laengerer Zeit ok.
- **Token-Scope** -> Posting braucht Page-Publish-Rechte, die der DM-Token noch nicht hat (Stufe D klaert das).
