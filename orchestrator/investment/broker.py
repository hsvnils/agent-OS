"""GATE C -- Alpaca-Paper-Broker-Adapter (simulierter Handel mit echten Kursen).

Austauschbarer Ausfuehrungs-Pfad (governance/investment.md, Abschnitt 2): advisory = nur loggen/melden;
**paper = dieser Adapter** gegen die Alpaca **Paper**-API (kein echtes Geld). Injizierbarer HTTP -> offline
testbar. Inert ohne Keys (`verfuegbar == False`).

Governance: paper-Modus aktivieren = **CEO-Tor**; jede Order zusaetzlich CEO-bestaetigt; Risiko-Limits werden
ab paper **hart** vom Risk-Agent geprueft (siehe `risk.RiskAgent.pruefe_order`). Keys via `.env`
(`ALPACA_API_KEY` / `ALPACA_API_SECRET`), Leck-Schutz -- nie committen.
"""
from __future__ import annotations

import json
import urllib.request

_BASE = "https://paper-api.alpaca.markets"

# CoinGecko-ID -> Alpaca-Krypto-Handelssymbol (USD-Paare). Nur bei Alpaca handelbare Majors; Rest -> None.
ALPACA_KRYPTO = {
    "bitcoin": "BTC/USD", "ethereum": "ETH/USD", "solana": "SOL/USD", "dogecoin": "DOGE/USD",
    "litecoin": "LTC/USD", "avalanche-2": "AVAX/USD", "chainlink": "LINK/USD", "aave": "AAVE/USD",
}


def alpaca_krypto_symbol(coingecko_id: str) -> str | None:
    """Alpaca-Handelssymbol zu einer CoinGecko-ID, oder None wenn (bei Alpaca) nicht handelbar."""
    return ALPACA_KRYPTO.get((coingecko_id or "").lower())


class AlpacaPaperBroker:
    def __init__(self, key: str, secret: str, *, http=None, base: str = _BASE):
        self.key = key
        self.secret = secret
        self.base = base
        self.http = http or self._urllib

    @property
    def verfuegbar(self) -> bool:
        return bool(self.key and self.secret)

    def _urllib(self, method: str, pfad: str, body: dict | None = None) -> dict:
        daten = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"{self.base}{pfad}", data=daten, method=method,
            headers={"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            roh = r.read().decode("utf-8")
        return json.loads(roh) if roh else {}

    def konto(self) -> dict | None:
        """{cash, buying_power, equity, ...} oder None bei Fehler/ohne Keys."""
        if not self.verfuegbar:
            return None
        try:
            return self.http("GET", "/v2/account")
        except Exception:
            return None

    def positionen(self) -> list:
        if not self.verfuegbar:
            return []
        try:
            r = self.http("GET", "/v2/positions")
            return r if isinstance(r, list) else []
        except Exception:
            return []

    def order(self, symbol: str, qty: float, side: str, *, typ: str = "market",
              time_in_force: str = "day") -> dict | None:
        """Platziert eine Paper-Order. side: 'buy'|'sell'. Gibt die Order (dict) oder None zurueck."""
        if not self.verfuegbar:
            return None
        body = {"symbol": symbol.upper(), "qty": str(qty), "side": side, "type": typ,
                "time_in_force": time_in_force}
        try:
            return self.http("POST", "/v2/orders", body)
        except Exception:
            return None
