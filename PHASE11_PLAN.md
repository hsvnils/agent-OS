# PHASE11_PLAN.md — Google Workspace (Gmail, Kalender, Drive, Sheets)

> **Status: OFFLINE GEBAUT — Go-Live wartet auf GATE (CEO-Tor + CISO, OAuth-Credentials).** Detailplan zu
> Phase 11 der `ROADMAP.md`, erweitert um Drive + Sheets. LUNA (HoA) erhaelt Zugriff auf ein **separates
> Google-Konto**. `AGENTS.md` bleibt kanonisch und uebergeordnet.

---

## 1. Zweck & Entscheidungen (CEO, 2026-06-25)

- **Konto:** ein **separates Google-Konto** nur fuer LUNA (saubere Trennung von privaten Daten).
- **Rechte-Modell:** **Lesen frei, Schreiben/Senden/Aendern nur nach Bestaetigung** (bzw. als Entwurf).
- **Umfang:** alle vier Dienste — Gmail, Kalender, Drive, Sheets — zusammen.

## 2. Sicherheits-Invarianten (nicht verhandelbar)

1. **Mensch-Tor fuer externe Aktionen (AGENTS.md 4):** `mail_senden`, `termin_anlegen`, `tabelle_schreiben`
   liefern ohne `bestaetigt=true` nur eine **Vorschau**; Ausfuehrung erst nach ausdruecklicher CEO-Bestaetigung.
   `mail_entwurf` ist sicher (legt nur einen Entwurf an, sendet nicht).
2. **Least-Privilege:** nur die noetigen OAuth-Scopes (readonly + compose/events/file/spreadsheets); CISO
   autorisiert. Erweiterung = neuer CEO-Tor.
3. **Secrets:** OAuth-Client-Secret + Refresh-Token NUR in `orchestrator/.env` (separates Konto), nie ins Repo
   (`.gitignore`). Leck-Schutz redigiert jedes Tool-Ergebnis.
4. **Capability-Muster:** LUNA erhaelt **Tools**, nie den Key-Text. Ohne Credentials -> Fall-B-Hinweis (CEO-Tor),
   kein Absturz, kein Netz.

## 3. Bausteine (gebaut)

- `orchestrator/governance/google_workspace.py` — `GoogleAuth` (OAuth aus .env, lazy Client-Bau),
  `GoogleWorkspace` (Gmail/Kalender/Drive/Sheets, Lesen direkt + Schreiben gated), `MockGoogleWorkspace`
  (Offline-Self-Checks). Lazy import der google-Libs.
- HoA-Tools in `orchestrator/core/hoa_tools.py`: `mail_suchen/lesen/entwurf/senden`, `kalender_agenda`,
  `termin_anlegen`, `drive_suchen/lesen`, `tabelle_lesen/schreiben` (Schreib-Tools gated). `ToolContext.google`.
- Bot-Verdrahtung (`telegram/bot.py`): Google aus den .env-Secrets.
- `orchestrator/tests/test_google_workspace.py` — 8 Offline-Self-Checks (Fall-B ohne Credentials, Lesen,
  Gating von Senden/Termin/Tabelle, Entwurf sicher, Tool-Specs, Leck-Schutz). Gesamtsuite 66/66 OK.
- `deploy/google-oauth-setup.md` (CEO-Anleitung) + `deploy/google_oauth_authorize.py` (einmaliger
  Refresh-Token). Dockerfile: google-api-python-client + google-auth (Runtime).

## 4. GATE — Go-Live-Checkliste (CEO + CISO)

1. Separates Google-Konto anlegen.
2. Google-Cloud-Projekt + 4 APIs aktivieren; OAuth-Consent (Scopes wie in `SCOPES`); OAuth-Desktop-Client.
3. `python deploy/google_oauth_authorize.py client_secret.json` -> 3 Werte in `orchestrator/.env` (Mac + NAS).
4. NAS: `deploy/sync-to-nas.sh --build` (zieht google-Libs); Live-Test ueber Telegram.
5. Zugriffs-Policy-Status auf „live" fortschreiben.

> Erst nach 1–4 liefern die Google-Tools echte Daten. Bis dahin alles gebaut, getestet, sicher inaktiv
> (Fall-B-Hinweis). Detailschritte: `deploy/google-oauth-setup.md`.

## 5. Spaeter / Erweiterung (Phase 11b-Ideen)

- Proaktiver Watcher/Notifier (neue Mail / Termin-Kollision -> Push ueber Telegram).
- Mehr Operationen je Dienst (Label/Verschieben, Termin aendern/loeschen, Datei anlegen/teilen) — je als
  gated Write, neue Scopes = CEO-Tor.
