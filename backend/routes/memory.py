from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.memory import MemoryService, get_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class RememberRequest(BaseModel):
    text: str = Field(..., description="Content to store in long-term memory")
    session_id: Optional[str] = Field(
        default=None, description="Optional session reference for the memory"
    )
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0)


class RememberResponse(BaseModel):
    memory_id: str


@router.get(
    "/{session_id}",
    summary="Fetch messages and memory items for a session",
)
def get_session_memory(
    session_id: str,
    limit: int = 100,
    service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    try:
        messages = service.list_messages(session_id=session_id, limit=limit)
        memory_items = service.list_memory_items(session_id=session_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"messages": messages, "memory": memory_items}


@router.post(
    "/remember",
    response_model=RememberResponse,
    summary="Store a memory snippet",
    status_code=201,
)
def remember_endpoint(
    payload: RememberRequest,
    service: MemoryService = Depends(get_memory_service),
) -> RememberResponse:
    try:
        if payload.session_id:
            service.ensure_session(payload.session_id)
        memory_id = service.remember(
            payload.text,
            tags=payload.tags,
            metadata=payload.metadata,
            session_id=payload.session_id,
            trust_score=payload.trust_score,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RememberResponse(memory_id=memory_id)
