"""Wochenplanung mit Zeitbloecken + Wochenrueckblick (JARVIS_ALLTAG J9, CEO-Go 2026-10-29).

- **Montag** (nach dem Morgen-Briefing, Einstellung „wochenplanung“): LUNA legt offene eigene To-dos ohne feste Uhrzeit
  als Bloecke (je `DAUER_MIN`) in freie Luecken Mo-Fr `TAG_VON`-`TAG_BIS` Uhr -- mit Mittagspause und Puffer um Termine.
  Ganztaegige Termine sperren den ganzen Tag. **Nichts landet ohne Bestaetigung im Kalender:** erst nach „✅ Eintragen“
  (Telegram) prueft LUNA den Kalender frisch und traegt nur Bloecke ein, die weiterhin frei sind (LUNAs eigener Kalender).
  Auch per Chat: Werkzeug `wochenplan_vorschlagen` („Plan mir die Woche“).
- **Freitag** 16 Uhr (Einstellung „wochenrueckblick“): erledigt, offen, Rechnungen der Woche, naechste Woche.

Speicher `wochenplan/log.jsonl` (nur NAS + Backup): `vorgeschlagen` (Woche, Bloecke), `eingetragen` (Termin-IDs),
`abgelehnt`.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

TAG_VON, TAG_BIS = 9, 18
MITTAG = (12, 13)
DAUER_MIN = 60
PUFFER_MIN = 15
MAX_BLOECKE = 6
RUECKBLICK_STUNDE = 16
_WT = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def montag(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _zeit(t: str) -> datetime | None:
    from .alltag import _zeit as z
    return z(t)


def _tag(t: str) -> date | None:
    try:
        return date.fromisoformat(str(t)[:10])
    except ValueError:
        return None


def belegt(termine: list[dict]) -> tuple[list[tuple[datetime, datetime]], set[date]]:
    """Zeitraeume (mit Puffer) und ganz gesperrte Tage (ganztaegige Termine) aus der Kalender-Agenda."""
    spannen, tage = [], set()
    for t in termine:
        s, e = _zeit(t.get("start", "")), _zeit(t.get("ende", ""))
        if s is None:                                     # ganztaegig: Start „JJJJ-MM-TT“, Ende exklusiv
            a, b = _tag(t.get("start", "")), _tag(t.get("ende", ""))
            if a:
                for i in range(max(((b or a + timedelta(days=1)) - a).days, 1)):
                    tage.add(a + timedelta(days=i))
            continue
        e = e or s + timedelta(hours=1)
        spannen.append((s - timedelta(minutes=PUFFER_MIN), e + timedelta(minutes=PUFFER_MIN)))
    return spannen, tage


def freie_luecken(termine: list[dict], jetzt: datetime) -> list[tuple[datetime, datetime]]:
    """Freie Zeitraeume von jetzt (auf 15 min aufgerundet, +30 min Vorlauf) bis Freitag `TAG_BIS` dieser Woche."""
    spannen, gesperrt = belegt(termine)
    ab = jetzt + timedelta(minutes=30)
    ab = ab.replace(second=0, microsecond=0) + timedelta(minutes=(15 - ab.minute % 15) % 15)
    out = []
    mo = montag(jetzt.date())
    for i in range(5):
        tag = mo + timedelta(days=i)
        if tag < jetzt.date() or tag in gesperrt:
            continue
        rahmen = [(datetime.combine(tag, datetime.min.time()).replace(hour=TAG_VON),
                   datetime.combine(tag, datetime.min.time()).replace(hour=MITTAG[0])),
                  (datetime.combine(tag, datetime.min.time()).replace(hour=MITTAG[1]),
                   datetime.combine(tag, datetime.min.time()).replace(hour=TAG_BIS))]
        for s, e in rahmen:
            s = max(s, ab)
            frei = [(s, e)] if s < e else []
            for bs, be in spannen:
                neu = []
                for fs, fe in frei:
                    if be <= fs or bs >= fe:
                        neu.append((fs, fe))
                        continue
                    if fs < bs:
                        neu.append((fs, bs))
                    if be < fe:
                        neu.append((be, fe))
                frei = neu
            out += [x for x in frei if x[1] - x[0] >= timedelta(minutes=DAUER_MIN)]
    return sorted(out)


def kandidaten(gruppen: dict, sonntag: date) -> list[dict]:
    """Offene To-dos ohne feste Uhrzeit: ueberfaellig, faellig bis Sonntag, dann ohne Datum (aelteste zuerst)."""
    out = [a for k in ("ueberfaellig", "heute", "demnaechst") for a in gruppen.get(k, [])
           if not a.get("uhrzeit") and (a.get("faellig") or "") <= sonntag.isoformat()]
    out += sorted((a for a in gruppen.get("ohne_datum", []) if not a.get("uhrzeit")), key=lambda a: a["angelegt"])
    return out


def vorschlagen(todos: list[dict], termine: list[dict], jetzt: datetime) -> list[dict]:
    """Bloecke {todo, titel, start, ende} -- frueheste passende Luecke, vor bzw. am Faelligkeitstag."""
    luecken = freie_luecken(termine, jetzt)
    dauer = timedelta(minutes=DAUER_MIN)
    bloecke = []
    for a in todos:
        if len(bloecke) >= MAX_BLOECKE:
            break
        faellig = _tag(a.get("faellig") or "")
        for i, (s, e) in enumerate(luecken):
            if faellig and faellig >= jetzt.date() and s.date() > faellig:
                continue                                   # nicht nach der Faelligkeit planen
            bloecke.append({"todo": a["id"], "titel": a["titel"], "start": s.strftime("%Y-%m-%dT%H:%M"),
                            "ende": (s + dauer).strftime("%Y-%m-%dT%H:%M")})
            rest = s + dauer
            luecken[i:i + 1] = [(rest, e)] if e - rest >= dauer else []
            break
    return sorted(bloecke, key=lambda b: b["start"])


def kollidiert(block: dict, termine: list[dict]) -> bool:
    s, e = datetime.fromisoformat(block["start"]), datetime.fromisoformat(block["ende"])
    spannen, gesperrt = belegt(termine)
    return s.date() in gesperrt or any(bs < e and be > s for bs, be in spannen)


def text(bloecke: list[dict], *, ohne_platz: int = 0) -> str:
    if not bloecke:
        return ("🗓️ Wochenplanung: Diese Woche gibt es keine offenen To-dos ohne feste Uhrzeit"
                + (" – oder keine freie Lücke dafür." if ohne_platz else "."))
    zeilen = [f"• {_WT[datetime.fromisoformat(b['start']).weekday()]} {b['start'][8:10]}.{b['start'][5:7]}. "
              f"{b['start'][11:16]}–{b['ende'][11:16]}  {b['titel']}" for b in bloecke]
    return ("🗓️ Vorschlag für deine Woche – je eine Stunde in freien Lücken (9–18 Uhr, Mittag frei):\n"
            + "\n".join(zeilen)
            + (f"\n\n{ohne_platz} weitere To-dos haben diese Woche keinen Platz mehr." if ohne_platz else "")
            + "\n\nEintragen in LUNAs Kalender? Vorher prüfe ich noch einmal, ob alles frei ist.")


class WochenplanStore:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()

    def _ereignisse(self) -> list[dict]:
        try:
            return [json.loads(z) for z in self.pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        except (OSError, ValueError):
            return []

    def _schreibe(self, typ: str, pid: str, daten: dict | None = None, von: str = "") -> None:
        e = {"ts": datetime.now().isoformat(timespec="seconds"), "typ": typ, "id": pid, "daten": daten or {}, "von": von}
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def get(self, pid: str) -> dict | None:
        p = None
        for e in self._ereignisse():
            if e.get("id") != pid:
                continue
            if e["typ"] == "vorgeschlagen":
                p = {"id": pid, "status": "offen", **e["daten"]}
            elif p and e["typ"] in ("eingetragen", "abgelehnt"):
                p |= {"status": e["typ"], **e["daten"]}
        return p

    def vorschlag(self, woche: str, bloecke: list[dict], *, von: str = "LUNA") -> dict:
        pid = "W-" + uuid.uuid4().hex[:8]
        self._schreibe("vorgeschlagen", pid, {"woche": woche, "bloecke": bloecke}, von)
        return self.get(pid)

    def entscheiden(self, pid: str, ja: bool, google, *, von: str = "Telegram:CEO") -> str:
        """✅: Kalender frisch lesen, nur freie Bloecke eintragen. ❌: nichts. Doppelklick aendert nichts."""
        p = self.get(pid)
        if not p:
            return "Diesen Vorschlag gibt es nicht mehr."
        if p["status"] != "offen":
            return "Schon erledigt." if p["status"] == "eingetragen" else "Schon verworfen."
        if not ja:
            self._schreibe("abgelehnt", pid, None, von)
            return "Okay, ich trage nichts ein."
        if google is None or not getattr(google, "verfuegbar", lambda: False)():
            return "⚠️ Kalender nicht verbunden – nichts eingetragen."
        ag = google.kalender_agenda(tage=8, max_results=100)
        if not ag.get("ok", True):
            return "⚠️ Kalender gerade nicht lesbar – nichts eingetragen. Bitte später noch einmal."
        termine = ag.get("termine") or []
        ids, belegt_ = [], []
        for b in p["bloecke"]:
            if kollidiert(b, termine):
                belegt_.append(b["titel"])
                continue
            r = google.termin_anlegen(f"🧱 {b['titel']}", b["start"] + ":00", b["ende"] + ":00",
                                      beschreibung=f"Zeitblock aus LUNAs Wochenplanung für To-do {b['todo']}.",
                                      bestaetigt=True)
            if r.get("ok"):
                ids.append(r.get("termin_id") or "")
                termine.append({"start": b["start"], "ende": b["ende"]})      # nachfolgende Bloecke sehen ihn
        self._schreibe("eingetragen", pid, {"termin_ids": ids, "uebersprungen": belegt_}, von)
        teile = [f"✅ {len(ids)} Zeitblöcke in LUNAs Kalender eingetragen."]
        if belegt_:
            teile.append("Inzwischen belegt, darum weggelassen: " + ", ".join(belegt_) + ".")
        return " ".join(teile)


def knoepfe(pid: str) -> list[dict]:
    return [{"text": "✅ Eintragen", "callback_data": f"wpl:{pid}:ja"},
            {"text": "❌ Nein", "callback_data": f"wpl:{pid}:nein"}]


def planen(gruppen: dict, termine: list[dict], jetzt: datetime) -> tuple[list[dict], int]:
    """-> (Bloecke, Anzahl To-dos ohne Platz)."""
    sonntag = montag(jetzt.date()) + timedelta(days=6)
    todos = kandidaten(gruppen, sonntag)
    bloecke = vorschlagen(todos, termine, jetzt)
    return bloecke, max(len(todos) - len(bloecke), 0)


def rueckblick(jetzt: datetime, *, erledigt: list[str], offen: int, rechnungen: list[dict], offen_cent: int,
               naechste: list[dict]) -> str:
    """Freitags-Text: erledigt, offen, Rechnungen der Woche, naechste Woche."""
    from .beleg_pdf import eur
    teile = [f"📅 Wochenrückblick KW {jetzt.isocalendar()[1]}"]
    teile.append(f"✅ Erledigt: {len(erledigt)} To-do{'s' if len(erledigt) != 1 else ''}"
                 + (" – " + ", ".join(erledigt[:6]) + (" …" if len(erledigt) > 6 else "") if erledigt else ""))
    teile.append(f"📌 Offen: {offen} To-do{'s' if offen != 1 else ''}")
    if rechnungen:
        teile.append(f"💶 Rechnungen diese Woche: {len(rechnungen)} über "
                     f"{eur(sum(int(r.get('summe_cent') or 0) for r in rechnungen))}")
    else:
        teile.append("💶 Diese Woche keine neue Rechnung.")
    if offen_cent:
        teile.append(f"   Noch offen insgesamt: {eur(offen_cent)}")
    zeitlich = [t for t in naechste if _zeit(t.get("start", ""))]
    teile.append(f"🔜 Nächste Woche: {len(naechste)} Termin{'e' if len(naechste) != 1 else ''}"
                 + (" – zuerst " + ", ".join(f"{_WT[_zeit(t['start']).weekday()]} {_zeit(t['start']):%H:%M} {t.get('titel', '')}"
                                             for t in zeitlich[:3]) if zeitlich else ""))
    teile.append("Am Montag schlage ich dir wieder Zeitblöcke vor.")
    return "\n".join(teile)


# -- Daten holen (Bot + Werkzeug) -----------------------------------------------------------------------------------------
def vorschlag_erstellen(root: Path | str, google, jetzt: datetime, *, von: str = "LUNA") -> dict:
    """-> {ok, text, id?} -- liest To-dos + Kalender, legt einen Vorschlag an (nur wenn es Bloecke gibt)."""
    from .aufgaben import AufgabenStore
    if google is None or not getattr(google, "verfuegbar", lambda: False)():
        return {"ok": False, "text": "Kalender nicht verbunden – ohne Kalender plane ich keine Zeitblöcke."}
    ag = google.kalender_agenda(tage=8, max_results=100)
    if not ag.get("ok", True):
        return {"ok": False, "text": "Kalender gerade nicht lesbar – Wochenplanung später noch einmal."}
    gruppen = AufgabenStore(Path(root) / "todos" / "log.jsonl").liste(heute=jetzt.date().isoformat(), mit_erledigt=False)
    bloecke, ohne = planen(gruppen, ag.get("termine") or [], jetzt)
    if not bloecke:
        return {"ok": True, "text": text([], ohne_platz=ohne)}
    p = WochenplanStore(Path(root) / "wochenplan" / "log.jsonl").vorschlag(montag(jetzt.date()).isoformat(), bloecke,
                                                                           von=von)
    return {"ok": True, "id": p["id"], "text": text(bloecke, ohne_platz=ohne), "bloecke": bloecke}


def rueckblick_erstellen(root: Path | str, google, jetzt: datetime) -> str:
    from .aufgaben import AufgabenStore
    root = Path(root)
    mo = montag(jetzt.date())
    g = AufgabenStore(root / "todos" / "log.jsonl").liste(heute=jetzt.date().isoformat())
    erledigt = [a["titel"] for a in g["erledigt"] if a["erledigt_am"][:10] >= mo.isoformat()]
    offen = sum(len(v) for k, v in g.items() if k != "erledigt")
    rechnungen, offen_cent = [], 0
    if (root / "buchhaltung" / "log.jsonl").exists():
        try:
            from .buchhaltung import Buchhaltung
            from .katalog import Katalog
            from .kunden import KundenStore
            from .rechnungen import RechnungStore
            bh = Buchhaltung(root / "buchhaltung")
            alle = RechnungStore(bh, KundenStore(bh), Katalog(bh)).uebersicht()["rechnungen"]
            rechnungen = [r for r in alle if mo.isoformat() <= str(r.get("rechnungsdatum") or "") <= jetzt.date().isoformat()
                          and r.get("status") not in ("storno", "storniert")]
            offen_cent = sum(max(int(r.get("summe_cent") or 0) - int(r.get("bezahlt_cent") or 0), 0)
                             for r in alle if r.get("status") == "offen")
        except Exception as exc:
            print(f"[wochenplan] Rechnungen: {exc.__class__.__name__}", flush=True)
    naechste = []
    if google is not None and getattr(google, "verfuegbar", lambda: False)():
        try:
            ag = google.kalender_agenda(tage=10, max_results=100)
            nmo, nso = mo + timedelta(days=7), mo + timedelta(days=13)
            naechste = [t for t in (ag.get("termine") or []) if (d := _tag(t.get("start", ""))) and nmo <= d <= nso]
        except Exception:
            pass
    return rueckblick(jetzt, erledigt=erledigt, offen=offen, rechnungen=rechnungen, offen_cent=offen_cent,
                      naechste=naechste)
