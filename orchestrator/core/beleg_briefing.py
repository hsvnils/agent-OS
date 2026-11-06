"""Belege im Briefing (CEO 2026-11-06): was seit dem letzten Briefing ankam und wer es gebucht hat.

Je Beleg eine Zeile: **von wem** (Lieferant), **wie hoch** (Betrag), **Status** (gebucht -- von LUNA oder vom CEO --
oder was der CEO noch von Hand tun muss). Dazu automatisch gebuchte Abos (Eigenbelege von LUNA) und Mails mit
Rechnungswort, die als Brief in der Firmenakte gelandet sind (Sicherheitsnetz, Fall WISO 2026-11-04).
Rein regelbasiert aus dem Kassenbuch, kein LLM.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .beleg_pdf import cent, eur
from .eingangsbelege import _BELEG_WORT, EingangStore


def vorheriges_briefing(jetzt: datetime, stunden: list[int]) -> datetime:
    """Zeitpunkt des letzten planmaessigen Briefings vor `jetzt` (z. B. 20:00 gestern fuer das Morgen-Briefing)."""
    jetzt = jetzt.replace(tzinfo=None, minute=0, second=0, microsecond=0)
    kandidaten = [(jetzt - timedelta(days=d)).replace(hour=h) for d in (0, 1) for h in stunden]
    frueher = [k for k in kandidaten if k < jetzt]
    return max(frueher) if frueher else jetzt - timedelta(hours=12)


def _zeit(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts)).replace(tzinfo=None)
    except ValueError:
        return None


def _wer(von: str) -> str:
    von = str(von or "")
    if von.startswith("LUNA-OS:"):
        name = von.split(":", 1)[1]
        return "von dir" if name.lower() == "ceo" else f"von {name}"
    if von.upper().endswith(":CEO"):
        return "von dir"
    return "von LUNA" if von.startswith("LUNA") else (f"von {von}" if von else "")


def _betrag(x: dict) -> str:
    f, v = x.get("felder") or {}, x.get("vorschlag") or {}
    if f.get("betrag_cent") is not None:
        return eur(f["betrag_cent"])
    if v.get("betrag"):
        try:
            return eur(cent(v["betrag"]))
        except ValueError:
            pass
    if v.get("betrag_fremd"):
        return f"{v['betrag_fremd']} {v.get('waehrung', '')}".strip()
    return "Betrag nicht erkannt"


def _tag(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}." if len(iso or "") >= 10 else ""


def zeilen(eintraege: list[dict], seit: datetime) -> list[str]:
    """Briefing-Zeilen fuer alles ab `seit` (naive lokale Zeit)."""
    out = []
    belege = EingangStore._falte(eintraege)
    beleg_mails = {x.get("mail_id") for x in belege.values() if x.get("mail_id")}
    for x in belege.values():
        rein, gebucht = _zeit(x.get("eingegangen", "")), _zeit(x.get("gebucht_am", ""))
        if not ((rein and rein >= seit) or (gebucht and gebucht >= seit)):
            continue
        f, v = x.get("felder") or {}, x.get("vorschlag") or {}
        wer = (f.get("lieferant") or v.get("lieferant") or v.get("absender") or x.get("dateiname") or "Unbekannt")[:60]
        kopf = f"{wer} – {_betrag(x)}"
        if x["status"] == "gebucht":
            von = next((s["von"] for s in reversed(x.get("verlauf") or []) if s.get("typ") == "eingang_gebucht"), "")
            z = v.get("zahlung") or {}
            zahl = (f"bezahlt {_tag(x['bezahlt_am'])}" if x.get("bezahlt_am")
                    else f"Lastschrift am {_tag(z['datum'])} – Zahlung ab dann bitte erfassen"
                    if z.get("status") == "lastschrift" and z.get("datum")
                    else "teilweise bezahlt – Rest bitte erfassen" if x.get("bezahlt_cent")
                    else "Zahlung noch offen – bitte bezahlen bzw. erfassen")
            out.append(f"✅ {kopf} → gebucht {_wer(von)} · {zahl} ({x['nummer']})")
        elif x["status"] == "verworfen":
            out.append(f"🗑 {kopf} → verworfen{': ' + x['grund'][:60] if x.get('grund') else ''} ({x['nummer']})")
        else:
            z = v.get("zahlung") or {}
            extra = ("; laut Beleg schon bezahlt" if z.get("status") == "bezahlt"
                     else f"; Lastschrift am {_tag(z['datum'])}" if z.get("status") == "lastschrift" and z.get("datum")
                     else "")
            if v.get("waehrung") and v.get("waehrung") != "EUR" and not v.get("betrag"):
                extra += "; Euro-Betrag vom Konto nachtragen"
            out.append(f"⚠️ {kopf} → noch NICHT gebucht – bitte in LUNA-OS prüfen und buchen{extra} ({x['nummer']})")
    for e in eintraege:
        t, d, ts = e.get("typ"), e.get("daten") or {}, _zeit(e.get("ts", ""))
        if not ts or ts < seit:
            continue
        if t == "eigenbeleg_angelegt" and _wer(e.get("von", "")) == "von LUNA":   # nicht „LUNA-OS:ceo“
            out.append(f"✅ {(d.get('gegenpartei') or d.get('text') or 'Abo')[:60]} – {eur(d.get('betrag_cent') or 0)} "
                       f"→ automatisch gebucht von LUNA ({d.get('nummer', '')})")
        elif (t == "akte_mail_offen" and _BELEG_WORT.search(str(d.get("titel", "")))
              and d.get("mail_id") not in beleg_mails):                     # inzwischen doch als Beleg erfasst
            von = re.sub(r"@.*", "", str(d.get("mail_von") or "")) or "unbekannt"
            out.append(f"⚠️ Mail „{str(d.get('titel', ''))[:70]}“ ({von}) → als Brief in der Akte, nicht als Beleg – "
                       f"bitte prüfen ({d.get('id', '')})")
    return out


def text(eintraege: list[dict], seit: datetime, *, max_zeilen: int = 15) -> str:
    alle = zeilen(eintraege, seit)
    if not alle:
        return ""
    offen = sum(1 for x in alle if "bitte" in x)
    z = sorted(alle, key=lambda x: "bitte" not in x)[:max_zeilen]               # zu tun zuerst
    if len(alle) > len(z):
        z.append(f"… und {len(alle) - len(z)} weitere (LUNA-OS → Belege)")
    fuss = f"\nVon Hand zu tun: {offen} {'Punkt' if offen == 1 else 'Punkte'}." if offen else "\nAlles gebucht und bezahlt, nichts zu tun."
    return f"📥 Belege seit dem letzten Briefing ({len(alle)}):\n" + "\n".join(f"  - {x}" for x in z) + fuss
