"""Nutzungs-Protokoll (Feature-Friedhof) -- zaehlt App-Oeffnungen in LUNA-OS. Bewusst minimal.

Erfasst wird NUR: Zeitstempel + App-Id (+ optional Nutzername). Keine Inhalte, keine Klickpfade, keine
Verweildauer. Zweck: der Leistungs-Agent erkennt brachliegende Apps ("Feature-Friedhof"), damit Gebautes,
das niemand nutzt, sichtbar wird. Vom CEO ausdruecklich gewuenscht (2026-07-10).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class NutzungStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def log(self, app: str, *, user: str = "") -> None:
        """Eine App-Oeffnung protokollieren. Best-effort -- Fehler duerfen nie die UI stoeren."""
        app = (app or "").strip()[:40]
        if not app:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            ev = {"ts": datetime.now().isoformat(timespec="seconds"), "app": app}
            if user:
                ev["user"] = user[:40]
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text("utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
        return out
