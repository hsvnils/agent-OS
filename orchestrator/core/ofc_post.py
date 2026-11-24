"""OFC_ROADMAP O3: Neue Bestellungen aus dem Fanclub-Postfach (HSV-Mails mit Rechnung und Ticket-PDFs).

Ablauf (regelbasiert, keine KI): HSV-Mails der letzten Wochen (nur `hsv.de`, nur lesend) -> PDF-Anhaenge -> Rechnung
(`ofc.rechnung_aus_text`) bzw. Ticket (`ofc.ticket_aus_text`) -> nach Rechnungsnummer gruppiert = Bestellung.
- Bestellung zu einem bekannten Spiel (Rechnungsnr oder gleicher Spieltag + Paarung) -> fehlende Dateien dort ergaenzen.
- Neue Bestellung mit Rechnung -> Spielordner nach E3 anlegen (`HSV vs <Gegner>` / `<Gegner> vs HSV`), Rechnung + Tickets
  ablegen. Tickets ohne Rechnung und ohne bekanntes Spiel bleiben „wartet“ (Hinweis), bis die Rechnung kommt.
- Dateien werden nur NEU angelegt (`open(..., "xb")`) -- nie ueberschrieben, nie geloescht; danach normaler Import (O1).
- `post_plan` = Dry-Run (schreibt nichts), `post_anwenden` legt an. E8: keine Telegram-Nachricht, Hinweise im Reiter.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from . import ofc
from .ofc_store import OfcStore, import_anwenden, name_sauber

HSV_DOMAINS = ("hsv.de",)
TAGE = 60
_LETZTER: dict = {}


def _ist_hsv(dom: str) -> bool:
    return any(dom == d or dom.endswith("." + d) for d in HSV_DOMAINS)


def bestellungen_aus_mails(mails: list[dict]) -> tuple[dict, int]:
    """[{roh}] -> ({rechnungsnr: {"rechnung": (datei, bytes, daten) | None, "tickets": {ticketnr: (datei, bytes)}}}, n_mails)."""
    out: dict = {}
    n = 0
    for x in mails:
        kopf, pdfs = ofc.mail_pdfs(x["roh"])
        if not _ist_hsv(kopf["domain"]) or not pdfs:
            continue
        n += 1
        for name, daten in pdfs:
            try:
                text = ofc.pdf_bytes_text(daten)
            except Exception:
                continue
            rg = ofc.rechnung_aus_text(text)
            if rg.get("erkannt") and rg.get("rechnungsnr"):
                b = out.setdefault(rg["rechnungsnr"], {"rechnung": None, "tickets": {}})
                b["rechnung"] = b["rechnung"] or (name, daten, rg)
                continue
            tk = ofc.ticket_aus_text(text)
            if tk:
                out.setdefault(tk["rechnungsnr"], {"rechnung": None, "tickets": {}})["tickets"].setdefault(tk["ticketnr"], (name, daten))
    return out, n


def ordner_name(rg: dict) -> str:
    """E3: Heimspiel `HSV vs <Gegner>`, Auswaerts `<Gegner> vs HSV`; sonst Titel der Rechnung."""
    gegner = name_sauber(rg.get("gegner") or "")
    if gegner and rg.get("heimspiel") is True:
        return f"HSV vs {gegner}"
    if gegner and rg.get("heimspiel") is False:
        return f"{gegner} vs HSV"
    return name_sauber(rg.get("spiel") or "") or f"Bestellung {rg.get('rechnungsnr', '')}"


def _ticket_datei(name: str, ticketnr: str) -> str:
    t = ofc.datei_name(name) if name else {}
    if t and f"{t['rechnungsnr']}-{t['pos']}" == ticketnr and "/" not in name and not name.startswith("."):
        return name
    return f"{ticketnr}.pdf"


def _tickets_im_ordner(ordner: Path) -> set[str]:
    out = set()
    for p in ordner.iterdir() if ordner.is_dir() else []:
        t = ofc.datei_name(p.name)
        if t:
            out.add(f"{t['rechnungsnr']}-{t['pos']}")
    return out


def post_plan(store: OfcStore, mails: list[dict], saison: Path | None = None) -> dict:
    """Dry-Run: welche Ordner/Dateien wuerden angelegt? Schreibt nichts. `_dateien` (mit Inhalt) nur intern."""
    saison = saison or ofc.nas_ordner()
    if not saison.is_dir():
        return {"ok": False, "hinweis": f"Saison-Ordner nicht gefunden ({saison.name}) -- Mount pruefen."}
    best, n_mails = bestellungen_aus_mails(mails)
    st = store.stand()
    rg_spiel = {r.get("rechnungsnr"): sid for sid, s in st["spiele"].items() for r in s.get("rechnungen") or [] if r.get("rechnungsnr")}
    rg_spiel |= {t["rechnungsnr"]: t["spiel"] for t in st["tickets"].values() if t.get("rechnungsnr") and t["rechnungsnr"] not in rg_spiel}
    paarung = {(s.get("spieltag"), s.get("heim"), s.get("gast")): sid for sid, s in st["spiele"].items() if s.get("spieltag")}
    tk_mit_datei = {nr for nr, t in st["tickets"].items() if t.get("datei")}
    liste, schreiben = [], []
    for rnr, b in sorted(best.items()):
        rg = b["rechnung"][2] if b["rechnung"] else {}
        sid = rg_spiel.get(rnr) or (paarung.get((rg.get("spieltag"), rg.get("heim"), rg.get("gast"))) if rg else None)
        eintrag = {"rechnungsnr": rnr, "spiel": rg.get("spiel") or "", "spieltag": rg.get("spieltag") or "",
                   "tickets_in_mails": len(b["tickets"]), "rechnung_in_mail": bool(b["rechnung"]), "dateien_neu": []}
        if sid:
            s = st["spiele"][sid]
            ordner, rel, neu_ordner = saison / s["pfad"], s["pfad"], False
            eintrag |= {"spiel": s.get("spiel") or sid, "spieltag": s.get("spieltag") or eintrag["spieltag"], "spiel_id": sid}
            if s.get("verworfen"):
                eintrag |= {"status": "verworfen"}
                liste.append(eintrag)
                continue
        elif rg:
            rel = ordner_name(rg)
            if (saison / rel).exists() or (saison / ofc.ABGESCHLOSSEN / rel).exists():
                tag = rg.get("spieltag") or ""
                rel = f"{rel} ({tag[8:10]}.{tag[5:7]}.)" if tag else f"{rel} ({rnr})"
            ordner, neu_ordner = saison / rel, not (saison / rel).exists()
        else:
            eintrag |= {"status": "wartet", "hinweis": "Tickets ohne Rechnung -- warte auf die Rechnung"}
            liste.append(eintrag)
            continue
        vorhanden = {p.name.casefold() for p in ordner.iterdir()} if ordner.is_dir() else set()
        im_ordner = _tickets_im_ordner(ordner)
        if b["rechnung"] and not (sid and rnr in {r.get("rechnungsnr") for r in st["spiele"][sid].get("rechnungen") or []}):
            datei = "Rechnung.pdf" if "rechnung.pdf" not in vorhanden else f"Rechnung-{rnr}.pdf"
            if datei.casefold() not in vorhanden:
                schreiben.append((ordner, datei, b["rechnung"][1]))
                eintrag["dateien_neu"].append(datei)
        for nr, (name, daten) in sorted(b["tickets"].items()):
            if nr in tk_mit_datei or nr in im_ordner:
                continue
            datei = _ticket_datei(name, nr)
            if datei.casefold() in vorhanden:
                continue
            schreiben.append((ordner, datei, daten))
            eintrag["dateien_neu"].append(datei)
        eintrag |= {"ordner": rel, "neu_ordner": neu_ordner and bool(eintrag["dateien_neu"]),
                    "status": ("neu" if neu_ordner else "ergaenzen") if eintrag["dateien_neu"] else "vorhanden"}
        if not b["tickets"] and eintrag["status"] != "vorhanden":
            eintrag["hinweis"] = "Rechnung da, Ticket-PDFs noch nicht im Postfach"
        liste.append(eintrag)
    return {"ok": True, "mails": n_mails, "bestellungen": liste,
            "neu": sum(1 for x in liste if x["status"] in ("neu", "ergaenzen")),
            "wartet": sum(1 for x in liste if x["status"] == "wartet"),
            "dateien": len(schreiben), "_dateien": schreiben}


def post_anwenden(store: OfcStore, mails: list[dict], saison: Path | None = None, *, von: str = "") -> dict:
    saison = saison or ofc.nas_ordner()
    plan = post_plan(store, mails, saison)
    if not plan["ok"]:
        return plan
    geschrieben, fehler = 0, []
    for ordner, datei, daten in plan.pop("_dateien"):
        try:
            ordner.mkdir(parents=True, exist_ok=True)
            with open(ordner / datei, "xb") as f:                 # nur neu anlegen -- nie ueberschreiben
                f.write(daten)
            geschrieben += 1
        except FileExistsError:
            continue
        except OSError as exc:
            fehler.append({"datei": datei, "fehler": exc.__class__.__name__})
    out = plan | {"geschrieben": geschrieben, "fehler": fehler}
    if geschrieben:
        imp = import_anwenden(store, saison, von=von or "post")
        out["import"] = {k: imp.get(k) for k in ("spiele_neu", "spiele_geaendert", "tickets_neu", "tickets_geaendert")}
        store.erfassen("ofc_post", {"dateien": geschrieben, "bestellungen": [x["rechnungsnr"] for x in plan["bestellungen"]
                                                                            if x["status"] in ("neu", "ergaenzen")]}, von=von)
    return out


def oeffentlich(plan: dict) -> dict:
    return {k: v for k, v in plan.items() if not k.startswith("_")}


# -- automatischer Lauf in luna-os (nur dort ist der Fanclub-Ordner eingehaengt) --------------------------------------
def letzter_lauf() -> dict:
    return dict(_LETZTER)


def lauf(store: OfcStore, postfach, *, von: str = "auto") -> dict:
    """Ein Lauf: HSV-Mails holen (nur lesend) und anlegen. Fehler ohne Text (koennte Zugangsdaten enthalten)."""
    try:
        if not postfach.verfuegbar():
            r = {"ok": False, "hinweis": "Postfach moin@ ist nicht eingerichtet."}
        else:
            r = oeffentlich(post_anwenden(store, postfach.posteingang(tage=TAGE, nur=HSV_DOMAINS), von=von))
    except Exception as exc:
        r = {"ok": False, "hinweis": f"Postfach-Abruf fehlgeschlagen ({exc.__class__.__name__})."}
    _LETZTER.clear()
    _LETZTER.update(r | {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return r


def starten(store_fabrik, postfach_fabrik, *, minuten: int = 15, weitere: tuple = ()) -> threading.Thread | None:
    """Hintergrund-Abruf alle `minuten` -- nur wenn der Fanclub-Ordner da ist und `OFC_AUTO_POST` nicht 0 ist."""
    if os.environ.get("OFC_AUTO_POST", "1").strip() == "0" or not ofc.nas_ordner().is_dir():
        return None

    def schleife():
        time.sleep(600)                                    # erster Lauf 10 Minuten nach dem Start
        while True:
            lauf(store_fabrik(), postfach_fabrik())
            for f in weitere:                                  # O4: eigene PayPal-Zahlungen im selben Takt
                try:
                    f(store_fabrik(), postfach_fabrik())
                except Exception:
                    pass
            time.sleep(max(5, minuten) * 60)

    t = threading.Thread(target=schleife, name="ofc-post", daemon=True)
    t.start()
    return t
