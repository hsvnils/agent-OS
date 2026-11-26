"""OFC_TICKETVERSAND TV3: Zahlungsbitte per Mail aus moin@hsvinside.de (CEO-Go 2026-11-26).

Regeln (CEO E1-E7, CISO TV3):
- Je **Mitglied und Spiel** eine Mail. „Mitglied“ ist die am Ticket gemerkte Nummer = wer zahlt (Gaeste traegt der CEO unter
  dem Mitglied ein, das sie mitbringt). Die Adresse kommt aus der Mitgliederliste (nur lesend) ueber die Nummer.
- Verwendungszweck `<Spieltag>-<Mitgliedsnummer>` (E2), Zahlweg PayPal an moin@hsvinside.de (kein PayPal.me, CEO).
- Nur nach CEO-Klick mit Bestaetigung; **nie doppelt** fuer dieselben Karten ohne „erneut“; Testmail geht an moin@ selbst.
- Hoechstens `LIMIT_STUNDE` Mails je Stunde. Feste Vorlage, keine KI. Protokoll `ofc_mail` ohne Mailtext, Adresse maskiert.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from .ofc_spielplan import kennung as _kennung

PAYPAL = "moin@hsvinside.de"
LIMIT_STUNDE = 30
ABSENDER_NAME = "HSVInside"


def _euro(cent: int) -> str:
    return f"{cent / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _datum(d: str) -> str:
    return f"{d[8:10]}.{d[5:7]}.{d[:4]}" if len(d or "") >= 10 else ""


def maskiert(adresse: str) -> str:
    lokal, _, dom = (adresse or "").partition("@")
    return (lokal[:1] + "…@" + dom) if dom else ""


def _mitglieder_je_nummer(mitglieder: list[dict] | None) -> dict:
    je: dict = {}
    for m in mitglieder or []:
        if m.get("nummer"):
            je.setdefault(str(m["nummer"]), []).append(m)
    return je


def _platz(t: dict) -> str:
    return ", ".join(x for x in (f"Block {t['block']}" if t.get("block") else "",
                                 f"Reihe {t['reihe']}" if t.get("reihe") and t["reihe"] != "-" else "",
                                 f"Sitz {t['sitz']}" if t.get("sitz") and t["sitz"] != "-" else "") if x)


def _gesendet(st: dict) -> list[dict]:
    return [m for m in (st.get("mails") or {}).values() if m.get("status") == "gesendet"]


def plan(st: dict, sid: str, mitglieder: list[dict] | None) -> dict:
    """Je Mitglied mit unbezahlten Karten in diesem Spiel: Betrag, Verwendungszweck, Adresse (maskiert), Status."""
    from .ofc_eingang import bezahlt_stand
    s = st["spiele"].get(sid)
    if not s:
        return {"ok": False, "hinweis": "Spiel nicht gefunden."}
    kn = _kennung(s)["kennung"]
    bz = bezahlt_stand(st)["tickets"]
    je_nr = _mitglieder_je_nummer(mitglieder)
    for pid, pe in (st.get("personen") or {}).items():              # TV3b: externe Personen G<Nr>
        je_nr[pid] = [{"nummer": pid, "vorname": pe.get("vorname", ""), "name": f"{pe.get('vorname', '')} {pe.get('nachname', '')}".strip(),
                       "email": pe.get("email", ""), "extern": True}]
    gruppen: dict = {}
    ohne = 0
    for t in st["tickets"].values():
        if t.get("spiel") != sid:
            continue
        b = bz.get(t["ticketnr"], {})
        if b.get("bezahlt"):
            continue
        nr = (t.get("mitglied") or "").strip()
        if not nr:
            ohne += 1
            continue
        g = gruppen.setdefault(nr, {"nummer": nr, "tickets": [], "betrag_cent": 0})
        g["tickets"].append({"ticketnr": t["ticketnr"], "name": t.get("name", ""), "platz": _platz(t),
                             "preis_cent": t.get("preis_cent") or 0})
        g["betrag_cent"] += max(0, (t.get("preis_cent") or 0) - (b.get("bezahlt_cent") or 0))
    frueher = _gesendet(st)
    out = []
    for nr, g in sorted(gruppen.items(), key=lambda x: x[0].zfill(8)):
        ms = je_nr.get(nr, [])
        m = ms[0] if len(ms) == 1 else None
        g["tickets"].sort(key=lambda x: x["ticketnr"])
        g["vorname"] = (m or {}).get("vorname", "") or ((m or {}).get("name", "").split(" ")[0] if m else "")
        g["name"] = (m or {}).get("name", "")
        adresse = ((m or {}).get("email") or "").strip()
        g["adresse_maskiert"] = maskiert(adresse)
        g["verwendungszweck"] = f"{kn}-{nr}" if kn else ""
        nrn = {x["ticketnr"] for x in g["tickets"]}
        alt = [x for x in frueher if x.get("art") == "zahlungsbitte" and x.get("spiel") == sid and x.get("nummer") == nr
               and not x.get("test") and set(x.get("tickets") or []) >= nrn]
        g["gebeten_am"] = max((x.get("ts", "") for x in alt), default="")
        g["extern"] = bool(m and m.get("extern"))
        if mitglieder is None and not g["extern"]:
            g["status"], g["hinweis"] = "gesperrt", "Mitgliederliste nicht lesbar."
        elif not m:
            g["status"], g["hinweis"] = "gesperrt", ("Mitgliedsnummer mehrfach in der Liste." if len(ms) > 1 else "Mitgliedsnummer nicht in der Liste.")
        elif "@" not in adresse:
            g["status"], g["hinweis"] = "gesperrt", ("Keine E-Mail-Adresse eingetragen." if g["extern"] else "Keine E-Mail-Adresse in der Mitgliederliste.")
        elif not kn:
            g["status"], g["hinweis"] = "gesperrt", "Spieltag fehlt – im Spiel bei ✏️ eintragen."
        elif not g["betrag_cent"]:
            g["status"], g["hinweis"] = "gesperrt", "Kein Betrag offen."
        else:
            g["status"], g["hinweis"] = ("gebeten" if g["gebeten_am"] else "bereit"), ""
        out.append(g)
    return {"ok": True, "spiel": sid, "kennung": kn, "gruppen": out, "ohne_mitglied": ohne,
            "bereit": sum(1 for g in out if g["status"] == "bereit")}


def text(s: dict, g: dict) -> tuple[str, str]:
    """Feste Vorlage (keine KI). -> (Betreff, Text)."""
    tag, zeit = _datum(s.get("spieltag", "")), s.get("uhrzeit", "")
    spiel = s.get("spiel", "")
    karten = "\n".join(f"- {x['platz'] or 'Karte'}{' – ' + x['name'] if x['name'] else ''} – {_euro(x['preis_cent'])}"
                       for x in g["tickets"])
    betreff = f"HSVInside: Bitte um Zahlung – {spiel}" + (f" ({tag})" if tag else "")
    t = (f"Moin {g.get('vorname') or ''},\n\n".replace(" ,", ",")
         + f"für das Spiel {spiel}" + (f" am {tag}" if tag else "") + (f" um {zeit} Uhr" if zeit else "")
         + f" hast du über deinen Fanclub HSVInside {'diese Karte' if len(g['tickets']) == 1 else 'diese Karten'}:\n{karten}\n\n"
         + f"Bitte zahle {_euro(g['betrag_cent'])} per PayPal an {PAYPAL}.\n"
         + f"Verwendungszweck: {g['verwendungszweck']}\n\n"
         + "Bitte gib genau diesen Verwendungszweck an – so können wir deine Zahlung sofort zuordnen. "
         + "Sobald sie da ist, schicken wir dir die Tickets (PDF und Wallet).\n\n"
         + "Viele Grüße\nHSVInside – Offizieller Fanclub des Hamburger SV\n")
    return betreff, t


def _letzte_stunde(st: dict, jetzt: datetime) -> int:
    grenze = (jetzt - timedelta(hours=1)).isoformat(timespec="seconds")
    return sum(1 for m in _gesendet(st) if (m.get("ts") or "") >= grenze)


def vorschau(st: dict, sid: str, nummer: str, mitglieder: list[dict] | None) -> dict:
    p = plan(st, sid, mitglieder)
    if not p["ok"]:
        return p
    g = next((x for x in p["gruppen"] if x["nummer"] == nummer), None)
    if not g:
        return {"ok": False, "hinweis": "Für dieses Mitglied ist in diesem Spiel nichts offen."}
    betreff, t = text(st["spiele"][sid], g)
    return {"ok": True, "gruppe": g, "betreff": betreff, "text": t}


def senden(store, postfach, sid: str, nummer: str, mitglieder: list[dict] | None, *, test: bool = False,
           erneut: bool = False, von: str = "", jetzt: datetime | None = None) -> dict:
    """Eine Zahlungsbitte senden (nach CEO-Bestaetigung im Endpunkt). Testmail geht an moin@ selbst, Betreff mit [TEST]."""
    jetzt = jetzt or datetime.now(timezone.utc)
    st = store.stand()
    v = vorschau(st, sid, nummer, mitglieder)
    if not v["ok"]:
        return v
    g = v["gruppe"]
    if g["status"] == "gesperrt":
        return {"ok": False, "hinweis": g["hinweis"]}
    if g["status"] == "gebeten" and not erneut and not test:
        return {"ok": False, "hinweis": f"Schon am {g['gebeten_am'][:10]} gebeten – zum erneuten Senden „erneut“ wählen."}
    if _letzte_stunde(st, jetzt) >= LIMIT_STUNDE:
        return {"ok": False, "hinweis": f"Höchstens {LIMIT_STUNDE} Mails je Stunde – bitte später weiter."}
    pe = (st.get("personen") or {}).get(nummer)
    m = {"email": pe.get("email", "")} if pe else next((x for x in mitglieder or [] if str(x.get("nummer")) == nummer), {})
    an = PAYPAL if test else (m.get("email") or "").strip()
    betreff = ("[TEST] " if test else "") + v["betreff"]
    r = postfach.mail_senden(an, betreff, v["text"], bestaetigt=True, absender_name=ABSENDER_NAME, ofc_freigabe=True)
    mid = "M-" + uuid.uuid4().hex[:10]
    store.erfassen("ofc_mail", {"id": mid, "art": "zahlungsbitte", "spiel": sid, "nummer": nummer,
                                "tickets": [x["ticketnr"] for x in g["tickets"]], "betrag_cent": g["betrag_cent"],
                                "verwendungszweck": g["verwendungszweck"], "an": maskiert(an), "test": test,
                                "status": "gesendet" if r.get("ok") else "fehler", "message_id": r.get("message_id", ""),
                                "hinweis": "" if r.get("ok") else str(r.get("hinweis", ""))[:200]}, von=von)
    if not r.get("ok"):
        return {"ok": False, "hinweis": r.get("hinweis") or "Senden fehlgeschlagen."}
    return {"ok": True, "an": maskiert(an), "test": test, "verwendungszweck": g["verwendungszweck"],
            "gesendet_ordner": r.get("gesendet_ordner", "")}


# -- TV4: Tickets nach Zahlung senden (PDF als Anhang + Wallet-Links) --------------------------------------------------
AUTO_TAGE = 14                                            # Auto-Versand nur fuer Zahlungen der letzten 14 Tage


def auto_an(env=None) -> bool:
    """Auto-Versand nur mit `OFC_AUTO_TICKETVERSAND=1` (CEO E5: erst nach der Abnahme einschalten)."""
    import os
    return ((env if env is not None else os.environ).get("OFC_AUTO_TICKETVERSAND") or "0").strip().lower() in ("1", "ja", "an", "true")


def _ticket_gesendet(st: dict) -> dict:
    """ticketnr -> Zeitpunkt der letzten echten Ticketmail."""
    out: dict = {}
    for m in _gesendet(st):
        if m.get("art") == "tickets" and not m.get("test"):
            for nr in m.get("tickets") or []:
                out[nr] = max(out.get(nr, ""), m.get("ts", ""))
    return out


def tickets_plan(st: dict, sid: str, mitglieder: list[dict] | None) -> dict:
    """Je Person: bezahlte Karten dieses Spiels mit Status bereit/gesendet/gesperrt (PDF, Wallet, Adresse)."""
    from .ofc_eingang import bezahlt_stand
    s = st["spiele"].get(sid)
    if not s:
        return {"ok": False, "hinweis": "Spiel nicht gefunden."}
    bz = bezahlt_stand(st)["tickets"]
    gesendet = _ticket_gesendet(st)
    je_nr = _mitglieder_je_nummer(mitglieder)
    for pid, pe in (st.get("personen") or {}).items():
        je_nr[pid] = [{"nummer": pid, "vorname": pe.get("vorname", ""), "name": f"{pe.get('vorname', '')} {pe.get('nachname', '')}".strip(),
                       "email": pe.get("email", ""), "extern": True}]
    gruppen: dict = {}
    for t in st["tickets"].values():
        nr = (t.get("mitglied") or "").strip()
        if t.get("spiel") != sid or not nr or not bz.get(t["ticketnr"], {}).get("bezahlt"):
            continue
        g = gruppen.setdefault(nr, {"nummer": nr, "tickets": []})
        g["tickets"].append({"ticketnr": t["ticketnr"], "name": t.get("name", ""), "platz": _platz(t), "datei": t.get("datei", ""),
                             "wallet": t.get("wallet", ""), "gesendet_am": gesendet.get(t["ticketnr"], "")})
    out = []
    for nr, g in sorted(gruppen.items(), key=lambda x: x[0].zfill(8)):
        ms = je_nr.get(nr, [])
        m = ms[0] if len(ms) == 1 else None
        g["tickets"].sort(key=lambda x: x["ticketnr"])
        g["name"], g["vorname"] = (m or {}).get("name", ""), (m or {}).get("vorname", "") or ((m or {}).get("name", "").split(" ")[0] if m else "")
        g["extern"] = bool(m and m.get("extern"))
        g["adresse_maskiert"] = maskiert((m or {}).get("email", ""))
        offen = [x for x in g["tickets"] if not x["gesendet_am"]]
        g["gesendet_am"] = max((x["gesendet_am"] for x in g["tickets"]), default="")
        fehlt = [h for h, ok in (("PDF fehlt", all(x["datei"] for x in offen)), ("Wallet fehlt", all(x["wallet"] for x in offen))) if not ok]
        if not offen:
            g["status"], g["hinweis"] = "gesendet", ""
        elif not m or "@" not in (m.get("email") or ""):
            g["status"], g["hinweis"] = "gesperrt", "Keine E-Mail-Adresse."
        elif "PDF fehlt" in fehlt:
            g["status"], g["hinweis"] = "gesperrt", "PDF-Ticket fehlt im Ordner."
        else:
            g["status"], g["hinweis"] = "bereit", ("Wallet-Link fehlt – nur PDF." if fehlt else "")
        g["offen"] = [x["ticketnr"] for x in offen]
        out.append(g)
    return {"ok": True, "spiel": sid, "gruppen": out, "bereit": sum(1 for g in out if g["status"] == "bereit")}


def tickets_text(s: dict, g: dict, tickets: list[dict]) -> tuple[str, str]:
    """Feste Vorlage (keine KI). -> (Betreff, Text)."""
    tag, zeit = _datum(s.get("spieltag", "")), s.get("uhrzeit", "")
    spiel = s.get("spiel", "")
    zeilen = "\n".join(f"- {x['platz'] or 'Karte'}{' – ' + x['name'] if x['name'] else ''}"
                       + (f"\n  Wallet (Apple/Google): {x['wallet']}" if x.get("wallet") else "") for x in tickets)
    betreff = f"HSVInside: Deine Tickets – {spiel}" + (f" ({tag})" if tag else "")
    t = (f"Moin {g.get('vorname') or ''},\n\n".replace(" ,", ",")
         + f"danke für deine Zahlung! Hier {'ist deine Karte' if len(tickets) == 1 else 'sind deine Karten'} für {spiel}"
         + (f" am {tag}" if tag else "") + (f" um {zeit} Uhr" if zeit else "") + ":\n\n" + zeilen + "\n\n"
         + "Die PDF-Tickets hängen an dieser Mail. Für das Handy-Wallet den Link auf dem Handy öffnen.\n\n"
         + "Viel Spaß im Stadion!\nHSVInside – Offizieller Fanclub des Hamburger SV\n")
    return betreff, t


def tickets_vorschau(st: dict, sid: str, nummer: str, mitglieder: list[dict] | None) -> dict:
    p = tickets_plan(st, sid, mitglieder)
    if not p["ok"]:
        return p
    g = next((x for x in p["gruppen"] if x["nummer"] == nummer), None)
    if not g:
        return {"ok": False, "hinweis": "Für diese Person gibt es in diesem Spiel keine bezahlten Karten."}
    tks = [x for x in g["tickets"] if x["ticketnr"] in g["offen"]] or g["tickets"]
    betreff, t = tickets_text(st["spiele"][sid], g, tks)
    return {"ok": True, "gruppe": g, "betreff": betreff, "text": t, "tickets": [x["ticketnr"] for x in tks],
            "anhaenge": [x["datei"] for x in tks if x["datei"]]}


def tickets_senden(store, postfach, sid: str, nummer: str, mitglieder: list[dict] | None, *, test: bool = False,
                   erneut: bool = False, auto: bool = False, von: str = "", jetzt: datetime | None = None) -> dict:
    """Ticketmail mit PDF-Anhaengen und Wallet-Links. Ohne „erneut“ nur Karten, die noch nicht gesendet wurden."""
    from .ofc_store import datei_pfad
    jetzt = jetzt or datetime.now(timezone.utc)
    st = store.stand()
    v = tickets_vorschau(st, sid, nummer, mitglieder)
    if not v["ok"]:
        return v
    g = v["gruppe"]
    if g["status"] == "gesperrt":
        return {"ok": False, "hinweis": g["hinweis"]}
    if g["status"] == "gesendet" and not erneut and not test:
        return {"ok": False, "hinweis": f"Tickets schon am {g['gesendet_am'][:10]} gesendet – zum erneuten Senden „erneut“ wählen."}
    if auto and (g["hinweis"] or not g["offen"]):
        return {"ok": False, "hinweis": "Automatisch nur mit PDF und Wallet-Link für alle Karten."}
    if _letzte_stunde(st, jetzt) >= LIMIT_STUNDE:
        return {"ok": False, "hinweis": f"Höchstens {LIMIT_STUNDE} Mails je Stunde – bitte später weiter."}
    anh = []
    for x in g["tickets"]:
        if x["ticketnr"] not in v["tickets"] or not x["datei"]:
            continue
        p = datei_pfad(store, sid, x["datei"])
        if p is None:
            return {"ok": False, "hinweis": f"PDF „{x['datei']}“ nicht gefunden – bitte „Ordner einlesen“."}
        anh.append((p.name, p.read_bytes(), "application/pdf"))
    pe = (st.get("personen") or {}).get(nummer)
    m = {"email": pe.get("email", "")} if pe else next((x for x in mitglieder or [] if str(x.get("nummer")) == nummer), {})
    an = PAYPAL if test else (m.get("email") or "").strip()
    r = postfach.mail_senden(an, ("[TEST] " if test else "") + v["betreff"], v["text"], bestaetigt=True, anhaenge=anh,
                             absender_name=ABSENDER_NAME, ofc_freigabe=True)
    store.erfassen("ofc_mail", {"id": "M-" + uuid.uuid4().hex[:10], "art": "tickets", "spiel": sid, "nummer": nummer,
                                "tickets": v["tickets"], "anhaenge": len(anh), "an": maskiert(an), "test": test, "auto": auto,
                                "status": "gesendet" if r.get("ok") else "fehler", "message_id": r.get("message_id", ""),
                                "hinweis": "" if r.get("ok") else str(r.get("hinweis", ""))[:200]}, von=von)
    if not r.get("ok"):
        return {"ok": False, "hinweis": r.get("hinweis") or "Senden fehlgeschlagen."}
    return {"ok": True, "an": maskiert(an), "test": test, "karten": len(v["tickets"]), "anhaenge": len(anh)}


def auto_lauf(store, postfach, mitglieder: list[dict] | None, *, env=None, heute=None) -> dict:
    """Im 15-Minuten-Lauf: Tickets automatisch senden, wenn eine PayPal-Zahlung per Verwendungszweck zugeordnet wurde
    (Code + genauer Betrag), die Person eine Adresse hat, PDF und Wallet fuer alle Karten da sind und noch nichts
    gesendet wurde. Nur mit `OFC_AUTO_TICKETVERSAND=1`."""
    from datetime import date, timedelta as _td
    if not auto_an(env):
        return {"ok": True, "aus": True, "gesendet": 0}
    heute = heute or date.today()
    grenze = (heute - _td(days=AUTO_TAGE)).isoformat()
    st = store.stand()
    ziele = set()
    for e in (st.get("eingaenge") or {}).values():
        if e.get("zuordnung") != "auto" or not e.get("zweck") or e.get("ersetzt") or (e.get("datum") or "") < grenze:
            continue
        for nr in e.get("tickets") or []:
            t = st["tickets"].get(nr) or {}
            if t.get("mitglied"):
                ziele.add((t["spiel"], t["mitglied"]))
    gesendet, fehler = 0, []
    for sid, nummer in sorted(ziele):
        p = tickets_plan(store.stand(), sid, mitglieder)
        g = next((x for x in p.get("gruppen", []) if x["nummer"] == nummer), None)
        if not g or g["status"] != "bereit" or g["hinweis"]:
            continue
        r = tickets_senden(store, postfach, sid, nummer, mitglieder, auto=True, von="auto")
        if r["ok"]:
            gesendet += 1
        else:
            fehler.append(r.get("hinweis", ""))
    return {"ok": True, "gesendet": gesendet, "fehler": fehler}
