"""OFC_ROADMAP O1: Speicher des Fanclubs (Spiele, Rechnungen, Tickets) -- getrennt von der Buchhaltung.

- Ablage `fanclub/log.jsonl` auf der NAS (nicht im Git, Backup wie die anderen NAS-Daten), nur Ereignisse anhaengen:
  `ofc_spiel` (Spiel anlegen/aktualisieren), `ofc_ticket` (Ticket anlegen/aktualisieren). Der Stand ergibt sich aus der
  Faltung (spaetere Felder ueberschreiben fruehere).
- **Import** aus dem Saison-Ordner (`ofc.ordner_lesen`): `import_plan` zeigt, was neu/anders waere (Dry-Run), `import_anwenden`
  schreibt genau diese Ereignisse. Namen aus den Dateinamen werden **nur beim ersten Erfassen** eines Tickets uebernommen --
  danach gilt der Name in LUNA (ab O2 im Reiter aenderbar).
- Spiel-ID = Ordnername (bleibt beim Verschieben nach `Abgeschlossen` gleich).
- Keine Namen in Protokollen; nichts wird auf der Freigabe geaendert (O1 liest nur).
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from . import ofc

_LOCK = threading.Lock()
SPIEL_FELDER = ("ordner", "pfad", "abgeschlossen", "spiel", "heim", "gast", "gegner", "heimspiel", "wettbewerb", "saison",
                "spieltag", "uhrzeit", "ort", "rechnungen")
TICKET_FELDER = ("spiel", "rechnungsnr", "pos", "block", "preisgruppe", "reihe", "sitz", "preis_cent", "datei", "ohne_rechnung")


class OfcStore:
    def __init__(self, ordner: Path):
        self.dir = Path(ordner)
        self.pfad = self.dir / "log.jsonl"

    def eintraege(self) -> list[dict]:
        if not self.pfad.exists():
            return []
        return [json.loads(z) for z in self.pfad.read_text(encoding="utf-8").splitlines() if z.strip()]

    def erfassen(self, typ: str, daten: dict, *, von: str = "") -> dict:
        e = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "typ": typ, "von": von, "daten": daten}
        with _LOCK:
            self.dir.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return e

    def stand(self) -> dict:
        spiele: dict = {}
        tickets: dict = {}
        letzter_import = ""
        for e in self.eintraege():
            d, t = e["daten"], e["typ"]
            if t == "ofc_spiel":
                spiele.setdefault(d["id"], {"id": d["id"]}).update({k: v for k, v in d.items() if k != "id"})
            elif t == "ofc_ticket":
                tickets.setdefault(d["ticketnr"], {"ticketnr": d["ticketnr"]}).update({k: v for k, v in d.items() if k != "ticketnr"})
            elif t == "ofc_import":
                letzter_import = e["ts"]
        return {"spiele": spiele, "tickets": tickets, "letzter_import": letzter_import}


# -- Import -------------------------------------------------------------------------------------------------------------
def _spiel_aus_ordner(d: dict, pfad: str, fertig: bool) -> dict:
    rgs = [rg for rg in d.get("rechnungs_liste", []) if rg.get("erkannt") or rg.get("rechnungsnr")]
    haupt = next((rg for rg in rgs if rg.get("erkannt")), rgs[0] if rgs else {})
    s = {"id": d["ordner"], "ordner": d["ordner"], "pfad": pfad, "abgeschlossen": fertig,
         "rechnungen": [{k: rg.get(k, "") for k in ("rechnungsnr", "auftragsnr", "kundennr", "datum", "summe_cent", "anzahl",
                                                    "zahlart", "datei")} for rg in rgs]}
    for k in ("spiel", "heim", "gast", "gegner", "heimspiel", "wettbewerb", "saison", "spieltag", "uhrzeit", "ort"):
        s[k] = haupt.get(k, "" if k != "heimspiel" else None)
    if not s["spiel"]:
        s["spiel"] = d["ordner"]                                   # ohne Rechnung: Ordnername als Titel
    return s


def _tickets_aus_ordner(d: dict, spiel_id: str) -> list[dict]:
    pos = {t["ticketnr"]: t for rg in d.get("rechnungs_liste", []) for t in rg.get("tickets", [])}
    out, gesehen = [], set()
    for f in d["tickets"]:
        nr = f["ticketnr"]
        if not nr or nr in gesehen:
            continue
        gesehen.add(nr)
        p = pos.get(nr, {})
        rnr, _, posnr = nr.partition("-")
        out.append({"ticketnr": nr, "spiel": spiel_id, "rechnungsnr": rnr, "pos": int(posnr) if posnr.isdigit() else 0,
                    "block": p.get("block", ""), "preisgruppe": p.get("preisgruppe", ""), "reihe": p.get("reihe", ""),
                    "sitz": p.get("sitz", ""), "preis_cent": p.get("preis_cent", 0), "datei": f["datei"],
                    "ohne_rechnung": not p, "_name_datei": f.get("name", "")})
    for nr, p in pos.items():                                       # in der Rechnung, aber keine Datei im Ordner
        if nr not in gesehen:
            out.append({"ticketnr": nr, "spiel": spiel_id, "rechnungsnr": nr.split("-")[0], "pos": p["pos"],
                        "block": p["block"], "preisgruppe": p["preisgruppe"], "reihe": p["reihe"], "sitz": p["sitz"],
                        "preis_cent": p["preis_cent"], "datei": "", "ohne_rechnung": False, "_name_datei": ""})
    return out


def import_plan(store: OfcStore, saison: Path | None = None) -> dict:
    """Dry-Run: welche Spiele/Tickets waeren neu oder geaendert? -> {ok, spiele_neu, spiele_geaendert, tickets_neu,
    tickets_geaendert, namen_neu, ereignisse}. Nichts wird geschrieben."""
    saison = saison or ofc.nas_ordner()
    if not saison.is_dir():
        return {"ok": False, "hinweis": f"Saison-Ordner nicht gefunden ({saison.name}) -- Mount pruefen."}
    try:
        liste = ofc._spielordner(saison)
    except PermissionError:
        return {"ok": False, "hinweis": "Keine Leseberechtigung auf den Fanclub-Ordner (DSM: Benutzer nilskrueger berechtigen)."}
    st = store.stand()
    ev: list[tuple[str, dict]] = []
    sn, sg, tn, tg, nn, fehler = [], [], 0, 0, 0, []
    for ordner, fertig in liste:
        try:
            d = ofc.ordner_lesen(ordner)
        except Exception as exc:
            fehler.append({"ordner": ordner.name, "fehler": exc.__class__.__name__})
            continue
        pfad = f"{ofc.ABGESCHLOSSEN}/{ordner.name}" if fertig else ordner.name
        s = _spiel_aus_ordner(d, pfad, fertig)
        alt = st["spiele"].get(s["id"])
        if alt is None:
            ev.append(("ofc_spiel", s))
            sn.append(s["id"])
        else:
            diff = {k: s[k] for k in SPIEL_FELDER if alt.get(k) != s[k]}
            if diff:
                ev.append(("ofc_spiel", {"id": s["id"], **diff}))
                sg.append(s["id"])
        for t in _tickets_aus_ordner(d, s["id"]):
            name_datei = t.pop("_name_datei")
            alt_t = st["tickets"].get(t["ticketnr"])
            if alt_t is None:
                ev.append(("ofc_ticket", t | {"name": name_datei}))
                tn += 1
                nn += int(bool(name_datei))
            else:
                diff = {k: t[k] for k in TICKET_FELDER if alt_t.get(k) != t[k]}
                if diff:
                    ev.append(("ofc_ticket", {"ticketnr": t["ticketnr"], **diff}))
                    tg += 1
    return {"ok": True, "saison": saison.name, "spiele_neu": sn, "spiele_geaendert": sg, "tickets_neu": tn,
            "tickets_geaendert": tg, "namen_neu": nn, "fehler": fehler, "ereignisse": ev}


def import_anwenden(store: OfcStore, saison: Path | None = None, *, von: str = "") -> dict:
    plan = import_plan(store, saison)
    if not plan["ok"]:
        return plan
    for typ, daten in plan["ereignisse"]:
        store.erfassen(typ, daten, von=von)
    store.erfassen("ofc_import", {"saison": plan["saison"], "spiele_neu": len(plan["spiele_neu"]),
                                  "spiele_geaendert": len(plan["spiele_geaendert"]), "tickets_neu": plan["tickets_neu"],
                                  "tickets_geaendert": plan["tickets_geaendert"]}, von=von)
    return {k: v for k, v in plan.items() if k != "ereignisse"}


# -- Uebersicht -------------------------------------------------------------------------------------------------------
def _hinweise(s: dict, tks: list[dict]) -> list[str]:
    h = []
    if not s.get("rechnungen"):
        h.append("Rechnung fehlt im Ordner")
    ohne_rg = {t["rechnungsnr"] for t in tks if t.get("ohne_rechnung")}
    if ohne_rg and s.get("rechnungen"):
        h.append(f"{len(ohne_rg)} weitere Bestellung(en) ohne Rechnung")
    fehlt = sum(1 for t in tks if not t.get("datei"))
    if fehlt:
        h.append(f"{fehlt} Ticket-Datei(en) fehlen")
    ohne = sum(1 for t in tks if not t.get("name"))
    if ohne:
        h.append(f"{ohne} Ticket(s) ohne Namen")
    return h


def uebersicht(store: OfcStore, heute: date | None = None) -> dict:
    heute = heute or date.today()
    st = store.stand()
    je: dict = {}
    for t in st["tickets"].values():
        je.setdefault(t["spiel"], []).append(t)
    spiele = []
    for s in st["spiele"].values():
        tks = je.get(s["id"], [])
        tag = s.get("spieltag") or ""
        status = "abgeschlossen" if s.get("abgeschlossen") else ("vorbei" if tag and tag < heute.isoformat() else "offen")
        spiele.append({k: s.get(k) for k in ("id", "spiel", "gegner", "heimspiel", "wettbewerb", "saison", "spieltag",
                                             "uhrzeit", "ort", "pfad")}
                      | {"status": status, "karten": len(tks), "mit_name": sum(1 for t in tks if t.get("name")),
                         "summe_cent": sum(r.get("summe_cent") or 0 for r in s.get("rechnungen") or []),
                         "hinweise": _hinweise(s, tks)})
    spiele.sort(key=lambda x: (x["status"] == "abgeschlossen", x.get("spieltag") or "9999"))
    offen = [x for x in spiele if x["status"] != "abgeschlossen"]
    return {"spiele": spiele, "letzter_import": st["letzter_import"],
            "summe": {"spiele": len(spiele), "offen": len(offen), "karten": sum(x["karten"] for x in spiele),
                      "ohne_name": sum(x["karten"] - x["mit_name"] for x in offen),
                      "hinweise": sum(len(x["hinweise"]) for x in offen)}}


def spiel_detail(store: OfcStore, sid: str) -> dict | None:
    st = store.stand()
    s = st["spiele"].get(sid)
    if not s:
        return None
    tks = sorted((t for t in st["tickets"].values() if t["spiel"] == sid), key=lambda t: (t["rechnungsnr"], t["pos"]))
    return {"spiel": s, "tickets": tks, "hinweise": _hinweise(s, tks)}


def datei_pfad(store: OfcStore, sid: str, datei: str, saison: Path | None = None) -> Path | None:
    """Pfad einer Datei des Spiels auf der Freigabe -- nur Dateien, die das Spiel kennt (kein freier Pfad)."""
    saison = saison or ofc.nas_ordner()
    d = spiel_detail(store, sid)
    if not d or not datei:
        return None
    bekannt = {t["datei"] for t in d["tickets"] if t.get("datei")} | {r.get("datei") for r in d["spiel"].get("rechnungen") or []}
    if datei not in bekannt or "/" in datei or datei.startswith("."):
        return None
    p = (saison / d["spiel"]["pfad"] / datei).resolve()
    return p if p.is_file() and saison.resolve() in p.parents else None
