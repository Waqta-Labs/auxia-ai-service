"""Urgency score of a zone (US-04, US-05, TS-02)."""

from http import HTTPStatus

from fastapi import APIRouter

from app.core.config import MODEL_VERSION
from app.core.errors import ApiError
from app.schemas.common import ErrorDetail
from app.schemas.urgency_scores import CalculateUrgencyScoreRequest, UrgencyScoreResponse
from app.services.urgency import InsufficientVariablesError, calculate_urgency_score

router = APIRouter(prefix="/urgency-scores", tags=["urgency scores"])


@router.post(
    "",
    summary="Calculate the urgency score of a zone",
    description="Responds 400 INSUFFICIENT_VARIABLES when damageLevel or peopleAffected is null.",
)
def calculate(request: CalculateUrgencyScoreRequest) -> UrgencyScoreResponse:
    try:
        urgency = calculate_urgency_score(request.indicators, request.zone_population)
    except InsufficientVariablesError as exc:
        raise ApiError(
            HTTPStatus.BAD_REQUEST,
            "INSUFFICIENT_VARIABLES",
            "The urgency score cannot be calculated with the variables received.",
            [
                ErrorDetail(
                    field=f"indicators.{variable}", message="Required to calculate the score"
                )
                for variable in exc.missing_variables
            ],
        ) from exc
    return UrgencyScoreResponse(
        score=urgency.score,
        priority_level=urgency.priority_level,
        top_features=urgency.top_features,
        model_version=MODEL_VERSION,
    )
