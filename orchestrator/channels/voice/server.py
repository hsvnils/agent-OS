"""Einstieg fuer den Live-Voice-Kanal: WebRTC-Server (lokal) + statische Browser-Seite.

Start (nach GATE, mit Keys in orchestrator/.env):
    python -m orchestrator.channels.voice.server
    -> Browser oeffnen: http://localhost:7860

Transport: SmallWebRTC (lokal/peer-to-peer, kein kostenpflichtiger Dienst). STT/TTS sind
kostenpflichtig (CEO-Tor, am GATE freigegeben). Keys ausschliesslich aus orchestrator/.env
(Capability-Muster); der Adapter erhaelt die Faehigkeit, nie den Key.

Hinweis: Pipecat-Importe sind lazy und werden am GATE gegen die installierte Version bestaetigt.
Fehlt Pipecat, gibt der Start eine klare Installationsanweisung aus statt eines Tracebacks.

Hinweis: KEIN `from __future__ import annotations` -- FastAPI muss die Typen `Request`/
`BackgroundTasks` der Routen-Parameter zur Laufzeit erkennen (sonst 422 "missing query").
"""
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

    cfg = _load_config()
    secrets = _load_secrets_map()
    secret_values = [v for v in secrets.values() if v]

    core = _build_live_core(cfg, secret_values)
    _serve(core, cfg, secrets, secret_values)


def _serve(core, cfg: dict, secrets: dict, leak_secrets: list) -> None:
    """FastAPI + SmallWebRTC-Signaling + statische Seite. Pipeline pro Verbindung.

    Nutzt Pipecats `SmallWebRTCRequestHandler` (managt pc_id, POST-Offer UND PATCH-Renegotiation
    fuer die Audio-Spuren -- ohne PATCH bleibt die Bot-Audiospur stumm).
    """
    import uvicorn
    from fastapi import BackgroundTasks, FastAPI, Request
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
    from pipecat.transports.smallwebrtc.request_handler import (
        IceCandidate,
        SmallWebRTCPatchRequest,
        SmallWebRTCRequest,
        SmallWebRTCRequestHandler,
    )
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        vad = SileroVADAnalyzer()
    except Exception:
        vad = None  # VAD optional; ohne VAD ist Barge-in eingeschraenkt

    from .pipeline import build_pipeline

    app = FastAPI()
    vcfg = cfg.get("voice", {})
    host = vcfg.get("host", "localhost")
    port = int(vcfg.get("port", 7860))
    handler = SmallWebRTCRequestHandler(host=host)

    from .voices import GERMAN_VOICES, get_selected_voice_id, set_selected_voice_id

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/api/voices")
    async def list_voices():
        return {"voices": GERMAN_VOICES, "selected": get_selected_voice_id()}

    @app.post("/api/voice")
    async def set_voice(raw: Request):
        data = await raw.json()
        ok = set_selected_voice_id((data or {}).get("voice_id", ""))
        return {"ok": ok, "selected": get_selected_voice_id()}

    def _camel_to_snake(d: dict) -> dict:
        # Client (Pipecat JS) sendet teils camelCase; Server-Dataclass nutzt snake_case.
        out = dict(d)
        for cam, snake in (("pcId", "pc_id"), ("restartPc", "restart_pc"),
                           ("requestData", "request_data")):
            if cam in out and snake not in out:
                out[snake] = out.pop(cam)
        return out

    @app.post("/api/offer")
    async def offer(raw: Request, background_tasks: BackgroundTasks):
        data = _camel_to_snake(await raw.json())
        print("[voice] offer keys:", sorted(data.keys()), flush=True)
        allowed = {"sdp", "type", "pc_id", "restart_pc", "request_data"}
        request = SmallWebRTCRequest(**{k: v for k, v in data.items() if k in allowed})

        async def on_connection(connection: SmallWebRTCConnection):
            transport = SmallWebRTCTransport(
                webrtc_connection=connection,
                params=TransportParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    vad_analyzer=vad,
                ),
            )
            task, runner = build_pipeline(
                transport, core, vcfg, secrets,
                finance_dir=ROOT / "finance", leak_secrets=leak_secrets,
            )
            background_tasks.add_task(runner.run, task)

        return await handler.handle_web_request(
            request=request, webrtc_connection_callback=on_connection
        )

    @app.patch("/api/offer")
    async def ice_candidate(raw: Request):
        data = await raw.json()
        print("[voice] patch keys:", sorted(data.keys()),
              "cand0:", sorted((data.get("candidates") or [{}])[0].keys()), flush=True)
        cands = []
        for c in data.get("candidates", []):
            cands.append(IceCandidate(
                candidate=c.get("candidate", ""),
                sdp_mid=c.get("sdpMid", c.get("sdp_mid")),
                sdp_mline_index=c.get("sdpMLineIndex", c.get("sdp_mline_index")),
            ))
        request = SmallWebRTCPatchRequest(
            pc_id=data.get("pc_id") or data.get("pcId"), candidates=cands
        )
        await handler.handle_patch_request(request)
        return {"status": "success"}

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    print(f"Live-Voice bereit -- Browser oeffnen: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
