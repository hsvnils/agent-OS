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

TABELLEN = ("watchlist", "screening", "forecasts", "actuals", "scorecard", "suggestions", "mode",
            "positions", "insider_signals")
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

    def list(self, tabelle: str, limit: int = 1_000_000) -> list[dict]:
        # Default praktisch "alles" -- Auswertungen/Scorecard lesen die KOMPLETTE All-Time-Historie.
        return [e for e in self._events() if e.get("tabelle") == tabelle][-limit:]

    def historie(self) -> dict:
        """All-Time-Zaehlung je Tabelle (zur Sichtbarkeit/Verifikation, dass nichts verloren geht)."""
        evs = self._events()
        zaehl = {t: 0 for t in TABELLEN}
        for e in evs:
            t = e.get("tabelle")
            if t in zaehl:
                zaehl[t] += 1
        erster = evs[0].get("ts") if evs else None
        letzter = evs[-1].get("ts") if evs else None
        return {"eintraege_gesamt": len(evs), "je_tabelle": zaehl, "seit": erster, "bis": letzter,
                "datei": str(self.path)}

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
                     rationale: str = "", basis_preis=None, asset: str = "aktie") -> str:
        return self.add("forecasts", {"symbol": symbol.upper(), "prognose": prognose,
                                      "konfidenz": konfidenz, "horizont": horizont, "rationale": rationale,
                                      "basis_preis": basis_preis, "asset": asset, "status": "offen"})

    def actual_add(self, symbol: str, *, wert, bezug_forecast: str = "") -> str:
        return self.add("actuals", {"symbol": symbol.upper(), "wert": wert, "bezug_forecast": bezug_forecast})

    # -- suggestions (inv_suggestions / Alerts) --
    def suggestion_add(self, symbol: str, *, aktion: str, grund: str, quellen: list[str] | None = None,
                       konfidenz: float = 0.0, risiko_label: str = "spekulativ") -> str:
        return self.add("suggestions", {"symbol": symbol.upper(), "aktion": aktion, "grund": grund,
                                        "quellen": quellen or [], "konfidenz": konfidenz,
                                        "risiko_label": risiko_label, "status": "offen"})

    # -- insider_signals (Insider-/Smart-Money-Signale, SEC Form 4) --
    def insider_signal_add(self, symbol: str, *, insider: str, rolle: str = "", transaktion: str = "kauf",
                           betrag=None, anzahl=None, datum: str = "", quelle: str = "", filing_url: str = "",
                           bewertung: str = "", konfidenz: float = 0.0, cluster: int = 1,
                           risiko_label: str = "spekulativ") -> str:
        return self.add("insider_signals", {"symbol": symbol.upper(), "insider": insider, "rolle": rolle,
                                            "transaktion": transaktion, "betrag": betrag, "anzahl": anzahl,
                                            "datum": datum, "quelle": quelle, "filing_url": filing_url,
                                            "bewertung": bewertung, "konfidenz": konfidenz, "cluster": cluster,
                                            "risiko_label": risiko_label, "status": "offen"})

    def insider_signals(self, limit: int = 200) -> list[dict]:
        """Neueste Insider-Signale zuerst (fuer Anzeige/Alerts)."""
        return list(reversed(self.list("insider_signals")))[:limit]

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
