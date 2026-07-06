"""Selbst-erneuernder Instagram/Meta-Token-Manager.

Haelt einen **langlebigen (60-Tage) Nutzer-Token** frisch und leitet daraus den **permanenten Seiten-Token**
ab (ein Page-Token aus einem long-lived User-Token laeuft **nicht** ab). Der Nutzer-Token wird automatisch
verlaengert, bevor er ablaeuft -> nach dem einmaligen Setzen des Seeds muss nichts mehr manuell nachgelegt
werden.

Ablauf (Meta Graph):
  kurzlebiger Nutzer-Token --(fb_exchange_token + App-Secret)--> 60-Tage-Nutzer-Token
  60-Tage-Nutzer-Token     --(GET /me/accounts)-->               permanenter Seiten-Token

Env (orchestrator/.env):
  INSTAGRAM_USER_TOKEN  -- Seed: (kurzlebiger) Nutzer-Token aus dem Graph-Explorer (einmalig).
  INSTAGRAM_APP_SECRET  -- App-Geheimnis (fuer den Token-Austausch).
  INSTAGRAM_APP_ID      -- Default 2013312522627370.
  INSTAGRAM_IG_USER_ID  -- ID des verknuepften IG-Business-Kontos (zur Seitenauswahl).
Persistenz: `state_path` (JSON {user_token, expires_at}); ueberlebt Neustarts, wird NICHT deployt/committed.
Secrets werden nie geloggt/zurueckgegeben -- nur der abgeleitete Token wird intern verwendet.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.facebook.com/v25.0"
DEFAULT_APP_ID = "2013312522627370"


def default_store_path() -> str:
    # orchestrator/state/instagram_token.json (relativ zum Paket -> cwd-unabhaengig).
    return str(Path(__file__).resolve().parents[1] / "state" / "instagram_token.json")


class InstagramTokenManager:
    def __init__(self, *, user_token_seed: str = "", app_id: str = DEFAULT_APP_ID, app_secret: str = "",
                 state_path: str | None = None, http=None, refresh_vor_tagen: int = 7,
                 page_cache_ttl: int = 6 * 3600):
        self.seed = (user_token_seed or "").strip()
        self.app_id = (app_id or DEFAULT_APP_ID).strip()
        self.app_secret = (app_secret or "").strip()
        self.state_path = state_path or default_store_path()
        self.http = http or self._http
        self.refresh_vor = refresh_vor_tagen * 86400
        self.page_cache_ttl = page_cache_ttl
        self.letzter_fehler = ""
        self._page_cache = ""
        self._page_cache_ts = 0.0

    @classmethod
    def from_env(cls, env: dict | None = None, *, state_path: str | None = None, http=None) -> "InstagramTokenManager":
        e = env if env is not None else os.environ
        return cls(user_token_seed=e.get("INSTAGRAM_USER_TOKEN", ""),
                   app_id=e.get("INSTAGRAM_APP_ID", DEFAULT_APP_ID),
                   app_secret=e.get("INSTAGRAM_APP_SECRET", ""),
                   state_path=state_path or e.get("INSTAGRAM_TOKEN_STORE"), http=http)

    def verfuegbar(self) -> bool:
        return bool(self.app_secret and (self.seed or self._load().get("user_token")))

    # ---------- HTTP ----------
    def _http(self, path: str, params: dict) -> dict:
        url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def _api(self, path: str, params: dict):
        """(daten, fehler) -- Metas Fehler-JSON wird lesbar durchgereicht, kein Absturz."""
        try:
            d = self.http(path, params)
        except urllib.error.HTTPError as e:
            try:
                d = json.loads(e.read().decode("utf-8"))
            except Exception:
                return None, f"HTTP {e.code}"
        except Exception as ex:
            return None, str(ex)[:160]
        if isinstance(d, dict) and d.get("error"):
            err = d["error"]
            return None, str(err.get("message") or err)[:160] if isinstance(err, dict) else str(err)[:160]
        return d, ""

    # ---------- Store ----------
    def _load(self) -> dict:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, token: str, expires_at: int) -> None:
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            tmp = self.state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"user_token": token, "expires_at": int(expires_at)}, f)
            os.replace(tmp, self.state_path)
            try:
                os.chmod(self.state_path, 0o600)
            except Exception:
                pass
        except Exception as ex:
            self.letzter_fehler = f"Token-Store nicht schreibbar: {ex}"[:160]

    def _exchange(self, token: str):
        """(neuer_token, expires_in, fehler) -- long-lived Nutzer-Token via fb_exchange_token."""
        d, err = self._api("oauth/access_token", {
            "grant_type": "fb_exchange_token", "client_id": self.app_id,
            "client_secret": self.app_secret, "fb_exchange_token": token})
        if err or not d:
            return "", 0, err or "kein Token in Antwort"
        return d.get("access_token", ""), int(d.get("expires_in") or 0), ""

    # ---------- Tokens ----------
    def user_token(self) -> str:
        """Gueltiger langlebiger Nutzer-Token (aus Store; verlaengert bei <refresh_vor; Seed als Fallback)."""
        st = self._load()
        tok, exp = st.get("user_token", ""), int(st.get("expires_at") or 0)
        now = time.time()
        if tok and exp - now > self.refresh_vor:
            return tok                                   # noch lange gueltig -> nichts tun
        basis = tok or self.seed                         # verlaengern: gespeicherten Token, sonst .env-Seed
        if not basis:
            self.letzter_fehler = "kein Nutzer-Token (Store leer + kein Seed in .env)"
            return ""
        neu, expires_in, err = self._exchange(basis)
        if err or not neu:
            self.letzter_fehler = f"Token-Verlaengerung fehlgeschlagen: {err}"[:160]
            return tok                                   # notfalls den (evtl. noch gueltigen) alten zurueck
        self._save(neu, int(now + (expires_in or 60 * 86400)))
        self._page_cache = ""                            # Nutzer-Token neu -> Seiten-Token neu ableiten
        return neu

    def page_token(self, *, ig_user_id: str = "") -> str:
        """Permanenter Seiten-Token, aus dem langlebigen Nutzer-Token abgeleitet. Prozess-Cache mit TTL."""
        now = time.time()
        if self._page_cache and (now - self._page_cache_ts) < self.page_cache_ttl:
            return self._page_cache
        ut = self.user_token()
        if not ut:
            return ""
        d, err = self._api("me/accounts", {
            "fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": ut})
        if err or not d:
            self.letzter_fehler = err or "me/accounts lieferte keine Daten"
            return ""
        pages = d.get("data", []) or []
        chosen = None
        for pg in pages:                                 # bevorzugt die Seite mit dem passenden IG-Konto
            igb = pg.get("instagram_business_account") or {}
            if ig_user_id and str(igb.get("id")) == str(ig_user_id):
                chosen = pg
                break
        chosen = chosen or (pages[0] if pages else None)
        if not chosen or not chosen.get("access_token"):
            self.letzter_fehler = "keine Seite mit Seiten-Token gefunden (Rechte/Verknuepfung pruefen)"
            return ""
        self._page_cache = chosen["access_token"]
        self._page_cache_ts = now
        return self._page_cache


def ig_reader_aus_env(env: dict, *, state_path: str | None = None, http=None):
    """Baut den `InstagramConversations`-Reader aus der .env.

    Bevorzugt den selbst-erneuernden Manager (INSTAGRAM_USER_TOKEN + INSTAGRAM_APP_SECRET -> permanenter
    Seiten-Token). Faellt sonst auf den statischen INSTAGRAM_ACCESS_TOKEN/INSTAGRAM_PAGE_TOKEN zurueck.
    """
    from .instagram import InstagramConversations
    igid = (env.get("INSTAGRAM_IG_USER_ID") or "").strip()
    token = ""
    if env.get("INSTAGRAM_USER_TOKEN") and env.get("INSTAGRAM_APP_SECRET"):
        mgr = InstagramTokenManager.from_env(env, state_path=state_path, http=http)
        token = mgr.page_token(ig_user_id=igid)
    if not token:                                        # Fallback: statischer Token (falls gesetzt)
        token = (env.get("INSTAGRAM_ACCESS_TOKEN") or env.get("INSTAGRAM_PAGE_TOKEN") or "").strip()
    return InstagramConversations(token, igid)
