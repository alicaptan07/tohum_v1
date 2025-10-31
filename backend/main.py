from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.memory import router as memory_router
from routes.voice import router as voice_router
from routes.voice_ws import router as voice_ws_router

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(voice_ws_router)


@app.get("/")
def root() -> dict[str, bool]:
    return {"ok": True}
