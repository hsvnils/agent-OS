"""Pipecat-Pipeline fuer den Live-Voice-Kanal (Laufzeit, erst am GATE aktiv).

Pipeline:  transport.input() -> STT -> HoaProcessor (Bruecke zum HoA-Kern) -> TTS -> transport.output()

- Barge-in: ueber PipelineParams(allow_interruptions=True) + VAD; laufende TTS/Antwort wird beim
  Lossprechen des CEO abgebrochen.
- Der HoA-Kern laeuft synchron (AgentSdkBackend nutzt intern asyncio.run); damit kein Event-Loop
  verschachtelt wird, ruft der Processor die Bruecke in einem Thread-Executor auf.
- show_panel: liefert die Bruecke ein Panel, sendet der Processor es als Transport-Message ueber den
  WebRTC-Datenkanal an die Browser-Seite (parallel zur gesprochenen Antwort).

Hinweis: Lazy imports -- Pipecat wird erst am GATE installiert. Die genauen Importpfade folgen der
oeffentlichen Pipecat-1.x-API und werden beim GATE gegen die installierte Version bestaetigt.
"""
from __future__ import annotations

import asyncio

from .bridge import BridgeResult, HoaBridge


def build_stt(cfg: dict, secrets: dict):
    """STT-Service aus Config (Default: Deepgram). Key kommt aus .env (Capability-Muster)."""
    provider = cfg.get("stt_provider", "deepgram").lower()
    if provider == "deepgram":
        from pipecat.services.deepgram.stt import DeepgramSTTService
        return DeepgramSTTService(api_key=secrets["DEEPGRAM_API_KEY"],
                                  live_options={"language": cfg.get("language", "de")})
    raise ValueError(f"Unbekannter STT-Provider: {provider}")


def build_tts(cfg: dict, secrets: dict):
    """TTS-Service aus Config (Cartesia ODER ElevenLabs). Key kommt aus .env."""
    provider = cfg.get("tts_provider", "cartesia").lower()
    if provider == "cartesia":
        from pipecat.services.cartesia.tts import CartesiaTTSService
        return CartesiaTTSService(api_key=secrets["CARTESIA_API_KEY"],
                                  voice_id=cfg.get("tts_voice_id", ""))
    if provider == "elevenlabs":
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        return ElevenLabsTTSService(api_key=secrets["ELEVENLABS_API_KEY"],
                                    voice_id=cfg.get("tts_voice_id", ""))
    raise ValueError(f"Unbekannter TTS-Provider: {provider}")


def make_hoa_processor(bridge: HoaBridge):
    """Custom FrameProcessor: erkannter Text -> HoA-Bruecke -> gesprochene Antwort (+ Panel)."""
    from pipecat.frames.frames import (
        StartInterruptionFrame,
        TranscriptionFrame,
        TransportMessageUrgentFrame,
        TTSSpeakFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class HoaProcessor(FrameProcessor):
        async def process_frame(self, frame, direction: "FrameDirection"):
            await super().process_frame(frame, direction)

            # Barge-in: CEO spricht los -> nichts weiter tun, Pipeline bricht TTS selbst ab.
            if isinstance(frame, StartInterruptionFrame):
                await self.push_frame(frame, direction)
                return

            # Finaler erkannter Satz des CEO -> HoA-Kern befragen.
            if isinstance(frame, TranscriptionFrame) and frame.text and frame.text.strip():
                loop = asyncio.get_running_loop()
                # Bruecke (synchron, HoA-Kern) im Executor -> kein verschachtelter Event-Loop.
                result: BridgeResult = await loop.run_in_executor(
                    None, self.bridge_respond, frame.text
                )
                # Panel zuerst einblenden (parallel zur Sprache).
                if result.panel is not None:
                    await self.push_frame(
                        TransportMessageUrgentFrame(message={"kind": "panel", "panel": result.panel})
                    )
                if result.spoken:
                    await self.push_frame(TTSSpeakFrame(result.spoken))
                return

            await self.push_frame(frame, direction)

        def bridge_respond(self, text: str) -> BridgeResult:
            return bridge.respond(text)

    return HoaProcessor()


def build_pipeline(transport, bridge: HoaBridge, cfg: dict, secrets: dict):
    """Setzt die komplette Pipeline + Task zusammen und gibt (task, runner) zurueck."""
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask

    stt = build_stt(cfg, secrets)
    tts = build_tts(cfg, secrets)
    hoa = make_hoa_processor(bridge)

    pipeline = Pipeline([
        transport.input(),
        stt,
        hoa,
        tts,
        transport.output(),
    ])
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    runner = PipelineRunner(handle_sigint=False)
    return task, runner
