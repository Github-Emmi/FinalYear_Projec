"""API v1 router. Phase 1: health check only."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check():
    """Returns 200 OK with status 'ok'. Used by Docker healthchecks and load balancers."""
    return {"status": "ok", "version": "1.0.0"}
