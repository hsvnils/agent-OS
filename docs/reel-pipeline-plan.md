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
- **Stufe C -- 1-Tap-Freigabe-Bridge**: **[gebaut]** Mac reicht das Reel per `reel_daily --einreichen` ->
  `LunaBridge.reel_einreichen` (base64/JSON, keine multipart-Dependency) bei LUNA-OS ein
  (`POST /api/reel/einreichen`); `ReelStore` (`core/reel_store.py`) haelt es als 'wartet'; LUNA-OS-App **Reels**
  (`app-v2.js`, Video-Vorschau + Freigeben/Ablehnen) + Telegram-Hinweis (Notifier). Freigabe -> Status
  'freigegeben' (Stufe D liest es). Endpunkte `/api/reel`(+`/einreichen`,`/{id}/video`,`/{id}/freigeben`,
  `/{id}/ablehnen`). Cache app-v2.js v14. Live-Daten `reel_freigabe/` (gitignored + sync-exkludiert).
- **Stufe D -- Facebook-Upload**: **[Code gebaut, Token-Scope offen]** `governance/facebook_reels.poste_reel`
  (3-Phasen `POST /{page-id}/video_reels`: start -> Binaer-Upload -> finish `video_state=PUBLISHED`, nur urllib);
  `instagram_token.page_info` liefert (page_id, Seiten-Token). Freigabe in der Reels-App startet den Upload im
  Hintergrund (`_reel_posten`, BackgroundTasks) -> Status gepostet(fb_video_id)|fehler; „🔁 Erneut posten" als
  Retry. **Aktivierung ganz am Ende:** Seed-Token einmalig mit **`pages_manage_posts`** (+ pages_read_engagement)
  neu holen (eigene Seite, du bist Admin -> i. d. R. ohne grosses App-Review). Bis dahin -> Status 'fehler' mit
  klarer Meldung.
- **Reels-App:** editierbarer, kurzer Caption-Text (wird 1:1 gepostet), Video-Vorschau, Freigeben&posten /
  Ablehnen / Erneut posten. Cache app-v2.js v15.
- **Stufe E -- Betrieb**: CFO-Kostenueberwachung, Themen-Rotation ausbauen, Retries, spaeter Performance-Report
  (Insights). **[offen]**

## Qualitaet & Inhaltserkennung
- **Qualitaetsfilter (lokal, gratis):** Der Index speichert die Aufloesung (breite/hoehe);
  `reel_select.filter_qualitaet` sortiert Clips aus, deren kurze Bildseite deutlich unter dem Median liegt
  (< max(480, 0.5*Median)) -> kein 360p zwischen HD, 720p bleibt neben 1080p.
- **Inhaltserkennung -- Stufen:** (a) Audio-Energie + Szenendichte = lokaler Gratis-Proxy fuer „lauter Moment"
  (Jubel/Tor), aber keine echte Erkennung. (b) **Gemini-Video-Tagging (opt-in, CEO-Tor)**:
  `gemini_video.tags_via_video` + Runner `cutter/reel_tag.py` lassen die Clips ANSEHEN und vergeben Inhalts-
  Tags (tor/jubel/choreo/fans/interview/stadion/spielszene) ins Index-Feld `themen`; `reel_select` bevorzugt
  dann zum Tagesthema passende Clips (`THEMA_TAGS`). Nur mit `CUTTER_VIDEO_KI=1` + `GEMINI_API_KEY`
  (`gemini-2.5-flash-lite`, 360p-Proxys, ~0,1-0,3 Cent/Clip einmalig). (c) Spaeter: lokales Vision-Modell
  (neuer Mac) = echte Erkennung ohne Cloud/Kosten.

## Governance / Risiken
- **Auto-Posten = CEO-Tor** -> geloest ueber 1-Tap-Freigabe pro Reel (Stufe C).
- **Musik/Rechte** -> Originalton (kein Fremdmusik-Risiko fuer Monetarisierung).
- **Content endlich** -> Themen-Mix + Anti-Doppel strecken das Spielarchiv; Wiederholung nach laengerer Zeit ok.
- **Token-Scope** -> Posting braucht Page-Publish-Rechte, die der DM-Token noch nicht hat (Stufe D klaert das).
