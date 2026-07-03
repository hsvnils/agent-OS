# Secrets-Rotation — Checkliste (operativ, CEO)

> **Zweck:** Alle Zugangs-Secrets des Systems geordnet neu erzeugen — vorrangig die, die irgendwann **im Chat
> geteilt** wurden. Dieses Dokument enthaelt **keine** Secret-Werte, nur Namen, Ablageorte und Schritte.
> Erstellt 2026-07-03 (Claude Code) als Vorbereitung; die Durchfuehrung macht der CEO.

---

## 0 So laeuft eine Rotation (immer gleich)

1. Im jeweiligen Anbieter-Portal den **neuen** Key/Token erzeugen (alten noch nicht loeschen).
2. Neuen Wert an **beiden** Stellen eintragen: `orchestrator/.env` **auf dem Mac** UND **auf der NAS**
   (`/volume1/docker/ki-unternehmen/orchestrator/.env`).
3. Container neu starten (DSM-Neustart **oder** `sudo /usr/local/bin/docker restart luna-telegram luna-os`).
4. Kurz verifizieren, dass die Funktion noch geht (siehe „Test" je Zeile).
5. Erst **danach** den alten Key im Portal **widerrufen/loeschen**.

**Wichtig:**
- `orchestrator/.env` ist gitignored und vom NAS-Sync ausgeschlossen — Werte landen **nie** im Repo.
- System-/Passwort-Einstellungen (LUNA-OS-Login, NAS-Passwort) macht der CEO selbst.
- Nach dem Eintragen keine Keys in Chats/Screenshots posten.

---

## 1 HOECHSTE PRIORITAET — im Chat geteilt (zuerst rotieren)

| Secret (`.env`-Key) | Wofuer | Neu erzeugen bei | Test nach Rotation |
|---|---|---|---|
| `GITHUB_TOKEN` (PAT) | Watcher (GitHub-API) + Branch-Push der Execution | github.com/settings/tokens (Fine-grained; nur noetige Repos/Scopes) | LUNA: „systemcheck" / Watcher-Tick ohne 401 |
| `OPENAI_API_KEY` | Fallback-Provider (Multi-Provider) | platform.openai.com/api-keys | Provider-Fallback greift; keine Auth-Fehler im Log |
| `GEMINI_API_KEY` | Cutter-Reihenfolge + Fallback | aistudio.google.com/app/apikey | Cutter-Lauf ordnet Clips; kein Auth-Fehler |

---

## 2 Kern-Betrieb (aktiv genutzt)

| Secret | Wofuer | Neu erzeugen bei | Test |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | LUNA-Chat/Fachagenten/Execution/Web-Eskalation | console.anthropic.com/settings/keys | LUNA antwortet im Chat |
| `TELEGRAM_BOT_TOKEN` | Telegram-Bot @luna_headofagents_bot | @BotFather -> /revoke bzw. /token | Bot antwortet dem CEO |
| `BRAVE_API_KEY` | Web-Recherche (Default-Suche) | api.search.brave.com/app/keys | LUNA: eine Recherche liefert Treffer |
| `SUPABASE_SERVICE_ROLE_KEY` | DB-Zugriff (CRM/Projektionen); `SUPABASE_URL` bleibt | supabase.com -> Project Settings -> API (Service Role neu rollen) | CRM-Timeline laedt; keine DB-Fehler |

## 3 Google Workspace (OAuth — zweistufig)

| Secret | Wofuer | Rotation |
|---|---|---|
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth-Client (Gmail/Kalender/Drive) | console.cloud.google.com -> APIs & Dienste -> Anmeldedaten -> Client -> **Secret zuruecksetzen** |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Dauerhafter Zugriff ohne erneutes Login | Nach Client-Secret-Wechsel **neu einwilligen** (OAuth-Consent-Flow erneut durchlaufen), neuen Refresh-Token uebernehmen |

- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_ACCOUNT_EMAIL` sind keine Geheimnisse (koennen bleiben).
- **Test:** LUNA liest eine ungelesene Mail / zeigt den heutigen Kalender.

## 4 Voice (nur falls Voice-Kanal genutzt wird)

| Secret | Wofuer | Neu erzeugen bei |
|---|---|---|
| `DEEPGRAM_API_KEY` | Spracherkennung (STT) | console.deepgram.com |
| `ELEVENLABS_API_KEY` | Sprachausgabe (TTS) | elevenlabs.io -> Profile -> API Keys |
| `CARTESIA_API_KEY` | alternative TTS (falls konfiguriert) | play.cartesia.ai |

## 5 Investment-Datenquellen (nur falls konfiguriert/genutzt)

| Secret | Anbieter |
|---|---|
| `ALPHAVANTAGE_API_KEY` | alphavantage.co/support/#api-key |
| `FINNHUB_API_KEY` | finnhub.io/dashboard |
| `FMP_API_KEY` | site.financialmodelingprep.com |
| `COINGECKO_API_KEY` | coingecko.com (nur falls Pro-Key gesetzt) |
| `AGENTOPS_API_KEY` | app.agentops.ai (Observability, optional) |

## 6 Instagram / Meta (erst mit GATE B relevant)

| Secret | Wofuer | Hinweis |
|---|---|---|
| `INSTAGRAM_APP_SECRET` | Meta-App-Secret | developers.facebook.com -> App -> Einstellungen |
| `INSTAGRAM_PAGE_TOKEN` | Page-/IG-Zugriffstoken | Graph API Explorer / App-Token neu erzeugen |
| `INSTAGRAM_VERIFY_TOKEN` | Webhook-Verify (selbst gewaehlt) | frei waehlbar; im Webhook + `.env` gleich setzen |

## 7 Passwoerter — macht der CEO in der jeweiligen Oberflaeche

| Secret | Wo aendern |
|---|---|
| `LUNA_OS_PASSWORD` (+ `LUNA_OS_USER`) | NAS-`.env`; Web-Login der LUNA-OS |
| NAS-/DSM-Passwort (sudo) | Synology DSM -> Benutzer |

---

## 8 KEINE Secrets (nicht rotieren — nur Konfiguration)

`SUPABASE_URL`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_ACCOUNT_EMAIL`, `GOOGLE_CALENDAR_DEFAULT_ATTENDEE`,
`GOOGLE_CALENDAR_TIMEZONE`, `LUNA_OS_HOST`, `LUNA_OS_PORT`, `PORT`, `TELEGRAM_ALLOWED_CHAT_ID`,
`WATCH_INTERVAL_HOURS`, `WEB_RESEARCH_ANTHROPIC`, `CONTENT_FEED_ENABLED`, `SELF_DEV_ENABLED`,
`SECURITY_AUDIT_ENABLED`, `INVESTMENT_AUTO_SCREEN`, `EXECUTION_AUTO_SNAPSHOT` — Adressen/Schalter, keine
Geheimnisse.

## 9 Nach Abschluss

- Alte Keys ueberall widerrufen (Portale).
- Kurz `sicherheits_audit` laufen lassen (Secret-Hygiene bleibt gruen).
- Diese Rotation im `projekt_changelog.md` vermerken (ohne Werte).
