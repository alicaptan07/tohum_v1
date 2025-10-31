from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional

import numpy as np

from core.config import Settings, get_settings

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    WhisperModel = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


class SpeechToTextService:
    """Wrapper around faster-whisper with graceful degradation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        if WhisperModel is None:
            logger.warning("faster-whisper is not installed; STT disabled.")
            return

        try:
            self._model = WhisperModel(
                self.settings.whisper_model,
                device=self.settings.whisper_device,
                compute_type="auto",
            )
            logger.info(
                "Loaded Whisper model '%s' on device '%s'",
                self.settings.whisper_model,
                self.settings.whisper_device,
            )
        except Exception as exc:  # pragma: no cover - requires runtime model files
            logger.error("Failed to load Whisper model: %s", exc)
            self._model = None

    def is_available(self) -> bool:
        return self._model is not None

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._model:
            raise RuntimeError("Speech model not available. Install faster-whisper.")

        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments_iterator, info = self._model.transcribe(
            audio,
            beam_size=1,
            language=language,
        )

        transcript_segments: List[TranscriptionSegment] = []
        for segment in segments_iterator:
            transcript_segments.append(
                TranscriptionSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=getattr(segment, "avg_logprob", None),
                )
            )

        full_text = " ".join(seg.text for seg in transcript_segments).strip()
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "segments": [seg.__dict__ for seg in transcript_segments],
        }


@lru_cache()
def get_stt_service() -> SpeechToTextService:
    return SpeechToTextService()
