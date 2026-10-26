"""Health check. It is open, so the backend and the hosting platform can probe the service."""

from fastapi import APIRouter

from app.core.config import MODEL_VERSION, VERSION
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check that the service is up")
def health() -> HealthResponse:
    return HealthResponse(status="UP", version=VERSION, model_version=MODEL_VERSION)
