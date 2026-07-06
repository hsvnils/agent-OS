"""Teil A / Phase 1 -- Instagram-Messaging-Capability (Capability-Muster) fuers Collab-CRM.

Liest eingehende Kooperations-DMs ueber die **Instagram Messaging API** (Meta Graph, Professional-Account).
**NUR Empfangen/Lesen -- kein Senden** (Aussendarstellung = Oeffentlichkeit = CEO-Tor).

Sicherheit: Webhook-Payloads werden per **HMAC-SHA256-Signatur** (Meta App-Secret, Header
`X-Hub-Signature-256`) verifiziert; die Verify-Challenge (GET) prueft den Verify-Token. Fehlen die
Credentials -> sauberer **Fall-B-Hinweis** (CEO-Tor + CISO), kein Absturz. Secrets nie im Klartext
(Leck-Schutz im Tool-Layer). Der `MockInstagramMessaging` deckt Parsing/Gating offline ab (kein Netz/Key).

Env (orchestrator/.env): INSTAGRAM_APP_SECRET, INSTAGRAM_VERIFY_TOKEN, INSTAGRAM_PAGE_TOKEN.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


def _fall_b(capability: str = "instagram_messaging") -> str:
    return (
        "ANFRAGE an CEO (Freigabe noetig)\n"
        f"- Capability: {capability}\n"
        "- Fuer: Collab-CRM (CRO) ueber LUNA (HoA)\n"
        "- Grund: neuer externer Zugang (Meta/Instagram, Empfangen/Lesen) -> CEO-Tor + CISO\n"
        "- Status: nicht aktiv bis Meta-Credentials in orchestrator/.env "
        "(INSTAGRAM_APP_SECRET/INSTAGRAM_VERIFY_TOKEN/INSTAGRAM_PAGE_TOKEN)"
    )


@dataclass
class InstagramAuth:
    app_secret: str = ""
    verify_token: str = ""
    page_token: str = ""

    @classmethod
    def from_env(cls, env: dict | None = None) -> "InstagramAuth":
        import os
        e = env if env is not None else os.environ
        return cls(app_secret=(e.get("INSTAGRAM_APP_SECRET") or "").strip(),
                   verify_token=(e.get("INSTAGRAM_VERIFY_TOKEN") or "").strip(),
                   page_token=(e.get("INSTAGRAM_PAGE_TOKEN") or "").strip())

    def verfuegbar(self) -> bool:
        # Empfang + Verifikation brauchen App-Secret + Verify-Token (Page-Token erst fuer aktive Reads).
        return bool(self.app_secret and self.verify_token)


class InstagramMessaging:
    """Verifiziert + parst eingehende Instagram-Webhooks. Kein Senden."""

    def __init__(self, auth: InstagramAuth):
        self.auth = auth

    def verfuegbar(self) -> bool:
        return self.auth.verfuegbar()

    def fall_b(self) -> dict:
        return {"ok": False, "fall_b": True, "hinweis": _fall_b()}

    def verify_challenge(self, mode: str, token: str, challenge: str):
        """GET-Handshake von Meta: gibt `challenge` zurueck, wenn mode=subscribe + Token stimmt, sonst None."""
        if mode == "subscribe" and token and hmac.compare_digest(token, self.auth.verify_token):
            return challenge
        return None

    def signatur_gueltig(self, body: bytes, header: str) -> bool:
        """Prueft `X-Hub-Signature-256` (HMAC-SHA256 des Roh-Bodys mit dem Meta-App-Secret)."""
        if not self.auth.app_secret or not header:
            return False
        sig = header[7:] if header.startswith("sha256=") else header
        erwartet = hmac.new(self.auth.app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, erwartet)

    @staticmethod
    def nachrichten_aus_webhook(payload: dict) -> list[dict]:
        """Normalisiert einen Instagram-Messaging-Webhook zu [{extern_id, absender, text, ts}] -- nur echte
        eingehende Text-Nachrichten (keine Echos/Reactions/Read-Events/Attachments). Robust gegen mehrere
        Payload-Formen: reales Envelope `entry[].messaging[]` bzw. `entry[].changes[].value`, sowie Metas
        flache Feldprobe `{"field":"messages","value":{...}}`."""
        payload = payload or {}
        rohe: list[dict] = []
        for entry in payload.get("entry", []):
            rohe.extend(entry.get("messaging", []) or [])
            for ch in entry.get("changes", []) or []:                 # Feld-Abo-Form (changes[].value)
                if ch.get("field") == "messages" and isinstance(ch.get("value"), dict):
                    rohe.append(ch["value"])
        if not rohe and payload.get("field") == "messages" and isinstance(payload.get("value"), dict):
            rohe.append(payload["value"])                             # Metas flache Feldprobe

        out = []
        for m in rohe:
            msg = m.get("message") or {}
            if msg.get("is_echo"):
                continue  # eigene ausgehende Nachricht
            text = (msg.get("text") or "").strip()
            if not text:
                continue  # nur Text (Attachments/Reactions ignorieren)
            out.append({"extern_id": msg.get("mid") or "",
                        "absender": (m.get("sender") or {}).get("id", ""),
                        "text": text, "ts": m.get("timestamp")})
        return out


class InstagramConversations:
    """Liest eingehende IG-DMs per Graph-API-**Poll** (Conversations-API) -- fuers EIGENE Konto, NUR Lesen.

    Anders als der Webhook (Advanced-Access-Review noetig) reicht hier ein Access-Token des eigenen Kontos
    mit `instagram_business_basic` + `instagram_business_manage_messages`. Endpoints (Instagram-Login):
    `GET /me/conversations?platform=instagram` -> Threads; `GET /{conv}?fields=messages{id,created_time,from,
    to,message}` -> Nachrichten. Injizierbarer HTTP -> offline testbar. Kein Senden.
    """

    def __init__(self, token: str, own_id, *, http=None,
                 base: str = "https://graph.facebook.com/v25.0", timeout: int = 15):
        # Default = Facebook-Login-Variante (graph.facebook.com, Konversationen ueber {ig-user-id}).
        # Fuer die Instagram-Login-Variante base auf graph.instagram.com setzen -> dann 'me/conversations'.
        self.token = (token or "").strip()
        self.own_id = str(own_id or "").strip()
        self.http = http or self._get
        self.base = base
        self.timeout = timeout              # kurzer Timeout -> haengende/leere Endseiten kosten wenig
        self.letzter_fehler = ""            # letzte API-Fehlermeldung (fuer Diagnose)

    def _konv_pfad(self) -> str:
        # DMs laufen ueber den SEITEN-Knoten -> `me/conversations` (Seiten-Token). Der IG-Account-Knoten
        # `{ig-id}/conversations` liefert "(#3) Application does not have the capability". `me` passt fuer
        # Seiten-Token (=Seite) UND Instagram-Login-Token (=IG-Konto).
        return "me/conversations"

    @property
    def verfuegbar(self) -> bool:
        return bool(self.token and self.own_id)

    def _get(self, pfad: str, params: dict) -> dict:
        import json
        import urllib.error
        import urllib.parse
        import urllib.request
        p = dict(params or {}); p["access_token"] = self.token
        url = f"{self.base}/{pfad}?{urllib.parse.urlencode(p)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:      # Metas Fehler-JSON (message/#code) lesbar durchreichen
            try:
                body = e.read().decode("utf-8")[:300]
            except Exception:
                body = ""
            raise RuntimeError(f"HTTP {e.code}: {body or e.reason}")

    def _fehler_pruefen(self, d) -> bool:
        """True (+ letzter_fehler gesetzt), wenn die API ein Fehler-Objekt lieferte."""
        if isinstance(d, dict) and d.get("error"):
            err = d["error"]
            self.letzter_fehler = str(err.get("message") or err)[:200] if isinstance(err, dict) else str(err)[:200]
            return True
        return False

    def konversationen(self, *, limit: int = 25, deadline: float = 0.0) -> list[str]:
        # Meta-Eigenheit: `platform=instagram` vertraegt pro Seite nur **limit=1** -- hoehere Limits liefern
        # zuverlaessig HTTP 500 / Code 1 ("Please reduce the amount of data you're asking for"). Deshalb
        # blaettern wir Thread fuer Thread mit dem `after`-Cursor durch, bis `limit` Threads gesammelt sind
        # oder keine Seite mehr folgt. Threads kommen nach Aktivitaet sortiert (neueste zuerst).
        # `deadline` (Unix-Sekunden, 0 = aus): Abbruch, sobald ueberschritten -> haelt Backfill-Laufzeit im Zaum.
        import time
        ids: list[str] = []
        after = None
        for _ in range(max(1, limit)):
            if deadline and time.time() > deadline:
                break
            params = {"platform": "instagram", "fields": "id", "limit": "1"}
            if after:
                params["after"] = after
            try:
                d = self.http(self._konv_pfad(), params)
            except Exception as exc:
                self.letzter_fehler = str(exc)[:200]
                break
            if self._fehler_pruefen(d):
                break
            data = (d or {}).get("data", []) or []
            for c in data:
                if c.get("id"):
                    ids.append(c["id"])
            after = (((d or {}).get("paging") or {}).get("cursors") or {}).get("after")
            if not after or not data:
                break
        return ids

    def nachrichten(self, conv_id: str) -> list[dict]:
        """[{id, from_id, from_username, text, ts}] der (max. 20) letzten Nachrichten eines Threads."""
        try:
            d = self.http(conv_id, {"fields": "messages.limit(20){id,created_time,from,to,message}"})
        except Exception as exc:
            self.letzter_fehler = str(exc)[:200]
            return []
        if self._fehler_pruefen(d):
            return []
        msgs = (((d or {}).get("messages") or {}).get("data")) or []
        return [self._norm(m) for m in msgs]

    @staticmethod
    def _norm(m: dict) -> dict:
        frm = m.get("from") or {}
        return {"id": m.get("id", ""), "from_id": str(frm.get("id", "")),
                "from_username": frm.get("username", ""), "text": (m.get("message") or "").strip(),
                "ts": m.get("created_time", "")}

    @staticmethod
    def _ts(iso: str) -> float:
        """ISO-8601 (Meta: '...+0000') -> Unix-Sekunden; 0.0 bei Fehler."""
        try:
            import datetime
            return datetime.datetime.fromisoformat((iso or "").replace("+0000", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def nachrichten_seit(self, conv_id: str, *, seit_ts: float = 0.0, max_seiten: int = 40,
                         pro_seite: int = 25, deadline: float = 0.0) -> list[dict]:
        """Alle Nachrichten eines Threads **ab** `seit_ts` (Unix-Sekunden) -- durch Zurueckblaettern der
        `messages`-Kante per `.after()`-Cursor (Nachrichten kommen neueste-zuerst). Stoppt, sobald eine
        Nachricht aelter als `seit_ts` erreicht ist, keine Seite mehr folgt, `max_seiten` erreicht ist oder
        die `deadline` (Unix-Sekunden, 0 = aus) ueberschritten wird. Fuer den einmaligen Rueck-Scan (Backfill).
        """
        import time
        out: list[dict] = []
        after = None
        for _ in range(max(1, max_seiten)):
            if deadline and time.time() > deadline:
                break
            felder = f"messages.limit({pro_seite})"
            if after:
                felder += f".after({after})"
            felder += "{id,created_time,from,message}"
            try:
                d = self.http(conv_id, {"fields": felder})
            except Exception as exc:
                self.letzter_fehler = str(exc)[:200]
                break
            if self._fehler_pruefen(d):
                break
            ed = (d or {}).get("messages") or {}
            data = ed.get("data") or []
            aelter = False
            for m in data:
                if seit_ts and self._ts(m.get("created_time")) < seit_ts:
                    aelter = True                 # aelter als Grenze -> nicht uebernehmen (Rest ist noch aelter)
                    continue
                out.append(self._norm(m))
            after = ((ed.get("paging") or {}).get("cursors") or {}).get("after")
            if aelter or not after or not data:
                break
        return out


class MockInstagramMessaging(InstagramMessaging):
    """Offline-Variante: Signatur immer 'gueltig' -- fuer Self-Checks ohne Keys/Netz."""

    def __init__(self):
        super().__init__(InstagramAuth(app_secret="mock", verify_token="mock", page_token="mock"))

    def signatur_gueltig(self, body: bytes, header: str) -> bool:
        return True
