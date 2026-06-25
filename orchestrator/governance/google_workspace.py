"""Phase 11 -- Google Workspace Integration (Capability-Muster) fuer LUNA (HoA).

Bindet ein **separates Google-Konto** (nur fuer LUNA) an: Gmail, Kalender, Drive, Sheets.

Sicherheitsmodell (CEO 2026-06-25): **Lesen frei, Schreiben/Senden/Aendern nur nach Bestaetigung**
(`bestaetigt=True`) bzw. als Entwurf. Externe Aktionen = Mensch-Tor (AGENTS.md 4). Least-Privilege ueber
OAuth-Scopes (CISO autorisiert).

Auth: OAuth2-Refresh-Token aus `orchestrator/.env`
(`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` / `GOOGLE_OAUTH_REFRESH_TOKEN`). Lazy import der
google-Libs -> Offline-Self-Checks brauchen weder Libs noch Netz. Fehlen Credentials -> sauberer
**Fall-B-Hinweis** (CEO-Tor), kein Absturz. Secrets nie im Klartext (Leck-Schutz greift im Tool-Layer).

Hinweis: Die echten API-Aufrufe werden erst beim Go-Live (Credentials vorhanden) real ausgefuehrt; offline
deckt der `MockGoogleWorkspace` die Tool-/Gating-Logik ab.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# Least-Privilege-Scopes (Lesen + abgesichertes Schreiben). Der OAuth-Consent muss genau diese umfassen.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",     # Mails lesen/suchen
    "https://www.googleapis.com/auth/gmail.compose",      # Entwuerfe anlegen + senden (gated)
    "https://www.googleapis.com/auth/calendar.readonly",  # Termine lesen
    "https://www.googleapis.com/auth/calendar.events",    # Termine anlegen/aendern (gated)
    "https://www.googleapis.com/auth/drive.readonly",     # Dateien lesen/suchen
    "https://www.googleapis.com/auth/drive.file",         # vom Bot erstellte Dateien (gated)
    "https://www.googleapis.com/auth/spreadsheets",       # Sheets lesen + schreiben (gated)
]
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _fall_b(capability: str = "google_workspace") -> str:
    return (
        "ANFRAGE an CEO (Freigabe noetig)\n"
        f"- Capability: {capability}\n"
        "- Fuer: LUNA (HoA)\n"
        "- Grund: neuer externer Zugang (Google OAuth) -> CEO-Tor + CISO\n"
        "- Status: nicht aktiv bis OAuth-Credentials in orchestrator/.env "
        "(GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN)"
    )


@dataclass
class GoogleAuth:
    """Haelt die OAuth-Credentials und baut bei Bedarf authentifizierte API-Clients (lazy)."""

    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    _services: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "GoogleAuth":
        import os
        e = env if env is not None else os.environ
        return cls(
            client_id=e.get("GOOGLE_OAUTH_CLIENT_ID", "").strip(),
            client_secret=e.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip(),
            refresh_token=e.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip(),
        )

    def verfuegbar(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def service(self, api: str, version: str):
        """Authentifizierter google-api-python-client (gecacht). Lazy import."""
        key = f"{api}:{version}"
        if key in self._services:
            return self._services[key]
        from google.oauth2.credentials import Credentials  # lazy
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None, refresh_token=self.refresh_token, token_uri=_TOKEN_URI,
            client_id=self.client_id, client_secret=self.client_secret, scopes=SCOPES,
        )
        creds.refresh(Request())
        svc = build(api, version, credentials=creds, cache_discovery=False)
        self._services[key] = svc
        return svc


def _ok(**kw) -> dict:
    return {"ok": True, **kw}


def _fehler(hinweis: str) -> dict:
    return {"ok": False, "hinweis": hinweis}


class GoogleWorkspace:
    """Gmail/Kalender/Drive/Sheets -- Lesen frei, Schreiben gated. Echte API (lazy)."""

    def __init__(self, auth: GoogleAuth, *, standard_einladung: str = "",
                 zeitzone: str = "Europe/Berlin"):
        self.auth = auth
        # Wird bei JEDEM Termin automatisch als Teilnehmer eingeladen (z. B. private iCloud-Adresse).
        self.standard_einladung = (standard_einladung or "").strip()
        # Pflicht fuer die Google Calendar API, wenn die ISO-Zeit keinen Offset traegt
        # (sonst Fehler „Missing time zone definition").
        self.zeitzone = (zeitzone or "Europe/Berlin").strip()

    def _event_body(self, titel: str, start: str, ende: str, ort: str, beschreibung: str,
                    einladungen: list[str]) -> dict:
        body = {"summary": titel, "location": ort, "description": beschreibung,
                "start": {"dateTime": start, "timeZone": self.zeitzone},
                "end": {"dateTime": ende, "timeZone": self.zeitzone}}
        if einladungen:
            body["attendees"] = [{"email": e} for e in einladungen]
        return body

    def verfuegbar(self) -> bool:
        return self.auth.verfuegbar()

    def _guard(self) -> dict | None:
        if not self.auth.verfuegbar():
            return {"ok": False, "fall_b": True,
                    "hinweis": "Google-Zugriff nicht aktiv -- OAuth-Credentials fehlen (CEO-Tor + CISO).",
                    "freigabe_anfrage": _fall_b()}
        return None

    # ---------------- Gmail ----------------

    def mail_suchen(self, query: str, max_results: int = 10) -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("gmail", "v1")
            resp = svc.users().messages().list(userId="me", q=query,
                                               maxResults=max(1, min(max_results, 25))).execute()
            mails = []
            for m in resp.get("messages", []):
                full = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
                h = {x["name"]: x["value"] for x in full.get("payload", {}).get("headers", [])}
                mails.append({"id": m["id"], "von": h.get("From", ""), "betreff": h.get("Subject", ""),
                              "datum": h.get("Date", ""), "snippet": full.get("snippet", "")})
            return _ok(mails=mails)
        except Exception as exc:
            return _fehler(f"Gmail-Suche fehlgeschlagen: {str(exc)[:160]}")

    def mail_lesen(self, message_id: str) -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("gmail", "v1")
            full = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
            payload = full.get("payload", {})
            h = {x["name"]: x["value"] for x in payload.get("headers", [])}
            return _ok(mail={"von": h.get("From", ""), "an": h.get("To", ""),
                             "betreff": h.get("Subject", ""), "datum": h.get("Date", ""),
                             "text": _extract_text(payload)})
        except Exception as exc:
            return _fehler(f"Gmail-Lesen fehlgeschlagen: {str(exc)[:160]}")

    def mail_entwurf(self, an: str, betreff: str, text: str) -> dict:
        """Sicher: legt einen Gmail-Entwurf an (sendet NICHT)."""
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("gmail", "v1")
            draft = svc.users().drafts().create(
                userId="me", body={"message": {"raw": _mime(an, betreff, text)}}).execute()
            return _ok(entwurf_id=draft.get("id"), hinweis="Entwurf angelegt (nicht gesendet).")
        except Exception as exc:
            return _fehler(f"Entwurf fehlgeschlagen: {str(exc)[:160]}")

    def mail_senden(self, an: str, betreff: str, text: str, *, bestaetigt: bool = False) -> dict:
        """Gated: ohne bestaetigt=True nur Vorschau (Mensch-Tor)."""
        if (g := self._guard()):
            return g
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"an": an, "betreff": betreff, "text": text},
                    "hinweis": "Senden braucht CEO-Bestaetigung -- erneut mit bestaetigt=true aufrufen."}
        try:
            svc = self.auth.service("gmail", "v1")
            sent = svc.users().messages().send(
                userId="me", body={"raw": _mime(an, betreff, text)}).execute()
            return _ok(gesendet=True, id=sent.get("id"))
        except Exception as exc:
            return _fehler(f"Senden fehlgeschlagen: {str(exc)[:160]}")

    # ---------------- Kalender ----------------

    def kalender_agenda(self, tage: int = 7, max_results: int = 20) -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("calendar", "v3")
            now = datetime.now(timezone.utc)
            resp = svc.events().list(
                calendarId="primary", timeMin=now.isoformat(),
                timeMax=(now + timedelta(days=tage)).isoformat(),
                singleEvents=True, orderBy="startTime", maxResults=max_results).execute()
            termine = [{"id": e.get("id"), "titel": e.get("summary", ""),
                        "start": (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date"),
                        "ende": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date"),
                        "ort": e.get("location", "")} for e in resp.get("items", [])]
            return _ok(termine=termine)
        except Exception as exc:
            return _fehler(f"Kalender-Abruf fehlgeschlagen: {str(exc)[:160]}")

    def termin_anlegen(self, titel: str, start: str, ende: str, *, ort: str = "",
                       beschreibung: str = "", bestaetigt: bool = False) -> dict:
        if (g := self._guard()):
            return g
        einladungen = [self.standard_einladung] if self.standard_einladung else []
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"titel": titel, "start": start, "ende": ende, "ort": ort,
                                 "einladung": einladungen},
                    "hinweis": "Termin anlegen braucht CEO-Bestaetigung -- erneut mit bestaetigt=true."}
        try:
            svc = self.auth.service("calendar", "v3")
            body = self._event_body(titel, start, ende, ort, beschreibung, einladungen)
            ev = svc.events().insert(calendarId="primary", body=body,
                                     sendUpdates="all").execute()  # Einladungs-Mail rausschicken
            return _ok(termin_id=ev.get("id"), link=ev.get("htmlLink"), eingeladen=einladungen)
        except Exception as exc:
            return _fehler(f"Termin anlegen fehlgeschlagen: {str(exc)[:160]}")

    def neue_mails(self, max_results: int = 10) -> dict:
        """Ungelesene Mails im Posteingang (fuer den proaktiven Mail-Watcher)."""
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("gmail", "v1")
            resp = svc.users().messages().list(userId="me", q="is:unread in:inbox",
                                               maxResults=max(1, min(max_results, 25))).execute()
            mails = []
            for m in resp.get("messages", []):
                full = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
                h = {x["name"]: x["value"] for x in full.get("payload", {}).get("headers", [])}
                mails.append({"id": m["id"], "von": h.get("From", ""), "betreff": h.get("Subject", ""),
                              "datum": h.get("Date", ""), "snippet": full.get("snippet", "")})
            return _ok(mails=mails)
        except Exception as exc:
            return _fehler(f"Posteingang-Abruf fehlgeschlagen: {str(exc)[:160]}")

    def kalender_kollisionen(self, tage: int = 7) -> dict:
        """Findet ueberlappende Termine (Kollisionen) in den naechsten Tagen."""
        if (g := self._guard()):
            return g
        ag = self.kalender_agenda(tage=tage, max_results=50)
        if not ag.get("ok"):
            return ag
        evs = []
        for t in ag["termine"]:
            s, e = _dt(t.get("start")), _dt(t.get("ende"))
            if s and e:
                evs.append((s, e, t.get("titel", "")))
        evs.sort()
        koll = []
        for i in range(len(evs) - 1):
            if evs[i + 1][0] < evs[i][1]:  # naechster Start vor aktuellem Ende
                koll.append({"a": evs[i][2], "b": evs[i + 1][2], "ab": evs[i + 1][0].isoformat()})
        return _ok(kollisionen=koll)

    def termin_aendern(self, event_id: str, *, titel: str = "", start: str = "", ende: str = "",
                       ort: str = "", bestaetigt: bool = False) -> dict:
        if (g := self._guard()):
            return g
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"event_id": event_id, "titel": titel, "start": start, "ende": ende},
                    "hinweis": "Termin aendern braucht CEO-Bestaetigung -- erneut mit bestaetigt=true."}
        try:
            svc = self.auth.service("calendar", "v3")
            patch: dict = {}
            if titel:
                patch["summary"] = titel
            if ort:
                patch["location"] = ort
            if start:
                patch["start"] = {"dateTime": start, "timeZone": self.zeitzone}
            if ende:
                patch["end"] = {"dateTime": ende, "timeZone": self.zeitzone}
            ev = svc.events().patch(calendarId="primary", eventId=event_id, body=patch,
                                    sendUpdates="all").execute()
            return _ok(termin_id=ev.get("id"), link=ev.get("htmlLink"))
        except Exception as exc:
            return _fehler(f"Termin aendern fehlgeschlagen: {str(exc)[:160]}")

    def termin_loeschen(self, event_id: str, *, bestaetigt: bool = False) -> dict:
        if (g := self._guard()):
            return g
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"event_id": event_id},
                    "hinweis": "Termin loeschen braucht CEO-Bestaetigung -- erneut mit bestaetigt=true."}
        try:
            svc = self.auth.service("calendar", "v3")
            svc.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()
            return _ok(geloescht=True)
        except Exception as exc:
            return _fehler(f"Termin loeschen fehlgeschlagen: {str(exc)[:160]}")

    def mail_markieren(self, message_id: str, *, gelesen: bool = True) -> dict:
        """Mail als gelesen/ungelesen markieren (benigne -- nicht gated)."""
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("gmail", "v1")
            body = {"removeLabelIds": ["UNREAD"]} if gelesen else {"addLabelIds": ["UNREAD"]}
            svc.users().messages().modify(userId="me", id=message_id, body=body).execute()
            return _ok(gelesen=gelesen)
        except Exception as exc:
            return _fehler(f"Mail markieren fehlgeschlagen: {str(exc)[:160]}")

    # ---------------- Drive ----------------

    def drive_suchen(self, query: str, max_results: int = 10) -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("drive", "v3")
            resp = svc.files().list(
                q=f"fullText contains '{query}' and trashed=false", pageSize=max(1, min(max_results, 25)),
                fields="files(id,name,mimeType,modifiedTime,webViewLink)").execute()
            dateien = [{"id": f.get("id"), "name": f.get("name"), "typ": f.get("mimeType"),
                        "geaendert": f.get("modifiedTime"), "link": f.get("webViewLink")}
                       for f in resp.get("files", [])]
            return _ok(dateien=dateien)
        except Exception as exc:
            return _fehler(f"Drive-Suche fehlgeschlagen: {str(exc)[:160]}")

    def drive_lesen(self, file_id: str) -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("drive", "v3")
            meta = svc.files().get(fileId=file_id, fields="id,name,mimeType").execute()
            mime = meta.get("mimeType", "")
            if mime.startswith("application/vnd.google-apps"):  # Google-Doc -> als Text exportieren
                data = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
            else:
                data = svc.files().get_media(fileId=file_id).execute()
            text = data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else str(data)
            return _ok(datei={"name": meta.get("name"), "typ": mime, "text": text[:20000]})
        except Exception as exc:
            return _fehler(f"Drive-Lesen fehlgeschlagen: {str(exc)[:160]}")

    def drive_anlegen(self, name: str, inhalt: str, *, bestaetigt: bool = False) -> dict:
        """Legt eine Textdatei in Drive an (gated). Teilen folgt spaeter (eigener Scope)."""
        if (g := self._guard()):
            return g
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"name": name},
                    "hinweis": "Datei anlegen braucht CEO-Bestaetigung -- erneut mit bestaetigt=true."}
        try:
            from googleapiclient.http import MediaInMemoryUpload
            svc = self.auth.service("drive", "v3")
            media = MediaInMemoryUpload(inhalt.encode("utf-8"), mimetype="text/plain")
            f = svc.files().create(body={"name": name}, media_body=media,
                                   fields="id,webViewLink").execute()
            return _ok(datei_id=f.get("id"), link=f.get("webViewLink"))
        except Exception as exc:
            return _fehler(f"Datei anlegen fehlgeschlagen: {str(exc)[:160]}")

    # ---------------- Sheets ----------------

    def tabelle_lesen(self, spreadsheet_id: str, bereich: str = "A1:Z100") -> dict:
        if (g := self._guard()):
            return g
        try:
            svc = self.auth.service("sheets", "v4")
            resp = svc.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=bereich).execute()
            return _ok(werte=resp.get("values", []))
        except Exception as exc:
            return _fehler(f"Tabelle lesen fehlgeschlagen: {str(exc)[:160]}")

    def tabelle_schreiben(self, spreadsheet_id: str, bereich: str, werte: list[list],
                          *, bestaetigt: bool = False) -> dict:
        if (g := self._guard()):
            return g
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"bereich": bereich, "zeilen": len(werte or [])},
                    "hinweis": "Tabelle schreiben braucht CEO-Bestaetigung -- erneut mit bestaetigt=true."}
        try:
            svc = self.auth.service("sheets", "v4")
            resp = svc.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=bereich, valueInputOption="USER_ENTERED",
                body={"values": werte}).execute()
            return _ok(aktualisiert=resp.get("updatedCells", 0))
        except Exception as exc:
            return _fehler(f"Tabelle schreiben fehlgeschlagen: {str(exc)[:160]}")


# ---------------- Helfer ----------------

def _dt(s: str):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _mime(an: str, betreff: str, text: str) -> str:
    msg = EmailMessage()
    msg["To"] = an
    msg["Subject"] = betreff
    msg.set_content(text)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def _extract_text(payload: dict) -> str:
    """Zieht den Klartext aus einer Gmail-Payload (rekursiv ueber parts)."""
    if payload.get("mimeType") == "text/plain":
        data = (payload.get("body") or {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        t = _extract_text(part)
        if t:
            return t
    return ""


class MockGoogleWorkspace:
    """Deterministischer Stub ohne Netz/Libs -- fuer Offline-Self-Checks. Gleiches Gating-Verhalten."""

    def __init__(self, standard_einladung: str = ""):
        self.gesendet: list[dict] = []
        self.termine: list[dict] = []
        self.standard_einladung = (standard_einladung or "").strip()

    def verfuegbar(self) -> bool:
        return True

    def mail_suchen(self, query, max_results=10):
        return _ok(mails=[{"id": "m1", "von": "a@test", "betreff": f"Treffer zu {query}",
                           "datum": "2026-06-25", "snippet": "Beispiel."}])

    def mail_lesen(self, message_id):
        return _ok(mail={"von": "a@test", "an": "luna@test", "betreff": "Betreff",
                         "datum": "2026-06-25", "text": "Mail-Text."})

    def mail_entwurf(self, an, betreff, text):
        return _ok(entwurf_id="d1", hinweis="Entwurf angelegt (nicht gesendet).")

    def mail_senden(self, an, betreff, text, *, bestaetigt=False):
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"an": an, "betreff": betreff, "text": text}}
        self.gesendet.append({"an": an, "betreff": betreff})
        return _ok(gesendet=True, id="s1")

    def kalender_agenda(self, tage=7, max_results=20):
        return _ok(termine=[{"id": "e1", "titel": "Demo", "start": "2026-06-26T10:00:00",
                             "ende": "2026-06-26T11:00:00", "ort": ""}])

    def termin_anlegen(self, titel, start, ende, *, ort="", beschreibung="", bestaetigt=False):
        einladungen = [self.standard_einladung] if self.standard_einladung else []
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"titel": titel, "start": start, "ende": ende, "einladung": einladungen}}
        self.termine.append({"titel": titel, "start": start, "einladung": einladungen})
        return _ok(termin_id="e2", link="https://cal.test/e2", eingeladen=einladungen)

    def neue_mails(self, max_results=10):
        return _ok(mails=[{"id": "m9", "von": "chef@firma.test", "betreff": "Wichtig: Angebot",
                           "datum": "2026-06-25", "snippet": "Bitte heute pruefen."}])

    def kalender_kollisionen(self, tage=7):
        return _ok(kollisionen=[])

    def termin_aendern(self, event_id, *, titel="", start="", ende="", ort="", bestaetigt=False):
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"event_id": event_id}}
        return _ok(termin_id=event_id, link="https://cal.test/e")

    def termin_loeschen(self, event_id, *, bestaetigt=False):
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"event_id": event_id}}
        return _ok(geloescht=True)

    def mail_markieren(self, message_id, *, gelesen=True):
        return _ok(gelesen=gelesen)

    def drive_anlegen(self, name, inhalt, *, bestaetigt=False):
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"name": name}}
        return _ok(datei_id="fneu", link="https://drive.test/fneu")

    def drive_suchen(self, query, max_results=10):
        return _ok(dateien=[{"id": "f1", "name": f"Datei {query}", "typ": "text/plain",
                             "geaendert": "2026-06-25", "link": "https://drive.test/f1"}])

    def drive_lesen(self, file_id):
        return _ok(datei={"name": "Datei", "typ": "text/plain", "text": "Inhalt."})

    def tabelle_lesen(self, spreadsheet_id, bereich="A1:Z100"):
        return _ok(werte=[["Kopf"], ["Wert"]])

    def tabelle_schreiben(self, spreadsheet_id, bereich, werte, *, bestaetigt=False):
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True,
                    "vorschau": {"bereich": bereich, "zeilen": len(werte or [])}}
        return _ok(aktualisiert=len(werte or []))
