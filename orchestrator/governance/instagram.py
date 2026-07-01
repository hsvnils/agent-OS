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


class MockInstagramMessaging(InstagramMessaging):
    """Offline-Variante: Signatur immer 'gueltig' -- fuer Self-Checks ohne Keys/Netz."""

    def __init__(self):
        super().__init__(InstagramAuth(app_secret="mock", verify_token="mock", page_token="mock"))

    def signatur_gueltig(self, body: bytes, header: str) -> bool:
        return True
