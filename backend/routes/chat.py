from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.chat import ChatService, get_chat_service

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Active chat session identifier")
    message: str = Field(..., description="User message content")
    mode: str = Field(default="text", description="Interaction mode (text or voice)")
    user_id: Optional[str] = Field(
        default=None, description="Optional user identifier linked to the session"
    )


class ChatReply(BaseModel):
    reply: str
    message_id: str
    user_message_id: str
    context: List[Dict[str, Any]]


@router.post("/chat", response_model=ChatReply, summary="Create a chat turn")
def chat_endpoint(
    req: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatReply:
    try:
        result = service.handle_message(
            session_id=req.session_id,
            message=req.message,
            mode=req.mode,
            user_id=req.user_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatReply(
        reply=result.reply,
        message_id=result.message_id,
        user_message_id=result.user_message_id,
        context=result.context,
    )
