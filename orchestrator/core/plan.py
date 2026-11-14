"""Plan, Meilensteine (Gates) und Ampel je Saeule (MONETARISIERUNG_ROADMAP.md, Etappe M2).

- **Plan** = Personen (Netto-Bedarf N, Ersatzbedarf E, Netto-Luecke L durch den Brueckenjob), Annahmen (Durchschnitt je
  Kooperation, Fixkosten, Stunden je Kooperation) und die Gate-Leiter (z. B. G0-G6). Gespeichert als Ereignis
  `plan_gespeichert` {plan} in der Hash-Kette; die letzte Fassung gilt, alle frueheren bleiben als Verlauf. Die Zahlen
  traegt der CEO in LUNA-OS ein -- im (oeffentlichen) Code steht kein Plan.
- **Gate** = Name, fruehester Termin, Saeulenziele (Deckungsbeitrag je Monat), Kooperationen je Monat, **Regeln mit
  Kontinuitaet** und Kriterien zum Abhaken. Erreicht ist ein Gate erst, wenn alle Regeln *und* Kriterien erfuellt sind.
- **Regel** = {was, art, monate, x, schwelle}: `was` = gewinn | einnahmen | koop_anzahl | koop_cent | Saeulen-Code;
  `art` = in_folge (jeder der letzten n Monate) | schnitt (Durchschnitt der letzten n) | x_von_y (mindestens x der
  letzten n). `schwelle` darf eine Formel aus Euro-Betraegen und Plan-Werten sein, z. B. `2*L_nils` oder `E_nils+2*L_celine`.
- Gezaehlt werden nur **abgeschlossene Monate** (der laufende Monat ist noch nicht fertig).
- **Ampel** je Saeule gegen das Ziel des naechsten Gates: gruen ab 95 %, gelb ab 80 %, sonst rot -- rot auch, wenn die
  letzten zwei Monate beide gelb waren.

Alles deterministisch im Code, kein Sprachmodell.
"""
from __future__ import annotations

import math
import re
from copy import deepcopy
from datetime import date

from .buchhaltung import jetzt
from .saeulen import PERSONEN, SAEULEN, Saeulen

ARTEN = {"in_folge": "in Folge", "schnitt": "im Schnitt", "x_von_y": "x von y"}
GELD = ("gewinn", "einnahmen", "koop_cent")
WAS = {"gewinn": "Gewinn", "einnahmen": "Einnahmen", "koop_anzahl": "Kooperationen", "koop_cent": "Kooperationen (Euro)"} | {
    c: f"{c} · {n}" for c, (n, _) in SAEULEN.items()}
ZIEL_CODES = [c for c in SAEULEN if c not in ("S2", "S3")]          # Ziele je Teil-Saeule (S2a, S3a ...)
LEER = {"personen": {p: {"netto_cent": 0, "E_cent": 0, "L_cent": 0} for p in PERSONEN},
        "annahmen": {"koop_schnitt_cent": 0, "fixkosten_cent": 0, "stunden_je_koop": 0}, "gates": []}


def _cent(wert, feld: str) -> int:
    """int/float = schon Cent (gespeicherter Plan); Text = Euro in deutscher Schreibweise („1.200,50")."""
    if isinstance(wert, (int, float)) and not isinstance(wert, bool):
        v = round(wert)
    else:
        t = str(wert or "").replace("€", "").replace(" ", "").strip()
        try:
            v = round(float(t.replace(".", "").replace(",", ".")) * 100) if t else 0
        except ValueError:
            raise ValueError(f"{feld}: bitte eine Zahl angeben.") from None
    if not 0 <= v <= 10_000_000_00:
        raise ValueError(f"{feld}: Betrag ausserhalb 0-10 Mio. EUR.")
    return v


def variablen(plan: dict) -> dict[str, int]:
    """Formel-Variablen in Cent: E_nils, L_nils, N_nils, ..., FIX, KOOP."""
    v = {"FIX": plan["annahmen"]["fixkosten_cent"], "KOOP": plan["annahmen"]["koop_schnitt_cent"]}
    for p, w in plan["personen"].items():
        v |= {f"E_{p}": w["E_cent"], f"L_{p}": w["L_cent"], f"N_{p}": w["netto_cent"]}
    return v


def formel(text: str, var: dict[str, int], geld: bool = True) -> int:
    """„2*L_nils+1000" -> Cent (geld) bzw. Anzahl. Nur Summen aus Zahl, Variable oder Zahl*Variable."""
    t = re.sub(r"\s+", "", str(text or ""))
    if not t:
        raise ValueError("Schwelle fehlt.")
    summe = 0.0
    for term in t.split("+"):
        m = re.fullmatch(r"(?:(\d+(?:[.,]\d+)?)\*)?([A-Za-z_]+)|(\d+(?:[.,]\d+)?)", term)
        if not m:
            raise ValueError(f"Schwelle „{text}“ nicht lesbar (Beispiel: 2*L_nils oder 1000).")
        if m.group(3):
            summe += float(m.group(3).replace(",", ".")) * (100 if geld else 1)
        else:
            if m.group(2) not in var:
                raise ValueError(f"Unbekannter Wert „{m.group(2)}“ (erlaubt: {', '.join(sorted(var))}).")
            summe += float((m.group(1) or "1").replace(",", ".")) * var[m.group(2)]
    return round(summe)


def pruefe_plan(roh: dict) -> dict:
    """Plan pruefen und normalisieren (Betraege in Cent als int, Pflichtfelder, Regeln lesbar)."""
    if not isinstance(roh, dict):
        raise ValueError("Plan fehlt.")
    p = deepcopy(LEER)
    for person in PERSONEN:
        w = (roh.get("personen") or {}).get(person) or {}
        for k in ("netto_cent", "E_cent", "L_cent"):
            p["personen"][person][k] = _cent(w.get(k, 0), f"{PERSONEN[person]} {k[:-5]}")
    a = roh.get("annahmen") or {}
    p["annahmen"]["koop_schnitt_cent"] = _cent(a.get("koop_schnitt_cent", 0), "Ø je Kooperation")
    p["annahmen"]["fixkosten_cent"] = _cent(a.get("fixkosten_cent", 0), "Fixkosten")
    try:
        p["annahmen"]["stunden_je_koop"] = max(0.0, float(str(a.get("stunden_je_koop") or 0).replace(",", ".")))
    except ValueError:
        raise ValueError("Stunden je Kooperation: bitte eine Zahl.") from None
    var = variablen(p)
    codes = set()
    for i, g in enumerate(roh.get("gates") or [], 1):
        code = str(g.get("code") or "").strip()[:8]
        name = str(g.get("name") or "").strip()[:80]
        if not code or not name:
            raise ValueError(f"Gate {i}: Kuerzel und Name angeben.")
        if code in codes:
            raise ValueError(f"Gate {code} gibt es doppelt.")
        codes.add(code)
        fr = str(g.get("fruehestens") or "").strip()
        if fr and not re.fullmatch(r"\d{4}-\d{2}", fr):
            raise ValueError(f"{code}: fruehester Termin als JJJJ-MM.")
        ziele = {}
        for c, w in (g.get("ziele") or {}).items():
            if c not in SAEULEN:
                raise ValueError(f"{code}: unbekannte Saeule {c}.")
            if _cent(w, f"{code} Ziel {c}"):
                ziele[c] = _cent(w, f"{code} Ziel {c}")
        regeln = []
        for r in g.get("regeln") or []:
            was, art = r.get("was"), r.get("art")
            if was not in WAS or art not in ARTEN:
                raise ValueError(f"{code}: Regel unvollstaendig (was/art).")
            try:
                n, x = int(r.get("monate") or 0), int(r.get("x") or 0)
            except ValueError:
                raise ValueError(f"{code}: Monate als Zahl.") from None
            if not 1 <= n <= 12 or (art == "x_von_y" and not 1 <= x <= n):
                raise ValueError(f"{code}: Monate 1-12, bei „x von y“ x zwischen 1 und y.")
            formel(r.get("schwelle"), var, geld=was != "koop_anzahl")          # lesbar?
            regeln.append({"was": was, "art": art, "monate": n, "x": x if art == "x_von_y" else 0,
                           "schwelle": re.sub(r"\s+", "", str(r["schwelle"]))})
        kriterien = [{"text": str(k.get("text") or "").strip()[:160], "erledigt": bool(k.get("erledigt"))}
                     for k in g.get("kriterien") or [] if str(k.get("text") or "").strip()]
        try:
            koop = max(0, int(g.get("koop_anzahl") or 0))
        except ValueError:
            raise ValueError(f"{code}: Kooperationen je Monat als ganze Zahl.") from None
        p["gates"].append({"code": code, "name": name, "fruehestens": fr, "ziele": ziele, "koop_anzahl": koop,
                           "regeln": regeln, "kriterien": kriterien, "notiz": str(g.get("notiz") or "").strip()[:300]})
    return p


def regel_pruefen(r: dict, reihe: list[dict], var: dict) -> dict:
    """reihe = abgeschlossene Monate, aelteste zuerst (je {monat, gewinn_cent, ...})."""
    geld = r["was"] != "koop_anzahl"
    schwelle = formel(r["schwelle"], var, geld)
    def wert(m):
        if r["was"] in ("gewinn", "einnahmen", "koop_anzahl", "koop_cent"):
            return m.get(f"{r['was']}_cent" if r["was"] in ("gewinn", "einnahmen") else r["was"], 0)
        return m["db"].get(r["was"], 0)
    werte = [wert(m) for m in reihe[-r["monate"]:]]
    voll = len(werte) == r["monate"]
    n = r["monate"]
    if r["art"] == "in_folge":
        folge = 0
        for w in reversed(werte):
            if w < schwelle:
                break
            folge += 1
        erfuellt, ist = voll and folge == n, folge
        text = f"{WAS[r['was']]} jeden Monat ≥ {{s}} ({n} Monate in Folge)"
    elif r["art"] == "schnitt":
        ist = round(sum(werte) / n) if werte else 0
        erfuellt = voll and sum(werte) >= schwelle * n          # ungerundet vergleichen (999,995 ist nicht 1.000)
        text = f"{WAS[r['was']]} im {n}-Monats-Schnitt ≥ {{s}}"
    else:
        ist = sum(1 for w in werte if w >= schwelle)
        erfuellt = voll and ist >= r["x"]
        text = f"{WAS[r['was']]} in {r['x']} von {n} Monaten ≥ {{s}}"
    return {"regel": r, "schwelle": schwelle, "geld": geld, "ist": ist, "erfuellt": erfuellt, "werte": werte,
            "voll": voll, "text": text}


def ampel(ziel: int, werte: list[int]) -> str:
    """Letzter abgeschlossener Monat gegen das Ziel; zwei gelbe Monate hintereinander = rot."""
    def farbe(w):
        q = w / ziel
        return "gruen" if q >= 0.95 else "gelb" if q >= 0.8 else "rot"
    if not werte:
        return "rot"
    f = farbe(werte[-1])
    if f == "gelb" and len(werte) >= 2 and farbe(werte[-2]) == "gelb":
        return "rot"
    return f


class Plan:
    def __init__(self, bh, kunden):
        self.bh, self.kunden = bh, kunden

    def verlauf(self, eintraege: list[dict] | None = None) -> list[dict]:
        e = self.bh.eintraege() if eintraege is None else eintraege
        return [{"ts": x["ts"], "von": x.get("von", ""), "plan": x["daten"]["plan"], "notiz": x["daten"].get("notiz", "")}
                for x in e if x["typ"] == "plan_gespeichert"]

    def aktuell(self) -> dict:
        v = self.verlauf()
        return v[-1]["plan"] if v else deepcopy(LEER)

    def speichern(self, roh: dict, *, notiz: str = "", von: str = "") -> dict:
        p = pruefe_plan(roh)
        if p == self.aktuell():
            return {"geaendert": False}
        self.bh.erfassen("plan_gespeichert", {"plan": p, "notiz": str(notiz or "")[:200]}, von=von)
        return {"geaendert": True}

    def kriterium(self, gate: str, index: int, erledigt: bool, *, von: str = "") -> dict:
        p = self.aktuell()
        g = next((x for x in p["gates"] if x["code"] == gate), None)
        if not g or not 0 <= int(index) < len(g["kriterien"]):
            raise ValueError("Kriterium nicht gefunden.")
        g["kriterien"][int(index)]["erledigt"] = bool(erledigt)
        txt = g["kriterien"][int(index)]["text"]
        return self.speichern(p, notiz=f"{gate}: „{txt}“ {'erledigt' if erledigt else 'wieder offen'}", von=von)

    # -- Auswertung -------------------------------------------------------------------------------------------------

    def _reihe(self, heute: date) -> list[dict]:
        """Abgeschlossene Monate der letzten 24 Monate, aelteste zuerst."""
        roh = Saeulen(self.bh, self.kunden).monatsreihe([heute.year - 2, heute.year - 1, heute.year])
        grenze = f"{heute.year}-{heute.month:02d}"
        return [{"monat": k} | v for k, v in sorted(roh.items()) if k < grenze][-24:]

    def auswertung(self) -> dict:
        heute = jetzt().date()
        plan = self.aktuell()
        var = variablen(plan)
        reihe = self._reihe(heute)
        ziel_gate, gates = None, []
        for g in plan["gates"]:
            regeln = [regel_pruefen(r, reihe, var) for r in g["regeln"]]
            krit_offen = sum(1 for k in g["kriterien"] if not k["erledigt"])
            hat_inhalt = bool(regeln or g["kriterien"])
            erreicht = hat_inhalt and all(r["erfuellt"] for r in regeln) and not krit_offen
            s1 = g["ziele"].get("S1", 0)
            koop_noetig = math.ceil(s1 / plan["annahmen"]["koop_schnitt_cent"]) if s1 and plan["annahmen"]["koop_schnitt_cent"] else None
            summe_ziele = sum(v for c, v in g["ziele"].items())
            x = g | {"regeln_stand": regeln, "kriterien_offen": krit_offen, "erreicht": erreicht,
                     "ziel_summe_cent": summe_ziele, "ziel_gewinn_cent": summe_ziele - plan["annahmen"]["fixkosten_cent"],
                     "koop_noetig": koop_noetig, "stunden_koop": round(max(g["koop_anzahl"], koop_noetig or 0)
                                                                         * plan["annahmen"]["stunden_je_koop"], 1)}
            if not erreicht and ziel_gate is None:
                ziel_gate = x
                x["naechstes"] = True
            gates.append(x)
        letzte = reihe[-12:]
        ampeln = []
        if ziel_gate:
            for c, ziel in ziel_gate["ziele"].items():
                werte = [m["db"].get(c, 0) for m in letzte]
                ampeln.append({"code": c, "name": SAEULEN[c][0], "gruppe": SAEULEN[c][1], "ziel_cent": ziel,
                               "letzter_cent": werte[-1] if werte else 0,
                               "schnitt3_cent": round(sum(werte[-3:]) / 3) if werte else 0,
                               "quote": round((werte[-1] if werte else 0) / ziel * 100) if ziel else None,
                               "ampel": ampel(ziel, werte)})
        koop = [{"monat": m["monat"], "anzahl": m["koop_anzahl"], "cent": m["koop_cent"]} for m in letzte]
        return {"stand": heute.isoformat(), "bis_monat": reihe[-1]["monat"] if reihe else "",
                "plan": plan, "hat_plan": bool(plan["gates"]), "variablen": var,
                "gates": gates, "ziel_gate": ziel_gate["code"] if ziel_gate else "",
                "ampeln": ampeln,
                "koop": {"monate": koop, "soll_anzahl": ziel_gate["koop_anzahl"] if ziel_gate else 0,
                         "soll_cent": ziel_gate["ziele"].get("S1", 0) if ziel_gate else 0},
                "monate": [{"monat": m["monat"], "gewinn_cent": m["gewinn_cent"], "einnahmen_cent": m["einnahmen_cent"]}
                           for m in letzte],
                "verlauf": [{"ts": v["ts"], "von": v["von"], "notiz": v["notiz"]} for v in self.verlauf()][-20:][::-1],
                "auswahl": {"was": WAS, "arten": ARTEN, "ziel_codes": ZIEL_CODES,
                            "saeulen": {c: n for c, (n, _) in SAEULEN.items()}, "personen": PERSONEN},
                "hinweis": "Gezählt werden abgeschlossene Monate; Gewinn wie in den Finanzen (inkl. Gemeinkosten). "
                           "Ein Gate gilt als erreicht, wenn alle Regeln und alle Kriterien erfüllt sind."}
