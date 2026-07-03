"""XMind tief verstehen (Phase 17, M5/#2) — LUNA liest UND bearbeitet den Inhalt einer .xmind-Datei.

`.xmind` (XMind Zen/2020+) ist ein ZIP mit `content.json` (Array von Blaettern, je mit `rootTopic` +
`children.attached`). LUNA kann so die Mindmap **strukturiert lesen** und **Knoten anlegen/umbenennen** —
ohne Screenshot, ohne Computer-Use. Praezise, aber app-spezifisch (nur XMind).

Hinweis (ehrlich): Aenderungen gehen in die DATEI. Hat XMind die Datei gerade offen, zeigt es sie erst nach
erneutem Oeffnen; am besten die Datei vor dem Bearbeiten schliessen oder danach neu oeffnen. „Live waehrend
geoeffnet" ist der Computer-Use-Weg (#3, ab 2026-07-01).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import zipfile
from pathlib import Path
from uuid import uuid4


def is_macos() -> bool:
    return sys.platform == "darwin"


def find_recent_xmind() -> str | None:
    """Neueste .xmind-Datei in Dokumente/Schreibtisch/Home (nach Aenderungszeit)."""
    bases = [Path.home() / "Documents", Path.home() / "Desktop", Path.home()]
    cands: list[str] = []
    for base in bases:
        try:
            cands += glob.glob(str(base / "**" / "*.xmind"), recursive=True)
        except Exception:
            continue
    cands = list(dict.fromkeys(cands))
    if not cands:
        return None
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0]


def _read_content(path: str) -> list:
    with zipfile.ZipFile(path, "r") as z:
        raw = z.read("content.json").decode("utf-8")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def _write_content(path: str, data: list) -> None:
    """content.json im ZIP ersetzen, alle anderen Eintraege unveraendert lassen."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "content.json":
                zout.writestr(item, json.dumps(data, ensure_ascii=False))
            else:
                zout.writestr(item, zin.read(item.filename))
    os.replace(tmp, path)


def _find_topic(topic: dict, ziel: str) -> dict | None:
    if (topic.get("title") or "").strip().lower() == ziel.strip().lower():
        return topic
    for kind in topic.get("children", {}).get("attached", []):
        treffer = _find_topic(kind, ziel)
        if treffer:
            return treffer
    return None


def _find_parent(topic: dict, ziel: str) -> dict | None:
    """Gibt den Knoten zurueck, dessen `children.attached` ein Kind mit Titel `ziel` enthaelt."""
    for kind in topic.get("children", {}).get("attached", []):
        if (kind.get("title") or "").strip().lower() == ziel.strip().lower():
            return topic
        treffer = _find_parent(kind, ziel)
        if treffer:
            return treffer
    return None


def _enthaelt(topic: dict, titel: str) -> bool:
    """True, wenn `topic` selbst oder ein Nachfahre `titel` traegt (Zyklus-Schutz beim Verschieben)."""
    if (topic.get("title") or "").strip().lower() == titel.strip().lower():
        return True
    return any(_enthaelt(k, titel) for k in topic.get("children", {}).get("attached", []))


def _walk(topic: dict, tiefe: int, lines: list) -> None:
    lines.append("  " * tiefe + "- " + (topic.get("title") or "(ohne Titel)"))
    for kind in topic.get("children", {}).get("attached", []):
        _walk(kind, tiefe + 1, lines)


def read_outline(path: str) -> dict:
    """Gibt die Mindmap als eingerueckte Gliederung zurueck. {ok, pfad, gliederung}."""
    try:
        data = _read_content(path)
    except Exception as exc:
        return {"ok": False, "grund": f"Konnte .xmind nicht lesen: {str(exc)[:200]}"}
    lines: list[str] = []
    for sheet in data:
        lines.append(f"# {sheet.get('title') or 'Blatt'}")
        root = sheet.get("rootTopic")
        if root:
            _walk(root, 0, lines)
    return {"ok": True, "pfad": path, "gliederung": "\n".join(lines)}


def add_node(path: str, titel: str, eltern: str | None = None) -> dict:
    titel = (titel or "").strip()
    if not titel:
        return {"ok": False, "grund": "Leerer Knoten-Titel."}
    try:
        data = _read_content(path)
    except Exception as exc:
        return {"ok": False, "grund": f"Lesefehler: {str(exc)[:200]}"}
    if not data:
        return {"ok": False, "grund": "Leere Mindmap."}
    target = None
    if eltern:
        for sheet in data:
            target = _find_topic(sheet.get("rootTopic", {}), eltern)
            if target:
                break
        if target is None:
            return {"ok": False, "grund": f"Eltern-Knoten '{eltern}' nicht gefunden."}
    else:
        target = data[0].get("rootTopic")
        if target is None:
            return {"ok": False, "grund": "Kein Wurzel-Knoten."}
    kinder = target.setdefault("children", {}).setdefault("attached", [])
    kinder.append({"id": uuid4().hex, "class": "topic", "title": titel})
    try:
        _write_content(path, data)
    except Exception as exc:
        return {"ok": False, "grund": f"Schreibfehler: {str(exc)[:200]}"}
    return {"ok": True, "pfad": path, "eltern": target.get("title"), "neuer_knoten": titel}


def rename_node(path: str, ziel: str, neuer_titel: str) -> dict:
    ziel = (ziel or "").strip()
    neuer_titel = (neuer_titel or "").strip()
    if not ziel or not neuer_titel:
        return {"ok": False, "grund": "Ziel oder neuer Titel fehlt."}
    try:
        data = _read_content(path)
    except Exception as exc:
        return {"ok": False, "grund": f"Lesefehler: {str(exc)[:200]}"}
    topic = None
    for sheet in data:
        topic = _find_topic(sheet.get("rootTopic", {}), ziel)
        if topic:
            break
    if topic is None:
        return {"ok": False, "grund": f"Knoten '{ziel}' nicht gefunden."}
    alt = topic.get("title")
    topic["title"] = neuer_titel
    try:
        _write_content(path, data)
    except Exception as exc:
        return {"ok": False, "grund": f"Schreibfehler: {str(exc)[:200]}"}
    return {"ok": True, "pfad": path, "alt": alt, "neu": neuer_titel}


def delete_node(path: str, ziel: str) -> dict:
    """Loescht den Knoten `ziel` (samt Unterknoten). Der Wurzel-Knoten kann nicht geloescht werden."""
    ziel = (ziel or "").strip()
    if not ziel:
        return {"ok": False, "grund": "Kein Ziel-Knoten."}
    try:
        data = _read_content(path)
    except Exception as exc:
        return {"ok": False, "grund": f"Lesefehler: {str(exc)[:200]}"}
    for sheet in data:
        root = sheet.get("rootTopic", {})
        if (root.get("title") or "").strip().lower() == ziel.lower():
            return {"ok": False, "grund": "Der Wurzel-Knoten kann nicht geloescht werden."}
        parent = _find_parent(root, ziel)
        if parent is None:
            continue
        attached = parent.get("children", {}).get("attached", [])
        neu = [k for k in attached if (k.get("title") or "").strip().lower() != ziel.lower()]
        parent["children"]["attached"] = neu
        try:
            _write_content(path, data)
        except Exception as exc:
            return {"ok": False, "grund": f"Schreibfehler: {str(exc)[:200]}"}
        return {"ok": True, "pfad": path, "geloescht": ziel, "anzahl": len(attached) - len(neu),
                "eltern": parent.get("title")}
    return {"ok": False, "grund": f"Knoten '{ziel}' nicht gefunden."}


def move_node(path: str, ziel: str, neuer_eltern: str) -> dict:
    """Verschiebt `ziel` (samt Unterknoten) unter den Knoten `neuer_eltern` (im selben Blatt)."""
    ziel = (ziel or "").strip()
    neuer_eltern = (neuer_eltern or "").strip()
    if not ziel or not neuer_eltern:
        return {"ok": False, "grund": "Ziel oder neuer Eltern-Knoten fehlt."}
    if ziel.lower() == neuer_eltern.lower():
        return {"ok": False, "grund": "Ziel und neuer Eltern-Knoten sind identisch."}
    try:
        data = _read_content(path)
    except Exception as exc:
        return {"ok": False, "grund": f"Lesefehler: {str(exc)[:200]}"}
    for sheet in data:
        root = sheet.get("rootTopic", {})
        if (root.get("title") or "").strip().lower() == ziel.lower():
            return {"ok": False, "grund": "Der Wurzel-Knoten kann nicht verschoben werden."}
        parent = _find_parent(root, ziel)
        if parent is None:
            continue                                   # Knoten nicht in diesem Blatt
        knoten = _find_topic(root, ziel)
        if _enthaelt(knoten, neuer_eltern):
            return {"ok": False, "grund": "Zielort liegt innerhalb des zu verschiebenden Knotens (Zyklus)."}
        neu_ziel = _find_topic(root, neuer_eltern)
        if neu_ziel is None:
            return {"ok": False, "grund": f"Neuer Eltern-Knoten '{neuer_eltern}' nicht gefunden (gleiches Blatt?)."}
        att = parent.get("children", {}).get("attached", [])
        parent["children"]["attached"] = [k for k in att if k is not knoten]
        neu_ziel.setdefault("children", {}).setdefault("attached", []).append(knoten)
        try:
            _write_content(path, data)
        except Exception as exc:
            return {"ok": False, "grund": f"Schreibfehler: {str(exc)[:200]}"}
        return {"ok": True, "pfad": path, "verschoben": ziel, "nach": neuer_eltern, "von": parent.get("title")}
    return {"ok": False, "grund": f"Knoten '{ziel}' nicht gefunden."}
