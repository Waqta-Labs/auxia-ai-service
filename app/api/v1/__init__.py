"""Endpoints that auxia-backend calls. All of them require the X-API-Key header."""

from fastapi import APIRouter, Depends

from app.api.v1 import distribution_recommendations, field_reports, urgency_scores
from app.core.security import require_api_key
from app.schemas.common import ErrorResponse

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
    responses={
        400: {"model": ErrorResponse, "description": "The request is not valid."},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key."},
    },
)
router.include_router(field_reports.router)
router.include_router(urgency_scores.router)
router.include_router(distribution_recommendations.router)
