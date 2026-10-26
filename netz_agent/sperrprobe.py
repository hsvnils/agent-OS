"""Sperrprobe des Netz-Agenten (NETZ_AGENT_ROADMAP.md, Q4): kommt der Container ins Heimnetz? Er darf es nicht.

Versucht kurze TCP-Verbindungen zu Fritz!Box, NAS (DSM, LUNA-OS), MACO470, zum Docker-Gateway und zum Container
`luna-os`; jede davon muss scheitern. Gegenprobe: die Brave-Schnittstelle muss erreichbar sein (sonst sperrt die Regel
zu viel). Ergebnis schreibt der Agent alle 5 min nach `netz_queue/zustand.json`; LUNAs Systemcheck liest daraus nur
`heimnetz_gesperrt` und den Zeitpunkt. Nur Standardbibliothek.

Aufruf im Container: `python -m netz_agent.sperrprobe`
"""
from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone

HEIMNETZ = [
    ("Fritz!Box", "192.168.178.1", 80),
    ("NAS DSM", "192.168.178.129", 5001),
    ("NAS LUNA-OS", "192.168.178.129", 8765),
    ("MACO470 SSH", "192.168.178.184", 22),
    ("Docker-Gateway (NAS)", "172.30.99.1", 8765),
    ("Container luna-os", "luna-os", 8765),
]
INTERNET = ("Brave-Schnittstelle", "api.search.brave.com", 443)


def _verbinden(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:                                    # abgelehnt, Zeitlimit, Name unbekannt -> nicht erreichbar
        return False


def pruefen(verbinden=_verbinden, *, timeout: float = 3.0) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    ziele = HEIMNETZ + [INTERNET]
    with ThreadPoolExecutor(max_workers=len(ziele)) as pool:          # gleichzeitig: gesperrte Ziele laufen ins Zeitlimit
        erreichbar = list(pool.map(lambda z: verbinden(z[1], z[2], timeout), ziele))
    offen = [z[0] for z, ok in zip(HEIMNETZ, erreichbar) if ok]
    internet = erreichbar[-1]
    return {"heimnetz_gesperrt": not offen, "heimnetz_offen": offen, "internet": internet,
            "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def main() -> None:
    e = pruefen()
    print(json.dumps(e, ensure_ascii=False))
    sys.exit(0 if e["heimnetz_gesperrt"] and e["internet"] else 1)


if __name__ == "__main__":
    main()
