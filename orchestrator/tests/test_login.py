"""LUNA_OS_UI_ROADMAP Etappen 2 + 6: Login-Formular mit Sitzungs-Cookie (Schluesselbund, 30 Tage angemeldet) und
Passkeys (Face ID). HTTP-Basic bleibt fuer Maschinen-Zugaenge; Webhooks bleiben offen."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from orchestrator.core.passkeys import Passkeys
from orchestrator.core.sitzungen import COOKIE, Sitzungen

HOST = "os.test"
ORIGIN = "https://" + HOST


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Geraet:
    """Simuliertes Face-ID-Geraet (Plattform-Authenticator, Attestation „none“, ES256)."""
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = b"geraet-" + hashlib.sha256(str(id(self)).encode()).digest()[:8]
        self.zaehler = 0

    def _cose(self) -> bytes:
        n = self.key.public_key().public_numbers()
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})

    def erstellen(self, optionen: dict, origin: str = ORIGIN) -> dict:
        cd = json.dumps({"type": "webauthn.create", "challenge": optionen["challenge"], "origin": origin}).encode()
        auth = hashlib.sha256(optionen["rp"]["id"].encode()).digest() + bytes([0x45]) + (0).to_bytes(4, "big") \
            + bytes(16) + len(self.cred_id).to_bytes(2, "big") + self.cred_id + self._cose()
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth})
        return {"id": _b64(self.cred_id), "rawId": _b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": _b64(cd), "attestationObject": _b64(att)}, "clientExtensionResults": {}}

    def anmelden(self, optionen: dict, origin: str = ORIGIN, uv: bool = True) -> dict:
        self.zaehler += 1
        cd = json.dumps({"type": "webauthn.get", "challenge": optionen["challenge"], "origin": origin}).encode()
        auth = hashlib.sha256(optionen["rpId"].encode()).digest() + bytes([0x05 if uv else 0x01]) \
            + self.zaehler.to_bytes(4, "big")
        sig = self.key.sign(auth + hashlib.sha256(cd).digest(), ec.ECDSA(hashes.SHA256()))
        return {"id": _b64(self.cred_id), "rawId": _b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": _b64(cd), "authenticatorData": _b64(auth), "signature": _b64(sig)},
                "clientExtensionResults": {}}


class LoginBasis(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        self.w = webapp
        self.orig = (webapp._PW, webapp._USER, webapp._sitzungen, webapp._passkeys)
        d = Path(tempfile.mkdtemp())
        webapp._PW, webapp._USER = "richtig-geheim", "ceo"
        webapp._sitzungen = Sitzungen(d / "sitzungen.json")
        webapp._passkeys = Passkeys(d / "passkeys.json")
        self.c = TestClient(webapp.app, base_url=ORIGIN, follow_redirects=False)

    def tearDown(self):
        self.w._PW, self.w._USER, self.w._sitzungen, self.w._passkeys = self.orig

    def einloggen(self, pw="richtig-geheim", weiter="/"):
        return self.c.post("/api/login", data={"username": "ceo", "password": pw, "weiter": weiter})


class TestLogin(LoginBasis):
    def test_1_ohne_login(self):
        r = self.c.get("/", headers={"accept": "text/html"})
        self.assertEqual((r.status_code, r.headers["location"]), (303, "/login?weiter=/"))
        r = self.c.get("/api/state")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("www-authenticate", r.headers)                 # kein graues Basic-Fenster fuer Menschen
        self.assertEqual(self.c.get("/login").status_code, 200)
        self.assertIn('autocomplete="current-password"', self.c.get("/login").text)

    def test_2_basic_fuer_maschinen(self):
        self.assertEqual(self.c.get("/api/state", auth=("ceo", "richtig-geheim")).status_code, 200)
        r = self.c.get("/api/state", auth=("ceo", "falsch"))
        self.assertEqual((r.status_code, r.headers.get("www-authenticate")), (401, "Basic"))
        self.assertNotEqual(self.c.get("/api/webhook/instagram").status_code, 401)     # Webhooks sichern sich selbst

    def test_3_formular_und_cookie(self):
        r = self.einloggen("falsch", "/x")
        self.assertEqual(r.headers["location"], "/login?fehler=falsch&weiter=/x")
        self.assertNotIn(COOKIE, r.cookies)
        r = self.einloggen(weiter="/#finanzen")
        self.assertEqual(r.status_code, 303)
        kopf = [v for k, v in r.headers.multi_items() if k == "set-cookie" and v.startswith(COOKIE)][0].lower()
        for teil in ("httponly", "secure", "samesite=lax", "max-age=2592000"):
            self.assertIn(teil, kopf)
        self.assertEqual(self.c.get("/api/state").status_code, 200)                    # Cookie traegt
        self.assertEqual(self.c.get("/login").status_code, 303)                        # schon angemeldet
        self.assertEqual(self.einloggen(weiter="//boese.example").headers["location"], "/")   # keine Fremd-Umleitung

    def test_4_fremde_seite_abgelehnt(self):
        self.einloggen()
        self.assertEqual(self.c.post("/api/nutzung", json={"app": "dash"}).status_code, 403)          # ohne Origin
        self.assertEqual(self.c.post("/api/nutzung", json={"app": "dash"},
                                     headers={"origin": "https://boese.example"}).status_code, 403)
        self.assertEqual(self.c.post("/api/nutzung", json={"app": "dash"}, headers={"origin": ORIGIN}).status_code, 200)

    def test_5_bremse(self):
        for _ in range(5):
            self.einloggen("falsch")
        r = self.einloggen()                                                       # richtig, aber gesperrt
        self.assertIn("fehler=gesperrt", r.headers["location"])
        self.assertNotIn(COOKIE, r.cookies)

    def test_5b_bremse_nicht_per_xff_umgehbar(self):
        for i in range(5):
            self.c.post("/api/login", data={"username": "ceo", "password": "falsch"},
                        headers={"x-real-ip": "203.0.113.7", "x-forwarded-for": f"10.0.0.{i}"})
        r = self.c.post("/api/login", data={"username": "ceo", "password": "richtig-geheim"},
                        headers={"x-real-ip": "203.0.113.7", "x-forwarded-for": "10.9.9.9"})
        self.assertIn("fehler=gesperrt", r.headers["location"])                    # gefaelschtes XFF hilft nicht

    def test_6_abmelden_und_widerrufen(self):
        self.einloggen()
        zweit = self.c.__class__(self.w.app, base_url=ORIGIN, follow_redirects=False)
        zweit.post("/api/login", data={"username": "ceo", "password": "richtig-geheim"})
        d = self.c.get("/api/sitzungen").json()
        self.assertEqual((len(d["sitzungen"]), sum(s["aktuell"] for s in d["sitzungen"])), (2, 1))
        r = self.c.post("/api/sitzungen/widerrufen", json={"alle": True}, headers={"origin": ORIGIN}).json()
        self.assertEqual(r["abgemeldet"], 1)
        self.assertEqual(zweit.get("/api/state").status_code, 401)                 # anderes Geraet raus
        self.assertEqual(self.c.get("/api/state").status_code, 200)                # dieses bleibt
        self.c.post("/api/logout", json={}, headers={"origin": ORIGIN})
        self.c.cookies.clear()
        self.assertEqual(self.c.get("/api/state").status_code, 401)

    def test_7_nur_hash_gespeichert(self):
        r = self.einloggen()
        token = r.cookies.get(COOKIE)
        inhalt = self.w._sitzungen.pfad.read_text()
        self.assertNotIn(token, inhalt)
        self.assertIn(hashlib.sha256(token.encode()).hexdigest(), inhalt)


class TestPasskey(LoginBasis):
    def _einrichten(self, g: Geraet) -> dict:
        start = self.c.post("/api/passkey/registrieren/start", headers={"origin": ORIGIN}).json()
        self.assertEqual(start["optionen"]["authenticatorSelection"]["residentKey"], "required")
        return self.c.post("/api/passkey/registrieren/ende", headers={"origin": ORIGIN},
                           json={"challenge_id": start["challenge_id"], "credential": g.erstellen(start["optionen"])}).json()

    def test_1_einrichten_und_anmelden(self):
        self.einloggen()
        g = Geraet()
        self.assertTrue(self._einrichten(g)["ok"])
        self.assertEqual(len(self.c.get("/api/sitzungen").json()["passkeys"]), 1)
        neu = self.c.__class__(self.w.app, base_url=ORIGIN, follow_redirects=False)       # frisches Geraet, kein Cookie
        self.assertEqual(neu.get("/api/state").status_code, 401)
        s = neu.post("/api/passkey/login/start").json()
        r = neu.post("/api/passkey/login/ende", headers={"origin": ORIGIN},
                     json={"challenge_id": s["challenge_id"], "credential": g.anmelden(s["optionen"]), "weiter": "/"})
        self.assertTrue(r.json()["ok"], r.json())
        self.assertEqual(neu.get("/api/state").status_code, 200)
        # Challenge nur einmal verwendbar
        r = neu.post("/api/passkey/login/ende", headers={"origin": ORIGIN},
                     json={"challenge_id": s["challenge_id"], "credential": g.anmelden(s["optionen"])})
        self.assertEqual(r.status_code, 401)

    def test_2_abgelehnt(self):
        self.einloggen()
        g, fremd = Geraet(), Geraet()
        self._einrichten(g)
        neu = self.c.__class__(self.w.app, base_url=ORIGIN, follow_redirects=False)
        for cred_fn in (lambda o: fremd.anmelden(o),                               # nicht hinterlegt
                        lambda o: g.anmelden(o, origin="https://boese.example"),    # falsche Herkunft
                        lambda o: g.anmelden(o, uv=False)):                         # ohne Face ID
            s = neu.post("/api/passkey/login/start").json()
            r = neu.post("/api/passkey/login/ende", headers={"origin": ORIGIN},
                         json={"challenge_id": s["challenge_id"], "credential": cred_fn(s["optionen"])})
            self.assertEqual(r.status_code, 401, r.json())
        self.assertEqual(neu.get("/api/state").status_code, 401)

    def test_3_nur_https_und_loeschen(self):
        http = self.c.__class__(self.w.app, base_url="http://192.168.178.129:8765", follow_redirects=False)
        self.assertEqual(http.post("/api/passkey/login/start").status_code, 400)
        self.einloggen()
        g = Geraet()
        pid = self._einrichten(g)["passkey"]["id"]
        self.assertTrue(self.c.post("/api/passkey/loeschen", json={"id": pid}, headers={"origin": ORIGIN}).json()["ok"])
        neu = self.c.__class__(self.w.app, base_url=ORIGIN, follow_redirects=False)
        s = neu.post("/api/passkey/login/start").json()
        r = neu.post("/api/passkey/login/ende", headers={"origin": ORIGIN},
                     json={"challenge_id": s["challenge_id"], "credential": g.anmelden(s["optionen"])})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
