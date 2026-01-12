"""API v1 router - aggregates all endpoint modules."""

from __future__ import annotations

from fastapi import APIRouter

from .playback import router as playback_router
from .talks import router as talks_router

api_router = APIRouter()

# Include sub-routers
api_router.include_router(talks_router, prefix="/talks", tags=["talks"])
api_router.include_router(playback_router, prefix="/playback", tags=["playback"])

# Future routers:
# api_router.include_router(vocabulary_router, prefix="/vocabulary", tags=["vocabulary"])
# api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
