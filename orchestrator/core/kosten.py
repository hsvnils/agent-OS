"""CFO Stufe 2 -- echte Token-/Kostenerfassung (CDO-Rohdaten -> CFO-Statistik).

Jeder echte Modell-Aufruf (Chat, Web-Synthese) meldet seine Token-Nutzung hier; daraus entsteht eine
fortlaufende Kostenstatistik je Monat/Quelle/Modell (Richtwerte, EUR-geschaetzt). Append-only JSONL
(`finance/kosten-log.jsonl`), leck-geschuetzt. Grundlage fuer Budget-Warnung und die Anthropic/OpenAI-
Lastverteilung (naechster Schritt).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

# Richtwerte USD je 1 Mio. Token (Input, Output) -- ueberschreibbar; nur fuer Schaetzung/Trend.
RATES_USD: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
}
USD_TO_EUR = 0.92


def _rate(modell: str) -> tuple[float, float]:
    return RATES_USD.get(modell, (1.0, 5.0))


def schaetze_eur(modell: str, input_tokens: int, output_tokens: int) -> float:
    rin, rout = _rate(modell)
    usd = input_tokens / 1_000_000 * rin + output_tokens / 1_000_000 * rout
    return round(usd * USD_TO_EUR, 4)


class KostenStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def record(self, *, quelle: str, modell: str, input_tokens: int, output_tokens: int) -> dict:
        eur = schaetze_eur(modell, input_tokens, output_tokens)
        ev = {"ts": datetime.now().isoformat(timespec="seconds"), "quelle": quelle, "modell": modell,
              "provider": _provider(modell), "in": int(input_tokens), "out": int(output_tokens),
              "eur": eur}
        self._append(ev)
        return ev

    def monat(self, ym: str | None = None) -> dict:
        ym = ym or datetime.now().strftime("%Y-%m")
        je_quelle: dict[str, dict] = {}
        je_provider: dict[str, float] = {}
        gesamt = 0.0
        for e in self._events():
            if not str(e.get("ts", "")).startswith(ym):
                continue
            q = e.get("quelle", "?")
            d = je_quelle.setdefault(q, {"in": 0, "out": 0, "eur": 0.0, "aufrufe": 0})
            d["in"] += e.get("in", 0); d["out"] += e.get("out", 0)
            d["eur"] = round(d["eur"] + e.get("eur", 0.0), 4); d["aufrufe"] += 1
            je_provider[e.get("provider", "?")] = round(
                je_provider.get(e.get("provider", "?"), 0.0) + e.get("eur", 0.0), 4)
            gesamt += e.get("eur", 0.0)
        return {"monat": ym, "gesamt_eur": round(gesamt, 2), "je_quelle": je_quelle,
                "je_provider": je_provider}

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


def _provider(modell: str) -> str:
    m = (modell or "").lower()
    if m.startswith("gpt") or "openai" in m:
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    return "?"
