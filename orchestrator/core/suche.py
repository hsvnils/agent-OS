"""GLOBALE_SUCHE G1 (CEO 2026-10-06): eine Suche ueber alle Geschaeftsdaten, Ergebnisse nach Kategorien.

Durchsucht die Buchhaltungs-Kette (nur lesend): Firmen + Ansprechpartner, Angebote, Auftraege, Rechnungen (auch Entwuerfe),
Mahnungen, Eingangsbelege (Ausgaben), Eigenbelege, Content-Plan, Konzept-Mappen und die Firmenakte. Jeder Datensatz wird
zu einem normalisierten Suchtext (klein, Umlaute -> ae/oe/ue/ss) inkl. Betraegen in deutscher Schreibweise („1.600,00“,
„1600“) und Daten („03.10.2026“, „oktober 2026“); alle Suchwoerter muessen vorkommen (UND). Kategorien nur, wenn der Nutzer
die zugehoerige App sehen darf.
"""
from __future__ import annotations

import re
import unicodedata

MAX_JE_GRUPPE = 8
MONATE = ("januar", "februar", "maerz", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "dezember")
# Kategorie -> (Titel, App fuer die Rechte -- wie in der Navigation)
GRUPPEN = {"kunden": ("Kunden & Interessenten", "kunden"), "angebote": ("Angebote", "angebote"),
           "auftraege": ("Aufträge", "angebote"), "rechnungen": ("Rechnungen", "rechnungen"),
           "mahnungen": ("Mahnungen", "rechnungen"), "ausgaben": ("Ausgaben (Belege)", "belege"),
           "eigenbelege": ("Eigenbelege", "belege"), "contentplan": ("Content-Plan", "trends"),
           "konzepte": ("Konzepte", "angebote"), "akte": ("Akte & Mails", "kunden")}


STATUS = {"entwurf": "Entwurf", "versendet": "Versendet", "angenommen": "Angenommen", "abgelehnt": "Abgelehnt",
          "beauftragt": "Beauftragt", "erledigt": "Geliefert", "offen": "Offen", "bezahlt": "Bezahlt", "storniert": "Storniert",
          "storno": "Stornorechnung", "teilbezahlt": "Teilweise bezahlt"}


def norm(s) -> str:
    s = str(s or "").lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


def _betrag(cent) -> str:
    try:
        c = int(cent)
    except (TypeError, ValueError):
        return ""
    e, r = divmod(abs(c), 100)
    tsd = f"{e:,}".replace(",", ".")
    return f"{tsd},{r:02d} {e},{r:02d} {tsd} {e}" + (f" {e}.{r:02d}" if r else "")


def _datum(d) -> str:
    d = str(d or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return ""
    j, m, t = d.split("-")
    return f"{d} {t}.{m}.{j} {int(t)}.{int(m)}.{j} {MONATE[int(m) - 1]} {j}"


def _suchtext(*teile, betraege=(), daten=()) -> str:
    return norm(" ".join([str(t) for t in teile if t] + [_betrag(b) for b in betraege if b not in (None, "")]
                         + [_datum(d) for d in daten if d]))


def _woerter(q: str) -> list[str]:
    return [w for w in norm(q).replace("€", " ").split(" ") if w]


def _treffer(text: str, woerter: list[str]) -> bool:
    return all(w in text for w in woerter)


def _pos_text(positionen) -> str:
    return " ".join(f"{p.get('beschreibung', '')} {p.get('detail', '')}" for p in positionen or [] if isinstance(p, dict))


def _eur(cent) -> str:
    try:
        return f"{int(cent) / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def suchen(bh, kunden, q: str, *, apps: list[str] | None = None) -> dict:
    """-> {q, gruppen: [{id, titel, anzahl, treffer: [{titel, info, act, act_id, datum}]}], gesamt}"""
    from .angebote import AngebotStore
    from .beauftragung import AuftragBuch
    from .contentplan import ContentPlan
    from .eigenbelege import EigenbelegStore
    from .eingangsbelege import EingangStore
    from .firmenakte import _falte as akte_falte
    from .konzept import KonzeptStore
    from .mahnungen import MahnStore
    from .rechnungen import RechnungStore
    woerter = _woerter(q)
    if len("".join(woerter)) < 2:
        return {"q": q, "gruppen": [], "gesamt": 0}
    darf = lambda g: apps is None or GRUPPEN[g][1] in apps
    e = bh.eintraege()
    firmen, aps = kunden._falte(e)
    fname = lambda nr: (firmen.get(nr) or {}).get("name", nr or "")
    ap_je_firma: dict[str, list] = {}
    for a in aps.values():
        ap_je_firma.setdefault(a.get("firma"), []).append(a)
    gruppen: dict[str, list] = {g: [] for g in GRUPPEN}

    def add(g, rang, datum, titel, info, act, act_id, text):
        if darf(g) and _treffer(text, woerter):
            exakt = any(w == norm(act_id) or w == norm(titel) for w in woerter)
            gruppen[g].append((0 if exakt else rang, str(datum or ""), {"titel": titel, "info": info, "act": act,
                                                                        "act_id": act_id, "datum": str(datum or "")[:10]}))

    for f in firmen.values():
        ap = ap_je_firma.get(f["nummer"], [])
        text = _suchtext(f.get("name"), " ".join(f.get("nummern") or [f["nummer"]]), f.get("ort"), f.get("strasse"), f.get("plz"),
                         f.get("rechnungsmail"), f.get("website"), f.get("ustid"), f.get("notiz"), f.get("telefon"),
                         " ".join(f"{a.get('vorname', '')} {a.get('nachname', '')} {a.get('mail', '')} {a.get('telefon', '')}" for a in ap))
        typ = {"kunde": "Kunde", "interessent": "Interessent", "lieferant": "Lieferant", "partner": "Partner"}.get(f.get("typ"), "")
        add("kunden", 1 if f.get("aktiv") else 2, f.get("angelegt", ""), f.get("name", f["nummer"]),
            " · ".join(x for x in (f.get("anzeige") or f["nummer"], typ, f.get("ort")) if x), "kunde-detail", f["nummer"], text)
    for a in AngebotStore._falte(e).values():
        add("angebote", 1, a.get("datum"), f"{a['nummer']} · {fname(a.get('firma'))}",
            " · ".join(x for x in (a.get("titel"), _eur(a.get("summe_cent")), STATUS.get(a.get("status"), a.get("status"))) if x), "an-detail", a["nummer"],
            _suchtext(a["nummer"], fname(a.get("firma")), a.get("titel"), _pos_text(a.get("positionen")), a.get("status"),
                      betraege=[a.get("summe_cent")], daten=[a.get("datum")]))
    for a in AuftragBuch._falte(e).values():
        add("auftraege", 1, a.get("datum") or a.get("angelegt"), f"{a['nummer']} · {fname(a.get('firma'))}",
            " · ".join(x for x in (a.get("titel"), _eur(a.get("summe_cent")), STATUS.get(a.get("status"), a.get("status"))) if x), "ab-detail", a["nummer"],
            _suchtext(a["nummer"], a.get("angebot"), fname(a.get("firma")), a.get("titel"), a.get("notiz"), _pos_text(a.get("positionen")),
                      betraege=[a.get("summe_cent")], daten=[a.get("datum"), a.get("leistung_von"), a.get("leistung_bis")]))
    entwuerfe, rechnungen = RechnungStore._falte(e)
    for eid, r in entwuerfe.items():
        add("rechnungen", 2, r.get("angelegt"), f"Entwurf · {fname(r.get('firma'))}",
            " · ".join(x for x in (r.get("titel"), "noch nicht festgeschrieben") if x), "re-detail", eid,
            _suchtext("entwurf", fname(r.get("firma")), r.get("titel"), _pos_text(r.get("positionen")), r.get("auftrag"),
                      daten=[r.get("leistung_von"), r.get("leistung_bis")]))
    for nr, r in rechnungen.items():
        add("rechnungen", 1, r.get("datum") or r.get("festgeschrieben_am"), f"{nr} · {fname(r.get('firma'))}",
            " · ".join(x for x in (r.get("titel"), _eur(r.get("summe_cent")), STATUS.get(r.get("status"), r.get("status"))) if x), "re-detail", nr,
            _suchtext(nr, fname(r.get("firma")), r.get("titel"), _pos_text(r.get("positionen")), r.get("auftrag"), r.get("bezug"),
                      r.get("status"), betraege=[r.get("summe_cent")], daten=[r.get("datum"), r.get("faellig_am"), r.get("leistung_von")]))
    for nr, m in MahnStore._falte(e).items():
        add("mahnungen", 1, m.get("datum"), f"{nr} · {fname((rechnungen.get(m.get('rechnung')) or {}).get('firma'))}",
            " · ".join(x for x in (f"zu {m.get('rechnung')}", _eur(m.get("summe_cent"))) if x), "ma-detail", nr,
            _suchtext(nr, m.get("rechnung"), fname((rechnungen.get(m.get("rechnung")) or {}).get("firma")), "mahnung",
                      betraege=[m.get("summe_cent")], daten=[m.get("datum"), m.get("frist")]))
    for nr, b in EingangStore._falte(e).items():
        f = b.get("felder") or {}
        v = b.get("vorschlag") or {}
        wer = f.get("lieferant") or v.get("lieferant") or b.get("dateiname", "")
        add("ausgaben", 1 if b.get("status") != "verworfen" else 3, f.get("rechnungsdatum") or b.get("eingegangen"),
            f"{nr} · {wer}", " · ".join(x for x in (_eur(f.get("betrag_cent")), b.get("zweck") or f.get("kategorie"),
                                                     {"zu_pruefen": "zu prüfen", "verworfen": "verworfen"}.get(b.get("status"), "")) if x),
            "bl-detail", nr, _suchtext(nr, wer, f.get("rechnungsnummer"), b.get("zweck"), f.get("kategorie"), b.get("dateiname"),
                                        fname(f.get("lieferant_firma")), betraege=[f.get("betrag_cent"), v.get("betrag_cent")],
                                        daten=[f.get("rechnungsdatum"), b.get("bezahlt_am")]))
    for nr, b in EigenbelegStore._falte(e).items():
        add("eigenbelege", 1 if b.get("status") != "storniert" else 3, b.get("datum"), f"{nr} · {b.get('text', '')[:60]}",
            " · ".join(x for x in (_eur(b.get("betrag_cent")), b.get("art")) if x), "eb-detail", nr,
            _suchtext(nr, b.get("text"), b.get("art"), b.get("kategorie"), fname(b.get("firma")), betraege=[b.get("betrag_cent")],
                      daten=[b.get("datum")]))
    from .contentplan import FORMATE, KANAELE, STATUS as CP_STATUS
    cp_info = lambda p: " · ".join(x for x in (KANAELE.get(p.get("kanal"), ""), FORMATE.get(p.get("format"), ""), CP_STATUS.get(p.get("status"), "")) if x)
    plan, anlaesse = ContentPlan._falte(e)
    for p in plan.values():
        add("contentplan", 1, p.get("datum"), p.get("titel", ""), cp_info(p),
            "cp-suche", p.get("datum", ""), _suchtext(p.get("titel"), p.get("notiz"), p.get("kanal"), p.get("format"), fname(p.get("kunde")),
                                                     daten=[p.get("datum")]))
    for s in ContentPlan._serien(e).values():
        add("contentplan", 1, s.get("start"), f"🔁 {s.get('titel', '')}", f"Serie ab {_datum(s.get('start')).split(' ')[1] if s.get('start') else ''}",
            "cp-suche", s.get("start", ""), _suchtext(s.get("titel"), s.get("notiz"), s.get("kanal"), s.get("format"), "serie",
                                                     daten=[s.get("start")]))
    for a in anlaesse.values():
        add("contentplan", 2, a.get("von"), f"📌 {a.get('titel', '')}", "Anlass", "cp-suche", a.get("von", ""),
            _suchtext(a.get("titel"), a.get("notiz"), daten=[a.get("von"), a.get("bis")]))
    for v, m in KonzeptStore._falte(e).items():
        ideen = " ".join(f"{i.get('titel', '')} {i.get('beschreibung', '')}" for i in (m.get("ideen") or {}).values())
        skripte = " ".join(f"{s.get('hook', '')} {s.get('text', '')}" for s in (m.get("skripte") or {}).values())
        add("konzepte", 1, m.get("geaendert"), f"Konzept {v}", (m.get("briefing") or {}).get("ziel", "")[:80], "konzept", v,
            _suchtext(v, " ".join(str(x) for x in (m.get("briefing") or {}).values()), ideen, skripte, (m.get("dreh") or {}).get("ort")))
    docs, offen = akte_falte(e)
    for d in docs.values():
        add("akte", 1, d.get("datum"), d.get("titel", ""), " · ".join(x for x in (fname(d.get("firma")), d.get("mail_von"), d.get("bezug")) if x),
            "kunde-detail", d.get("firma", ""), _suchtext(d.get("titel"), d.get("mail_von"), d.get("notiz"), d.get("bezug"),
                                                         fname(d.get("firma")), daten=[d.get("datum")]))
    out = []
    for g, (titel, _) in GRUPPEN.items():
        liste = sorted(gruppen[g], key=lambda x: (x[0], [-ord(c) for c in x[1]]))
        if liste:
            out.append({"id": g, "titel": titel, "anzahl": len(liste), "treffer": [x[2] for x in liste[:MAX_JE_GRUPPE]]})
    return {"q": q, "gruppen": out, "gesamt": sum(x["anzahl"] for x in out)}
