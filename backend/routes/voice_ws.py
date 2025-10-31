from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from routes.utils import webm_to_pcm16
from services.stt import SpeechToTextService, get_stt_service
from services.tts import TextToSpeechService, get_tts_service

router = APIRouter(prefix="/ws", tags=["voice-ws"])


@router.websocket("/voice")
async def voice_socket(
    websocket: WebSocket,
    stt: SpeechToTextService = Depends(get_stt_service),
    tts: TextToSpeechService = Depends(get_tts_service),
) -> None:
    await websocket.accept()
    buffer = bytearray()

    try:
        await websocket.send_json({"type": "ready"})
        while True:
            message = await websocket.receive()
            if chunk := message.get("bytes"):
                await _handle_audio_chunk(websocket, chunk, buffer, stt)
            else:
                text_data = message.get("text")
                if text_data is None:
                    continue
                await _handle_text_command(websocket, text_data, buffer, stt, tts)
    except WebSocketDisconnect:
        return


async def _handle_audio_chunk(
    websocket: WebSocket,
    chunk: bytes,
    buffer: bytearray,
    stt: SpeechToTextService,
) -> None:
    try:
        pcm = webm_to_pcm16(chunk, sr=16000)
    except RuntimeError as exc:
        await websocket.send_json({"type": "error", "reason": str(exc)})
        return

    buffer.extend(pcm)
    try:
        result = stt.transcribe(bytes(buffer), sample_rate=16000)
    except RuntimeError as exc:
        await websocket.send_json({"type": "error", "reason": str(exc)})
        return

    await websocket.send_json(
        {
            "type": "partial",
            "text": result.get("text", ""),
            "language": result.get("language"),
        }
    )


async def _handle_text_command(
    websocket: WebSocket,
    payload: str,
    buffer: bytearray,
    stt: SpeechToTextService,
    tts: TextToSpeechService,
) -> None:
    try:
        message = json.loads(payload)
    except json.JSONDecodeError:
        await websocket.send_json(
            {"type": "error", "reason": "Invalid JSON payload received."}
        )
        return

    command = message.get("type")
    if command == "flush":
        if not buffer:
            await websocket.send_json({"type": "final", "text": "", "language": None})
            return
        try:
            result = stt.transcribe(bytes(buffer), sample_rate=16000)
        except RuntimeError as exc:
            await websocket.send_json({"type": "error", "reason": str(exc)})
            return
        buffer.clear()
        await websocket.send_json(
            {
                "type": "final",
                "text": result.get("text", ""),
                "language": result.get("language"),
            }
        )
    elif command == "reset":
        buffer.clear()
        await websocket.send_json({"type": "reset"})
    elif command == "speak":
        text = message.get("text")
        if not text:
            await websocket.send_json(
                {"type": "error", "reason": "Missing 'text' for speak command."}
            )
            return
        voice = message.get("voice")
        language = message.get("language")
        try:
            result = tts.synthesize(text, voice=voice, lang=language)
        except RuntimeError as exc:
            await websocket.send_json({"type": "error", "reason": str(exc)})
            return
        await websocket.send_json(
            {
                "type": "tts",
                "audio_base64": base64.b64encode(result.audio).decode("utf-8"),
                "format": result.format,
                "sample_rate": result.sample_rate,
            }
        )
    else:
        await websocket.send_json(
            {"type": "error", "reason": f"Unknown command: {command}"}
        )
