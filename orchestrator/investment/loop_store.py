"""Speicher fuer den Investment-Walk-Forward-Lern-Loop (CEO-gewuenscht 2026-07-03).

Fuehrt die Loop-Tabellen (`inv_features`, `inv_forecasts`, `inv_actuals`, `inv_deviations`, `inv_model_runs`).
**Lokaler append-only JSONL = Quelle + Offline-Fallback**; **Supabase = durable/abfragbare Zweitschrift**
(write-through, best-effort). So laeuft der Loop auch ohne Netz/Keys weiter und Supabase kann nie den lokalen
Stand ueberschreiben. Schema: `docs/hcc_inv_loop.sql`. Leck-geschuetzt beim lokalen Schreiben. Keine Trades.

Das **Abweichungs-Register** (`inv_deviations`) ist bewusst getrennt und wird **nie ueberschrieben** -- es ist
der Beweis, ob Daten-/Wissens-Anreicherung die Prognosen ueber Zeit genauer macht.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

TABELLEN = ("inv_features", "inv_forecasts", "inv_actuals", "inv_deviations", "inv_model_runs")

# Upsert-Schluessel je Tabelle (fuer Supabase; lokal bleibt alles append-only).
_ON_CONFLICT = {"inv_features": "symbol,datum"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class LoopStore:
    def __init__(self, path: str | Path, *, supabase=None, secrets: list[str] | None = None):
        self.path = Path(path)
        self.sb = supabase          # governance.supabase.SupabaseClient oder None
        self.secrets = secrets or []

    # -- generisch --
    def add(self, tabelle: str, row: dict) -> dict:
        if tabelle not in TABELLEN:
            raise ValueError(f"Unbekannte Tabelle: {tabelle}")
        self._append({"ts": _now(), "tabelle": tabelle, **row})
        if self.sb is not None:
            try:
                if self.sb.verfuegbar():
                    self.sb.upsert(tabelle, row, on_conflict=_ON_CONFLICT.get(tabelle))
            except Exception:
                pass  # Supabase-Ausfall darf den lokalen Loop nie stoppen
        return row

    def list(self, tabelle: str) -> list[dict]:
        return [e for e in self._events() if e.get("tabelle") == tabelle]

    def last_datum(self, tabelle: str) -> str:
        items = self.list(tabelle)
        return items[-1].get("datum", items[-1].get("ts", "")[:10]) if items else ""

    # -- inv_features --
    def feature_add(self, symbol: str, asset: str, datum: str, close, change_pct, features: dict, *,
                    baseline: bool = False, quelle: str = "") -> dict:
        return self.add("inv_features", {"symbol": symbol.upper(), "asset": asset, "datum": datum,
                                         "close": close, "change_pct": change_pct, "features": features,
                                         "baseline": baseline, "quelle": quelle})

    def has_feature(self, symbol: str, datum: str) -> bool:
        sym = symbol.upper()
        return any(e.get("symbol") == sym and e.get("datum") == datum for e in self.list("inv_features"))

    def features_for(self, symbol: str) -> list[dict]:
        """Chronologische Kurs-Historie eines Werts: [{datum, close}] aufsteigend nach Datum."""
        sym = symbol.upper()
        rows = [{"datum": e.get("datum"), "close": _num(e.get("close"))}
                for e in self.list("inv_features") if e.get("symbol") == sym and _num(e.get("close")) > 0]
        return sorted(rows, key=lambda r: r.get("datum") or "")

    # -- inv_forecasts / inv_actuals / inv_deviations / inv_model_runs (Schritt 2 nutzt diese) --
    def forecast_add(self, row: dict) -> dict:
        return self.add("inv_forecasts", row)

    def actual_add(self, row: dict) -> dict:
        return self.add("inv_actuals", row)

    def deviation_add(self, row: dict) -> dict:
        """Eintrag ins SEPARATE, dauerhafte Abweichungs-Register (nie ueberschreiben)."""
        return self.add("inv_deviations", row)

    def model_run_add(self, row: dict) -> dict:
        return self.add("inv_model_runs", row)

    # -- intern --
    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
