# Social-Media-Analyzer -- Setup (CEO)

> Der Analyzer holt die Insights **deines eigenen** Instagram-Business-/Creator-Kontos ueber die Meta Graph
> API, verdichtet sie zu Kennzahlen mit **Monats-Historie** und liefert einen **Media-Kit-Entwurf**.
> **Wichtig:** Das ist NICHT die abgebrochene Advanced-Access-Review (GATE B, fuer fremde DMs). Fuers eigene
> Konto reicht ein Token, das du als App-Admin selbst erzeugst. Posten/Canva bleibt CEO-Tor.

## Was der CEO einmalig einrichtet

1. **Instagram-Konto** ist ein **Business- oder Creator-Konto** und mit einer **Facebook-Seite** verknuepft
   (Instagram-App -> Einstellungen -> Konto -> Verknuepfte Konten).
2. In der App **AGENT-OS** (developers.facebook.com) die Instagram-Produkte aktiv; du bist Admin.
3. **IG-User-ID** und ein **Access-Token mit Insights-Scope** besorgen (Graph API Explorer oder
   Seiten-Token). Benoetigte Scopes fuers eigene Konto: `instagram_basic`, `instagram_manage_insights`,
   `pages_read_engagement` (Seite). Token als **langlebiges** Token erzeugen (60 Tage / Seiten-Token).
4. Beides in `orchestrator/.env` eintragen (Mac + NAS):
   ```
   INSTAGRAM_IG_USER_ID=17841400000000000
   INSTAGRAM_INSIGHTS_TOKEN=EAAG...        # ODER vorhandenes INSTAGRAM_PAGE_TOKEN wird genutzt
   ```
5. `luna-telegram` neu starten (Sync + Neustart), damit die .env geladen wird.

## Nutzung (in LUNA/Telegram)

- **Monatlich abrufen + speichern + Media-Kit:** „Erstelle den Social-Media-Report / das Media-Kit fuer
  diesen Monat." -> Tool `social_media_analyzer` holt die Zahlen, legt den Monats-Snapshot ab und gibt den
  Media-Kit-Entwurf mit Trend ggue. Vormonat aus.
- **Nur Historie zeigen (kein Abruf):** „Zeig mir die Social-Media-Historie."

## Was drin ist (v1)

Follower, Reichweite (28 Tage), Profilaufrufe, Engagement-Rate (aus den letzten Posts), Beitragszahl,
Durchschnitt Likes/Kommentare, Top-3-Posts -- je Monat, mit **Monatstrend**. Metriken sind konfigurierbar
(`core/social_kit.py`, `_KONTO_METRIKEN`), falls Meta welche deprecatet.

## Spaeter (optional, eigener Antrag)

**Canva-Autofill:** Media-Kit automatisch in ein Canva-Brand-Template befuellen (Canva Connect API). Braucht
Canva-API-Zugang (Kosten/CEO-Tor) -> separat entscheiden. Bis dahin liefert der Analyzer die aufbereiteten
Zahlen als Entwurf, den du in Canva einsetzt.
