"""Rechtsquellen des CLO aktuell halten (CLO_AUSBAU C2/C3, CEO 2026-10-05: „nachts die Quellen auf Veraenderungen pruefen“).

Die Skills unter `skills/clo/<skill>/quellen.md` enthalten die Kernnormen im Wortlaut (abgerufen von
gesetze-im-internet.de) mit Abrufdatum und Pruefdatum. Der naechtliche Lauf holt jede Norm neu, vergleicht den
**normalisierten Wortlaut** mit dem gespeicherten und meldet Aenderungen sowie ueberschrittene Pruefdaten. Er aendert
**keine** Skills selbst -- eine Gesetzesaenderung kann die Pruef-Checkliste inhaltlich betreffen; nachgezogen wird
bewusst (Skill + quellen.md neu, Commit). Zustand (letzter Lauf, bekannte Abweichungen) in `orchestrator/state/
rechtsquellen.json` (NAS, fluechtig).
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

KOPF = re.compile(r"^## (?P<norm>.+?) -- .*?\nQuelle: (?P<url>https://www\.gesetze-im-internet\.de/\S+) · Stand: (?P<stand>\d{4}-\d{2}-\d{2})\n\n"
                  r"(?P<text>(?:> .*\n?)+)", re.M)
PRUEF = re.compile(r"Naechste Pruefung: (\d{4}-\d{2}-\d{2})")


def normalisieren(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def quellen(skills_dir: Path | str) -> list[dict]:
    """Alle hinterlegten Normen: Skill, Norm, URL, Stand, Pruefdatum, Hash des gespeicherten Wortlauts."""
    out = []
    for q in sorted(Path(skills_dir).glob("*/quellen.md")):
        s = q.read_text(encoding="utf-8")
        pruef = (PRUEF.search(s) or [None, ""])[1]
        for m in KOPF.finditer(s):
            text = "\n".join(z[2:] for z in m["text"].strip("\n").split("\n"))
            out.append({"skill": q.parent.name, "norm": m["norm"].strip(), "url": m["url"], "stand": m["stand"],
                        "pruefen_bis": pruef, "hash": hashlib.sha256(normalisieren(text).encode()).hexdigest()})
    return out


def wortlaut(roh_html: str) -> str:
    """Normtext aus einer Seite von gesetze-im-internet.de (wie beim Abruf fuer quellen.md)."""
    m = re.search(r'<div class="jnhtml">(.*?)</div>\s*</div>', roh_html, re.S)
    if not m:
        raise ValueError("Normtext nicht gefunden (Seitenaufbau geaendert?)")
    t = m.group(1).replace("</div>", "\n").replace("<br>", "\n").replace("</dd>", "\n")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return "\n".join(re.sub(r"[ \t]+", " ", z).strip() for z in t.split("\n") if z.strip())


def _holen(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LUNA Rechtsquellen-Check)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("iso-8859-1", "replace")


def pruefen(skills_dir: Path | str, *, heute: date | None = None, holen=_holen) -> dict:
    """-> {geprueft, geaendert: [...], fehler: [...], faellig: [...]} -- vergleicht jede Norm mit der amtlichen Seite."""
    heute = heute or date.today()
    qs = quellen(skills_dir)
    geaendert, fehler, gesehen = [], [], {}
    for q in qs:
        if q["url"] in gesehen:                           # gleiche Norm in mehreren Skills nur einmal holen
            neu = gesehen[q["url"]]
        else:
            try:
                neu = hashlib.sha256(normalisieren(wortlaut(holen(q["url"]))).encode()).hexdigest()
            except Exception as exc:                      # Netz/Seitenaufbau -- melden, nicht als Aenderung werten
                neu = None
                fehler.append({"norm": q["norm"], "url": q["url"], "fehler": f"{exc.__class__.__name__}: {str(exc)[:80]}"})
            gesehen[q["url"]] = neu
        if neu and neu != q["hash"]:
            geaendert.append({k: q[k] for k in ("skill", "norm", "url", "stand")})
    faellig = sorted({q["skill"] for q in qs if q["pruefen_bis"] and q["pruefen_bis"] <= heute.isoformat()})
    return {"geprueft": len(gesehen), "normen": len(qs), "geaendert": geaendert, "fehler": fehler, "faellig": faellig,
            "datum": heute.isoformat()}


def meldung(erg: dict, bekannt: set[str]) -> str:
    """Telegram-/Briefing-Text nur fuer **neue** Befunde (bekannte nicht jede Nacht wiederholen)."""
    neu = [g for g in erg["geaendert"] if f"{g['norm']}|{g['skill']}" not in bekannt]
    zeilen = [f"• {g['norm']} hat sich geaendert -> Skill „{g['skill']}“ pruefen ({g['url']})" for g in neu]
    zeilen += [f"• Pruefdatum der Quellen erreicht: Skill „{s}“" for s in erg["faellig"] if f"faellig|{s}" not in bekannt]
    if len(erg["fehler"]) >= max(3, erg["geprueft"] // 2):
        zeilen.append(f"• {len(erg['fehler'])} Normen nicht abrufbar (gesetze-im-internet.de erreichbar?)")
    return ("⚖️ CLO-Rechtsquellen:\n" + "\n".join(zeilen)) if zeilen else ""


def lauf(skills_dir: Path | str, zustand: Path | str, notify=None, *, heute: date | None = None, holen=_holen) -> dict:
    """Naechtlicher Lauf: pruefen, neue Befunde melden, Zustand merken."""
    z = Path(zustand)
    try:
        alt = json.loads(z.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        alt = {}
    bekannt = set(alt.get("bekannt") or [])
    erg = pruefen(skills_dir, heute=heute, holen=holen)
    text = meldung(erg, bekannt)
    if text and notify:
        notify(text, abteilung="CLO", kategorie="info", quelle="rechtsquellen", detail="Skills unter skills/clo/ pruefen")
    erg["bekannt"] = sorted(bekannt | {f"{g['norm']}|{g['skill']}" for g in erg["geaendert"]} | {f"faellig|{s}" for s in erg["faellig"]})
    z.parent.mkdir(parents=True, exist_ok=True)
    z.write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    return erg
