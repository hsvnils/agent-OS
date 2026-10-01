# Roadmap: Reels aufraeumen (Verfall, Videos loeschen, Nachschub-Bremse)
- Status: geplant
- Stand: 2026-10-01
- Arbeitsbranch: `ai/plan-reels` (Plan); Umsetzung auf `ai/reels-aufraeumen`
- Basiscommit: `fbfa09c`
- Naechster Schritt: CEO-Go fuer Etappe 1 abwarten; bis dahin keine Umsetzung.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-01)

„Was machen wir mit Reels, die mehr als 30 Tage nicht bestaetigt wurden? Die Liste wird sonst sehr lang.“
CEO-Entscheidungen 2026-10-01: Verfall nach **30 Tagen**; Videos abgelehnter und verfallener Reels **loeschen**
(nach 14 Tagen); **gepostete behalten**; **Nachschub-Bremse bei 10** wartenden Reels.

## Analyse (read-only, 2026-10-01)

- NAS `reel_freigabe/log.jsonl`: 40 Reels -- 10 gepostet, 5 abgelehnt, **25 warten, davon 18 aelter als 30 Tage**.
- Speicher: `reel_freigabe/` = 1,5 GB (40 MP4 je ~37 MB); NAS 9,9 TB frei -> kein Platzproblem, aber unbegrenztes
  Wachstum (~1 GB/Monat). Die MP4 sind nicht im Backup (nur das Log).
- `core/reel_store.py`: Status `wartet/freigegeben/abgelehnt/gepostet/fehler`, kein Verfall.
- Nachtlauf `cutter/reel_daily.py --einreichen` schneidet jede Nacht ein Reel und reicht es ueber
  `cutter/luna_bridge.py` (`POST /api/reel/einreichen`) ein -- auch wenn niemand die vorigen ansieht.
- **Stolperfalle:** `core/betriebswacht.py` meldet „Kein Reel“, wenn `reel_stunden` (30 h) lang keines eingereicht
  wurde (`ReelStore.zuletzt_eingereicht`, Bot-Loop `bot.py`). Eine Bremse ohne Gegenmassnahme erzeugt Fehlalarme.

## Scope / Nicht-Scope

- Scope: `core/reel_store.py`, `cutter/reel_daily.py`, `cutter/luna_bridge.py`, Endpunkte in `app.py`, Bot-Tagesjob,
  `core/betriebswacht.py`, Reels-Ansicht in LUNA-OS, Tests.
- Nicht-Scope: Original-Clips im NAS-Archiv (`/mnt/nas-clips`, bleiben unberuehrt), gepostete Reels, Facebook,
  DSM-Aufgabe/Zeitplan des Nachtlaufs (bleibt 03:30).

## Etappe 1: Verfall, Aufraeumen, Bremse

- Status: geplant
- Ziel / Scope:
  - **Verfall:** Neuer Status `verfallen`. Ein Reel, das 30 Tage nach dem Einreichen noch `wartet`, verfaellt -- es
    wird nie gepostet, faellt aus Freigabe-Liste und Handlungsbedarf. Taeglicher Lauf im Bot (mit den anderen
    Tagesjobs); eine Telegram-Meldung je Lauf nur, wenn etwas verfallen ist („3 Reels verfallen“). Die 18 alten
    verfallen beim ersten Lauf (eine Sammelmeldung).
  - **Videos loeschen (CEO-Freigabe 2026-10-01):** Bei `abgelehnt` und `verfallen` loescht LUNA die MP4 14 Tage nach
    der Entscheidung (Ereignis `video_geloescht` im Log). Daten (Datum, Thema, Caption, Status) bleiben fuer Statistik
    und Leistungsbericht. `gepostet` behaelt das Video. Die Reels-Ansicht zeigt „Video geloescht“ statt eines
    Players.
  - **Bremse:** Neuer Endpunkt `GET /api/reel/bremse` -> `{wartet, bremse}` (bremse ab 10 wartenden). Der Nachtlauf
    fragt das **vor** dem Schnitt ab; bei Bremse schneidet er nicht und meldet `POST /api/reel/uebersprungen`
    (Ereignis im Reel-Log, Grund + Anzahl). Ist LUNA-OS nicht erreichbar, laeuft der Nachtlauf wie bisher.
  - **Wacht ohne Fehlalarm:** Die Betriebs-Wacht wertet „zuletzt aktiv“ = juengstes Einreichen **oder** Uebersprungen;
    eine gebremste Nacht ist kein Ausfall.
- Gate: Tests -- Verfall genau ab Tag 31 (Tag 30 noch wartend), kein Verfall fuer freigegeben/abgelehnt/gepostet;
  Loeschen nur abgelehnt/verfallen und erst ab Tag 14, gepostet nie, fehlende Datei kein Fehler, idempotent;
  Bremse bei 9 aus, bei 10 an; Nachtlauf schneidet bei Bremse nicht (Mock-Bruecke); Wacht ohne Alarm nach
  „uebersprungen“, mit Alarm wenn beides fehlt. Gegenprobe je Pruefung. Suite + Doku-Check gruen.
- Verifikation (nach Deploy): `GET /api/reel/bremse` -> erwartet `wartet = 7, bremse = false` nach dem ersten
  Verfall-Lauf (18 der 25 verfallen); 14 Tage spaeter: MP4 der 5 abgelehnten + 18 verfallenen fehlen,
  `du -sh reel_freigabe` deutlich kleiner, gepostete 10 MP4 vorhanden.
- Risiko / Rueckweg: Loeschen ist endgueltig (CEO-Freigabe liegt vor); Original-Clips bleiben, ein Reel ist neu
  schneidbar. Verfall selbst ist nur ein Status.
- Aufwand: klein bis mittel.

## Doku

`projekt_changelog.md`, `docs/datenfluesse.md` (neue Endpunkte, Ereignisse, Loeschregel), `docs/entscheidungs-register.md`
(Verfall/Loeschen/Bremse), Memory-Notiz zur Reel-Pipeline.

## Definition of Done

Etappe 1 verifiziert (Verfall-Lauf, Bremse, nach 14 Tagen Loeschung) und vom CEO abgenommen.
