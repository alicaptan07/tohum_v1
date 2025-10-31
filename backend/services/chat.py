from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.config import Settings, get_settings
from services.memory import MemoryService, get_memory_service

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    reply: str
    message_id: str
    context: List[Dict[str, Any]]
    user_message_id: str


class ChatService:
    """Thin orchestration layer for chat interactions."""

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.memory = memory_service or get_memory_service()

    def handle_message(
        self,
        session_id: str,
        message: str,
        *,
        mode: str = "text",
        user_id: Optional[str] = None,
    ) -> ChatResponse:
        self.memory.ensure_session(session_id, user_id)
        user_message_id = self.memory.append_message(
            session_id=session_id,
            role="user",
            text=message,
        )

        intent = self._detect_intent(message)
        if intent == "remember":
            payload, tags = self._extract_memory_payload(message)
            memory_id = self.memory.remember(
                payload,
                tags=tags,
                session_id=session_id,
                metadata={"source": "user", "mode": mode},
            )
            reply = f"Not ettim ({memory_id[:8]}…). Başka ne ekleyelim?"
            context: List[Dict[str, Any]] = []
        else:
            context = self.memory.search_memory(
                message, session_id=session_id, limit=5
            )
            reply = self._generate_reply(message, context)

        assistant_message_id = self.memory.append_message(
            session_id=session_id,
            role="assistant",
            text=reply,
        )
        return ChatResponse(
            reply=reply,
            message_id=assistant_message_id,
            context=context,
            user_message_id=user_message_id,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _detect_intent(self, message: str) -> str:
        normalized = message.strip().lower()
        triggers = ("hatırla:", "hatirla:", "remember:")
        return "remember" if normalized.startswith(triggers) else "chat"

    def _extract_memory_payload(self, message: str) -> tuple[str, List[str]]:
        body = message.split(":", 1)[-1].strip()
        tags: List[str] = []

        if "[" in body and body.endswith("]"):
            try:
                text_part, tags_part = body.rsplit("[", 1)
                tags_str = tags_part.strip("] ")
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                body = text_part.strip()
            except ValueError:
                logger.debug("Unable to parse tags from memory payload: %s", body)
        return body, tags

    def _generate_reply(
        self, message: str, context: List[Dict[str, Any]]
    ) -> str:
        if not context:
            return f"Mesajını aldım: {message}"

        highlights = "; ".join(item["text"] for item in context[:2])
        return (
            f"Daha önce not aldıkların: {highlights}. "
            f"Sorunla ilgili birlikte düşünelim: {message}"
        )


def get_chat_service() -> ChatService:
    return ChatService()
