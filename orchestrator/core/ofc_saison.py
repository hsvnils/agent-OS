"""OFC_ROADMAP O6: Abschluss, offene Posten, Saisonuebersicht, Statistik je Mitglied, Export (CSV, PDF A4 hochkant).

- **Abschliessen (E7):** „abschliessbar“ = Spieltag vorbei und alle Karten bezahlt; der CEO klickt -> der Spielordner wandert
  nach `Abgeschlossen/` (`os.rename`, nie ueberschreiben, nie loeschen); „wieder oeffnen“ schiebt zurueck. Vorschau vorher.
- **Offene Posten** je Kartenname (wer schuldet was, fuer welches Spiel) mit Text zum Kopieren -- LUNA verschickt nichts.
- **Saisonuebersicht:** eingekauft (Rechnungen), eigene Zahlungen (O4), eingenommen (O5), offen, Differenz.
- **Statistik je Mitglied:** wie oft wer Karten bekommen hat (je Saison, je Wettbewerb) -- Grundlage fuer faire Vergabe.
Regelbasiert, keine KI; nur fuer den CEO; getrennt von der Buchhaltung.
"""
from __future__ import annotations

import csv
import io
import os
import re
from datetime import date
from pathlib import Path

from . import ofc
from .ofc_eingang import bezahlt_stand
from .ofc_store import OfcStore, _LOCK
from .ofc_zahlung import zahlungs_status


def _eur(c: int) -> str:
    neg = c < 0
    e, r = divmod(abs(int(c)), 100)
    return ("-" if neg else "") + f"{e:,}".replace(",", ".") + f",{r:02d} €"


def _tag(iso: str) -> str:
    try:
        return date.fromisoformat(iso[:10]).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return ""


def _wettbewerb(s: dict) -> str:
    w = (s.get("wettbewerb") or "").strip()
    if not w and s.get("heimspiel") is False:
        return "Auswärts"
    return w or "Liga"


def _name_key(n: str) -> str:
    return re.sub(r"\s+", " ", (n or "").strip()).casefold()


# -- Abschliessen -----------------------------------------------------------------------------------------------------
def abschluss_plan(store: OfcStore, sid: str, saison: Path | None = None, *, zurueck: bool = False,
                   heute: date | None = None) -> dict:
    """Dry-Run: verschiebe `<Ordner>` nach `Abgeschlossen/<Ordner>` (oder zurueck). Prueft „abschliessbar“ und Kollision."""
    from .ofc_store import uebersicht
    saison = saison or ofc.nas_ordner()
    st = store.stand()
    s = st["spiele"].get(sid)
    if not s or s.get("verworfen"):
        return {"ok": False, "hinweis": "Spiel nicht gefunden."}
    if bool(s.get("abgeschlossen")) != zurueck:
        return {"ok": False, "hinweis": "Spiel ist schon abgeschlossen." if not zurueck else "Spiel ist nicht abgeschlossen."}
    name = Path(s["pfad"]).name
    von = saison / s["pfad"]
    nach_rel = name if zurueck else f"{ofc.ABGESCHLOSSEN}/{name}"
    nach = saison / nach_rel
    plan = {"ok": True, "id": sid, "von": s["pfad"], "nach": nach_rel, "zurueck": zurueck}
    if not von.is_dir():
        return plan | {"ok": False, "hinweis": f"Ordner „{s['pfad']}“ nicht gefunden – bitte zuerst „Ordner einlesen“."}
    if nach.exists() or (nach.parent.is_dir() and any(p.name.casefold() == name.casefold() for p in nach.parent.iterdir()
                                                      if p != von)):
        return plan | {"ok": False, "hinweis": f"„{nach_rel}“ gibt es schon – nichts verschoben."}
    if not zurueck:
        x = next((x for x in uebersicht(store, heute=heute)["spiele"] if x["id"] == sid), {})
        plan["abschliessbar"] = x.get("status") == "abschliessbar"
        if not plan["abschliessbar"]:
            plan["hinweis"] = "Noch nicht abschließbar (Spieltag nicht vorbei oder nicht alle Karten bezahlt)."
    return plan


def abschliessen(store: OfcStore, sid: str, saison: Path | None = None, *, zurueck: bool = False, trotzdem: bool = False,
                 von: str = "", heute: date | None = None) -> dict:
    saison = saison or ofc.nas_ordner()
    plan = abschluss_plan(store, sid, saison, zurueck=zurueck, heute=heute)
    if not plan["ok"]:
        return plan
    if not zurueck and not plan.get("abschliessbar") and not trotzdem:
        return plan | {"ok": False}
    with _LOCK:
        try:
            if not zurueck:
                (saison / ofc.ABGESCHLOSSEN).mkdir(exist_ok=True)
            ziel = saison / plan["nach"]
            if ziel.exists():
                return plan | {"ok": False, "hinweis": "Ziel ist inzwischen vorhanden – nichts verschoben."}
            os.rename(saison / plan["von"], ziel)                     # nie ueberschreiben, nie loeschen
        except OSError as exc:
            return plan | {"ok": False, "hinweis": f"Verschieben nicht möglich ({exc.__class__.__name__})."}
    store.erfassen("ofc_spiel", {"id": sid, "pfad": plan["nach"], "abgeschlossen": not zurueck}, von=von)
    return plan | {"verschoben": True}


# -- Offene Posten, Saison, Statistik ----------------------------------------------------------------------------------
def _sichtbar(st: dict) -> dict:
    return {sid: s for sid, s in st["spiele"].items() if not s.get("verworfen")}


def offene_posten(st: dict, *, alle: bool = False) -> list[dict]:
    """Je Kartenname: unbezahlte Karten (offener Betrag, Spiel, Datum) + Text zum Kopieren. `alle`: auch abgeschlossene Spiele."""
    sp = _sichtbar(st)
    bz = bezahlt_stand(st)["tickets"]
    je: dict = {}
    for nr, t in st["tickets"].items():
        s = sp.get(t["spiel"])
        if not s or (s.get("abgeschlossen") and not alle) or bz.get(nr, {}).get("bezahlt"):
            continue
        offen = max((t.get("preis_cent") or 0) - bz.get(nr, {}).get("bezahlt_cent", 0), 0)
        name = (t.get("name") or "").strip() or "ohne Namen"
        p = je.setdefault(_name_key(name), {"name": name, "posten": [], "summe_cent": 0, "unbekannt": 0})
        p["posten"].append({"ticketnr": nr, "spiel": s.get("spiel") or t["spiel"], "spiel_id": t["spiel"],
                            "spieltag": s.get("spieltag") or "", "offen_cent": offen, "preis_bekannt": bool(t.get("preis_cent"))})
        p["summe_cent"] += offen
        p["unbekannt"] += int(not t.get("preis_cent"))
    out = []
    for p in je.values():
        p["posten"].sort(key=lambda x: (x["spieltag"] or "9999", x["ticketnr"]))
        if p["name"] != "ohne Namen":
            vor = p["name"].split()[0]
            zeilen = {}
            for x in p["posten"]:
                k = (x["spiel"], x["spieltag"])
                zeilen.setdefault(k, [0, 0, 0])
                zeilen[k][0] += 1
                zeilen[k][1] += x["offen_cent"]
                zeilen[k][2] += int(not x["preis_bekannt"])
            teile = [f"- {spiel}{' am ' + _tag(tag) if tag else ''}: {n} Karte{'n' if n != 1 else ''}"
                     + (f", {_eur(c)}" if c else "") + (" (Betrag folgt)" if u and not c else "")
                     for (spiel, tag), (n, c, u) in zeilen.items()]
            p["text"] = (f"Hallo {vor}, kurze Erinnerung vom HSVInside: für folgende Karten ist die Zahlung noch offen:\n"
                         + "\n".join(teile) + (f"\nZusammen: {_eur(p['summe_cent'])}." if p["summe_cent"] else "")
                         + "\nDanke dir! 💙")
        out.append(p)
    return sorted(out, key=lambda p: (p["name"] == "ohne Namen", -p["summe_cent"], p["name"].casefold()))


def saison_summen(st: dict) -> dict:
    sp = _sichtbar(st)
    eingekauft = sum(r.get("summe_cent") or 0 for s in sp.values() for r in s.get("rechnungen") or [])
    ohne_rg = sum(t.get("preis_cent") or 0 for t in st["tickets"].values() if t.get("ohne_rechnung") and t["spiel"] in sp)
    eigene = sum((-z["betrag_cent"] if z.get("art") == "erstattung" else z["betrag_cent"])
                 for z in zahlungs_status(st) if z.get("zuordnung") != "ignoriert")
    es = [e for e in st.get("eingaenge", {}).values() if not e.get("ersetzt")]
    eingenommen = sum(e["betrag_cent"] for e in es if e.get("zuordnung") in ("auto", "manuell") and e.get("tickets"))
    nicht_zu = sum(e["betrag_cent"] for e in es if e.get("zuordnung") == "offen")
    bz = bezahlt_stand(st)["tickets"]
    offen = sum(max((t.get("preis_cent") or 0) - bz.get(nr, {}).get("bezahlt_cent", 0), 0)
                for nr, t in st["tickets"].items() if t["spiel"] in sp and not bz.get(nr, {}).get("bezahlt"))
    return {"spiele": len(sp), "karten": sum(1 for t in st["tickets"].values() if t["spiel"] in sp),
            "karten_bezahlt": sum(1 for nr, t in st["tickets"].items() if t["spiel"] in sp and bz.get(nr, {}).get("bezahlt")),
            "eingekauft_cent": eingekauft + ohne_rg, "eigene_zahlungen_cent": eigene, "eingenommen_cent": eingenommen,
            "nicht_zugeordnet_cent": nicht_zu, "offen_cent": offen, "differenz_cent": eingenommen - (eingekauft + ohne_rg)}


def statistik(st: dict) -> dict:
    """Wer hat wie oft Karten bekommen -- je Saison und Wettbewerb (Kartennamen, ohne „ohne Namen“)."""
    sp = _sichtbar(st)
    wett = sorted({_wettbewerb(s) for s in sp.values()})
    je: dict = {}
    for t in st["tickets"].values():
        s = sp.get(t["spiel"])
        name = (t.get("name") or "").strip()
        if not s or not name:
            continue
        p = je.setdefault(_name_key(name), {"name": name, "karten": 0, "spiele": set(), "je_wettbewerb": {}, "je_saison": {}})
        p["karten"] += 1
        p["spiele"].add(t["spiel"])
        w = _wettbewerb(s)
        p["je_wettbewerb"][w] = p["je_wettbewerb"].get(w, 0) + 1
        sa = s.get("saison") or "?"
        p["je_saison"][sa] = p["je_saison"].get(sa, 0) + 1
    zeilen = [p | {"spiele": len(p["spiele"])} for p in je.values()]
    zeilen.sort(key=lambda p: (-p["karten"], p["name"].casefold()))
    return {"wettbewerbe": wett, "personen": zeilen, "ohne_namen": sum(1 for t in st["tickets"].values()
                                                                       if t["spiel"] in sp and not (t.get("name") or "").strip())}


# -- Export ------------------------------------------------------------------------------------------------------------
def export_csv(st: dict) -> bytes:
    sp = _sichtbar(st)
    bz = bezahlt_stand(st)["tickets"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Saison", "Spiel", "Datum", "Wettbewerb", "Status", "Ticketnummer", "Block", "Reihe", "Sitz", "Name", "Preis",
                "Bezahlt", "Offen"])
    for nr, t in sorted(st["tickets"].items(), key=lambda x: ((sp.get(x[1]["spiel"]) or {}).get("spieltag") or "9999", x[0])):
        s = sp.get(t["spiel"])
        if not s:
            continue
        b = bz.get(nr, {})
        preis = t.get("preis_cent") or 0
        w.writerow([s.get("saison") or "", s.get("spiel") or t["spiel"], _tag(s.get("spieltag") or ""), _wettbewerb(s),
                    "abgeschlossen" if s.get("abgeschlossen") else "offen", nr, t.get("block") or "", t.get("reihe") or "",
                    t.get("sitz") or "", t.get("name") or "", _eur(preis) if preis else "", "ja" if b.get("bezahlt") else "nein",
                    _eur(max(preis - b.get("bezahlt_cent", 0), 0)) if preis and not b.get("bezahlt") else ""])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def export_pdf(st: dict, *, saison_name: str = "", schrift_dir: Path | None = None) -> bytes:
    """Saisonbericht A4 hochkant: Summen, Spiele, offene Posten, Statistik."""
    from fpdf import FPDF
    from .beleg_pdf import BLAU, DEJAVU, GRAU, LINIE, ROT, _latin1
    sd = Path(schrift_dir) if schrift_dir else DEJAVU
    uni = (sd / "DejaVuSans.ttf").exists() and (sd / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1
    p = FPDF(format="A4", orientation="P")
    if uni:
        p.add_font("DejaVu", "", str(sd / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(sd / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    else:
        S = "Helvetica"
    p.set_title(T(f"HSVInside Saison {saison_name}"))
    p.set_creator("LUNA-OS")
    p.set_margins(16, 14, 16)
    p.set_auto_page_break(True, margin=16)
    p.add_page()
    B = p.w - 32
    p.set_fill_color(*BLAU); p.rect(16, 14, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT); p.rect(16 + B / 2, 14, B / 2, 1.6, style="F")
    p.set_xy(16, 20)
    p.set_font(S, "B", 17)
    p.cell(B, 9, T(f"HSVInside – Saison {saison_name}".strip(" –")), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, size=9); p.set_text_color(90, 90, 90)
    p.cell(B, 5, T(f"Stand {date.today().strftime('%d.%m.%Y')} · erstellt von LUNA"), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0); p.ln(3)
    su = saison_summen(st)
    kacheln = [("Eingekauft", _eur(su["eingekauft_cent"])), ("Eingenommen", _eur(su["eingenommen_cent"])),
               ("Offen", _eur(su["offen_cent"])), ("Differenz", _eur(su["differenz_cent"]))]
    w = B / 4
    y0 = p.get_y()
    p.set_fill_color(*GRAU); p.rect(16, y0, B, 17, style="F")
    for i, (l, v) in enumerate(kacheln):
        p.set_xy(16 + i * w + 3, y0 + 2.5); p.set_font(S, size=7.5); p.set_text_color(110, 110, 110); p.cell(w - 6, 4, T(l))
        p.set_xy(16 + i * w + 3, y0 + 7.5); p.set_font(S, "B", 11.5); p.set_text_color(*BLAU); p.cell(w - 6, 7, T(v))
    p.set_text_color(0, 0, 0); p.set_y(y0 + 21)
    p.set_font(S, size=8.5)
    p.multi_cell(B, 4.5, T(f"{su['spiele']} Spiele · {su['karten']} Karten, davon {su['karten_bezahlt']} bezahlt · eigene "
                           f"Zahlungen {_eur(su['eigene_zahlungen_cent'])} · noch nicht zugeordnete Eingänge "
                           f"{_eur(su['nicht_zugeordnet_cent'])}"), new_x="LMARGIN", new_y="NEXT")
    p.ln(2)

    def kopf(t):
        if p.get_y() > p.h - 40:
            p.add_page()
        p.set_font(S, "B", 12); p.cell(B, 7, T(t), new_x="LMARGIN", new_y="NEXT"); p.set_draw_color(*LINIE)

    def tabelle(spalten, zeilen):
        p.set_font(S, "B", 8)
        for k, b in spalten:
            p.cell(b, 6, T(k), border="B")
        p.ln(6); p.set_font(S, size=8)
        for z in zeilen:
            if p.get_y() > p.h - 22:
                p.add_page()
            for (_, b), v in zip(spalten, z):
                txt = T(v)
                while p.get_string_width(txt) > b - 1.5 and len(txt) > 3:
                    txt = txt[:-2] + "…" if uni else txt[:-2] + "."
                p.cell(b, 5.5, txt, border="B")
            p.ln(5.5)
        p.ln(3)

    sp = sorted(_sichtbar(st).values(), key=lambda s: s.get("spieltag") or "9999")
    bz = bezahlt_stand(st)["tickets"]
    kopf("Spiele")
    zeilen = []
    for s in sp:
        tks = [t for t in st["tickets"].values() if t["spiel"] == s["id"]]
        zeilen.append([_tag(s.get("spieltag") or ""), s.get("spiel") or s["id"], _wettbewerb(s), str(len(tks)),
                       str(sum(1 for t in tks if bz.get(t["ticketnr"], {}).get("bezahlt"))),
                       _eur(sum(r.get("summe_cent") or 0 for r in s.get("rechnungen") or [])),
                       "abgeschlossen" if s.get("abgeschlossen") else "offen"])
    tabelle([("Datum", 20), ("Spiel", 58), ("Wettbewerb", 24), ("Karten", 14), ("bezahlt", 14), ("Rechnung", 22), ("Status", B - 152)], zeilen)
    posten = [x for x in offene_posten(st, alle=True) if x["name"] != "ohne Namen"]
    if posten:
        kopf("Offene Posten")
        tabelle([("Name", 46), ("Spiele", B - 46 - 26), ("Offen", 26)],
                [[x["name"], ", ".join(dict.fromkeys(y["spiel"] for y in x["posten"])),
                  _eur(x["summe_cent"]) if x["summe_cent"] else "unbekannt"] for x in posten])
    stat = statistik(st)
    if stat["personen"]:
        kopf("Statistik je Mitglied (Karten)")
        ws = stat["wettbewerbe"][:4]
        rest = B - 50 - 16 - 16
        tabelle([("Name", 50), ("Karten", 16), ("Spiele", 16)] + [(x, rest / max(len(ws), 1)) for x in ws],
                [[x["name"], str(x["karten"]), str(x["spiele"])] + [str(x["je_wettbewerb"].get(w_, 0) or "") for w_ in ws]
                 for x in stat["personen"]])
    return bytes(p.output())
