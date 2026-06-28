"""Investment-Datenspeicher (Phase 1) -- dateibasierter Stand-in fuer die Supabase inv_*-Tabellen.

Event-sourced JSONL (`investment/log.jsonl`), jeder Eintrag getaggt mit `tabelle`. Spaeter ersetzbar durch
Supabase (gleiches Schema). Leck-geschuetzt beim Schreiben. Store ist gitignored + vom NAS-Sync ausgeschlossen.

Modi: advisory (Default) / paper / live -- Wechsel ist ein CEO-Tor (hier nur gespeichert, nicht erzwungen;
die Durchsetzung erfolgt ueber die Governance/Tools). Keine Trades.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

TABELLEN = ("watchlist", "screening", "forecasts", "actuals", "scorecard", "suggestions", "mode", "positions")
MODI = ("advisory", "paper", "live")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class InvestmentStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    # -- generisch --
    def add(self, tabelle: str, daten: dict) -> str:
        if tabelle not in TABELLEN:
            raise ValueError(f"Unbekannte Tabelle: {tabelle}")
        rid = tabelle[:3].upper() + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": rid, "tabelle": tabelle, **daten})
        return rid

    def list(self, tabelle: str, limit: int = 500) -> list[dict]:
        return [e for e in self._events() if e.get("tabelle") == tabelle][-limit:]

    # -- mode (inv_mode) --
    def mode(self) -> str:
        ms = [e for e in self._events() if e.get("tabelle") == "mode"]
        return ms[-1].get("modus", "advisory") if ms else "advisory"

    def set_mode(self, modus: str, *, akteur: str = "CEO", grund: str = "") -> str:
        if modus not in MODI:
            raise ValueError(f"Unbekannter Modus: {modus}")
        return self.add("mode", {"modus": modus, "akteur": akteur, "grund": grund})

    # -- watchlist (inv_watchlist) --
    def watchlist_add(self, symbol: str, asset: str = "aktie") -> str:
        return self.add("watchlist", {"symbol": symbol.upper(), "asset": asset, "aktion": "add"})

    def watchlist_remove(self, symbol: str) -> str:
        return self.add("watchlist", {"symbol": symbol.upper(), "aktion": "remove"})

    def watchlist(self) -> list[dict]:
        """Gefalteter Stand: zuletzt hinzugefuegte, nicht wieder entfernte Symbole."""
        stand: dict[str, dict] = {}
        for e in self.list("watchlist"):
            sym = e.get("symbol")
            if not sym:
                continue
            if e.get("aktion") == "remove":
                stand.pop(sym, None)
            else:
                stand[sym] = {"symbol": sym, "asset": e.get("asset", "aktie")}
        return list(stand.values())

    # -- forecasts/actuals/scorecard --
    def forecast_add(self, symbol: str, *, prognose: str, konfidenz: float, horizont: str,
                     rationale: str = "") -> str:
        return self.add("forecasts", {"symbol": symbol.upper(), "prognose": prognose,
                                      "konfidenz": konfidenz, "horizont": horizont, "rationale": rationale,
                                      "status": "offen"})

    def actual_add(self, symbol: str, *, wert, bezug_forecast: str = "") -> str:
        return self.add("actuals", {"symbol": symbol.upper(), "wert": wert, "bezug_forecast": bezug_forecast})

    # -- suggestions (inv_suggestions / Alerts) --
    def suggestion_add(self, symbol: str, *, aktion: str, grund: str, quellen: list[str] | None = None,
                       konfidenz: float = 0.0, risiko_label: str = "spekulativ") -> str:
        return self.add("suggestions", {"symbol": symbol.upper(), "aktion": aktion, "grund": grund,
                                        "quellen": quellen or [], "konfidenz": konfidenz,
                                        "risiko_label": risiko_label, "status": "offen"})

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
