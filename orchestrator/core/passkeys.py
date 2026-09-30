"""Passkeys (WebAuthn) fuer LUNA-OS (LUNA_OS_UI_ROADMAP Etappe 6, CEO 2026-09-30: „Passkey kannst du gern mit
einbauen“) -- Anmeldung per Face ID/Touch ID statt Passwort; das Passwort bleibt als Notweg.

Pruefung der Signaturen mit der Bibliothek `webauthn` (py_webauthn, Open Source, OSV ohne Funde 2026-09-30).
Gespeichert werden nur **oeffentliche** Schluessel (Datei auf der NAS unter `orchestrator/state/`, nicht im Git);
der private Schluessel verlaesst das Geraet nie. Passkeys sind „auffindbar“ (resident), die Anmeldung braucht daher
keinen Nutzernamen, und verlangen Nutzer-Verifikation (Face ID/Geraete-Code). Challenges gelten 5 Minuten und nur
einmal. Passkeys funktionieren nur ueber HTTPS (`os.hanserautisch.synology.me`), nicht ueber die LAN-IP.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path

CHALLENGE_S = 300


def _b64(b: bytes) -> str:
    from webauthn.helpers import bytes_to_base64url
    return bytes_to_base64url(b)


def _bytes(s: str) -> bytes:
    from webauthn.helpers import base64url_to_bytes
    return base64url_to_bytes(s)


class PasskeyFehler(ValueError):
    pass


class Passkeys:
    def __init__(self, pfad: Path | str, *, rp_name: str = "LUNA"):
        self.pfad = Path(pfad)
        self.rp_name = rp_name
        self._lock = threading.Lock()
        self._challenges: dict[str, dict] = {}

    # -- Speicher ------------------------------------------------------------
    def _laden(self) -> list[dict]:
        try:
            d = json.loads(self.pfad.read_text(encoding="utf-8"))
            return d if isinstance(d, list) else []
        except (OSError, ValueError):
            return []

    def _speichern(self, liste: list[dict]) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(liste, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
        tmp.replace(self.pfad)

    def liste(self, username: str) -> list[dict]:
        return [{k: p.get(k) for k in ("id", "geraet", "erstellt", "zuletzt")}
                for p in self._laden() if p.get("username") == username]

    def loeschen(self, username: str, cred_id: str) -> bool:
        with self._lock:
            alt = self._laden()
            neu = [p for p in alt if not (p.get("username") == username and p.get("id") == cred_id)]
            if len(neu) == len(alt):
                return False
            self._speichern(neu)
        return True

    # -- Challenges ----------------------------------------------------------
    def _challenge_merken(self, challenge: bytes, **daten) -> str:
        jetzt = time.time()
        for k in [k for k, v in self._challenges.items() if v["bis"] < jetzt]:
            del self._challenges[k]
        cid = secrets.token_urlsafe(16)
        self._challenges[cid] = {"challenge": challenge, "bis": jetzt + CHALLENGE_S, **daten}
        return cid

    def _challenge_holen(self, cid: str) -> dict:
        c = self._challenges.pop(cid or "", None)            # nur einmal verwendbar
        if not c or c["bis"] < time.time():
            raise PasskeyFehler("Anfrage abgelaufen -- bitte noch einmal versuchen.")
        return c

    # -- Registrieren (nur angemeldet) ----------------------------------------
    def registrierung_start(self, *, rp_id: str, username: str, anzeigename: str, art: str) -> dict:
        from webauthn import generate_registration_options, options_to_json
        from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
                                              ResidentKeyRequirement, UserVerificationRequirement)
        vorhanden = [PublicKeyCredentialDescriptor(id=_bytes(p["id"])) for p in self._laden()
                     if p.get("username") == username]
        opt = generate_registration_options(
            rp_id=rp_id, rp_name=self.rp_name, user_name=username, user_display_name=anzeigename or username,
            user_id=hashlib.sha256(("luna-os:" + username).encode()).digest()[:16],
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=vorhanden)
        cid = self._challenge_merken(opt.challenge, zweck="registrieren", username=username, art=art)
        return {"challenge_id": cid, "optionen": json.loads(options_to_json(opt))}

    def registrierung_ende(self, *, challenge_id: str, credential: dict, rp_id: str, origin: str,
                           username: str, geraet: str = "") -> dict:
        from webauthn import verify_registration_response
        c = self._challenge_holen(challenge_id)
        if c.get("zweck") != "registrieren" or c.get("username") != username:
            raise PasskeyFehler("Anfrage passt nicht zu dieser Anmeldung.")
        try:
            v = verify_registration_response(credential=credential, expected_challenge=c["challenge"],
                                             expected_rp_id=rp_id, expected_origin=origin,
                                             require_user_verification=True)
        except Exception as e:                                    # Bibliothek wirft je Fehler eigene Klassen
            raise PasskeyFehler(f"Passkey nicht bestaetigt: {e}") from e
        jetzt = datetime.now().isoformat(timespec="seconds")
        eintrag = {"id": _b64(v.credential_id), "username": username, "art": c.get("art", ""),
                   "public_key": _b64(v.credential_public_key), "sign_count": v.sign_count,
                   "geraet": geraet[:60], "erstellt": jetzt, "zuletzt": jetzt}
        with self._lock:
            liste = [p for p in self._laden() if p.get("id") != eintrag["id"]]
            self._speichern(liste + [eintrag])
        return {k: eintrag[k] for k in ("id", "geraet", "erstellt")}

    # -- Anmelden (offen) ------------------------------------------------------
    def login_start(self, *, rp_id: str) -> dict:
        from webauthn import generate_authentication_options, options_to_json
        from webauthn.helpers.structs import UserVerificationRequirement
        opt = generate_authentication_options(rp_id=rp_id, user_verification=UserVerificationRequirement.REQUIRED)
        cid = self._challenge_merken(opt.challenge, zweck="login")
        return {"challenge_id": cid, "optionen": json.loads(options_to_json(opt))}

    def login_ende(self, *, challenge_id: str, credential: dict, rp_id: str, origin: str) -> dict:
        """Gueltige Face-ID-Anmeldung -> {username, art}; sonst PasskeyFehler."""
        from webauthn import verify_authentication_response
        c = self._challenge_holen(challenge_id)
        if c.get("zweck") != "login":
            raise PasskeyFehler("Anfrage passt nicht.")
        cred_id = (credential or {}).get("id") or (credential or {}).get("rawId") or ""
        with self._lock:
            liste = self._laden()
            p = next((x for x in liste if x.get("id") == cred_id), None)
            if not p:
                raise PasskeyFehler("Dieser Passkey ist bei LUNA nicht (mehr) hinterlegt.")
            try:
                v = verify_authentication_response(credential=credential, expected_challenge=c["challenge"],
                                                   expected_rp_id=rp_id, expected_origin=origin,
                                                   credential_public_key=_bytes(p["public_key"]),
                                                   credential_current_sign_count=int(p.get("sign_count") or 0),
                                                   require_user_verification=True)
            except Exception as e:
                raise PasskeyFehler(f"Face ID nicht bestaetigt: {e}") from e
            p["sign_count"] = v.new_sign_count
            p["zuletzt"] = datetime.now().isoformat(timespec="seconds")
            self._speichern(liste)
        return {"username": p["username"], "art": p.get("art", "")}
