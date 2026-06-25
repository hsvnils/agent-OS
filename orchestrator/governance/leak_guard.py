"""Leck-Schutz: redigiert Werte aus der .env aus beliebigem Text.

Greift kanaluebergreifend (Ausgaben, Tool-Ergebnisse, Changelog, CEO-Nachrichten),
damit nie ein Key im Klartext erscheint -- auch nicht in Logs oder Verlauf.
"""
from __future__ import annotations

from pathlib import Path

REDACTED = "[REDACTED]"


def is_redactable_secret(val: str) -> bool:
    """Nur echte Secrets redigieren -- NICHT kurze Flags/Zahlen/E-Mails.

    Sonst vergiftet z. B. `WEB_RESEARCH_ANTHROPIC=1` die Redaktion (jede '1' wuerde zu [REDACTED]) und
    verstuemmelt IDs, Zeitstempel und Logs. Echte Keys/Token sind lang und nicht rein numerisch.
    """
    val = (val or "").strip()
    if len(val) < 12:        # Flags ('1'), Chat-IDs, kurze Werte
        return False
    if val.isdigit():        # reine Zahlen (z. B. IDs)
        return False
    if "@" in val:           # E-Mail-Adressen (PII, aber kein Secret)
        return False
    return True


def redact(text: str, secrets: list[str]) -> str:
    out = text
    # laengste zuerst, damit Teilstrings nicht stehen bleiben
    for s in sorted((s for s in secrets if s), key=len, reverse=True):
        out = out.replace(s, REDACTED)
    return out


def load_env_secrets(env_path: str | Path) -> list[str]:
    p = Path(env_path)
    if not p.exists():
        return []
    vals: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        _, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        if is_redactable_secret(val):
            vals.append(val)
    return vals
