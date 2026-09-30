"""Handlungsbedarf ueber das ganze LUNA-System (LUNA_OS_UI_ROADMAP Etappe 3, CEO 2026-09-30: „eine Kachel, die alle
dringenden Handlungen ueber das gesamte LUNA-System anzeigt, die ich durchfuehren muss“).

Sammelt die bestehenden Tages-To-dos (`/api/todos`: Rechnungen, Angebote, Belege, Abos, Zeiten, Firmenakte, CRM,
Reels) und ergaenzt: offene Antraege (Freigaben), offene Investment-Entscheidungen der letzten 2 Tage (aeltere
Kauf-Chancen sind ueberholt und bleiben unangetastet im Speicher) und
Betriebsstoerungen (Bot-Herzschlag, haengende Telegram-Meldungen, gleiche Schwellen wie der Waechter). Jeder Punkt
bekommt eine **Stufe** -- dringend (ueberfaellig/heute oder Stoerung), diese Woche (faellig in 7 Tagen oder wartet
auf dich), wenn Zeit ist -- und den Bereich der neuen Navigation fuer Filter und Sprung. Reine Lesefunktion: Erledigt
wird in der Fachseite; der Punkt verschwindet, sobald die Quelle ihn nicht mehr meldet.

Nicht enthalten: das naechtliche Backup (Status nur auf dem MACO470, meldet der Waechter per Telegram) und
Sicherheits-Befunde (landen als Antrag und damit unter „Freigaben“).
"""
from __future__ import annotations

from datetime import date, timedelta

from .betriebswaechter import BOT_STUMM_MIN, ZUSTELLUNG_MIN

STUFEN = ("dringend", "woche", "spaeter")
INVESTMENT_MAX_TAGE = 2      # Kauf-/Verkaufs-Chancen veralten schnell; aeltere offene Telegram-Anfragen sind ueberholt
# To-do-Bereich (core/todos.py, /api/todos) -> Bereich der Navigation
_BEREICH = {"CRM": "content", "Content": "content", "Investment": "investment", "Freigaben": "luna", "Betrieb": "luna"}


def _stufe(p: dict, woche_bis: str) -> str:
    if p.get("dringend"):
        return "dringend"
    if p.get("stufe") in STUFEN:
        return p["stufe"]
    return "woche" if p.get("faellig") and p["faellig"] <= woche_bis else "spaeter"


def zusammenstellen(todos: list[dict], *, antraege: list[dict] | None = None, investment: list[dict] | None = None,
                    betrieb: dict | None = None, heute: date) -> dict:
    punkte = [dict(t) for t in todos]
    if antraege:
        aeltester = min((a.get("verlauf") or [{}])[0].get("ts", "") for a in antraege)[:10]
        punkte.append({"id": "freigaben", "bereich": "Freigaben", "icon": "✔",
                       "titel": f"{len(antraege)} Antrag/Anträge warten auf deine Freigabe" if len(antraege) > 1
                       else "1 Antrag wartet auf deine Freigabe",
                       "detail": "; ".join(a.get("titel", "")[:50] for a in antraege[:3]) + (" …" if len(antraege) > 3 else ""),
                       "act": "go:freigaben", "act_id": "", "faellig": "", "dringend": False, "stufe": "woche", "anzahl": len(antraege),
                       "seit": aeltester, "erledigen": None})
    if investment:                                 # nur frische Anfragen (Datum steckt in der ID: APV-JJJJMMTT-...)
        grenze = (heute - timedelta(days=INVESTMENT_MAX_TAGE)).strftime("%Y%m%d")
        investment = [a for a in investment if (a.get("id") or "")[4:12] >= grenze
                      or str(a.get("erstellt") or "")[:10].replace("-", "") >= grenze]
    if investment:
        punkte.append({"id": "investment-freigaben", "bereich": "Investment", "icon": "📈",
                       "titel": f"{len(investment)} Investment-Entscheidung(en) offen",
                       "detail": (investment[0].get("frage") or "")[:90] + (" …" if len(investment) > 1 else ""),
                       "act": "go:investment", "act_id": "", "faellig": heute.isoformat(), "dringend": True,
                       "erledigen": None})
    if betrieb:
        bot = betrieb.get("bot_alter_min")
        if bot is not None and bot > BOT_STUMM_MIN:
            punkte.append({"id": "betrieb-bot", "bereich": "Betrieb", "icon": "📡",
                           "titel": f"Telegram-Bot meldet sich seit {int(bot)} Minuten nicht",
                           "detail": "Container luna-telegram prüfen oder neu starten", "act": "go:system", "act_id": "",
                           "faellig": heute.isoformat(), "dringend": True, "erledigen": None})
        alt = betrieb.get("aelteste_unzugestellt_min")
        if betrieb.get("unzugestellt") and alt is not None and alt > ZUSTELLUNG_MIN:
            punkte.append({"id": "betrieb-zustellung", "bereich": "Betrieb", "icon": "📨",
                           "titel": f"{betrieb['unzugestellt']} Telegram-Meldung(en) hängen seit {int(alt)} Minuten",
                           "detail": "Zustellung an dich klemmt", "act": "go:system", "act_id": "",
                           "faellig": heute.isoformat(), "dringend": True, "erledigen": None})
    woche_bis = (heute + timedelta(days=7)).isoformat()
    for p in punkte:
        p["stufe"] = _stufe(p, woche_bis)
        p["bereich_id"] = _BEREICH.get(p.get("bereich", ""), "geschaeft")
    rang = {s: i for i, s in enumerate(STUFEN)}
    punkte.sort(key=lambda p: (rang[p["stufe"]], p.get("faellig") or "9999", p.get("titel", "")))
    zaehler = {s: sum(1 for p in punkte if p["stufe"] == s) for s in STUFEN} | {"gesamt": len(punkte)}
    bereiche: dict[str, int] = {}
    for p in punkte:
        bereiche[p["bereich_id"]] = bereiche.get(p["bereich_id"], 0) + 1
    return {"punkte": punkte, "zaehler": zaehler, "bereiche": bereiche}
