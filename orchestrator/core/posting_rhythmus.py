"""Posting-Rhythmus Soll/Ist je Plattform und Woche (MONETARISIERUNG_ROADMAP.md, Etappe M4).

- **Soll** je Plattform und Format als Spanne (mindestens/hoechstens) je Woche. Startwerte aus dem Skill
  `skills/cmo/kanal-wachstum/SKILL.md` („Frequenz als Startwert"), in LUNA-OS anpassbar. Eine Aenderung gilt ab der
  laufenden Woche; fruehere Wochen werden weiter am damaligen Soll gemessen (Ereignis `soll` im Reichweiten-Log).
- **Ist** je Woche:
  - Instagram automatisch: Beitraege und Reels aus der Medienliste des eigenen Kontos (vorhandener Zugang, gleiche
    Schnittstelle wie M3), Zeitpunkte in Europe/Berlin gezaehlt; der Tageslauf 05:00 aktualisiert die Zaehlung.
  - Facebook: eingetragener Wert, sonst die von LUNA geposteten Reels der Reel-Pipeline (dann nur „mindestens").
  - TikTok/YouTube: von Hand oder aus dem CSV-Import (Metriken `beitraege`, `beitraege_kurz`, `beitraege_lang`).
- **Briefing:** dienstags die Formate der Vorwoche unter Soll; mittwochs bis samstags automatisch gezaehlte Formate, die
  hinter dem Wochen-Tempo liegen. Keine Zahl wird geraten: unbekanntes Ist bleibt „unbekannt".
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .reichweite import PLATTFORMEN, montag

TZ = ZoneInfo("Europe/Berlin")
WOCHEN = 8

# plattform -> [(format, Anzeige, Soll min, Soll max (None = offen), Metrik im Reichweiten-Log, Tipp)]
FORMATE = {
    "instagram": [("beitraege", "Beiträge (Feed und Reels)", 3, 5, "beitraege", ""),
                  ("reels", "davon Reels", 2, 5, "beitraege_kurz", "")],
    "facebook": [("beitraege", "Reels und Beiträge", 3, 5, "beitraege", "Reels und Beiträge aus Instagram wiederverwerten.")],
    "tiktok": [("videos", "Videos", 3, 5, "beitraege", ""),
               ("lang", "davon über 1 Minute", 1, None, "beitraege_lang",
                "Für die Creator Rewards zählen nur Videos über 1 Minute.")],
    "youtube": [("shorts", "Shorts", 2, 4, "beitraege_kurz", ""),
                ("lang", "Langvideos", 1, None, "beitraege_lang", "Ein Langvideo je Woche oder je Spieltag.")],
}


def _formate(plattform: str) -> dict[str, tuple]:
    return {f[0]: f for f in FORMATE.get(plattform, [])}


def _lokal_datum(ts: str) -> date | None:
    """Zeitstempel (Meta: `2026-11-15T23:30:00+0000`, Pipeline: lokal ohne Zone) -> Datum in Europe/Berlin."""
    if not ts:
        return None
    s = str(ts).strip().replace("Z", "+00:00")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":          # +0000 -> +00:00
        s = s[:-2] + ":" + s[-2:]
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return (d.astimezone(TZ) if d.tzinfo else d).date()


def instagram_zaehlen(posts: list[dict], *, voll: bool = False) -> dict[str, dict[str, int]]:
    """Medienliste (`timestamp`, `media_product_type`) -> {woche: {beitraege, beitraege_kurz}}.

    Gezaehlt werden nur Wochen, die die Liste vollstaendig abdeckt: aelter als der aelteste Beitrag reicht die Liste
    nicht zurueck, dessen Woche bleibt aussen vor -- ausser die Liste ist die ganze Historie (`voll`)."""
    tage = [(d, str(p.get("media_product_type") or "").upper()) for p in posts or []
            if (d := _lokal_datum(p.get("timestamp") or p.get("ts") or ""))]
    if not tage:
        return {}
    grenze = "" if voll else montag(min(d for d, _ in tage))
    out: dict[str, dict[str, int]] = {}
    for d, typ in tage:
        w = montag(d)
        if w <= grenze:
            continue
        x = out.setdefault(w, {"beitraege": 0, "beitraege_kurz": 0})
        x["beitraege"] += 1
        x["beitraege_kurz"] += typ == "REELS"
    return out


def instagram_beitraege(store, posts: list[dict] | None, heute: date | None = None, *, voll: bool = False,
                        von: str = "LUNA") -> list[str]:
    """Gezaehlte Instagram-Beitraege ins Reichweiten-Log schreiben (nur Wochen mit geaendertem Wert). -> Wochen."""
    if posts is None:
        return []
    heute = heute or date.today()
    bisher = store.wochen()["instagram"]
    geschrieben = []
    for w, werte in sorted(instagram_zaehlen(posts, voll=voll).items()):
        if w > montag(heute):
            continue
        alt = bisher.get(w, {}).get("werte", {})
        if all(alt.get(k) == v for k, v in werte.items()):
            continue
        store.erfassen("instagram", w, werte, quelle="api", notiz="automatisch gezählt (Medienliste)", von=von)
        geschrieben.append(w)
    return geschrieben


def instagram_abrufen(store, insights, heute: date | None = None, *, limit: int = 50, von: str = "LUNA") -> list[str] | None:
    """Medienliste holen (core/social_kit.MetaInsights.beitraege) und zaehlen. None = Abruf fehlgeschlagen."""
    posts = insights.beitraege(limit)
    if posts is None:
        return None
    return instagram_beitraege(store, posts, heute, voll=len(posts) < limit, von=von)


def pipeline_facebook(reels) -> dict[str, int]:
    """Von LUNA auf Facebook gepostete Reels je Woche (Status `gepostet` mit Video-ID)."""
    out: dict[str, int] = {}
    if reels is None:
        return out
    for r in reels.liste(status="gepostet", limit=100000):
        d = _lokal_datum(r.get("entschieden") or r.get("ts") or "")
        if d and r.get("fb_video_id"):
            w = montag(d)
            out[w] = out.get(w, 0) + 1
    return out


def _soll_ereignisse(store) -> list[dict]:
    return [e for e in store._ereignisse() if e.get("typ") == "soll"]


def soll_fuer(ereignisse: list[dict], plattform: str, fmt: str, woche: str) -> tuple[int, int | None]:
    f = _formate(plattform)[fmt]
    mn, mx = f[2], f[3]
    for e in ereignisse:                                     # chronologisch; letzte gueltige Aenderung gilt
        if e.get("plattform") == plattform and e.get("format") == fmt and e.get("ab", "") <= woche:
            mn, mx = e["min"], e.get("max")
    return mn, mx


def soll_setzen(store, plattform: str, fmt: str, mn, mx=None, heute: date | None = None, *, von: str = "") -> dict:
    if plattform not in PLATTFORMEN or fmt not in _formate(plattform):
        raise ValueError("Unbekannte Plattform oder unbekanntes Format.")

    def zahl(x, name):
        try:
            z = int(str(x).strip())
        except (TypeError, ValueError):
            raise ValueError(f"{name}: bitte eine ganze Zahl.") from None
        if not 0 <= z <= 50:
            raise ValueError(f"{name}: bitte zwischen 0 und 50.")
        return z
    mn = zahl(mn, "Mindestens")
    mx = None if mx in (None, "") else zahl(mx, "Höchstens")
    if mx is not None and mx < mn:
        raise ValueError("Höchstens darf nicht kleiner als mindestens sein.")
    e = {"typ": "soll", "plattform": plattform, "format": fmt, "min": mn, "max": mx,
         "ab": montag(heute or date.today()), "von": von}
    store._schreibe(e)
    return {k: e[k] for k in ("plattform", "format", "min", "max", "ab")}


def auswertung(store, reels=None, heute: date | None = None, wochen: int = WOCHEN) -> dict:
    heute = heute or date.today()
    aktuell = montag(heute)
    liste = [montag(heute - timedelta(days=7 * i)) for i in range(wochen - 1, -1, -1)]   # alt -> neu, inkl. laufender
    alle, soll_ev, fb = store.wochen(), _soll_ereignisse(store), pipeline_facebook(reels)
    tag = heute.weekday()                                     # 0 = Montag
    plattformen = []
    for p, name in PLATTFORMEN.items():
        formate = []
        for fmt, anzeige, _mn, _mx, metrik, tipp in FORMATE[p]:
            verlauf = []
            for w in liste:
                werte = alle[p].get(w, {})
                ist, quelle = werte.get("werte", {}).get(metrik), werte.get("quellen", {}).get(metrik, "")
                mindestens = False
                if ist is None and p == "facebook" and metrik == "beitraege" and fb.get(w):
                    ist, quelle, mindestens = fb[w], "pipeline", True
                mn, mx = soll_fuer(soll_ev, p, fmt, w)
                if ist is None:
                    status = "unbekannt"
                elif ist >= mn:
                    status = "ok"
                else:
                    status = "offen" if w == aktuell else "unter"
                verlauf.append({"woche": w, "ist": ist, "quelle": quelle, "mindestens": mindestens,
                                "soll_min": mn, "soll_max": mx, "status": status})
            fertig = [v for v in verlauf[:-1] if v["status"] in ("ok", "unter")]
            jetzt = verlauf[-1]
            tempo = math.ceil(jetzt["soll_min"] * (tag + 1) / 7)
            formate.append({"id": fmt, "name": anzeige, "metrik": metrik, "tipp": tipp,
                            "soll_min": jetzt["soll_min"], "soll_max": jetzt["soll_max"],
                            "aktuell": jetzt, "verlauf": verlauf,
                            "erfuellt": sum(v["status"] == "ok" for v in fertig), "bewertet": len(fertig),
                            "hinter_tempo": jetzt["ist"] is not None and jetzt["quelle"] == "api" and jetzt["ist"] < tempo})
        plattformen.append({"id": p, "name": name, "formate": formate})
    return {"heute": heute.isoformat(), "aktuelle_woche": aktuell, "wochen": liste, "tage_rest": 6 - tag,
            "plattformen": plattformen,
            "hinweis": "Instagram zählt LUNA täglich selbst. Facebook ohne eingetragenen Wert: nur die von LUNA geposteten "
                       "Reels (mindestens). TikTok und YouTube: Anzahl in „Woche eintragen“."}


def _soll_text(mn: int, mx: int | None) -> str:
    return f"mind. {mn}" if mx is None or mx == mn else f"{mn}–{mx}"


def briefing_zeilen(ausw: dict) -> list[str]:
    """Hinweise fuers Morgen-Briefing (siehe Modul-Doku). Leere Liste = nichts nachzulegen."""
    tag = date.fromisoformat(ausw["heute"]).weekday()
    out = []
    for p in ausw["plattformen"]:
        for f in p["formate"]:
            tipp = f" – {f['tipp']}" if f["tipp"] else ""
            if tag == 1:
                v = f["verlauf"][-2]
                if v["status"] == "unter":
                    out.append(f"Letzte Woche unter Soll: {p['name']} {f['name']} {v['ist']} von "
                               f"{_soll_text(v['soll_min'], v['soll_max'])}{tipp}")
            elif 2 <= tag <= 5 and f["hinter_tempo"]:
                a = f["aktuell"]
                out.append(f"{p['name']} {f['name']}: diese Woche {a['ist']} von {_soll_text(a['soll_min'], a['soll_max'])}, "
                           f"noch {ausw['tage_rest']} Tag(e) bis Sonntag{tipp}")
    return out
