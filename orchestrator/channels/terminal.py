"""Terminal-Chat-Adapter (Streaming). Der einzige Adapter dieses Builds.

Streams sind injizierbar (fuer Tests via io.StringIO).
"""
from __future__ import annotations

import sys
from typing import TextIO

from .base import ChannelAdapter


class TerminalAdapter(ChannelAdapter):
    def __init__(self, in_stream: TextIO | None = None, out_stream: TextIO | None = None,
                 prompt: str = "CEO> "):
        self.in_stream = in_stream or sys.stdin
        self.out = out_stream or sys.stdout
        self.prompt = prompt

    def next_message(self) -> str | None:
        self.out.write(self.prompt)
        self.out.flush()
        line = self.in_stream.readline()
        if not line:
            return None
        line = line.strip()
        if line.lower() in ("exit", "quit", ":q"):
            return None
        return line

    def emit(self, chunk: str) -> None:
        self.out.write(chunk)
        self.out.flush()
