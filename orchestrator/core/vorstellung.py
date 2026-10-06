"""SERIEN_UND_VORSTELLUNG V1/V2: Vorstellungs-Mails an Unternehmen aus LUNA-OS.

- **V1 Senden in einem Schritt:** Empfaenger ist eine vorhandene Firma oder Name + Mailadresse; nach erfolgreichem Versand
  (ueber den Kundenversand, heute luna@hanserautisch.de) wird eine neue Firma als **Interessent** angelegt, die Mail (.eml)
  liegt in der Firmenakte und die Kennung im Ereignis `vorstellung_gesendet` -- so erkennt `core/mail_antworten.py`
  die Antwort und meldet sie. Senden nur nach Klick (Oeffentlichkeit = CEO-Tor).
- **Recht:** § 7 Abs. 2 UWG -- Werbung per Mail braucht grundsaetzlich eine vorherige Einwilligung, auch gegenueber
  Unternehmen. CEO-Entscheidung 2026-10-06: nur Hinweis im Dialog, Anlass optional als Nachweis.
- **V2 Ueberblick:** wer wann angeschrieben wurde, Antwort ja/nein, Nachfassen faellig nach `NACHFASSEN_TAGE` ohne Antwort
  (Handlungsbedarf), „Kein Interesse“ schliesst ab (`vorstellung_erledigt`).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

NACHFASSEN_TAGE = 7
ANLAESSE = {"anfrage": "Anfrage der Firma", "einwilligung": "Einwilligung (z. B. Visitenkarte, Gespräch)",
            "kontakt": "Antwort auf deren Kontakt", "bestand": "Bestehende Geschäftsbeziehung", "sonstiges": "Sonstiges"}
HINWEIS_UWG = ("Werbung per E-Mail braucht in Deutschland grundsätzlich eine vorherige Einwilligung – auch gegenüber "
               "Unternehmen (§ 7 Abs. 2 UWG). Reine Kaltakquise ist abmahnfähig. Vermerke den Anlass, wenn es einen gibt.")
_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FREEMAIL = ("gmail.com", "googlemail.com", "gmx.de", "gmx.net", "web.de", "t-online.de", "outlook.com", "hotmail.com",
            "icloud.com", "me.com", "yahoo.com", "yahoo.de", "aol.com", "posteo.de", "mail.de", "freenet.de")


def werte(firma: dict, ap: dict | None, katalog_texte: dict | None, *, gesendet_am: str = "") -> dict:
    from .textbausteine import anrede_werte
    t = katalog_texte or {}
    link = t.get("praesentation_de") or ""
    w = anrede_werte(ap) | {"kunde": (firma or {}).get("name", ""),
                            "praesentation": f"{t.get('praesentation_text_de') or 'Unsere Präsentation'}: {link}" if link else ""}
    if gesendet_am:
        w["gesendet_am"] = f"{gesendet_am[8:10]}.{gesendet_am[5:7]}.{gesendet_am[:4]}"
    return w


def _domain(mail: str) -> str:
    return (mail or "").rsplit("@", 1)[-1].strip().lower()


def dubletten(kunden, name: str, mail: str) -> list[str]:
    """Gleicher Name oder gleiche (nicht Freemail-)Domain bei Ansprechpartnern/Rechnungsmail einer vorhandenen Firma."""
    from .kunden import _key
    dom = _domain(mail)
    out = []
    for f in kunden.firmen():
        voll = kunden.firma(f["nummer"]) or f
        adressen = [voll.get("rechnungsmail") or ""] + [a.get("mail") or "" for a in voll.get("ansprechpartner_liste") or []]
        if (name and _key(f["name"]) == _key(name)) or (dom and dom not in FREEMAIL and any(_domain(a) == dom for a in adressen if a)):
            out.append(f["nummer"])
    return out


def _ereignisse(eintraege: list[dict]) -> dict:
    """{firma: {gesendet: [...], erledigt: {...}|None, antworten: [...]}}"""
    out: dict = {}
    for e in eintraege:
        d, t = e["daten"], e["typ"]
        if t == "vorstellung_gesendet":
            out.setdefault(d["nummer"], {"gesendet": [], "erledigt": None, "antworten": []})["gesendet"].append(d | {"ts": e["ts"]})
        elif t == "vorstellung_erledigt" and d.get("nummer") in out:
            out[d["nummer"]]["erledigt"] = d | {"ts": e["ts"]}
        elif t == "mail_antwort" and str(d.get("nummer", "")).startswith("K-"):
            out.setdefault(d["nummer"], {"gesendet": [], "erledigt": None, "antworten": []})["antworten"].append(d | {"ts": e["ts"]})
    return {k: v for k, v in out.items() if v["gesendet"]}


def senden(bh, kunden, versand, daten: dict, *, absender_name: str, eigene: list[str], von: str = "") -> dict:
    """Vorstellungs- bzw. Nachfass-Mail senden (nur mit Bestaetigung). Neue Firma erst NACH erfolgreichem Versand anlegen."""
    from .firmenakte import Firmenakte
    from .kunden import DubletteFehler
    if (daten or {}).get("bestaetigt") is not True:
        raise ValueError("Senden braucht die ausdrueckliche Bestaetigung.")
    an = str(daten.get("an") or "").strip()
    betreff, text = str(daten.get("betreff") or "").strip(), str(daten.get("text") or "").strip()
    if not _MAIL.match(an) or not betreff or not text:
        raise ValueError("Empfaenger (gueltige Mailadresse), Betreff und Text sind Pflicht.")
    anlass = str(daten.get("anlass") or "").strip()
    if anlass and anlass not in ANLAESSE:
        raise ValueError("Unbekannter Anlass.")
    nr = str(daten.get("firma") or "").strip().upper()
    neu = daten.get("neu") or {}
    if nr:
        if not kunden.firma(nr):
            raise KeyError(nr)
    else:
        name = str(neu.get("name") or "").strip()
        if not name:
            raise ValueError("Firmenname fehlt.")
        gleich = dubletten(kunden, name, an)
        if gleich and not daten.get("trotz_dublette"):
            raise DubletteFehler(f"Diese Firma gibt es vermutlich schon ({', '.join(gleich)}) – bitte aus der Liste waehlen.", gleich)
    s = versand.mail_senden(an, betreff, text, bestaetigt=True, absender_name=absender_name)
    if not s.get("ok"):
        raise ValueError(s.get("hinweis") or "Senden fehlgeschlagen.")
    angelegt = False
    if not nr:
        firma = {"name": str(neu["name"]).strip(), "typ": "interessent", "notiz": f"Vorstellung per Mail an {an}"}
        if neu.get("website"):
            firma["website"] = str(neu["website"]).strip()
        nr = kunden.firma_anlegen(firma, von=von, trotz_dublette=True)["nummer"]
        angelegt = True
        if str(neu.get("vorname") or "").strip() or str(neu.get("nachname") or "").strip():
            kunden.ansprechpartner_anlegen(nr, {"vorname": neu.get("vorname") or "", "nachname": neu.get("nachname") or "",
                                                "mail": an}, von=von)
    akte = ""
    roh = versand.mail_roh(s["id"]) if s.get("id") and hasattr(versand, "mail_roh") else {}
    if roh.get("ok"):
        akte = Firmenakte(bh, kunden).mail_aufnehmen(roh["roh"], s["id"], eigene=eigene, weitergeleitet=False, von=von,
                                                     firma=nr)["id"]
    bh.erfassen("vorstellung_gesendet", {"nummer": nr, "message_id": s.get("id", ""), "kanal": s.get("kanal", "gmail"),
                                         "an": an, "betreff": betreff[:200], "anlass": anlass,
                                         "anlass_notiz": str(daten.get("anlass_notiz") or "").strip()[:300],
                                         "nachfassen": bool(daten.get("nachfassen")), "akte_id": akte}, von=von)
    return {"firma": nr, "neu_angelegt": angelegt, "an": an}


def erledigt(bh, nummer: str, grund: str = "", *, von: str = "") -> dict:
    nummer = (nummer or "").strip().upper()
    if nummer not in _ereignisse(bh.eintraege()):
        raise KeyError(nummer)
    bh.erfassen("vorstellung_erledigt", {"nummer": nummer, "grund": str(grund or "kein Interesse").strip()[:300]}, von=von)
    return {"nummer": nummer}


def liste(bh, kunden, heute: date) -> list[dict]:
    out = []
    for nr, x in _ereignisse(bh.eintraege()).items():
        f = kunden.firma(nr) or {}
        g = sorted(x["gesendet"], key=lambda y: y["ts"])
        erste, letzte = g[0], g[-1]
        antwort = [a for a in x["antworten"] if a["ts"] >= erste["ts"]]
        seit = date.fromisoformat(letzte["ts"][:10])
        faellig_am = (seit + timedelta(days=NACHFASSEN_TAGE)).isoformat()
        offen = not antwort and not x["erledigt"] and f.get("typ", "interessent") == "interessent"
        out.append({"firma": nr, "name": f.get("name", nr), "typ": f.get("typ", ""), "an": letzte["an"],
                    "erste": erste["ts"], "letzte": letzte["ts"], "anzahl": len(g), "nachgefasst": sum(1 for y in g if y.get("nachfassen")),
                    "anlass": erste.get("anlass", ""), "antwort": antwort[-1]["ts"] if antwort else "",
                    "antwort_von": antwort[-1].get("von", "") if antwort else "", "erledigt": (x["erledigt"] or {}).get("grund", ""),
                    "nachfassen_faellig": offen and faellig_am <= heute.isoformat(), "faellig_am": faellig_am if offen else ""})
    return sorted(out, key=lambda y: y["letzte"], reverse=True)


def todos(bh, kunden, heute: date) -> list[dict]:
    """Handlungsbedarf: nach NACHFASSEN_TAGE ohne Antwort nachfassen (oder „Kein Interesse“)."""
    return [{"id": f"vorstellung:{x['firma']}", "bereich": "Kunden", "icon": "✉️", "titel": f"Nachfassen: {x['name']}",
             "detail": f"Vorstellung vom {x['letzte'][8:10]}.{x['letzte'][5:7]}. ohne Antwort", "act": "vs-neu",
             "act_id": x["firma"], "faellig": x["faellig_am"], "dringend": False, "stufe": "woche",
             "erledigen": {"pfad": f"/api/crm/vorstellungen/{x['firma']}/erledigt", "label": "Kein Interesse"}}
            for x in liste(bh, kunden, heute) if x["nachfassen_faellig"]]
