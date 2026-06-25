# Google Workspace fuer LUNA -- OAuth-Setup (Phase 11)

Damit LUNA auf Gmail, Kalender, Drive und Sheets zugreifen kann, braucht es einmalig OAuth-Zugangsdaten eines
**separaten Google-Kontos** (nur fuer LUNA -- saubere Trennung von privaten Daten). Alle Schritte 1–5 machst
**du** (CEO); danach laeuft alles ueber `orchestrator/.env`. Sicherheitsmodell: **Lesen frei, Senden/Aendern
nur nach Bestaetigung** (siehe `governance/zugriffs-policy.md`).

## Schritt 1 -- Separates Google-Konto
Lege ein neues Google-Konto an (z. B. `luna.hanserautisch@gmail.com`). **Dieses** Konto verbindet LUNA.

## Schritt 2 -- Google-Cloud-Projekt + APIs aktivieren
1. https://console.cloud.google.com -> mit dem neuen Konto anmelden -> **Neues Projekt** (z. B. „LUNA").
2. Unter **APIs & Dienste -> Bibliothek** diese vier APIs aktivieren:
   - **Gmail API**, **Google Calendar API**, **Google Drive API**, **Google Sheets API**.

## Schritt 3 -- OAuth-Consent-Screen
1. **APIs & Dienste -> OAuth-Zustimmungsbildschirm** -> Nutzertyp **Extern** -> erstellen.
2. App-Name „LUNA", Support-Mail = das neue Konto.
3. **Scopes**: hinzufuegen (Least-Privilege; muss zu `SCOPES` in `orchestrator/governance/google_workspace.py`
   passen):
   - `.../auth/gmail.readonly`, `.../auth/gmail.compose`
   - `.../auth/calendar.readonly`, `.../auth/calendar.events`
   - `.../auth/drive.readonly`, `.../auth/drive.file`
   - `.../auth/spreadsheets`
4. **Testnutzer**: das neue Konto als Testnutzer hinzufuegen (im „Testing"-Modus reicht das -- keine
   Google-Verifizierung noetig).

## Schritt 4 -- OAuth-Client (Desktop)
**APIs & Dienste -> Anmeldedaten -> Anmeldedaten erstellen -> OAuth-Client-ID -> Anwendungstyp „Desktop".**
JSON herunterladen (`client_secret.json`).

## Schritt 5 -- Einmalige Autorisierung -> Refresh-Token
Auf dem Mac (oeffnet den Browser zur Zustimmung mit dem neuen Konto):
```sh
pip install google-auth-oauthlib google-api-python-client   # einmalig, falls noch nicht da
python deploy/google_oauth_authorize.py /pfad/zu/client_secret.json
```
Das Skript druckt drei Zeilen. Diese in **`orchestrator/.env`** eintragen (Mac UND NAS):
```
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...
```
> `client_secret.json` und der Refresh-Token sind Secrets -- **niemals ins Repo** (nur `.env`, gitignored).

## Schritt 6 -- Go-Live
- Google-Libs ins NAS-Image: `deploy/sync-to-nas.sh --build` (Dockerfile installiert sie bereits).
- Danach Live-Test: LUNA auf Telegram „zeig meine naechsten Termine" / „such Mails von X".
- Ohne Credentials liefert jedes Google-Tool einen Fall-B-Hinweis (kein Absturz).

## Scopes spaeter erweitern
Mehr Rechte (z. B. Mails loeschen) = neue Scopes im Consent-Screen + erneute Autorisierung (Schritt 5) +
Anpassung von `SCOPES`. Neue Scopes sind ein CEO-Tor (CISO autorisiert).
