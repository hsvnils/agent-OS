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

import statistics
from collections import Counter
from datetime import datetime, timedelta

FENSTER_TAGE = 7
FRIEDHOF_TAGE = 28             # App laenger als 4 Wochen nicht geoeffnet -> "brachliegend"
# Kanonische App-Liste fuer den Feature-Friedhof (mit der NAV in app-v2.js synchron halten).
DEFAULT_APPS = ("dash", "freigaben", "devroadmap", "investment", "crm", "radar", "content",
                "cutter", "reel", "wissen", "agenten", "system", "team", "einstellungen")


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


def _median_stunden(paare: list[tuple[datetime, datetime]]) -> float | None:
    """Median-Dauer (Stunden) aus (start, ende)-Paaren; negative/kaputte Paare fallen raus."""
    dauern = [(e - s).total_seconds() / 3600 for s, e in paare if e >= s]
    return round(statistics.median(dauern), 2) if dauern else None


class PerformanceAgent:
    def __init__(self, *, reels=None, antraege=None, cutter=None, aktivitaet=None, kosten=None,
                 nutzung=None, apps: tuple = DEFAULT_APPS):
        self.reels = reels          # ReelStore (Events: einreichen / status)
        self.antraege = antraege    # Antraege  (Events: event=eingereicht/freigegeben/...)
        self.cutter = cutter        # ContentStore luna_cutter_jobs (rows mit status + updated_at)
        self.aktivitaet = aktivitaet
        self.kosten = kosten
        self.nutzung = nutzung      # NutzungStore (App-Oeffnungen; Feature-Friedhof)
        self.apps = tuple(apps)

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
        je_quelle: Counter = Counter()
        for e in evs:
            je_quelle[e.get("quelle", "?")] += float(e.get("eur") or 0)
        top = {q: round(v, 2) for q, v in je_quelle.most_common(3) if v > 0}
        return {"eur": round(sum(je_quelle.values()), 2), "aufrufe": len(evs), "top_quellen": top}

    def _reaktionszeiten(self, start: datetime, ende: datetime) -> dict | None:
        """Median-Dauern (Stunden) fuer im Fenster ABGESCHLOSSENE Vorgaenge:
        Cutter (angelegt -> done), Antraege (eingereicht -> erledigt), Reels (eingereicht -> CEO-Entscheidung)."""
        out: dict = {}
        if self.cutter is not None:
            try:
                paare = [(_ts(r.get("created_at")), _ts(r.get("updated_at")))
                         for r in self.cutter.list(limit=300)
                         if r.get("status") == "done" and _in_fenster(r.get("updated_at"), start, ende)]
                out["cutter_h"] = _median_stunden([(s, e) for s, e in paare if s and e])
            except Exception:
                pass
        if self.antraege is not None:
            try:
                erste: dict = {}
                paare = []
                for e in self.antraege._events():
                    aid, t = e.get("antrag_id"), _ts(e.get("ts"))
                    if not aid or t is None:
                        continue
                    if e.get("event") == "eingereicht":
                        erste.setdefault(aid, t)
                    elif e.get("event") == "erledigt" and aid in erste and _in_fenster(e.get("ts"), start, ende):
                        paare.append((erste[aid], t))
                out["antrag_h"] = _median_stunden(paare)
            except Exception:
                pass
        if self.reels is not None:
            try:
                eingereicht: dict = {}
                paare = []
                entschieden: set = set()
                for e in self.reels._events():
                    rid, t = e.get("id"), _ts(e.get("ts"))
                    if not rid or t is None:
                        continue
                    if e.get("typ") == "einreichen":
                        eingereicht.setdefault(rid, t)
                    elif (e.get("typ") == "status" and e.get("status") in ("freigegeben", "abgelehnt")
                          and rid in eingereicht and rid not in entschieden):
                        entschieden.add(rid)                     # nur die ERSTE Entscheidung zaehlt
                        if _in_fenster(e.get("ts"), start, ende):
                            paare.append((eingereicht[rid], t))
                out["reel_entscheidung_h"] = _median_stunden(paare)
            except Exception:
                pass
        return out if any(v is not None for v in out.values()) else (out or None)

    def _nutzung(self, start: datetime, ende: datetime) -> dict | None:
        if self.nutzung is None:
            return None
        try:
            evs = [e for e in self.nutzung._events() if _in_fenster(e.get("ts"), start, ende)]
        except Exception:
            return None
        return {"oeffnungen": len(evs),
                "je_app": dict(Counter(e.get("app", "?") for e in evs).most_common())}

    def _friedhof(self, jetzt: datetime) -> list | None:
        """Apps der kanonischen Liste, die seit FRIEDHOF_TAGE nicht geoeffnet wurden. None ohne Nutzungsdaten
        (erste Tage nach Einfuehrung des Loggings waere sonst ALLES faelschlich 'brachliegend')."""
        if self.nutzung is None:
            return None
        try:
            evs = self.nutzung._events()
        except Exception:
            return None
        if not evs:
            return None
        grenze = jetzt - timedelta(days=FRIEDHOF_TAGE)
        aeltestes = min((t for t in (_ts(e.get("ts")) for e in evs) if t), default=None)
        if aeltestes is None or aeltestes > grenze:
            return None            # Logging ist juenger als FRIEDHOF_TAGE -> noch keine faire Aussage
        aktiv = {e.get("app") for e in evs if (_ts(e.get("ts")) or grenze) > grenze}
        return sorted(a for a in self.apps if a not in aktiv)

    # -- Bericht --

    def _fenster_bereiche(self, start: datetime, ende: datetime) -> dict:
        return {"reels": self._reels(start, ende), "antraege": self._antraege(start, ende),
                "cutter": self._cutter(start, ende), "aktivitaet": self._aktivitaet(start, ende),
                "kosten": self._kosten(start, ende),
                "reaktionszeiten": self._reaktionszeiten(start, ende),
                "nutzung": self._nutzung(start, ende)}

    def historie(self, wochen: int = 8, jetzt: datetime | None = None) -> list[dict]:
        """Kennzahlen der letzten `wochen` Wochenfenster (aelteste zuerst) -- fuer den Verlaufs-Chart.
        Rein rueckwirkend aus den Event-Zeitstempeln berechnet, keine Persistenz noetig."""
        jetzt = jetzt or datetime.now()
        out: list[dict] = []
        for i in range(wochen, 0, -1):
            start = jetzt - timedelta(days=i * FENSTER_TAGE)
            ende = jetzt - timedelta(days=(i - 1) * FENSTER_TAGE)
            b = self._fenster_bereiche(start, ende)
            out.append({
                "label": f"KW{ende.isocalendar()[1]:02d}", "start": start.date().isoformat(),
                "freigabequote": (b["reels"] or {}).get("freigabequote"),
                "reels_erstellt": (b["reels"] or {}).get("erstellt", 0),
                "fehler": ((b["reels"] or {}).get("fehler", 0)) + ((b["cutter"] or {}).get("failed", 0)),
                "aktionen": (b["aktivitaet"] or {}).get("aktionen", 0),
                "kosten_eur": (b["kosten"] or {}).get("eur", 0.0),
            })
        return out

    def bericht(self, jetzt: datetime | None = None) -> dict:
        """Wochenbericht: aktuelle Woche + Vorwoche + Ampeln. Bereiche ohne Store fehlen (None)."""
        jetzt = jetzt or datetime.now()
        w_start = jetzt - timedelta(days=FENSTER_TAGE)
        v_start = jetzt - timedelta(days=2 * FENSTER_TAGE)
        woche = self._fenster_bereiche(w_start, jetzt)
        vorwoche = self._fenster_bereiche(v_start, w_start)
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
                "fehler_gesamt": fehler, "friedhof": self._friedhof(jetzt),
                "friedhof_tage": FRIEDHOF_TAGE}

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
            treiber = ", ".join(f"{q} {v_:.2f}" for q, v_ in (k.get("top_quellen") or {}).items())
            z.append(f"\U0001f4b6 Kosten: {k['eur']:.2f} EUR ({k['aufrufe']} Aufrufe)"
                     + delta(k["eur"], (v["kosten"] or {}).get("eur"), " EUR")
                     + (f" — Treiber: {treiber}" if treiber else ""))
        rz = w.get("reaktionszeiten") or {}
        rz_teile = [t for t in (
            f"Cutter {rz['cutter_h']:.1f} h" if rz.get("cutter_h") is not None else None,
            f"Antraege {rz['antrag_h']:.1f} h" if rz.get("antrag_h") is not None else None,
            f"Reel-Entscheidung {rz['reel_entscheidung_h']:.1f} h" if rz.get("reel_entscheidung_h") is not None else None,
        ) if t]
        if rz_teile:
            z.append("⏱ Reaktionszeiten (Median): " + " · ".join(rz_teile))
        nz = w.get("nutzung")
        if nz:
            top = ", ".join(f"{a} ({n})" for a, n in list(nz["je_app"].items())[:3])
            z.append(f"\U0001f4f1 Nutzung: {nz['oeffnungen']} App-Oeffnungen" + (f" — meist: {top}" if top else ""))
        if b.get("friedhof"):
            z.append(f"\U0001faa6 Brachliegend (> {b['friedhof_tage']} Tage nicht geoeffnet): "
                     + ", ".join(b["friedhof"]))
        z.append(f"{e[b['ampeln']['fehler']]} Fehler gesamt: {b['fehler_gesamt']}")
        return "\n".join(z)
