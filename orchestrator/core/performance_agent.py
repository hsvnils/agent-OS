"""Leistungs-Agent (CDO) -- beurteilt woechentlich die Leistungsfaehigkeit des Systems. Regelbasiert, kein LLM.

Verdichtet vorhandene Event-Stores zu einem Wochenbericht (letzte 7 Tage vs. Vorwoche):

  * **Ergebnis-Qualitaet** -- die CEO-Entscheidungen selbst sind das Signal: Freigabequote bei Reels und
    Antraegen (sinkende Quote = das System produziert am CEO vorbei).
  * **Zuverlaessigkeit** -- Erfolgs-/Fehlerquote der Pipelines (Reels, Cutter-Jobs).
  * **Durchsatz** -- Aktionen je Woche (Aktivitaets-Log), aktivste Akteure.
  * **Kosten** -- Token-/API-Kosten der Woche (KostenStore), Trend zur Vorwoche.

Ampel-Schwellen (bewusst transparent, hier dokumentiert):
  Freigabequote:   >= 70 % gruen | >= 40 % gelb | darunter rot   (nur wenn Entscheidungen vorlagen)
  Pipeline-Erfolg: >= 90 % gruen | >= 70 % gelb | darunter rot   (nur wenn Jobs liefen)
  Fehler gesamt:   0 gruen | <= 2 gelb | > 2 rot

Alle Stores sind optional -- fehlt einer, entfaellt der Bereich (keine geratenen Zahlen). Läuft im Bot
(woechentlicher Telegram-Bericht) und im Web (`/api/performance`, System-Tab „Leistung").
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

FENSTER_TAGE = 7


def _ts(v) -> datetime | None:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "").split("+")[0])
    except (ValueError, TypeError):
        return None


def _in_fenster(v, start: datetime, ende: datetime) -> bool:
    t = _ts(v)
    return t is not None and start <= t < ende


def _quote(gut: int, schlecht: int) -> float | None:
    n = gut + schlecht
    return round(gut / n, 3) if n else None


def _ampel_quote(q: float | None) -> str | None:
    if q is None:
        return None
    return "gruen" if q >= 0.7 else ("gelb" if q >= 0.4 else "rot")


def _ampel_erfolg(q: float | None) -> str | None:
    if q is None:
        return None
    return "gruen" if q >= 0.9 else ("gelb" if q >= 0.7 else "rot")


def _ampel_fehler(n: int) -> str:
    return "gruen" if n == 0 else ("gelb" if n <= 2 else "rot")


class PerformanceAgent:
    def __init__(self, *, reels=None, antraege=None, cutter=None, aktivitaet=None, kosten=None):
        self.reels = reels          # ReelStore (Events: einreichen / status)
        self.antraege = antraege    # Antraege  (Events: event=eingereicht/freigegeben/...)
        self.cutter = cutter        # ContentStore luna_cutter_jobs (rows mit status + updated_at)
        self.aktivitaet = aktivitaet
        self.kosten = kosten

    # -- Bereiche (je ein dict fuer EIN Zeitfenster) --

    def _reels(self, start: datetime, ende: datetime) -> dict | None:
        if self.reels is None:
            return None
        try:
            evs = [e for e in self.reels._events() if _in_fenster(e.get("ts"), start, ende)]
        except Exception:
            return None
        st = Counter(e.get("status") for e in evs if e.get("typ") == "status")
        erstellt = sum(1 for e in evs if e.get("typ") == "einreichen")
        frei, abgelehnt = st.get("freigegeben", 0), st.get("abgelehnt", 0)
        return {"erstellt": erstellt, "freigegeben": frei, "abgelehnt": abgelehnt,
                "gepostet": st.get("gepostet", 0), "fehler": st.get("fehler", 0),
                "freigabequote": _quote(frei, abgelehnt)}

    def _antraege(self, start: datetime, ende: datetime) -> dict | None:
        if self.antraege is None:
            return None
        try:
            evs = [e for e in self.antraege._events() if _in_fenster(e.get("ts"), start, ende)]
        except Exception:
            return None
        st = Counter(e.get("event") for e in evs)
        frei, abgelehnt = st.get("freigegeben", 0), st.get("abgelehnt", 0)
        return {"eingereicht": st.get("eingereicht", 0), "freigegeben": frei, "abgelehnt": abgelehnt,
                "erledigt": st.get("erledigt", 0), "freigabequote": _quote(frei, abgelehnt)}

    def _cutter(self, start: datetime, ende: datetime) -> dict | None:
        if self.cutter is None:
            return None
        try:
            rows = self.cutter.list(limit=300)
        except Exception:
            return None
        fenster = [r for r in rows if _in_fenster(r.get("updated_at") or r.get("created_at"), start, ende)]
        done = sum(1 for r in fenster if r.get("status") == "done")
        failed = sum(1 for r in fenster if r.get("status") == "failed")
        return {"jobs": len(fenster), "done": done, "failed": failed, "erfolgsquote": _quote(done, failed)}

    def _aktivitaet(self, start: datetime, ende: datetime) -> dict | None:
        if self.aktivitaet is None:
            return None
        try:
            evs = [e for e in self.aktivitaet.seit(start) if _in_fenster(e.get("ts"), start, ende)]
        except Exception:
            return None
        return {"aktionen": len(evs),
                "top_akteure": dict(Counter(e.get("akteur", "?") for e in evs).most_common(5))}

    def _kosten(self, start: datetime, ende: datetime) -> dict | None:
        if self.kosten is None:
            return None
        try:
            evs = [e for e in self.kosten._events() if _in_fenster(e.get("ts"), start, ende)]
        except Exception:
            return None
        return {"eur": round(sum(float(e.get("eur") or 0) for e in evs), 2), "aufrufe": len(evs)}

    # -- Bericht --

    def bericht(self, jetzt: datetime | None = None) -> dict:
        """Wochenbericht: aktuelle Woche + Vorwoche + Ampeln. Bereiche ohne Store fehlen (None)."""
        jetzt = jetzt or datetime.now()
        w_start = jetzt - timedelta(days=FENSTER_TAGE)
        v_start = jetzt - timedelta(days=2 * FENSTER_TAGE)
        woche = {"reels": self._reels(w_start, jetzt), "antraege": self._antraege(w_start, jetzt),
                 "cutter": self._cutter(w_start, jetzt), "aktivitaet": self._aktivitaet(w_start, jetzt),
                 "kosten": self._kosten(w_start, jetzt)}
        vorwoche = {"reels": self._reels(v_start, w_start), "antraege": self._antraege(v_start, w_start),
                    "cutter": self._cutter(v_start, w_start), "aktivitaet": self._aktivitaet(v_start, w_start),
                    "kosten": self._kosten(v_start, w_start)}
        fehler = ((woche["reels"] or {}).get("fehler", 0)) + ((woche["cutter"] or {}).get("failed", 0))
        ampeln = {
            "reel_qualitaet": _ampel_quote((woche["reels"] or {}).get("freigabequote")),
            "antrag_qualitaet": _ampel_quote((woche["antraege"] or {}).get("freigabequote")),
            "pipeline": _ampel_erfolg((woche["cutter"] or {}).get("erfolgsquote")),
            # Fehler-Ampel nur, wenn ueberhaupt Pipeline-Daten vorlagen -- sonst waere "0 Fehler = gruen"
            # bei komplett fehlenden Daten irrefuehrend.
            "fehler": _ampel_fehler(fehler) if (woche["reels"] is not None or woche["cutter"] is not None) else None,
        }
        belegt = [a for a in ampeln.values() if a]
        gesamt = ("rot" if "rot" in belegt else "gelb" if "gelb" in belegt else "gruen") if belegt else None
        return {"stand": jetzt.isoformat(timespec="seconds"), "fenster_tage": FENSTER_TAGE,
                "woche": woche, "vorwoche": vorwoche, "ampeln": ampeln, "gesamt": gesamt,
                "fehler_gesamt": fehler}

    def als_text(self, b: dict | None = None) -> str:
        """Kompakter Telegram-Text (Wochenbericht mit Ampeln + Trend zur Vorwoche)."""
        b = b or self.bericht()
        e = {"gruen": "\U0001f7e2", "gelb": "\U0001f7e1", "rot": "\U0001f534", None: "⚪"}
        w, v = b["woche"], b["vorwoche"]

        def pct(q):
            return f"{round(q * 100)} %" if q is not None else "keine Entscheidungen"

        def delta(w_wert, v_wert, einheit=""):
            if w_wert is None or v_wert is None:
                return ""
            d = w_wert - v_wert
            pfeil = "↗" if d > 0 else ("↘" if d < 0 else "→")
            return f" ({pfeil} Vorwoche {v_wert}{einheit})"

        z = [f"{e[b['gesamt']]} Leistungsbericht (letzte {b['fenster_tage']} Tage)"]
        if w["reels"]:
            r = w["reels"]
            z.append(f"{e[b['ampeln']['reel_qualitaet']]} Reels: {r['erstellt']} erstellt, Freigabequote "
                     f"{pct(r['freigabequote'])} ({r['freigegeben']} frei / {r['abgelehnt']} abgelehnt), "
                     f"{r['gepostet']} gepostet, {r['fehler']} Fehler"
                     + delta(r["erstellt"], (v["reels"] or {}).get("erstellt")))
        if w["antraege"]:
            a = w["antraege"]
            z.append(f"{e[b['ampeln']['antrag_qualitaet']]} Antraege: {a['eingereicht']} neu, Freigabequote "
                     f"{pct(a['freigabequote'])}, {a['erledigt']} erledigt"
                     + delta(a["eingereicht"], (v["antraege"] or {}).get("eingereicht")))
        if w["cutter"]:
            c = w["cutter"]
            q = f"{round(c['erfolgsquote'] * 100)} %" if c["erfolgsquote"] is not None else "keine Jobs"
            z.append(f"{e[b['ampeln']['pipeline']]} Cutter: {c['jobs']} Jobs, Erfolgsquote {q} "
                     f"({c['done']} ok / {c['failed']} Fehler)")
        if w["aktivitaet"]:
            ak = w["aktivitaet"]
            top = ", ".join(f"{k} ({n})" for k, n in list(ak["top_akteure"].items())[:3])
            z.append(f"⚙️ Durchsatz: {ak['aktionen']} Aktionen"
                     + delta(ak["aktionen"], (v["aktivitaet"] or {}).get("aktionen"))
                     + (f" — aktiv: {top}" if top else ""))
        if w["kosten"]:
            k = w["kosten"]
            z.append(f"\U0001f4b6 Kosten: {k['eur']:.2f} EUR ({k['aufrufe']} Aufrufe)"
                     + delta(k["eur"], (v["kosten"] or {}).get("eur"), " EUR"))
        z.append(f"{e[b['ampeln']['fehler']]} Fehler gesamt: {b['fehler_gesamt']}")
        return "\n".join(z)
