from __future__ import annotations

import base64
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.stt import SpeechToTextService, get_stt_service
from services.tts import TextToSpeechService, get_tts_service

router = APIRouter(prefix="/voice", tags=["voice"])


class TranscribeRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio payload")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    language: Optional[str] = Field(
        default=None, description="Force transcription language (e.g. 'tr')"
    )


class TranscribeResponse(BaseModel):
    text: str
    language: Optional[str]
    duration: Optional[float]
    segments: list[Dict[str, Any]]


class SynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text to transform into speech")
    voice: Optional[str] = Field(default=None, description="Voice preset or code")
    language: Optional[str] = Field(default=None, description="Language hint")


class SynthesizeResponse(BaseModel):
    audio_base64: str
    format: str
    sample_rate: int
    filename: Optional[str]


def _decode_audio(payload: str) -> bytes:
    try:
        return base64.b64decode(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload") from exc


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="Speech-to-text with faster-whisper",
)
def transcribe_endpoint(
    request: TranscribeRequest,
    stt: SpeechToTextService = Depends(get_stt_service),
) -> TranscribeResponse:
    audio = _decode_audio(request.audio_base64)
    try:
        result = stt.transcribe(
            audio,
            sample_rate=request.sample_rate,
            language=request.language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail="Transcription failed") from exc

    return TranscribeResponse(
        text=result["text"],
        language=result.get("language"),
        duration=result.get("duration"),
        segments=result.get("segments", []),
    )


@router.post(
    "/synthesize",
    response_model=SynthesizeResponse,
    summary="Text-to-speech synthesis",
)
def synthesize_endpoint(
    request: SynthesizeRequest,
    tts: TextToSpeechService = Depends(get_tts_service),
) -> SynthesizeResponse:
    try:
        result = tts.synthesize(
            request.text,
            voice=request.voice,
            lang=request.language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail="Synthesis failed") from exc

    audio_base64 = base64.b64encode(result.audio).decode("utf-8")
    return SynthesizeResponse(
        audio_base64=audio_base64,
        format=result.format,
        sample_rate=result.sample_rate,
        filename=result.filename,
    )
