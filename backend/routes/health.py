from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from fastapi import APIRouter

from core.config import get_settings
from services.memory import get_memory_service
from services.stt import get_stt_service
from services.tts import get_tts_service

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe with dependency diagnostics")
def ready() -> Dict[str, object]:
    settings = get_settings()

    ffmpeg_path = _which("ffmpeg")
    stt_service = get_stt_service()
    tts_service = get_tts_service()
    memory_service = get_memory_service()

    sqlite_ok = _check_sqlite(settings.sqlite_path)
    chroma_ok = _check_chroma(settings.chroma_path)
    ffmpeg_ok = ffmpeg_path is not None
    stt_ok = stt_service.is_available()
    tts_ok, tts_details = _check_tts(settings)

    env_required = [
        "TTS_PROFILE",
        "WHISPER_DEVICE",
        "WHISPER_MODEL",
        "CHROMADB_PATH",
    ]
    missing_env = [key for key in env_required if not os.getenv(key)]

    checks: Dict[str, object] = {
        "ffmpeg": {"ok": ffmpeg_ok, "path": ffmpeg_path},
        "sqlite": {"ok": sqlite_ok, "path": settings.sqlite_path},
        "chroma": {"ok": chroma_ok, "path": settings.chroma_path},
        "stt": {"ok": stt_ok, "profile": settings.whisper_model},
        "tts": {"ok": tts_ok, "profile": settings.tts_profile, "details": tts_details},
        "env": {"ok": len(missing_env) == 0, "missing": missing_env},
        "audio_tmp": _check_audio_tmp(settings.audio_tmp_dir),
    }

    try:
        memory_service.list_memory_items(limit=1)
        checks["memory_service"] = {"ok": True}
    except Exception as exc:  # pragma: no cover - runtime guard
        checks["memory_service"] = {"ok": False, "error": str(exc)}

    checks["ready"] = (
        ffmpeg_ok
        and sqlite_ok
        and chroma_ok
        and tts_ok
        and len(missing_env) == 0
    )
    return checks


def _which(binary: str) -> str | None:
    from shutil import which

    return which(binary)


def _check_sqlite(path: str) -> bool:
    try:
        parent = Path(path).parent
        parent.mkdir(parents=True, exist_ok=True)
        test = parent / ".sqlite_check"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _check_chroma(path: str) -> bool:
    try:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        return target.exists()
    except Exception:
        return False


def _check_audio_tmp(path: str) -> Dict[str, object]:
    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(target)}


def _check_tts(settings) -> tuple[bool, Dict[str, object]]:
    details: Dict[str, object] = {}
    if settings.tts_profile == "offline":
        binary = _which("piper")
        details["piper_binary"] = binary
        details["model_path"] = settings.piper_model_path
        ok = bool(binary and settings.piper_model_path)
    else:
        try:
            from gtts import gTTS  # noqa: F401

            ok = True
        except ImportError:
            ok = False
    return ok, details
