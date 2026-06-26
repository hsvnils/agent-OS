"""Phase 14 -- generische Visualisierungs-Schicht (frei darstellbar, ohne externe Dienste).

LUNA kann Inhalte nicht nur als feste Panel-Typen, sondern **frei visuell** darstellen: MindMap,
Organigramm, Graph, Balkendiagramm. Die Darstellung ist eine **Spezifikation** (dict), aus der ein
**reines SVG** erzeugt wird -- ohne Fremd-Bibliotheken und ohne externe Render-Dienste (Phase-14-GATE:
keine externen Kosten). Dasselbe SVG nutzen der Telegram-Kanal (als Datei) und die Browser-Oberflaeche
(Panel). Die bisherigen festen Panels werden so zu Spezialfaellen einer generischen Schicht.

Spezifikations-Typen:
- mindmap:     {"type":"mindmap","titel":..,"wurzel":..,"zweige":[{"label":..,"kinder":[..]}, ..]}
- organigramm: {"type":"organigramm","titel":..}              (aus dem Agenten-Verzeichnis gebaut)
- balken:      {"type":"balken","titel":..,"werte":[["Label",zahl], ..]}
- graph:       {"type":"graph","titel":..,"knoten":[..],"kanten":[["a","b"], ..]}
"""
from __future__ import annotations

import math
from html import escape

_FARBEN = ["#2563eb", "#16a34a", "#db2777", "#d97706", "#7c3aed", "#0891b2",
           "#dc2626", "#4f46e5", "#059669", "#ca8a04"]
_BG = "#0b1220"
_FG = "#e5e7eb"
_MUTED = "#94a3b8"


def _esc(s) -> str:
    return escape(str(s), quote=True)


def _breite(text: str, *, px: float = 7.2) -> float:
    return max(40.0, len(str(text)) * px + 22)


# -- Spezifikations-Builder --------------------------------------------------

def mindmap(titel: str, wurzel: str, zweige: list[dict]) -> dict:
    return {"type": "mindmap", "titel": titel, "wurzel": wurzel, "zweige": zweige}


def balken(titel: str, werte: list) -> dict:
    norm = []
    for w in werte:
        if isinstance(w, (list, tuple)) and len(w) >= 2:
            try:
                norm.append([str(w[0]), float(w[1])])
            except (TypeError, ValueError):
                continue
    return {"type": "balken", "titel": titel, "werte": norm}


def graph(titel: str, knoten: list, kanten: list) -> dict:
    return {"type": "graph", "titel": titel, "knoten": [str(k) for k in knoten],
            "kanten": [[str(a), str(b)] for a, b in kanten if a and b]}


def organigramm(titel: str = "Organigramm") -> dict:
    """Organigramm des Unternehmens als MindMap-Spezifikation (CEO -> HoA -> Abteilungen)."""
    try:
        from ..channels.voice.directory import AGENTS
        zweige = [{"label": f"{a['kuerzel']} -- {a['name']}", "kinder": [a["bereich"]]} for a in AGENTS]
    except Exception:
        zweige = []
    return {"type": "organigramm", "titel": titel,
            "wurzel": "CEO (Nils) -> Head of Agents (LUNA)", "zweige": zweige}


# -- Render -> SVG -----------------------------------------------------------

def to_svg(spec: dict) -> str:
    t = (spec or {}).get("type")
    if t in ("mindmap", "organigramm"):
        return _svg_mindmap(spec)
    if t == "balken":
        return _svg_balken(spec)
    if t == "graph":
        return _svg_graph(spec)
    return _svg_rahmen(800, 200, spec.get("titel", "Visualisierung"),
                       [f'<text x="400" y="120" fill="{_MUTED}" font-size="16" '
                        f'text-anchor="middle">Unbekannter Typ: {_esc(t)}</text>'])


def _svg_rahmen(w: float, h: float, titel: str, inner: list[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(w)} {int(h)}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">'
        f'<rect x="0" y="0" width="{int(w)}" height="{int(h)}" rx="14" fill="{_BG}"/>'
        f'<text x="{int(w/2)}" y="34" fill="{_FG}" font-size="20" font-weight="700" '
        f'text-anchor="middle">{_esc(titel)}</text>'
        + "".join(inner) + "</svg>"
    )


def _knoten(x: float, y: float, text: str, farbe: str, *, gross: bool = False) -> str:
    bw = _breite(text, px=8 if gross else 7.2)
    bh = 38 if gross else 30
    fs = 15 if gross else 13
    return (
        f'<g><rect x="{x - bw/2:.1f}" y="{y - bh/2:.1f}" width="{bw:.1f}" height="{bh}" rx="9" '
        f'fill="{farbe}" opacity="0.92"/>'
        f'<text x="{x:.1f}" y="{y + fs*0.35:.1f}" fill="#ffffff" font-size="{fs}" '
        f'font-weight="{700 if gross else 600}" text-anchor="middle">{_esc(text)}</text></g>'
    )


def _svg_mindmap(spec: dict) -> str:
    zweige = spec.get("zweige", []) or []
    n = max(1, len(zweige))
    cx, cy = 500.0, 360.0
    radius = 250.0
    w, h = 1000.0, 720.0
    inner: list[str] = []
    for i, zw in enumerate(zweige):
        ang = (2 * math.pi * i / n) - math.pi / 2
        zx, zy = cx + radius * math.cos(ang), cy + radius * math.sin(ang)
        farbe = _FARBEN[i % len(_FARBEN)]
        inner.append(f'<line x1="{cx}" y1="{cy}" x2="{zx:.1f}" y2="{zy:.1f}" '
                     f'stroke="{farbe}" stroke-width="2" opacity="0.6"/>')
        for j, kind in enumerate(zw.get("kinder", []) or []):
            kr = radius + 95 + j * 34
            kx, ky = cx + kr * math.cos(ang), cy + kr * math.sin(ang)
            inner.append(f'<line x1="{zx:.1f}" y1="{zy:.1f}" x2="{kx:.1f}" y2="{ky:.1f}" '
                         f'stroke="{_MUTED}" stroke-width="1" opacity="0.4"/>')
            inner.append(_knoten(kx, ky, kind, "#1e293b"))
        inner.append(_knoten(zx, zy, zw.get("label", "?"), farbe))
    inner.append(_knoten(cx, cy, spec.get("wurzel", "?"), "#0f172a", gross=True))
    return _svg_rahmen(w, h, spec.get("titel", "MindMap"), inner)


def _svg_balken(spec: dict) -> str:
    werte = spec.get("werte", []) or []
    if not werte:
        return _svg_rahmen(800, 200, spec.get("titel", "Diagramm"),
                           [f'<text x="400" y="120" fill="{_MUTED}" font-size="16" '
                            f'text-anchor="middle">Keine Werte</text>'])
    maxv = max((v for _, v in werte), default=1) or 1
    n = len(werte)
    pad_l, pad_b, top = 60, 70, 70
    bar_area_h = 360
    w = max(640, 80 + n * 90)
    h = top + bar_area_h + pad_b
    bw = (w - pad_l - 30) / n * 0.6
    gap = (w - pad_l - 30) / n
    inner = [f'<line x1="{pad_l}" y1="{top + bar_area_h}" x2="{w - 20}" y2="{top + bar_area_h}" '
             f'stroke="{_MUTED}" stroke-width="1.5"/>']
    for i, (label, v) in enumerate(werte):
        bh = (v / maxv) * (bar_area_h - 20)
        x = pad_l + i * gap + (gap - bw) / 2
        y = top + bar_area_h - bh
        farbe = _FARBEN[i % len(_FARBEN)]
        inner.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" '
                     f'fill="{farbe}"/>')
        inner.append(f'<text x="{x + bw/2:.1f}" y="{y - 8:.1f}" fill="{_FG}" font-size="13" '
                     f'font-weight="600" text-anchor="middle">{_esc(_zahl(v))}</text>')
        inner.append(f'<text x="{x + bw/2:.1f}" y="{top + bar_area_h + 22:.1f}" fill="{_MUTED}" '
                     f'font-size="12" text-anchor="middle">{_esc(label)}</text>')
    return _svg_rahmen(w, h, spec.get("titel", "Diagramm"), inner)


def _svg_graph(spec: dict) -> str:
    knoten = spec.get("knoten", []) or []
    kanten = spec.get("kanten", []) or []
    n = max(1, len(knoten))
    cx, cy, r = 450.0, 360.0, 230.0
    w, h = 900.0, 720.0
    pos = {}
    for i, k in enumerate(knoten):
        ang = (2 * math.pi * i / n) - math.pi / 2
        pos[k] = (cx + r * math.cos(ang), cy + r * math.sin(ang))
    inner: list[str] = []
    for a, b in kanten:
        if a in pos and b in pos:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            inner.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{_MUTED}" stroke-width="1.5" opacity="0.5"/>')
    for i, k in enumerate(knoten):
        x, y = pos[k]
        inner.append(_knoten(x, y, k, _FARBEN[i % len(_FARBEN)]))
    return _svg_rahmen(w, h, spec.get("titel", "Graph"), inner)


def _zahl(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


# -- Komfort: einfache Texteingaben (vom LUNA-Tool) zu Spezifikation ---------

def aus_text(art: str, titel: str, inhalt: str = "") -> dict:
    """Baut eine Spezifikation aus einfachen Text-Eingaben, damit LUNA sie per Sprache/Text fuellen kann.

    - mindmap:  inhalt = "Zweig A: kind1, kind2; Zweig B: kind3"
    - balken:   inhalt = "Label1=10, Label2=20"
    - graph:    inhalt = "a-b, b-c, c-a"  (Knoten implizit aus den Kanten)
    - organigramm: inhalt ignoriert (aus dem Verzeichnis).
    """
    art = (art or "").strip().lower()
    titel = titel or art.capitalize()
    if art == "organigramm":
        return organigramm(titel)
    if art == "balken":
        werte = []
        for teil in (inhalt or "").split(","):
            if "=" in teil:
                k, _, v = teil.partition("=")
                werte.append([k.strip(), v.strip()])
        return balken(titel, werte)
    if art == "graph":
        kanten, knoten = [], []
        for teil in (inhalt or "").replace(";", ",").split(","):
            if "-" in teil:
                a, _, b = teil.partition("-")
                a, b = a.strip(), b.strip()
                if a and b:
                    kanten.append([a, b])
                    knoten += [a, b]
        return graph(titel, list(dict.fromkeys(knoten)), kanten)
    # Default: mindmap
    zweige = []
    for block in (inhalt or "").split(";"):
        block = block.strip()
        if not block:
            continue
        if ":" in block:
            label, _, rest = block.partition(":")
            kinder = [x.strip() for x in rest.split(",") if x.strip()]
            zweige.append({"label": label.strip(), "kinder": kinder})
        else:
            zweige.append({"label": block, "kinder": []})
    return mindmap(titel, titel, zweige)
