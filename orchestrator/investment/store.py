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
            "positions", "insider_signals", "real_depot", "settings")
MODI = ("advisory", "paper", "live")

# In der Weboberflaeche einstellbare Werte (geteilte SSOT: Web + Telegram-Bot lesen `settings()`).
SETTINGS_DEFAULTS = {
    # A -- echtes Depot (Beratung)
    "depot_stop_pct": 8.0,          # Stop-Loss-Hinweis ab -x %
    "depot_target_pct": 15.0,       # Take-Profit-Hinweis ab +x %
    "depot_alerts": True,           # Advisory-Push-Alerts (Telegram) an/aus
    # B -- Paper-Depot (Spielgeld-Auto-Trading)
    "paper_stop_pct": 8.0,          # Auto-Stop-Loss (verkauft) ab -x %
    "paper_target_pct": 15.0,       # Take-Profit-Vorschlag ab +x %
    "paper_order_betrag_usd": 30.0, # Standard-Order-Betrag fuer 1-Tap-Kaeufe
    "paper_dip_schwelle_pct": 4.0,  # Empfindlichkeit Live-Dip-Monitor
    # C -- Benachrichtigungen / Briefings
    "briefing_morgen_stunde": 8,    # Morgen-Briefing (Stunde 0-23)
    "briefing_abend_stunde": 20,    # Abend-Briefing (Stunde 0-23)
    "ruhezeit_von": None,           # "Nicht stoeren" von Stunde (None = aus)
    "ruhezeit_bis": None,           # "Nicht stoeren" bis Stunde (None = aus)
    "alert_investment": True,       # Alert-Arten (Push-Kategorien) an/aus
    "alert_crm": True,
    "alert_security": True,
    "alert_content": True,
}


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

    # -- real_depot: manuelles Transaktions-Ledger des ECHTEN Depots (getrennt vom Paper-Konto) --
    # Jede Buchung (Kauf/Verkauf) ist ein Event; Bestand + Ø-Einstand + realisierte G/V werden gefaltet.
    # Bewusst als Ledger (nicht statischer Bestand), damit eine spaetere echte Broker-Anbindung dasselbe
    # Schema nutzen kann. Legacy-Events (aktion add/remove aus der ersten Version) bleiben kompatibel.
    def real_trade(self, symbol: str, *, side: str = "kauf", klasse: str = "aktie", stueck: float = 0.0,
                   preis: float = 0.0, gebuehr: float = 0.0, kurs_id: str = "", waehrung: str = "USD",
                   datum: str = "") -> str:
        """Bucht einen Kauf ('kauf') oder Verkauf ('verkauf'). kurs_id = CoinGecko-Id bei Krypto, sonst Ticker."""
        side = "verkauf" if str(side).lower().startswith("verk") else "kauf"
        return self.add("real_depot", {"symbol": symbol.upper(), "klasse": klasse, "side": side,
                                       "stueck": float(stueck), "preis": float(preis), "gebuehr": float(gebuehr),
                                       "waehrung": waehrung.upper(), "kurs_id": (kurs_id or symbol).strip(),
                                       "datum": datum, "aktion": "trade"})

    def real_storno(self, ref_id: str) -> str:
        """Storniert eine einzelne Buchung (macht sie rueckgaengig)."""
        return self.add("real_depot", {"ref": ref_id, "aktion": "storno"})

    def real_trades(self) -> list[dict]:
        """Aktive (nicht stornierte) Buchungen, chronologisch. Legacy 'add' -> Kauf, 'remove' -> Storno."""
        events = self.list("real_depot")
        storniert = {e.get("ref") for e in events if e.get("aktion") in ("storno", "remove")}
        trades: list[dict] = []
        for e in events:
            if e.get("aktion") in ("storno", "remove") or e.get("id") in storniert:
                continue
            if e.get("aktion") == "add":         # Legacy-Bestand -> als Kauf interpretieren
                trades.append({"id": e.get("id"), "symbol": e.get("symbol"), "klasse": e.get("klasse", "aktie"),
                               "side": "kauf", "stueck": float(e.get("stueck") or 0), "preis": float(e.get("einstand_preis") or 0),
                               "gebuehr": 0.0, "waehrung": e.get("waehrung", "USD"), "kurs_id": e.get("kurs_id", ""),
                               "datum": e.get("datum", ""), "ts": e.get("ts")})
            elif e.get("aktion") == "trade":
                trades.append({"id": e.get("id"), "symbol": e.get("symbol"), "klasse": e.get("klasse", "aktie"),
                               "side": e.get("side", "kauf"), "stueck": float(e.get("stueck") or 0),
                               "preis": float(e.get("preis") or 0), "gebuehr": float(e.get("gebuehr") or 0),
                               "waehrung": e.get("waehrung", "USD"), "kurs_id": e.get("kurs_id", ""),
                               "datum": e.get("datum", ""), "ts": e.get("ts")})
        return trades

    def real_positionen(self) -> dict:
        """Faltet die Buchungen zu Netto-Positionen (Ø-Einstand, Bestand) und realisierter G/V (Durchschnittskosten).
        Rueckgabe: {"positionen": [...], "realisiert": float}. Nur Positionen mit Bestand > 0 werden gelistet."""
        proto: dict[str, dict] = {}
        for t in self.real_trades():                      # chronologisch (list() erhaelt Reihenfolge)
            sym = t["symbol"]
            p = proto.setdefault(sym, {"symbol": sym, "klasse": t["klasse"], "kurs_id": t["kurs_id"] or sym,
                                       "waehrung": t["waehrung"], "qty": 0.0, "cost": 0.0, "realisiert": 0.0})
            p["klasse"] = t["klasse"]; p["kurs_id"] = t["kurs_id"] or p["kurs_id"]; p["waehrung"] = t["waehrung"]
            if t["side"] == "verkauf":
                avg = (p["cost"] / p["qty"]) if p["qty"] > 1e-12 else 0.0
                verk = min(t["stueck"], p["qty"]) if p["qty"] > 1e-12 else t["stueck"]
                p["realisiert"] += verk * t["preis"] - verk * avg - t["gebuehr"]
                p["cost"] -= verk * avg
                p["qty"] -= verk
            else:                                          # kauf
                p["qty"] += t["stueck"]
                p["cost"] += t["stueck"] * t["preis"] + t["gebuehr"]
        positionen, realisiert_ges = [], 0.0
        for p in proto.values():
            realisiert_ges += p["realisiert"]
            if p["qty"] > 1e-9:
                positionen.append({"symbol": p["symbol"], "klasse": p["klasse"], "kurs_id": p["kurs_id"],
                                   "waehrung": p["waehrung"], "stueck": round(p["qty"], 10),
                                   "einstand_preis": (p["cost"] / p["qty"]) if p["qty"] else 0.0})
        return {"positionen": positionen, "realisiert": round(realisiert_ges, 6)}

    # -- settings (in der Weboberflaeche einstellbar; geteilte SSOT fuer Web + Bot) --
    def settings(self) -> dict:
        """Gefalteter Einstellungsstand = Defaults, ueberlagert von gespeicherten Aenderungen (letzte gewinnt)."""
        stand = dict(SETTINGS_DEFAULTS)
        for e in self.list("settings"):
            k = e.get("key")
            if k in SETTINGS_DEFAULTS:
                stand[k] = e.get("wert")
        return stand

    def set_setting(self, key: str, wert, *, akteur: str = "CEO") -> str:
        if key not in SETTINGS_DEFAULTS:
            raise ValueError(f"Unbekannte Einstellung: {key}")
        return self.add("settings", {"key": key, "wert": wert, "akteur": akteur})

    def set_settings(self, werte: dict, *, akteur: str = "CEO") -> list[str]:
        return [self.set_setting(k, v, akteur=akteur) for k, v in werte.items() if k in SETTINGS_DEFAULTS]

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
