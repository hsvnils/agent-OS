"""TKP-Abrechnung nach erzielter Reichweite (TKP_ABRECHNUNG_ROADMAP T1-T3, CEO 2026-10-27).

Je Angebot (und mit ihm eingefroren im Auftrag) eine **Abrechnungsart** fuer alle TKP-Positionen (Kontakte x TKP):

- **Festpreis** (Standard, Feld leer): wie bisher -- der Preis aus den geplanten Kontakten gilt.
- **Nach Reichweite** (`reichweite`): abgerechnet werden die erzielten Kontakte x TKP / 1.000 je Position, die
  Produktion bleibt fest. Optionaler Deckel: hoechstens `deckel_prozent` mehr Kontakte als geplant (Standard 25 %).
- **Festpreis mit Ausgleich** (`ausgleich`): Festpreis, dazu nach der Kampagne **eine** Ausgleichsposition ueber die
  Summe aller TKP-Positionen: weicht die Kontaktsumme um mehr als `toleranz_prozent` (Standard 10 %) ab, wird die
  **ganze** Abweichung mit dem vereinbarten TKP (bzw. `ausgleich_tkp_cent`) ausgeglichen -- Mehrleistung als Aufschlag
  (hoechstens `deckel_prozent` vom geplanten Media-Wert), Minderleistung als Abzug (einzige negative Position).

Kontakt = Aufrufe (Reel/Story) bzw. Impressionen (Bild-Post), Stand 7 Tage nach Veroeffentlichung -- dieselben
bestaetigten Kennzahlen wie im Projektbericht (`core/postings.py`). In der Rechnung tragen die betroffenen Positionen
das Feld `reichweite` (Plan, gemessen, abgerechnet, TKP); den Betrag rechnet immer der Server. Ein von der Messung
abweichender Wert braucht einen Grund; fehlt eine Messung, ist das Festschreiben gesperrt.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from .beleg_pdf import cent, eur, menge_text

ARTEN = {"fest": "Festpreis", "reichweite": "Nach Reichweite", "ausgleich": "Festpreis mit Ausgleich"}
TOLERANZ_STANDARD = 10
DECKEL_STANDARD = 25
TYPEN = ("media", "ausgleich")
MESSUNG = ("Kontakte = Aufrufe bei Reels und Stories, Impressionen bei Bild-Posts, Stand 7 Tage nach Veröffentlichung; "
           "Nachweis über die Statistik (Insights) im Projektbericht")


def _rund(d: Decimal) -> int:
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def media_cent(kontakte: int, tkp_cent: int) -> int:
    """Kontakte x TKP / 1.000 in Cent (kaufmaennisch gerundet, auch negativ)."""
    return _rund(Decimal(int(kontakte)) * int(tkp_cent) / 1000)


def _tsd(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def _prozent(v, feld: str, hoechst: int) -> int:
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{feld}: ganze Zahl in Prozent.") from None
    if not 0 <= n <= hoechst:
        raise ValueError(f"{feld}: 0 bis {hoechst} Prozent.")
    return n


def pruefen(roh) -> dict:
    """Kopf-Feld `abrechnung` normalisieren; {} = Festpreis. Deckel: fehlt der Schluessel -> Standard, leer -> keiner."""
    if not roh:
        return {}
    if not isinstance(roh, dict) or (roh.get("art") or "fest") not in ARTEN:
        raise ValueError("Abrechnung: Festpreis, nach Reichweite oder Festpreis mit Ausgleich.")
    art = roh.get("art") or "fest"
    if art == "fest":
        return {}
    out = {"art": art}
    d = roh.get("deckel_prozent", DECKEL_STANDARD)
    if d not in (None, ""):
        out["deckel_prozent"] = _prozent(d, "Höchstbetrag", 500)
    if art == "ausgleich":
        out["toleranz_prozent"] = _prozent(roh.get("toleranz_prozent", TOLERANZ_STANDARD), "Toleranz", 50)
        t = roh.get("ausgleich_tkp_cent")
        if t in (None, "") and roh.get("ausgleich_tkp") not in (None, ""):
            t = cent(roh["ausgleich_tkp"])
        if t not in (None, "", 0, "0"):
            try:
                t = int(t)
            except (TypeError, ValueError):
                raise ValueError("Ausgleichs-TKP ungueltig.") from None
            if not 100 <= t <= 50_000:
                raise ValueError("Ausgleichs-TKP zwischen 1 und 500 €.")
            out["ausgleich_tkp_cent"] = t
    return out


def ist_tkp(p: dict) -> bool:
    """TKP-Position (Kontakte x TKP), deren Preis nicht von Hand ueberschrieben wurde."""
    return bool(p.get("kontakte") and p.get("tkp_cent")) and not p.get("provision") and not p.get("reichweite")


def _stueck(p: dict) -> Decimal:
    return Decimal(str(p.get("menge") or "1"))


def kontakt_label(p: dict) -> str:
    from .postings import FELDER, KONTAKT, format_von
    f = format_von(p)
    return dict(FELDER[f[0]])[KONTAKT[f[0]]] if f else "Kontakte"


def _kappe(plan: int, deckel) -> int | None:
    return None if deckel is None else math.ceil(plan * (100 + int(deckel)) / 100)


def _preisvarianten(positionen: list[dict], ab: dict, art: str) -> list[dict]:
    """Positionen mit ersetztem Einzelpreis: `ohne_media` (nur Produktion) bzw. `hoechst` (Deckel ausgeschoepft)."""
    out = []
    for p in positionen:
        if not ist_tkp(p):
            out.append(p)
            continue
        prod = int(p.get("produktion_cent") or 0)
        if art == "ohne_media":
            ep = prod
        else:
            ep = media_cent(_kappe(int(p["kontakte"]), ab["deckel_prozent"]), p["tkp_cent"]) + prod
        out.append(p | {"einzelpreis_cent": ep})
    return out


def hoechstbetrag(a: dict) -> int | None:
    """Hoechstens zu zahlende Summe laut Angebot (mit Zuschlaegen/Rabatt) -- None ohne Deckel bzw. ohne TKP-Positionen."""
    from .angebote import summen
    ab = a.get("abrechnung") or {}
    pos = a.get("positionen") or []
    if ab.get("deckel_prozent") is None or not any(ist_tkp(p) for p in pos):
        return None
    z, r = a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0
    if ab["art"] == "reichweite":
        return summen(_preisvarianten(pos, ab, "hoechst"), z, r)["gesamt_cent"]
    plan = sum(media_cent(int(p["kontakte"]) * _stueck(p), p["tkp_cent"]) for p in pos if ist_tkp(p))
    extra = {"beschreibung": "Ausgleich", "menge": "1", "einzelpreis_cent": _rund(Decimal(plan) * ab["deckel_prozent"] / 100)}
    return summen(list(pos) + [extra], z, r)["gesamt_cent"]


def vorkasse_basis(a: dict, geld_cent: int) -> int:
    """Basis der Vorkasse: bei Abrechnung nach Reichweite nur Produktion + Festpreis-Positionen (E8)."""
    from .angebote import summen
    ab = a.get("abrechnung") or {}
    if ab.get("art") != "reichweite":
        return geld_cent
    z, r = a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0
    voll = summen(a["positionen"], z, r)["gesamt_cent"]
    ohne = summen(_preisvarianten(a["positionen"], ab, "ohne_media"), z, r)["gesamt_cent"]
    return max(0, geld_cent - (voll - ohne))


def angebot_text(a: dict) -> str:
    """Absatz fuer Angebot/Auftragsbestaetigung (Entwurf Claude Code, vor Einsatz anwaltlich pruefen -- E9)."""
    ab = a.get("abrechnung") or {}
    tkp = [p for p in a.get("positionen") or [] if ist_tkp(p)]
    if not ab or not tkp:
        return ""
    hoechst = hoechstbetrag(a)
    if ab["art"] == "reichweite":
        satz = ("Abrechnung nach Reichweite: Die genannte Summe ist voraussichtlich. Berechnet werden die tatsächlich "
                "erzielten Kontakte je Leistung × vereinbarter TKP / 1.000 zuzüglich der festen Produktionskosten ("
                + MESSUNG + ").")
        if hoechst is not None:
            satz += (f" Abgerechnet werden höchstens {ab['deckel_prozent']} % mehr Kontakte als geplant; der Gesamtbetrag "
                     f"liegt damit bei höchstens {eur(hoechst)}.")
        return satz
    plan = sum(int(p["kontakte"]) * _stueck(p) for p in tkp)
    satz_tkp = (f"{eur(ab['ausgleich_tkp_cent'])} TKP" if ab.get("ausgleich_tkp_cent")
                else "dem vereinbarten TKP der jeweiligen Leistung")
    satz = (f"Reichweiten-Ausgleich: Geplant sind insgesamt {_tsd(plan)} Kontakte ({MESSUNG}). Weicht die erzielte Summe "
            f"um mehr als {ab['toleranz_prozent']} % davon ab, gleichen wir die gesamte Abweichung mit {satz_tkp} je 1.000 "
            "Kontakte aus – Mehrleistung als Aufschlag, Minderleistung als Gutschrift auf der Rechnung. Die Produktion "
            "bleibt unverändert.")
    if hoechst is not None:
        satz += f" Der Aufschlag beträgt höchstens {ab['deckel_prozent']} % des geplanten Media-Werts (Gesamtbetrag höchstens {eur(hoechst)})."
    return satz


# -- Rechnung ------------------------------------------------------------------------------------------------------

def ist_je_position(postings: list[dict]) -> dict[int, int | None]:
    """Erzielte Kontakte je Auftragsposition (1-basiert) -- None, solange ein Posting der Position ungemessen ist."""
    out: dict[int, int | None] = {}
    for p in postings:
        v = (p.get("kennzahlen") or {}).get(p["kontakt_feld"])
        alt = out.get(p["position"], 0)
        out[p["position"]] = None if v is None or alt is None else alt + int(v)
    return out


def _zeile(p: dict, ist, pos: int) -> dict:
    return {"position": pos, "titel": p["beschreibung"][:200], "plan": int(int(p["kontakte"]) * _stueck(p)), "tkp_cent": int(p["tkp_cent"]),
            "kontakt": kontakt_label(p), "gemessen": ist, "ist": ist}


def rechnungs_positionen(auftrag: dict, postings: list[dict]) -> list[dict]:
    """Positionen des Rechnungsentwurfs aus dem Auftrag -- bei Abrechnung nach Reichweite bzw. mit Ausgleich mit den
    erzielten Kontakten aus den Postings (Betrag rechnet `_positionen` -> `berechnen`)."""
    pos = [{k: v for k, v in p.items() if k != "gesamt_cent"} for p in auftrag["positionen"]]
    ab = auftrag.get("abrechnung") or {}
    if not ab or not any(ist_tkp(p) for p in pos):
        return pos
    ist = ist_je_position(postings)
    if ab["art"] == "reichweite":
        out = []
        for i, p in enumerate(pos, 1):
            if not ist_tkp(p):
                out.append(p)
                continue
            rest = {k: p[k] for k in ("gruppe", "gruppe_farbe") if p.get(k)}
            rw = {"typ": "media", "zeilen": [_zeile(p, ist.get(i), i)]}
            if ab.get("deckel_prozent") is not None:
                rw["deckel_prozent"] = ab["deckel_prozent"]
            out.append(rest | {"beschreibung": p["beschreibung"], "menge": "1", "einheit": "", "reichweite": rw})
            if int(p.get("produktion_cent") or 0):
                out.append(rest | {"beschreibung": f"Produktion: {p['beschreibung']}"[:500], "menge": p["menge"],
                                   "einheit": p.get("einheit", ""), "einzelpreis_cent": int(p["produktion_cent"])})
        return out
    rw = {"typ": "ausgleich", "zeilen": [_zeile(p, ist.get(i), i) for i, p in enumerate(pos, 1) if ist_tkp(p)],
          "toleranz_prozent": ab.get("toleranz_prozent", TOLERANZ_STANDARD)}
    for k in ("ausgleich_tkp_cent", "deckel_prozent"):
        if ab.get(k) is not None:
            rw[k] = ab[k]
    gruppe = next((p.get("gruppe") for p in pos if ist_tkp(p) and p.get("gruppe")), "")
    return pos + [({"gruppe": gruppe} if gruppe else {}) | {"beschreibung": "Reichweiten-Ausgleich", "menge": "1",
                                                           "einheit": "", "reichweite": rw}]


def _ganz(v, feld: str, i: int) -> int | None:
    if v in (None, ""):
        return None
    try:
        n = int(str(v).replace(".", "").replace(" ", ""))
    except (TypeError, ValueError):
        raise ValueError(f"Position {i}: {feld} als ganze Zahl.") from None
    if not 0 <= n <= 1_000_000_000:
        raise ValueError(f"Position {i}: {feld} ausserhalb des Rahmens.")
    return n


def berechnen(roh, i: int) -> dict:
    """Feld `reichweite` einer Rechnungsposition pruefen und den Betrag rechnen -> {menge, einzelpreis_cent, detail,
    reichweite}. Abweichung vom gemessenen Wert nur mit Grund; ohne Wert bleibt der Betrag 0 (`offen`)."""
    if not isinstance(roh, dict) or roh.get("typ") not in TYPEN or not isinstance(roh.get("zeilen"), list):
        raise ValueError(f"Position {i}: Reichweiten-Abrechnung ungueltig.")
    zeilen = []
    for z in roh["zeilen"][:60]:
        if not isinstance(z, dict):
            raise ValueError(f"Position {i}: Reichweiten-Zeile ungueltig.")
        plan, tkp = _ganz(z.get("plan"), "geplante Kontakte", i), _ganz(z.get("tkp_cent"), "TKP", i)
        if not plan or not tkp or not 100 <= tkp <= 50_000:
            raise ValueError(f"Position {i}: geplante Kontakte und TKP (1-500 €) noetig.")
        gem, ist = _ganz(z.get("gemessen"), "gemessene Kontakte", i), _ganz(z.get("ist"), "erzielte Kontakte", i)
        neu = {"position": _ganz(z.get("position"), "Auftragsposition", i) or 0, "titel": str(z.get("titel") or "")[:200], "plan": plan, "tkp_cent": tkp,
               "kontakt": str(z.get("kontakt") or "Kontakte")[:30], "gemessen": gem, "ist": ist}
        grund = str(z.get("grund") or "").strip()[:300]
        if ist is not None and ist != gem:
            if not grund:
                raise ValueError(f"Position {i}: Grund fuer die abweichenden Kontakte ({neu['titel']}) fehlt.")
            neu["grund"] = grund
        zeilen.append(neu)
    if not zeilen or (roh["typ"] == "media" and len(zeilen) != 1):
        raise ValueError(f"Position {i}: Reichweiten-Zeile fehlt.")
    out = {"typ": roh["typ"], "zeilen": zeilen}
    deckel = roh.get("deckel_prozent")
    if deckel not in (None, ""):
        out["deckel_prozent"] = _prozent(deckel, "Höchstbetrag", 500)
    offen = any(z["ist"] is None for z in zeilen)
    out["offen"] = offen
    if roh["typ"] == "media":
        z = zeilen[0]
        if offen:
            return {"menge": "1", "einzelpreis_cent": 0, "reichweite": out,
                    "detail": f"{z['kontakt']} noch nicht gemessen · {eur(z['tkp_cent'])} TKP je 1.000"}
        kappe = _kappe(z["plan"], out.get("deckel_prozent"))
        z["abgerechnet"] = min(z["ist"], kappe) if kappe is not None else z["ist"]
        detail = (f"{_tsd(z['ist'])} {z['kontakt']} erzielt (geplant {_tsd(z['plan'])}) × {eur(z['tkp_cent'])} TKP / 1.000"
                  + (f" · begrenzt auf {_tsd(z['abgerechnet'])} (Höchstbetrag laut Angebot)" if z["abgerechnet"] < z["ist"] else ""))
        return {"menge": "1", "einzelpreis_cent": media_cent(z["abgerechnet"], z["tkp_cent"]), "reichweite": out,
                "detail": detail}
    out["toleranz_prozent"] = _prozent(roh.get("toleranz_prozent", TOLERANZ_STANDARD), "Toleranz", 50)
    atkp = roh.get("ausgleich_tkp_cent")
    if atkp not in (None, "", 0):
        atkp = _ganz(atkp, "Ausgleichs-TKP", i)
        if not 100 <= atkp <= 50_000:
            raise ValueError(f"Position {i}: Ausgleichs-TKP zwischen 1 und 500 €.")
        out["ausgleich_tkp_cent"] = atkp
    plan = sum(z["plan"] for z in zeilen)
    if offen:
        return {"menge": "1", "einzelpreis_cent": 0, "reichweite": out,
                "detail": f"Kontakte noch nicht vollständig gemessen (geplant {_tsd(plan)})"}
    ist = sum(z["ist"] for z in zeilen)
    abw = ist - plan
    pz = Decimal(abw) * 100 / plan
    out |= {"plan": plan, "ist": ist, "abweichung_prozent": float(pz.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))}
    pz_text = ("+" if abw >= 0 else "−") + menge_text(abs(Decimal(str(out["abweichung_prozent"])))).replace(".", ",") + " %"
    basis = f"Erzielt {_tsd(ist)} von geplant {_tsd(plan)} Kontakten ({pz_text})"
    if abs(pz) <= out["toleranz_prozent"]:
        return {"menge": "1", "einzelpreis_cent": 0, "reichweite": out,
                "detail": f"{basis} – innerhalb der Toleranz von ±{out['toleranz_prozent']} %, kein Ausgleich"}
    if out.get("ausgleich_tkp_cent"):
        betrag, wie = media_cent(abw, out["ausgleich_tkp_cent"]), f"mit {eur(out['ausgleich_tkp_cent'])} TKP je 1.000 Kontakte"
    else:
        betrag = _rund(sum(Decimal(z["ist"] - z["plan"]) * z["tkp_cent"] / 1000 for z in zeilen))
        wie = (f"mit {eur(zeilen[0]['tkp_cent'])} TKP je 1.000 Kontakte" if len({z["tkp_cent"] for z in zeilen}) == 1
               else "zum vereinbarten TKP der jeweiligen Leistung")
    detail = f"{basis} · Ausgleich der gesamten Abweichung {wie}"
    if betrag > 0 and out.get("deckel_prozent") is not None:
        kappe = _rund(sum(Decimal(z["plan"]) * z["tkp_cent"] / 1000 for z in zeilen) * out["deckel_prozent"] / 100)
        if betrag > kappe:
            betrag = kappe
            detail += f" · begrenzt auf {out['deckel_prozent']} % des Media-Werts"
    return {"menge": "1", "einzelpreis_cent": betrag, "reichweite": out, "detail": detail,
            "beschreibung": "Reichweiten-Ausgleich: " + ("Mehrleistung" if betrag > 0 else "Minderleistung")}


def aktualisieren(positionen: list[dict], postings: list[dict]) -> list[dict] | None:
    """Neue Messwerte in einen bestehenden Entwurf uebernehmen: `gemessen` immer, `ist` nur, wenn er bisher der Messung
    folgte (von Hand mit Grund gesetzte Werte bleiben). None = nichts geaendert."""
    ist = ist_je_position(postings)
    neu, geaendert = [], False
    for p in positionen:
        rw = p.get("reichweite")
        if not rw:
            neu.append(p)
            continue
        zeilen = []
        for z in rw["zeilen"]:
            m = ist.get(z.get("position"))
            if m != z.get("gemessen"):
                geaendert = True
                folgt = z.get("ist") == z.get("gemessen")
                z = z | {"gemessen": m} | ({"ist": m} if folgt else {})
                if folgt:
                    z.pop("grund", None)
            zeilen.append({k: v for k, v in z.items() if k != "abgerechnet"})
        neu.append({k: v for k, v in p.items() if k not in ("gesamt_cent", "einzelpreis_cent")} | {"reichweite": rw | {"zeilen": zeilen}})
    return neu if geaendert else None


def offene(positionen: list[dict]) -> list[str]:
    return [p["beschreibung"] for p in positionen if (p.get("reichweite") or {}).get("offen")]


def anreichern(a: dict, sm: dict, geld_cent: int) -> dict:
    """Zusatzfelder fuer Angebot/Auftrag (LUNA-OS + PDF): Vorkasse-Basis, Hoechstbetrag, Text; Summe „voraussichtlich“."""
    ab = a.get("abrechnung") or {}
    if not ab or not any(ist_tkp(p) for p in a.get("positionen") or []):
        return {}
    if ab["art"] == "reichweite":
        sm["gesamt_label"] = "Gesamt (voraussichtlich)"
    return {"vorkasse_basis_cent": vorkasse_basis(a, geld_cent), "hoechst_cent": hoechstbetrag(a),
            "abrechnung_text": angebot_text(a), "abrechnung_art": ARTEN[ab["art"]]}
