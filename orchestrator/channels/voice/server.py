"""Einstieg fuer den Live-Voice-Kanal: WebRTC-Server (lokal) + statische Browser-Seite.

Start (nach GATE, mit Keys in orchestrator/.env):
    python -m orchestrator.channels.voice.server
    -> Browser oeffnen: http://localhost:7860

Transport: SmallWebRTC (lokal/peer-to-peer, kein kostenpflichtiger Dienst). STT/TTS sind
kostenpflichtig (CEO-Tor, am GATE freigegeben). Keys ausschliesslich aus orchestrator/.env
(Capability-Muster); der Adapter erhaelt die Faehigkeit, nie den Key.

Hinweis: Pipecat-Importe sind lazy und werden am GATE gegen die installierte Version bestaetigt.
Fehlt Pipecat, gibt der Start eine klare Installationsanweisung aus statt eines Tracebacks.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"

INSTALL_HINT = (
    "Voice-Abhaengigkeiten fehlen. Installation (siehe channels/voice/requirements.txt):\n"
    '  pip install "pipecat-ai[webrtc,deepgram,silero,elevenlabs]" fastapi uvicorn\n'
)


def _load_config() -> dict:
    with open(ROOT / "orchestrator" / "config.toml", "rb") as fh:
        return tomllib.load(fh)


def _load_secrets_map() -> dict:
    """liest orchestrator/.env als dict (nur fuer Capability-Uebergabe an die Services)."""
    env = ROOT / "orchestrator" / ".env"
    out: dict[str, str] = {}
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _build_live_core(cfg: dict, secret_values: list[str]):
    """Live-HoA-Kern (AgentSdkBackend) inkl. Gedaechtnis, Changelog, Leck-Schutz, CEO-Tor."""
    from functools import partial

    from ...core.backends import AgentSdkBackend
    from ...core.hoa import HeadOfAgents
    from ...core.memory import Memory
    from ...core.subagents import load_default_subagents
    from ...governance.ceo_gate_hook import CeoGate
    from ...governance.changelog_tool import append_changelog
    from ...observability.logging import Logger

    backend = AgentSdkBackend(cfg["models"], cfg["effort"], gate=CeoGate(),
                              max_turns=cfg["run"].get("max_turns", 4))
    changelog = partial(append_changelog, ROOT / cfg["governance"]["changelog_file"])
    mem_cfg = cfg.get("memory", {})
    memory = Memory(ROOT / mem_cfg.get("path", "orchestrator/memory/log.jsonl"),
                    secrets=secret_values, recall_limit=mem_cfg.get("recall_limit", 5)) \
        if mem_cfg.get("enabled", True) else None
    return HeadOfAgents(backend, load_default_subagents(), gate=CeoGate(),
                        leak_secrets=secret_values, changelog=changelog,
                        logger=Logger(), memory=memory)


def main() -> None:
    try:
        import pipecat  # noqa: F401
    except ImportError:
        print(INSTALL_HINT, file=sys.stderr)
        raise SystemExit(2)

    from .bridge import HoaBridge

    cfg = _load_config()
    vcfg = cfg.get("voice", {})
    secrets = _load_secrets_map()
    secret_values = [v for v in secrets.values() if v]

    core = _build_live_core(cfg, secret_values)
    bridge = HoaBridge(core, leak_secrets=secret_values, finance_dir=ROOT / "finance")

    _serve(bridge, vcfg, secrets)


def _serve(bridge, vcfg: dict, secrets: dict) -> None:
    """FastAPI + SmallWebRTC-Signaling + statische Seite. Pipeline pro Verbindung.

    GATE-verifiziert: die SmallWebRTC-Signaling-Details (offer/answer) werden beim GATE
    gegen die installierte Pipecat-Version bestaetigt.
    """
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pipecat.transports.smallwebrtc.connection import IceServer, SmallWebRTCConnection
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    from pipecat.transports.base_transport import TransportParams

    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        vad = SileroVADAnalyzer()
    except Exception:
        vad = None  # VAD optional; ohne VAD ist Barge-in eingeschraenkt

    from .pipeline import build_pipeline

    app = FastAPI()
    host = vcfg.get("host", "localhost")
    port = int(vcfg.get("port", 7860))

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.post("/api/offer")
    async def offer(payload: dict):
        connection = SmallWebRTCConnection(
            ice_servers=[IceServer(urls=["stun:stun.l.google.com:19302"])]
        )
        await connection.initialize(sdp=payload["sdp"], type=payload["type"])

        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=vad,
            ),
        )
        task, runner = build_pipeline(transport, bridge, vcfg, secrets)

        import asyncio
        asyncio.create_task(runner.run(task))

        answer = connection.get_answer()
        return {"sdp": answer["sdp"], "type": answer["type"]}

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    print(f"Live-Voice bereit -- Browser oeffnen: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
