"""Content-Plan (CONTENT_PLAN_ROADMAP C1-C3, CEO 2026-10-05): Kalender fuer Planung und Verwaltung.

- **Eigene Eintraege** (C1): Datum, optional Uhrzeit, Kanal, Format, Titel, Status (Idee -> online), Notiz, optional
  Kunde/Auftrag/Link -- als Ereignisse `plan_eintrag` / `plan_entfernt` in der Buchhaltungs-Kette (nachvollziehbar).
- **Automatisch** (C2, nur lesend): Kunden-Postings aus Auftraegen (geplantes Datum `posting_geplant`, sonst
  Veroeffentlichungsdatum) und Drehtermine aus der Konzept-Mappe.
- **Anlaesse** (C3): gesetzliche Feiertage Hamburg (lokal berechnet, kein externer Dienst) und eigene Zeitraeume
  (`plan_anlass` / `plan_anlass_entfernt`).
"""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

KANAELE = {"instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube", "facebook": "Facebook",
           "threads": "Threads", "twitch": "Twitch", "x": "X", "sonstiges": "Sonstiges"}
FORMATE = {"reel": "Reel", "post": "Post", "karussell": "Karussell", "story": "Story", "short": "Short", "video": "Video",
           "live": "Live", "sonstiges": "Sonstiges"}
STATUS = {"idee": "Idee", "skript": "Skript", "gedreht": "Gedreht", "geschnitten": "Geschnitten", "geplant": "Geplant",
          "online": "Online"}
_ZEIT = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_TAGE = 400


def _t(v, n: int) -> str:
    return str(v if v is not None else "").strip()[:n]


def _datum(v, feld: str = "Datum") -> str:
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{feld}: ungueltig (JJJJ-MM-TT).") from None


def ostersonntag(jahr: int) -> date:
    """Gausssche Osterformel (gregorianisch)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    monat = (h + l_ - 7 * m + 114) // 31
    tag = (h + l_ - 7 * m + 114) % 31 + 1
    return date(jahr, monat, tag)


def feiertage_hamburg(jahr: int) -> dict[str, str]:
    o = ostersonntag(jahr)
    t = {date(jahr, 1, 1): "Neujahr", o - timedelta(days=2): "Karfreitag", o + timedelta(days=1): "Ostermontag",
         date(jahr, 5, 1): "Tag der Arbeit", o + timedelta(days=39): "Christi Himmelfahrt",
         o + timedelta(days=50): "Pfingstmontag", date(jahr, 10, 3): "Tag der Deutschen Einheit",
         date(jahr, 10, 31): "Reformationstag", date(jahr, 12, 25): "1. Weihnachtstag", date(jahr, 12, 26): "2. Weihnachtstag"}
    return {d.isoformat(): n for d, n in sorted(t.items())}


class ContentPlan:
    def __init__(self, bh):
        self.bh = bh

    # -- Faltung --------------------------------------------------------------------------------------------------

    @staticmethod
    def _falte(eintraege: list[dict]) -> tuple[dict, dict]:
        plan, anlaesse = {}, {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "plan_eintrag":
                x = plan.setdefault(d["id"], {"id": d["id"], "angelegt": e["ts"]})
                x.update(d["felder"])
                x["geaendert"] = e["ts"]
            elif t == "plan_entfernt":
                plan.pop(d["id"], None)
            elif t == "plan_anlass":
                anlaesse[d["id"]] = {"id": d["id"], **d["felder"]}
            elif t == "plan_anlass_entfernt":
                anlaesse.pop(d["id"], None)
        return plan, anlaesse

    # -- Schreiben ------------------------------------------------------------------------------------------------

    @staticmethod
    def _felder(daten: dict, neu: bool) -> dict:
        f = {}
        if "datum" in daten or neu:
            f["datum"] = _datum(daten.get("datum"))
        if "zeit" in daten:
            z = _t(daten.get("zeit"), 5)
            if z and not _ZEIT.match(z):
                raise ValueError("Uhrzeit: HH:MM.")
            f["zeit"] = z
        for k, erlaubt in (("kanal", KANAELE), ("format", FORMATE), ("status", STATUS)):
            if k in daten or neu:
                v = daten.get(k) or ("idee" if k == "status" else "instagram" if k == "kanal" else "reel")
                if v not in erlaubt:
                    raise ValueError(f"{k.capitalize()}: {', '.join(erlaubt)}.")
                f[k] = v
        for k, n in (("titel", 160), ("notiz", 2000), ("kunde", 20), ("auftrag", 20), ("link", 500)):
            if k in daten:
                f[k] = _t(daten[k], n)
        if neu and not f.get("titel"):
            raise ValueError("Titel fehlt.")
        if "titel" in f and not f["titel"]:
            raise ValueError("Titel darf nicht leer sein.")
        return f

    def anlegen(self, daten: dict, *, von: str = "") -> dict:
        pid = "CP-" + uuid.uuid4().hex[:8]
        self.bh.erfassen("plan_eintrag", {"id": pid, "felder": self._felder(daten or {}, True)}, von=von)
        return {"id": pid}

    def aendern(self, pid: str, daten: dict, *, von: str = "") -> dict:
        if pid not in self._falte(self.bh.eintraege())[0]:
            raise KeyError(pid)
        f = self._felder(daten or {}, False)
        if not f:
            raise ValueError("Nichts zu speichern.")
        self.bh.erfassen("plan_eintrag", {"id": pid, "felder": f}, von=von)
        return {"id": pid}

    def entfernen(self, pid: str, *, von: str = "") -> dict:
        if pid not in self._falte(self.bh.eintraege())[0]:
            raise KeyError(pid)
        self.bh.erfassen("plan_entfernt", {"id": pid}, von=von)
        return {"id": pid}

    def anlass(self, daten: dict, *, von: str = "") -> dict:
        aid = _t(daten.get("id"), 20) or "CA-" + uuid.uuid4().hex[:8]
        f = {"von": _datum(daten.get("von"), "Von"), "bis": _datum(daten.get("bis") or daten.get("von"), "Bis"),
             "titel": _t(daten.get("titel"), 120), "notiz": _t(daten.get("notiz"), 500)}
        if not f["titel"]:
            raise ValueError("Titel des Anlasses fehlt.")
        if f["bis"] < f["von"]:
            raise ValueError("Bis liegt vor Von.")
        self.bh.erfassen("plan_anlass", {"id": aid, "felder": f}, von=von)
        return {"id": aid}

    def anlass_entfernen(self, aid: str, *, von: str = "") -> dict:
        if aid not in self._falte(self.bh.eintraege())[1]:
            raise KeyError(aid)
        self.bh.erfassen("plan_anlass_entfernt", {"id": aid}, von=von)
        return {"id": aid}

    # -- Lesen (C1-C3 zusammengefuehrt) ---------------------------------------------------------------------------

    def zeitraum(self, von: str, bis: str, *, heute: str | None = None) -> dict:
        from .beauftragung import AuftragBuch
        from .konzept import KonzeptStore
        from .postings import Postings, postings_aus
        von, bis = _datum(von, "Von"), _datum(bis, "Bis")
        if bis < von or (date.fromisoformat(bis) - date.fromisoformat(von)).days > MAX_TAGE:
            raise ValueError(f"Zeitraum: hoechstens {MAX_TAGE} Tage.")
        heute = heute or date.today().isoformat()
        e = self.bh.eintraege()
        plan, anlaesse = self._falte(e)
        drin = lambda d: bool(d) and von <= d <= bis
        firmen = {}
        try:
            from .kunden import KundenStore
            firmen = {f["nummer"]: f.get("name", "") for f in KundenStore(self.bh).firmen()}
        except Exception:
            pass
        out = [{"quelle": "plan", **p} | ({"kunde_name": firmen.get(p["kunde"], "")} if p.get("kunde") else {})
               for p in plan.values() if drin(p.get("datum"))]
        # Kunden-Postings (C2)
        st = Postings._falte(e)
        for a in AuftragBuch._falte(e).values():
            if a.get("status") == "storniert":
                continue
            for p in postings_aus(a):
                x = st.get(p["id"], {})
                datum = x.get("datum") or x.get("geplant")
                if not drin(datum):
                    continue
                online = bool(x.get("datum"))
                kunde = firmen.get(a.get("firma"), "")
                out.append({"quelle": "posting", "id": p["id"], "datum": datum,
                            "titel": f"{p['titel']}" + (f" · {kunde}" if kunde else "") + (f" ({a['titel']})" if a.get("titel") else ""),
                            "format": p.get("format", ""), "kanal": (x.get("plattform") or p.get("plattform") or "instagram").lower(),
                            "status": "online" if online else "geplant", "auftrag": a["nummer"],
                            "kunde": a.get("firma", ""), "kunde_name": kunde, "link": x.get("link", ""),
                            "ueberfaellig": not online and datum < heute})
        # Drehtermine aus der Konzept-Mappe (C2), mit Kundenname aus Angebot/Auftrag
        from .angebote import AngebotStore
        kunde_von = {nr: firmen.get(x.get("firma"), "") for nr, x in AngebotStore._falte(e).items()}
        kunde_von |= {nr: firmen.get(x.get("firma"), "") for nr, x in AuftragBuch._falte(e).items()}
        for vorgang, m in KonzeptStore._falte(e).items():
            d = (m.get("dreh") or {})
            if drin(d.get("datum")):
                wer = kunde_von.get(vorgang) or vorgang
                out.append({"quelle": "dreh", "id": f"DREH-{vorgang}", "datum": d["datum"], "zeit": d.get("zeit", ""),
                            "titel": f"Dreh {wer}" + (f" · {d['ort']}" if d.get("ort") else ""), "vorgang": vorgang})
        # Feiertage + eigene Anlaesse (C3)
        feiertage = {}
        for j in range(int(von[:4]), int(bis[:4]) + 1):
            feiertage |= {k: v for k, v in feiertage_hamburg(j).items() if drin(k)}
        anl = [a for a in anlaesse.values() if a["bis"] >= von and a["von"] <= bis]
        out.sort(key=lambda x: (x["datum"], x.get("zeit") or "99:99", x.get("titel", "")))
        return {"von": von, "bis": bis, "eintraege": out, "feiertage": feiertage, "anlaesse": sorted(anl, key=lambda a: a["von"]),
                "kanaele": KANAELE, "formate": FORMATE, "status": STATUS}


# -- Wochenplan-Vorschlag (C3, CCO-Skill `content-kalender`; nur Entwurf) ----------------------------------------------

AUFTRAG = """Schlage als CCO einen Content-Plan fuer den Zeitraum vor (Skill content-kalender): Kundentermine stehen fest,
ergaenze eigene Hanserautisch-Inhalte (Fussball/HSV, Kiez, Community, Behind the Scenes) mit gutem Mix, nicht mehr als ein
eigenes Posting pro Tag, Feiertage und Anlaesse beachten, Luecken fuellen. Antworte NUR mit JSON:
{"vorschlaege": [{"datum": "JJJJ-MM-TT", "kanal": "instagram|tiktok|youtube|facebook|threads|twitch|x|sonstiges",
  "format": "reel|post|karussell|story|short|video|live|sonstiges", "titel": "kurz", "notiz": "Idee in einem Satz"}]}"""


def vorschlag(plan: dict, *, system: str, client, modell: str = "gemini-2.5-flash") -> list[dict]:
    import json as _json
    zeilen = [f"Zeitraum {plan['von']} bis {plan['bis']}"]
    # Kundentermine ohne Namen/Titel (nur dass der Tag belegt ist), eigene Eintraege mit Titel
    was = lambda x: {"posting": "Kunden-Posting", "dreh": "Kundendreh"}.get(x.get("quelle")) or x.get("titel", "")
    zeilen += [f"- {x['datum']} {was(x)} ({x.get('kanal', '')}/{x.get('format', '')}, {x.get('status', '')})"
               for x in plan["eintraege"]]
    zeilen += [f"- {d} Feiertag: {n}" for d, n in plan["feiertage"].items()]
    zeilen += [f"- {a['von']} bis {a['bis']} Anlass: {a['titel']}" for a in plan["anlaesse"]]
    r = client.chat.completions.create(model=modell, max_tokens=4000, messages=[
        {"role": "system", "content": system}, {"role": "user", "content": AUFTRAG + "\n\n" + "\n".join(zeilen)}])
    m = re.search(r"\{.*\}", r.choices[0].message.content or "", re.S)
    if not m:
        raise ValueError("Kein auswertbarer Vorschlag -- bitte erneut versuchen.")
    out = []
    for v in (_json.loads(m.group(0)).get("vorschlaege") or [])[:20]:
        try:
            d = _datum(v.get("datum"))
        except ValueError:
            continue
        if not (plan["von"] <= d <= plan["bis"]) or not _t(v.get("titel"), 160):
            continue
        out.append({"datum": d, "kanal": v.get("kanal") if v.get("kanal") in KANAELE else "instagram",
                    "format": v.get("format") if v.get("format") in FORMATE else "reel",
                    "titel": _t(v.get("titel"), 160), "notiz": _t(v.get("notiz"), 500)})
    if not out:
        raise ValueError("Der Vorschlag enthielt keine passenden Eintraege -- bitte erneut versuchen.")
    return out
