from __future__ import annotations

import subprocess
from typing import Optional


def webm_to_pcm16(audio_bytes: bytes, sr: int = 16000) -> bytes:
    """Convert WebM/Opus audio bytes to PCM16 mono using FFmpeg."""

    command = [
        "ffmpeg",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(sr),
        "pipe:1",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    process = subprocess.run(
        command,
        input=audio_bytes,
        capture_output=True,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg conversion failed: {process.stderr.decode('utf-8', errors='ignore')}"
        )
    return process.stdout
