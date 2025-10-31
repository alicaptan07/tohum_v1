from __future__ import annotations

import io
import logging
import shlex
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from typing import Optional

from core.config import Settings, get_settings

try:
    from gtts import gTTS  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    gTTS = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    audio: bytes
    format: str
    sample_rate: int
    filename: Optional[str] = None


class TextToSpeechService:
    """Text-to-speech facade supporting offline (piper) and online (gTTS) profiles."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._audio_dir = Path(self.settings.audio_tmp_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)

    def is_online_profile(self) -> bool:
        return self.settings.tts_profile == "online"

    def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        lang: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> TTSResult:
        if self.settings.tts_profile == "offline":
            return self._synthesize_with_piper(
                text,
                voice=voice,
                filename=filename,
            )
        return self._synthesize_with_gtts(
            text,
            voice=voice,
            lang=lang or self.settings.gtts_language,
            filename=filename,
        )

    # ------------------------------------------------------------------
    # Offline: Piper CLI
    # ------------------------------------------------------------------
    def _synthesize_with_piper(
        self,
        text: str,
        *,
        voice: Optional[str],
        filename: Optional[str],
    ) -> TTSResult:
        if not self.settings.piper_model_path:
            logger.warning(
                "PIPER_MODEL_PATH is not set; falling back to gTTS online synthesis."
            )
            return self._synthesize_with_gtts(
                text,
                voice=voice,
                lang=self.settings.gtts_language,
                filename=filename,
            )

        binary = shutil.which("piper")
        if not binary:
            logger.warning("piper binary not found; falling back to gTTS.")
            return self._synthesize_with_gtts(
                text,
                voice=voice,
                lang=self.settings.gtts_language,
                filename=filename,
            )

        output_path = self._resolve_output_path(filename or f"{uuid.uuid4()}.wav")
        command = f'{binary} --model "{self.settings.piper_model_path}" --output_file "{output_path}"'
        if voice or self.settings.piper_speaker:
            speaker = voice or self.settings.piper_speaker
            if speaker:
                command += f' --speaker "{speaker}"'

        logger.debug("Running piper command: %s", command)
        proc = subprocess.run(
            shlex.split(command),
            input=text.encode("utf-8"),
            capture_output=True,
        )
        if proc.returncode != 0:
            logger.error(
                "Piper synthesis failed: %s",
                proc.stderr.decode("utf-8", errors="ignore"),
            )
            raise RuntimeError("Piper synthesis failed.")

        audio_bytes = output_path.read_bytes()
        return TTSResult(
            audio=audio_bytes,
            format="wav",
            sample_rate=22050,
            filename=str(output_path),
        )

    # ------------------------------------------------------------------
    # Online: Google TTS
    # ------------------------------------------------------------------
    def _synthesize_with_gtts(
        self,
        text: str,
        *,
        voice: Optional[str],
        lang: str,
        filename: Optional[str],
    ) -> TTSResult:
        if gTTS is None:
            raise RuntimeError("gTTS is not installed. Install gTTS to use online TTS.")

        buffer = io.BytesIO()
        tts = gTTS(text=text, lang=lang, tld=self._resolve_tld_for_voice(voice))
        tts.write_to_fp(buffer)
        buffer.seek(0)

        output_path = self._resolve_output_path(filename or f"{uuid.uuid4()}.mp3")
        output_path.write_bytes(buffer.getvalue())

        return TTSResult(
            audio=buffer.getvalue(),
            format="mp3",
            sample_rate=22050,
            filename=str(output_path),
        )

    def _resolve_output_path(self, filename: str) -> Path:
        path = self._audio_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_tld_for_voice(self, voice: Optional[str]) -> str:
        if not voice:
            return "com.tr"
        mapping = {
            "tr": "com.tr",
            "en": "co.uk",
            "en-us": "com",
            "en-gb": "co.uk",
        }
        return mapping.get(voice.lower(), "com")

    def cleanup_expired(self, ttl_hours: Optional[int] = None) -> int:
        ttl = ttl_hours or self.settings.audio_ttl_hours
        removed = 0
        if ttl <= 0:
            return removed

        cutoff = self._now_timestamp() - (ttl * 3600)
        for path in self._audio_dir.glob("*"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except FileNotFoundError:  # pragma: no cover - race condition guard
                continue
        return removed

    def _now_timestamp(self) -> float:
        import time

        return time.time()


@lru_cache()
def get_tts_service() -> TextToSpeechService:
    return TextToSpeechService()
